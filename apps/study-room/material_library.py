"""Study-room evidence lookup. Local cache and tokenizer only; never generates model answers."""
import hashlib
import importlib.util
import json
import os
import re
import threading
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
LOCK=threading.RLock()
MODULES={}

def module(name,path):
    if name not in MODULES:
        spec=importlib.util.spec_from_file_location(name,path)
        obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);MODULES[name]=obj
    return MODULES[name]

def engine():
    return module('study_material_cache',PROJECT/'skills/sources/study-cache/scripts/study_cache.py')

def auditor():
    return module('study_material_audit',PROJECT/'skills/management/stella-token-audit/scripts/token_audit.py')

def group_key(source):
    fields=[source.get('exam','중간고사'),source['course'],source['scope'],source['title']]
    return hashlib.sha256(json.dumps(fields,ensure_ascii=False).encode()).hexdigest()[:24]

def catalog(sources,exam):
    if exam not in ('중간고사','기말고사'):raise ValueError('시험 구분을 선택해 주세요.')
    groups={}
    for s in sources.values():
        if s.get('course')=='demo' or s.get('exam','중간고사')!=exam:continue
        key=group_key(s)
        item=groups.setdefault(key,{'id':key,'course':s['course'],'scope':s['scope'],'title':s['title'],'sections':0})
        item['sections']+=1
    return sorted(groups.values(),key=lambda s:(s['course'],s['scope'],s['title']))

def keywords(question):
    stop={'설명해줘','알려줘','무엇인가','어떤','비교해줘','해줘','뭐야','대해','뭔가요','설명','주세요'}
    words=re.findall(r'[\w-]+',question)
    return ' '.join(w for w in words if w not in stop) or question

def prepare(sources,exam,group,private):
    entries=sorted((s for s in sources.values() if group_key(s)==group and s.get('exam','중간고사')==exam),key=lambda s:s['id'])
    if not entries:raise ValueError('등록된 해당 시험 자료가 없습니다. 다른 시험 자료를 자동 포함하지 않습니다.')
    # Preserve one entry per source ID; source coordinates stay in the response mapping.
    data={'tabs':[{'tabProperties':{'title':s['location'],'tabId':s['id']},
                    'documentTab':{'body':{'content':[{'paragraph':{'elements':[{'textRun':{'content':s['text']}}]}}]}}} for s in entries]}
    text=json.dumps(data,ensure_ascii=False,separators=(',',':'))
    directory=Path(private)/'materials-cache';directory.mkdir(parents=True,exist_ok=True)
    file=directory/(group+'.json')
    if not file.exists() or file.read_text('utf-8')!=text:
        tmp=file.with_suffix('.tmp');tmp.write_text(text,encoding='utf-8');tmp.replace(file)
    cache=engine();db=cache.connect(directory/'sources.sqlite')
    try:
        ingest=cache.ingest(db,SimpleNamespace(file=str(file),course=exam+'::'+entries[0]['course'],remote_id='',revision=''))
    except Exception:db.close();raise
    return entries,cache,db,ingest

def context_text(items):
    return '\n\n'.join('['+s['id']+' · '+s['location']+']\n'+s['text'] for s in items)

def compare_text(before,after,required):
    try:
        audit=auditor()
        enc=audit.tokenizer('o200k_base',Path(os.environ.get('STELLA_TOKEN_AUDIT_RUNTIME', str(PROJECT/'local/token-audit'))),Path(os.environ.get('STELLA_TOKEN_CACHE', str(PROJECT/'local/token-cache'))))
        result=audit.text_comparison(before,after,enc,required)
        return {'available':True,'encoding':result['encoding'],**result['text_tokens'],
                'missing':result['required_literal_checks']['after_missing'],
                'baselineMissing':result['required_literal_checks']['baseline_missing'],
                'status':result['status'],'scope':'선택한 범위의 전체 근거 텍스트 ↔ 검색 발췌 텍스트 (출처 표기 포함)',
                'wholeTask':None,'semanticQualityVerified':False}
    except (ImportError,ValueError,OSError):
        return {'available':False,'before':None,'after':None,'saved':None,'reduction_percent':None,
                'beforeChars':len(before),'afterChars':len(after),'missing':[s for s in required if s not in after],
                'baselineMissing':[s for s in required if s not in before],
                'scope':'토크나이저 미준비: 문자 수만 확인 가능','wholeTask':None,'semanticQualityVerified':False}

def search(sources,payload,private):
    exam=payload.get('exam','기말고사'); group=payload.get('group')
    if exam not in ('기말고사','중간고사') or not isinstance(group,str) or not re.fullmatch(r'[0-9a-f]{24}',group):
        raise ValueError('시험과 자료를 선택해 주세요.')
    question=payload.get('question','')
    if not isinstance(question,str) or not 1<=len(question.strip())<=500:raise ValueError('질문은 1~500자로 입력해 주세요.')
    required=payload.get('required',[])
    if not isinstance(required,list) or len(required)>12 or any(not isinstance(v,str) or not 1<=len(v)<=150 for v in required):
        raise ValueError('필수 표현은 최대 12개, 각 150자까지입니다.')
    budget=payload.get('budget',3600)
    if type(budget) is not int or not 300<=budget<=7200:raise ValueError('발췌 한도는 300~7200자입니다.')
    with LOCK:
        entries,cache,db,ingest=prepare(sources,exam,group,private)
        try:
            result=cache.search(db,SimpleNamespace(query=keywords(question),course=exam+'::'+entries[0]['course'],
                source_id=ingest['source_id'],limit=3,max_chars=min(1200,budget),max_total_chars=budget,context_sections=0))
        finally:db.close()
    selected=[]
    for h in result['hits']:
        s=entries[h['section']-1]
        selected.append({'id':s['id'],'title':s['title'],'location':s['location'],'page':s.get('page'),
            'kind':s.get('sourceKind','미확인'),'text':h['text'],'truncated':h['truncated'],
            'offset':h['offset'],'section':h['section'],'duplicates':h.get('duplicate_count',0)})
    before=context_text(entries);after=context_text(selected)
    counts=compare_text(before,after,required)
    return {'exam':exam,'group':group,'question':question,'query':keywords(question),'cache':ingest['status'],
            'registeredSections':len(entries),'matchedSections':result['matched_sections'],'hits':selected,
            'tokens':counts,'modelCalls':0,'remoteFreshness':'로컬 저장본 · 원격 최신 상태 미확인',
            'quality':{'automatic':'필수 표현 문자열 검사만 수행. 정의·조건·예외의 의미 검토는 직접 확인하세요.',
                       'definition':None,'conditions':None,'exceptions':None},
            'prompt':('제공한 근거만 사용해 다음 질문에 답해줘: '+question+'\n정의·조건·예외를 구분하고 근거 위치를 표시해줘. 근거가 부족하면 미확인이라고 해줘.\n\n'+after) if selected else None}

def read(sources,payload):
    sid=payload.get('id');exam=payload.get('exam','기말고사')
    s=sources.get(sid) if isinstance(sid,str) else None
    if not s or s.get('exam','중간고사')!=exam:raise ValueError('해당 시험에 등록된 근거가 없습니다.')
    offset=payload.get('offset',0)
    if type(offset) is not int or offset<0:raise ValueError('올바른 위치를 지정해 주세요.')
    text=s['text'][offset:offset+2400]
    return {'id':sid,'text':text,'location':s['location'],'offset':offset,'totalChars':len(s['text']),
            'nextOffset':offset+len(text) if offset+len(text)<len(s['text']) else None,'visualVerified':False}

