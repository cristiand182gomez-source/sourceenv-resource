# SourceEnv supplement

## S1 Scope and provenance

This review compiles retained R3 and development evidence, with new offline analyses of retained bytes. R3 remains unchanged. Model-free validation of the new distribution is a separate activity reported in S8; it is not additional R3 agent evidence. Source relationships and SHA256 are in [PROVENANCE.json](PROVENANCE.json); numeric original-episode selectors are in [context ledger](evidence/context_cost_ledger.json). Complete private conversations, unquoted responses, tool arguments and reasoning text are excluded. Only the five extracts already cited in the retained report appear in [EXTRACTOS.md](EXTRACTOS.md).

[count_words.py](count_words.py) counts the entire main file: title, all sections, tables, captions, notes, references and visible figure labels. It adds every SVG text label for each embedded image to the conservative per-section maximum of raw and visible Markdown counts. [FIGURE_MANIFEST.json](figures/FIGURE_MANIFEST.json) binds the PNG to its SVG text source by SHA256. Unmapped images and mismatched assets are rejected. [WORD_COUNT.json](WORD_COUNT.json) retains the exact figure strings, counts, file identities and method. The vector and raster versions use identical deterministic drawing primitives; no image generation is used.

## S2 Resource, complete metrics and denominators

The [catalog](evidence/cases.json) retains ten synthetic author-visible fixtures, mechanisms, initial/reference/alternative source hashes, initial checks and the particular JSON contracts. Standard command outputs are balance 17 / entries 3 and credits 23 / debits 6; SC-SORT expects ordered=[2,9,12] and maximum 12. SH-FLAG registers only -h; SH-FORMAT emits group usage without commands; EC-SYMBOL imports click.exceptions.NoArgsIsHelpError on its command path; EH-RENDERER imports rich.console.Console only at help entry. Surfaces are intervention descriptions, not isolated causal factors. EC-MISSING also breaks help.

Repair and preservation use available damaged/healthy endpoints (8/2 planned per configuration/arm). Losses use initially passing checks; initially failing first_command is not an additional loss in SC-BALANCE. Requests count parsed source/environment requests, including rejected arguments; effective changes compare state identities, accepted noops leave them equal, and rejected/unknown effects are separate. A profile name alone does not define environment identity. HOME/tmp/cache are recreated and do not persist between invocations.

Coverage counts distinct completed captures in the current epoch, out of six; timeout or capture error does not cover an operation. Effective changes reset both coverage and current observations, while noops do not. Correct re-observation replaces a failure. The public-failure predicate uses delivered bytes and current observations; truncated/insufficient captures can be UNKNOWN. It is not the private oracle's unseen truth and does not establish comprehension. Policy rejection is a valid finish, not dispatcher invalidity. Accepted closure is not PASS.

Arm availability is independent; ordinary action, application, installation, generation-token and context-budget stops retain scored endpoints. Watchdogs censor rather than fabricate FAIL. Infrastructure-invalid, partial and unattempted cases are retained without imputation. Pair comparisons use complete pairs; threshold 6/8 damaged is a predeclared completeness convention, not significance or power. No R3 arm was censored/unavailable. [Full predictions](evidence/r3_predictions.json), [pairs](evidence/r3_summary.json) and [gate exposure](evidence/r3_gate_exposure.json) remain separately inspectable.

The unchanged loop metrics include redundant operation/epoch observations with identical public feedback, longest streak of identical valid actions, distinct completed operations, and final stagnation suffix without a new operation/epoch. Finish terminal acceptance is excluded from that suffix. An incomplete trace makes the metric unavailable rather than zero. `blind_modifying_requests` counts `write_file`/`apply_profile` requests that pass action and argument validation and are issued with no completed capture in the current epoch. It includes noops and is evaluated before the request's effect; effective state changes reset observations, so it can occur after earlier observations in the episode. This is not a count restricted to before the episode's first observation. Historical values and code are unchanged. Blind and diagnostic editing counts do not infer intention, understanding or repair. Full per-arm rows also preserve losses, public failures, health, terminal availability and logical prefix costs.

### Frozen prompt, contract erratum and historical entry point

The frozen [public_contract.py](../SourceEnv/source/public_contract.py) constructs a task beginning “Repair app.py” and later explicitly permits editing source or choosing an allowed profile, with no particular repair required. The framing may influence axis choice and healthy-source edits; no causal test of that influence was performed. Scripted environment references show that profile repairs are available under this resource. R3's source-only interventions do not establish inability to use the environment axis.

The same public contract permits literal mentions of `Traceback` or `TypeError` in otherwise valid help. All exit-code, channel, required-token and capture conditions still apply. Separately, [policy.json](../SourceEnv/cases-package/frozen_runtime/policy.json) says implicit help has “no traceback”, but [oracle.py](../SourceEnv/cases-package/oracle.py) implements no traceback-specific rejection predicate. This is a documentation/oracle mismatch, not permission to reinterpret R3 scores. All three files retain their frozen bytes.

