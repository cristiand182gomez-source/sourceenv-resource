"""Actual capture attempts and proven launch bounds; missing rows are not zero."""
def capture_counts(rows):
    rows=list(rows);known=unknown=failed=0
    for r in rows:
        if r.get('error')=='LAUNCH_FAILED':failed+=1
        elif type(r.get('exit_code')) is int:known+=1
        else:unknown+=1
    return {'capture_attempts':len(rows),'processes_launched_lower_bound':known,
            'processes_launched_upper_bound':known+unknown,'launch_failed':failed,
            'launch_accounting_complete':unknown==0,'unknown_launches_are_zero':False}
