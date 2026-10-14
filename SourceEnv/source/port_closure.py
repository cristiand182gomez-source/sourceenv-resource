"""Administrative TCP closure proof, shared by both Windows owners.

Only explicit refusal proves closure. No HTTP payload, model retry or candidate
probe. An accepting listener may be polled while it closes; an unresolved
connect is retained as indeterminate, never treated as refusal.
"""
import errno
import socket
import time

ATTEMPT_SECONDS = 3.0
POLL_SECONDS = 0.05
MAX_TCP_ATTEMPTS = 40


def probe_tcp_closed(host, port, deadline):
    start = time.monotonic()
    proof = {'host': host, 'port': port, 'deadline_monotonic': deadline,
             'attempt_seconds_maximum': ATTEMPT_SECONDS,
             'maximum_attempts': MAX_TCP_ATTEMPTS, 'attempts': [],
             'status': 'INDETERMINATE', 'closed': False, 'reason': 'deadline_exhausted'}
    while len(proof['attempts']) < MAX_TCP_ATTEMPTS and time.monotonic() < deadline:
        began = time.monotonic()
        timeout = min(ATTEMPT_SECONDS, deadline - began)
        if timeout <= 0:
            break
        row = {'index': len(proof['attempts']) + 1, 'started_monotonic': began,
               'timeout_seconds': timeout, 'result': 'INDETERMINATE',
               'errno': None, 'winerror': None, 'socket_closed': False}
        conn = None
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(timeout)
            conn.connect((host, port))
            row['result'] = 'OPEN'
        except OSError as exc:
            row.update(error_type=type(exc).__name__, error=str(exc),
                       errno=exc.errno, winerror=getattr(exc, 'winerror', None))
            if exc.errno in (errno.ECONNREFUSED, 10061) or getattr(exc, 'winerror', None) == 10061:
                row['result'] = 'REFUSED'
        finally:
            if conn is not None:
                try:
                    conn.close()
                    row['socket_closed'] = True
                except OSError as exc:
                    row['close_error'] = repr(exc)
            row['completed_monotonic'] = time.monotonic()
            row['elapsed_seconds'] = row['completed_monotonic'] - began
            proof['attempts'].append(row)
        if not row['socket_closed'] or row['completed_monotonic'] > deadline:
            # A successful connection is positive evidence of an open port,
            # even if the scheduler returned late. A late refusal cannot prove
            # closure within the deadline.
            proof['status'] = 'OPEN' if row['result'] == 'OPEN' and row['socket_closed'] else 'INDETERMINATE'
            proof['reason'] = 'socket_close_unconfirmed' if not row['socket_closed'] else 'deadline_exhausted'
            break
        if row['result'] == 'REFUSED':
            proof.update(status='CLOSED', closed=True, reason='explicit_connection_refused')
            break
        if row['result'] == 'INDETERMINATE':
            proof['status'] = 'INDETERMINATE'
            proof['reason'] = 'unresolved_connect'
            break
        proof.update(status='OPEN', reason='listener_accepts_connection')
        time.sleep(min(POLL_SECONDS, max(0, deadline - time.monotonic())))
    else:
        if len(proof['attempts']) == MAX_TCP_ATTEMPTS:
            proof['reason'] = 'tcp_attempt_budget_exhausted'
    proof['completed_monotonic'] = time.monotonic()
    proof['elapsed_seconds'] = proof['completed_monotonic'] - start
    proof['tcp_connect_attempts'] = len(proof['attempts'])
    return proof
