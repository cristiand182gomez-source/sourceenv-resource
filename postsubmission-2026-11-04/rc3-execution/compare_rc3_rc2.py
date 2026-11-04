"""Compare the new rc3 public-ZIP run with the rc2 evidence shipped in the package.

Fields that are by construction run-specific (episode hashes, state identities,
timings) are excluded and listed; every other field must be equal.
"""
import json
import sys
from pathlib import Path

RUN_SPECIFIC = {"episode_sha256", "state_identity", "elapsed_seconds", "scenario_sha256", "score_sha256"}


def strip(row):
    return {k: v for k, v in row.items() if k not in RUN_SPECIFIC}


def main(new_resolvability, shipped_resolvability, new_validator, shipped_validation_json, out):
    new = json.loads(Path(new_resolvability).read_bytes())
    old = json.loads(Path(shipped_resolvability).read_bytes())
    old_rows = old if isinstance(old, list) else old.get("rows", old.get("results", old))
    diffs = []
    key = lambda r: (r["fixture"], r["control"])
    om = {key(r): r for r in old_rows}
    for r in new:
        o = om.get(key(r))
        if o is None:
            diffs.append({"row": key(r), "issue": "missing_in_rc2"})
            continue
        a, b = strip(r), strip(o)
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                diffs.append({"row": key(r), "field": k, "rc3": a.get(k), "rc2": b.get(k)})
    val = json.loads(Path(new_validator).read_bytes())
    report = {"reproduce_rows_rc3": len(new), "reproduce_rows_rc2": len(old_rows),
              "excluded_run_specific_fields": sorted(RUN_SPECIFIC), "reproduce_differences": diffs,
              "validator_rows": len(val), "validator_all_pass": all(v["validation_status"] == "PASS" for v in val),
              "validator_oracle_status_counts": {s: sum(v["oracle_status"] == s for v in val) for s in ("PASS", "FAIL")}}
    if shipped_validation_json and Path(shipped_validation_json).exists():
        sv = json.loads(Path(shipped_validation_json).read_bytes())
        report["shipped_fixture_validation_note"] = "rc2 receipt fields: " + ", ".join(list(sv)[:12])
    Path(out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "reproduce_differences"}, indent=2))
    print("differences:", len(diffs))
    for d in diffs[:20]:
        print(d)


if __name__ == "__main__":
    main(*sys.argv[1:6])
