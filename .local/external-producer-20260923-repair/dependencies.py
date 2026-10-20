"""Hash known executable/code dependencies; explicit dynamic-load coverage limit."""
import hashlib,os,shutil,sys,sysconfig
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def paths(workspace):
 files=set()
 for base in [REPO/'hermes/call-omp/scripts',REPO/'hermes/call-omp/templates',REPO/'hermes/call-omp/tests']:
  files.update(p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 files.update(ROOT.glob('*.py'))
 files.update(workspace.glob('*.py'))
 # Bind standard-library source, bytecode and extension modules, without site packages.
 for directory, dirs, names in os.walk(sysconfig.get_path('stdlib')):
  dirs[:]=[d for d in dirs if d not in ('site-packages','test','tests','idlelib','tkinter','turtledemo','ensurepip')]
  files.update(Path(directory)/n for n in names if n.endswith(('.py','.pyc','.so','.dylib','.zip')))
 for tool in ('omp','bash','sh','python3','jq','ps','sleep','git','env','sed','awk','date','stat','shasum','perl','dirname','cat','mkdir','chmod','mv','rm','grep','head','tail','wc','tr','kill','tee','cut','find','sort','uname','readlink','mktemp','touch','cp','basename','xargs','which'):
  p=shutil.which(tool)
  if p:files.add(Path(p))
 files.update(map(Path,[sys.executable,'/bin/bash','/bin/sh','/bin/ps','/bin/sleep','/usr/bin/env']))
 # Framework shared interpreter and Homebrew libraries (source-free binary inventory).
 prefix=Path(sys.base_prefix)
 for p in [prefix/'Python',prefix/'Python.framework/Versions/3.14/Python']:
  if p.is_file():files.add(p)
 return sorted(files,key=str)
def manifest(files):
 result={}
 for p in files:
  try:result[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size,'resolved':str(p.resolve())}
  except Exception as e:result[str(p)]={'unknown':type(e).__name__}
 return result
