"""Portable native schemas extracted verbatim; no model owner is bundled."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def tools():
    spec=json.loads((ROOT/'source/interface_contract.json').read_bytes());result=[]
    descriptions={'run_app':'Observe one allowed CLI operation.', 'apply_profile':'Select and install an allowed dependency profile offline.',
        'write_file':'Write the complete UTF-8 file content.', 'read_file':'Read a workspace file.',
        'list_files':'List workspace files.', 'finish':'End the repair and provide a short summary.'}
    for name,row in spec['tools'].items():
        props={k:{'type':'string'} for k in row['required']}
        if name=='run_app':props['operation']['enum']=list(row['operations'])
        if name=='apply_profile':
            props['profile']['enum']=list(spec['allowed_profiles'])
            props['profile']['description']='Allowed dependency versions: '+json.dumps(spec['allowed_profiles'],sort_keys=True)
        result.append({'type':'function','function':{'name':name,'description':descriptions[name],
            'parameters':{'type':'object','properties':props,'required':list(row['required']),'additionalProperties':False}}})
    return result

def template_payload(messages,thinking):
    return {'messages':messages,'tools':tools(),'tool_choice':'auto','parallel_tool_calls':False,
            'chat_template_kwargs':{'enable_thinking':thinking},'reasoning_format':'deepseek'}
