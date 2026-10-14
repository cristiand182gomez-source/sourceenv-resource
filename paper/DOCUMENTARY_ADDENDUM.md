# Documentary addendum — SourceEnv 1.0.0-rc3

The extraction instruction in `../SourceEnv/CLEAN_MACHINE.md`, step 2, now says **Extract `SourceEnv/`**, the actual ZIP root. All other bytes of the numbered procedure are preserved. Distribution version, documentation and manifests were updated to distinguish this revision from the tested predecessor. There is no change to executable code, fixtures, prompts, profiles, oracle, sandbox, budgets or metrics.

| Identity | Executed predecessor rc2 | Documentary revision rc3 |
| --- | --- | --- |
| Archive | `SourceEnv-1.0.0-rc2.zip` (access-limited original; not bundled) | `SourceEnv-1.0.0-rc3.zip` (canonical release asset; publication pending) |
| ZIP SHA256 | `18f9d83a432b4213f63408e66ff51694471b8c6caf0b83a6dd215198c41fc71e` | `7a59f1c3cf01e49cbf98356d14de65bf83a7cfb492f0504c9badbe1c57704e28` |
| Manifest SHA256 | `ae78ad40f529d8bff24e7ee6a2c35946c6602997e7a1403935c0141cb9dd5fca` | `a6e4d165738b27cb05ec102ca5c1f695a226c044f14b91fc9431a0e28fa7230d` |
| Archive bytes | 229,675 | 230,002 |
| Evidence | [Unchanged rc2 execution receipt](../release-info/history/rc2/validation/RELEASE_VALIDATION.json) | [Current documentary receipt](../release-info/validation/RELEASE_VALIDATION.json) |

Both archives pass CRC. The rc3 inventory/manifest hashes and every member were checked against the extracted distribution tree. Of 158 members, 151 are byte-identical; the seven differing files are four Markdown documents, VERSION and the two distribution manifest files. The [complete comparison](../release-info/validation/COMPONENT_EQUIVALENCE.json) records every before/after hash, the tested rc2 member inventory and all 95 executable/input components bound by the retained validator plan. Those 95 components, all Python files and all files under source/cases-package/tests are unchanged. [RESOURCE.diff](../release-info/RESOURCE_RC2_TO_RC3.diff) gives the exact documentary/metadata differences.

**The rc3 ZIP was not executed.** Its unchanged components are linked to rc2's retained checks by bytes. The earlier 16 scripted episodes, 24 additional scenarios and their 432 application captures belong to rc2; they were not repeated or charged as current work. This phase used zero models, applications, probes, workers, offline installations, repeated controls or network requests. No sandbox changes were made.

The original rc2 folder, ZIP and receipts remain intact; only the selected receipt is included in this public staging, with its original bytes/hash; the full local history is not bundled. Current manuscript and supplement state the documentary scope and identify rc3. The R3 experimental freeze and results are unchanged. Publication and submission remain pending; neither GitHub visibility/history nor Kaggle was changed.

## Distribution staging r4

This delivery rearranges the public repository around the unchanged rc3 package. It does not create rc4. The resource ZIP, all 158 members and internal manifests are unchanged. The [dependency map](../release-info/DEPENDENCY_INDEX.json) distinguishes bundled files from historical source identifiers. SHA256 of a withheld original is not a downloadable copy or proof that all trajectory metrics can be independently reconstructed. [ACCESS_LIMITS.md](ACCESS_LIMITS.md) lists exclusions. No public HTTP destination has been checked in this phase.
