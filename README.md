# SourceEnv resource and paper

**Public release, verified on 2026-10-14.** Resource version **1.0.0-rc3** is available in the [versioned release](https://github.com/cristiand182gomez-source/sourceenv-resource/releases/tag/v1.0.0-rc3). “r4” identifies the editorial/distribution bundle, not a new experimental resource or run.

The current manuscript prepared for submission is the [Kaggle Writeup](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/writeups/sourceenv-separating-source-and-environment-fault). It is saved as a draft and has not been submitted; draft access may require the owner's account. The manuscript includes verified public destinations and presentation corrections made after publication.

**Historical snapshots:** `paper/DRAFT.md`, `paper/SUPPLEMENT.md`, the texts inside `SourceEnv/`, and the release bundles preserve the audited bytes prepared before publication. Their statements such as “not published” and `PENDING_PUBLICATION` describe that preparation stage, not the current availability of this repository. The paper snapshot is not the latest submission manuscript. Public release does not make the private historical predeclaration receipt publicly time-verifiable.

Project-authored material is offered under **MIT OR Apache-2.0**; third-party terms and attributions remain applicable. See the licensing links below.

SourceEnv separates the available source and environment repair axes in ten synthetic CLI fixtures (eight damaged and two healthy), with a six-operation contract, an oracle hidden from the agent at runtime, a sandboxed harness and derived BASE endpoints. The observed R3 model repairs used source edits; the resource's two axes do not imply that models changed profiles.

- [Resource README and quickstart](SourceEnv/README.md), [fixture guide](SourceEnv/FIXTURES.md), [running details](SourceEnv/RUNNING.md).
- [Audited paper snapshot](paper/DRAFT.md), [supplement](paper/SUPPLEMENT.md), [five selected excerpts](paper/EXTRACTOS.md), [figure](paper/figures/prefix_closure.png).
- [Licensing and attribution](paper/LICENSING.md), [external audit data](paper/DATA_ATTRIBUTION.md), [access limits](paper/ACCESS_LIMITS.md).
- [Explicit paper inventory](release-info/PAPER_MANIFEST.json), [link map](release-info/LINK_MAP.json), [file-dependency map](release-info/DEPENDENCY_INDEX.json).
- [Distribution checksums](release-info/RELEASE_CHECKSUMS.json), [documentary addendum](paper/DOCUMENTARY_ADDENDUM.md), [historical receipt dossier](release-info/receipt-dossier/README.md).

## Layout and integrity

The Git repository belongs in this parent directory. `SourceEnv/` must contain exactly the 158 files from the canonical `SourceEnv-1.0.0-rc3.zip`, whose SHA256 is `7a59f1c3cf01e49cbf98356d14de65bf83a7cfb492f0504c9badbe1c57704e28`. Its manifest SHA256 is `a6e4d165738b27cb05ec102ca5c1f695a226c044f14b91fc9431a0e28fa7230d`. Do not initialize Git, create outputs, install an environment or add documentation inside `SourceEnv/`. The parent `.gitattributes` disables text conversion for that subtree; the publication procedure also uses `core.autocrlf false`.

The integrity command below checks the **original release tree**: extract `SourceEnv-paper-r4.zip` from the versioned release into a separate directory, or use a checkout of audited commit `20dfaf03122d62888d8550f558dcc25e5f66f002`. Run it from that extracted parent directory. It checks bytes and inventories only:

```sh
python3 -B release-info/verify_public_tree.py .
```

The release inventory hashes the root README as well as the resource and paper files. This post-publication README update intentionally differs from that inventory; do not run the original whole-tree check against the updated `main` checkout. The original release bundle and audited commit remain unchanged.

It neither imports the evaluation core nor executes applications or models. On Windows, replace `python3` with the installed Python executable. Model-free controls and agent evaluation are separate commands documented in the resource; they are not part of publication validation. Put their outputs outside the package, as documented.

The paper bundle includes this parent tree and the exact resource subtree so that its relative links work offline. The separate canonical resource ZIP remains byte-for-byte rc3. The tested predecessor was rc2; rc3 has documentary/component-equivalence checks, not a new execution of its whole archive. Historical R3, the clean-machine check, rc2 controls and this offline r4 preparation remain distinct.

The repository, original commit tree and release assets were verified publicly on 2026-10-14. The release tag remains attached to audited commit `20dfaf03122d62888d8550f558dcc25e5f66f002`; this status-only README correction does not change any release asset or the historical link map. The original private repository, full conversations, raw execution states, model weights and dependency wheels are not included.
