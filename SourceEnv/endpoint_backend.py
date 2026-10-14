"""Trusted HTTP client; never imports candidate code or owns a model process."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import copy, json, math, re, shlex, subprocess, threading, time, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parent / 'source'))
from critical_guards import ensure
from native_api import template_payload, tools

CONTEXT_SIZE = 32768
APPROXIMATE_CONTEXT_LIMIT = CONTEXT_SIZE * 85 // 100


def context_accounting(args):
    if args.backend == 'scripted':
        return 'synthetic'
    return 'approximate' if args.protocol == 'openai' and not args.tokenizer_command else 'exact'


class NoEndpointRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('ENDPOINT_REDIRECT_BLOCKED')


class EndpointBackend:
    def __init__(self, args, output, ledger):
        self.args, self.output, self.ledger = args, Path(output), ledger
        self.root_url = args.base_url.rstrip('/')
        if args.protocol == 'llama-cpp' and self.root_url.endswith('/v1'):
            self.root_url = self.root_url[:-3]
        self.pieces = {}
        self.case_id = None
        self.http_index = 0
        self.context_accounting = 'approximate' if args.protocol == 'openai' and not args.tokenizer_command else 'exact'
        self.context_history = {}
        self.prepared_context = {}
        self.global_deadline = ledger['started_monotonic'] + ledger['limits']['machine_seconds']
        ensure(self.root_url.startswith(('http://', 'https://')), 'HTTP_BASE_URL_REQUIRED')
        parsed = urllib.parse.urlsplit(self.root_url)
        ensure(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment, 'CREDENTIAL_FREE_BASE_URL_REQUIRED')
        # Do not use proxy environment variables: credentials are sent only to
        # the explicit endpoint. TLS uses the standard certificate verifier.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoEndpointRedirect())

    def persist(self):
        self.ledger['machine_seconds'] = time.monotonic() - self.ledger['started_monotonic']
        attempts = self.ledger['completion_attempts']
        known = sum(a['known_tokens'] or 0 for a in attempts)
        self.ledger['generated_tokens_lower_bound'] = known
        self.ledger['generated_tokens_upper_bound'] = known + sum(a['cap'] for a in attempts if a['known_tokens'] is None)
        # The aggregate alias is exact only when every attempt has known usage.
        # Unknown/possibly started requests retain their existing cost bounds.
        self.ledger['generated_tokens'] = known if all(a['known_tokens'] is not None for a in attempts) else None
        self.ledger['reasoning_tokens_lower_bound'] = sum(a.get('reasoning_tokens') or 0 for a in attempts)
        self.ledger['reasoning_tokens_upper_bound'] = self.ledger['reasoning_tokens_lower_bound'] + sum(
            a['cap'] if a['known_tokens'] is None else a['known_tokens']
            for a in attempts if a.get('reasoning_tokens') is None)
        (self.output / 'costs.json').write_text(json.dumps(self.ledger, indent=2) + '\n', encoding='utf-8')

    def request(self, path, payload=None, timeout=60):
        remaining = self.global_deadline - time.monotonic()
        ensure(remaining > 0, 'GLOBAL_WATCHDOG')
        self.http_index += 1
        folder = self.output / 'http'
        folder.mkdir(exist_ok=True)
        prefix = folder / ('%05d' % self.http_index)
        prefix.with_suffix('.request.json').write_text(json.dumps({'fixture': self.case_id, 'path': path, 'body': payload}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        headers = {'Content-Type': 'application/json'}
        if self.args.api_key:
            headers['Authorization'] = 'Bearer ' + self.args.api_key
        route = path[3:] if self.args.protocol == 'openai' and path.startswith('/v1/') else path
        req = urllib.request.Request(self.root_url + route, None if payload is None else json.dumps(payload, ensure_ascii=False).encode(),
                                     headers=headers, method='GET' if payload is None else 'POST')
        try:
            result = {}; done = threading.Event(); absolute_timeout = min(timeout, remaining)
            def receive():
                try:
                    with self.opener.open(req, timeout=absolute_timeout) as response:
                        result['raw'] = response.read(64 * 1024 * 1024 + 1)
                except Exception as exc:
                    result['error_type'] = type(exc).__name__; result['http_status'] = getattr(exc, 'code', None)
                finally: done.set()
            threading.Thread(target=receive, daemon=True).start()
            if not done.wait(absolute_timeout):
                # Do not join a possibly stuck request or claim server closure.
                # The daemon cannot dispatch actions or write retained files.
                raise TimeoutError('HTTP_ABSOLUTE_DEADLINE_REMOTE_CLOSE_UNPROVEN')
            if 'error_type' in result:
                prefix.with_suffix('.failure.json').write_text(json.dumps({'error_type': result['error_type'],
                    'http_status': result['http_status'], 'retry': False}) + '\n')
                raise RuntimeError('HTTP_TRANSPORT_FAILURE')
            raw = result['raw']
            ensure(len(raw) <= 64 * 1024 * 1024, 'ENDPOINT_RESPONSE_TOO_LARGE')
            prefix.with_suffix('.response.json').write_bytes(raw)
            return json.loads(raw)
        except Exception as exc:
            # Error bodies may echo credentials; never log the request headers,
            # API key, URL query or an arbitrary remote exception string.
            if not prefix.with_suffix('.failure.json').exists():
                prefix.with_suffix('.failure.json').write_text(json.dumps({'error_type': type(exc).__name__, 'http_status': getattr(exc, 'code', None),
                     'retry': False, 'remote_close_proved': False}) + '\n')
            raise RuntimeError('ENDPOINT_REQUEST_FAILED:' + type(exc).__name__) from None

    def validate_service(self):
        if self.args.protocol == 'llama-cpp':
            props = self.request('/props')
            ensure(props['default_generation_settings']['n_ctx'] == 32768, 'SERVER_CONTEXT_MUST_BE_32768')
            (self.output / 'service_properties.json').write_text(json.dumps(props, indent=2) + '\n', encoding='utf-8')

    def body(self, messages, cap):
        a = self.args
        if a.protocol == 'llama-cpp':
            body = template_payload(messages, False)
            samplers = []
            if a.repeat_penalty != 1.0 or a.presence_penalty != 0.0 or a.frequency_penalty != 0.0: samplers.append('penalties')
            if a.dry_multiplier != 0.0: samplers.append('dry')
            samplers.extend(['top_k', 'top_p'])
            if a.min_p != 0.0: samplers.append('min_p')
            if a.xtc_probability != 0.0: samplers.append('xtc')
            samplers.append('temperature')
            body.update(top_k=a.top_k, repeat_penalty=a.repeat_penalty, min_p=a.min_p,
                        dry_multiplier=a.dry_multiplier, dry_sequence_breakers=['\n', ':', '"', '*'],
                        xtc_probability=a.xtc_probability, mirostat=0, samplers=samplers,
                        cache_prompt=a.cache_prompt, return_tokens=True, verbose=True)
        else:
            body = {'messages': messages, 'tools': tools(), 'tool_choice': 'auto', 'parallel_tool_calls': False}
            if a.top_k:
                body['top_k'] = a.top_k
            for key, default in [('repeat_penalty', 1.0), ('min_p', 0.0), ('dry_multiplier', 0.0), ('xtc_probability', 0.0)]:
                if getattr(a, key) != default: body[key] = getattr(a, key)
        body.update(model=a.model, max_tokens=cap, temperature=a.temperature,
                    top_p=a.top_p, seed=a.seed, presence_penalty=a.presence_penalty,
                    frequency_penalty=a.frequency_penalty, stream=False)
        return body

    def reasoning(self, raw):
        if self.args.protocol != 'llama-cpp':
            n = raw.get('usage', {}).get('completion_tokens_details', {}).get('reasoning_tokens')
            ensure(n is None or type(n) is int and 0 <= n <= raw['usage']['completion_tokens'], 'REASONING_TOKEN_USAGE')
            return n
        v = raw['__verbose']
        parts = []
        for token in v['tokens']:
            if token not in self.pieces:
                self.ledger['tokenizer_requests'] += 1
                self.pieces[token] = self.request('/detokenize', {'tokens': [token]})['content']
            parts.append(self.pieces[token])
        prefix = v['generation_settings'].get('generation_prompt', '')
        text = prefix + ''.join(parts)
        spans = [m.span() for m in re.finditer(r'<\|channel>thought[\s\S]*?(?:<channel\|>|\Z)', text)]
        n, pos = 0, len(prefix)
        for piece in parts:
            end = pos + len(piece)
            n += any(pos < b and end > a for a, b in spans)
            pos = end
        ensure(n <= raw['usage']['completion_tokens'], 'REASONING_TOKEN_USAGE')
        return n

    def approximate_prepare(self, messages):
        # Prior usage measures the preceding request, not its assistant reply.
        # The actual reply and public feedback are therefore part of the delta.
        prior = self.context_history.get(self.case_id)
        request_shape = {'tools': tools(), 'tool_choice': 'auto', 'parallel_tool_calls': False}
        same_prefix = prior is not None and prior['request_shape'] == request_shape and messages[:len(prior['messages'])] == prior['messages']
        if same_prefix:
            new_messages = messages[len(prior['messages']):]
            value = new_messages
            exact_history = prior['prompt_tokens']
            anchor = 'previous_usage'
        else:
            value = {'messages': messages, **request_shape}
            exact_history = None
            anchor = 'history_reset' if prior is not None else 'initial_estimate'
        new_bytes = len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) if value else 0
        estimated_new = (new_bytes + 2) // 3
        count = (exact_history or 0) + estimated_new
        prepared = {'input_tokens': count, 'context': CONTEXT_SIZE, 'context_accounting': 'approximate',
            'input_tokens_estimate': count, 'exact_history_prompt_tokens': exact_history,
            'estimated_new_bytes': new_bytes, 'estimated_new_tokens': estimated_new,
            'history_anchor': anchor, 'context_stop_limit': APPROXIMATE_CONTEXT_LIMIT}
        self.prepared_context[self.case_id] = {'messages': copy.deepcopy(messages), 'prepared': prepared,
                                              'request_shape': request_shape}
        return prepared

    def rpc(self, phase, **data):
        if phase == 'cancel':
            # A disconnected HTTP client cannot prove remote cancellation.
            # This is a global uncertain-close error, never claimed as censoring.
            raise RuntimeError('REMOTE_CLOSURE_UNPROVEN:STOP_REMAINDER')
        if phase == 'prepare':
            if self.args.protocol == 'llama-cpp':
                self.ledger['tokenizer_requests'] += 2
                prompt = self.request('/apply-template', template_payload(data['messages'], False))['prompt']
                tokens = self.request('/tokenize', {'content': prompt, 'add_special': True, 'parse_special': True})['tokens']
                ensure(type(tokens) is list and all(type(t) is int for t in tokens), 'TOKENIZER_TOKEN_IDS')
                prepared = {'input_tokens': len(tokens), 'context': 32768, 'rendered_prompt': prompt, 'token_ids': tokens}
            elif self.context_accounting == 'approximate':
                prepared = self.approximate_prepare(data['messages'])
            else:
                self.ledger['tokenizer_commands'] += 1
                consumed = sum(a['known_tokens'] or 0 for a in self.ledger['completion_attempts'] if a['fixture'] == self.case_id)
                reservation = min(2048, 8192 - consumed)
                ensure(reservation > 0, 'EXACT_COUNTER_RESERVATION')
                payload = {'model': self.args.model, 'body': self.body(data['messages'], reservation), 'include_generation_prefix': True}
                result = subprocess.run(shlex.split(self.args.tokenizer_command), input=json.dumps(payload).encode(),
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=True)
                prepared = json.loads(result.stdout)
                ensure(type(prepared.get('input_tokens')) is int and prepared['input_tokens'] >= 0 and
                       prepared.get('context') == 32768, 'EXACT_TOKENIZER_CONTRACT')
            prepared.setdefault('context_accounting', self.context_accounting)
            prepared.setdefault('context_stop_limit', CONTEXT_SIZE)
            self.persist()
            return prepared
        ensure(phase == 'generate', 'UNKNOWN_BACKEND_PHASE')
        ledger = self.ledger
        if ledger['model_calls'] >= ledger['limits']['model_calls']:
            return {'ordinary_stop': 'global_call_budget'}
        cap = data['cap']
        ensure(type(cap) is int and 0 < cap <= 2048, 'REPLY_RESERVATION_LIMIT')
        if self.context_accounting == 'approximate':
            prior = self.prepared_context.get(self.case_id)
            ensure(prior is not None and prior['messages'] == data['messages'] and
                   prior['prepared']['input_tokens'] == data['expected_input_tokens'], 'APPROXIMATE_PREPARED_IDENTITY')
            if data['expected_input_tokens'] + cap > APPROXIMATE_CONTEXT_LIMIT:
                return {'ordinary_stop': 'context_budget', 'context_accounting': 'approximate'}
        ensure(ledger.get('generated_tokens_upper_bound', 0) + cap <= ledger['limits']['generated_tokens'], 'GLOBAL_TOKEN_RESERVATION')
        ensure(time.monotonic() < self.global_deadline, 'GLOBAL_WATCHDOG')
        ledger['model_calls'] += 1
        attempt = {'index': ledger['model_calls'], 'fixture': self.case_id, 'cap': cap,
                   'known_tokens': None, 'reasoning_tokens': None, 'possibly_started': True,
                   'context_accounting': self.context_accounting, 'prepared_input_tokens': data['expected_input_tokens']}
        ledger['completion_attempts'].append(attempt)
        self.persist()  # Count an attempt before sending, including uncertain costs.
        raw = self.request('/v1/chat/completions', self.body(data['messages'], cap), timeout=data['remaining_seconds'])
        n = raw['usage']['completion_tokens']
        ensure(type(n) is int and 0 <= n <= cap, 'MODEL_TOKEN_ACCOUNTING')
        prompt_tokens = raw['usage']['prompt_tokens']
        ensure(type(prompt_tokens) is int and prompt_tokens >= 0, 'PROMPT_TOKEN_USAGE')
        attempt['reported_prompt_tokens'] = prompt_tokens
        if self.context_accounting == 'exact':
            ensure(prompt_tokens == data['expected_input_tokens'], 'REPLY_INPUT_TOKEN_IDENTITY')
        else:
            self.context_history[self.case_id] = {'messages': copy.deepcopy(data['messages']),
                'prompt_tokens': prompt_tokens, 'request_shape': self.prepared_context[self.case_id]['request_shape']}
        if self.args.protocol == 'llama-cpp':
            v = raw['__verbose']; settings = v['generation_settings']
            ensure(n == v['tokens_predicted'] and len(v['tokens']) == n and v['truncated'] is False, 'LLAMA_TOKEN_ACCOUNTING')
            ensure(math.isclose(settings['temperature'], self.args.temperature, abs_tol=1e-6) and
                   settings['top_k'] == self.args.top_k and math.isclose(settings['top_p'], self.args.top_p, abs_tol=1e-6), 'EFFECTIVE_SAMPLING_CHANGED')
        attempt['known_tokens'] = n
        self.persist()
        reasoning = self.reasoning(raw)
        attempt['reasoning_tokens'] = reasoning
        self.persist()
        ensure(len(raw['choices']) == 1, 'ONE_REPLY_REQUIRED')
        msg = copy.deepcopy(raw['choices'][0]['message'])
        thought = msg.pop('reasoning_content', None)
        msg.pop('reasoning', None)
        ensure(msg.get('role') == 'assistant', 'ASSISTANT_REPLY_REQUIRED')
        return {'message': msg, 'reasoning_content': thought, 'reasoning_tokens': reasoning,
                'generated_tokens': n, 'input_tokens': data['expected_input_tokens'],
                'reported_prompt_tokens': prompt_tokens, 'context_accounting': self.context_accounting,
                'finish_reason': raw['choices'][0]['finish_reason']}


class ScriptedBackend:
    """Development check only. Counts are synthetic, never model tokenization."""
    context_accounting = 'synthetic'
    def __init__(self, case, mode, root, ledger):
        self.ledger, self.case_id = ledger, case['case_id']
        self.actions = []
        if mode == 'reference':
            if case['category'] == 'environment':
                self.actions.append(('apply_profile', {'profile': case['reference_profile']}))
            else:
                self.actions.append(('write_file', {'path': 'app.py', 'content': (root / 'cases-package/cases' / self.case_id / 'reference.py').read_text(encoding='utf-8')}))
            self.actions.extend(('run_app', {'operation': op}) for op in ['first_command', 'second_command', 'no_args', 'explicit_help', 'first_command_help', 'second_command_help'])
        self.index = 0

    def rpc(self, phase, **data):
        if phase == 'prepare':
            return {'input_tokens': 0, 'context': 32768, 'synthetic_not_model_tokenization': True}
        ensure(phase == 'generate', 'SCRIPTED_BACKEND_PHASE')
        tool, args = self.actions[self.index] if self.index < len(self.actions) else ('finish', {'summary': 'Scripted control.'})
        self.index += 1
        self.ledger['scripted_replies'] += 1
        msg = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'script-' + str(self.index),
               'type': 'function', 'function': {'name': tool, 'arguments': json.dumps(args, ensure_ascii=False)}}]}
        return {'message': msg, 'generated_tokens': 0, 'input_tokens': 0, 'reasoning_tokens': 0, 'finish_reason': 'tool_calls'}
