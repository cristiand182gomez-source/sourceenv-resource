# Licensing decision and review evidence

This new review package offers its project-authored manuscript, supplement, figure, documentation and helper code under **MIT OR Apache-2.0**, at the recipient's option, to the extent of the SourceEnv contributors' rights. The copyright notice remains **Copyright (c) 2026 SourceEnv contributors**. The grant and complete texts are [SourceEnv/LICENSE](../SourceEnv/LICENSE), [MIT](../SourceEnv/licenses/MIT.txt), and [Apache-2.0](../SourceEnv/licenses/Apache-2.0.txt); the same options apply to the owned material named in this paragraph. Third-party captures, quoted passages, data and notices are excluded. This changes only the new distribution. Historical licenses and experiment bytes are preserved.

The authorized preparation adds the Apache option required by the Paper Track's named winner-license type while retaining MIT. It does not assert an ownership transfer, organizer approval, winner status, eligibility certification, or a completed publication. The right to license belongs to the respective contributors; the existing contributor notice is preserved rather than replaced with an inferred individual legal identity.

## Verified primary rule scope

The complete competition-specific and foundational [Paper Track rules](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/rules) were retrieved from Kaggle's public official page service on 2026-10-14. Original response/text hashes, versioned URLs and JSON selectors, without the full captured works, are documented in [sources/KAGGLE_PRIMARY_VERIFICATION.json](sources/KAGGLE_PRIMARY_VERIFICATION.json). Public HTML alone returned a JavaScript shell; the public page API resolved the content. No rule acceptance, entry or submission was performed.

| Primary section | Consequence for this preparation |
| --- | --- |
| Specific 1.6 | Winner License Type is **Open Source Apache 2.0**. |
| Specific 2.5(a.1), 2.5(b) | Winning submission and generation source must receive the specified commercial-use-compatible open-source grant; methodology and reproduction instructions may be required. |
| Specific 2.5(a.2–a.3) | Unowned generally commercially available software procurable without undue expense, and incompatible-license input data/pretrained models, are explicitly excepted from the corresponding open-source grant. No relicensing of those items is attempted. |
| Specific 2.8 | Winner delivery includes reproduction-capable code/documentation and environment/resources; grant rights must be represented, and prize acceptance documents supplied if required. Preparing dual licensing alone does not prove all future winner obligations are met. |
| Specific 2.4 | Broad use permission coexists with restrictions on redistributing Competition Data to nonparticipants. Official inputs must be obtained through their authorized source. |
| Foundational preamble; 3.6; 3.14 | Foundational rules control conflicts; public Competition Code must also be shared on the competition-specific Kaggle forum/notebooks; third-party rights and original-work warranties remain applicable. |
| Submission Requirements | Code assets are optional; code, if submitted, should be a public notebook in Project Links. A public PDF link can carry the paper. Draft/unsubmitted writeups do not count. Private Kaggle resources attached to the public writeup become public after the deadline. |

For the later publication phase, use a separate public release destination, share relevant Competition Code on Kaggle as required, and attach only the deliberately public deliverables. Keep the historical private repository and access-limited conversations/receipts outside those attachments. Recheck rules and submission requirements at the actual submission date. No new experiment or historical public date is implied by publication.

## Third-party evidence and attribution

- **M01 labels:** Veerakrishna (Kaggle account `veerukhannan`), *Gemma 4 SWE Agent Benchmark Audit*, dataset v6 (2026-10-10), [versioned source](https://www.kaggle.com/datasets/veerukhannan/gemma4-swe-benchmark-audit?datasetVersionNumber=6). Its README declares labels **CC BY 4.0** and code **Apache-2.0**. `evidence/M01_v6_gradability_labels.csv` is retained without relabeling; counts, comparisons and tables are SourceEnv analysis derived from those labels. The writeup has no retained byline: the dataset account is provenance, not an invented author attribution.
- **M02 measurements/documentation:** Copyright 2026 **Dmitry Gluzdov**, *Gemma 4 Task Soundness and Local Results*, dataset v8 (2026-10-11), [versioned source](https://www.kaggle.com/datasets/dmitriigluzdov/gemma-4-task-soundness-and-local-results?datasetVersionNumber=8). **CC BY 4.0**; `evidence/M02_v8_task_soundness.csv` retains the published mask. SourceEnv's extracted timeout list, recounts and comparisons are derived analyses, not changed source labels. The source license notice is retained in `attributions/M02_v8_LICENSE.txt`.
- **CC BY 4.0:** [license and attribution conditions](https://creativecommons.org/licenses/by/4.0/). These materials remain under that license and are excluded from the SourceEnv dual grant. Do not imply endorsement by the cited authors.
- **Dependency notices:** ten wheel prerequisites and verbatim notices are identified in [resource/THIRD_PARTY_NOTICES.md](../SourceEnv/THIRD_PARTY_NOTICES.md); wheel payloads, runtimes and model weights are not distributed. Their original licenses and terms control.
- **Paper/webpage captures:** Full primary verification captures are retained privately; this public staging includes metadata and selectors only. arXiv's perpetual non-exclusive display license is not a general third-party republication license; the cited papers and webpage captures are not covered by the project grant. Exclude this fulltext verification archive from the public resource ZIP. Cite the canonical/versioned sources in the public paper and distribute only excerpts permitted by the applicable rights. Advani's retained HTML identifies CC BY 4.0; Du, DEPBENCH and RepoRescue identify the arXiv non-exclusive license.

No competition tasks, patches, snapshots, model weights or additional private conversations are licensed by this package. The prepared release grant and the historical experimental freeze are separate identities.

## Selected output channels

[CAPTURE_RIGHTS.md](CAPTURE_RIGHTS.md) reviews the eighty exact endpoint channels individually through the selected inventory. Short source/diagnostic fragments keep the relevant dependency notices and are excluded from any blanket project grant. M01/M02 source CSVs and derived masks/recounts are CC BY 4.0, separately attributed in [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md).
