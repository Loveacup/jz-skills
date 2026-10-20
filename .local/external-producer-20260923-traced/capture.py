#!/usr/bin/env python3
"""Read-only bounded snapshot. Sensitive runtime files: lstat only, never open."""
import datetime, hashlib, json, os, pathlib, stat, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent.parent
CONTRACT = pathlib.Path('/Users/alexcai/code/local-agent-governance/.local/hermes-deployment-20260922/remediation-cycle3/call-omp-trace-contract.json')
C = json.loads(CONTRACT.read_text())
BASE = pathlib.Path(C['coordinator_baseline']).expanduser()
B = json.loads(BASE.read_text())
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def meta(path, content=False):
    p = pathlib.Path(path).expanduser()
    try: s=p.lstat()
    except FileNotFoundError: return {'exists':False}
    except OSError as e: return {'state':'unknown','error':type(e).__name__}
    d=dict(exists=True,device=s.st_dev,inode=s.st_ino,mode=s.st_mode,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,
           kind='symlink' if p.is_symlink() else 'dir' if p.is_dir() else 'file')
    if p.is_symlink(): d['link_target']=os.readlink(p)
    elif content and stat.S_ISREG(s.st_mode): d['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    return d
def tree(path, content=False):
    p=pathlib.Path(path).expanduser()
    result={'root':str(p),'metadata':meta(p),'files':{}}
    if p.is_dir():
        for d, dirs, files in os.walk(p,followlinks=False):
            for n in sorted(dirs+files):
                f=pathlib.Path(d)/n
                result['files'][str(f.relative_to(p))]=meta(f,content)
    return result
def run(argv):
    started=now()
    try:
        r=subprocess.run(argv,capture_output=True,text=True,timeout=15)
        d=dict(argv=argv,started_at=started,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except Exception as e: d=dict(argv=argv,started_at=started,state='unknown',error=str(e))
    with (ROOT/'commands.jsonl').open('a') as f:f.write(json.dumps(d)+'\n')
    return d
def snapshot(label):
    gd=pathlib.Path('/Users/alexcai/code/jz-skills/.git/worktrees/call-omp-independent-candidate')
    common=gd.parent.parent
    head=(gd/'HEAD').read_text().strip();ref=head.removeprefix('ref: ')
    commit=(common/ref).read_text().strip() if head.startswith('ref: ') and (common/ref).exists() else head
    omp=pathlib.Path('/opt/homebrew/bin/omp')
    s=dict(captured_at=now(),git_identity=dict(git_dir=str(gd),head_text=head,commit=commit,ref=ref),
           repository=tree(REPO/'hermes/call-omp',True),omp_launcher=dict(path=str(omp),metadata=meta(omp),resolved_path=str(omp.resolve()),resolved_metadata=meta(omp.resolve(),True)),
           contract=meta(CONTRACT,True),coordinator_baseline=meta(BASE,True))
    s['watched_surfaces']={}
    for name,old in B['watched_surfaces'].items():
        if name.startswith('~/.hermes/'):
            s['watched_surfaces'][name]=meta(name,content=name.endswith('SOUL.md') or name.endswith('gateway_state.json'))
    prior=pathlib.Path(C['prior_review']).expanduser()
    s['watched_surfaces']['prior_call_review']=meta(prior,True)
    s['prior_evidence']=tree(prior.parent,True)
    # Runtime config/MCP/extensions may embed credentials: metadata only, no hashes.
    s['omp_runtime_metadata_only']={str(p):tree(p) if p.is_dir() else meta(p) for p in [pathlib.Path.home()/'.omp',pathlib.Path.home()/'.config/omp',REPO/'.omp']}
    s['git_inputs']={str(p):meta(p,True) for p in [common/'config',gd/'config.worktree',pathlib.Path.home()/'.gitconfig',pathlib.Path.home()/'.config/git/config',pathlib.Path('/etc/gitconfig'),common/'info/attributes',pathlib.Path.home()/'.config/git/attributes']}
    s['attributes']={str(p):meta(p,True) for p in REPO.rglob('.gitattributes') if '.local' not in p.parts}
    s['hooks']=tree(common/'hooks',True)
    # Executable command names only, not argv or environments of unrelated processes.
    s['process_identity']=run(['/bin/ps','-axo','pid=,ppid=,pgid=,sid=,lstart=,comm='])
    (ROOT/(label+'.json')).write_text(json.dumps(s,indent=2)+'\n')
    return s
if __name__=='__main__':
    os.umask(0o077)
    if sys.argv[1]=='probe':
        for a in [['/usr/bin/id','-u'],['/usr/bin/csrutil','status'],['/usr/sbin/dtrace','-l','-n','syscall::open*:entry'],['/usr/bin/fs_usage','-w','-f','filesys','-t','1'],['/usr/bin/sw_vers'],['/usr/bin/uname','-a']]:run(a)
    else:
        s=snapshot(sys.argv[1]); print(json.dumps({'label':sys.argv[1],'captured_at':s['captured_at'],'head':s['git_identity']['commit']}))
