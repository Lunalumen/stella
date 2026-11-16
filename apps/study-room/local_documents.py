"""Owner-scoped local PDF/image preview and Windows OCR. No cloud calls."""
import base64
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT=Path(__file__).resolve().parent
GATE=threading.Semaphore(2)
MAX_BYTES=6*1024*1024

def run(command,timeout=30):
    try:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=True)
        return result.stdout.decode('utf-8-sig').strip()
    except (subprocess.SubprocessError,OSError) as exc:
        raise ValueError('로컬 문서 처리를 완료하지 못했습니다. 도구·언어·파일 상태를 확인해 주세요.') from exc

def owner_dir(private,owner):
    folder=Path(private)/'materials-files'/hashlib.sha256(owner.encode()).hexdigest()
    folder.mkdir(parents=True,exist_ok=True)
    return folder

def get_doc(private,owner,docid):
    if not isinstance(docid,str) or not re.fullmatch(r'[0-9a-f]{64}',docid):raise ValueError('문서 ID가 올바르지 않습니다.')
    folder=owner_dir(private,owner)/docid
    try:meta=json.loads((folder/'meta.json').read_text('utf-8'))
    except (OSError,ValueError):raise ValueError('이 브라우저의 임시 검토 문서가 없습니다.') from None
    return folder,meta

def upload(private,owner,payload):
    name=payload.get('name','')
    content=payload.get('content','')
    if not isinstance(name,str) or not isinstance(content,str) or len(content)>MAX_BYTES*4//3+4:
        raise ValueError('파일은 6MB 이하 PDF·PNG·JPEG로 선택해 주세요.')
    ext=Path(name).suffix.lower()
    if ext not in ('.pdf','.png','.jpg','.jpeg'):raise ValueError('PDF·PNG·JPEG만 지원합니다.')
    try:raw=base64.b64decode(content,validate=True)
    except ValueError:raise ValueError('파일 전송 형식이 올바르지 않습니다.') from None
    if not raw or len(raw)>MAX_BYTES:raise ValueError('파일은 6MB 이하여야 합니다.')
    if ext=='.pdf':
        from pypdf import PdfReader
        try:
            reader=PdfReader(io.BytesIO(raw))
            if reader.is_encrypted:raise ValueError()
            pages=len(reader.pages)
            if not 1<=pages<=500:raise ValueError()
        except Exception:raise ValueError('암호 없는 PDF, 최대 500쪽이 필요합니다.') from None
        stored_ext='.pdf'
    else:
        from PIL import Image
        try:
            with Image.open(io.BytesIO(raw)) as im:
                if im.width*im.height>12000000 or min(im.size)<1:raise ValueError()
                im.verify()
        except Exception:raise ValueError('읽을 수 있는 1,200만 화소 이하 이미지가 필요합니다.') from None
        pages=1;stored_ext=ext
    docid=hashlib.sha256(raw).hexdigest()
    folder=owner_dir(private,owner)/docid
    folder.mkdir(exist_ok=True)
    meta={'id':docid,'name':Path(name.replace('\\','/')).name[:150],'pages':pages,'extension':stored_ext,'registration':'임시 검토함 · 시험 출처/문제은행에 미등록'}
    file=folder/('original'+stored_ext)
    if not file.exists():file.write_bytes(raw)
    (folder/'meta.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    return meta

def validate_page(meta,page):
    if type(page) is not int or not 1<=page<=meta['pages']:raise ValueError('올바른 페이지 번호가 필요합니다.')

def preview(private,owner,docid,page):
    folder,meta=get_doc(private,owner,docid);validate_page(meta,page)
    output=folder/('page-'+str(page)+'.png')
    if output.exists():return output
    original=folder/('original'+meta['extension'])
    with GATE:
        if output.exists():return output
        if meta['extension']=='.pdf':
            binary=shutil.which('pdftoppm') or str(Path(sys.executable).parent.parent/'native/poppler/Library/bin/pdftoppm.exe')
            run([binary,'-f',str(page),'-l',str(page),'-singlefile','-scale-to','1800','-png',str(original),str(output.with_suffix(''))],45)
        else:
            from PIL import Image
            with Image.open(original) as im:
                im=im.convert('RGB');im.thumbnail((1800,1800));im.save(output,'PNG')
    if not output.exists():raise ValueError('페이지 이미지 생성에 실패했습니다.')
    return output

def page_text(private,owner,docid,page):
    folder,meta=get_doc(private,owner,docid);validate_page(meta,page)
    cache=folder/('text-'+str(page)+'.json')
    if cache.exists():return json.loads(cache.read_text('utf-8'))
    text=''
    if meta['extension']=='.pdf':
        from pypdf import PdfReader
        text=PdfReader(folder/('original'+meta['extension'])).pages[page-1].extract_text() or ''
    result={'page':page,'text':text[:12000],'truncated':len(text)>12000,'ocrNeeded':not bool(text.strip()),'visualVerified':False}
    cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    return result

def powershell():
    return str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe')


def tables(private,owner,payload):
    """Explicit page only. No OCR, model downloads, network calls or source registration."""
    from importlib.metadata import version,PackageNotFoundError
    docid=payload.get('id');page=payload.get('page',1)
    folder,meta=get_doc(private,owner,docid);validate_page(meta,page)
    if meta['extension']!='.pdf':raise ValueError('표 추출은 텍스트 PDF에서 사용할 수 있습니다. 사진은 OCR과 원본 대조를 이용하세요.')
    try:installed=version('pdfplumber')
    except PackageNotFoundError:raise ValueError('이 Python 환경에 선택 기능 pdfplumber가 준비되지 않았습니다.') from None
    worker=ROOT/'tools/pdf-tables.py'
    signature=hashlib.sha256(worker.read_bytes()+installed.encode()).hexdigest()[:16]
    cache=folder/f'tables-{page}-{signature}.json'
    with GATE:
        if cache.exists():return {**json.loads(cache.read_text('utf-8')),'cache':'reused'}
        result=json.loads(run([sys.executable,'-X','utf8',str(worker),str(folder/('original'+meta['extension'])),str(page)],30))
        cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    return {**result,'cache':'created'}

def capabilities():
    try:
        result=json.loads(run([powershell(),'-NoProfile','-File',str(ROOT/'tools/windows-ocr.ps1'),'-Capabilities'],15))
        return {'available':True,**result}
    except (ValueError,json.JSONDecodeError):return {'available':False,'languages':[],'engine':'Windows.Media.Ocr'}

def ocr(private,owner,payload):
    docid=payload.get('id');page=payload.get('page',1);language=payload.get('language','ko')
    if language not in ('ko','ko-KR','en','en-US'):raise ValueError('지원하는 OCR 언어를 선택해 주세요.')
    image=preview(private,owner,docid,page)
    engine_hash=hashlib.sha256((ROOT/'tools/windows-ocr.ps1').read_bytes()).hexdigest()[:12]
    cache=image.parent/('ocr-'+str(page)+'-'+language+'-'+engine_hash+'.json')
    if cache.exists():return {**json.loads(cache.read_text('utf-8')),'cache':'reused'}
    with GATE:
        if cache.exists():return {**json.loads(cache.read_text('utf-8')),'cache':'reused'}
        result=json.loads(run([powershell(),'-NoProfile','-File',str(ROOT/'tools/windows-ocr.ps1'),'-ImagePath',str(image.resolve()),'-Language',language],45))
        result.update(page=page,verified=False,warning='기계 인식 결과 · 숫자·수식·표는 원본과 대조하세요.')
        cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    return {**result,'cache':'created'}

