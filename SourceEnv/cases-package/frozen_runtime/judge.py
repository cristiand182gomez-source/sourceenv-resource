"""Trusted external finite judge. Candidate code runs only in Bubblewrap."""

from pathlib import Path
import sys

# With -I -S Python omits the script directory. Add only this trusted directory;
# the application workspace and site-packages are never added to judge sys.path.
ROOT = Path(__file__).resolve().parent
if not (sys.flags.isolated and sys.flags.no_site
        and Path(sys.executable).resolve() == Path('/usr/bin/python3').resolve()):
    raise SystemExit('Use /usr/bin/python3 -I -S judge.py outside candidate Python')
sys.path.insert(0, str(ROOT))

import base64
from hashlib import sha256
import json
import os
import resource
import selectors
import shutil
import signal
import socket
import subprocess
import tempfile
import time

from offline import policy, require


def capture(argv, payload=b'', timeout=None):
    p = policy()
    timeout = timeout or p['timeout_seconds']
    limit = p['output_limit_bytes']
    started = time.monotonic()
    streams = {'stdout': bytearray(), 'stderr': bytearray()}
    require(len(payload) < 8192, 'Unexpected input size')
    def limits():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (timeout + 1, timeout + 2))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True,
                                   cwd=ROOT, env={'PATH': '/usr/bin:/bin'}, preexec_fn=limits)
    except OSError as exc:
        return {'argv': argv, 'exit_code': None, 'error': 'LAUNCH_FAILED',
                'stdout': '', 'stderr': str(exc), 'utf8_valid': True}
    # Payloads are bounded trusted-probe requests; applications get empty stdin.
    try:
        process.stdin.write(payload)
        process.stdin.close()
    except BrokenPipeError:
        pass
    selector = selectors.DefaultSelector()
    for stream, label in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, label)
    error = None
    try:
        while selector.get_map():
            if time.monotonic() - started > timeout:
                error = 'TIMEOUT'
                break
            for key, _ in selector.select(0.05):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                label = key.data
                room = limit - len(streams[label])
                streams[label].extend(chunk[:room])
                if len(chunk) > room:
                    error = 'OUTPUT_LIMIT'
                    break
            if error:
                break
        if error:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=max(0.1, timeout - (time.monotonic() - started)))
        except subprocess.TimeoutExpired:
            error = 'TIMEOUT'
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            stream.close()
    result = {'argv': argv, 'exit_code': process.returncode, 'error': error,
              'elapsed_seconds': time.monotonic() - started, 'utf8_valid': True}
    for label, raw in streams.items():
        result[label + '_base64'] = base64.b64encode(raw).decode('ascii')
        try:
            result[label] = raw.decode('utf-8')
        except UnicodeError:
            result['utf8_valid'] = False
            result[label] = raw.decode('utf-8', errors='backslashreplace')
    return result


def sandbox_command(snapshot, argv, probe=False):
    binary = shutil.which('bwrap')
    if binary is None:
        raise RuntimeError('Bubblewrap unavailable')
    require(not ROOT.is_relative_to('/usr'), 'Evaluator would be exposed by /usr mount')
    require(not ROOT.is_relative_to(snapshot['workspace'])
            and not ROOT.is_relative_to(snapshot['environment']), 'Evaluator inside candidate state')
    command = [binary, '--unshare-all', '--unshare-user', '--die-with-parent',
               '--new-session', '--clearenv', '--cap-drop', 'ALL',
               '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'HOME', '/tmp/home',
               '--setenv', 'TMPDIR', '/tmp/tmp', '--setenv', 'XDG_CACHE_HOME', '/tmp/cache',
               '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'LC_ALL', 'C.UTF-8',
               '--setenv', 'TZ', 'UTC', '--setenv', 'PYTHONHASHSEED', '0',
               '--setenv', 'PYTHONNOUSERSITE', '1', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1',
               '--setenv', 'PYTHONIOENCODING', 'utf-8', '--setenv', 'NO_COLOR', '1',
               '--setenv', 'COLUMNS', '100', '--setenv', 'TERM', 'dumb',
               '--ro-bind', '/usr', '/usr']
    for folder in ('/lib', '/lib64'):
        if Path(folder).exists():
            command.extend(['--ro-bind', folder, folder])
    command.extend(['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/tmp/home', '--dir', '/tmp/tmp', '--dir', '/tmp/cache',
                    '--ro-bind', snapshot['workspace'], '/candidate',
                    '--ro-bind', snapshot['environment'], '/environment', '--chdir', '/candidate'])
    if probe:
        command.extend(['--ro-bind', str(ROOT / 'native_probe.py'), '/probe.py',
                        '--', '/usr/bin/python3', '-I', '-S', '/probe.py'])
    else:
        command.extend(['--', '/environment/bin/python', '/candidate/app.py', *argv])
    return command


def native_preflight(snapshot):
    record = {'available': False, 'checks_executed': False, 'application_processes_launched': 0,
              'agent_gate': 'BLOCKED', 'process_limit': 'UNVERIFIED_FOR_PRIVILEGED_UID', 'records': []}
    binary = shutil.which('bwrap')
    if binary:
        record['bwrap_sha256'] = sha256(Path(binary).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='typer-private-probe-') as temp, socket.socket() as listener:
        marker = Path(temp) / 'reference-marker'
        marker.write_text('not mounted')
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        request = {'evaluator': str(ROOT / 'judge.py'), 'reference_marker': str(marker),
                   'parent_pid': os.getpid(), 'pid_namespace': os.readlink('/proc/self/ns/pid'),
                   'net_namespace': os.readlink('/proc/self/ns/net'),
                   'port': listener.getsockname()[1]}
        for phase in (1, 2):
            try:
                row = capture(sandbox_command(snapshot, [], probe=True),
                              json.dumps(dict(request, phase=phase)).encode())
            except RuntimeError as exc:
                record['detail'] = str(exc)
                break
            record['records'].append(row)
            if row['error'] or row['exit_code'] != 0:
                break
            try:
                observation = json.loads(row['stdout'])
                checks = observation['checks']
                row['observation'] = observation
            except (ValueError, KeyError):
                record['detail'] = 'Invalid trusted probe output'
                break
            record['checks_executed'] = True
            if not checks or not all(value is True for value in checks.values()):
                record['detail'] = 'Native property check failed'
                break
        else:
            record['available'] = True
    record['status'] = ('NATIVE_SAMPLED_CHECKS_PASSED_AGENT_GATE_BLOCKED' if record['available']
                        else 'BLOCKED_SANDBOX_UNAVAILABLE')
    return record

