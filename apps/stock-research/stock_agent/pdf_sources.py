"""Page-preserving PDF reading and cached Poppler rendering; no OCR/model API."""
import json
import re
import shutil
import subprocess
from pathlib import Path
from .cache import digest

PDF_VERSION='3'

def inspect_pdf(store, path):
    path=Path(path)
    body=path.read_bytes()
    if not body.startswith(b'%PDF') or len(body)>100_000_000: raise ValueError('지원할 수 없는 PDF 형식 또는 크기')
    sha=digest(body)
    target=store.root/'extracted'/(sha+'.pdf.json')
    if target.exists():
        data=json.loads(target.read_text('utf-8'))
        if data.get('parser_version')==PDF_VERSION: return data
    try:
        from pypdf import PdfReader
        reader=PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(''): raise ValueError('암호화 PDF: 암호는 채팅·로그에 저장하지 않습니다. 읽을 수 있는 복사본이 필요합니다.')
        if len(reader.pages)>1000: raise ValueError('PDF 1000쪽 제한. 필요한 보고서 범위를 분리하세요.')
        pages=[]
        for n,page in enumerate(reader.pages,1):
            text=page.extract_text() or ''
            pages.append(dict(page=n,text=text,characters=len(text),extraction='pypdf_plain; table_layout_requires_visual_review',
                status='text_extracted_visual_unverified' if text.strip() else 'no_text_ocr_or_visual_required'))
    except ImportError: raise ValueError('PDF 읽기에는 pypdf가 필요합니다') from None
    (store.root/'raw'/(sha+'.bin')).write_bytes(body)
    data=dict(source_hash=sha,page_count=len(pages),pages=pages,parser_version=PDF_VERSION,visual_verified=False,ocr_performed=False)
    store.write('extracted',sha+'.pdf.json',data)
    store.stats['extractions']+=1
    return data

def document(store, sha):
    if not re.fullmatch('[0-9a-f]{64}',sha): raise ValueError('PDF 해시 오류')
    path=store.root/'extracted'/(sha+'.pdf.json')
    if not path.exists(): raise ValueError('먼저 pdf-inspect 또는 PDF import를 실행하세요')
    return json.loads(path.read_text('utf-8'))

def read_page(store, sha, page, offset=0, max_chars=3000):
    data=document(store,sha)
    if page<1 or page>data['page_count'] or offset<0 or not 1<=max_chars<=12000: raise ValueError('PDF 페이지·출력 범위 오류')
    p=data['pages'][page-1]; text=p['text'][offset:offset+max_chars]
    review=store.artifact(f'pdf-review:{sha}:{page}')
    return dict(source_hash=sha,page=page,text=text,offset=offset,total_characters=len(p['text']),truncated=offset>0 or offset+len(text)<len(p['text']),status=p['status'],visual_review=review,ocr_performed=False)

def search(store,sha,query,limit=3,max_chars=1200):
    if not query.strip() or not 1<=limit<=10 or not 1<=max_chars<=4000: raise ValueError('PDF 검색 범위 오류')
    terms=re.findall(r'[\w-]+',query.casefold()); hits=[]
    for page in document(store,sha)['pages']:
        lower=page['text'].casefold(); score=sum(lower.count(t) for t in terms)
        if not score: continue
        start=max(0,min(lower.find(t) for t in terms if t in lower)-150)
        result=read_page(store,sha,page['page'],start,max_chars)
        hits.append(dict(result,score=score))
    return dict(hits=sorted(hits,key=lambda x:-x['score'])[:limit],matched_pages=len(hits),model_calls=0)

def render_page(store,sha,page):
    data=document(store,sha)
    if not 1<=page<=data['page_count']: raise ValueError('PDF 페이지 범위 오류')
    renderer=shutil.which('pdftoppm')
    if not renderer: raise ValueError('PDF 시각 확인에는 Poppler pdftoppm이 필요합니다')
    folder=store.root/'pdf-pages';folder.mkdir(exist_ok=True)
    prefix=folder/f'{sha}-p{page}-1800';png=prefix.with_suffix('.png')
    reused=png.exists()
    if not reused:
        r=subprocess.run([renderer,'-f',str(page),'-l',str(page),'-singlefile','-scale-to','1800','-png',str(store.root/'raw'/(sha+'.bin')),str(prefix)],capture_output=True,timeout=40)
        if r.returncode or not png.exists(): raise ValueError('PDF 페이지 렌더링 실패')
    return dict(page=page,image=png.resolve().as_posix(),cached=reused,image_hash=digest(png.read_bytes()),status='rendered_not_reviewed',model_calls=0)

def record_review(store,sha,page,notes):
    result=render_page(store,sha,page)
    if not notes.strip(): raise ValueError('직접 확인한 표·단위·축·주석과 미확인 사항을 적으세요')
    review=dict(page=page,image_hash=result['image_hash'],notes=notes,verification='agent-reported visual inspection; not independently proven')
    store.artifact(f'pdf-review:{sha}:{page}',review)
    return review
