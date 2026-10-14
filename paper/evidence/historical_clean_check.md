# Clean Debian check — VERIFIED

Completed on 2026-10-13 in a newly installed Debian 13.7 VM: ordinary account, Python 3.13.5, Bubblewrap 0.12.0, 4 vCPUs and 6 GiB RAM. Its new disk and installation did not reuse the historical VM's environments, caches or experiment states. Administrative evidence stays outside the public distribution.

| CLEAN_MACHINE step | Expected | Observed |
| --- | --- | --- |
| 1 — prerequisites and isolation | Ordinary account; Debian 13; Bubblewrap | Passed; isolation checks passed in all 33 episodes |
| 2 — integrity, tests, wheels | Intact package; ten exact wheels | Passed; 15 portable tests and ten SHA256 matches |
| 2 — reproduce controls | Eight reference PASS/PASS; eight noop FAIL/FAIL | All 16 matched; reference coverage 6/6, noop 0/6 |
| 3 — scripted public runner | Endpoints, actions, changes and BASE prefix preserved | All 16 matched; reference 8 actions and one effective repair; noop FC 20 actions, BASE finish at action 1 |
| 4 — runtime/model | Linux b11429; retained E2B identity | Compiled official tag, commit d81235049384534c167caea52b85a694f6103d14; GGUF matched R3 |
| 4 — readiness/smoke | Localhost; tools, exact context, scoring and costs | One H-RC0; both arms VALID, PASS/PASS, finish/finish; 16 calls, 2267 tokens, 27 applications |
| 5 — integrity/closure | Evidence retained; server stopped | Passed before/after correction; server exited 0, port closed; new VM shut down |

Analyses: `../SourceEnv_CleanCheck_20261013/analysis/reference-analysis.json`, `noop-analysis.json` and `smoke-H-RC0-01-analysis-corrected-debian.json`; original smoke analysis retained alongside. Every environment reference used `typer0160_click820`. Smoke maximum input: 5698 tokens, `context_accounting: exact`; FC coverage 6/6 and BASE 2/6 at the checkpoint. PASS is an observed behavioral result, not the integration criterion.

Demonstrated defect: aggregate `generated_tokens` stayed zero although exact bounds and episode recorded 2267. The alias now follows known usage; uncertain usage remains null with bounds. The analyzer explicitly normalizes older aliases. Seven tests passed on Windows and Debian, plus replay of all 16 real attempts. Raw evidence unchanged; no generations or applications repeated for the correction.

Deviations: QEMU/WHPX replaced unavailable Hyper-V administration; administrative SFTP replaced removable media; compilation supplemented the installed-server prerequisite; an equivalent non-generative urllib GET checked readiness. Shallow b11429 reports build 1; exact tag/commit and linked binary hashes retained. Linux symlinks/long paths prevent complete Windows extraction: the full SHA-verified TAR retains states, with metadata separately extracted.

Costs: 32 scripted episodes, zero model calls, 576 applications; one smoke, 16 calls, 2267 tokens, 27 applications. Total 603 applications, 66 probes, 302 workers, 41 offline installs. VM interval including installation: at most 1996.55 seconds. No R3 rerun or publication. Technically ready for human publication review; no access blocker remains.
