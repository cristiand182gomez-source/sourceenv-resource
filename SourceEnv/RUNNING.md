# Running SourceEnv

## Reproduce the non-model baselines with one command

From this directory on Debian, as an unprivileged account:

```sh
/usr/bin/python3 -I -S reproduce.py --wheelhouse /opt/sourceenv-wheels
```

This creates `../sourceenv-scripted-output` and refuses to overwrite it. It runs **16 scripted episodes, no model**: a reference repair and an always-finish noop for each of the eight damaged fixtures. Environment references use `apply_profile`; source references use `write_file`. References run all six operations and finish. Noop requests only finish: BASE closes immediately; FC reaches its unchanged 20-action budget. Initial, terminal and checkpoint scores are retained before cleanup; no cleanup is performed. Inspect `resolvability.json`, `costs.json`, `closure.json` and per-fixture raw records in that output directory. These new local records may contain local paths; they are not intended for redistribution.

Requirements: Debian Linux, trusted `/usr/bin/python3` (validated with Python 3.13.5), standard-library `venv`, Bubblewrap, and enabled unprivileged user/PID/network namespaces. Provide the ten original wheels in an external directory (the example uses `/opt/sourceenv-wheels`). Exact filenames and SHA256 are in `cases-package/frozen_runtime/wheel_sha256.json`; version pins are in `requirements-wheels.txt`. Obtain these prerequisites separately from the respective upstream distributions. All ten must pass hash verification before any application is launched. The command copies them into immutable evaluator inputs outside this public directory. Root, optimized Python and unavailable isolation block execution. Reserve 500 MB of writable space for retained scripted states; requirements can differ with the interpreter version. No pip, network, credentials, model, inference service or administrative bridge is used by reproduction. Full license notices are included; dependency wheels are excluded because upstream code/docstrings contain generic platform path examples. There is no unsafe sandbox fallback.

```sh
/usr/bin/python3 -I -S reproduce.py --verify-only
python3 -B analyze.py
```

The second command summarizes the released r3 aggregate rows. `analyze.py episode1.json ...` applies the retained r3 metrics to independently available raw native logs. `analyze.py /path/to/run-output` reads the result directory produced by `run_agent.py` directly, including partial runs and their costs. Analyze separate runs separately. Public aggregates alone cannot reconstruct withheld conversations or independently verify every trajectory-derived metric.

## Evaluate your agent

Start an OpenAI-compatible server separately; the evaluator never starts, restarts or owns it. For example, with a separately installed llama.cpp server and a model that supports native tools:

```sh
llama-server -m /opt/models/model.gguf --alias sourceenv-agent --host 127.0.0.1 --port 8080 -c 32768 -np 1 --jinja --reasoning off --reasoning-format deepseek --no-reasoning-preserve --no-context-shift --cache-prompt --cache-ram 0 --no-warmup --no-webui --offline
```

Obtain the exact dependency inputs once (this is the only dependency-fetch step with network):

```sh
/usr/bin/python3 -I -S fetch_wheels.py ../sourceenv-wheels
```

Then evaluate all ten fixtures in the retained r3 order and analyze the output:

```sh
/usr/bin/python3 -I -S run_agent.py --base-url http://127.0.0.1:8080/v1 --model sourceenv-agent --wheelhouse ../sourceenv-wheels --output ../agent-results
/usr/bin/python3 -I -S analyze.py ../agent-results --output ../agent-analysis.json
```

Each physical episode uses FC; BASE is derived before the first valid closure reaches the FC policy. No independent BASE generations or generative preflights are made. The tools, prompts, public feedback, six-operation oracle and independent arm availability are the retained r3 implementation. Limits per fixture: 20 actions, 12 application requests, 3 parsed profile requests (noop/invalid included; the fourth stops), 2,048 tokens per reply, 8,192 per episode, 32,768 context and a 14,400-second watchdog. Ten fixtures: at most 200 generation attempts, 81,920 generated tokens, 300 application captures, 20 isolation probes, 520 workers, 40 offline installations, 10 fresh states and 43,200 seconds. Setup and scoring count separately from the episode clock but toward global costs. No retries, replacements or cleanup. Raw conversations, captures, states and scores stay in the output directory; do not publish them without checking for private data. The caller stops its server after evaluation.

Defaults are r3: temperature 1.0, top_k 64, top_p 0.95, seed 0, repeat_penalty 1, presence/frequency penalties 0, min_p 0, dry_multiplier 0, xtc_probability 0, thinking OFF, cache_prompt enabled, no reasoning reinjection. All these decoding numbers have corresponding CLI options, for example `--temperature`, `--top-k`, `--repeat-penalty` and `--presence-penalty`; `--no-cache-prompt` disables the cache. Changed decoding choices differ from r3. `--api-key` is optional; prefer `OPENAI_API_KEY` to keep it out of shell history. The key stays in the trusted HTTP client and is absent from candidate mounts and recorded request headers. Candidate applications have no network.

