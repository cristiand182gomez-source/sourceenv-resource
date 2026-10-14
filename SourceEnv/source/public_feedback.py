"""C3 public serialization retained; no private verdicts are added."""
import json
from invalid_feedback import explain
def canonical(value):return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))
def lf(text):return text.replace('\r\n','\n').replace('\r','\n')
def feedback_text(response,tool_name=None):
    response=explain(response)
    if response.get('error')=='EMPTY_REPLY':return response['message']
    if tool_name=='run_app' or 'capture_completed' in response:
        response={k:v for k,v in response.items() if k!='ok'}
    if 'capture_completed' in response:
        metadata={k:v for k,v in response.items() if k not in ('stdout','stderr')}
        return ('Application capture (not a task verdict):\n'+json.dumps(metadata,ensure_ascii=False,sort_keys=True,indent=2)
            +'\n===== stdout =====\n'+response['stdout']+'\n===== stderr =====\n'+response['stderr']+'\n===== END capture =====')
    if response.get('ok') is True and type(response.get('content')) is str:
        return (canonical({k:v for k,v in response.items() if k!='content'})+'\n===== file content (LF display) =====\n'
            +lf(response['content'])+'\n===== END file content =====')
    return canonical(response)
