"""Health of actual retained replies/actions. Works for native and older logs."""
import collections,copy,json,re
from interface import parse_action,validate_arguments,CONTRACT
from invalid_feedback import NON_INVALID
OUTDATED=('Usá un único objeto JSON','empezá con {','sin Markdown ni bloques de código','Return exactly one JSON object','You must return exactly one JSON object','typer-action-json-0.2-gbnf')
def _action(event):
    try:
        a=parse_action(event.get('request'));validate_arguments(a);return a,None
    except Exception as exc:
        return None,event.get('response',{}).get('error') or str(exc)
def _kind(event,turn):
    a,error=_action(event)
    if not a:return 'invalid:'+str(error)
    if a['tool']=='finish':
        msg=turn.get('reply',{}).get('message',{})
        return 'finish_tool' if msg.get('tool_calls') else 'finish_text'
    return a['tool']
def analyze_arm(episode,arm):
    base=episode.get('derived_BASE') or {};limit=episode.get('actions',0) if arm=='FC' else base.get('terminal_action_index',episode.get('actions',0))
    events=copy.deepcopy([e for e in episode.get('events',[]) if e.get('index',0)<=limit])
    if arm=='BASE' and base.get('stop_reason')=='finish' and events:events[-1]['response']={'ok':True,'finished':True}
    received=[t for t in episode.get('conversation',{}).get('turns',[]) if 'reply' in t and (arm=='FC' or t['index']<=limit)]
    by_index={t['index']:t for t in received};without=sum(not t['reply'].get('message',{}).get('tool_calls') for t in received)
    empty=sum(not t['reply'].get('message',{}).get('tool_calls') and not (t['reply'].get('message',{}).get('content') or '').strip() for t in received)
    invalid=collections.Counter();post=collections.Counter();first=None
    for e in events:
        a,error=_action(e);response=e.get('response',{})
        code=response.get('error')
        if a is None:invalid[error]+=1
        elif response.get('ok') is False and code not in NON_INVALID:invalid[code or 'REJECTED_WITHOUT_CODE']+=1
        if first is not None:post[_kind(e,by_index.get(e['index'],{}))]+=1
        if first is None and code=='PENDING_OPERATIONS' and a and a['tool']=='finish':first=e['index']
    record=episode if arm=='FC' else base;finishes=(record.get('coverage_metrics') or {}).get('finish_attempts',[])
    actual_messages=[]
    for t in received:
        actual_messages.extend(m for m in t.get('messages',[]) if m.get('role') in ['system','user','tool'])
    if arm=='FC':actual_messages.extend(m for m in episode.get('conversation',{}).get('messages',[]) if m.get('role') in ['system','user','tool'])
    stale=sorted({s for m in actual_messages for s in OUTDATED if s in (m.get('content') or '')})
    n=len(events);count=sum(invalid.values());budget=CONTRACT['budget']['max_actions']
    complete=(n==limit and all(e.get('index')==i for i,e in enumerate(events,1)) and len(received)>=n)
    return {'arm':arm,'terminal':record.get('stop_reason'),'primary_availability':record.get('primary_availability'),
       'replies_received':len(received),'actions_dispatched':n,'action_budget':budget,'complete_retained_trace':complete,
       'responses_without_tool_calls':{'count':without,'denominator':len(received),'rate':without/len(received) if received else None},
       'empty_replies_without_tool_calls':empty,'invalid_actions':count,'invalid_rate':count/n if n else None,
       'invalid_by_type':{k:{'count':v,'denominator':n,'rate':v/n} for k,v in sorted(invalid.items())},
       'invalid_share_of_action_budget':{'count':count,'denominator':budget,'percent':100*count/budget},
       'valid_finish_requests':len(finishes),'accepted_finish_requests':sum(f['accepted'] for f in finishes),
       'first_FC_rejection_action':first if arm=='FC' else None,'actions_after_first_FC_rejection':dict(post) if arm=='FC' else {},
       'actions_after_first_FC_rejection_total':sum(post.values()) if arm=='FC' else 0,'outdated_messages':stale,
       'model_replies_not_dispatched':len(received)-n,
       'denominators':'no-tool/replies retained; invalid/actions dispatched; budget percent/20; finish rejection is valid, not invalid'}
def analyze_episode(episode):
    return {'case_id':episode.get('case_id'),'FC':analyze_arm(episode,'FC'),'BASE':analyze_arm(episode,'BASE')}
def health_passed(health):
    r=health['FC']
    return r['primary_availability']=='VALID' and r['complete_retained_trace'] and r['invalid_rate'] is not None and r['invalid_rate']<.1 and r['valid_finish_requests']>=1 and not r['outdated_messages']
def main():
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('episodes',nargs='+');p.add_argument('--output',required=True);args=p.parse_args()
    rows=[analyze_episode(json.loads(Path(e).read_bytes())) for e in args.episodes]
    out=Path(args.output)
    if out.exists():raise RuntimeError('OUTPUT_EXISTS')
    out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