For a different OpenAI-compatible provider, select `--protocol openai`. The provider's full base URL prefix is respected. Native tools and OpenAI sampling fields are sent; top_k is also sent when nonzero. Use `--top-k 0` for providers without that extension, recording the decoding difference. Llama-specific cache/thinking options are not sent in generic mode; configure thinking OFF at the provider and check its effective settings. Rejected options or missing/invalid usage stop the run; fields are never silently removed. Provider reasoning-token counts are retained when supplied, otherwise bounded as unknown. Reasoning is never reinserted in history.

### Approximate context for generic endpoints

Without `--tokenizer-command`, `--protocol openai` uses `context_accounting: "approximate"`. The last successful response's `usage.prompt_tokens` is the exact, provider-reported count of the **previous request**. It does not cover that response's assistant message. The next estimate adds `ceil(new UTF-8 JSON bytes / 3)` for all messages added since that request, including the assistant reply/tool calls and public tool feedback. JSON role/argument wrappers are included. Prior reasoning is excluded because it is not reinjected. Tools are already covered by the anchor. If no anchor exists (including the first turn), the complete messages plus native tool schema/choice are estimated. Changed history or tool schema resets the anchor and estimates the complete request. Anchors are independent by fixture.

Stop before generating if **estimated input + actual reply reservation > 27,852**, the rounded-down 85% of 32,768. Equality is allowed. The reservation is at most 2,048 and shrinks with the remaining episode token budget. This is an ordinary `context_budget` terminal: score the retained state and derived BASE under the existing availability rules, with no reset/exclusion. The immutable core adapter still checks 32,768; the endpoint wrapper additionally enforces the stricter approximate threshold before sending a request.

Bytes/3 plus 15% headroom is a conservative heuristic, not a proven upper bound for every tokenizer/template. The total is **not exact**: only the anchored prefix is exact as reported by the endpoint. Every episode (including setup failures), its derived BASE, run metadata, costs and analyzer output record the accounting mode. Prepared turns retain the anchor, delta bytes/tokens, estimate and threshold. `reply.reported_prompt_tokens`/the raw usage preserve the actual count; `reply.input_tokens` remains the accounting value matched to preparation by the unchanged adapter. These fields must not be mistaken for two measured counts. Approximate runs are not exact-context replications of r3.

### Exact context

`--protocol llama-cpp` is the default and always uses exact accounting: `/apply-template`, `/tokenize`, `/detokenize` and `/v1/chat/completions`. Its prepared template includes the generation prefix. The actual server context must be 32,768; actual prompt usage must match the prepared count. Its cut remains input plus reservation > 32,768.

Generic endpoints can also use exact accounting with `--tokenizer-command '/path/to/trusted-exact-counter'`. Standard chat APIs do not provide template tokenization before generation. This local trusted command receives JSON stdin with `model`, the request `body` including its actual remaining reply reservation, and `include_generation_prefix: true`. It must return the actual complete template count as integer `input_tokens` and `context: 32768`. A tokenizer for another model or a text-only estimate is insufficient. Completion prompt usage must agree with preparation. Adding this option selects `context_accounting: "exact"` and the full 32,768 context guard.


In llama.cpp mode, explicitly changed penalty/DRY/min_p/XTC settings activate their corresponding samplers. The default sampler chain remains exactly r3's `top_k`, `top_p`, `temperature`. `PACKAGE_MANIFEST.json` is the current distribution inventory. `cases-package/manifest.json` is retained historical input provenance; task entries refer to original bytes before the training-exclusion comments, and external wheels are intentionally absent from this distribution.

Model weights and runtime binaries are not included. A timeout or transport failure cannot prove cancellation in a server owned by someone else: retain independently valid BASE, mark FC unavailable, bound unknown generation cost by the reserved reply tokens, and stop the remainder. This is a limitation of externally owned endpoints, not a successful server-close claim.

The non-model runner check uses `--backend scripted --control reference` or `--control noop` and `--fixtures` for a subset. Its context counts are deliberately marked synthetic; they are not model token measurements. See `CLEAN_MACHINE.md` for the clean Debian procedure.


## Tests

```sh
/usr/bin/python3 -I -S tests/test_portable.py
/usr/bin/python3 -I -S tests/test_context.py
```

These use scripted backend responses and local HTTP sockets; no model or candidate application is executed. The adapter context-terminal test requires the trusted Debian interpreter. See `CLEAN_MACHINE.md` for an independent integration smoke, its retry policy and local E2B server.

Cost accounting: generated_tokens is the exact aggregate when all requests have known usage, otherwise null. The existing lower/upper bounds retain uncertain partial costs. analyze.py normalizes the stale aggregate alias in older public-runner logs from those retained bounds and records the correction without changing raw evidence.
