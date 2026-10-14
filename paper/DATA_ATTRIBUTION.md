# M01/M02 source data and derived analyses

These materials remain **CC BY 4.0**, outside the SourceEnv MIT OR Apache-2.0 grant. See the [license terms](https://creativecommons.org/licenses/by/4.0/) and [legal code](https://creativecommons.org/licenses/by/4.0/legalcode). No endorsement is implied.

| Source | Creator, version and primary URL | Unmodified CSV and SHA256 |
| --- | --- | --- |
| M01: Gemma 4 SWE Agent Benchmark Audit | Veerakrishna (account `veerukhannan`), v6, created 2026-10-10T01:39:42.477Z; [versioned dataset](https://www.kaggle.com/datasets/veerukhannan/gemma4-swe-benchmark-audit?datasetVersionNumber=6) | [M01_v6_gradability_labels.csv](evidence/M01_v6_gradability_labels.csv), `7f54059a0e79c28c0f46f9ab8d92b4c61706274b61285603f48131fc8ebbe408` |
| M02: Gemma 4 Task Soundness and Local Results | Copyright 2026 Dmitry Gluzdov (account `dmitriigluzdov`; API display Dmitrii), v8, created 2026-10-11T02:02:58.127Z; [versioned dataset](https://www.kaggle.com/datasets/dmitriigluzdov/gemma-4-task-soundness-and-local-results?datasetVersionNumber=8) | [M02_v8_task_soundness.csv](evidence/M02_v8_task_soundness.csv), `910280fba76a0578eefe00f5e14b764969b8caa2f77032a671ec3f927c0ca142` |

[M01's license notice excerpt](attributions/M01_v6_LICENSE_EXCERPT.md) attributes its labels to CC BY 4.0 and code to Apache-2.0; that code is not included. [M02's original license notice](attributions/M02_v8_LICENSE.txt) is retained verbatim. [Version metadata](evidence/dataset_versions.json) retains dates, version selectors and original metadata hashes. M02's later dataset description is not substituted for version 8. M01's `paper.md` title is known, but its editorial version, date and byline are not inferred from the dataset version.

The CSV bytes are unmodified. SourceEnv's [recount](evidence/M01_M02_recount.json), [explicit masks](evidence/M01_M02_masks.json), [47 shared IDs](evidence/M01_shared_ids.csv), [timeout extraction](evidence/M02_timeouts.json) and comparative tables are identified derived analyses, not publisher relabeling. These derived data retain CC BY 4.0 attribution. M01 uses the published `gradable` label (reference passes and empty fails). M02's primary mask is `sound=1` (114); the four flags alone yield 117, with `rich_3480`, `rich_3772` and `rich_4006` explicitly excluded for empty-control timeout. All denominators remain 129 unique IDs.

Differences between the M01 configurations involve Python and packages/wheels. They do not isolate a causal Python effect. Shared task IDs do not establish independent replication between M01 and M02. No competition task text, reference/test patches, repository snapshots or complete third-party writeup is included in this bundle.
