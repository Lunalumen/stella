"""Small local integration router. Connected plugin calls remain in the AI host."""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read(path,default=None):
    return json.loads(path.read_text('utf-8')) if path.exists() else default

def choose(text):
    terms=[('stock',r'주식|상장|기업.?분석|실적|공시|SEC|DART|KR:\d{6}|US:[A-Z]+'),
           ('github',r'github|깃허브|저장소|커밋|pull request'),
           ('workspace',r'google|구글|drive|드라이브|gmail|메일|캘린더|스프레드시트'),
           ('notion',r'notion|노션'),('context7',r'context7|개발.?문서|라이브러리|SDK'),
           ('firecrawl',r'https?://|firecrawl|웹.?수집|웹.?본문')]
    for mode,pattern in terms:
        if re.search(pattern,text,re.I):return mode
    return None

def route(text,mode=None):
    config=read(ROOT/'registry.json');mode=mode or choose(text)
    if mode not in [s['id'] for s in config['sources']]+['stock']:raise ValueError('연결 대상을 지정해 주세요: github/workspace/firecrawl/context7/notion/stock')
    result={'route':mode,'request':text,'reference':str(ROOT/'routes'/f'{mode}.md'),'execution':'현재 AI 대화가 이 분기의 도구 또는 모듈만 실행. 이 route 출력 자체는 외부 도구 실행이 아닙니다.','model_calls_by_router':0,'total_chat_tokens':None}
    if mode=='stock':
        root=(ROOT / config['stock']['root']).resolve();result.update(module=str(root),skill=str((ROOT/config['stock']['skill']).resolve()),github='https://github.com/'+config['stock']['github_repository']+'/blob/main/'+config['stock']['github_skill'],markets=config['stock']['markets'])
    else:
        source=next(s for s in config['sources'] if s['id']==mode)
        result.update(source='https://github.com/'+source['repository'],connector=source['connector'],local_source=str(ROOT/'upstream'/mode))
    return result

def status():
    config=read(ROOT/'registry.json');lock=read(ROOT/'upstream-lock.json',{'sources':[]})
    checks=read(ROOT/'private/connector-checks.json',{})
    runtime=read(ROOT/'private/runtime-checks.json',{})
    sources=[]
    for source in config['sources']:
        record=next((s for s in lock['sources'] if s['id']==source['id']),{})
        sources.append({'id':source['id'],'source_downloaded':bool(record),'commit':record.get('commit'),'local_runtime_check':runtime.get(source['id']),'connector_check':checks.get(source['id']),'verification_is_live':False})
    stock=(ROOT / config['stock']['root']).resolve()
    return {'sources':sources,'stock':{'module_present':(stock/'stock_agent/__main__.py').is_file(),'skill_present':(ROOT/config['stock']['skill']).resolve().is_file(),'github_skill':'https://github.com/'+config['stock']['github_repository']+'/blob/main/'+config['stock']['github_skill']},'docker_available':bool(shutil.which('docker')),'paid_model_api':False,'note':'기록된 연결 검증과 현재 인증 상태는 다릅니다. 작업 시 연결을 다시 확인합니다.'}

def stock_call(args):
    allowed={'status','resolve','request','complete','import','sync-symbols','pdf-inspect','pdf-search','pdf-read','pdf-render','pdf-reviewed'}
    if not args or args[0] not in allowed:raise ValueError('기존 stock_agent의 리서치 명령만 실행할 수 있습니다.')
    config=read(ROOT/'registry.json');root=(ROOT / config['stock']['root']).resolve()
    if not (root/'stock_agent/__main__.py').exists():raise ValueError('설정된 주식 모듈을 찾을 수 없습니다.')
    return subprocess.run([sys.executable,'-X','utf8','-m','stock_agent',*args],cwd=root,check=False).returncode

def main():
    p=argparse.ArgumentParser(description='명월 통합 도구: 필요한 분기만 선택. 주문·추가 모델 API 없음.')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    r=sub.add_parser('route');r.add_argument('request');r.add_argument('--mode',choices=['github','workspace','firecrawl','context7','notion','stock'])
    r=sub.add_parser('stock');r.add_argument('args',nargs=argparse.REMAINDER)
    args=p.parse_args()
    if args.command=='stock':return stock_call(args.args)
    result=status() if args.command=='status' else route(args.request,args.mode)
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);sys.exit(2)
