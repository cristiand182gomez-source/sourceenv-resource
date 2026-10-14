"""Private lifecycle evidence. Never insert these records into agent feedback."""
import copy
import time

EPISODE_WATCHDOG = 14400
PREFLIGHT_WATCHDOG = 1800
STARTUP_SECONDS = 240
RECOVERY_SECONDS = 120
GRADING_SECONDS = 180
MAX_TRANSPORT_SECONDS = EPISODE_WATCHDOG + STARTUP_SECONDS + RECOVERY_SECONDS


class LocalFailure(RuntimeError):
    def __init__(self, kind, detail, evidence=None):
        super().__init__(detail)
        self.kind, self.scope, self.evidence = kind, 'LOCAL', evidence or {}


class GlobalFailure(LocalFailure):
    def __init__(self, kind, detail, evidence=None):
        super().__init__(kind, detail, evidence)
        self.scope = 'GLOBAL'


class OwnDeadline(LocalFailure):
    """Only the deadline owner creates this; TimeoutError alone never qualifies."""
    def __init__(self, evidence):
        super().__init__('OWN_WATCHDOG', 'Owned absolute deadline fired', evidence)


def fault(exc):
    return {'scope': getattr(exc, 'scope', 'UNKNOWN'),
            'kind': getattr(exc, 'kind', 'UNCLASSIFIED'),
            'type': type(exc).__name__, 'detail': str(exc),
            'evidence': copy.deepcopy(getattr(exc, 'evidence', {}))}


def deadline_proof(deadline, phase, clock=time.monotonic, owner='serial_adapter'):
    now = clock()
    if now < deadline:
        raise GlobalFailure('DEADLINE_PROOF', 'A watchdog was claimed before its deadline')
    return {'owner': owner, 'phase': phase, 'deadline_monotonic': deadline,
            'observed_monotonic': now, 'deadline_fired': True}


def valid_deadline(proof, deadline):
    return (type(proof) is dict and proof.get('owner') in ('serial_adapter', 'parent_http', 'preflight')
            and proof.get('deadline_fired') is True
            and type(proof.get('deadline_monotonic')) in (int, float)
            and abs(proof['deadline_monotonic'] - deadline) < .001
            and type(proof.get('observed_monotonic')) in (int, float)
            and proof['observed_monotonic'] >= deadline)


def require_closure(proof, session=None):
    required = ('model_process_terminated', 'model_job_closed', 'server_port_closed', 'slot_directory_empty',
                'no_active_request', 'closure_verified')
    if (not isinstance(proof, dict) or proof.get('status') != 'CLOSED'
            or not all(proof.get(k) is True for k in required)
            or session is not None and proof.get('session') != session):
        raise GlobalFailure('UNCONFIRMED_CANCELLATION', 'Old model session closure is not verified', proof)
    if proof.get('global_failure') is True:
        raise GlobalFailure('WINDOWS_GLOBAL_FAILURE', 'Windows detected a compromised or unknown session', proof)
    return proof


class CompletionLedger:
    def __init__(self):
        self.rows = []

    def begin(self, cap):
        assert type(cap) is int and 0 < cap <= 2048
        row = {'index': len(self.rows)+1, 'requested_cap': cap,
               'completion_started': None, 'known_tokens': None}
        self.rows.append(row)
        return row

    def record(self):
        known = sum(r['known_tokens'] for r in self.rows if type(r['known_tokens']) is int)
        unknown = [r for r in self.rows if r['known_tokens'] is None and r['completion_started'] is not False]
        return {'model_calls_attempted': len(self.rows), 'known_generated_tokens': known,
                'additional_tokens_upper_bound': sum(r['requested_cap'] for r in unknown),
                'generated_tokens_lower_bound': known,
                'generated_tokens_upper_bound': known + sum(r['requested_cap'] for r in unknown),
                'generation_accounting_complete': not unknown,
                'calls': copy.deepcopy(self.rows), 'unknown_costs_are_zero': False}


def backend_cost(backend, fallback=None):
    return copy.deepcopy(backend.cost_record() if hasattr(backend, 'cost_record') else fallback or {})


def resolve_watchdog(conversation, closure):
    """Classification follows cancellation AND retained-state verification."""
    if not conversation.get('watchdog'):
        return False
    require_closure(closure)
    proof = conversation['watchdog']
    if (not valid_deadline(proof, conversation['deadline_monotonic'])
            or proof.get('retained_state_verified') is not True):
        raise GlobalFailure('UNVERIFIED_RETAINED_STATE', 'Deadline or pre-call state evidence is incomplete')
    return True
