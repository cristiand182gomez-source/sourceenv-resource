"""Non-model scripted resolvability through the unchanged r3 execution core."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'cases-package/frozen_runtime'),str(ROOT/'cases-package')]
from critical_guards import require_unoptimized,ensure
require_unoptimized()
import argparse,hashlib,json,os,socket,time,platform,shutil,traceback
import offline,judge,oracle
from common import save
from interface import worker,CONTRACT
from coverage_policy import CoverageDispatcher
from checkpoint import PrefixCheckpoint
from scoring import grade_case
from availability import settle
from native_actions import encode_action,feedback_messages
from public_feedback import feedback_text
ORDER=['EH-API','SC-BALANCE','EC-MISSING','SH-FLAG','EH-RENDERER','SC-SORT','EC-SYMBOL','SH-FORMAT']
LIMITS={'applications':288,'probes':32,'workers':256,'offline_installs':20,'fresh_states':16,'checkpoint_copies':8,'machine_seconds':7200}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify():
 manifest=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_bytes())
 for row in manifest['files']:
  rel=Path(row['path']);ensure(not rel.is_absolute() and '..' not in rel.parts,'PACKAGE_PATH')
  p=ROOT/rel;ensure(p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],'PACKAGE_BYTES:'+row['path'])
 ensure(len({r['path'] for r in manifest['files']})==len(manifest['files']),'PACKAGE_DUPLICATE')
 actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name not in ['PACKAGE_MANIFEST.json','PACKAGE_MANIFEST.sha256']}
 ensure(actual=={r['path'] for r in manifest['files']},'PACKAGE_INVENTORY')
 provenance=json.loads((ROOT/'PROVENANCE.json').read_bytes())
 for row in provenance['files']:ensure(digest(ROOT/row['path'])==row['sha256'],'R3_CORE_CHANGED:'+row['path'])
 for row in provenance.get('adapted_tasks',[]):
  data=(ROOT/row['path']).read_bytes();comment,separator,original=data.partition(b'\n')
  ensure(separator and comment.startswith(b'# SourceEnv canary ') and digest(ROOT/row['path'])==row['distribution_sha256'] and
   hashlib.sha256(original).hexdigest()==row['original_r3_sha256'],'TASK_COMMENT_OR_CONTRACT_CHANGED:'+row['path'])
 sidecar=(ROOT/'PACKAGE_MANIFEST.sha256').read_text(encoding='utf-8').split()
 ensure(sidecar==[digest(ROOT/'PACKAGE_MANIFEST.json'),'PACKAGE_MANIFEST.json'],'MANIFEST_SIDECAR')
 ensure(CONTRACT['budget']['max_actions']==20 and CONTRACT['budget']['max_run_app_actions']==12 and CONTRACT['budget']['max_install_actions']==3,'R3_LIMITS')
 return digest(ROOT/'PACKAGE_MANIFEST.json')

def native_message(tool,args,index):
 return {'role':'assistant','content':None,'tool_calls':[{'id':'script-'+str(index),'type':'function','function':{'name':tool,'arguments':json.dumps(args,ensure_ascii=False)}}]}

def prepare_runtime(output,wheelhouse):
 """Relocate exact offline inputs only; public files stay unchanged."""
 wheelhouse=wheelhouse.resolve()
 hashes=json.loads((ROOT/'cases-package/frozen_runtime/wheel_sha256.json').read_bytes())
 for name,h in hashes.items():
  p=wheelhouse/name
  ensure(p.is_file() and not p.is_symlink() and digest(p)==h,'OFFLINE_WHEEL_REQUIRED:'+name)
 inputs=output/'inputs';inputs.mkdir()
 target=inputs/'cases-package';shutil.copytree(ROOT/'cases-package',target)
 wheels=target/'frozen_runtime/wheelhouse';wheels.mkdir(exist_ok=True)
 for name in hashes:shutil.copy2(wheelhouse/name,wheels/name)
 # Payload, policy, probe and launcher bytes are identical. Only immutable
 # evaluator input locations are relocated; candidates see the same mounts.
 offline.ROOT=target/'frozen_runtime';judge.ROOT=offline.ROOT
 for p in (ROOT/'cases-package').rglob('*'):
  if p.is_file():ensure(digest(p)==digest(target/p.relative_to(ROOT/'cases-package')),'RUNTIME_INPUT_COPY')
 save(output/'runtime_inputs.json',{'wheel_hashes':hashes,'inputs_relocated_only':True,
  'application_contract_unchanged':True,'model_calls':0,'applications':0})

def run_case(case,mode,out,cost):
 cid=case['case_id'];out.mkdir(parents=True,exist_ok=False)
 state=out/'state';records=[];cost['fresh_states']+=1
 initial=offline.prepare(state,ROOT/'cases-package/cases'/cid/'initial.py',case['initial_profile'])
 ensure(initial['source_files']=={'app.py':case['source_sha256']},'INITIAL_SOURCE')
 paths={n:out/n for n in ['home','tmp','cache']}
 for p in paths.values():p.mkdir()
 gate=judge.native_preflight(initial);save(out/'isolation.json',gate);ensure(gate['available'],'NATIVE_ISOLATION_BLOCKED')
 with socket.socket() as listener:
  listener.bind(('127.0.0.1',0));listener.listen()
  properties=worker(initial,paths,judge,'native_properties',{'parent_pid':os.getpid(),
   'pid_namespace':os.readlink('/proc/self/ns/pid'),'net_namespace':os.readlink('/proc/self/ns/net'),
   'listener_port':listener.getsockname()[1],'private_paths':[str(ROOT/'source'),str(out/'episode.json')]},records)
 ensure(properties['ok'] and properties['checks'] and all(properties['checks'].values()),'WRITABLE_ISOLATION_BLOCKED')
 gate['writable_properties_passed']=True
 d=CoverageDispatcher(state,paths,offline,judge,gate,records,cid,case=case,oracle=oracle,policy='FINISH-COVERAGE')
 baseline=grade_case(d,case,offline.policy(),oracle,out/'initial-score.json')
 ensure(baseline['checks']==case['initial_checks_expected'],'INITIAL_CONTRACT_CHANGED')
 cp=PrefixCheckpoint(out);d.before_finish=cp.capture
 report={'case_id':cid,'configuration':'SCRIPTED','control':mode,'execution_origin':'scripted_FC',
  'model_calls':0,'generated_tokens':0,'model_processes':0,'preflights_generative':0,
  'initial_score':baseline,'cleanup_performed':False,'conversation':{'origin':'SCRIPTED_NOT_MODEL','messages':[],'turns':[]}}
 d.started=time.monotonic();failure=None
 script=[]
 if mode=='reference':
  if case['category']=='environment':
   ensure(case['reference_profile'] in CONTRACT['allowed_profiles'],'REFERENCE_PROFILE_NOT_AGENT_SELECTABLE')
   ensure(case['reference_source_sha256']==case['source_sha256'],'ENVIRONMENT_REFERENCE_REQUIRES_SOURCE')
   script.append(('apply_profile',{'profile':case['reference_profile']}))
  else:
   p=ROOT/'cases-package/cases'/cid/'reference.py';ensure(digest(p)==case['reference_source_sha256'],'REFERENCE_SOURCE')
   script.append(('write_file',{'path':'app.py','content':p.read_text(encoding='utf-8')}))
  script.extend(('run_app',{'operation':op}) for op in offline.policy()['operations'])
 script.append(('finish',{'summary':'Scripted '+mode+' control.'}))
 try:
  for tool,args in script:
   if d.stopped:break
   msg=native_message(tool,args,d.actions+1);raw=encode_action(msg)
   response=d.dispatch(raw,tool_name=tool)
   report['conversation']['messages'].append(msg)
   report['conversation']['messages'].extend(feedback_messages(msg,response,feedback_text))
   ensure(response.get('ok') is True or response.get('error')=='PENDING_OPERATIONS','SCRIPT_ACTION_FAILED')
  # The noop policy is always-finish, not a new scripted stop rule. FC uses
  # its existing action budget; derived BASE ends at the first valid finish.
  while mode=='noop' and not d.stopped:
   msg=native_message('finish',{'summary':'Scripted noop control.'},d.actions+1)
   response=d.dispatch(encode_action(msg),tool_name='finish')
   report['conversation']['messages'].append(msg)
   report['conversation']['messages'].extend(feedback_messages(msg,response,feedback_text))
   ensure(response.get('error')=='PENDING_OPERATIONS','NOOP_POLICY_CHANGED')
  ensure(d.stopped,'SCRIPT_DID_NOT_REACH_TERMINAL')
 except Exception as exc:
  failure=str(exc);d.stopped=True;d.stop_reason='infrastructure_failure';report['error']=failure
 finally:
  if cp.record:
   cp.record.update(model_replies_received=0,generated_tokens_consumed=0)
   save(out/'derived-base/checkpoint.json',cp.record)
  report.update(events=d.events,actions=d.actions,run_app_attempts=d.runs,profile_change_attempts=d.installs,
   stop_reason=d.stop_reason,coverage_metrics=d.coverage_record(),records=records)
  save(out/'episode.partial.json',report)
  settle(report,d,cp,case,baseline,out,failure)
  report['elapsed_seconds']=time.monotonic()-d.started
  report['scored_before_cleanup']=True;save(out/'episode.json',report)
  cost['checkpoint_copies']+=bool(cp.record and cp.record.get('copied_state'))
 if failure:raise RuntimeError(failure)
 ensure(report['primary_availability']=='VALID' and report['derived_BASE']['primary_availability']=='VALID','SCRIPT_SCORE_UNAVAILABLE')
 expected=mode=='reference'
 ensure(report['final_task_pass'] is expected and report['derived_BASE']['final_task_pass'] is expected,'RESOLVABILITY_ENDPOINT')
 ensure(d.actions<=20 and d.runs<=12 and d.installs<=3,'EPISODE_BUDGET_EXCEEDED')
 if mode=='reference':
  ensure(d.actions==8 and d.runs==6 and d.stop_reason=='finish','REFERENCE_TRAJECTORY')
  ensure(not report['observed_behavior_loss_vs_initial'],'REFERENCE_BEHAVIOR_LOSS')
  ensure(report['coverage_metrics']['final_state_coverage_count']==6,'REFERENCE_COVERAGE')
 else:ensure(d.actions==20 and d.runs==0 and d.installs==0 and d.stop_reason=='action_budget','NOOP_TRAJECTORY')
 return {'fixture':cid,'control':mode,'repair_tool':script[0][0] if mode=='reference' else None,
  'reference_profile':case['reference_profile'] if case['category']=='environment' and mode=='reference' else None,
  'FC_endpoint':report['final_score']['status'],'BASE_endpoint':report['derived_BASE']['final_score']['status'],
  'FC_terminal':d.stop_reason,'BASE_terminal':report['derived_BASE']['stop_reason'],
  'actions':d.actions,'run_app_actions':d.runs,'install_actions':d.installs,
  'coverage':report['coverage_metrics']['final_state_coverage_count'],
  'operation_checks':report['operation_checks'],'losses':report['observed_behavior_loss_vs_initial'],
  'effective_source_changes':sum(e.get('effective_source_change') is True for e in d.events),
  'effective_environment_changes':sum(e.get('effective_environment_change') is True for e in d.events),
  'model_calls':0,'episode_sha256':digest(out/'episode.json'),'scored_before_cleanup':True,
  'state_identity':d.coverage.identity,'isolation_passed':True}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT.parent/'sourceenv-scripted-output')
 parser.add_argument('--wheelhouse',type=Path,help='External directory with the ten exact pinned offline wheels')
 parser.add_argument('--verify-only',action='store_true');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
 identity=verify()
 if args.verify_only:print(json.dumps({'integrity':'PASS','package_manifest_sha256':identity,'model_calls':0}));return
 ensure(sys.platform=='linux' and sys.flags.isolated and sys.flags.no_site and os.getuid()==os.geteuid()!=0,'TRUSTED_DEBIAN_UNPRIVILEGED_REQUIRED')
 output=args.output.resolve();ensure(output!=ROOT and not ROOT.is_relative_to(output) and not output.is_relative_to(ROOT),'OUTPUT_MUST_BE_OUTSIDE_PACKAGE')
 ensure(shutil.which('bwrap') is not None,'BUBBLEWRAP_REQUIRED')
 ensure(args.wheelhouse is not None,'Provide --wheelhouse with the ten pinned offline wheels; no download is performed')
 output.mkdir(parents=True,exist_ok=False)
 prepare_runtime(output,args.wheelhouse)
 if args.prepare_only:
  verify();print(json.dumps({'inputs_prepared':True,'model_calls':0,'applications':0,'probes':0,'workers':0}));return
 started=time.monotonic();cost={k:0 for k in LIMITS};cost.update(model_calls=0,generated_tokens=0,model_processes=0,tokenizer_calls=0)
 save(output/'preparation_budget.json',dict(LIMITS,model_calls=0,generated_tokens=0))
 cases=json.loads((ROOT/'source/cases.json').read_bytes());rows=[]
 original_capture=judge.capture;original_install=offline.apply_profile;ledger=[]
 def captured(argv,*args,**kwargs):
  kind='workers' if '/file_worker.py' in argv else 'probes' if '/probe.py' in argv else 'applications'
  ensure(cost[kind]<LIMITS[kind] and time.monotonic()-started<7200,'PREPARATION_CAPTURE_LIMIT')
  cost[kind]+=1;entry={'kind':kind,'started':True,'returned':False};ledger.append(entry)
  save(output/'capture_ledger.json',ledger)
  try:
   result=original_capture(argv,*args,**kwargs)
   entry.update(returned=True,error=result.get('error'),process_launched=result.get('process_launched'),exit_code=result.get('exit_code'))
   return result
  finally:save(output/'capture_ledger.json',ledger);save(output/'costs.json',cost)
 def installed(*args,**kwargs):
  ensure(cost['offline_installs']<20,'PREPARATION_INSTALL_LIMIT');cost['offline_installs']+=1
  save(output/'costs.json',cost);return original_install(*args,**kwargs)
 judge.capture=captured;offline.apply_profile=installed
 try:
  for cid in ORDER:
   ensure(not cases[cid]['healthy'],'DAMAGED_FIXTURES_ONLY')
   for mode in ['reference','noop']:
    ensure(time.monotonic()-started<7200,'PREPARATION_TIME_LIMIT')
    row=run_case(cases[cid],mode,output/cid/mode,cost);rows.append(row)
    cost['machine_seconds']=time.monotonic()-started
    ensure(all(cost[k]<=v for k,v in LIMITS.items()),'PREPARATION_LIMIT')
    save(output/'resolvability.json',rows);save(output/'costs.json',cost);print(json.dumps(row),flush=True)
  verify();save(output/'closure.json',{'status':'COMPLETED','model_calls':0,'cleanup_performed':False,
   'scripted_episodes':len(rows),'package_manifest_sha256':identity,'python_version':platform.python_version(),
   'bubblewrap_sha256':digest(Path(shutil.which('bwrap'))),'scored_before_cleanup':True})
 except BaseException as exc:
  cost['machine_seconds']=time.monotonic()-started;save(output/'costs.json',cost)
  save(output/'failure.json',{'error':str(exc),'traceback':traceback.format_exc(),'completed_rows':rows,'no_retry':True})
  raise
if __name__=='__main__':main()
