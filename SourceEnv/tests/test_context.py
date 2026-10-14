"""Scripted context accounting and analyzer tests; no models or candidate apps."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
import copy, json, subprocess, tempfile, time, unittest
from types import SimpleNamespace
from unittest.mock import patch
import endpoint_backend as eb
import run_agent
import test_portable


class ContextTests(unittest.TestCase):
    args = test_portable.PortableTests.args
    ledger = test_portable.PortableTests.ledger

    def reply(self, prompt_tokens):
        return {'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': 0,
                         'completion_tokens_details': {'reasoning_tokens': 0}},
            'choices': [{'message': {'role': 'assistant', 'content': 'A scripted reply.',
                                    'reasoning_content': 'Never reinject this.'}, 'finish_reason': 'stop'}]}

    def generate(self, backend, messages, reported=321, cap=2048):
        prepared = backend.rpc('prepare', messages=messages)
        with patch.object(backend, 'request', return_value=self.reply(reported)) as request:
            result = backend.rpc('generate', messages=messages, cap=cap,
                expected_input_tokens=prepared['input_tokens'], remaining_seconds=60)
        return prepared, result, request

    def test_first_turn_uses_utf8_and_native_tool_schema(self):
        args = run_agent.arguments(['--protocol', 'openai', '--output', 'results', '--wheelhouse', 'wheels'])
        self.assertEqual(eb.context_accounting(args), 'approximate')
        with tempfile.TemporaryDirectory() as folder:
            backend = eb.EndpointBackend(self.args(protocol='openai'), folder, self.ledger())
            messages = [{'role': 'system', 'content': 'Task.'}, {'role': 'user', 'content': 'á🙂'}]
            prepared = backend.rpc('prepare', messages=messages)
            payload = {'messages': messages, 'tools': eb.tools(), 'tool_choice': 'auto', 'parallel_tool_calls': False}
            size = len(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
            self.assertEqual(prepared['estimated_new_bytes'], size)
            self.assertEqual(prepared['input_tokens'], (size + 2) // 3)
            self.assertIsNone(prepared['exact_history_prompt_tokens'])
            self.assertEqual(prepared['history_anchor'], 'initial_estimate')
            self.assertEqual(prepared['context_stop_limit'], 27852)
            self.assertEqual(backend.ledger['tokenizer_commands'], 0)
            self.assertEqual(backend.ledger['model_calls'], 0)

    def test_usage_anchor_adds_reply_and_public_feedback(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = eb.EndpointBackend(self.args(protocol='openai'), folder, self.ledger())
            messages = [{'role': 'user', 'content': 'Read the CLI.'}]
            first, result, request = self.generate(backend, messages, reported=1700)
            self.assertNotEqual(first['input_tokens'], result['reported_prompt_tokens'])
            self.assertEqual(result['input_tokens'], first['input_tokens'])
            self.assertEqual(result['context_accounting'], 'approximate')
            self.assertNotIn('reasoning_content', result['message'])
            added = [result['message'], {'role': 'user', 'content': 'Finish rejected; run the missing operations.'}]
            second = backend.rpc('prepare', messages=messages + added)
            size = len(json.dumps(added, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
            self.assertEqual(second['input_tokens'], 1700 + (size + 2) // 3)
            self.assertEqual(second['exact_history_prompt_tokens'], 1700)
            self.assertEqual(second['history_anchor'], 'previous_usage')
            self.assertEqual(backend.ledger['completion_attempts'][0]['reported_prompt_tokens'], 1700)
            request.assert_called_once()

    def test_anchor_reset_and_fixture_independence(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = eb.EndpointBackend(self.args(protocol='openai'), folder, self.ledger())
            messages = [{'role': 'user', 'content': 'Original task.'}]
            backend.case_id = 'H-RC0'
            self.generate(backend, messages, reported=5000)
            backend.case_id = 'H-RC2'
            fresh = backend.rpc('prepare', messages=messages)
            self.assertIsNone(fresh['exact_history_prompt_tokens'])
            backend.case_id = 'H-RC0'
            unchanged = backend.rpc('prepare', messages=messages)
            self.assertEqual(unchanged['input_tokens'], 5000)
            self.assertEqual(unchanged['estimated_new_bytes'], 0)
            reset = backend.rpc('prepare', messages=[{'role': 'user', 'content': 'Different task.'}])
            self.assertEqual(reset['history_anchor'], 'history_reset')
            self.assertIsNone(reset['exact_history_prompt_tokens'])

    def test_85_percent_cut_includes_reply_and_is_ordinary(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = eb.EndpointBackend(self.args(protocol='openai'), folder, self.ledger())
            messages = [{'role': 'user', 'content': 'Task.'}]
            backend.context_history[None] = {'messages': copy.deepcopy(messages),
                'prompt_tokens': 27852 - 2048, 'request_shape': {'tools': eb.tools(), 'tool_choice': 'auto', 'parallel_tool_calls': False}}
            _, result, request = self.generate(backend, messages, reported=27852 - 2048)
            self.assertIn('message', result)
            request.assert_called_once()
            backend.context_history[None]['prompt_tokens'] += 1
            _, stopped, request = self.generate(backend, messages)
            self.assertEqual(stopped['ordinary_stop'], 'context_budget')
            request.assert_not_called()
            self.assertEqual(backend.ledger['model_calls'], 1)

    def test_bad_prompt_usage_and_prepared_identity_are_errors(self):
        for reported in [-1, True, '100', None]:
            with self.subTest(reported=reported), tempfile.TemporaryDirectory() as folder:
                backend = eb.EndpointBackend(self.args(protocol='openai'), folder, self.ledger())
                with self.assertRaisesRegex(RuntimeError, 'PROMPT_TOKEN_USAGE'):
                    self.generate(backend, [], reported=reported)
                self.assertEqual(backend.context_history, {})
        with tempfile.TemporaryDirectory() as folder:
            backend = eb.EndpointBackend(self.args(protocol='openai'), folder, self.ledger())
            prepared = backend.rpc('prepare', messages=[])
            with patch.object(backend, 'request') as request:
                with self.assertRaisesRegex(RuntimeError, 'APPROXIMATE_PREPARED_IDENTITY'):
                    backend.rpc('generate', messages=[{'role': 'user', 'content': 'changed'}], cap=2048,
                        expected_input_tokens=prepared['input_tokens'], remaining_seconds=60)
                request.assert_not_called()
            self.assertEqual(backend.ledger['model_calls'], 0)

    def test_exact_counter_still_requires_matching_usage(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = eb.EndpointBackend(self.args(protocol='openai', tokenizer_command='trusted-counter'), folder, self.ledger())
            with patch.object(eb.subprocess, 'run', return_value=SimpleNamespace(stdout=b'{"input_tokens": 400, "context": 32768}')):
                prepared = backend.rpc('prepare', messages=[])
            self.assertEqual(prepared['context_accounting'], 'exact')
            self.assertEqual(prepared['context_stop_limit'], 32768)
            with patch.object(backend, 'request', return_value=self.reply(401)):
                with self.assertRaisesRegex(RuntimeError, 'REPLY_INPUT_TOKEN_IDENTITY'):
                    backend.rpc('generate', messages=[], cap=2048, expected_input_tokens=400, remaining_seconds=60)

    @unittest.skipUnless(sys.platform == 'linux', 'Retained native core requires the trusted Debian interpreter.')
    def test_adapter_retains_ordinary_context_terminal_without_dispatch(self):
        import exploration_episode as episode
        with tempfile.TemporaryDirectory() as folder:
            backend = eb.EndpointBackend(self.args(protocol='openai'), folder, self.ledger())
            dispatcher = SimpleNamespace(stopped=False, stop_reason=None,
                state='scripted-state', offline=SimpleNamespace(inspect_state=lambda _: {}), check_integrity=lambda: None)
            adapter = episode.Adapter.__new__(episode.Adapter)
            adapter.dispatcher = dispatcher
            adapter.messages = [{'role': 'user', 'content': 'z' * 78000}]
            adapter.generated = adapter.replies = 0
            adapter.total_cap, adapter.reply_cap = 8192, 2048
            adapter.deadline = time.monotonic() + 60
            adapter.turns, adapter.thinking = [], False
            with patch.object(episode, 'rpc', side_effect=backend.rpc), patch.object(backend, 'request') as request:
                result = adapter.run(Path(folder))
            self.assertEqual(result['stop_reason'], 'context_budget')
            self.assertEqual(adapter.replies, 0)
            self.assertEqual(len(adapter.turns), 1)
            self.assertEqual(adapter.turns[0]['prepared']['context_accounting'], 'approximate')
            self.assertLessEqual(adapter.turns[0]['prepared']['input_tokens'] + 2048, 32768)
            self.assertTrue((Path(folder) / 'conversation.partial.json').exists())
            request.assert_not_called()

    def test_analyzer_preserves_accounting_with_no_imputation(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / 'episodes/H-RC0').mkdir(parents=True)
            episode = {'case_id': 'H-RC0', 'actions': 0, 'events': [], 'context_accounting': 'approximate',
                'primary_availability': 'VALID', 'final_task_pass': True, 'stop_reason': 'context_budget',
                'conversation': {'messages': [], 'turns': []},
                'derived_BASE': {'primary_availability': 'VALID', 'final_task_pass': True, 'terminal_action_index': 0, 'stop_reason': 'context_budget'}}
            (out / 'episodes/H-RC0/episode.json').write_text(json.dumps(episode))
            (out / 'run.json').write_text('{"context_accounting":"approximate"}')
            result = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT / 'analyze.py'), str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            analyzed = json.loads(result.stdout)
            self.assertEqual(analyzed['context_accounting'], {'approximate': 1})
            self.assertEqual(analyzed['episodes']['H-RC0']['context_accounting'], 'approximate')
            self.assertEqual(analyzed['run_context_accounting'], 'approximate')
            self.assertEqual(analyzed['summary']['arms']['FC']['healthy_preservation_denominator'], 1)
            self.assertEqual(len(analyzed['summary']['unattempted']), 9)


if __name__ == '__main__': unittest.main(verbosity=2)
