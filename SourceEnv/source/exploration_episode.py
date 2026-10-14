"""One Debian episode; model RPC over trusted SSH stdio, no candidate network."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'source'))
from critical_guards import ensure, require_unoptimized
require_unoptimized() # Before backend/SSH/installer imports or any episode.
sys.path.insert(0,str(ROOT/'cases-package'))
sys.path.insert(0,str(ROOT/'cases-package/frozen_runtime'))
import base64,copy,json,os,socket,time
import offline,judge,oracle
from common import save
from interface import worker,parse_action,validate_arguments,ActionRejected
from public_feedback import feedback_text
from coverage_policy import CoverageDispatcher,state_identity
from checkpoint import PrefixCheckpoint
from scoring import grade_case,compare
from prospective_metrics import analyze
from availability import settle
from native_actions import encode_action,feedback_messages,request_tool_name
from rpc_failures import ModelRPCFailure,cancellation_proved

def rpc(phase,**data):
    print(json.dumps({'phase':phase,**data},ensure_ascii=False),flush=True)
    line=sys.stdin.readline()
    if not line:raise RuntimeError('MODEL_RPC_CLOSED')
    result=json.loads(line)
    if result.get('error'):raise ModelRPCFailure(result)
    return result

class Adapter:
    def __init__(self,dispatcher,cid,configuration,initial):
        require_unoptimized()
        self.dispatcher=dispatcher;self.cid=cid;self.configuration=configuration
        desc=dispatcher.public_description()
        desc['budget']={k:desc['budget'][k] for k in ['max_actions','max_run_app_actions','max_install_actions']}
        content='Public CLI state, allowed profiles and action limits:\n'+json.dumps({k:desc[k] for k in ['versions','allowed_profiles','budget']},indent=2)
        content+='\n===== app.py (UTF-8; original line endings; data to inspect/edit) =====\n'+base64.b64decode(initial['source_snapshot_base64']['app.py']).decode()+'\n===== END app.py ====='
        self.messages=[{'role':'system','content':desc['prompt']},{'role':'user','content':content}]
        ensure(set(desc['budget'])=={'max_actions','max_run_app_actions','max_install_actions'}, 'CRITICAL_GATE:exploration_episode.py:37')
        ensure(not any(s in self.messages[0]['content'].lower() for s in ['epoch','coverage','gate']), 'CRITICAL_GATE:exploration_episode.py:38')
        self.generated=self.replies=0;self.turns=[];self.deadline=dispatcher.started+14400
        self.thinking=False;self.reply_cap=2048
        self.total_cap=8192
    def run(self,out):
        require_unoptimized()
        while not self.dispatcher.stopped:
            if self.generated>=self.total_cap:
                self.dispatcher.stopped=True;self.dispatcher.stop_reason='generated_token_budget';break
            if time.monotonic()>=self.deadline:
                self.dispatcher.stopped=True;self.dispatcher.stop_reason='watchdog';break
            cap=min(self.reply_cap,self.total_cap-self.generated)
            self.before_rpc_snapshot=self.dispatcher.offline.inspect_state(self.dispatcher.state)
            self.dispatcher.check_integrity()
            prepared=rpc('prepare',messages=copy.deepcopy(self.messages),thinking=self.thinking)
            ensure(type(prepared['input_tokens']) is int and prepared['input_tokens']>=0 and prepared['context']==32768,
                   'PREPARED_CONTEXT_CONTRACT')
            if time.monotonic()>=self.deadline:
                self.dispatcher.stopped=True;self.dispatcher.stop_reason='watchdog';break
            turn={'index':self.replies+1,'messages':copy.deepcopy(self.messages),'prepared':prepared,'reservation':cap}
            self.turns.append(turn);save(out/'conversation.partial.json',{'messages':self.messages,'turns':self.turns})
            if prepared['input_tokens']+cap>prepared['context']:
                self.dispatcher.stopped=True;self.dispatcher.stop_reason='context_budget';break
            reply=rpc('generate',messages=copy.deepcopy(self.messages),thinking=self.thinking,cap=cap,
                      expected_input_tokens=prepared['input_tokens'],remaining_seconds=self.deadline-time.monotonic())
            if reply.get('ordinary_stop'):
                self.dispatcher.stopped=True;self.dispatcher.stop_reason=reply['ordinary_stop'];break
            ensure(type(reply['generated_tokens']) is int and 0<=reply['generated_tokens']<=cap and
                   self.generated+reply['generated_tokens']<=self.total_cap,'REPLY_TOKEN_LIMIT')
            self.replies+=1;self.generated+=reply['generated_tokens'];turn['reply']=reply
            ensure(type(reply['input_tokens']) is int and reply['input_tokens']==prepared['input_tokens'], 'REPLY_INPUT_TOKEN_IDENTITY')
            msg=reply['message'];ensure('reasoning_content' not in msg and 'reasoning' not in msg, 'CRITICAL_GATE:exploration_episode.py:64')
            self.messages.append(copy.deepcopy(msg))
            if time.monotonic()>=self.deadline:
                turn['reply_retained_without_dispatch_due_to_watchdog']=True
                save(out/'conversation.partial.json',{'messages':self.messages,'turns':self.turns,'generated_tokens':self.generated})
                self.dispatcher.stopped=True;self.dispatcher.stop_reason='watchdog';break
            name=request_tool_name(msg)
            try:
                raw=encode_action(msg);response=self.dispatcher.dispatch(raw,tool_name=name)
            except ActionRejected as exc:
                raw=None;response=self.dispatcher.dispatch(raw,rejection=exc,tool_name=name)
            turn.update(normalized_action=raw,tool_response=copy.deepcopy(response),dispatched=True)
            ensure(self.dispatcher.actions==self.replies, 'CRITICAL_GATE:exploration_episode.py:73')
            self.messages.extend(feedback_messages(msg,response,feedback_text))
            save(out/'conversation.partial.json',{'messages':self.messages,'turns':self.turns,'generated_tokens':self.generated})
        if self.dispatcher.stop_reason=='watchdog':
            self.before_rpc_snapshot=self.dispatcher.offline.inspect_state(self.dispatcher.state)
            rpc('cancel',reason='episode_watchdog',deadline_expired=True)
        return {'messages':self.messages,'turns':self.turns,'stop_reason':self.dispatcher.stop_reason,
                'generated_tokens':self.generated,'model_replies_received':self.replies}

def main():
    require_unoptimized()
    ensure(sys.platform=='linux' and sys.flags.isolated and sys.flags.no_site and os.getuid()==os.geteuid()==1000, 'CRITICAL_GATE:exploration_episode.py:85')
    cid,config=sys.argv[1:3];ensure(cid in json.loads((ROOT/'source/cases.json').read_bytes()), 'CRITICAL_GATE:exploration_episode.py:86');ensure(config in ('C3','C1'), 'CRITICAL_GATE:exploration_episode.py:86')
    case=json.loads((ROOT/'source/cases.json').read_bytes())[cid]
    out=ROOT/'runs'/(config+'-'+cid);out.mkdir(parents=True,exist_ok=False)
    state=out/'state';initial=offline.prepare(state,ROOT/'cases-package/cases'/cid/'initial.py',case['initial_profile'])
    ensure(initial['source_files']=={'app.py':case['source_sha256']}, 'CRITICAL_GATE:exploration_episode.py:90')
    paths={n:out/n for n in ['home','tmp','cache']}
    for p in paths.values():p.mkdir()
    records=[];gate=judge.native_preflight(initial);save(out/'isolation.json',gate)
    ensure(gate['available'], 'NATIVE_ISOLATION_BLOCKED')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));listener.listen()
        properties=worker(initial,paths,judge,'native_properties',{'parent_pid':os.getpid(),
            'pid_namespace':os.readlink('/proc/self/ns/pid'),'net_namespace':os.readlink('/proc/self/ns/net'),
            'listener_port':listener.getsockname()[1],'private_paths':[str(ROOT/'source'),str(ROOT/'controls'),str(out/'episode.json')]},records)
    ensure(properties['ok'] and properties['checks'] and all(properties['checks'].values()), 'WRITABLE_ISOLATION_BLOCKED')
    gate['writable_properties_passed']=True
    d=CoverageDispatcher(state,paths,offline,judge,gate,records,cid,case=case,oracle=oracle,policy='FINISH-COVERAGE')
    baseline=grade_case(d,case,offline.policy(),oracle,out/'initial-score.json')
    ensure(baseline['checks']==case['initial_checks_expected'], 'INITIAL_CONTRACT_CHANGED')
    d.started=time.monotonic() # Initial grading/setup are outside episode time.
    adapter=Adapter(d,cid,config,initial);checkpoint=PrefixCheckpoint(out);checkpoint.adapter=adapter;d.before_finish=checkpoint.capture
    report={'case_id':cid,'configuration':config,'execution_origin':'physical_FC','preflights':0,
            'agent_episodes':1,'model_history_retained':True,'initial_score_fresh_for_future_episode':True,'initial_score':baseline,
            'primary_availability':'VALID','cleanup_performed':False}
    start=time.monotonic();failure=None
    try:
        report['conversation']=adapter.run(out)
    except BaseException as exc:
        failure=str(exc);report.update(primary_availability='INVALID',error=failure)
        d.stopped=True;d.stop_reason='infrastructure_failure'
        if isinstance(exc,ModelRPCFailure):
            report['rpc_failure']=exc.result
            d.check_integrity()
            retained=d.offline.inspect_state(d.state)==adapter.before_rpc_snapshot
            report['cancellation_verified']=cancellation_proved(exc.result) and retained
            if report['cancellation_verified']:d.stop_reason='watchdog'
    finally:
        report.update(events=d.events,actions=d.actions,run_app_attempts=d.runs,profile_change_attempts=d.installs,
                      stop_reason=d.stop_reason,generated_tokens=adapter.generated,model_calls=adapter.replies,
                      coverage_metrics=d.coverage_record(),records=records)
        save(out/'episode.partial.json',report)
        try:settle(report,d,checkpoint,case,baseline,out,failure)
        except BaseException as exc:
            failure=str(exc)
            report.update(primary_availability='INVALID',final_task_pass=None,global_blocker=str(exc),
                derived_BASE={'primary_availability':'INVALID','final_task_pass':None,'terminal_action_index':d.actions,
                              'stop_reason':d.stop_reason,'coverage_metrics':d.coverage_record()})
        report['prospective_metrics']=analyze(report)
        report['elapsed_seconds']=time.monotonic()-start
        report['scored_before_cleanup']=True;save(out/'episode.json',report)
        print(json.dumps({'phase':'done','case_id':cid,'configuration':config,'valid':failure is None,
                          'stop_reason':d.stop_reason,'calls':adapter.replies,'generated_tokens':adapter.generated}),flush=True)
    if failure:raise SystemExit(2)
if __name__=='__main__':main()