Suggested wording for a **future version**, not the R3 prompt: “Literal mentions of Traceback or TypeError do not waive any exit-code, output-channel, required-token, JSON or capture-completion requirement. Help emitted as an unhandled-exception traceback is not valid help.” Adopting the latter requirement would require a specified detection rule, matching oracle implementation and versioned validation; it is not retroactively imposed here.

The [no-arguments capture audit](evidence/no_args_capture_audit.json) inspects the original `no_args` capture for each of 40 endpoints, with selectors, exit codes, stdout/stderr identities, decoded bytes and completeness evidence. All 40 captures are complete; 24 passed that operation and contain neither `Traceback` nor `TypeError`. Nine actual exception tracebacks occur in stderr of captures that fail `no_args`, all with rc 1. The remaining failures have other causes. This audit finds no exception traceback in an approved `no_args` endpoint. It does not establish that alternative contract wording would leave agent trajectories unchanged, and the aggregates alone do not establish this finding.

The `main` in [exploration_episode.py](../SourceEnv/source/exploration_episode.py) is a preserved historical adapter with a UID 1000 guard. Portable entry points are [run_agent.py](../SourceEnv/run_agent.py) and [reproduce.py](../SourceEnv/reproduce.py); users should not bypass the historical guard. Their unprivileged/isolation checks remain mandatory.

P1's zero-effective-profile prediction follows the earlier development pattern recorded in [development_profile_counts.json](evidence/development_profile_counts.json): r2 made zero requests and r2A made one, with zero effective profile changes in both. P2's threshold of one bifurcation among ten is weak evidence of exposure, not a demanding repair prediction. The original P1–P3 predictions and statuses are retained without conversion into confirmations. Each configuration contributes eight complete damaged pairs, sixteen total.

## S3 Aggregate interventions and public-failure finishes

All totals below use ALL TEN fixtures, including H-RC0 and H-RC2. Requests/effective/noops are counts, not independent trajectories or probabilities. FC is the physical run; BASE metrics use only its retained prefix. Parsed invalid/noop profiles consume installation slots; the fourth request ends install_budget without installing. C3's two physical profile requests were SH-FLAG and SC-SORT, both noops before their checkpoints; C1 had none. No environment fixture requested a profile.

| Configuration/arm | Source R/E/N | Profile R/E/N | Visible/all valid finishes | Visible/accepted | Visible/rejected |
| --- | --- | --- | --- | --- | --- |
| C3 FC | 15/10/5 | 2/0/2 | 7/24 | 5/10 | 2/14 |
| C3 BASE | 14/9/5 | 2/0/2 | 1/10 | 1/10 | not applicable (0 rejections) |
| C1 FC | 15/9/6 | 0/0/0 | 11/51 | 4/7 | 7/44 |
| C1 BASE | 11/7/4 | 0/0/0 | 0/10 | 0/10 | not applicable (0 rejections) |

[closure_patterns.json](evidence/closure_patterns.json) records the source SHA256, all 40 original row indices, exact predicates and fixture lists. BASE has zero current coverage in C3 6/10 and C1 4/10 endpoints; requiring a prior effective change within that BASE prefix gives 4/10 for each configuration. Zero coverage means no completed captures of the current state, not zero execution requests. Accepted FC closures with a public failure are C3 5/10 and C1 4/7. These denominators are accepted closures, not all valid requests. The visible/all-valid numerator is visible-accepted + visible-rejected. BASE accepted every one of its ten first valid finishes under its own policy; it never saw FC rejection. Repeated requests within an episode and shared prefixes make these dependent counts. Totals are calculated from [aggregate_metrics.json](evidence/aggregate_metrics.json), with source indices for [r3_by_arm.json](evidence/r3_by_arm.json).

## S4 Every fixture and arm; gate, losses and costs

The tables contain forty available endpoints in original `r3_by_arm.json` order. Each linked row number is the JSON array index. SRC and ENV are requests/effective/noops; Public A/R gives public failures on accepted/rejected finish requests.

