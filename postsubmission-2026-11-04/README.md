# Post-submission addendum (2026-11-04)

This folder records model-free checks run **after** the Kaggle submission of 2026-10-14. It does **not** change the submitted writeup, the `v1.0.0-rc3` release or its assets, `SourceEnv/`, `paper/`, `release-info/` or any R3 result. Nothing here is part of the predeclared R3 study. No Gemma inference was run.

Status labels used below:
- **MEASURED** means executed and retained.
- **POST-HOC** means defined after the R3 data had been seen.
- **SYNTHETIC** means a hand-written control, not model output.

## 1. The public rc3 ZIP, executed (MEASURED)

The release asset `SourceEnv-1.0.0-rc3.zip` was downloaded from this repository's release inside Debian. Its SHA-256 was `7a59f1c3…`, as expected, and its CRC check passed. It was then run once, without retries.

- **Machine.** Debian 13.7, kernel 6.12.107, Python 3.13.5, Bubblewrap 0.12.0, ordinary UID. This was a **new qcow2 overlay of the 2026-10-13 fresh-install disk**, which had already been used for the rc2 clean check. It was **not a new installation**.

| Step | Result |
|---|---|
| `reproduce.py --verify-only`, before and after | PASS; manifest `a6e4d165…` |
| `tests/` (portable, validate_fixture, context, costs) | 4/4 PASS |
| `fetch_wheels.py` (10 pinned wheels from PyPI, hash-checked) | PASS |
| `reproduce.py`, 16 scripted episodes | PASS. **0 field differences** from the rc2 `SourceEnv/evidence/resolvability.json`, excluding episode hashes, state identities and timings. Costs: 288 applications, 32 probes, 140 workers, 20 installs, 193.5 s |
| `validate_fixture.py --selection new-coverage`, 24 scenarios | 24/24 expectations PASS (14 oracle PASS, 10 expected FAIL) |
| `run_agent.py --backend scripted` reference / noop, 8 fixtures | Reference 8/8 PASS in FC and BASE; noop 0/8 in both |

Files are in [rc3-execution/](rc3-execution/). The comparison script is `compare_rc3_rc2.py`. Raw states and installed environments are retained privately and are not published here.

## 2. Executable claims ledger (MEASURED, offline)

[claims-ledger/claims_ledger.py](claims-ledger/claims_ledger.py) recomputes every registered phrase of the manuscript from [`paper/evidence/`](../paper/evidence/) and exits 1 on any mismatch. The phrases cover Tables 2 and 3, costs, invalid responses, accepted and rejected closures, discordance, P3 and the absence of profile changes. **Result: 22/22 PASS** against the submitted manuscript. Where possible, each phrase was also cross-checked against the retained raw R3 endpoint snapshots.

Of the manuscript's 88 numerals, 39 are not yet registered. They are years, arXiv IDs, configuration values, external-audit counts (M01/M02) and the P3 threshold; they are listed in `CLAIMS_LEDGER.json`.

The ledger also accepts the public snapshot `paper/DRAFT.md`, which differs from the submitted text only in five link and availability lines. [notebook-draft/](notebook-draft/) runs the ledger on a CPU using only the standard library. It was tested offline; it **has not been run on Kaggle** and is not published there.

## 3. R3 endpoint sources (MEASURED, extracted offline)

The scorer retained the `app.py` bytes of all 40 R3 endpoints. [r3-endpoints/](r3-endpoints/) contains those bytes, the raw diffs and the diffs normalized for line endings and blank lines.

**Clarification of the manuscript's byte-level counts.** "Effective source change" means a change in byte identity. Four R3 edits are rewrites of line endings only: C1 SH-FLAG, SH-FORMAT, EH-RENDERER and H-RC2. So of the "three of four physical healthy episodes [that] effectively edited source", one (C1/H-RC2) changed line endings only.

## 4. Counterfactual-environment differential, CED (POST-HOC, MEASURED, not predeclared)

**Idea.** In the four environment fixtures, `reference.py` is byte-identical to `initial.py`, and the reference repair is only `apply_profile(reference_profile)`. The original program under the restored profile is therefore an executable specification of intended behavior, and the contract oracle never consults it.

