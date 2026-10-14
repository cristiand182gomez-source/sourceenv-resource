"""Trusted bounded file worker. CLI runs only under -I -S inside Bubblewrap."""

import base64
import errno
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import secrets
import socket
import stat
import sys

FILE_LIMIT = 65536
FILE_COUNT = 64
TOTAL_LIMIT = 1048576
DIR_COUNT = 128


class Rejected(Exception):
    def __init__(self, code):
        self.code = code


def require(value, code):
    if not value:
        raise Rejected(code)


def parts(path):
    require(type(path) is str and bool(path), 'PATH_REJECTED')
    try:
        encoded = path.encode('utf-8')
    except UnicodeError:
        raise Rejected('PATH_REJECTED')
    value = path.split('/')
    require(len(encoded) <= 1024 and len(value) <= 16 and '\\' not in path
            and '\0' not in path and all(p not in ('', '.', '..') for p in value)
            and all(len(p.encode('utf-8')) <= 255 for p in value), 'PATH_REJECTED')
    return value


def directory(name, fd=None):
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                   dir_fd=fd)


def regular_bytes(name, fd, maximum):
    before = os.stat(name, dir_fd=fd, follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'NONREGULAR_REJECTED')
    require(before.st_size <= maximum, 'FILE_LIMIT')
    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     dir_fd=fd)
    try:
        actual = os.fstat(handle)
        require(stat.S_ISREG(actual.st_mode) and actual.st_nlink == 1
                and (actual.st_dev, actual.st_ino) == (before.st_dev, before.st_ino),
                'WORKSPACE_CHANGED')
        raw = bytearray()
        while len(raw) <= maximum:
            chunk = os.read(handle, min(65536, maximum + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        require(len(raw) <= maximum, 'FILE_LIMIT')
        after = os.fstat(handle)
        require(len(raw) == actual.st_size and actual.st_size == after.st_size
                and actual.st_mtime_ns == after.st_mtime_ns, 'WORKSPACE_CHANGED')
        return bytes(raw)
    finally:
        os.close(handle)


def inventory(root_fd):
    files, dirs = {}, []
    total = 0
    def walk(fd, prefix):
        nonlocal total
        for name in sorted(os.listdir(fd)):
            relative = prefix + name
            parts(relative)
            st = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(st.st_mode):
                dirs.append(relative)
                require(len(dirs) <= DIR_COUNT, 'WORKSPACE_LIMIT')
                child = directory(name, fd)
                try:
                    walk(child, relative + '/')
                finally:
                    os.close(child)
            else:
                require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, 'NONREGULAR_REJECTED')
                require(len(files) < FILE_COUNT and total + st.st_size <= TOTAL_LIMIT,
                        'WORKSPACE_LIMIT')
                data = regular_bytes(name, fd, FILE_LIMIT)
                total += len(data)
                files[relative] = data
    walk(root_fd, '')
    return files, dirs, total


def parent_fd(root_fd, components, dirs=None):
    handle = os.dup(root_fd)
    created = 0
    try:
        for part in components[:-1]:
            try:
                child = directory(part, handle)
            except FileNotFoundError:
                require(dirs is not None and len(dirs) + created < DIR_COUNT,
                        'PATH_REJECTED' if dirs is None else 'WORKSPACE_LIMIT')
                os.mkdir(part, 0o700, dir_fd=handle)
                created += 1
                child = directory(part, handle)
            os.close(handle)
            handle = child
        return handle
    except Exception:
        os.close(handle)
        raise


def operate(root, operation, arguments):
    fd = directory(root)
    try:
        files, dirs, total = inventory(fd)
        if operation == 'list_files':
            return {'ok': True, 'files': [{'path': name, 'bytes': len(data), 'type': 'file'}
                                         for name, data in files.items()]}
        if operation == 'snapshot':
            return {'ok': True, 'files': {name: {'sha256': sha256(data).hexdigest(),
                    'bytes': len(data), 'base64': base64.b64encode(data).decode('ascii')}
                    for name, data in files.items()}, 'directories': dirs, 'total_bytes': total}
        components = parts(arguments['path'])
        if operation == 'read_file':
            parent = parent_fd(fd, components)
            try:
                data = regular_bytes(components[-1], parent, FILE_LIMIT)
                text = data.decode('utf-8')
            finally:
                os.close(parent)
            return {'ok': True, 'path': arguments['path'], 'content': text, 'bytes': len(data)}
        require(operation == 'write_file', 'TOOL_REJECTED')
        require(type(arguments['content']) is str, 'ARGUMENTS_REJECTED')
        data = arguments['content'].encode('utf-8')
        require(len(data) <= FILE_LIMIT, 'FILE_LIMIT')
        old = files.get(arguments['path'])
        require(len(files) + (old is None) <= FILE_COUNT
                and total - (len(old) if old is not None else 0) + len(data) <= TOTAL_LIMIT,
                'WORKSPACE_LIMIT')
        parent = parent_fd(fd, components, dirs)
        temporary = '.write-' + secrets.token_hex(16)
        try:
            try:
                st = os.stat(components[-1], dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, 'NONREGULAR_REJECTED')
            output = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
            with os.fdopen(output, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, components[-1], src_dir_fd=parent, dst_dir_fd=parent)
            os.fsync(parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass
            os.close(parent)
        return {'ok': True, 'path': arguments['path'], 'bytes': len(data)}
    finally:
        os.close(fd)


def readonly(path):
    try:
        Path(path).write_bytes(b'bounded interface probe')
        return False
    except OSError as exc:
        return exc.errno == errno.EROFS


def hidden(path):
    try:
        Path(path).stat()
        return False
    except OSError as exc:
        return exc.errno == errno.ENOENT


def native_properties(request):
    status = Path('/proc/self/status').read_text()
    capabilities = int(next(line.split()[1] for line in status.splitlines()
                            if line.startswith('CapEff:')), 16)
    with socket.socket() as connection:
        connection.settimeout(0.3)
        try:
            connection.connect(('127.0.0.1', request['listener_port']))
            unreachable = False
        except OSError:
            unreachable = True
    checks = {
        'nonprivileged_uid': os.getuid() != 0 and os.geteuid() != 0,
        'zero_capabilities': capabilities == 0,
        'nproc64': resource.getrlimit(resource.RLIMIT_NPROC) == (64, 64),
        'cwd_candidate': os.getcwd() == '/candidate',
        'private_home_cache': os.environ.get('HOME') == '/home/candidate'
                             and os.environ.get('XDG_CACHE_HOME') == '/cache',
        'usr_readonly': readonly('/usr/.interface-probe'),
        'environment_readonly': readonly('/environment/.interface-probe'),
        'worker_readonly': readonly('/file_worker.py'),
        'request_readonly': readonly('/request.json'),
        'trusted_paths_hidden': all(hidden(path) for path in request['private_paths']),
        'pid_distinct': os.readlink('/proc/self/ns/pid') != request['pid_namespace'],
        'net_distinct': os.readlink('/proc/self/ns/net') != request['net_namespace'],
        'parent_pid_hidden': hidden('/proc/' + str(request['parent_pid'])),
        'parent_listener_unreachable': unreachable,
    }
    return {'ok': all(checks.values()), 'checks': checks, 'uid': os.getuid()}


def main():
    require(sys.flags.isolated and sys.flags.no_site and os.getcwd() == '/candidate'
            and len(sys.argv) == 2 and sys.argv[1] == '/request.json', 'TRUSTED_ENTRY_REQUIRED')
    raw = Path('/request.json').read_bytes()
    require(len(raw) <= 131072, 'REQUEST_LIMIT')
    request = json.loads(raw)
    try:
        if request['operation'] == 'native_properties':
            response = native_properties(request['arguments'])
        elif request['operation'] == 'snapshot_all':
            response = {'ok': True, 'state': {
                name: operate(root, 'snapshot', {}) for name, root in
                [('workspace', '/candidate'), ('home', '/home/candidate'),
                 ('tmp', '/tmp'), ('cache', '/cache')]}}
        else:
            response = operate('/candidate', request['operation'], request['arguments'])
    except Rejected as exc:
        response = {'ok': False, 'error': exc.code}
    except FileNotFoundError:
        response = {'ok': False, 'error': 'FILE_NOT_FOUND'}
    except UnicodeError:
        response = {'ok': False, 'error': 'INVALID_UTF8'}
    except OSError:
        response = {'ok': False, 'error': 'FILESYSTEM_REJECTED'}
    print(json.dumps(response, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