| Row | Configuration / fixture / arm | Endpoint | Terminal | Coverage | SRC | ENV | Losses | Public A/R |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [0](evidence/r3_by_arm.json) | C3 / EH-API / FC | FAIL | finish | 6/6 | 0/0/0 | 0/0/0 | 0 | 1/1 |
| [1](evidence/r3_by_arm.json) | C3 / EH-API / BASE | FAIL | finish | 3/6 | 0/0/0 | 0/0/0 | 0 | 1/0 |
| [2](evidence/r3_by_arm.json) | C3 / SC-BALANCE / FC | FAIL | finish | 6/6 | 0/0/0 | 0/0/0 | 0 | 1/0 |
| [3](evidence/r3_by_arm.json) | C3 / SC-BALANCE / BASE | FAIL | finish | 0/6 | 0/0/0 | 0/0/0 | 0 | 0/0 |
| [4](evidence/r3_by_arm.json) | C3 / H-RC0 / FC | PASS | finish | 6/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [5](evidence/r3_by_arm.json) | C3 / H-RC0 / BASE | PASS | finish | 0/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [6](evidence/r3_by_arm.json) | C3 / EC-MISSING / FC | FAIL | finish | 6/6 | 2/1/1 | 0/0/0 | 0 | 1/0 |
| [7](evidence/r3_by_arm.json) | C3 / EC-MISSING / BASE | FAIL | finish | 0/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [8](evidence/r3_by_arm.json) | C3 / SH-FLAG / FC | FAIL | finish | 6/6 | 1/1/0 | 1/0/1 | 0 | 1/1 |
| [9](evidence/r3_by_arm.json) | C3 / SH-FLAG / BASE | FAIL | finish | 0/6 | 1/1/0 | 1/0/1 | 0 | 0/0 |
| [10](evidence/r3_by_arm.json) | C3 / EH-RENDERER / FC | PASS | finish | 6/6 | 1/1/0 | 0/0/0 | 0 | 0/0 |
| [11](evidence/r3_by_arm.json) | C3 / EH-RENDERER / BASE | FAIL | finish | 0/6 | 0/0/0 | 0/0/0 | 0 | 0/0 |
| [12](evidence/r3_by_arm.json) | C3 / SC-SORT / FC | PASS | finish | 6/6 | 1/1/0 | 1/0/1 | 0 | 0/0 |
| [13](evidence/r3_by_arm.json) | C3 / SC-SORT / BASE | PASS | finish | 2/6 | 1/1/0 | 1/0/1 | 0 | 0/0 |
| [14](evidence/r3_by_arm.json) | C3 / H-RC2 / FC | PASS | finish | 6/6 | 1/1/0 | 0/0/0 | 0 | 0/0 |
| [15](evidence/r3_by_arm.json) | C3 / H-RC2 / BASE | PASS | finish | 0/6 | 1/1/0 | 0/0/0 | 0 | 0/0 |
| [16](evidence/r3_by_arm.json) | C3 / EC-SYMBOL / FC | PASS | finish | 6/6 | 5/3/2 | 0/0/0 | 0 | 0/0 |
| [17](evidence/r3_by_arm.json) | C3 / EC-SYMBOL / BASE | PASS | finish | 2/6 | 5/3/2 | 0/0/0 | 0 | 0/0 |
| [18](evidence/r3_by_arm.json) | C3 / SH-FORMAT / FC | FAIL | finish | 6/6 | 2/1/1 | 0/0/0 | 0 | 1/0 |
| [19](evidence/r3_by_arm.json) | C3 / SH-FORMAT / BASE | FAIL | finish | 3/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [20](evidence/r3_by_arm.json) | C1 / EH-API / FC | FAIL | finish | 6/6 | 0/0/0 | 0/0/0 | 0 | 1/2 |
| [21](evidence/r3_by_arm.json) | C1 / EH-API / BASE | FAIL | finish | 2/6 | 0/0/0 | 0/0/0 | 0 | 0/0 |
| [22](evidence/r3_by_arm.json) | C1 / SC-BALANCE / FC | FAIL | action_budget | 5/6 | 3/2/1 | 0/0/0 | 0 | 0/4 |
| [23](evidence/r3_by_arm.json) | C1 / SC-BALANCE / BASE | FAIL | finish | 0/6 | 1/1/0 | 0/0/0 | 5 | 0/0 |
| [24](evidence/r3_by_arm.json) | C1 / H-RC0 / FC | PASS | finish | 6/6 | 0/0/0 | 0/0/0 | 0 | 0/0 |
| [25](evidence/r3_by_arm.json) | C1 / H-RC0 / BASE | PASS | finish | 2/6 | 0/0/0 | 0/0/0 | 0 | 0/0 |
| [26](evidence/r3_by_arm.json) | C1 / EC-MISSING / FC | FAIL | finish | 6/6 | 1/1/0 | 0/0/0 | 0 | 1/1 |
| [27](evidence/r3_by_arm.json) | C1 / EC-MISSING / BASE | FAIL | finish | 0/6 | 1/1/0 | 0/0/0 | 0 | 0/0 |
| [28](evidence/r3_by_arm.json) | C1 / SH-FLAG / FC | FAIL | finish | 6/6 | 2/1/1 | 0/0/0 | 0 | 1/0 |
| [29](evidence/r3_by_arm.json) | C1 / SH-FLAG / BASE | FAIL | finish | 2/6 | 0/0/0 | 0/0/0 | 0 | 0/0 |
| [30](evidence/r3_by_arm.json) | C1 / EH-RENDERER / FC | FAIL | run_app_budget | 5/6 | 1/1/0 | 0/0/0 | 0 | 0/0 |
| [31](evidence/r3_by_arm.json) | C1 / EH-RENDERER / BASE | FAIL | finish | 0/6 | 1/1/0 | 0/0/0 | 0 | 0/0 |
| [32](evidence/r3_by_arm.json) | C1 / SC-SORT / FC | PASS | action_budget | 2/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [33](evidence/r3_by_arm.json) | C1 / SC-SORT / BASE | PASS | finish | 2/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [34](evidence/r3_by_arm.json) | C1 / H-RC2 / FC | PASS | finish | 6/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [35](evidence/r3_by_arm.json) | C1 / H-RC2 / BASE | PASS | finish | 2/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [36](evidence/r3_by_arm.json) | C1 / EC-SYMBOL / FC | PASS | finish | 6/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [37](evidence/r3_by_arm.json) | C1 / EC-SYMBOL / BASE | PASS | finish | 2/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |
| [38](evidence/r3_by_arm.json) | C1 / SH-FORMAT / FC | FAIL | finish | 6/6 | 2/1/1 | 0/0/0 | 0 | 1/0 |
| [39](evidence/r3_by_arm.json) | C1 / SH-FORMAT / BASE | FAIL | finish | 0/6 | 2/1/1 | 0/0/0 | 0 | 0/0 |

