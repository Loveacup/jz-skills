#!/usr/bin/env python3
"""Readback of producer evidence, not independent W1 acceptance."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'hermes/call-omp/tests'))
import process_probe
from dependencies import sha

def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
revision=git('rev-parse','HEAD').decode().strip()
parent=git('log','-1','--format=%P').decode().strip()
assert revision=='3c0caa8bdcb9c6b89a066ed8a7a00adab708fd60'
assert parent=='aa44eecc4630e96c82f7688a44ec2e452b8fdfae'
assert git('diff','--name-only')==b'' and git('diff','--cached','--name-only')==b''
checks={'revision':revision,'parent':parent,'status':git('status','--porcelain').decode(),'scenarios':{},'commit_file_binding':{}}
for rel in git('ls-tree','-r','--name-only',revision,'--','hermes/call-omp/scripts','hermes/call-omp/templates','hermes/call-omp/tests/process_probe.py','hermes/call-omp/tests/test_process_probe.py').decode().splitlines():
 expected=hashlib.sha256(git('show',revision+':'+rel)).hexdigest()
 actual=sha(REPO/rel)
 checks['commit_file_binding'][rel]={'commit_sha256':expected,'disk_sha256':actual,'equal':expected==actual}
 assert expected==actual
for mode in ['normal','failure','cancel']:
 ps=list(ROOT.glob('real-omp-'+mode+'-*/receipt.json'));assert len(ps)==1
 p=ps[0];d=json.loads(p.read_text())
 assert d['candidate_commit']==revision and d['candidate_parent']==parent
 assert d['status']=='SCENARIO_ASSERTIONS_SATISFIED_PRODUCER_SCOPE'
 assert d['dependency_unexpected_changes']==[]
 manifest=d['dependencies_before'];after=d['dependencies_after']
 for rel,binding in checks['commit_file_binding'].items():
  key=str(REPO/rel)
  if key in manifest:assert manifest[key]['sha256']==binding['commit_sha256']==after[key]['sha256']
 assert str(REPO/'hermes/call-omp/templates/execute-prompt-template.md') in manifest
 assert str(ROOT/'run-scenario.py') in manifest
 for key,value in d['native_evidence_sha256'].items():assert sha(key)==value
 entry={'receipt':str(p),'sha256':sha(p),'worker_exit':d['resource_receipt']['worker_exit_code'],
        'accept_exit':d['accept_exit_code'],'dependency_count':len(manifest),'changes':d['dependency_changes'],
        'attempt_id':d['attempt_id'],'launch_fingerprint':d['launch_fingerprint'],
        'native_file_hashes_verified':len(d['native_evidence_sha256'])}
 if mode=='normal':
  assert entry['worker_exit']==0 and entry['accept_exit']==0
  assert all(c['actual']==c['expected'] for c in d['consumer_cases'])
  assert d['consumer_executed_artifact_before_sha256']==d['consumer_executed_artifact_after_sha256']==d['artifact_sha256']
 elif mode=='failure':assert entry['worker_exit']!=0 and entry['accept_exit']!=0
 else:
  native=d['pid_store_before_stop'];worker=d['owned_before_stop']['omp_worker']['identity']
  assert (worker['pid'],worker['ppid'],worker['pgid'],worker['sid'])==(native['pid'],native['supervisor_pid'],native['pgid'],native['session_id'])
  assert all(x['state']=='dead' and x['exit_code']==1 and x['stdout']=='' and x['stderr']=='' for x in d['owned_after_stop'].values())
  assert d['unrelated_after_stop']['identity']==d['unrelated_before_stop']['identity']
  assert d['unrelated_after_stop']['state']=='alive'
  assert d['resource_receipt']['cleanup_confirmed'] and entry['accept_exit']!=0
  entry['owned_identity_consistency']={k:{field:v['identity'][field] for field in ('pid','ppid','pgid','sid','start_time')} for k,v in d['owned_before_stop'].items()}
  entry['full_command_lengths']={k:len(v['identity']['command']) for k,v in d['owned_before_stop'].items()}
  entry['post_harness_sentinel_probe']=process_probe.probe(d['unrelated_after_stop']['pid'])
 checks['scenarios'][mode]=entry
before=json.loads((ROOT/'watched-before.json').read_text());after=json.loads((ROOT/'watched-after.json').read_text())
checks['prior_evidence_unchanged']=before['prior_evidence_sha256']==after['prior_evidence_sha256']
assert checks['prior_evidence_unchanged']
checks['watched_metadata_deltas']=[{'before':a,'after':b} for a,b in zip(before['metadata_only'],after['metadata_only']) if a!=b]
checks['git_remote_config_equal']=before['git_remote_config']==after['git_remote_config']
checks['hook_equal']=before['git_hook']==after['git_hook']
checks['refs_removed']=sorted(set(before['git_refs']['stdout'].splitlines())-set(after['git_refs']['stdout'].splitlines()))
checks['refs_added']=sorted(set(after['git_refs']['stdout'].splitlines())-set(before['git_refs']['stdout'].splitlines()))
checks['producer_checks']='OBSERVED_ASSERTIONS_SATISFIED; not final W1 verdict'
(ROOT/'producer-readback.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps({'scenarios':{m:{'worker_exit':x['worker_exit'],'accept_exit':x['accept_exit']} for m,x in checks['scenarios'].items()},'prior_evidence_unchanged':checks['prior_evidence_unchanged'],'watched_metadata_deltas':checks['watched_metadata_deltas'],'refs_added':checks['refs_added'],'refs_removed':checks['refs_removed']},indent=2))
