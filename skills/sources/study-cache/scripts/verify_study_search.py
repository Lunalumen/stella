import importlib.util, json, tempfile, socket, os
from pathlib import Path
from types import SimpleNamespace as NS
from reportlab.pdfgen import canvas
root = Path(__file__).resolve().parent
def module(name, file):
    spec=importlib.util.spec_from_file_location(name,file)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
new=module('after',root/'study_cache.py')
for key in list(os.environ):
    if any(v in key.upper() for v in ('API_KEY','TOKEN','SECRET','CREDENTIAL')): os.environ.pop(key)
def deny(*a,**k): raise AssertionError('No network permitted')
socket.socket=deny
checks=[]
with tempfile.TemporaryDirectory(dir=root) as temp:
    p=Path(temp); db=new.connect(p/'cache.sqlite')
    def ingest(name,text,course='study'):
        f=p/name; f.write_text(text,encoding='utf-8')
        return new.ingest(db,NS(file=str(f),course=course,remote_id='',revision=''))
    ingest('spacing.txt','이진 탐색은 정렬된 배열의 탐색 범위를 절반씩 줄인다.')
    def query(mod,q,course='study',**kw):
        args=dict(query=q,course=course,limit=3,max_chars=1200,context_sections=0,max_total_chars=3600)
        args.update(kw); return mod.search(db,NS(**args))
    after=query(new,'이진탐색')
    assert after['hits']
    checks.append({'case':'Korean spacing','after_found':True})
    ingest('noise.txt','정렬 '*100,'rank')
    ingest('answer.txt','정렬 비교 기준은 비교 횟수와 이동 횟수다.','rank')
    after=query(new,'정렬 비교','rank')
    assert Path(after['hits'][0]['source_path']).name=='answer.txt'
    checks.append({'case':'multiple terms outrank repeated one term','after_top':'answer'})
    f=p/'pages.pdf'; c=canvas.Canvas(str(f))
    for text in ['BUDGET is 1200 USD.','Exception: interns are excluded.','Other information.']:
        c.drawString(40,800,text); c.showPage()
    c.save()
    pdf=new.ingest(db,NS(file=str(f),course='pdf',remote_id='',revision=''))
    out=query(new,'BUDGET','pdf',context_sections=1,max_total_chars=300)
    assert out['hits'][0]['section']==1
    assert 'interns' in out['hits'][0]['context'][0]['text']
    assert 'page 2' in out['hits'][0]['context'][0]['location']
    checks.append({'case':'neighbor page exception retained','passed':True})
    short=query(new,'BUDGET','pdf',context_sections=1,max_total_chars=5)
    assert short['returned_text_chars']==5 and short['hits'][0]['truncated'] and short['context_omitted_for_budget']
    checks.append({'case':'shared budget and omissions flagged','passed':True})
    assert not query(new,'이진탐색','rank')['hits']
    checks.append({'case':'course isolation','passed':True})
    again=new.ingest(db,NS(file=str(f),course='pdf',remote_id='',revision=''))
    assert again['status']=='unchanged'
    f.write_bytes(b'changed')
    assert not query(new,'BUDGET','pdf',context_sections=1)['hits']
    checks.append({'case':'cache reuse and stale exclusion','passed':True})
    assert not query(new,'절대없는단어')['hits']
    checks.append({'case':'no invented match','passed':True})
    db.close()
result={'checks':checks,'model_calls':0,'network_blocked':True,'api_keys_removed':True,'scope':'Synthetic Korean TXT and text PDF retrieval; not a real student answer or token benchmark'}
(root/'study-search-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))


