"""Finite dispatcher. All candidate execution is Debian Bubblewrap-only."""
from pathlib import Path
import sys
import base64
from hashlib import sha256
import json
import math
import os
import secrets
import tempfile
import time
from lifecycle import GlobalFailure, LocalFailure
from invalid_feedback import MESSAGES,explain
ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / 'interface_contract.json').read_bytes())
def require(value, message):
    if not value:
        raise RuntimeError(message)
def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()
class ActionRejected(Exception):
    def __init__(self, code, detail=None):
        super().__init__(code)
        self.detail = detail if detail is not None else {"message":MESSAGES.get(code,"The request was rejected: "+code+".")}

def no_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ActionRejected('DUPLICATE_KEY', {'message':'Duplicate tool argument key: '+key+'. Use each argument name once.'})
        value[key] = item
    return value

def reject_constant(value):
    raise ActionRejected('NONFINITE_NUMBER')

def parse_action(raw):
    if type(raw) is not str:
        raise ActionRejected('INVALID_JSON')
    try:
        require(len(raw.encode('utf-8')) <= CONTRACT['transport']['max_request_bytes'],
                'request limit')
        action = json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)
        if type(action) is not dict or set(action) != {'tool', 'arguments'}:
            raise ActionRejected('INVALID_ACTION')
        if type(action['tool']) is not str or type(action['arguments']) is not dict:
            raise ActionRejected('INVALID_ACTION')
        if action['tool'] not in CONTRACT['tools']:
            raise ActionRejected('TOOL_REJECTED')
        # Reject overflow/nonfinite values even where arguments will be rejected.
        json.dumps(action, allow_nan=False)
        return action
    except json.JSONDecodeError as exc:
        raise ActionRejected('INVALID_JSON', {
            'message': MESSAGES['INVALID_JSON']+' Parser: '+exc.msg,
            'line': exc.lineno, 'column': exc.colno, 'position': exc.pos})
    except (UnicodeError, ValueError, RecursionError, RuntimeError):
        raise ActionRejected('INVALID_JSON')

def validate_arguments(action):
    tool, args = action['tool'], action['arguments']
    if set(args) != set(CONTRACT['tools'][tool]['required']) or any(type(v) is not str for v in args.values()):
        raise ActionRejected('ARGUMENTS_REJECTED', {'message':'Tool '+tool+' requires exactly these string arguments: '+(', '.join(CONTRACT['tools'][tool]['required']) or '(none)')+'. Received keys: '+(', '.join(args) or '(none)')+'.'})
    if tool == 'run_app' and args['operation'] not in CONTRACT['tools']['run_app']['operations']:
        raise ActionRejected('OPERATION_REJECTED', {'message':'Unknown operation '+repr(args['operation'])+'. Use one of: '+', '.join(CONTRACT['tools']['run_app']['operations'])+'.'})
    if tool == 'apply_profile' and args['profile'] not in CONTRACT['allowed_profiles']:
        raise ActionRejected('PROFILE_REJECTED', {'message':'Unknown profile '+repr(args['profile'])+'. Use one of: '+', '.join(CONTRACT['allowed_profiles'])+'.'})
    try:
        for value in args.values():
            value.encode('utf-8')
        if tool in ('list_files', 'read_file', 'write_file'):
            encoded = json.dumps({'operation': tool, 'arguments': args}, ensure_ascii=False).encode('utf-8')
            if len(encoded) > 131072:
                raise ActionRejected('REQUEST_LIMIT')
        if tool == 'finish' and len(args['summary'].encode('utf-8')) > 2000:
            raise ActionRejected('SUMMARY_LIMIT')
        if tool == 'write_file' and len(args['content'].encode('utf-8')) > 65536:
            raise ActionRejected('FILE_LIMIT')
    except UnicodeError:
        raise ActionRejected('INVALID_UTF8')

