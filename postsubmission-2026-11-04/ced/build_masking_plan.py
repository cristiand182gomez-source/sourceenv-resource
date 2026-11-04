"""Build the post-hoc counterfactual-environment plan (host side, no execution).

Inputs: the frozen rc3 SourceEnv tree (read-only), the R3 endpoint sources
extracted by extract_r3_endpoints.py, and the hand-written synthetic controls.
Output: candidates/ (exact bytes to stage) and plan.json (hash-bound rows).
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ENV = ("EC-MISSING", "EC-SYMBOL", "EH-API", "EH-RENDERER")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(rc3_root, endpoints_dir, synthetic_dir, out_dir):
    rc3, ep, syn, out = map(Path, (rc3_root, endpoints_dir, synthetic_dir, out_dir))
    cases = json.loads((rc3 / "source/cases.json").read_bytes())
    rows_r3 = json.loads((ep / "r3_endpoints.json").read_bytes())
    cand = out / "candidates"
    cand.mkdir(parents=True, exist_ok=False)
    staged = {}

    def stage(data, label):
        h = sha(data)
        name = f"{h[:16]}.py"
        if h not in staged:
            (cand / name).write_bytes(data)
            staged[h] = {"file": "candidates/" + name, "sha256": h, "labels": []}
        staged[h]["labels"].append(label)
        return staged[h]

    plan = []

    def row(cid, kind, origin, data, profile, label, repeat=0):
        s = stage(data, label)
        plan.append({"id": f"{cid}/{label}@{profile}" + (f"#{repeat}" if repeat else ""),
                     "case_id": cid, "kind": kind, "origin": origin, "label": label,
                     "source": s["file"], "sha256": s["sha256"], "profile": profile})

    for cid, case in cases.items():
        base = rc3 / "cases-package/cases" / cid
        ref = (base / "reference.py").read_bytes()
        init = (base / "initial.py").read_bytes()
        alt = (base / "alternative.py").read_bytes()
        rp, ip = case["reference_profile"], case["initial_profile"]
        env = cid in ENV
        # Behavioural specification and its determinism floor.
        row(cid, "spec", "AUTHOR_FIXTURE", ref, rp, "reference")
        row(cid, "spec_repeat", "AUTHOR_FIXTURE", ref, rp, "reference", repeat=1)
        if env:
            row(cid, "baseline_damaged", "AUTHOR_FIXTURE", init, ip, "initial")
            for p in sorted({ip, rp}):
                row(cid, "author_alternative", "AUTHOR_FIXTURE", alt, p, "alternative")
        seen = set()
        for r in rows_r3:
            if r["fixture"] != cid or not r["source_changed"]:
                continue
            data = (ep / r["final_source_file"]).read_bytes()
            key = sha(data)
            label = f"R3-{r['configuration']}-{r['arm']}"
            if key in seen:
                staged[key]["labels"].append(label)  # same bytes, already planned
                continue
            seen.add(key)
            for p in sorted({ip, rp}):
                row(cid, "r3_endpoint", "R3_MODEL_ENDPOINT", data, p, label)
    for f in sorted(syn.glob("*.py")):
        cid = f.name.split("__")[0]
        label = f.stem.split("__")[1]
        case = cases[cid]
        for p in sorted({case["initial_profile"], case["reference_profile"]}):
            row(cid, "synthetic_control", "SYNTHETIC_CONTROL_NOT_MODEL", f.read_bytes(), p, label)
    doc = {"schema": 1, "kind": "POSTHOC_COUNTERFACTUAL_ENVIRONMENT_NOT_PREREGISTERED",
           "rc3_package_manifest_sha256": sha((rc3 / "PACKAGE_MANIFEST.json").read_bytes()),
           "rows": plan, "candidates": sorted(staged.values(), key=lambda s: s["file"]),
           "limits": {"fresh_states": len(plan), "applications": 6 * len(plan),
                      "probes": 2 * len(plan), "workers": 2 * len(plan),
                      "offline_installs": len(plan), "machine_seconds": 5400,
                      "model_calls": 0, "automatic_retries": 0}}
    (out / "plan.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(plan), "unique_sources": len(staged), "limits": doc["limits"]}, indent=2))
    for r in plan:
        print(r["kind"].ljust(18), r["id"])


if __name__ == "__main__":
    main(*sys.argv[1:5])
