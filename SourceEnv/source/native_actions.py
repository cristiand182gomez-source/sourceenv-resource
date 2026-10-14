"""Native replies map to exactly one dispatcher action; preserve raw arguments."""
import json
from interface import ActionRejected
EMPTY='Empty reply: call a tool, or reply with your final summary to finish.'
def request_tool_name(message):
    calls=message.get('tool_calls') if type(message) is dict else None
    if type(calls) is list and len(calls)==1 and type(calls[0]) is dict:
        function=calls[0].get('function')
        if type(function) is dict and type(function.get('name')) is str:return function['name']
    return None
def encode_action(message):
    if type(message) is not dict:raise ActionRejected('NATIVE_REPLY_TYPE',{'message':'Expected an assistant message object.'})
    calls=message.get('tool_calls')
    if calls is None:calls=[]
    if type(calls) is not list:raise ActionRejected('NATIVE_CALLS_TYPE',{'message':'tool_calls must be an array of native function calls.'})
    if not calls:
        text=message.get('content')
        if text is None:text=''
        if type(text) is not str:raise ActionRejected('NATIVE_CONTENT_TYPE',{'message':'Reply content must be text or one native tool call.'})
        if not text.strip():raise ActionRejected('EMPTY_REPLY',{'message':EMPTY})
        return json.dumps({'tool':'finish','arguments':{'summary':text}},ensure_ascii=False)
    if len(calls)!=1:raise ActionRejected('MULTIPLE_TOOL_CALLS',{'message':'Call exactly one tool per response; parallel tool calls are not supported.'})
    try:
        f=calls[0]['function'];name=f['name'];args=f['arguments']
        if type(name) is not str:raise TypeError('function name is not a string')
        raw=args if type(args) is str else json.dumps(args,ensure_ascii=False,allow_nan=False)
        return '{"tool":'+json.dumps(name)+',"arguments":'+raw+'}'
    except (KeyError,ValueError,TypeError) as exc:
        raise ActionRejected('MALFORMED_TOOL_CALL',{'message':'Malformed native tool call: '+str(exc)+'. Supply function.name and function.arguments matching the tool schema.'})

def feedback_messages(message,response,serialize):
    calls=message.get('tool_calls') if type(message) is dict else None
    usable=[c for c in calls if type(c) is dict and type(c.get('id')) is str and type(c.get('function')) is dict and type(c['function'].get('name')) is str] if type(calls) is list else []
    if usable:
        return [{'role':'tool','tool_call_id':c['id'],'name':c['function']['name'],'content':serialize(response,tool_name=c['function']['name'])} for c in usable]
    return [{'role':'user','content':serialize(response)}]
