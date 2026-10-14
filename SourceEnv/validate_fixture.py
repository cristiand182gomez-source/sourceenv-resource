"""Bounded, no-model validation of the current stateless-cli-v1 catalogue.

Planning and schema checks are portable. Executing a saved plan requires the
trusted Debian interpreter and the existing Bubblewrap sandbox, without fallback.
No fixture module is imported by this program.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import sys
import time
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
OPERATIONS = ('first_command', 'second_command', 'no_args', 'explicit_help',
              'first_command_help', 'second_command_help')
VARIANTS = ('initial', 'noop', 'reference', 'alternative', 'negative')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'DUPLICATE_JSON_KEY:' + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('NONFINITE_JSON:' + value)
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
                      parse_constant=nonfinite)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.new')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                               allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def checks_valid(checks):
    return (type(checks) is dict and set(checks) == set(OPERATIONS)
            and all(type(value) is bool for value in checks.values()))


def read_catalog(root=ROOT):
    """Validate metadata and fixture bytes, without importing candidate code."""
    cases = read_json(root / 'source/cases.json')
    contract = read_json(root / 'cases-package/contract.json')
    policy = read_json(root / 'cases-package/frozen_runtime/policy.json')
    variants = read_json(root / 'fixture_validation.json')
    require(type(cases) is dict and cases, 'EMPTY_CATALOG')
    require(cases == {c['case_id']: c for c in contract['cases']}, 'CATALOG_DIVERGENCE')
    require(list(policy['operations']) == list(OPERATIONS), 'UNSUPPORTED_OPERATIONS')
    require(contract['application_contract']['id'] == 'stateless-cli-v1', 'UNSUPPORTED_CONTRACT')
    require(variants['schema'] == 1 and variants['fixture_contract'] == 'stateless-cli-v1',
            'UNSUPPORTED_VARIANT_METADATA')
    require(set(variants['cases']) == set(cases), 'VARIANT_CATALOG_MISMATCH')
    for cid, case in cases.items():
        require(re.fullmatch(r'[A-Z0-9]+(?:-[A-Z0-9]+)*', cid) is not None
                and case['case_id'] == cid, 'INVALID_CASE_ID')
        require(case['fixture_contract'] == 'stateless-cli-v1', 'UNSUPPORTED_FIXTURE:' + cid)
        require(type(case['healthy']) is bool and checks_valid(case['initial_checks_expected']),
                'INVALID_INITIAL_CHECKS:' + cid)
        require(case['healthy'] == all(case['initial_checks_expected'].values()),
                'HEALTH_INITIAL_CONFLICT:' + cid)
        require(set(case['command_json']) == {'first_command', 'second_command'}
                and all(type(v) is dict for v in case['command_json'].values()),
                'UNSUPPORTED_COMMAND_SCHEMA:' + cid)
        for variant, field in [('initial', 'source_sha256'),
                               ('reference', 'reference_source_sha256'),
                               ('alternative', 'alternative_source_sha256')]:
            path = root / 'cases-package/cases' / cid / (variant + '.py')
            require(path.is_file() and not path.is_symlink()
                    and digest(path) == case[field], 'FIXTURE_BYTES:' + cid + '/' + variant)
        for field in ('initial_profile', 'reference_profile', 'alternative_profile'):
            require(case[field] in policy['profiles'], 'UNKNOWN_PROFILE:' + cid)
        metadata = variants['cases'][cid]
        require(set(metadata) == {'alternative', 'negative'}, 'VARIANT_KEYS:' + cid)
        for variant, row in metadata.items():
            path = root / 'cases-package/cases' / cid / (variant + '.py')
            require(row['source'] == path.relative_to(root).as_posix()
                    and path.is_file() and not path.is_symlink()
                    and digest(path) == row['source_sha256'], 'VARIANT_BYTES:' + cid + '/' + variant)
            profile_field = 'alternative_profile' if variant == 'alternative' else 'reference_profile'
            require(row['profile'] == case[profile_field], 'VARIANT_PROFILE:' + cid + '/' + variant)
            require(checks_valid(row['expected_checks']), 'VARIANT_EXPECTATIONS:' + cid + '/' + variant)
            require(row['expected_status'] == ('PASS' if all(row['expected_checks'].values()) else 'FAIL'),
                    'VARIANT_STATUS:' + cid + '/' + variant)
            require(re.fullmatch(r'[0-9a-f]{64}', row['historical_evidence']['sha256']) is not None,
                    'VARIANT_PROVENANCE:' + cid + '/' + variant)
    return cases, policy, variants


def scenario_matrix(cases, variants):
    rows = []
    for cid, case in cases.items():
        for variant in VARIANTS:
            # The healthy requirements are initial and noop; there is no redundant
            # healthy reference scenario in this finite validation matrix.
            if variant == 'reference' and case['healthy']:
                continue
            if variant in ('alternative', 'negative'):
                metadata = variants['cases'][cid][variant]
                source = metadata['source']
                profile = metadata['profile']
                expected = metadata['expected_checks']
            else:
                name = 'initial' if variant == 'noop' else variant
                source = f'cases-package/cases/{cid}/{name}.py'
                profile = case['reference_profile'] if variant == 'reference' else case['initial_profile']
                expected = (dict.fromkeys(OPERATIONS, True) if variant == 'reference'
                            else case['initial_checks_expected'])
            row = {'id': cid + '/' + variant, 'case_id': cid, 'variant': variant,
                   'source': source, 'profile': profile, 'expected_checks': expected,
                   'expected_status': 'PASS' if all(expected.values()) else 'FAIL',
                   'fresh_state': True, 'application_captures': 6}
            if variant in ('initial', 'noop') and 'initial_no_args_rc' in case:
                row['expected_no_args_rc'] = case['initial_no_args_rc']
            rows.append(row)
    return rows


def component_hashes(root=ROOT):
    paths = [root / 'validate_fixture.py', root / 'fixture_validation.json', root / 'reproduce.py']
    for folder in ('source', 'cases-package'):
        paths.extend(p for p in (root / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(paths)}


def make_plan(root=ROOT, selection='all', selected=None):
    cases, policy, variants = read_catalog(root)
    matrix = scenario_matrix(cases, variants)
    if selection == 'new-coverage':
        wanted = {r['id'] for r in matrix if r['variant'] in ('alternative', 'negative')
                  or cases[r['case_id']]['healthy']}
    elif selection == 'selected':
        require(selected and len(set(selected)) == len(selected), 'EMPTY_OR_DUPLICATE_SELECTION')
        wanted = set(selected)
        require(wanted <= {r['id'] for r in matrix}, 'UNKNOWN_SCENARIO_SELECTION')
    else:
        require(selection == 'all', 'UNKNOWN_SELECTION')
        wanted = {r['id'] for r in matrix}
    rows = [r for r in matrix if r['id'] in wanted]
    n = len(rows)
    return {'schema': 1, 'kind': 'FIXTURE_VALIDATION_NOT_R3_MODEL_RESULTS',
            'fixture_contract': 'stateless-cli-v1', 'selection': selection,
            'selected_ids': [r['id'] for r in rows], 'scenarios': rows,
            'components_sha256': component_hashes(root),
            'limits': {'applications': 6*n, 'probes': 2*n, 'workers': 2*n,
                       'offline_installs': n, 'fresh_states': n, 'checkpoint_copies': 0,
                       'machine_seconds': 7200, 'model_calls': 0, 'generated_tokens': 0,
                       'model_processes': 0, 'automatic_retries': 0},
            'per_capture_timeout_seconds': policy['timeout_seconds'],
            'per_stream_output_limit_bytes': policy['output_limit_bytes'],
            'execution': 'One fresh endpoint per scenario; existing oracle and sandbox; no FC/BASE episode',
            'reuse_note': ('Damaged initial/reference/noop scenarios are omitted only by selection. '
                          'A separate identity-linked reproduce.py receipt is required to cover them.'),
            'cleanup_performed': False, 'stop_on_failure': True, 'isolation_fallback': False}


def check_plan(plan, root=ROOT):
    expected = make_plan(root, plan['selection'], plan['selected_ids'])
    require(plan == expected, 'PLAN_CHANGED_OR_STALE')
    return expected


def entry_gate():
    require(sys.flags.optimize == 0, 'OPTIMIZATION_FORBIDDEN')
    require(sys.platform == 'linux' and sys.flags.isolated and sys.flags.no_site,
            'TRUSTED_DEBIAN_PYTHON_I_S_REQUIRED')
    require(os.getuid() == os.geteuid() != 0, 'UNPRIVILEGED_UID_REQUIRED')
    require(Path(sys.executable).resolve() == Path('/usr/bin/python3').resolve(),
            'TRUSTED_USR_BIN_PYTHON_REQUIRED')
    require(Path('/etc/debian_version').is_file(), 'DEBIAN_REQUIRED')
    require(shutil.which('bwrap') is not None, 'BUBBLEWRAP_REQUIRED_NO_FALLBACK')


def validate_score(row, score):
    require(score['checks'] == row['expected_checks'] and score['status'] == row['expected_status'],
            'SCENARIO_EXPECTATION_FAILED:' + row['id'])
    if 'expected_no_args_rc' in row:
        require(score['operations']['no_args']['exit_code'] == row['expected_no_args_rc'],
                'HEALTHY_NO_ARGS_RC:' + row['id'])


def run_scenario(row, case, out, runtime, cost):
    """Only offline.prepare copies bytes; execution is exclusively judge.capture."""
    out.mkdir(parents=True, exist_ok=False)
    offline, judge, oracle, Dispatcher, worker, grade_case = runtime
    state = out / 'state'
    cost['fresh_states'] += 1
    snapshot = offline.prepare(state, ROOT / row['source'], row['profile'])
    require(snapshot['source_files'] == {'app.py': digest(ROOT / row['source'])}, 'PREPARED_SOURCE_BYTES')
    paths = {name: out / name for name in ('home', 'tmp', 'cache')}
    for path in paths.values():
        path.mkdir()
    records = []
    report = {'scenario': row, 'model_calls': 0, 'cleanup_performed': False,
              'status': 'PREPARING', 'records': records, 'scored_before_cleanup': False}
    save(out / 'scenario.json', report)
    try:
        gate = judge.native_preflight(snapshot)
        save(out / 'isolation.json', gate)
        require(gate.get('available') is True, 'NATIVE_ISOLATION_BLOCKED')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            properties = worker(snapshot, paths, judge, 'native_properties', {
                'parent_pid': os.getpid(), 'pid_namespace': os.readlink('/proc/self/ns/pid'),
                'net_namespace': os.readlink('/proc/self/ns/net'),
                'listener_port': listener.getsockname()[1],
                'private_paths': [str(ROOT), str(out / 'scenario.json')]}, records)
        save(out / 'writable_properties.json', properties)
        require(properties.get('ok') is True and properties.get('checks')
                and all(value is True for value in properties['checks'].values()),
                'WRITABLE_ISOLATION_BLOCKED')
        gate['writable_properties_passed'] = True
        d = Dispatcher(state, paths, offline, judge, gate, records, row['case_id'])
        if row['variant'] == 'noop':
            response = d.dispatch(json.dumps({'tool': 'finish', 'arguments': {'summary': 'No-op fixture validation.'}}))
            require(response.get('ok') is True and d.stop_reason == 'finish', 'NOOP_ACTION_FAILED')
        score = grade_case(d, case, offline.policy(), oracle, out / 'score.json')
        report.update(status='SCORED', score_sha256=digest(out / 'score.json'),
                      observed_checks=score['checks'], observed_status=score['status'],
                      events=d.events, scored_before_cleanup=score['scored_before_cleanup'],
                      final_state_preserved=score['final_state_preserved'])
        save(out / 'scenario.json', report)
        require(score['before'] == snapshot and score['after'] == snapshot, 'ENDPOINT_STATE_CHANGED')
        validate_score(row, score)
        report['status'] = 'PASS'
        save(out / 'scenario.json', report)
        return {'id': row['id'], 'validation_status': 'PASS', 'oracle_status': score['status'],
                'observed_checks': score['checks'], 'scored_before_cleanup': True,
                'scenario_sha256': digest(out / 'scenario.json'), 'score_sha256': digest(out / 'score.json')}
    except BaseException as exc:
        report.update(status='FAILED', error=str(exc), traceback=traceback.format_exc())
        save(out / 'scenario.json', report)
        raise


def execute_plan(plan_path, output, wheelhouse):
    plan = check_plan(read_json(plan_path))
    output = Path(output).resolve()
    require(output != ROOT and not output.is_relative_to(ROOT) and not ROOT.is_relative_to(output),
            'OUTPUT_MUST_BE_OUTSIDE_PACKAGE')
    output.mkdir(parents=True, exist_ok=False)
    save(output / 'plan.json', plan)
    started = time.monotonic()
    limits = plan['limits']
    cost = dict.fromkeys(limits, 0)
    rows, ledger = [], []
    save(output / 'costs.json', cost)
    try:
        entry_gate()
        sys.path[:0] = [str(ROOT), str(ROOT / 'source'), str(ROOT / 'cases-package/frozen_runtime'),
                       str(ROOT / 'cases-package')]
        import reproduce
        from interface import Dispatcher, worker
        from scoring import grade_case
        offline, judge, oracle = reproduce.offline, reproduce.judge, reproduce.oracle
        manifest_hash = reproduce.verify()
        save(output / 'environment.json', {
            'python_version': platform.python_version(), 'python_sha256': digest(Path(sys.executable).resolve()),
            'debian_version': Path('/etc/debian_version').read_text().strip(),
            'kernel': platform.release(), 'uid': os.getuid(), 'euid': os.geteuid(),
            'isolated': sys.flags.isolated, 'no_site': sys.flags.no_site, 'optimize': sys.flags.optimize,
            'bubblewrap_sha256': digest(Path(shutil.which('bwrap'))),
            'package_manifest_sha256': manifest_hash, 'plan_sha256': digest(plan_path)})
        reproduce.prepare_runtime(output, Path(wheelhouse))
        original_capture, original_install = judge.capture, offline.apply_profile

        def checkpoint_cost():
            cost['machine_seconds'] = time.monotonic() - started
            save(output / 'costs.json', cost)

        def captured(argv, *args, **kwargs):
            require(Path(argv[0]).resolve() == Path(shutil.which('bwrap')).resolve()
                    and '--unshare-all' in argv and '--cap-drop' in argv, 'SANDBOX_ONLY_NO_FALLBACK')
            kind = 'workers' if '/file_worker.py' in argv else 'probes' if '/probe.py' in argv else 'applications'
            require(cost[kind] < limits[kind] and time.monotonic() - started < limits['machine_seconds'],
                    'CAPTURE_BUDGET_EXHAUSTED')
            cost[kind] += 1
            item = {'index': len(ledger) + 1, 'kind': kind, 'returned': False, 'argv': argv}
            ledger.append(item)
            save(output / 'capture_ledger.json', ledger)
            checkpoint_cost()
            try:
                result = original_capture(argv, *args, **kwargs)
                save(output / 'captures' / ('%06d.json' % item['index']), result)
                item.update(returned=True, error=result.get('error'), exit_code=result.get('exit_code'))
                # Launch/isolation errors are infrastructure failures, not valid
                # negative fixture results. No next scenario runs after a failure.
                require(result.get('error') is None and type(result.get('exit_code')) is int
                        and result['exit_code'] >= 0 and result.get('utf8_valid') is True,
                        'INCOMPLETE_CAPTURE:' + kind)
                require(not result.get('stderr', '').startswith('bwrap:'), 'BUBBLEWRAP_LAUNCH_ERROR')
                return result
            finally:
                save(output / 'capture_ledger.json', ledger)
                checkpoint_cost()

        def installed(*args, **kwargs):
            require(cost['offline_installs'] < limits['offline_installs']
                    and time.monotonic() - started < limits['machine_seconds'], 'INSTALL_BUDGET_EXHAUSTED')
            cost['offline_installs'] += 1
            checkpoint_cost()
            return original_install(*args, **kwargs)

        judge.capture, offline.apply_profile = captured, installed
        cases, _, _ = read_catalog()
        runtime = (offline, judge, oracle, Dispatcher, worker, grade_case)
        for row in plan['scenarios']:
            require(cost['fresh_states'] < limits['fresh_states']
                    and time.monotonic() - started < limits['machine_seconds'], 'SCENARIO_BUDGET_EXHAUSTED')
            result = run_scenario(row, cases[row['case_id']], output / row['case_id'] / row['variant'], runtime, cost)
            rows.append(result)
            checkpoint_cost()
            save(output / 'results.json', rows)
            print(json.dumps(result), flush=True)
        require(component_hashes() == plan['components_sha256'], 'COMPONENTS_CHANGED_DURING_VALIDATION')
        require(reproduce.verify() == manifest_hash, 'PACKAGE_CHANGED_DURING_VALIDATION')
        checkpoint_cost()
        require(all(cost[key] <= value for key, value in limits.items()), 'FINAL_BUDGET_EXCEEDED')
        save(output / 'closure.json', {'status': 'COMPLETED', 'scenario_count': len(rows),
             'package_manifest_sha256': manifest_hash, 'plan_sha256': digest(plan_path),
             'scored_before_cleanup': True, 'cleanup_performed': False,
             'model_calls': 0, 'automatic_retries': 0, 'r3_model_result': False})
    except BaseException as exc:
        cost['machine_seconds'] = time.monotonic() - started
        save(output / 'costs.json', cost)
        save(output / 'failure.json', {'error': str(exc), 'traceback': traceback.format_exc(),
             'completed_scenarios': rows, 'no_retry': True, 'cleanup_performed': False,
             'isolation_fallback': False})
        raise


def main(argv=None):
    require(sys.flags.optimize == 0, 'OPTIMIZATION_FORBIDDEN')
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_mutually_exclusive_group()
    command.add_argument('--write-plan', type=Path)
    command.add_argument('--execute-plan', type=Path)
    parser.add_argument('--selection', choices=('all', 'new-coverage', 'selected'), default='all')
    parser.add_argument('--scenarios', nargs='+', help='Exact CASE/variant ids for --selection selected')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--wheelhouse', type=Path)
    args = parser.parse_args(argv)
    if args.execute_plan:
        require(args.output is not None and args.wheelhouse is not None, 'OUTPUT_AND_WHEELHOUSE_REQUIRED')
        require(args.selection == 'all' and args.scenarios is None, 'EXECUTE_USES_SAVED_PLAN_ONLY')
        execute_plan(args.execute_plan, args.output, args.wheelhouse)
    else:
        require(args.scenarios is None or args.selection == 'selected', 'SCENARIOS_REQUIRE_SELECTED')
        plan = make_plan(selection=args.selection, selected=args.scenarios)
        if args.write_plan:
            require(not args.write_plan.exists(), 'REFUSE_TO_OVERWRITE_PLAN')
            save(args.write_plan, plan)
        print(json.dumps({'schema_check': 'PASS', 'scenario_count': len(plan['scenarios']),
                          'selection': plan['selection'], 'limits': plan['limits'],
                          'applications_executed': 0, 'model_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