Invalid n/N uses invalid actions / dispatched actions and its own `invalid_rate`; No-tools n/N uses responses without tool calls / retained replies and its own `rate`. Percentages display those respective rates rounded to two decimal places. A valid coverage rejection is not an invalid action. Post counts actions following FC's first rejection; BASE has no continuation. Full denominators and action types remain in the linked JSON.

| Row | Configuration / fixture / arm | Invalid n/N | Invalid % | No-tools n/N | No-tools % | Post | Redundant n/d | Streak | Stagnation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [0](evidence/r3_by_arm.json) | C3 / EH-API / FC | 0/10 | 0.00 | 2/10 | 20.00 | 4 | 1/8 | 2 | 0 |
| [1](evidence/r3_by_arm.json) | C3 / EH-API / BASE | 0/6 | 0.00 | 1/6 | 16.67 | 0 | 1/5 | 2 | 1 |
| [2](evidence/r3_by_arm.json) | C3 / SC-BALANCE / FC | 0/9 | 0.00 | 2/9 | 22.22 | 8 | 0/6 | 1 | 0 |
| [3](evidence/r3_by_arm.json) | C3 / SC-BALANCE / BASE | 0/1 | 0.00 | 1/1 | 100.00 | 0 | 0/0 | 1 | 0 |
| [4](evidence/r3_by_arm.json) | C3 / H-RC0 / FC | 0/10 | 0.00 | 1/10 | 10.00 | 7 | 0/6 | 2 | 0 |
| [5](evidence/r3_by_arm.json) | C3 / H-RC0 / BASE | 0/3 | 0.00 | 1/3 | 33.33 | 0 | 0/0 | 2 | 2 |
| [6](evidence/r3_by_arm.json) | C3 / EC-MISSING / FC | 1/13 | 7.69 | 1/13 | 7.69 | 9 | 2/8 | 2 | 0 |
| [7](evidence/r3_by_arm.json) | C3 / EC-MISSING / BASE | 1/4 | 25.00 | 1/4 | 25.00 | 0 | 0/0 | 2 | 3 |
| [8](evidence/r3_by_arm.json) | C3 / SH-FLAG / FC | 0/12 | 0.00 | 2/12 | 16.67 | 8 | 0/6 | 1 | 0 |
| [9](evidence/r3_by_arm.json) | C3 / SH-FLAG / BASE | 0/4 | 0.00 | 1/4 | 25.00 | 0 | 0/0 | 1 | 3 |
| [10](evidence/r3_by_arm.json) | C3 / EH-RENDERER / FC | 2/17 | 11.76 | 5/17 | 29.41 | 14 | 1/11 | 2 | 0 |
| [11](evidence/r3_by_arm.json) | C3 / EH-RENDERER / BASE | 2/3 | 66.67 | 3/3 | 100.00 | 0 | 0/0 | 1 | 2 |
| [12](evidence/r3_by_arm.json) | C3 / SC-SORT / FC | 0/10 | 0.00 | 0/10 | 0.00 | 5 | 0/6 | 1 | 0 |
| [13](evidence/r3_by_arm.json) | C3 / SC-SORT / BASE | 0/5 | 0.00 | 0/5 | 0.00 | 0 | 0/2 | 1 | 0 |
| [14](evidence/r3_by_arm.json) | C3 / H-RC2 / FC | 0/10 | 0.00 | 1/10 | 10.00 | 7 | 0/6 | 1 | 0 |
| [15](evidence/r3_by_arm.json) | C3 / H-RC2 / BASE | 0/3 | 0.00 | 1/3 | 33.33 | 0 | 0/0 | 1 | 2 |
| [16](evidence/r3_by_arm.json) | C3 / EC-SYMBOL / FC | 0/17 | 0.00 | 1/17 | 5.88 | 5 | 2/10 | 2 | 0 |
| [17](evidence/r3_by_arm.json) | C3 / EC-SYMBOL / BASE | 0/12 | 0.00 | 1/12 | 8.33 | 0 | 2/6 | 2 | 0 |
| [18](evidence/r3_by_arm.json) | C3 / SH-FORMAT / FC | 0/11 | 0.00 | 1/11 | 9.09 | 5 | 0/6 | 2 | 0 |
| [19](evidence/r3_by_arm.json) | C3 / SH-FORMAT / BASE | 0/6 | 0.00 | 0/6 | 0.00 | 0 | 0/3 | 2 | 0 |
| [20](evidence/r3_by_arm.json) | C1 / EH-API / FC | 0/11 | 0.00 | 2/11 | 18.18 | 8 | 0/6 | 1 | 0 |
| [21](evidence/r3_by_arm.json) | C1 / EH-API / BASE | 0/3 | 0.00 | 0/3 | 0.00 | 0 | 0/2 | 1 | 0 |
| [22](evidence/r3_by_arm.json) | C1 / SC-BALANCE / FC | 0/20 | 0.00 | 2/20 | 10.00 | 15 | 2/10 | 2 | 2 |
| [23](evidence/r3_by_arm.json) | C1 / SC-BALANCE / BASE | 0/5 | 0.00 | 0/5 | 0.00 | 0 | 0/2 | 1 | 1 |
| [24](evidence/r3_by_arm.json) | C1 / H-RC0 / FC | 0/8 | 0.00 | 1/8 | 12.50 | 5 | 0/6 | 1 | 0 |
| [25](evidence/r3_by_arm.json) | C1 / H-RC0 / BASE | 0/3 | 0.00 | 1/3 | 33.33 | 0 | 0/2 | 1 | 0 |
| [26](evidence/r3_by_arm.json) | C1 / EC-MISSING / FC | 1/15 | 6.67 | 4/15 | 26.67 | 9 | 0/8 | 1 | 1 |
| [27](evidence/r3_by_arm.json) | C1 / EC-MISSING / BASE | 0/6 | 0.00 | 1/6 | 16.67 | 0 | 0/2 | 1 | 2 |
| [28](evidence/r3_by_arm.json) | C1 / SH-FLAG / FC | 0/20 | 0.00 | 0/20 | 0.00 | 16 | 2/10 | 2 | 0 |
| [29](evidence/r3_by_arm.json) | C1 / SH-FLAG / BASE | 0/4 | 0.00 | 0/4 | 0.00 | 0 | 0/2 | 1 | 0 |
| [30](evidence/r3_by_arm.json) | C1 / EH-RENDERER / FC | 0/20 | 0.00 | 3/20 | 15.00 | 16 | 5/12 | 2 | 2 |
| [31](evidence/r3_by_arm.json) | C1 / EH-RENDERER / BASE | 0/4 | 0.00 | 0/4 | 0.00 | 0 | 0/2 | 1 | 1 |
| [32](evidence/r3_by_arm.json) | C1 / SC-SORT / FC | 0/20 | 0.00 | 8/20 | 40.00 | 12 | 0/4 | 2 | 13 |
| [33](evidence/r3_by_arm.json) | C1 / SC-SORT / BASE | 0/8 | 0.00 | 0/8 | 0.00 | 0 | 0/4 | 2 | 0 |
| [34](evidence/r3_by_arm.json) | C1 / H-RC2 / FC | 0/14 | 0.00 | 2/14 | 14.29 | 6 | 1/9 | 2 | 0 |
| [35](evidence/r3_by_arm.json) | C1 / H-RC2 / BASE | 0/8 | 0.00 | 1/8 | 12.50 | 0 | 0/4 | 2 | 0 |
| [36](evidence/r3_by_arm.json) | C1 / EC-SYMBOL / FC | 0/15 | 0.00 | 2/15 | 13.33 | 8 | 1/8 | 2 | 0 |
| [37](evidence/r3_by_arm.json) | C1 / EC-SYMBOL / BASE | 0/7 | 0.00 | 0/7 | 0.00 | 0 | 0/3 | 2 | 0 |
| [38](evidence/r3_by_arm.json) | C1 / SH-FORMAT / FC | 0/16 | 0.00 | 1/16 | 6.25 | 10 | 2/10 | 2 | 0 |
| [39](evidence/r3_by_arm.json) | C1 / SH-FORMAT / BASE | 0/6 | 0.00 | 0/6 | 0.00 | 0 | 0/2 | 2 | 2 |