**Method.** A retained source *c* that closes an environment failure is scored in fresh states under the damaged and the restored profile. Its exact captures (rc, stdout, stderr) on the six operations are compared with that specification, run twice to check determinism. Each candidate is classified as:
- **ENV_COUPLED**: FAIL when restored;
- **DIVERGENT_UNDER_RESTORATION**: PASS, but with differing captures;
- **OBSERVATIONALLY_EQUIVALENT**: PASS with no difference on the six operations only. This does not prove the patch harmless.

**Seal.** The protocol, predictions and plan were hashed **before execution**: [ced/PROTOCOLO_CED_POSTHOC.md](ced/PROTOCOLO_CED_POSTHOC.md), written in Spanish, together with its `.sha256` file. The R3 diffs had already been seen, so the check is post-hoc.

**Execution.** The [runner](ced/masking_check.py) imports rc3's unchanged oracle, dispatcher, `offline.prepare` and Bubblewrap launcher, with budgets, no fallback and no retries. The run used 61 fresh states, 366 applications and 173.7 s. No model was involved.

| Candidate | Origin | Damaged | Restored | Δ vs specification | Class |
|---|---|---|---|---|---|
| specification ×2, 10 fixtures | author | — | PASS/PASS | empty determinism floor in 10/10 | — |
| EH-RENDERER `alternative.py` (try rich / print) | author | PASS | PASS | ∅ | EQUIVALENT |
| EC-SYMBOL `alternative.py` | author | PASS | PASS | ∅ | EQUIVALENT |
| SYN-HARDCODED-HELP | SYNTHETIC | PASS | PASS | 4 help ops | DIVERGENT |
| SYN-ENV-COUPLED | SYNTHETIC | PASS | FAIL | 4 | ENV_COUPLED |
| SYN-EOL-ONLY | SYNTHETIC | FAIL | PASS | ∅ | does not close |
| **R3 C3 FC, EH-RENDERER (Gemma 4 E4B)** | model | **PASS** | **PASS** | **no_args, explicit_help, both command helps: the original "Command reference" line is gone** | **DIVERGENT** |
| R3 C3 EC-SYMBOL (FC = BASE bytes) | model | PASS | PASS | ∅; an unreachable `if not DATA` branch was deleted, which the static diff shows | EQUIVALENT |
| R3 C1 EC-SYMBOL (FC = BASE bytes) | model | PASS | PASS | ∅ | EQUIVALENT |
| R3 C3 / C1 EC-MISSING, C1 EH-RENDERER | model | FAIL | PASS | 4 / ∅ / ∅ | do not close |
| R3 healthy C3 H-RC0, C3 H-RC2 | model | — | PASS | 4 help ops (docstrings rewritten) | PASS with changed help |

**Results.**
- All 15 prediction rows held. None of the three pre-stated refutation conditions occurred.
- **Model output.** Of the three Gemma source repairs that closed an environment failure, one passes under both environments but deletes original behavior. That one is the only C3 repair that FC added over BASE (the EH-RENDERER discordance in the paper). The other two are equivalent on the probed operations.
- **Controls.** The SYNTHETIC and author rows validate the mechanism only; they are not model results.
- **Limits.** n = 3, one seed, synthetic author-visible fixtures from one family, six probed operations. This demonstrates the mechanism and estimates no rate.

[ced/score-excerpts/](ced/score-excerpts/) holds the raw scores for the EH-RENDERER comparison.

**Related work.** DEPBENCH (arXiv 2608.30300, §III-D) introduced the four-state dependency oracle and, in §VI, names downgrades and weakened validation as unmeasured risks. PATCH-SIM (Xiong et al., ICSE 2018) compares the runtime behavior of original and patched programs. Smith et al. (FSE 2015) studied overfitting. CED claims no priority for counterfactual oracles or behavior comparison. Its narrower point is that restoring the environment turns the original program into an exact behavioral specification, which exposes code-level masking that a contract oracle passes.

## Integrity

`SHA256SUMS.txt` lists every file in this folder. To reproduce section 1, follow `SourceEnv/CLEAN_MACHINE.md` together with `rc3-execution/rc3_guest_steps.py`. To reproduce section 4, run `ced/masking_check.py` with the extracted rc3 package, `ced/masking_plan/` and the pinned wheels; it requires Debian with Bubblewrap. Section 3 needs the private R3 evidence ZIP. Its outputs are published here, but the input is not.
