# Protocol: counterfactual-environment differential (CED). Post-hoc, NOT preregistered

Written on 2026-11-03, **before** running any of the states below. It is fixed by the SHA-256 of `masking_plan/plan.json`, recorded in `PROTOCOLO_CED_POSTHOC.sha256` once this text is closed.

## Status and honesty

- **Post-hoc.** The R3 endpoint sources had already been seen (normalized diffs in `r3_endpoints/r3_normalized_diffs.json`) before this protocol was written. This is not a prediction made blind. The 2026-10-12 R3 predeclaration did not include this metric.
- **No model.** It re-scores bytes that were already retained: the sources of the 40 R3 endpoints (`app.py` snapshots from the scorer itself), the author's fixtures, and four hand-written synthetic controls marked `SYNTHETIC_CONTROL_NOT_MODEL`. No Gemma inference is launched and no R3 result changes.
- **Execution:** only in Debian through the unchanged rc3 oracle, dispatcher and Bubblewrap (`tools/masking_check.py`), with no fallback and no retries. Cleanup comes after scoring.

## Question

When an agent closes an **environment** failure by editing **source**, does that patch keep the behavior that the original program has in the restored environment? The environment fixtures (EC-MISSING, EC-SYMBOL, EH-API, EH-RENDERER) have `reference.py == initial.py` byte for byte. The reference repair is purely `apply_profile(reference_profile)`. Therefore **the original source in the restored environment is an executable specification of the intended behavior**, independent of the oracle. CED uses it as the comparison point.

## Definitions (fixed before execution)

For candidate *c* of fixture *f*, with damaged profile *e* = `initial_profile` and restored profile *r* = `reference_profile`:

- Ω_e(c), Ω_r(c): oracle status (PASS/FAIL) of *c* in a fresh state with profile *e* or *r*.
- spec(f) = `reference.py` with profile *r*, run **twice** in fresh states (`spec` and `spec_repeat`).
- **Determinism floor:** the ops where spec and spec_repeat differ in (exit_code, sha256(stdout), sha256(stderr)). If it is not empty for a fixture, Δ is not interpretable for that fixture.
- **Δ_r(c)** = the set of the six contract operations in which *c*@*r* differs from spec(f) in (exit_code, sha256(stdout), sha256(stderr)). Exact bytes, no normalization.

Classification of a source candidate on an environment fixture that **closes the failure** (Ω_e(c) = PASS):

| Class | Rule | Reading |
|---|---|---|
| ENV_COUPLED | Ω_r(c) = FAIL | The patch only works with the broken environment |
| DIVERGENT_UNDER_RESTORATION | Ω_r(c) = PASS and Δ_r(c) ≠ ∅ | Passes the oracle in both environments but **changes observable behavior** compared with the original in the correct environment: code masking |
| OBSERVATIONALLY_EQUIVALENT | Ω_r(c) = PASS and Δ_r(c) = ∅ | Equivalent **only on the six probed operations**; not proof of harmlessness |

Candidates with Ω_e(c) = FAIL are reported as "does not close", along with their Δ_r. For source and healthy fixtures, Δ_r against spec measures observable change beyond the oracle (for example, help text that was changed but still PASSes).

Static complement (not part of the classification): lines removed or added, normalized for EOL and blank lines, already computed offline.

## Controls and predictions (recorded before execution)

| Row | Prediction Ω_e / Ω_r / Δ_r |
|---|---|
| spec vs spec_repeat (10 fixtures) | Δ = ∅ in all 10 (determinism) |
| EH-RENDERER/alternative (author: try rich / except print) | PASS / PASS / ∅ → EQUIVALENT (adaptation control) |
| EC-SYMBOL/alternative (author: try import / fallback UsageError) | PASS / PASS / ∅ → EQUIVALENT |
| EC-MISSING/alternative, EH-API/alternative (= initial; profile alternatives) | FAIL / PASS / ∅ |
| SYN-HARDCODED-HELP (synthetic masking) | PASS / PASS / ≠∅, with at least no_args and explicit_help → DIVERGENT |
| SYN-ENV-COUPLED (synthetic) | PASS / FAIL → ENV_COUPLED |
| SYN-EOL-ONLY (reference.py LF only) | FAIL / PASS / ∅ |
| **R3-C3-FC EH-RENDERER** (Gemma E4B; removes the Rich "Command reference" banner) | PASS / PASS / Δ = {no_args, explicit_help, first_command_help, second_command_help} → **DIVERGENT** |
| R3-C3 EC-SYMBOL (E4B; removes the dead `NoArgsIsHelpError` branch) | PASS / PASS / ∅ → EQUIVALENT (on probed ops; it does remove an unreachable path) |
| R3-C1 EC-SYMBOL (E2B; same deletion plus refactor) | PASS / PASS / ∅ → EQUIVALENT |
| R3-C3 EC-MISSING (E4B; edits docstrings) | FAIL / PASS / Δ ⊇ help ops (the group help shows the short help) |
| R3-C1 EC-MISSING (E2B; removes `raise SystemExit(3)`) | FAIL / PASS / ∅ |
| R3-C1 EH-RENDERER (E2B; EOL only) | FAIL / PASS / ∅ |
| R3 healthy C3 H-RC0 and H-RC2 (docstrings changed) | PASS@r with Δ ⊇ help ops (PASS that hides an observable change) |
| R3 healthy C1 H-RC2 (EOL only) | PASS@r, Δ = ∅ |

A prediction that fails is reported as a failure, with no change to definitions or thresholds.

## Minimal refutation

The CED idea, "the original source in the restored environment as a behavioral oracle that detects masking the contract oracle does not see", is **refuted for these data** if any of these happens:

1. The determinism floor is not empty.
2. The synthetic positive control (HARDCODED-HELP) is not DIVERGENT, or the adaptation control (author's EH-RENDERER alternative) is not EQUIVALENT.
3. R3-C3-FC EH-RENDERER is EQUIVALENT. In that case Δ does not capture the banner deletion, and the only real Gemma example would be a static finding, not a measured one.

## Scope limits

- n = 3 R3 patches that close environment failures (two different byte sequences in EC-SYMBOL and one in EH-RENDERER), one seed, synthetic fixtures from one family, all visible to the author. This is a demonstration of the mechanism and a descriptive count, not a rate estimate.
- "Equivalent" covers only the six operations. Unexecuted paths (for example the empty-`DATA` branch) remain invisible; the static diff is reported separately.
- The VM used is an overlay of the Debian disk installed fresh on 2026-10-13 and already used for the rc2 clean check. It is **not a new installation**.
