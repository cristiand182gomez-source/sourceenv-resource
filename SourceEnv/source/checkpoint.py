"""Small shared-prefix checkpoint. No model calls and no in-loop grading."""
import copy,shutil,time
from pathlib import Path
from common import save,require
from coverage_policy import state_identity

class PrefixCheckpoint:
    def __init__(self,output):
        self.output=Path(output)/'derived-base';self.output.mkdir(exist_ok=False)
        self.record=None;self.tracker=None;self.adapter=None
    def capture(self,dispatcher,args):
        if self.record is not None:return
        start=time.monotonic();snapshot=dispatcher.offline.inspect_state(dispatcher.state)
        self.tracker=copy.deepcopy(dispatcher.coverage)
        record={'origin':'first_eligible_valid_finish','action_index':dispatcher.actions,
            'epoch':dispatcher.coverage.epoch,'state_identity':state_identity(snapshot),
            'pending_finish_summary':args['summary'],'actions':dispatcher.actions,
            'run_app_attempts':dispatcher.runs,'profile_attempts':dispatcher.installs,
            'prefix_events':copy.deepcopy(dispatcher.events),'state_preserved':True,
            'checkpoint_time_charged_to_episode':True,'generation_calls':0,
            'snapshot_before':snapshot}
        if self.adapter:
            record.update(messages_before_policy_response=copy.deepcopy(self.adapter.messages),
                generated_tokens_consumed=self.adapter.generated,model_replies_received=self.adapter.replies,
                deadline_monotonic=self.adapter.deadline)
        # No copy is needed when coverage is already complete: both policies
        # stop immediately and the retained terminal can be scored once.
        if dispatcher.coverage.missing():
            target=self.output/'state';target.mkdir(exist_ok=False)
            shutil.copytree(dispatcher.state/'workspace',target/'workspace',symlinks=False)
            selected=__import__('json').loads((dispatcher.state/'active.json').read_bytes())
            (target/'environments').mkdir()
            shutil.copytree(Path(snapshot['environment']),target/'environments'/selected['directory'],symlinks=True)
            shutil.copy2(dispatcher.state/'active.json',target/'active.json')
            copied=dispatcher.offline.inspect_state(target)
            require(state_identity(copied)==record['state_identity'],'CHECKPOINT_IDENTITY_CHANGED')
            record.update(copied_state=str(target),copied_bytes=sum(p.stat().st_size for p in target.rglob('*') if p.is_file() and not p.is_symlink()))
        else:record.update(copied_state=None,copied_bytes=0)
        require(dispatcher.offline.inspect_state(dispatcher.state)==snapshot,'CHECKPOINT_MUTATED_FC')
        record.update(copy_elapsed_seconds=time.monotonic()-start,
                      episode_remaining_after_checkpoint=dispatcher.remaining())
        self.record=record;save(self.output/'checkpoint.json',record)
    def reaches_policy(self,dispatcher):
        return bool(self.record and any(f['action_index']==self.record['action_index']
                                        for f in dispatcher.coverage.finishes))
    def has_independent_terminal(self,dispatcher):
        return self.reaches_policy(dispatcher) and bool(self.record.get('copied_state'))
    def derive(self,dispatcher,case,initial_grade,final_grade,reference,valid):
        from scoring import grade_case,compare
        from types import SimpleNamespace
        reaches_policy=self.reaches_policy(dispatcher)
        if reaches_policy:
            # A later FC transport failure cannot undo BASE's already retained
            # terminal. Clone grading still verifies current trusted integrity.
            base_valid=True if self.has_independent_terminal(dispatcher) else valid
            tracker=copy.deepcopy(self.tracker);tracker.finish('BASE',self.record['action_index'])
            common=dispatcher.stop_reason=='finish' and len(dispatcher.coverage.finishes)==1 and dispatcher.coverage.finishes[0]['accepted']
            state=dispatcher.state if common else Path(self.record['copied_state'])
            if common:
                require(final_grade is not None,'SHARED_TERMINAL_EVALUATION_UNAVAILABLE')
                require(state_identity(final_grade['before'])==self.record['state_identity'],'COMMON_TERMINAL_CHANGED')
                grade=final_grade;origin='shared_finish_terminal_score'
            else:
                from lifecycle import GlobalFailure
                if state_identity(dispatcher.offline.inspect_state(state))!=self.record['state_identity']:
                    raise GlobalFailure('BASE_CHECKPOINT_INTEGRITY','Retained BASE checkpoint identity changed')
                clone=SimpleNamespace(state=state,offline=dispatcher.offline,judge=dispatcher.judge,check_integrity=dispatcher.check_integrity)
                grade=grade_case(clone,case,dispatcher.offline.policy(),dispatcher.metric_oracle,self.output/'final-score.json')
                origin='checkpoint_score_after_fc_stopped'
            coverage=tracker.record();stop='finish';index=self.record['action_index']
        else:
            base_valid=valid
            # No eligible policy finish: neither branch diverged. Budget/context/
            # wall terminals are included and reuse their exact retained score.
            require(final_grade is not None,'SHARED_TERMINAL_EVALUATION_UNAVAILABLE')
            grade=final_grade;origin='shared_terminal_without_policy_finish'
            coverage=dispatcher.coverage_record();stop=dispatcher.stop_reason;index=dispatcher.actions
            state=dispatcher.state
        result={'status':'DERIVED_CASE_SCORED' if base_valid else 'INVALID_INFRASTRUCTURE',
            'physical_fc_infrastructure_valid':valid,
            'execution_origin':'derived_BASE','basis_case':case['case_id'],'condition':'BASE',
            'score_origin':origin,'stop_reason':stop,'state_directory':str(state),
            'terminal_action_index':index,'coverage_metrics':coverage,'initial_score_reused':True,
            'physical_model_episodes':0,'model_inferences_attempted':0,'generated_tokens':0,
            'additional_grading_applications':6 if origin=='checkpoint_score_after_fc_stopped' else 0,
            'checkpoint':self.record,'final_score':grade,'cleanup_performed':False}
        result.update(compare(grade,initial_grade,reference,
            grade['before']['source_files']!=initial_grade['before']['source_files'],
            grade['before']['profile']!=initial_grade['before']['profile'],case,base_valid))
        save(self.output/'result.json',result);return result
