# Fixture contract and external validation

This release contains ten synthetic, author-visible fixtures in one small Typer CLI family: eight damaged cases and two healthy controls. `validate_fixture.py` validates this catalogue through its real `stateless-cli-v1` contract. It is an external utility with its own plans and evidence; it does not alter the frozen R3 core, oracle, policy, prompts, fixtures, model results or the sixteen default episodes of `reproduce.py`.

## Inputs and metadata

`source/cases.json` maps case IDs to metadata and must equal the cases array in `cases-package/contract.json`. Each case declares its category, healthy flag, mechanism and symptom surface, `fixture_contract`, initial/reference/alternative profiles, initial/reference/alternative source SHA256, exact command JSON values, and six Boolean `initial_checks_expected`. Healthy cases additionally record the observed initial `no_args` return code. `initial.py`, `reference.py`, `alternative.py` and `negative.py` are input bytes; the validator never imports them in the evaluator.

`fixture_validation.json` is a new sidecar for the current twenty alternative/negative endpoints. Each row explicitly supplies the source path and SHA256, profile, expected six-check vector and expected status. It records the SHA256 and JSON selectors of retained historical `control.json` metadata. Those raw records remain outside the public package because they include host paths. The sidecar is newly derived documentation, not a historical freeze. Historical source writes converted CRLF to LF; the sidecar states that correspondence and retains both hashes. The new validator prepares the exact distribution bytes, without normalizing or rewriting them.

The current alternatives all have six expected successful checks. The current negatives fail `first_command` and pass the other five checks. These are explicit recorded expectations for these fixtures, not rules inferred from filenames. Negatives use their historical `reference_profile`; alternatives use `alternative_profile`. In particular, `EH-RENDERER/alternative` retains the profile without Rich. It must not be silently changed to a full dependency profile to obtain PASS.

The catalogue uses these profile names:

| Abbreviation below | Profile | Typer / Click |
|---|---|---|
| A | `typer0153_click820` | 0.15.3 / 8.2.0 |
| B | `typer0153_click818` | 0.15.3 / 8.1.8 |
| C | `typer0160_click820` | 0.16.0 / 8.2.0 |
| MT | `missing_typer_click820` | absent / 8.2.0 |
| MR | `missing_rich_typer0160_click820` | 0.16.0 / 8.2.0, Rich absent |

Only A, B and C are agent-selectable profiles. MT and MR are fixture environments. Preparing a declared alternative endpoint in MR is not an added agent action.

## Six operations and expected initial behavior

Every evaluation captures exactly these six operations in this order, using `cases-package/frozen_runtime/policy.json`:

| Operation | Application arguments | Contract |
|---|---|---|
| `first_command` | `first-command` | Exact per-case JSON object |
| `second_command` | `second-command` | Exact per-case JSON object |
| `no_args` | none | Implicit group help |
| `explicit_help` | `--help` | Explicit group help |
| `first_command_help` | `first-command --help` | First command help |
| `second_command_help` | `second-command --help` | Second command help |

Commands require rc 0, empty stderr and exactly one JSON object on stdout with the declared keys and values. The oracle rejects duplicate keys, extra content, nonfinite numbers, booleans in place of numbers, and numeric strings. Equivalent finite integer/float values and JSON whitespace/key-order variations are accepted. Most cases emit balance/entries and credits/debits; SC-SORT emits ordered/maximum.

Explicit help requires rc 0, stdout help and empty stderr. Implicit help accepts rc 0 with stdout help and empty stderr, or rc 2 with help on stdout and/or stderr. Group help must contain the case-sensitive tokens `Usage`, `first-command` and `second-command`; command help must contain `Usage` and its own command name. Valid UTF-8 and complete captures are required. The frozen public contract allows legitimate mentions of `Traceback` or `TypeError`. The oracle does not implement a general traceback blacklist; the older policy sentence ending “no traceback” is a documented wording discrepancy, not a newly added scoring rule. No claim that historical outcomes were independent of traceback follows from this validator.

