"""Optional local runtimes, isolated from bundled Python and existing connectors."""
import base64,hashlib,io,json,os,shutil,subprocess,sys,tarfile,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/'runtime'
NODE=Path(os.environ.get('NODE_EXE') or shutil.which('node') or 'node')
NODE_HOME=NODE.resolve().parent

def run(args,timeout=300):
    env=dict(os.environ);env['PATH']=str(NODE.parent)+os.pathsep+env.get('PATH','')
    p=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr[-1600:])
    return p.stdout.strip()

def npm_cli():
    bundled=NODE_HOME/'node_modules/npm/bin/npm-cli.js'
    if bundled.exists():return bundled
    target=RUNTIME/'npm';cli=target/'package/bin/npm-cli.js'
    if cli.exists():return cli
    with urllib.request.urlopen('https://registry.npmjs.org/npm/11.6.2',timeout=30) as r:meta=json.load(r)
    url=meta['dist']['tarball']
    if not url.startswith('https://registry.npmjs.org/'):raise ValueError('Unexpected npm distribution host')
    with urllib.request.urlopen(url,timeout=60) as r:raw=r.read()
    integrity=meta['dist']['integrity']
    if 'sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode()!=integrity:raise ValueError('npm integrity mismatch')
    target.mkdir(exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        archive.extractall(target,filter='data')
    return cli

def main():
    RUNTIME.mkdir(exist_ok=True)
    (ROOT/'private').mkdir(exist_ok=True)
    results={}
    try:
        url='https://github.com/github/github-mcp-server/releases/download/v2.0.3/github-mcp-server_Windows_x86_64.zip'
        expected='f0e1b9880a1b88730d1250d1c25cfee39617ec3e800a7a252f2279cd0c8394e0'
        target=RUNTIME/'github';target.mkdir(exist_ok=True);archive=target/'release.zip'
        if not archive.exists():
            with urllib.request.urlopen(url,timeout=60) as response:archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError('GitHub release digest mismatch')
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                dest=(target/info.filename).resolve()
                if not dest.is_relative_to(target.resolve()):raise ValueError('Archive path outside runtime')
                z.extract(info,target)
        exe=next(target.rglob('github-mcp-server.exe'))
        results['github']={'installed':True,'version':'2.0.3','release':url,'sha256':expected,'version_output':run([str(exe),'--version'])[:300]}
    except Exception as exc:results['github']={'installed':False,'error':str(exc)[:1600]}
    print(json.dumps({'github':results['github']},ensure_ascii=False),flush=True)
    try:
        target=RUNTIME/'node';target.mkdir(exist_ok=True)
        package={'name':'myeongwol-local-integrations','private':True,'version':'1.0.0','dependencies':{'@upstash/context7-mcp':'4.4.4','@notionhq/notion-mcp-server':'2.6.1'}}
        (target/'package.json').write_text(json.dumps(package,indent=2),encoding='utf-8')
        run([str(NODE),str(npm_cli()),'install','--prefix',str(target),'--ignore-scripts','--omit=dev','--no-audit','--no-fund','--registry','https://registry.npmjs.org'],300)
        for key,pkg in [('context7','@upstash/context7-mcp'),('notion','@notionhq/notion-mcp-server')]:
            path=target/'node_modules'/pkg;meta=json.loads((path/'package.json').read_text('utf-8'))
            results[key]={'installed':True,'package':pkg,'version':meta['version'],'entrypoints':meta.get('bin',{}),'auth_and_remote_access_verified':False}
    except Exception as exc:
        for key in ['context7','notion']:results.setdefault(key,{'installed':False,'error':str(exc)[:1600]})
    print(json.dumps({k:results[k] for k in ['context7','notion']},ensure_ascii=False),flush=True)
    try:
        target=RUNTIME/'workspace';python=target/'Scripts/python.exe'
        if not python.exists():run([sys.executable,'-m','venv',str(target)])
        query=[str(python),'-X','utf8','-c',"import importlib.metadata; print(importlib.metadata.version('workspace-mcp'))"]
        try:installed=run(query,30)
        except RuntimeError:installed=None
        if installed!='2.2.1':
            run([str(python),'-X','utf8','-m','pip','install','--disable-pip-version-check','--no-input','--only-binary=:all:','workspace-mcp==2.2.1'],300)
            installed=run(query,30)
        results['workspace']={'installed':True,'package':'workspace-mcp','version':installed,'isolated_environment':True,'auth_and_remote_access_verified':False}
    except Exception as exc:results['workspace']={'installed':False,'error':str(exc)[:1600]}
    print(json.dumps({'workspace':results['workspace']},ensure_ascii=False),flush=True)
    (ROOT/'private/runtime-install.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
