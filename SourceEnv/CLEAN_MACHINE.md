# Clean Debian 13 check

This procedure documents a new Debian 13 installation. The historical check of the earlier public package completed on a fresh Debian 13.7 installation, including both scripted drivers and one E2B smoke; see `HISTORICAL_CLEAN_CHECK.md` for component identities and the later cost-alias correction. Release 1.0.0-rc2 was checked without a model on an overlay of that retained installation, not on a newly installed machine. Release 1.0.0-rc3 only corrects the extraction-root name and updates distribution documentation/identities. Its components are byte-equivalent to those tested in rc2; the rc3 ZIP was not executed. The external documentary addendum links both archives and the unchanged rc2 execution receipt.

**For model-free release validation, execute steps 1–3 and 5 only. Skip all of step 4: do not download or start a model.** Reuse exact prior component evidence where documented; the added `validate_fixture.py` has its own explicit matrix/budgets in `FIXTURES.md`. A candidate may run only after all isolation guards pass.

1. Install Debian 13, create an ordinary unprivileged account and obtain the package through local removable media. OS prerequisites are `/usr/bin/python3` (Python 3.13), the standard-library venv module, Bubblewrap, CA certificates, GNU grep and curl. Install them as administrator from your Debian package source; this OS provisioning is separate from the benchmark's wheel fetch. If network is unavailable, supply the Debian packages and their dependencies from installation media/local package cache:

   ```sh
   sudo apt-get install python3 python3-venv bubblewrap ca-certificates grep curl
   /usr/bin/python3 --version
   bwrap --version
   ```

2. Return to the ordinary account. Extract `SourceEnv/` beneath its writable working directory; run the following inside that directory. Never run the evaluator as root, with `-O`, or without `-I -S`. Do not disable or bypass isolation if a probe fails. The package must remain unchanged; outputs and wheels go into siblings.

   ```sh
   /usr/bin/python3 -I -S reproduce.py --verify-only
   /usr/bin/python3 -I -S tests/test_portable.py
   /usr/bin/python3 -I -S fetch_wheels.py ../sourceenv-wheels
   /usr/bin/python3 -I -S reproduce.py --wheelhouse ../sourceenv-wheels --output ../scripted-resolvability
   ```

   Expected: ten wheels verified; 16 scripted episodes; eight reference PASS/PASS endpoints and eight noop FAIL/FAIL endpoints, six current operations for references and zero for noops. Noop FC stops at `action_budget`, BASE at its first `finish`. Model calls and generated tokens are zero. Inspect `resolvability.json`, `costs.json`, `closure.json`, `capture_ledger.json` and retained per-case states. Failures are evidence; do not relaunch over an existing directory.

3. Test the new runner without a model. The environment references must select a profile, and the source references must write their reference source. The two output directories must be new:

   ```sh
   /usr/bin/python3 -I -S run_agent.py --backend scripted --control reference --fixtures EH-API SC-BALANCE EC-MISSING SH-FLAG EH-RENDERER SC-SORT EC-SYMBOL SH-FORMAT --wheelhouse ../sourceenv-wheels --output ../runner-reference
   /usr/bin/python3 -I -S run_agent.py --backend scripted --control noop --fixtures EH-API SC-BALANCE EC-MISSING SH-FLAG EH-RENDERER SC-SORT EC-SYMBOL SH-FORMAT --wheelhouse ../sourceenv-wheels --output ../runner-noop
   /usr/bin/python3 -I -S analyze.py ../runner-reference --output ../reference-analysis.json
   /usr/bin/python3 -I -S analyze.py ../runner-noop --output ../noop-analysis.json
   ```

   Expected endpoints, action/run/install counts, operation checks, coverage and changes match `evidence/resolvability.json`. Health traces are complete. Scripted counts are not a measurement of a model's tokenization.

4. Integration smoke with E2B **inside this same VM**. Smoke tests are independent diagnostics: they require no additional human authorization and consume no prospective/confirmatory experiment attempts. A connectivity failure can be retried after fixing the network. This does not authorize relaunching historical frozen studies. Preserve each smoke's logs and actual generation/application costs; these costs do not disappear because the check is diagnostic. There are no automatic retries in `run_agent.py`, and each invocation still respects its per-fixture limits. Use a new output directory after an unsuccessful invocation; never overwrite evidence.

   Provide a separately licensed Gemma 4 E2B Q4_0 GGUF at `../models/e2b.gguf` and an already installed Linux llama.cpp server with native Gemma tools/Jinja support (the retained study used build b11429). The package does not download runtimes or models. Use two terminals within the VM; no reverse SSH forwarding is needed. In terminal A, from the package directory:

   ```sh
   llama-server -m ../models/e2b.gguf --alias sourceenv-agent --host 127.0.0.1 --port 8080 -c 32768 -np 1 --jinja --reasoning off --reasoning-format deepseek --no-reasoning-preserve --no-context-shift --cache-prompt --cache-ram 0 --no-warmup --no-webui --offline
   ```

   In terminal B, from the same directory, check reachability before invoking the evaluator. If the non-generative readiness check fails, stop, fix the server/network and repeat it; no episode has started:

   ```sh
   curl --fail --silent --show-error http://127.0.0.1:8080/props
   ```

   Once ready, run only the healthy fixture, then analyze it:

   ```sh
   /usr/bin/python3 -I -S run_agent.py --fixtures H-RC0 --base-url http://127.0.0.1:8080/v1 --model sourceenv-agent --wheelhouse ../sourceenv-wheels --output ../smoke-H-RC0-01
   /usr/bin/python3 -I -S analyze.py ../smoke-H-RC0-01 --output ../smoke-H-RC0-01-analysis.json
   ```

   Confirm preserved conversations, ordinary terminals or errors, independent FC/BASE availability, costs and `context_accounting: "exact"`. PASS is a behavioral result, not guaranteed by endpoint integration. For a smoke repeated after repairing connectivity, use e.g. `../smoke-H-RC0-02` and its matching analysis filename. If a request may have reached the server, retain the partial token cost bounds and uncertain-close status rather than claiming zero cost. Close the previous server/request before starting the repaired diagnostic. For other endpoints, `--protocol openai` defaults to approximate context; supply `--tokenizer-command` to select exact accounting. See RUNNING.md.

5. Check integrity again, then inspect analysis and raw evidence. Avoid placing credentials in the package or logs. Keep private outputs outside the distribution. Stop any separately started model server. Reversal requires only removing the new output/wheel directories you created after inspecting their absolute paths; no OS settings or historical experiment files are changed by the evaluator.

   ```sh
   /usr/bin/python3 -I -S reproduce.py --verify-only
   /usr/bin/python3 -I -S analyze.py
   ```
