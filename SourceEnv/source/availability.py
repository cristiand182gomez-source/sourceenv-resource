"""Arm-specific grading; an exclusive error never discards the other arm."""
from pathlib import Path
import json
from scoring import grade_case,compare
from lifecycle import GlobalFailure,LocalFailure

ORDINARY={'finish','action_budget','run_app_budget','install_budget','generated_token_budget','context_budget','global_call_budget'}

def settle(report,d,checkpoint,case,baseline,out,failure=None,grade=grade_case):
    terminal=d.stop_reason
    primary='VALID' if failure is None and terminal in ORDINARY else 'CENSORED' if report.get('cancellation_verified') else 'INVALID'
    report.update(primary_availability=primary,final_task_pass=None)
    final=None
    try:
        final=grade(d,case,d.offline.policy(),d.metric_oracle,Path(out)/'final-score.json')
        report['final_score']=final
        report.update(compare(final,baseline,baseline,final['before']['source_files']!=baseline['before']['source_files'],
                    final['before']['profile']!=baseline['before']['profile'],case,primary=='VALID'))
    except GlobalFailure:raise
    except LocalFailure as exc:
        report.update(primary_availability='INVALID' if primary=='VALID' else primary,grading_error=str(exc))
        path=Path(out)/'final-score.json'
        if path.exists():report['partial_final_grading']=json.loads(path.read_bytes())
    except Exception as exc:raise GlobalFailure('UNKNOWN_FC_GRADER','Unclassified grader error',{'detail':str(exc)}) from exc
    try:
        if final is None and not checkpoint.has_independent_terminal(d):
            raise LocalFailure('SHARED_EVALUATION_UNAVAILABLE','Common terminal score unavailable')
        base=checkpoint.derive(d,case,baseline,final,baseline,primary=='VALID')
        independent=checkpoint.has_independent_terminal(d)
        availability='VALID' if independent else report['primary_availability']
        if base.get('infrastructure_invalid') and availability=='VALID':availability='INVALID'
        base['primary_availability']=availability
        if availability!='VALID':base['final_task_pass']=None
        report['derived_BASE']=base
    except GlobalFailure:raise
    except LocalFailure as exc:
        report['derived_BASE']={'execution_origin':'derived_BASE','primary_availability':'CENSORED' if primary=='CENSORED' and not checkpoint.has_independent_terminal(d) else 'INVALID','final_task_pass':None,
            'grading_error':str(exc),'terminal_action_index':checkpoint.record['action_index'] if checkpoint.reaches_policy(d) else d.actions,
            'coverage_metrics':checkpoint.tracker.record() if checkpoint.reaches_policy(d) else d.coverage_record(),
            'stop_reason':'finish' if checkpoint.reaches_policy(d) else terminal,'model_inferences_attempted':0}
        path=Path(out)/'derived-base/final-score.json'
        if path.exists():report['derived_BASE']['partial_final_grading']=json.loads(path.read_bytes())
    except Exception as exc:raise GlobalFailure('UNKNOWN_BASE_GRADER','Unclassified BASE grader error',{'detail':str(exc)}) from exc
    report['pair_complete']=report['primary_availability']=='VALID' and report['derived_BASE']['primary_availability']=='VALID'
    base=report['derived_BASE'];record=checkpoint.record if checkpoint.reaches_policy(d) else None
    base['logical_prefix_cost']={'received_model_replies':record.get('model_replies_received') if record else report.get('model_calls'),
        'known_generated_tokens':record.get('generated_tokens_consumed') if record else report.get('generated_tokens'),
        'physical_additional_generation_calls':0,'shared_cost_not_counted_twice':True}
    report['gate_exposure']={'policy_rejections':d.coverage_record()['finish_policy_rejections'],
        'bifurcated':checkpoint.has_independent_terminal(d),
        'checkpoint_reached_policy':checkpoint.reaches_policy(d)}
