"""Download pristine, shallow sparse GitHub sources and lock their revisions.
No upstream install scripts or generated repository instructions are executed.
"""
import hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(args,cwd=None):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    if p.returncode:raise RuntimeError(p.stderr[-1000:])
    return p.stdout.strip()

def main():
    registry=json.loads((ROOT/'registry.json').read_text('utf-8'))
    source_root=ROOT/'upstream';source_root.mkdir(exist_ok=True)
    hooks=ROOT/'private/no-hooks';hooks.mkdir(parents=True,exist_ok=True)
    records=[]
    for source in registry['sources']:
        target=source_root/source['id'];url='https://github.com/'+source['repository']+'.git'
        git=['git','-c','core.longpaths=true','-c','core.hooksPath='+str(hooks)]
        if not target.exists():
            run(git+['clone','--filter=blob:none','--depth','1','--sparse',url,str(target)])
            run(git+['sparse-checkout','set',*source['sparse']],target)
        if run(git+['remote','get-url','origin'],target)!=url:raise RuntimeError('Unexpected upstream remote: '+source['id'])
        if run(git+['status','--porcelain','--untracked-files=no'],target):raise RuntimeError('Upstream copy has local changes; preserve and review them before relocking: '+source['id'])
        # Never reset/pull a user's existing source copy. A rerun only verifies it.
        commit=run(git+['rev-parse','HEAD'],target)
        paths=run(git+['ls-files'],target).splitlines()
        files=[]
        for rel in paths:
            path=target/rel
            if path.is_file() and not path.is_symlink():files.append({'path':rel,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        licenses=[x for x in files if Path(x['path']).name.lower().startswith(('license','copying','notice'))]
        if not licenses:raise RuntimeError('Upstream license missing: '+source['id'])
        records.append({'id':source['id'],'repository':source['repository'],'commit':commit,'mode':'shallow sparse source checkout','files':files,'licenses':licenses,'runtime_verified':False})
        print(json.dumps({'id':source['id'],'commit':commit,'files':len(files),'licenses':len(licenses)},ensure_ascii=False),flush=True)
    (ROOT/'upstream-lock.json').write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),'sources':records},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
