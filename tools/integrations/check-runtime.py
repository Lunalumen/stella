"""Check local process/stdio readiness, without invoking service tools or OAuth."""
import json,os,queue,shutil,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NODE=Path(os.environ.get('NODE_EXE') or shutil.which('node') or 'node')

def stdio(command,env=None,timeout=25):
    p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',errors='replace',env=env,cwd=ROOT)
    messages=queue.Queue()
    def reader():
        for line in p.stdout:
            try:messages.put(json.loads(line))
            except ValueError:pass
    threading.Thread(target=reader,daemon=True).start()
    def send(value):p.stdin.write(json.dumps(value)+'\n');p.stdin.flush()
    def response(id):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:r=messages.get(timeout=.25)
            except queue.Empty:
                if p.poll() is not None:raise ValueError('process exited before MCP handshake')
                continue
            if r.get('id')==id:
                if 'error' in r:raise ValueError('MCP rejected request')
                return r['result']
        raise TimeoutError('MCP handshake timed out')
    try:
        send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'myeongwol-local-check','version':'1.0.0'}}})
        init=response(1);send({'jsonrpc':'2.0','method':'notifications/initialized'})
        send({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}})
        tools=response(2)
        return {'stdio_initialized':True,'server':init.get('serverInfo'),'tool_count':len(tools.get('tools',[])),'tool_names':[t['name'] for t in tools.get('tools',[])],'service_tools_called':0,'authenticated_service_access_verified':False}
    finally:
        try:p.stdin.close();p.wait(timeout=3)
        except (OSError,subprocess.TimeoutExpired):p.kill();p.wait()

def main():
    commands={
        'context7':[str(NODE),str(ROOT/'runtime/node/node_modules/@upstash/context7-mcp/dist/index.js')],
        'notion':[str(NODE),str(ROOT/'runtime/node/node_modules/@notionhq/notion-mcp-server/bin/cli.mjs')],
        'workspace':[str(ROOT/'runtime/workspace/Scripts/python.exe'),'-X','utf8','-m','main','--transport','stdio','--tools','drive','--tool-tier','core','--read-only']
    }
    results={}
    for id,command in commands.items():
        env=dict(os.environ);env['PYTHONIOENCODING']='utf-8'
        env['WORKSPACE_MCP_CREDENTIALS_DIR']=str(ROOT/'private/google-credentials')
        env['WORKSPACE_MCP_LOG_DIR']=str(ROOT/'private/google-logs')
        env['DO_NOT_TRACK']='1';env['OTEL_SDK_DISABLED']='true'
        try:results[id]=stdio(command,env)
        except Exception as exc:results[id]={'stdio_initialized':False,'reason':str(exc),'service_tools_called':0}
        print(json.dumps({id:results[id]},ensure_ascii=False),flush=True)
    exe=ROOT/'runtime/github/github-mcp-server.exe'
    if exe.exists():
        version=subprocess.run([str(exe),'--version'],capture_output=True,text=True,encoding='utf-8',timeout=15)
        results['github']={'binary_started':version.returncode==0,'version':version.stdout.strip(),'stdio_initialized':False,'reason':'Local OAuth/PAT is not configured; existing GitHub connector is verified separately.'}
    results['firecrawl']={'source_prepared':True,'self_host_started':False,'reason':'Docker is not installed. Existing connected Firecrawl remains the working route.'}
    (ROOT/'private/runtime-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
