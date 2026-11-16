import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .cache import Store
from .data import COMPANIES, resolve
from .engine import Research
from .providers import import_local

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description='명월 한국·미국 기업 리서치. 주문·유료 API 없음.')
    p.add_argument('--data-dir', type=Path, default=Path(os.getenv('STOCK_DATA_DIR', ROOT / 'private' / 'research')))
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('request'); r.add_argument('text'); r.add_argument('--refresh', action='store_true'); r.add_argument('--as-of'); r.add_argument('--target')
    r = sub.add_parser('resolve'); r.add_argument('company')
    r = sub.add_parser('complete'); r.add_argument('fingerprint'); r.add_argument('summary', type=Path)
    r = sub.add_parser('import'); r.add_argument('company'); r.add_argument('file', type=Path); r.add_argument('--kind', choices=['text','facts'], default='text'); r.add_argument('--url', required=True); r.add_argument('--document-id', default=''); r.add_argument('--revision', default=''); r.add_argument('--period', required=True); r.add_argument('--period-end', required=True)
    r = sub.add_parser('status')
    r = sub.add_parser('sync-symbols'); r.add_argument('--market', choices=['KR','US'], required=True); r.add_argument('--refresh', action='store_true')
    r = sub.add_parser('pdf-inspect'); r.add_argument('file',type=Path)
    r = sub.add_parser('pdf-read'); r.add_argument('hash'); r.add_argument('--page',type=int,required=True); r.add_argument('--offset',type=int,default=0); r.add_argument('--max-chars',type=int,default=3000)
    r = sub.add_parser('pdf-search'); r.add_argument('hash'); r.add_argument('query'); r.add_argument('--limit',type=int,default=3); r.add_argument('--max-chars',type=int,default=1200)
    r = sub.add_parser('pdf-render'); r.add_argument('hash'); r.add_argument('--page',type=int,required=True)
    r = sub.add_parser('pdf-reviewed'); r.add_argument('hash'); r.add_argument('--page',type=int,required=True); r.add_argument('--notes',required=True)
    args = p.parse_args()
    config_path = ROOT / 'config' / 'local.json'
    config = json.loads(config_path.read_text('utf-8-sig')) if config_path.exists() else {}
    registry = COMPANIES + config.get('companies', [])
    store = Store(args.data_dir)
    try:
        catalog = {c['id']:c for c in store.artifact('company-catalog') or []}
        catalog.update({c['id']:c for c in registry})
        registry = list(catalog.values())
        research = Research(store, registry)
        if args.command.startswith('pdf-'):
            from . import pdf_sources
            if args.command=='pdf-inspect':
                pdf=pdf_sources.inspect_pdf(store,args.file)
                result={k:v for k,v in pdf.items() if k!='pages'} | {'pages':[{'page':p['page'],'characters':p['characters'],'status':p['status']} for p in pdf['pages']]}
            elif args.command=='pdf-read': result=pdf_sources.read_page(store,args.hash,args.page,args.offset,args.max_chars)
            elif args.command=='pdf-search': result=pdf_sources.search(store,args.hash,args.query,args.limit,args.max_chars)
            elif args.command=='pdf-render': result=pdf_sources.render_page(store,args.hash,args.page)
            else: result=pdf_sources.record_review(store,args.hash,args.page,args.notes)
        elif args.command == 'resolve': result = resolve(args.company, registry)
        elif args.command == 'sync-symbols':
            from .catalog import sync
            result = sync(store,args.market,args.refresh)
        elif args.command == 'request': result = research.run(args.text, args.as_of, args.refresh, args.target)
        elif args.command == 'complete': result = research.complete(args.fingerprint, json.loads(args.summary.read_text('utf-8-sig')))
        elif args.command == 'import':
            company = resolve(args.company, registry)
            module = Path(config.get('study_cache_module', ROOT.parents[1] / 'skills' / 'sources' / 'study-cache' / 'scripts' / 'study_cache.py'))
            metadata = dict(company_id=company['id'], source_url=args.url, document_id=args.document_id,
                revision=args.revision, period=args.period, period_end=args.period_end,
                checked_at=datetime.now(timezone.utc).isoformat())
            if bool(args.document_id) != bool(args.revision): raise ValueError('원격 문서 ID와 revision을 함께 지정하세요')
            result = import_local(store, args.file.resolve(strict=True), args.kind, metadata, module)
        else:
            result = dict(mode='current_codex_session', paid_model_api=False, broker_connected=False,
                sec_user_agent_configured=bool(os.getenv('SEC_USER_AGENT')), dart_key_configured=bool(os.getenv('DART_API_KEY')),
                extra_model_calls=0, model_tokens='미측정', last_companies=store.artifact('last-companies'))
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    finally: store.close()

if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, OSError, KeyError) as e:
        # No traceback, process environment, headers, or secret-bearing request URLs.
        from .cache import safe_url
        message = str(e)
        for name in ('DART_API_KEY', 'OPENAI_API_KEY', 'SEC_USER_AGENT'):
            value = os.getenv(name)
            if value: message = message.replace(value, '[REDACTED]')
        print(json.dumps({'status':'needs-input-or-source', 'error':message}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
