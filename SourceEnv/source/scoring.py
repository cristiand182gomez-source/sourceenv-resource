"""One stateless CLI contract for agent and scorer; no resets or feedback."""
from common import require,save
import time
from lifecycle import GRADING_SECONDS, LocalFailure, GlobalFailure
def compare(final,initial,reference,source_changed,profile_changed,case,valid=True):
    losses=[op for op,ok in initial['checks'].items() if ok and not final['checks'].get(op,False)]
    return {'final_task_pass':final['status']=='PASS' if valid else None,
            'source_changed':source_changed,'installed_profile_changed':profile_changed,
            'operation_checks':final['checks'],'observed_behavior_loss_vs_initial':losses,
            'healthy_fixture':case['healthy'],'infrastructure_invalid':not valid}
def grade_case(dispatcher,case,policy,oracle,output):
    start=time.monotonic();deadline=start+GRADING_SECONDS
    before=dispatcher.offline.inspect_state(dispatcher.state)
    record={'status':'GRADING','phase':'grading','started_monotonic':start,'deadline_monotonic':deadline,
            'before':before,'operations':{},'scored_before_cleanup':False,'cleanup_performed':False}
    save(output,record)
    for op,argv in policy['operations'].items():
        if time.monotonic()+10>deadline:
            raise LocalFailure('GRADING_DEADLINE','Insufficient grading phase time; partial rows retained')
        record['operations'][op]={'kind':'grading/'+op,'status':'CAPTURE_PENDING','process_launched':None}
        save(output,record) # Retain attempted capture even if capture itself raises.
        row=dispatcher.judge.capture(dispatcher.judge.sandbox_command(before,argv),timeout=10)
        row['kind']='grading/'+op;record['operations'][op]=row;save(output,record)
        if row.get('error')=='LAUNCH_FAILED':raise LocalFailure('GRADER','Scorer launcher unavailable')
        if time.monotonic()>=deadline:raise LocalFailure('GRADING_DEADLINE','Private grading phase expired')
    record.update(oracle.classify(record['operations'],case,before['profile'],policy))
    after=dispatcher.offline.inspect_state(dispatcher.state)
    if before!=after:raise GlobalFailure('SCORER_CHANGED_STATE','Private grader changed the repair')
    dispatcher.check_integrity()
    record.update(after=after,final_state_preserved=True,scored_before_cleanup=True,elapsed_seconds=time.monotonic()-start)
    save(output,record);return record