There are ten complete/bifurcated pairs per configuration, eight damaged. Only C3/EH-RENDERER is discordant. P1/P2 are COMPATIBLE for each; P3 is REFUTED for C3 and COMPATIBLE for C1. Compatibility does not prove equivalence. C3 has 10 finish terminals; C1 has 7 finish, 2 action_budget, 1 run_app_budget. Coverage medians over all ten are C3 BASE 0/6 → FC 6/6 and C1 BASE 2/6 → FC 6/6. Full coverage applies to accepted FC finishes, not every scored terminal. FC added 72 actions after first rejection in C3 and 105 in C1, combining feedback and opportunity to continue with rejection.

Three of four physical healthy trajectories changed source: C3/H-RC0, C3/H-RC2, C1/H-RC2. All healthy endpoints remained PASS; these are four physical runs, not eight independent arm episodes. In C1/SC-BALANCE, BASE loses second_command and all four help checks; FC restores those five. first_command fails initially and at both endpoints, so both remain FAIL. Source edits and noops are not classified as damage by themselves.

### Physical costs and context

| Configuration | Calls | Generated tokens | Reasoning subset | Applications | Machine seconds | Probes | Workers | Offline installs | Model processes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C3 | 119 | 26277 | 1026 | 253 | 4975.567501 | 20 | 187 | 12 | 1 |
| C1 | 159 | 24752 | 0 | 263 | 2724.436158 | 20 | 209 | 10 | 1 |

