"""Known source -> existing cache -> bounded read/search, without discovery or AI calls."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROUTES={'.pdf':'references/pdf/READ.md','.pptx':'references/ppt/READ.md',
        '.docx':'references/document/READ.md','.txt':'references/document/READ.md',
        '.md':'references/document/READ.md','.json':'references/document/READ.md'}

def load_cache():
    path=Path(__file__).resolve().parents[2]/'study-cache/scripts/study_cache.py'
    spec=importlib.util.spec_from_file_location('stella_existing_cache',path)
    cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)
    return cache

def perform(cache,args):
    db=cache.connect(args.db)
    try:
        status='existing_source'
        if args.file:
            if args.file.suffix.lower() not in ROUTES:raise ValueError('Unsupported format')
            source=cache.ingest(db,SimpleNamespace(file=str(args.file),course=args.course,remote_id=args.remote_id,revision=args.revision))
            source_id=source['source_id'];status=source['status']
        else:source_id=args.source_id
        record=db.execute('SELECT * FROM sources WHERE id=? AND course=?',(source_id,args.course)).fetchone()
        if not record:raise ValueError('Source not found in the specified course; no broad search performed')
        route=ROUTES.get(Path(record['path']).suffix.lower())
        if args.query is not None:
            result=cache.search(db,SimpleNamespace(query=args.query,course=args.course,source_id=source_id,
                limit=args.limit,max_chars=args.max_chars,max_total_chars=args.max_total_chars,context_sections=args.context_sections))
        else:
            result=cache.read(db,SimpleNamespace(source_id=source_id,section=args.section,offset=args.offset,max_chars=args.max_chars))
        return {'source_id':source_id,'cache':status,'route':route,'scope':'specified_source','result':result}
    finally:db.close()

def main():
    cache=load_cache()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('file',nargs='?',type=Path)
    p.add_argument('--source-id')
    p.add_argument('--db',required=True,type=Path)
    p.add_argument('--course',required=True)
    target=p.add_mutually_exclusive_group(required=True)
    target.add_argument('--query');target.add_argument('--section',type=cache.positive)
    p.add_argument('--limit',type=cache.positive,default=3)
    p.add_argument('--max-chars',type=cache.positive,default=1200)
    p.add_argument('--max-total-chars',type=cache.positive,default=3600)
    p.add_argument('--context-sections',type=int,choices=range(3),default=0)
    p.add_argument('--offset',type=int,default=0)
    p.add_argument('--remote-id',default='');p.add_argument('--revision',default='')
    a=p.parse_args()
    if bool(a.file)==bool(a.source_id):p.error('Provide exactly one file or --source-id')
    if a.offset<0:p.error('Offset must not be negative')
    if not a.file and (a.remote_id or a.revision):p.error('Remote registration metadata requires a file')
    print(json.dumps(perform(cache,a),ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);sys.exit(1)