In the next table, a vector lists successful (`1`) and failing (`0`) initial checks in the operation order above. Initial validation means exact equality with this vector, not a requirement that all checks fail.

| Fixture | Initial vector | Initial profile | Reference profile | Alternative profile | Negative profile |
|---|---|---|---|---|---|
| EH-API | 110000 | A | C | B | C |
| EH-RENDERER | 110000 | MR | C | MR | C |
| EC-MISSING | 000000 | MT | C | B | C |
| EC-SYMBOL | 001111 | B | C | B | C |
| SC-BALANCE | 011111 | C | C | C | C |
| SC-SORT | 011111 | C | C | C | C |
| SH-FLAG | 111000 | C | C | C | C |
| SH-FORMAT | 110011 | C | C | C | C |
| H-RC0 | 111111 | B | B | C | B |
| H-RC2 | 111111 | C | C | B | C |

Damaged reference endpoints must PASS; damaged noops must FAIL with their initial vector unchanged. Healthy initial and noop endpoints must PASS, preserving their declared initial `no_args` rc (0 for H-RC0 and 2 for H-RC2). A noop is one valid `finish` through the existing finite dispatcher, without source/profile operations. These endpoint checks do not reproduce the FC always-finish trajectory or derive a BASE arm; `reproduce.py` retains that separate purpose.

## Plan before execution

With no flags the utility only checks schema, source hashes and matrix construction. It runs no candidate processes and is usable offline on Windows or Linux. The ten directed unit tests are also offline:

```text
python -I -S validate_fixture.py
python -I -S tests/test_validate_fixture.py
```

The complete matrix (`--selection all`) contains 48 distinct scenarios: ten initial, ten noop, eight damaged reference, ten alternative and ten negative. It does not add redundant healthy reference checks. `--selection new-coverage` selects 24: initial and noop for both healthy fixtures, plus alternative and negative for all ten fixtures. The latter selection requires separate identity-linked evidence for the omitted damaged initial/reference/noop checks; it does not declare them newly executed. `--selection selected --scenarios CASE/variant ...` permits an explicit smaller subset and rejects duplicate or unknown scenario IDs.

For the release verification, the existing sixteen `reproduce.py` episodes cover the eight damaged initial/reference/noop requirements. The 24 new scenarios cover the added utility and the omitted variants/healthy endpoints. Historical runner results may be reused only with an explicit component-equivalence record. New fixture controls are not new R3 model results.

Create a plan outside the package before invoking the application sandbox:

```sh
/usr/bin/python3 -I -S validate_fixture.py --write-plan ../fixture-plan.json --selection new-coverage
/usr/bin/python3 -I -S validate_fixture.py --execute-plan ../fixture-plan.json --wheelhouse ../wheelhouse --output ../fixture-validation
```

The plan stores exact scenario IDs, profiles, source paths, expectations, limits and hashes of the validator, sidecar, runtime/core and fixture inputs. Execution rejects stale or changed plans. It also verifies the current package manifest before and after execution; the release sidecar separately binds the tested ZIP. Prose-only changes do not change a scenario's executable/input equivalence, but the ZIP and package manifest retain their own identities.

| Limit | Complete matrix | New coverage selection |
|---|---:|---:|
| Fresh states | 48 | 24 |
| Application captures | 288 | 144 |
| Native isolation probe captures | 96 | 48 |
| Trusted worker captures | 96 | 48 |
| Offline installations | 48 | 24 |
| Checkpoint copies | 0 | 0 |
| Machine seconds, maximum | 7,200 | 7,200 |
| Model calls / generated tokens / model processes / automatic retries | 0 | 0 |

Each successful scenario uses six application captures, two native probes, one writable-property worker and one dispatcher workspace-snapshot worker. Counters are charged before attempted captures/installations; raw rows record whether they returned. A failure can therefore consume a counter without producing a successful process result. The 24-scenario selection combined with the unchanged sixteen `reproduce.py` defaults is bounded by 432 applications, 80 probes, 304 workers, 44 offline installations, 40 fresh states, eight checkpoint copies and 14,400 machine seconds. These are ceilings, not claims of observed costs.

