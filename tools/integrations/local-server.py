"""Explicit optional local MCP launch; existing hosted connectors remain default."""
import json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NODE=Path(os.environ.get('NODE_EXE') or shutil.which('node') or 'node')

def main():
    if len(sys.argv)!=2:raise ValueError('Choose github, workspace, context7, notion or firecrawl')
    id=sys.argv[1];env=dict(os.environ)
    env['WORKSPACE_MCP_CREDENTIALS_DIR']=str(ROOT/'private/google-credentials')
    env['WORKSPACE_MCP_LOG_DIR']=str(ROOT/'private/google-logs')
    env['OTEL_SDK_DISABLED']='true'
    if id=='github':
        if not env.get('GITHUB_PERSONAL_ACCESS_TOKEN'):raise ValueError('Local GitHub token not configured. Use the existing connected GitHub plugin.')
        cmd=[str(ROOT/'runtime/github/github-mcp-server.exe'),'stdio','--read-only','--toolsets','repos,issues,pull_requests','--content-window-size','3000']
    elif id=='context7':cmd=[str(NODE),str(ROOT/'runtime/node/node_modules/@upstash/context7-mcp/dist/index.js')]
    elif id=='notion':
        if not env.get('NOTION_TOKEN') and not env.get('OPENAPI_MCP_HEADERS'):raise ValueError('Local Notion credentials not configured. Use the existing connected Notion plugin.')
        cmd=[str(NODE),str(ROOT/'runtime/node/node_modules/@notionhq/notion-mcp-server/bin/cli.mjs')]
    elif id=='workspace':
        creds=ROOT/'private/google-credentials'
        configured=bool(env.get('GOOGLE_OAUTH_CLIENT_ID') and env.get('GOOGLE_OAUTH_CLIENT_SECRET'))
        if not configured and not (creds.exists() and any(creds.glob('*.json'))):raise ValueError('Local Google OAuth not configured. Use the existing connected Google plugins.')
        cmd=[str(ROOT/'runtime/workspace/Scripts/python.exe'),'-X','utf8','-m','main','--transport','stdio','--tools','drive','docs','sheets','slides','gmail','calendar','--tool-tier','core','--read-only']
    elif id=='firecrawl':
        raise ValueError('Firecrawl source is installed; a Docker service stack and release-specific .env setup are needed for self-hosting. The existing Firecrawl connector is the active route. See README.md.')
    else:raise ValueError('Unknown local server')
    return subprocess.run(cmd,env=env,cwd=ROOT,check=False).returncode

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError) as exc:
        print(json.dumps({'status':'needs-local-configuration','error':str(exc)}),file=sys.stderr);sys.exit(2)
