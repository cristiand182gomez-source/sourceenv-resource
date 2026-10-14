"""Directed transport, argument, token-budget and wheel integrity tests; no model."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import io, json, subprocess, tempfile, threading, time, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest.mock import patch
import endpoint_backend as eb
import fetch_wheels as fw
import run_agent


class PortableTests(unittest.TestCase):
    def test_isolated_entrypoint(self):
        result = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'run_agent.py'), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--base-url', result.stdout)

    def args(self, **overrides):
        a = dict(base_url='http://127.0.0.1:1/v1', model='test-agent', api_key='synthetic-test-key',
                 protocol='llama-cpp', tokenizer_command=None, temperature=1.0, top_k=64,
                 top_p=.95, seed=0, cache_prompt=True, repeat_penalty=1.0, presence_penalty=0.0, frequency_penalty=0.0,
                 min_p=0.0, dry_multiplier=0.0, xtc_probability=0.0)
        a.update(overrides); return SimpleNamespace(**a)

    def ledger(self):
        return {'started_monotonic': time.monotonic(), 'limits': {'machine_seconds': 43200, 'model_calls': 200, 'generated_tokens': 81920},
                'model_calls': 0, 'completion_attempts': [], 'tokenizer_requests': 0, 'tokenizer_commands': 0}

    def test_defaults_and_cli(self):
        a = run_agent.arguments(['--output', 'result', '--wheelhouse', 'wheels'])
        self.assertEqual((a.temperature, a.top_k, a.top_p, a.seed, a.cache_prompt), (1.0, 64, .95, 0, True))
        a = run_agent.arguments(['--output', 'result', '--wheelhouse', 'wheels', '--temperature', '.2', '--top-k', '8', '--seed', '9', '--no-cache-prompt'])
        self.assertEqual((a.temperature, a.top_k, a.seed, a.cache_prompt), (.2, 8, 9, False))
        with self.assertRaises(RuntimeError): run_agent.arguments(['--output', 'result', '--wheelhouse', 'wheels', '--fixtures', 'H-RC0', 'H-RC0'])
        a = run_agent.arguments(['--output', 'result', '--wheelhouse', 'wheels', '--protocol', 'openai'])
        self.assertEqual(eb.context_accounting(a), 'approximate')
        with self.assertRaises(RuntimeError): run_agent.arguments(['--output', 'result', '--wheelhouse', 'wheels', '--temperature', 'nan'])

    def test_real_socket_native_path(self):
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                seen.append((self.path, None, self.headers.get('Authorization')))
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"default_generation_settings":{"n_ctx":32768}}')
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.append((self.path, body, self.headers.get('Authorization')))
                values = {'/apply-template': {'prompt': 'fixture template and generation prefix'}, '/tokenize': {'tokens': [1, 2, 3]},
                          '/v1/chat/completions': {'usage': {'completion_tokens': 0, 'prompt_tokens': 3},
                          '__verbose': {'tokens': [], 'tokens_predicted': 0, 'truncated': False, 'generation_settings': {'temperature': 1.0, 'top_k': 64, 'top_p': .95}},
                          'choices': [{'message': {'role': 'assistant', 'content': 'Done.', 'reasoning_content': 'do not reinject'}, 'finish_reason': 'stop'}]}}
                data = json.dumps(values[self.path]).encode(); self.send_response(200); self.end_headers(); self.wfile.write(data)
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                b = eb.EndpointBackend(self.args(base_url='http://127.0.0.1:%s/v1' % server.server_port), folder, self.ledger())
                b.validate_service()
                messages = [{'role': 'user', 'content': 'Task.'}]
                prep = b.rpc('prepare', messages=messages, thinking=False)
                r = b.rpc('generate', messages=messages, cap=2048, expected_input_tokens=prep['input_tokens'], remaining_seconds=60)
                self.assertEqual(prep['input_tokens'], 3); self.assertNotIn('reasoning_content', r['message'])
                self.assertEqual(r['reasoning_content'], 'do not reinject'); self.assertEqual(b.ledger['model_calls'], 1)
                self.assertEqual([s[0] for s in seen], ['/props', '/apply-template', '/tokenize', '/v1/chat/completions'])
                self.assertEqual(seen[-1][1]['tools'], eb.tools()); self.assertTrue(seen[-1][1]['cache_prompt'])
                self.assertEqual(seen[-1][2], 'Bearer synthetic-test-key')
                self.assertFalse(any('synthetic-test-key' in p.read_text() for p in Path(folder).rglob('*') if p.is_file()))
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_bad_server_context_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            b = eb.EndpointBackend(self.args(), folder, self.ledger())
            with patch.object(b, 'request', return_value={'default_generation_settings': {'n_ctx': 16384}}):
                with self.assertRaisesRegex(RuntimeError, 'SERVER_CONTEXT_MUST_BE_32768'): b.validate_service()
            self.assertEqual(b.ledger['model_calls'], 0)

    def test_generic_endpoint_custom_base_prefix(self):
        paths = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length'])); paths.append(self.path)
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'usage': {'prompt_tokens': 3, 'completion_tokens': 0, 'completion_tokens_details': {'reasoning_tokens': 0}},
                    'choices': [{'message': {'role': 'assistant', 'content': 'Done.'}, 'finish_reason': 'stop'}]}).encode())
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                b = eb.EndpointBackend(self.args(protocol='openai', top_k=0, tokenizer_command='trusted-counter',
                    base_url='http://127.0.0.1:%s/compatible/openai' % server.server_port), folder, self.ledger())
                result = b.rpc('generate', messages=[], cap=2048, expected_input_tokens=3, remaining_seconds=60)
                self.assertEqual(result['message']['content'], 'Done.')
                self.assertEqual(paths, ['/compatible/openai/chat/completions'])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_partial_cost_and_uncertain_close(self):
        with tempfile.TemporaryDirectory() as folder:
            b = eb.EndpointBackend(self.args(), folder, self.ledger())
            with patch.object(b, 'request', side_effect=RuntimeError('simulated disconnect')):
                with self.assertRaises(RuntimeError): b.rpc('generate', messages=[], cap=2048, expected_input_tokens=0, remaining_seconds=60)
            self.assertEqual(b.ledger['model_calls'], 1)
            self.assertEqual((b.ledger['generated_tokens_lower_bound'], b.ledger['generated_tokens_upper_bound']), (0, 2048))
            with self.assertRaisesRegex(RuntimeError, 'REMOTE_CLOSURE_UNPROVEN'): b.rpc('cancel')

    def test_absolute_deadline_handles_trickle(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.end_headers()
                for chunk in [b'{', b'"ok":', b'true}']:
                    self.wfile.write(chunk); self.wfile.flush(); time.sleep(.035)
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                b = eb.EndpointBackend(self.args(base_url='http://127.0.0.1:%s/v1' % server.server_port), folder, self.ledger())
                started = time.monotonic()
                with self.assertRaisesRegex(RuntimeError, 'TimeoutError'): b.request('/test', {}, timeout=.055)
                self.assertLess(time.monotonic() - started, .5)
                time.sleep(.12)
                self.assertFalse(list((Path(folder) / 'http').glob('*.response.json')))
                self.assertTrue(list((Path(folder) / 'http').glob('*.failure.json')))
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_budget_stops_before_request(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = self.ledger(); ledger['model_calls'] = 200
            b = eb.EndpointBackend(self.args(), folder, ledger)
            with patch.object(b, 'request') as req:
                self.assertEqual(b.rpc('generate', cap=2048)['ordinary_stop'], 'global_call_budget'); req.assert_not_called()

    def test_generic_payload_and_exact_counter(self):
        with tempfile.TemporaryDirectory() as folder:
            b = eb.EndpointBackend(self.args(protocol='openai', top_k=0, tokenizer_command='trusted-counter'), folder, self.ledger())
            body = b.body([], 2048)
            self.assertNotIn('top_k', body); self.assertNotIn('cache_prompt', body)
            self.assertEqual(body['tools'], eb.tools())
            result = SimpleNamespace(stdout=b'{"input_tokens": 321, "context": 32768}')
            with patch.object(eb.subprocess, 'run', return_value=result) as cmd:
                self.assertEqual(b.rpc('prepare', messages=[])['input_tokens'], 321)
                self.assertTrue(json.loads(cmd.call_args.kwargs['input'])['include_generation_prefix'])

    def test_generic_counter_matches_last_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = self.ledger(); ledger['model_calls'] = 4
            ledger['completion_attempts'] = [{'fixture': 'H-RC0', 'known_tokens': n, 'cap': 2048, 'reasoning_tokens': 0} for n in [2048, 2048, 2048, 2036]]
            b = eb.EndpointBackend(self.args(protocol='openai', tokenizer_command='trusted-counter'), folder, ledger); b.case_id = 'H-RC0'
            with patch.object(eb.subprocess, 'run', return_value=SimpleNamespace(stdout=b'{"input_tokens":321,"context":32768}')) as command:
                b.rpc('prepare', messages=[])
                self.assertEqual(json.loads(command.call_args.kwargs['input'])['body']['max_tokens'], 12)

    def test_explicit_sampler_options_are_active(self):
        with tempfile.TemporaryDirectory() as folder:
            b = eb.EndpointBackend(self.args(), folder, self.ledger())
            self.assertEqual(b.body([], 2048)['samplers'], ['top_k', 'top_p', 'temperature'])
            b.args.repeat_penalty = 1.1; b.args.dry_multiplier = .2; b.args.min_p = .05; b.args.xtc_probability = .1
            self.assertEqual(b.body([], 2048)['samplers'], ['penalties', 'dry', 'top_k', 'top_p', 'min_p', 'xtc', 'temperature'])

    def test_analyze_pre_episode_blocked_run(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / 'episodes').mkdir(); (out / 'run.json').write_text('{"order":[]}'); (out / 'closure.json').write_text('{"status":"BLOCKED"}')
            (out / 'costs.json').write_text('{"model_calls":0}')
            result = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'analyze.py'), folder], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report['summary']['unattempted']), 10)
            self.assertEqual(report['summary']['arms']['FC']['repair_denominator'], 0)
            self.assertEqual(report['costs']['model_calls'], 0)

    def test_cached_bad_wheel_fails_without_network(self):
        name = next(iter(json.loads((ROOT / 'cases-package/frozen_runtime/wheel_sha256.json').read_bytes())))
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / name).write_bytes(b'bad wheel')
            opener = SimpleNamespace(open=lambda *a, **kw: self.fail('network used for bad cached wheel'))
            with self.assertRaisesRegex(RuntimeError, 'CACHED_WHEEL_SHA256_MISMATCH'): fw.fetch(folder, opener)

    def test_pypi_metadata_hash_mismatch(self):
        hashes = json.loads((ROOT / 'cases-package/frozen_runtime/wheel_sha256.json').read_bytes()); name = sorted(hashes)[0]
        class Opener:
            def open(self, *args, **kw): return io.BytesIO(json.dumps({'urls': [{'filename': name, 'digests': {'sha256': '0' * 64}}]}).encode())
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'PYPI_METADATA_SHA256_MISMATCH'): fw.fetch(folder, Opener())
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_download_hash_mismatch_no_partial(self):
        hashes = json.loads((ROOT / 'cases-package/frozen_runtime/wheel_sha256.json').read_bytes()); name = sorted(hashes)[0]
        class Opener:
            def open(self, url, **kw):
                if 'pypi.org' in url:
                    return io.BytesIO(json.dumps({'urls': [{'filename': name, 'digests': {'sha256': hashes[name]},
                           'url': 'https://files.pythonhosted.org/one.whl', 'size': 3}]}).encode())
                return io.BytesIO(b'bad')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'DOWNLOADED_WHEEL_SHA256_MISMATCH'): fw.fetch(folder, Opener())
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == '__main__': unittest.main(verbosity=2)
