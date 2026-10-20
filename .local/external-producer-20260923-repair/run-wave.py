#!/usr/bin/env python3
"""Exactly one invocation per scenario class; preserve setup failures and exits."""
import json,os,subprocess,sys,time
from pathlib import Path
import dependencies
ROOT=Path(__file__).resolve().parent
for mode in ('normal','failure','cancel'):
    entry={'mode':mode,'started_ns':time.time_ns(),'argv':[sys.executable,str(ROOT/'run-scenario.py'),mode]}
    launch_files=dependencies.paths(ROOT)
    entry['launcher_dependencies_before']=dependencies.manifest(launch_files)
    with (ROOT/(mode+'-invocation.json')).open('x') as f:json.dump(entry,f,indent=2)
    with (ROOT/(mode+'-harness.log')).open('x') as log:
        try:
            result=subprocess.run(entry['argv'],stdout=log,stderr=log,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            entry['exit']=result.returncode
        except Exception as e:entry.update(exit=None,error=repr(e),classification='SETUP_FAILURE_NO_RETRY')
    entry['finished_ns']=time.time_ns()
    entry['launcher_dependencies_after']=dependencies.manifest(launch_files)
    entry['receipts']=[str(p) for p in ROOT.glob('real-omp-'+mode+'-*/receipt.json')]
    entry['classification']='SCENARIO_RECORDED' if entry['receipts'] else 'SETUP_FAILURE_NO_RETRY'
    with (ROOT/(mode+'-settlement.json')).open('x') as f:json.dump(entry,f,indent=2)
    print(json.dumps({'mode':mode,'exit':entry['exit'],'classification':entry['classification'],'receipts':entry['receipts']}),flush=True)