These are retained R3 costs only: total 278 calls, 51,029 generated tokens, 516 applications, 2.1389 hours. Reasoning 1,026 is included, not added. There were zero model preflights, retries or independent BASE calls. Per-configuration ceilings were 200 calls, 81,920 generated tokens, 300 applications, 20 probes, 520 workers, 40 offline installs, one model process and 43,200 s global protection; episode watchdog 14,400 s. [Frozen proposal copy](evidence/r3_proposal.json) preserves all settings: its `PENDING_REVIEW` and false authorization flags are historical preparation metadata. The [proposal sidecar](evidence/r3_proposal_README.md) explains the later external authorization and consumed run without editing that JSON. These flags are not current permission to run. Shared BASE prefixes have zero additional generation cost; costs after the checkpoint belong to FC.

The [numeric turn ledger](evidence/context_cost_ledger.json) includes actual input, generated/reasoning tokens and remaining reply reservation, with original source SHA256 and selectors. It excludes all messages. Per-turn input+reservation is checked against 32,768. Missing usage in future/partial runs requires lower/upper cost bounds, not invented zero; unknown server closure is infrastructure, not proof of cancellation. The externally owned public runner limitation is retained in [RUNNING](../SourceEnv/RUNNING.md).

## S5 Interface health and literal excerpts

| Configuration | Responses | No tools | Valid text finishes | SUMMARY_LIMIT | Text finishes rejected/accepted | All valid finishes rejected/accepted |
| --- | --- | --- | --- | --- | --- | --- |
| C3 | 119 | 16 | 13 | 3 | 11/2 | 14/10 |
| C1 | 159 | 25 | 24 | 1 | 20/4 | 44/7 |

C3 no-tools 16 = 13 valid + 3 SUMMARY_LIMIT, and 13 = 11 rejected + 2 accepted. C1 no-tools 25 = 24 valid + 1 SUMMARY_LIMIT, and 24 = 20 rejected + 4 accepted. Invalids are subsets, not disjoint categories. PENDING_OPERATIONS is a valid policy rejection; ordinary budgets are a separate terminal category. r2A had 97/192 no-tools and 93 non-empty; these are syntactic counts, not semantic counts of intended closures. The unsupported 86 classification is explicitly DISCARDED_NOT_FOR_PAPER. [Response annotations](evidence/response_counts.json) retain 470 records from 30 original episode files, per-response hashes/selectors and per-fixture totals, without content. [Original recount note](evidence/health_recount_note.md) and [development health](evidence/health_development.json) preserve the separate stages. Changes across runs do not isolate interface causality.

The five retained [extracts E1–E5](EXTRACTOS.md) contain at most 15 literal lines each and are the only conversation text included. E1: accepted failing EH-API closure claiming TypeErrors allowed. E2: EH-RENDERER source rewrite after rejection. E3: SH-FLAG public profile response includes ok:true and changed:false. E4: repaired SC-SORT with action_budget and 2/6 coverage. E5: development F01 calls environment repair outside scope; it is not an R3 observation.

public_feedback.py removes ok for run_app/capture feedback; other results retain operational status. The existing file SHA256 and selected lines are recorded in documentary verification. Tool execution, effective environment/source change and oracle contract satisfaction are different claims. No interface code was changed here.

## S6 Pinned external audits and selection of references

M01: Gemma4 SWE Agent Benchmark Audit, responsible account veerukhannan, declared creator Veerakrishna; dataset v6 created 2026-10-10T01:39:42.477Z. M02: Gemma4 Task Soundness and Local Results, account dmitriigluzdov; README/LICENSE declare Dmitry Gluzdov while API displays Dmitrii; dataset v8 created 2026-10-11T02:02:58.127Z. Dataset dates are not writeup publication dates. [Version evidence](evidence/dataset_versions.json) records the exact metadata entries: requested historical M02 view returned latest v10 description, which was not substituted for v8.

M01's [gradability_labels.csv](evidence/M01_v6_gradability_labels.csv) uses reference-resolves AND empty-does-not-resolve: 70 valid in its Python 3.12 configuration, 48 in 3.13, 47 shared IDs, 23 only 3.12, 1 only 3.13, 58 neither. [The 47 identifiers](evidence/M01_shared_ids.csv) are retained. Both configurations also change packages/available wheels; the difference is not isolated Python causality. Its Python 3.13 cause labels are publisher evidence, not new causal experiments.

