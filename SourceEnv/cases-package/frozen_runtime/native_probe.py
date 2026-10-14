"""Fixed native-property probe. Never executed outside Bubblewrap."""

import errno
import json
import os
from pathlib import Path
import socket
import sys


def inaccessible(path):
    try:
        Path(path).read_bytes()
        return False
    except OSError as exc:
        return exc.errno == errno.ENOENT


def readonly(path):
    try:
        Path(path).write_bytes(b'controlled native probe')
        return False
    except OSError as exc:
        return exc.errno == errno.EROFS


request = json.load(sys.stdin)
marker = Path('/tmp/typer-probe-marker')
checks = {
    'evaluator_inaccessible': inaccessible(request['evaluator']),
    'reference_marker_inaccessible': inaccessible(request['reference_marker']),
    'workspace_readonly': readonly('/candidate/.native-probe'),
    'environment_readonly': readonly('/environment/.native-probe'),
    'usr_readonly': readonly('/usr/.native-probe'),
    'pid_namespace_distinct': os.readlink('/proc/self/ns/pid') != request['pid_namespace'],
    'net_namespace_distinct': os.readlink('/proc/self/ns/net') != request['net_namespace'],
    'parent_pid_invisible': not Path('/proc/' + str(request['parent_pid'])).exists(),
}
with socket.socket() as connection:
    connection.settimeout(0.3)
    checks['parent_listener_inaccessible'] = connection.connect_ex(('127.0.0.1', request['port'])) != 0
if request['phase'] == 1:
    marker.write_bytes(b'phase one')
    checks['tmp_writable'] = marker.read_bytes() == b'phase one'
else:
    checks['tmp_fresh'] = not marker.exists()
print(json.dumps({'checks': checks, 'uid': os.getuid()}))
