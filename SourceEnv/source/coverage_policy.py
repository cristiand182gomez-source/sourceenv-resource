"""Private observations; one shared prefix, policy read only at finish."""
import copy,json
from common import canonical,sha
from interface import Dispatcher,parse_action,validate_arguments,CONTRACT,ActionRejected

def state_identity(snapshot):
    config=[line for line in snapshot['environment_configuration'].splitlines()
            if not line.startswith('command =')]
    return sha(canonical({'source':snapshot['source_files'],
        'payload':snapshot['installed_payload_sha256'],
        'interpreter':snapshot['trusted_base_interpreter_sha256'],
        'configuration':config,'invocation_contract':CONTRACT['stateless_application_contract']}).encode())

def environment_identity(snapshot):
    return state_identity(dict(snapshot,source_files={}))

class CoverageTracker:
    def __init__(self,operations,snapshot):
        self.operations=list(operations);self.identity=state_identity(snapshot);self.epoch=0
        self.current=set();self.cumulative=set();self.observations={};self.changes=[];self.finishes=[]
    def reconcile(self,snapshot,index,cause):
        identity=state_identity(snapshot) if snapshot is not None else None
        changed=identity is None or self.identity is None or identity!=self.identity
        if changed:
            self.changes.append({'action_index':index,'cause':cause,'before':self.identity,
                'after':identity,'epoch_before':self.epoch,'epoch_after':self.epoch+1})
            self.epoch+=1;self.current.clear();self.observations.clear()
        self.identity=identity;return changed
    def observe(self,operation,completed,private_pass,feedback_verdict,index,same_state=True,truncated=False):
        if completed:
            self.cumulative.add(operation)
            if same_state:self.current.add(operation)
        if same_state:
            self.observations[operation]={'action_index':index,'completed':completed,
                'oracle_pass':private_pass,'feedback_verdict':feedback_verdict,'truncated':truncated}
    def missing(self):return [op for op in self.operations if op not in self.current]
    def pending(self):
        return {'oracle_failure_operations':[op for op in self.operations if op in self.observations and self.observations[op]['oracle_pass'] is False],
                'feedback_failure_operations':[op for op in self.operations if op in self.observations and self.observations[op]['feedback_verdict']=='FAIL'],
                'feedback_unknown_operations':[op for op in self.operations if op in self.observations and self.observations[op]['feedback_verdict']=='UNKNOWN'],
                'unobserved_operations':[op for op in self.operations if op not in self.observations]}
    def finish(self,policy,index):
        missing=self.missing();accepted=policy=='BASE' or not missing
        self.finishes.append({'action_index':index,'epoch':self.epoch,'state_identity':self.identity,
            'coverage_count':len(self.current),'missing_operations':missing,'accepted':accepted,**self.pending()})
        if accepted:return {'ok':True,'finished':True}
        message=('Finish rejected: these operations have not been run in the current state: '
            +json.dumps(missing)+'. Coverage resets with every effective change to source or environment. '
            +'Run them in the current state before finishing.')
        return {'ok':False,'error':'PENDING_OPERATIONS','missing_operations':missing,'message':message}
    def record(self):
        accepted=[f for f in self.finishes if f['accepted']]
        return {'epoch':self.epoch,'state_identity':self.identity,'epoch_changes':copy.deepcopy(self.changes),
            'cumulative_operations':[op for op in self.operations if op in self.cumulative],
            'cumulative_coverage_count':len(self.cumulative),
            'final_state_operations':[op for op in self.operations if op in self.current],
            'final_state_coverage_count':len(self.current),'current_observations':copy.deepcopy(self.observations),
            'finish_attempts':copy.deepcopy(self.finishes),'finish_policy_rejections':sum(not f['accepted'] for f in self.finishes),
            'coverage_before_finish':accepted[-1]['coverage_count'] if accepted else None}

def feedback_verdict(response,operation,oracle,case,profile,policy):
    # Conservative rule: only a complete, untruncated UTF-8 view can establish
    # a behavioral verdict. UNKNOWN is not PASS and not evidence of understanding.
    if response.get('truncated') is not False or response.get('utf8_valid') is not True:
        return 'UNKNOWN'
    return 'PASS' if oracle.operation_check(operation,response,case,profile,policy) else 'FAIL'

class CoverageDispatcher(Dispatcher):
    def __init__(self,*args,case,oracle,policy,**kwargs):
        assert policy in ('BASE','FINISH-COVERAGE')
        self.metric_case,self.metric_oracle,self.finish_policy=case,oracle,policy
        self.before_finish=None
        super().__init__(*args,**kwargs)
        self.coverage=CoverageTracker(self.offline.policy()['operations'],self.initial)
    def finish_action(self,args):
        # Same hook in both policies; no condition is read before this point.
        if self.before_finish:self.before_finish(self,args)
        if self.remaining()<=0:
            self.stopped,self.stop_reason=True,'watchdog'
            return {'ok':False,'error':'WALL_BUDGET_EXHAUSTED'}
        response=self.coverage.finish(self.finish_policy,self.actions)
        if response['ok']:self.stopped,self.stop_reason=True,'finish'
        return response
    def dispatch(self,raw, *, rejection=None,tool_name=None):
        if self.stopped:return super().dispatch(raw,rejection=rejection)
        try:before=self.offline.inspect_state(self.state)
        except Exception:
            self.coverage.reconcile(None,self.actions+1,'before_action_unknown');raise
        self.coverage.reconcile(before,self.actions+1,'before_action_changed')
        try:response=super().dispatch(raw,rejection=rejection)
        except BaseException:
            try:after=self.offline.inspect_state(self.state)
            except Exception:after=None
            self.coverage.reconcile(after,self.actions,'failed_action_unknown_or_changed');raise
        after=self.offline.inspect_state(self.state)
        changed=self.coverage.reconcile(after,self.actions,'effective_source_or_environment_change')
        if not self.events:return response
        event=self.events[-1]
        environment_changed=environment_identity(before)!=environment_identity(after)
        try:action=parse_action(raw)
        except ActionRejected:
            if tool_name=='apply_profile':response['changed']=environment_changed
            return response
        if action['tool']=='apply_profile':
            response['changed']=environment_changed
            event['effective_environment_change']=environment_changed
        try:validate_arguments(action)
        except ActionRejected:return response
        event.update(epoch_after=self.coverage.epoch,effective_state_change=changed,state_identity_after=self.coverage.identity)
        if action['tool']=='write_file':
            event['effective_source_change']=before['source_files']!=after['source_files']
        if action['tool']=='apply_profile':
            event['effective_environment_change']=environment_changed
        if action['tool']=='run_app' and 'capture_completed' in response:
            op=action['arguments']['operation']
            row=next(r for r in reversed(self.records) if r.get('kind')=='run_app/'+op)
            completed=row.get('error') is None and row.get('utf8_valid') is True and type(row.get('exit_code')) is int and row['exit_code']>=0
            passed=self.metric_oracle.operation_check(op,row,self.metric_case,before['profile'],self.offline.policy())
            visible=feedback_verdict(response,op,self.metric_oracle,self.metric_case,before['profile'],self.offline.policy())
            self.coverage.observe(op,completed,passed,visible,self.actions,not changed,response.get('truncated',False))
            event['observation']={'completed':completed,'oracle_pass':passed,'feedback_verdict':visible,'truncated':response.get('truncated')}
        return response
    def coverage_record(self):return self.coverage.record()
