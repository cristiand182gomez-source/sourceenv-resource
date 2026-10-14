"""Offline validator tests. No candidate imports, processes, apps or models."""
from pathlib import Path
import copy
import importlib.util
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fixture_validator_under_test', ROOT / 'validate_fixture.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.policy, cls.variants = validator.read_catalog()
        cls.rows = {r['id']: r for r in validator.scenario_matrix(cls.cases, cls.variants)}

    def test_complete_matrix_separates_health_and_initial_checks(self):
        self.assertEqual(len(self.rows), 48)
        for cid, case in self.cases.items():
            for variant in ('initial', 'noop'):
                row = self.rows[cid + '/' + variant]
                self.assertEqual(row['expected_checks'], case['initial_checks_expected'])
                self.assertEqual(row['expected_status'], 'PASS' if case['healthy'] else 'FAIL')
                self.assertEqual(row['profile'], case['initial_profile'])
            self.assertEqual(cid + '/reference' in self.rows, not case['healthy'])
            if not case['healthy']:
                self.assertTrue(all(self.rows[cid + '/reference']['expected_checks'].values()))
        self.assertEqual(sum(self.rows['SC-BALANCE/initial']['expected_checks'].values()), 5)
        self.assertEqual(sum(self.rows['EC-MISSING/initial']['expected_checks'].values()), 0)

    def test_variant_profiles_and_vectors_come_from_metadata(self):
        for cid, value in self.variants['cases'].items():
            for variant, metadata in value.items():
                row = self.rows[cid + '/' + variant]
                self.assertEqual(row['profile'], metadata['profile'])
                self.assertEqual(row['expected_checks'], metadata['expected_checks'])
                self.assertEqual(row['source'], metadata['source'])
        self.assertEqual(self.rows['EH-RENDERER/alternative']['profile'], 'missing_rich_typer0160_click820')
        self.assertEqual(self.rows['EH-API/negative']['profile'], 'typer0160_click820')
        self.assertFalse(self.rows['SC-SORT/negative']['expected_checks']['first_command'])
        self.assertTrue(self.rows['SC-SORT/negative']['expected_checks']['second_command'])

    def test_new_coverage_selection_is_exact_and_bounded(self):
        plan = validator.make_plan(selection='new-coverage')
        self.assertEqual(len(plan['scenarios']), 24)
        self.assertEqual(plan['limits']['applications'], 144)
        self.assertEqual(plan['limits']['probes'], 48)
        self.assertEqual(plan['limits']['workers'], 48)
        self.assertEqual(plan['limits']['offline_installs'], 24)
        self.assertEqual(plan['limits']['model_calls'], 0)
        self.assertEqual(plan['limits']['automatic_retries'], 0)
        self.assertEqual({r['id'] for r in plan['scenarios'] if r['variant'] in ('initial', 'noop')},
                         {'H-RC0/initial', 'H-RC0/noop', 'H-RC2/initial', 'H-RC2/noop'})

    def test_saved_plan_binds_components_and_expectations(self):
        plan = validator.make_plan(selection='selected', selected=['SC-BALANCE/initial'])
        self.assertEqual(validator.check_plan(plan), plan)
        for mutation in ('component', 'expectation', 'budget'):
            changed = copy.deepcopy(plan)
            if mutation == 'component':
                changed['components_sha256']['validate_fixture.py'] = '0' * 64
            elif mutation == 'expectation':
                changed['scenarios'][0]['expected_checks']['first_command'] = True
            else:
                changed['limits']['applications'] += 6
            with self.assertRaisesRegex(RuntimeError, 'PLAN_CHANGED_OR_STALE'):
                validator.check_plan(changed)

    def test_invalid_selection_rejected_before_runtime(self):
        for selected in ([], ['NO-SUCH/initial'], ['H-RC0/noop', 'H-RC0/noop']):
            with self.assertRaises(RuntimeError):
                validator.make_plan(selection='selected', selected=selected)

    def test_initial_requires_vector_equality_not_all_fail(self):
        row = self.rows['SC-BALANCE/initial']
        score = {'checks': row['expected_checks'], 'status': 'FAIL'}
        validator.validate_score(row, score)
        score['checks'] = dict.fromkeys(validator.OPERATIONS, False)
        with self.assertRaisesRegex(RuntimeError, 'SCENARIO_EXPECTATION_FAILED'):
            validator.validate_score(row, score)

    def test_healthy_noop_preserves_specific_rc(self):
        row = self.rows['H-RC2/noop']
        score = {'checks': row['expected_checks'], 'status': 'PASS',
                 'operations': {'no_args': {'exit_code': 2}}}
        validator.validate_score(row, score)
        score['operations']['no_args']['exit_code'] = 0
        with self.assertRaisesRegex(RuntimeError, 'HEALTHY_NO_ARGS_RC'):
            validator.validate_score(row, score)

    def test_optimized_or_nonisolated_or_privileged_entry_is_blocked(self):
        for flags, uid, expected in [(SimpleNamespace(optimize=1, isolated=1, no_site=1), 1000, 'OPTIMIZATION'),
                                     (SimpleNamespace(optimize=0, isolated=0, no_site=1), 1000, 'PYTHON_I_S'),
                                     (SimpleNamespace(optimize=0, isolated=1, no_site=1), 0, 'UNPRIVILEGED')]:
            with patch.object(validator.sys, 'flags', flags), patch.object(validator.sys, 'platform', 'linux'), \
                 patch.object(validator.os, 'getuid', create=True, return_value=uid), \
                 patch.object(validator.os, 'geteuid', create=True, return_value=uid):
                with self.assertRaisesRegex(RuntimeError, expected):
                    validator.entry_gate()

    def test_isolation_failure_stops_before_scoring_and_preserves_record(self):
        row = self.rows['H-RC0/initial']
        snapshot = {'source_files': {'app.py': validator.digest(ROOT / row['source'])}}
        offline = SimpleNamespace(prepare=Mock(return_value=snapshot))
        judge = SimpleNamespace(native_preflight=Mock(return_value={'available': False, 'records': []}))
        dispatcher, worker, grade = Mock(), Mock(), Mock()
        runtime = (offline, judge, Mock(), dispatcher, worker, grade)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'scenario'
            with self.assertRaisesRegex(RuntimeError, 'NATIVE_ISOLATION_BLOCKED'):
                validator.run_scenario(row, self.cases['H-RC0'], out, runtime, {'fresh_states': 0})
            self.assertEqual(validator.read_json(out / 'scenario.json')['status'], 'FAILED')
            self.assertTrue((out / 'isolation.json').is_file())
            dispatcher.assert_not_called()
            worker.assert_not_called()
            grade.assert_not_called()

    def test_duplicate_metadata_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'duplicate.json'
            path.write_text('{"schema":1,"schema":2}', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'DUPLICATE_JSON_KEY'):
                validator.read_json(path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
