"""English explanations for rejected native requests. No private verdicts."""
MESSAGES={
 'INVALID_JSON':'Tool arguments are not valid JSON. Call one tool with an argument object matching its schema, or reply with your final summary to finish.',
 'INVALID_ACTION':'Expected one native tool call with a function name and an argument object, or a non-empty final summary.',
 'DUPLICATE_KEY':'Tool arguments contain a duplicate key; use each argument name once.',
 'NONFINITE_NUMBER':'Tool arguments contain NaN or Infinity; these values are not permitted.',
 'TOOL_REJECTED':'Unknown tool name. Use list_files, read_file, write_file, run_app, apply_profile, or finish.',
 'ARGUMENTS_REJECTED':'The tool arguments do not match its documented names and string types.',
 'OPERATION_REJECTED':'Unknown operation. Use first_command, second_command, no_args, explicit_help, first_command_help, or second_command_help.',
 'PROFILE_REJECTED':'Unknown dependency profile. Select one of the documented allowed profile names.',
 'REQUEST_LIMIT':'The tool request exceeds the allowed request size.',
 'SUMMARY_LIMIT':'The final summary exceeds 2000 UTF-8 bytes; provide a shorter final summary.',
 'FILE_LIMIT':'The file exceeds the allowed 65536-byte limit.',
 'INVALID_UTF8':'The tool request or file is not valid UTF-8.',
 'PATH_REJECTED':'The path is not a permitted relative workspace path. Absolute paths, empty or dot components, backslashes and traversal are not allowed.',
 'NONREGULAR_REJECTED':'The requested path is not a regular file; links and special files are not allowed.',
 'WORKSPACE_CHANGED':'The file changed during the operation; the request was rejected.',
 'WORKSPACE_LIMIT':'The request exceeds the workspace file, directory or total byte limit.',
 'FILE_NOT_FOUND':'The requested workspace file does not exist.',
 'FILESYSTEM_REJECTED':'The filesystem operation was not permitted by the workspace contract.',
 'SESSION_STOPPED':'The episode has already stopped; no further action can be executed.',
 'RUN_APP_BUDGET_EXHAUSTED':'The run_app request limit has been exceeded; the retained state will be scored.',
 'INSTALL_BUDGET_EXHAUSTED':'The apply_profile request limit has been exceeded; the retained state will be scored.',
 'WALL_BUDGET_EXHAUSTED':'The episode watchdog expired; no further action can execute.',
 'INSUFFICIENT_APPLICATION_TIME':'The episode watchdog expired before this application could start.',
 'INFRASTRUCTURE_FAILURE':'The harness could not safely complete the request; execution has stopped.'}
NON_INVALID={'PENDING_OPERATIONS','SESSION_STOPPED','RUN_APP_BUDGET_EXHAUSTED','INSTALL_BUDGET_EXHAUSTED','WALL_BUDGET_EXHAUSTED','INSUFFICIENT_APPLICATION_TIME','INFRASTRUCTURE_FAILURE'}
def explain(response):
    if response.get('ok') is not False or not response.get('error') or response['error']=='PENDING_OPERATIONS':return response
    response=dict(response);detail=response.get('detail') or {}
    response['message']=detail.get('message') or MESSAGES.get(response['error'],'The tool request was rejected: '+str(response['error'])+'. Check its documented argument values.')
    return response