## Isolation, scoring and evidence

Execution requires supported Debian, trusted `/usr/bin/python3 -I -S`, optimization disabled and matching nonzero real/effective UIDs. An ordinary UID other than 1000 is permitted. Bubblewrap must pass the existing read-only and writable-worker property checks. Failure stops the run; there is no fallback or automatic retry. Wheel acquisition is a separate prerequisite; this utility downloads nothing and checks all ten wheel hashes before preparing the runtime.

Every scenario receives a fresh managed state with exact source bytes and its declared profile. Applications run only through the existing `judge.sandbox_command` and `judge.capture`: separate namespaces, no network, dropped capabilities, read-only source/environment mounts and fresh auxiliary directories per invocation. The frozen limits remain ten seconds per capture, 2 MiB per captured stream, 768 MiB address space and 64 processes. The validator uses the existing `grade_case` and `oracle.classify`, verifies the state before/after scoring and performs no cleanup. It does not import candidate source or candidate dependencies into the evaluator, and it does not expose the oracle, references, host home or evidence inside the application sandbox.

Evidence is written outside the package: the saved plan and environment identity, `costs.json`, capture ledger and raw capture records, per-scenario isolation/property records, `score.json`, `scenario.json`, result rows and closure. A failure retains partial scoring, state and `failure.json` and stops later scenarios. Score files are committed before expectations are checked, so unexpected outcomes are retained. A PASS validation row means that the observed endpoint equals the declared expectation; a negative's valid oracle status is still FAIL.

`PACKAGE_MANIFEST.json` and its SHA256 sidecar identify this distribution. `PROVENANCE.json` identifies preserved experimental components, including the documented task-comment adaptation; neither is interchangeable with an R3 experimental freeze. The nested historical `cases-package/manifest.json` retains its historical scope, including externally fetched wheels. Release inventory must use the new package manifest.

## Extension boundary

The current utility intentionally supports this finite `stateless-cli-v1` shape. The six operation names/arguments, help tokens, CLI invocation and mount contract, file bounds and allowed profiles are coupled across policy, oracle, interface metadata and dispatcher. `public_contract.py` additionally special-cases SC-SORT's command meaning, and `reproduce.py` has an explicit list of eight damaged fixtures. The prompt files and runner selections are catalogue-specific. A different application family is not automatically supported by adding a directory.

For another fixture in this family, prepare a new version/copy: add its four source variants and task/prompt, document its mechanism and provenance, supply complete metadata and explicit expected vectors/profiles, add it consistently to both catalogues and the validation sidecar, and update versioned selection logic, inventories and provenance. Verify exact source/wheel identities; create a new bounded validation plan and retain expected or unexpected outcomes. Reuse of earlier checks requires matching relevant components and inputs. If operations, help syntax, dependency combinations, invocation state or source permissions change, version and review the affected policy/oracle/interface/sandbox contract first. Preserve the existing R3 bytes and results.

## Historical metric and entry-point semantics

`blind_modifying_requests` counts `write_file` or `apply_profile` requests that pass action and argument validation when no entry in the current-epoch observation map has `completed == true`. It includes valid noops and is evaluated before the request's effective change is reconciled. A changed state starts a new epoch and clears current observations. This is not “before the first observation in the whole episode,” and it does not identify intent or cognition. Historical code and values remain unchanged.

`source/exploration_episode.py` has a historical `main` adapter requiring UID 1000. It is retained for provenance. Users should use the portable public entry points `run_agent.py` and `reproduce.py`, which require an unprivileged matching real/effective UID without prescribing 1000. This validator follows the same portable UID rule. Choosing a different UID does not relax namespaces, limits, interpreter flags or either native isolation gate.
