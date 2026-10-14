"""Predeclared metrics from retained logs, never tools or candidate imports."""
import copy,json
from interface import parse_action,validate_arguments
from loop_metrics import analyze_episode
from health_metrics import analyze_episode as analyze_health
HELPS={'no_args','explicit_help','first_command_help','second_command_help'}

def trace(events):
    out={'source':{'requests':0,'effective':0,'noops':0,'rejected_or_failed':0,'unknown_effect':0},
         'environment':{'requests':0,'effective':0,'noops':0,'rejected_or_failed':0,'unknown_effect':0},
         'valid_finish_requests':0,'finish_with_current_public_failure':{'accepted':0,'rejected':0},
         'blind_modifying_requests':0,'diagnostic_effective_current':0,'diagnostic_effective_historical':0,
         'profile_after_help_failure_current':0,'profile_after_help_failure_historical':0,
         'profile_effective_after_help_failure_current':0,'profile_effective_after_help_failure_historical':0}
    epoch=0;observed={};ever_failed=set()
    for e in events:
        try:a=parse_action(e['request'])
        except Exception:continue
        try:validate_arguments(a)
        except Exception:
            if a['tool'] in ['write_file','apply_profile']:
                m=out['source' if a['tool']=='write_file' else 'environment'];m['requests']+=1;m['rejected_or_failed']+=1
            continue
        tool=a['tool'];current={o for o,r in observed.items() if r.get('feedback_verdict')=='FAIL'}
        if tool in ['write_file','apply_profile']:
            axis='source' if tool=='write_file' else 'environment';m=out[axis];m['requests']+=1
            ok=e.get('response',{}).get('ok') is True
            flag=e.get('effective_source_change' if axis=='source' else 'effective_environment_change')
            changed=flag is True
            m['effective']+=changed
            m['noops']+=ok and flag is False
            m['rejected_or_failed']+=not ok and flag is False
            m['unknown_effect']+=flag is None
            out['blind_modifying_requests']+=not any(r.get('completed') is True for r in observed.values())
            out['diagnostic_effective_current']+=changed and bool(current)
            out['diagnostic_effective_historical']+=changed and bool(ever_failed)
            if axis=='environment':
                out['profile_after_help_failure_current']+=bool(current&HELPS)
                out['profile_after_help_failure_historical']+=bool(ever_failed&HELPS)
                out['profile_effective_after_help_failure_current']+=changed and bool(current&HELPS)
                out['profile_effective_after_help_failure_historical']+=changed and bool(ever_failed&HELPS)
        if tool=='finish':
            out['valid_finish_requests']+=1
            accepted=e.get('response',{}).get('finished') is True and e.get('response',{}).get('ok') is True
            if current and (accepted or e.get('response',{}).get('error')=='PENDING_OPERATIONS'):
                out['finish_with_current_public_failure']['accepted' if accepted else 'rejected']+=1
        new_epoch=e.get('epoch_after',epoch)
        if new_epoch!=epoch:observed.clear();epoch=new_epoch
        if tool=='run_app' and e.get('observation') is not None:
            op=a['arguments']['operation'];observed[op]=copy.deepcopy(e['observation'])
            if observed[op].get('feedback_verdict')=='FAIL':ever_failed.add(op)
    out['terminal_current_public_failure_operations']=sorted(o for o,r in observed.items() if r.get('feedback_verdict')=='FAIL')
    return out

def analyze(episode):
    base=episode.get('derived_BASE') or {}; limit=base.get('terminal_action_index',episode['actions'])
    own=copy.deepcopy(episode['events'][:limit])
    if own and base.get('stop_reason')=='finish':own[-1]['response']={'ok':True,'finished':True}
    result={'FC':trace(episode['events']),'BASE':trace(own),'loops':analyze_episode(episode),
            'gate_exposure':episode.get('gate_exposure'),'physical_generation_counted_once':True,'health':analyze_health(episode)}
    for name,r in [('FC',episode),('BASE',base)]:
        result[name].update(primary_availability=r.get('primary_availability'),final_task_pass=r.get('final_task_pass'),
             losses=r.get('observed_behavior_loss_vs_initial'),coverage=r.get('coverage_metrics'),stop_reason=r.get('stop_reason'))
    return result

def aggregate(episodes,cases):
    rows={e['case_id']:e for e in episodes};result={'planned_cases':len(cases),'unattempted':[c for c in cases if c not in rows],
        'arms':{},'complete_damaged_pairs':[],'incomplete_pairs':[],'bifurcated_complete_damaged_pairs':[]}
    for arm in ['FC','BASE']:
        available=[];damaged=[];healthy=[]
        for cid,e in rows.items():
            r=e if arm=='FC' else e.get('derived_BASE',{})
            if r.get('primary_availability')=='VALID' and type(r.get('final_task_pass')) is bool:
                available.append(cid);(healthy if cases[cid]['healthy'] else damaged).append(cid)
        def passes(ids):return sum((rows[c] if arm=='FC' else rows[c]['derived_BASE'])['final_task_pass'] for c in ids)
        result['arms'][arm]={'available':available,'repair_numerator':passes(damaged),'repair_denominator':len(damaged),
                'healthy_preservation_numerator':passes(healthy),'healthy_preservation_denominator':len(healthy),
                'planned_damaged_denominator':8,'planned_healthy_denominator':2}
    for cid,e in rows.items():
        complete=all((e if arm=='FC' else e.get('derived_BASE',{})).get('primary_availability')=='VALID'
                     and type((e if arm=='FC' else e.get('derived_BASE',{})).get('final_task_pass')) is bool for arm in ['FC','BASE'])
        if not complete:result['incomplete_pairs'].append(cid)
        elif not cases[cid]['healthy']:
            result['complete_damaged_pairs'].append(cid)
            if e.get('gate_exposure',{}).get('bifurcated'):result['bifurcated_complete_damaged_pairs'].append(cid)
    result['descriptive_pair_comparison_interpretable']=len(result['complete_damaged_pairs'])>=6
    result['few_bifurcations_limit']='0: no observed policy divergence; 1-2: case descriptions only; >=3: still descriptive and conditional subset, not significance/power'
    return result