def output_view(row):
    limit = CONTRACT['budget']['agent_output_view_limit_bytes']
    raw = {name: base64.b64decode(row[name + '_base64']) for name in ('stdout', 'stderr')}
    total = sum(len(v) for v in raw.values())
    if total <= limit:
        shown = raw
    else:
        allocations = {name: min(len(data), limit // 2) for name, data in raw.items()}
        leftover = limit - sum(allocations.values())
        for name in ('stdout', 'stderr'):
            extra = min(leftover, len(raw[name]) - allocations[name])
            allocations[name] += extra
            leftover -= extra
        shown = {name: (data if len(data) <= allocations[name] else
                       data[:allocations[name] // 2] + data[-(allocations[name] - allocations[name] // 2):])
                 for name, data in raw.items()}
    return {'capture_completed': row.get('error') is None and row.get('utf8_valid') is True and type(row.get('exit_code')) is int and row['exit_code'] >= 0, 'exit_code': row['exit_code'], 'error': row['error'],
            'stdout': shown['stdout'].decode('utf-8', errors='replace'),
            'stderr': shown['stderr'].decode('utf-8', errors='replace'),
            'utf8_valid': row['utf8_valid'], 'truncated': total > limit,
            'captured_bytes': {name: len(v) for name, v in raw.items()},
            'view_bytes': sum(len(v) for v in shown.values()),
            'capture_hit_limit': row['error'] == 'OUTPUT_LIMIT'}

def application_command(snapshot, judge, argv):
    return judge.sandbox_command(snapshot, argv)

def tool_command(snapshot, paths, judge, worker_request=None, tag=None):
    original = judge.sandbox_command(snapshot, [], probe=True)
    prefix = original[:original.index('--')]
    index = prefix.index(snapshot['workspace'])
    require(prefix[index - 1] == '--ro-bind' and prefix[index + 1] == '/candidate',
            'Unexpected frozen candidate mount')
    prefix[index - 1] = '--bind'
    index = prefix.index('--tmpfs')
    require(prefix[index + 1] == '/tmp', 'Unexpected frozen tmp mount')
    prefix[index:index + 2] = ['--bind', str(paths['tmp']), '/tmp']
    index = prefix.index('HOME')
    require(prefix[index - 1] == '--setenv', 'Unexpected frozen HOME')
    prefix[index + 1] = '/home/candidate'
    index = prefix.index(str(judge.ROOT / 'native_probe.py'))
    prefix[index] = str(ROOT / 'file_worker.py')
    prefix[index + 1] = '/file_worker.py'
    prefix.extend(['--dir', '/home', '--bind', str(paths['home']), '/home/candidate',
                   '--bind', str(paths['cache']), '/cache', '--setenv', 'XDG_CACHE_HOME', '/cache',
                   '--setenv', 'TMPDIR', '/tmp'])
    if tag is not None:
        prefix.extend(['--setenv', 'EPISODE_RUN_TAG', tag])
    if worker_request is not None:
        prefix.extend(['--ro-bind', str(worker_request), '/request.json'])
    return prefix

def worker(snapshot, paths, judge, operation, arguments, records, timeout=10):
    request = {'operation': operation, 'arguments': arguments}
    with tempfile.TemporaryDirectory(prefix='typer-private-file-request-') as temp:
        path = Path(temp) / 'request.json'
        path.write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
        require(path.stat().st_size <= 131072, 'Trusted worker request exceeded limit')
        argv = [*tool_command(snapshot, paths, judge, worker_request=path), '--',
                '/usr/bin/python3', '-I', '-S', '/file_worker.py', '/request.json']
        row = judge.capture(argv, timeout=timeout)
    row['kind'] = 'file_worker/' + operation
    records.append(row)
    if not (row['error'] is None and row['exit_code'] == 0 and row['utf8_valid']):
        raise LocalFailure('FILE_WORKER','Trusted file worker failed; retained state must be evaluated',row)
    observation = json.loads(row['stdout'], object_pairs_hook=no_duplicates, parse_constant=reject_constant)
    require(type(observation) is dict and type(observation.get('ok')) is bool,
            'Invalid trusted worker observation')
    return observation

class Dispatcher:
    def __init__(self, state, paths, offline, judge, native_gate, records, case_id):
        require(os.getuid() != 0 and os.geteuid() != 0, 'Privileged UID blocks dispatcher')
        require(native_gate.get('available') is True and native_gate.get('writable_properties_passed') is True,
                'Both native gates are mandatory')
        self.case_id = case_id
        self.state, self.paths, self.offline, self.judge = state, paths, offline, judge
        self.records = records
        self.initial = offline.inspect_state(state)
        self.started = time.monotonic()
        self.actions = self.runs = self.installs = 0
        self.stopped = False
        self.stop_reason = None
        self.events = []
        self.tag = secrets.token_hex(16)
        self.integrity_baseline = self.trusted_files()
        self.valid_workspace()

    def trusted_files(self):
        paths = [*ROOT.glob('*.py'), *ROOT.glob('*.json'), ROOT / 'action.gbnf',
                 * (ROOT / 'prompts').rglob('*'), *self.offline.ROOT.parent.rglob('*')]
        return {str(p): digest(p) for p in paths if p.is_file() and '__pycache__' not in p.parts}

    def check_integrity(self):
        if self.trusted_files() != self.integrity_baseline:
            raise GlobalFailure('TRUSTED_INTEGRITY', 'Trusted files changed; session poisoned')

    def action_timeout(self):
        remaining = self.remaining()
        if remaining <= 0:
            self.stopped, self.stop_reason = True, 'watchdog'
            raise ActionRejected('WALL_BUDGET_EXHAUSTED')
        # Frozen judge uses integer RLIMIT_CPU values in its child preexec.
        # Round upward only for workers; a late return is handled by the
        # episode watchdog, never by changing the CLI's ten-second timeout.
        return min(10, math.ceil(remaining))

    def application_timeout(self):
        timeout = CONTRACT['budget']['application_timeout_seconds']
        if self.remaining() <= 0:
            self.stopped, self.stop_reason = True, 'watchdog'
            raise ActionRejected('INSUFFICIENT_APPLICATION_TIME')
        return timeout

    def remaining(self):
        return CONTRACT['budget']['watchdog_seconds'] - (time.monotonic() - self.started)

    def valid_workspace(self):
        observation = worker(self.snapshot(), self.paths, self.judge, 'snapshot', {}, self.records)
        require(observation['ok'], 'Workspace violates bounded contract')
        return observation

    def snapshot(self):
        # File-tool paths are never resolved here. The frozen installer/judge
        # inspect only the complete state bound by the trusted parent.
        return {'workspace': str(self.state / 'workspace'), 'environment': self.environment()}

    def environment(self):
        active = json.loads((self.state / 'active.json').read_text())
        name = active['directory']
        require(type(name) is str and name.startswith('env-') and '/' not in name and '..' not in name,
                'Invalid parent-owned environment selection')
        return str(self.state / 'environments' / name)

    def dispatch(self, raw, *, rejection=None):
        if self.stopped:
            return explain({'ok': False, 'error': 'SESSION_STOPPED'})
        if self.remaining() <= 0:
            self.stopped, self.stop_reason = True, 'watchdog'
            return explain({'ok': False, 'error': 'WALL_BUDGET_EXHAUSTED'})
        self.actions += 1
        event = {'index': self.actions, 'request': raw, 'started_monotonic': time.monotonic()}
        try:
            self.check_integrity()
            if rejection is not None:
                if not isinstance(rejection,ActionRejected):raise TypeError("Invalid native rejection type")
                raise rejection
            action = parse_action(raw)
            tool, args = action['tool'], action['arguments']
            if tool == 'run_app':
                self.runs += 1
                if self.runs > CONTRACT['budget']['max_run_app_actions']:
                    self.stopped, self.stop_reason = True, 'run_app_budget'
                    raise ActionRejected('RUN_APP_BUDGET_EXHAUSTED')
            if tool == 'apply_profile':
                self.installs += 1
                if self.installs > CONTRACT['budget']['max_install_actions']:
                    self.stopped, self.stop_reason = True, 'install_budget'
                    raise ActionRejected('INSTALL_BUDGET_EXHAUSTED')
            validate_arguments(action)
            if tool in ('list_files', 'read_file', 'write_file'):
                response = worker(self.snapshot(), self.paths, self.judge, tool, args, self.records,
                                  timeout=self.action_timeout())
            elif tool == 'run_app':
                self.valid_workspace()
                snapshot = self.offline.inspect_state(self.state)
                argv = application_command(snapshot, self.judge, CONTRACT['tools']['run_app']['operations'][args['operation']])
                capture_index=len(self.records)
                self.records.append({'kind':'run_app/'+args['operation'],'status':'CAPTURE_PENDING','process_launched':None})
                row = self.judge.capture(argv, timeout=self.application_timeout())
                row['kind'] = 'run_app/' + args['operation']
                self.records[capture_index]=row
                if row['error']=='LAUNCH_FAILED':raise LocalFailure('APPLICATION_LAUNCHER','Application launcher unavailable',row)
                response = {'ok': True, **output_view(row)} # ok is private transport accounting.
                self.valid_workspace()
            elif tool == 'apply_profile':
                before = self.valid_workspace()
                changed = self.offline.apply_profile(self.state, args['profile'])
                require(self.valid_workspace() == before, 'Offline installation changed source')
                response = {'ok': True, 'profile': changed['profile'], 'versions': changed['versions']}
            else:
                response = self.finish_action(args)
            response=explain(response)
            self.check_integrity()
        except ActionRejected as exc:
            response = {'ok': False, 'error': str(exc)}
            if exc.detail is not None:
                response['detail'] = dict(exc.detail)
            response=explain(response)
        except Exception:
            self.stopped, self.stop_reason = True, 'infrastructure_failure'
            response = {'ok': False, 'error': 'INFRASTRUCTURE_FAILURE'}
            raise
        finally:
            event['elapsed_seconds'] = time.monotonic() - event['started_monotonic']
            event['counters'] = {'actions': self.actions, 'run_app_attempts': self.runs,
                                 'install_attempts': self.installs}
            if 'response' in locals():
                event['response'] = response
            self.events.append(event)
        if not self.stopped and self.actions >= CONTRACT['budget']['max_actions']:
            self.stopped, self.stop_reason = True, 'action_budget'
        if not self.stopped and self.remaining() <= 0:
            self.stopped, self.stop_reason = True, 'watchdog'
        return response

    def finish_action(self, args):
        self.stopped, self.stop_reason = True, 'finish'
        return {'ok': True, 'finished': True}

    def public_description(self):
        active = self.offline.inspect_state(self.state)
        signatures = {name: {'arguments': spec['required']} for name, spec in CONTRACT['tools'].items()}
        signatures['run_app']['operations'] = CONTRACT['tools']['run_app']['operations']
        return {'prompt': (ROOT / 'prompts' / (self.case_id + '.system.txt')).read_text(encoding='utf-8'), 'versions': active['versions'],
                'tools': signatures, 'allowed_profiles': CONTRACT['allowed_profiles'],
                'budget': CONTRACT['budget']}
