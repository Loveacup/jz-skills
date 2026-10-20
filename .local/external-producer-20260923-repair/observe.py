#!/usr/bin/env python3
"""Bounded metadata observer; never reads credentials or runtime configuration."""
import hashlib,json,os,stat,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def meta(p):
 p=Path(p)
 try:
  s=p.lstat();d={'path':str(p),'mode':oct(s.st_mode),'size':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino}
  if p.is_symlink():d['link']=os.readlink(p)
  return d
 except FileNotFoundError:return {'path':str(p),'missing':True}
 except Exception as e:return {'path':str(p),'unknown':type(e).__name__}
def cmd(a):
 r=subprocess.run(a,cwd=REPO,text=True,capture_output=True);return {'argv':a,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
def snapshot():
 home=Path.home()
 names=['.hermes','.hermes/skills','.hermes/skills/call-omp','.hermes/skills/cc-tmux','.hermes/profiles','.hermes/hermes-agent','.agents/call-omp','.agents/skills/call-omp','.agents/skills/cc-tmux','.claude/skills/call-omp','.claude/skills/cc-tmux','.omp','.omp/agent','.config/omp']
 return {'observed_ns':time.time_ns(),'metadata_only':[meta(home/n) for n in names],
 'prior_evidence_sha256':{str(p.relative_to(REPO)):sha(p) for p in sorted((REPO/'.local/external-producer-20260923').rglob('*')) if p.is_file()},
 'git_refs':cmd(['git','for-each-ref','--format=%(refname) %(objectname)']),
 'git_remote_config':cmd(['git','config','--get-regexp',r'^(remote\..*\.(url|pushurl|fetch)|push\..*)$']),
 'git_hook':{'metadata':meta('/Users/alexcai/code/jz-skills/.git/hooks/pre-commit'),'sha256':sha('/Users/alexcai/code/jz-skills/.git/hooks/pre-commit')},
 'blocked':{'credentials_provider':'not inspected: sensitive contents outside authorization; metadata on containing directories cannot prove no mutation',
 'Gateway_Kanban':'no authorized exact state paths or execution-host observer; unknown',
 'installed_skill_contents':'entry/path metadata only; contents/transitive target writes unknown',
 'OMP_implicit_startup':'no syscall or dynamic-load observer; runtime configuration/session contents not inspected',
 'remote_push':'local remote config/refs observed only; server push audit unknown',
 'history':'before/after local refs and commit parent bound; no global concurrent history observer'}}
if __name__=='__main__':
 import sys
 target=ROOT/sys.argv[1]
 with target.open('x') as f:json.dump(snapshot(),f,indent=2);f.write('\n')