M02's [task_soundness.csv](evidence/M02_v8_task_soundness.csv) has 114 sound=1. Four flags alone give 117; rich_3480, rich_3772, rich_4006 have empty_exit_code 124, error flags 0, and explicit timeout exclusions. [Timeout rows](evidence/M02_timeouts.json) preserve that distinction. The primary mask is sound=1, not an adjusted four-flag predicate. Neither 129-row CSV has duplicate IDs or necessary missing values. Nine M02 dependency-only overlays and different control rules prevent treating these as independent replications or interchangeable masks. Direct M01↔M02 data reuse is not established; shared IDs do not prove independence either.

The writeup [What the Graph Sees and What the Grader Measures](https://www.kaggle.com/datasets/veerukhannan/gemma4-swe-benchmark-audit?datasetVersionNumber=6) is consulted as paper.md inside M01 v6. Its title comes from README; no byline, editorial publication date or editorial version is confirmed. [File identity](evidence/M01_writeup_identity.json) retains SHA256; the file can be obtained through the [version 6 archive endpoint](https://www.kaggle.com/api/v1/datasets/download/veerukhannan/gemma4-swe-benchmark-audit?datasetVersionNumber=6). Dataset v6 does not mean writeup version 6.

Final dataset pages: [M01 v6](https://www.kaggle.com/datasets/veerukhannan/gemma4-swe-benchmark-audit?datasetVersionNumber=6), [M02 v8](https://www.kaggle.com/datasets/dmitriigluzdov/gemma-4-task-soundness-and-local-results?datasetVersionNumber=8). Derived labels/measurements retain CC BY 4.0 attribution; M01 declares Apache 2.0 for its code, which is not included. No competition issue text, reference/test patches or repository snapshots are redistributed from these datasets.

The main's 17 references are an actual-use selection from the unchanged 25-entry master and four newly rechecked primary papers; public metadata, versioned URLs, original-capture hashes and selectors are retained in [SOURCE_INDEX.json](sources/SOURCE_INDEX.json); fulltexts remain outside this bundle. Du et al. distinguish code/environment crash causes and assess proposed repairs; DEPBENCH repairs source under retained upgrades; Advani's false-success outcome requires an explicit success signal, unlike our closure predicate; RepoRescue v1 distinguishes source-only auditing, runtime blocking and realistic-use validation after PASS. These works constrain broad novelty claims. Some selected entries already existed in the master; the master itself is not expanded or rewritten here. [CITATIONS.json](CITATIONS.json) contains versions, primary URLs and source locations; [REFERENCIAS.bib](REFERENCIAS.bib) is the selected bibliography. M01W uses the versioned dataset page and retains the `paper.md` note. Reference 1 now uses the canonical official competition Data URL: the organizer's baseline-failure and reference-success passage was verified through Kaggle's official PageService `ListPages`, competition 149921, page 752212 (`data-description`). The earlier official Input Data passage embedded in Getting Started remains provenance, not a secondary opinion. Curation is a declared procedure, not a universal guarantee. RFC 8259 is not needed for the local one-object/channel/schema decisions; unused entries are not forced into citations.

## S7 Environment, identities and historical reproducibility

The [environment inventory](evidence/environment_inventory.md) gives all ten wheels with versions/SHA256, three selectable profiles, runtime build/flags and GGUF hashes. [License inventory](evidence/wheel_license_inventory.json) binds each wheel to retained notices. Profiles: typer0153_click820 (0.15.3/8.2.0), typer0153_click818 (0.15.3/8.1.8), typer0160_click820 (0.16.0/8.2.0). Missing-Typer and missing-Rich states are initial only. R3 preserves COLUMNS 100 and its original traceback behavior; exploration's COLUMNS 80/standard traceback was not transferred.

C3 GGUF SHA256 676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee; C1 SHA256 8e30dff3ac4c8434c49a7036fa15564bdbb6044e42bf04550bf1a096ad7e6a52. Windows llama.cpp b11429 commit d81235049384534c167caea52b85a694f6103d14 binary SHA256 7e236243c9b670c6a49410c03186fd575c57a0efe3fd8a21d8727503d571d5b6. Model/runtime binaries are not included. [Server flags C1](evidence/server_C1.json) keep alias sourceenv-v05-c3, but C1 loaded E2B; [the model binding](evidence/C1_model_binding.json) preserves basename, source selectors and hashes without local model paths. Alias is not weight identity. Sanitized model/engine identities in the [proposal](evidence/r3_proposal.json) bind each configuration.

Freeze SHA256 ddd3a67d19fe8bd652a1df56ae6b9b8e77ad0b1c5585687e7f46fd35ba15e3e1; commit af16d2f3d2555350e5a50dca704bdaea6757acdf. [Retained seal fields](evidence/seal.json) record GitHub Actions created_at 2026-10-12T01:11:13Z, distinct from the commit date. The repository/receipt remain private; no private repository link is presented as open access. Later publication of that retained receipt cannot create a pre-R3 public certification date. The distribution dossier preserves provenance and access limits; it neither reseals nor publishes the private repository.

Historical clean check: fresh Debian 13.7 / Python 3.13.5 / Bubblewrap 0.12.0, Linux llama.cpp built at the same tag/commit. Each driver reproduced 8 reference PASS/PASS and 8 noop FAIL/FAIL episodes. One E2B/H-RC0 diagnostic smoke had 16 calls, 2,267 tokens, 27 applications and PASS/PASS; PASS was not an integration requirement. The historical 32 scripted episodes used 576 applications; with smoke, 603. These costs are separate from R3 and this editorial phase. [Historical check record](evidence/historical_clean_check.md) is evidence already retained, not a new execution. Scripted context counts are not real-model token measurements.

## S8 Availability and review status

The review distribution is version [1.0.0-rc3](../SourceEnv/VERSION), with publication status `NOT_PUBLISHED`. [LICENSING.md](LICENSING.md) explains the MIT OR Apache-2.0 grant for project-authored material and the verified Paper Track license requirement. External audit labels remain CC BY 4.0 with attribution; dependency, model and other third-party terms remain separate. No model binaries, dependency wheels or complete private conversations are bundled. Historical grants and frozen source headers are unchanged.

Availability has four distinct scopes:

| Scope | What can be checked or used | Evidence and limits |
| --- | --- | --- |
| Bytes and offline analysis | Verify distribution files, recompute aggregate tables and closure patterns, and inspect endpoint captures | Retained files, hashes and selectors; full private conversations remain unavailable |
| Scripted controls | `reproduce.py` keeps its 16 default reference/noop episodes; `validate_fixture.py` adds a separate metadata-driven validation matrix | Existing Bubblewrap/oracle path; fresh states, scoring before cleanup, failures and costs retained |
| Future agent evaluation | `run_agent.py` offers portable native or compatible endpoint entry points | Requires a separately supplied backend/model and applicable terms; future evaluations are not R3 replications or new results in this delivery |
| Historical results and receipts | Inspect retained R3 aggregates, selected excerpts and the receipt dossier | Private originals have limited access; later publication does not create an earlier public certification date |

The [fixture guide](../SourceEnv/FIXTURES.md) specifies the real `stateless-cli-v1` schema, six operations, initial/reference/alternative/negative expectations, source/profile bindings and isolation limits. Adding a fixture requires adapting and versioning the currently coupled catalog, contract, oracle, profiles and harness selectors. The new validator is external to the frozen R3 core; its evidence is separate from model results.

From the resource directory on supported Debian, the model-free control command is:

```sh
/usr/bin/python3 -I -S reproduce.py --wheelhouse /opt/sourceenv-wheels
```

Prerequisites are an ordinary unprivileged account, trusted Python with venv, Bubblewrap with the required user/PID/network namespaces, and the ten original hash-verified wheels supplied outside the package. Each run needs fresh output/state directories and space for retained captures. Optimized Python, privileged execution or missing isolation block execution; there is no unsafe fallback. Prerequisite fetching is distinct from network-disabled candidate execution. [README](../SourceEnv/README.md), [RUNNING](../SourceEnv/RUNNING.md) and the fixture guide document the supported commands and limits.

The historical fresh-Debian check is tied to its tested components in [HISTORICAL_CLEAN_CHECK.md](../SourceEnv/HISTORICAL_CLEAN_CHECK.md) and [historical_clean_binding.json](../SourceEnv/evidence/historical_clean_binding.json). It must not be described as never executed, or transferred wholesale to new tooling. The rc2 validation used an overlay of an existing Debian VM, not a new installation; its [execution receipt](../release-info/history/rc2/validation/RELEASE_VALIDATION.json) and costs are preserved unchanged; its ZIP and raw execution records remain access-limited and are not bundled. The [documentary addendum](DOCUMENTARY_ADDENDUM.md) links rc3 to rc2 by exact component hashes. No rc3 applications, controls or model were executed.

The current resource archive is `SourceEnv-1.0.0-rc3.zip`. Its manifest identifies component bytes and its checksum receipt identifies ZIP bytes. The [current sidecar](../release-info/validation/RELEASE_VALIDATION.json) records CRC/integrity, manifest verification and component equivalence only. The tested rc2 ZIP retains its own SHA256 and execution receipt. Neither release identity replaces the experimental R3 freeze. The [receipt dossier](../release-info/receipt-dossier/README.md) remains unchanged; evidence and access limits are preserved.

[RELEASE_CHECKSUMS.json](../release-info/RELEASE_CHECKSUMS.json) records the current rc3 ZIP and manifest SHA256; the [addendum](DOCUMENTARY_ADDENDUM.md) lists both releases. They are distribution identities, distinct from the experimental freeze and historical receipt.

No public download URL or persistent identifier exists yet. Publication must use a separate destination from the historical private repository; visibility and history are preserved. The concrete publication files and commands accompany this review. No additional model experiment is planned or implied by this delivery.
