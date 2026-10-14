"""Read-only trajectory metrics. Never dispatch tools or import candidate code."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from interface import parse_action, validate_arguments, CONTRACT

OPS=tuple(CONTRACT['tools']['run_app']['operations'])
VIEW_FIELDS=('exit_code','stdout','stderr','error','utf8_valid','truncated',
             'capture_hit_limit','captured_bytes','view_bytes')

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def valid_action(raw):
    try:
        a=parse_action(raw);validate_arguments(a);return a
    except Exception:return None

def unavailable(reason, **evidence):return {'available':False,'value':None,'reason':reason,**evidence}
def measured(value, **evidence):return {'available':True,'value':value,**evidence}

def trace_metrics(events, *, expected_actions, terminal_epoch, epoch_changes=(), closed=True):
    """Metrics require all dispatched actions; missing model replies are not actions.

    A completely retained censored/invalid primary can have available trace metrics.
    A missing action event makes whole-trajectory metrics unavailable and leaves
    only an explicitly partial observed-prefix diagnostic.
    """
    if type(events) is not list or type(expected_actions) is not int or expected_actions<0:
        return {'availability':'UNAVAILABLE','reason':'missing_action_trace_or_count'}
    contiguous=all(type(e) is dict and e.get('index')==i for i,e in enumerate(events,1))
    if not contiguous or len(events)!=expected_actions:
        return {'availability':'UNAVAILABLE','reason':'missing_or_duplicate_action_events',
                'expected_actions':expected_actions,'retained_actions':len(events),
                'observed_prefix_is_not_terminal_metric':True}
    if not closed or type(terminal_epoch) is not int or terminal_epoch<0:
        return {'availability':'UNAVAILABLE','reason':'terminal_epoch_or_closure_missing','retained_actions':len(events)}
    changes={}
    for c in epoch_changes:
        if type(c.get('action_index')) is not int or type(c.get('epoch_after')) is not int:
            return {'availability':'UNAVAILABLE','reason':'malformed_epoch_changes'}
        changes[c['action_index']]=max(changes.get(c['action_index'],0),c['epoch_after'])
    maximum=run=0;last=None;epoch=0;seen=set();ops=set();in_epoch=set();suffix=0
    completed=redundant=unknown_signature=0;signatures={};valid=invalid=0;accepted_finish_excluded=0
    for i,e in enumerate(events,1):
        a=valid_action(e.get('request'))
        key=canonical(a) if a is not None else None
        if a is None:invalid+=1;run=0;last=None
        else:
            valid+=1;run=run+1 if key==last else 1;last=key;maximum=max(maximum,run)
        new_epoch=e.get('epoch_after',changes.get(i,epoch))
        if type(new_epoch) is not int or new_epoch<epoch:
            return {'availability':'UNAVAILABLE','reason':'epoch_missing_or_regressed','at_action':i}
        if new_epoch!=epoch:in_epoch.clear()
        epoch=new_epoch;new_pair=False
        response=e.get('response',{})
        observation=e.get('observation')
        if a and a['tool']=='run_app' and observation is not None:
            if type(observation.get('completed')) is not bool:
                return {'availability':'UNAVAILABLE','reason':'completion_flag_missing','at_action':i}
            complete=observation['completed']
            # Contract: capture error=None, UTF-8 valid, nonnegative integer rc.
            if all(k in response for k in ('error','utf8_valid','exit_code')):
                contract_complete=(response['error'] is None and response['utf8_valid'] is True
                                   and type(response['exit_code']) is int and response['exit_code']>=0)
                if contract_complete!=complete:
                    return {'availability':'UNAVAILABLE','reason':'completion_flag_disagrees_with_contract','at_action':i}
            if complete:
                if e.get('effective_state_change') is True:
                    return {'availability':'UNAVAILABLE','reason':'completed_capture_spans_state_change','at_action':i}
                completed+=1;op=a['arguments']['operation'];pair=(op,epoch)
                new_pair=pair not in seen;seen.add(pair);ops.add(op);in_epoch.add(op)
                if all(k in response for k in VIEW_FIELDS):
                    # Exact delivered characters/flags/byte counts, no normalization.
                    signature=canonical({k:response[k] for k in VIEW_FIELDS})
                    prior=signatures.setdefault(pair,set())
                    if signature in prior:redundant+=1
                    prior.add(signature)
                else:unknown_signature+=1
        elif a and a['tool']=='run_app' and response.get('ok') is True:
            # ok=True alone cannot establish a completed capture.
            return {'availability':'UNAVAILABLE','reason':'capture_completion_evidence_missing','at_action':i}
        terminal_finish=(i==expected_actions and a and a['tool']=='finish'
                         and response.get('ok') is True and response.get('finished') is True)
        if i<expected_actions and a and a['tool']=='finish' and response.get('ok') is True and response.get('finished') is True:
            return {'availability':'UNAVAILABLE','reason':'accepted_finish_before_terminal','at_action':i}
        if terminal_finish:accepted_finish_excluded=1
        else:suffix=0 if new_pair else suffix+1
    if epoch!=terminal_epoch:
        # A state change without a dispatched action is already reflected by
        # coverage_record: no earlier observations are current in that epoch.
        if terminal_epoch<epoch:return {'availability':'UNAVAILABLE','reason':'terminal_epoch_regressed'}
        epoch=terminal_epoch;in_epoch.clear()
    redundancy=(unavailable('zero_completed_captures',numerator=0,denominator=0) if completed==0 else
                unavailable('delivered_capture_fields_missing',numerator_known=redundant,denominator=completed,
                            missing_signatures=unknown_signature) if unknown_signature else
                measured(redundant/completed,numerator=redundant,denominator=completed))
    return {'availability':'AVAILABLE','retained_actions':len(events),'argumentally_valid_actions':valid,'invalid_actions':invalid,
            'maximum_identical_action_streak':measured(maximum), 'run_app_redundancy':redundancy,
            'distinct_completed_operations_cumulative':measured(len(ops),operations=[o for o in OPS if o in ops],denominator=6),
            'distinct_completed_operations_terminal_epoch':measured(len(in_epoch),operations=[o for o in OPS if o in in_epoch],
                                                                   denominator=6,epoch=epoch),
            'suffix_without_new_operation_epoch':measured(suffix,accepted_terminal_finish_excluded=accepted_finish_excluded),
            'understanding_or_no_progress_inferred':False}

def analyze_episode(episode):
    events=episode.get('events');coverage=episode.get('coverage_metrics') or {}
    expected=episode.get('actions',episode.get('conversation',{}).get('actions_dispatched'))
    closed=episode.get('stop_reason') is not None and episode.get('model_history_retained',True) is True
    kwargs=dict(expected_actions=expected,terminal_epoch=coverage.get('epoch'),epoch_changes=coverage.get('epoch_changes',()),closed=closed)
    fc=trace_metrics(events,**kwargs)
    base=episode.get('derived_BASE') or {}
    if base and type(base.get('terminal_action_index')) is int and events is not None:
        limit=base['terminal_action_index'];own=copy.deepcopy([e for e in events if e.get('index',0)<=limit]);cov=base.get('coverage_metrics') or {}
        if base.get('stop_reason')=='finish':
            accepted={f['action_index'] for f in cov.get('finish_attempts',[]) if f.get('accepted') is True}
            if limit not in accepted or not own or not valid_action(own[-1].get('request')):
                b={'availability':'UNAVAILABLE','reason':'derived_BASE_policy_response_proof_missing'}
            else:
                # Substitute only the already recorded BASE policy response.
                # No later FC action, observation, grading or feedback is used.
                own[-1]['response']={'ok':True,'finished':True}
                b=trace_metrics(own,expected_actions=limit,terminal_epoch=cov.get('epoch'),epoch_changes=cov.get('epoch_changes',()),closed=True)
        else:b=trace_metrics(own,expected_actions=limit,terminal_epoch=cov.get('epoch'),epoch_changes=cov.get('epoch_changes',()),closed=closed)
    else:b={'availability':'UNAVAILABLE','reason':'derived_BASE_terminal_not_retained'}
    return {'schema':1,'case_id':episode.get('case_id'),'FC':fc,'BASE':b,
            'primary_availability_is_separate':True,'retrospective_unless_declared_before_new_lot':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('episode',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();inputs={};rows=[]
    for path in a.episode:
        data=path.read_bytes();inputs[str(path.resolve())]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        rows.append(analyze_episode(json.loads(data)))
    result={'schema':1,'input_identity':inputs,'results':rows,'native_execution':False,'generation_calls':0}
    with a.output.open('x',encoding='utf-8') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'LOGS_ANALYZED_READ_ONLY','episodes':len(rows),'generation_calls':0,'candidate_applications':0}))
if __name__=='__main__':main()
