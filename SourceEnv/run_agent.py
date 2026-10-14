"""Evaluate a native-tool agent in Debian/Bubblewrap; no model process owner."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'source')]
from critical_guards import require_unoptimized, ensure
require_unoptimized()
import argparse, copy, datetime, hashlib, json, math, os, shutil, socket, time
from endpoint_backend import EndpointBackend, ScriptedBackend, context_accounting, APPROXIMATE_CONTEXT_LIMIT

ORDER = ['EH-API', 'SC-BALANCE', 'H-RC0', 'EC-MISSING', 'SH-FLAG', 'EH-RENDERER', 'SC-SORT', 'H-RC2', 'EC-SYMBOL', 'SH-FORMAT']


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def arguments(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', default='http://127.0.0.1:8080/v1')
    p.add_argument('--model', default='sourceenv-agent')
    p.add_argument('--api-key', default=os.environ.get('OPENAI_API_KEY'), help='Optional; prefer OPENAI_API_KEY. Never passed to the candidate.')
    p.add_argument('--protocol', choices=['llama-cpp', 'openai'], default='llama-cpp')
    p.add_argument('--tokenizer-command', help='Optional exact counter for generic OpenAI endpoints; absent: prior usage + UTF-8 bytes/3, 85%% cutoff. JSON stdin/stdout, no shell.')
    p.add_argument('--temperature', type=float, default=1.0)
    p.add_argument('--top-k', type=int, default=64, help='Use 0 to omit the nonstandard parameter in generic OpenAI mode.')
    p.add_argument('--top-p', type=float, default=0.95)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--repeat-penalty', type=float, default=1.0)
    p.add_argument('--presence-penalty', type=float, default=0.0)
    p.add_argument('--frequency-penalty', type=float, default=0.0)
    p.add_argument('--min-p', type=float, default=0.0)
    p.add_argument('--dry-multiplier', type=float, default=0.0)
    p.add_argument('--xtc-probability', type=float, default=0.0)
    p.add_argument('--cache-prompt', action=argparse.BooleanOptionalAction, default=True)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--wheelhouse', required=True, type=Path)
    p.add_argument('--fixtures', nargs='+', choices=ORDER, help='Optional subset for integration checks, kept in benchmark order; default all ten.')
    p.add_argument('--backend', choices=['endpoint', 'scripted'], default='endpoint')
    p.add_argument('--control', choices=['reference', 'noop'], default='reference', help='Used only with --backend scripted.')
    args = p.parse_args(argv)
    values = [getattr(args, name) for name in ['temperature', 'top_p', 'repeat_penalty', 'presence_penalty', 'frequency_penalty', 'min_p', 'dry_multiplier', 'xtc_probability']]
    ensure(all(math.isfinite(v) for v in values) and args.temperature >= 0 and 0 < args.top_p <= 1 and args.top_k >= 0 and
           args.repeat_penalty > 0 and 0 <= args.min_p <= 1 and args.dry_multiplier >= 0 and 0 <= args.xtc_probability <= 1, 'SAMPLING_ARGUMENTS')
    ensure(not args.fixtures or len(set(args.fixtures)) == len(args.fixtures), 'DUPLICATE_FIXTURE')
    return args


def run_one(case, args, out, backend, ledger, runtime):
    reproduce, episode = runtime
    offline, judge, oracle = episode.offline, episode.judge, episode.oracle
    out.mkdir(parents=True, exist_ok=False)
    report = {'case_id': case['case_id'], 'configuration': args.model if args.backend == 'endpoint' else 'SCRIPTED',
              'control': args.control if args.backend == 'scripted' else None,
              'execution_origin': 'physical_FC' if args.backend == 'endpoint' else 'scripted_FC',
              'context_accounting': backend.context_accounting,
              'preflights': 0, 'agent_episodes': 1, 'model_processes_started_by_runner': 0,
              'cleanup_performed': False, 'primary_availability': 'INVALID', 'final_task_pass': None,
              'events': [], 'actions': 0, 'conversation': {'messages': [], 'turns': []},
              'derived_BASE': {'primary_availability': 'INVALID', 'final_task_pass': None, 'terminal_action_index': 0}}
    d = adapter = checkpoint = baseline = None
    started = time.monotonic()
    failure = None
    old_rpc = episode.rpc
    try:
        ledger['fresh_states'] += 1
        ensure(ledger['fresh_states'] <= ledger['limits']['fresh_states'], 'FRESH_STATE_LIMIT')
        initial = offline.prepare(out / 'state', ROOT / 'cases-package/cases' / case['case_id'] / 'initial.py', case['initial_profile'])
        ensure(initial['source_files'] == {'app.py': case['source_sha256']}, 'INITIAL_SOURCE')
        paths = {n: out / n for n in ['home', 'tmp', 'cache']}
        for path in paths.values(): path.mkdir()
        records = []
        gate = judge.native_preflight(initial)
        save(out / 'isolation.json', gate)
        ensure(gate['available'], 'NATIVE_ISOLATION_BLOCKED')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            properties = episode.worker(initial, paths, judge, 'native_properties', {
                'parent_pid': os.getpid(), 'pid_namespace': os.readlink('/proc/self/ns/pid'),
                'net_namespace': os.readlink('/proc/self/ns/net'), 'listener_port': listener.getsockname()[1],
                'private_paths': [str(ROOT / 'source'), str(out / 'episode.json')]}, records)
        ensure(properties['ok'] and properties['checks'] and all(properties['checks'].values()), 'WRITABLE_ISOLATION_BLOCKED')
        gate['writable_properties_passed'] = True
        d = episode.CoverageDispatcher(out / 'state', paths, offline, judge, gate, records,
            case['case_id'], case=case, oracle=oracle, policy='FINISH-COVERAGE')
        baseline = episode.grade_case(d, case, offline.policy(), oracle, out / 'initial-score.json')
        ensure(baseline['checks'] == case['initial_checks_expected'], 'INITIAL_CONTRACT_CHANGED')
        report['initial_score'] = baseline
        d.started = time.monotonic()  # Same r3 episode clock; setup is separate.
        report['setup_seconds'] = d.started - started
        adapter = episode.Adapter(d, case['case_id'], report['configuration'], initial)
        checkpoint = episode.PrefixCheckpoint(out); checkpoint.adapter = adapter; d.before_finish = checkpoint.capture
        episode.rpc = backend.rpc
        backend.case_id = case['case_id']
        report['conversation'] = adapter.run(out)
    except Exception as exc:
        # Do not log arbitrary exception strings which could echo an API key.
        failure = type(exc).__name__ + ':' + str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        report['error'] = failure
        report['remote_close_proved'] = False
        report['global_stop_required'] = True
        if d is not None:
            d.stopped = True; d.stop_reason = 'infrastructure_failure'
    finally:
        episode.rpc = old_rpc
        if adapter is not None:
            report['conversation'] = {'messages': copy.deepcopy(adapter.messages), 'turns': copy.deepcopy(adapter.turns),
                'stop_reason': d.stop_reason, 'generated_tokens': adapter.generated, 'model_replies_received': adapter.replies,
                'synthetic_not_model_tokenization': args.backend == 'scripted'}
        if d is not None:
            report.update(events=d.events, actions=d.actions, run_app_attempts=d.runs, profile_change_attempts=d.installs,
                stop_reason=d.stop_reason, generated_tokens=adapter.generated if adapter else 0,
                model_calls=adapter.replies if adapter and args.backend == 'endpoint' else 0,
                scripted_replies=adapter.replies if adapter and args.backend == 'scripted' else 0,
                coverage_metrics=d.coverage_record(), records=d.records)
            save(out / 'episode.partial.json', report)
            if checkpoint is not None and baseline is not None:
                try:
                    episode.settle(report, d, checkpoint, case, baseline, out, failure)
                except Exception as exc:
                    report.update(primary_availability='INVALID', final_task_pass=None,
                        global_stop_required=True, grading_error=type(exc).__name__,
                        derived_BASE={'primary_availability': 'INVALID', 'final_task_pass': None,
                                      'terminal_action_index': d.actions, 'stop_reason': d.stop_reason})
                    failure = type(exc).__name__
                ledger['checkpoint_copies'] += bool(checkpoint.record and checkpoint.record.get('copied_state'))
        else:
            report['stop_reason'] = 'setup_failure'
        if baseline is None:
            report['unavailable_reason'] = 'Initial contract or isolation not verified; no endpoint imputed.'
        report['derived_BASE']['context_accounting'] = report['context_accounting']
        report['prospective_metrics'] = {**episode.analyze(report), 'context_accounting': report['context_accounting']}
        report['elapsed_seconds_including_setup_and_grading'] = time.monotonic() - started
        report['scored_before_cleanup'] = baseline is not None and checkpoint is not None and not report.get('grading_error')
        save(out / 'episode.json', report)
    return report, failure


def main(argv=None):
    args = arguments(argv)
    ensure(sys.platform == 'linux' and sys.flags.isolated and sys.flags.no_site and os.getuid() == os.geteuid() != 0,
           'Use unprivileged /usr/bin/python3 -I -S in Debian; no unsafe fallback')
    ensure(shutil.which('bwrap') is not None, 'BUBBLEWRAP_REQUIRED')
    # Import the exact retained r3 execution core only after platform guards.
    sys.path[:0] = [str(ROOT), str(ROOT / 'cases-package/frozen_runtime'), str(ROOT / 'cases-package')]
    import reproduce, exploration_episode as episode
    identity = reproduce.verify()
    order = [cid for cid in ORDER if args.fixtures is None or cid in args.fixtures]
    output = args.output.resolve()
    ensure(not output.is_relative_to(ROOT) and not ROOT.is_relative_to(output), 'OUTPUT_MUST_BE_OUTSIDE_PACKAGE')
    ensure(not output.exists(), 'OUTPUT_EXISTS:NO_RESTART_OR_RETRY')
    output.mkdir(parents=True)
    n = len(order)
    limits = {'model_calls': n * 20 if args.backend == 'endpoint' else 0,
              'generated_tokens': n * 8192 if args.backend == 'endpoint' else 0,
              'applications': n * (30 if args.backend == 'endpoint' else 18), 'probes': n * 2,
              'workers': n * 52, 'offline_installs': n * 4, 'fresh_states': n,
              'machine_seconds': 43200, 'checkpoint_copies': n}
    ledger = {k: 0 for k in limits}
    ledger.update(limits=limits, started_monotonic=time.monotonic(), model_calls=0,
                  context_accounting=context_accounting(args),
                  completion_attempts=[], scripted_replies=0, tokenizer_requests=0, tokenizer_commands=0,
                  model_processes_started=0, retries=0, replacements=0, cleanup_performed=False,
                  status='RUNNING', completed=[], unattempted=order.copy())
    save(output / 'budget.json', {'limits': limits, 'per_episode': {'actions': 20, 'run_app': 12, 'install_requests': 3,
         'reply_tokens': 2048, 'episode_tokens': 8192, 'context': 32768, 'watchdog_seconds': 14400},
         'context_accounting': context_accounting(args),
         'context_stop_limit': APPROXIMATE_CONTEXT_LIMIT if context_accounting(args) == 'approximate' else 32768,
         'model_preflights': 0, 'BASE_generation_calls': 0})
    # API keys and endpoint addresses are deliberately absent from this metadata.
    save(output / 'run.json', {'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'package_manifest_sha256': identity, 'order': order, 'backend': args.backend, 'model': args.model,
         'protocol': args.protocol, 'thinking': False, 'reasoning_reinjection': False,
         'context_accounting': context_accounting(args),
         'decoding': {k: getattr(args, k) for k in ['temperature', 'top_k', 'top_p', 'seed', 'repeat_penalty', 'presence_penalty', 'frequency_penalty',
                      'min_p', 'dry_multiplier', 'xtc_probability', 'cache_prompt']},
         'endpoint_process_owned': False, 'generic_provider_options_are_not_silently_dropped': True})
    backend = EndpointBackend(args, output, ledger) if args.backend == 'endpoint' else None
    capture = episode.judge.capture; install = episode.offline.apply_profile; captures = []
    def captured(command, *pos, **kw):
        kind = 'workers' if '/file_worker.py' in command else 'probes' if '/probe.py' in command else 'applications'
        ensure(ledger[kind] < limits[kind] and time.monotonic() - ledger['started_monotonic'] < limits['machine_seconds'], 'GLOBAL_CAPTURE_LIMIT')
        ledger[kind] += 1
        row = {'kind': kind, 'returned': False}; captures.append(row)
        save(output / 'capture_ledger.json', captures); save(output / 'costs.json', ledger)
        try:
            result = capture(command, *pos, **kw)
            row.update(returned=True, error=result.get('error'), exit_code=result.get('exit_code'), process_launched=result.get('process_launched'))
            return result
        finally:
            save(output / 'capture_ledger.json', captures); save(output / 'costs.json', ledger)
    def installed(*pos, **kw):
        ensure(ledger['offline_installs'] < limits['offline_installs'], 'GLOBAL_INSTALL_LIMIT')
        ledger['offline_installs'] += 1; save(output / 'costs.json', ledger)
        return install(*pos, **kw)
    episode.judge.capture, episode.offline.apply_profile = captured, installed
    (output / 'episodes').mkdir()
    reports = []
    try:
        if backend: backend.validate_service()  # Non-generative guard before candidate applications.
        reproduce.prepare_runtime(output, args.wheelhouse)
        cases = json.loads((ROOT / 'source/cases.json').read_bytes())
        for cid in order:
            ensure(time.monotonic() - ledger['started_monotonic'] < limits['machine_seconds'], 'GLOBAL_WATCHDOG')
            ledger['unattempted'].remove(cid)
            selected = backend or ScriptedBackend(cases[cid], args.control, ROOT, ledger)
            report, failure = run_one(cases[cid], args, output / 'episodes' / cid, selected, ledger, (reproduce, episode))
            reports.append(report); ledger['completed'].append(cid)
            save(output / 'costs.json', ledger)
            print(json.dumps({'fixture': cid, 'FC': report.get('final_task_pass'), 'BASE': report['derived_BASE'].get('final_task_pass'),
                              'terminal': report['stop_reason'], 'model_calls': report['model_calls'] if 'model_calls' in report else 0}), flush=True)
            if failure or report.get('global_stop_required'):
                ledger.update(status='STOPPED_REMAINDER_RETAINED', blocker=failure or 'GRADING_UNCERTAIN'); break
        else: ledger['status'] = 'COMPLETED'
        reproduce.verify()
        from prospective_metrics import aggregate
        save(output / 'summary.json', aggregate(reports, cases))
    except Exception as exc:
        ledger.update(status='BLOCKED', blocker=type(exc).__name__)
        raise
    finally:
        episode.judge.capture, episode.offline.apply_profile = capture, install
        ledger['machine_seconds'] = time.monotonic() - ledger['started_monotonic']
        if backend: backend.persist()
        else:
            ledger.update(generated_tokens_lower_bound=0, generated_tokens_upper_bound=0,
                          reasoning_tokens_lower_bound=0, reasoning_tokens_upper_bound=0)
            save(output / 'costs.json', ledger)
        save(output / 'closure.json', {'status': ledger['status'], 'unattempted': ledger['unattempted'], 'no_retry': True,
                                      'cleanup_performed': False, 'model_server_owned': False, 'server_shutdown_is_operator_responsibility': True})
    return 0 if ledger['status'] == 'COMPLETED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
