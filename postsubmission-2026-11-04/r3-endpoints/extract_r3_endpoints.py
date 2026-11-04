"""Offline, read-only extraction of R3 endpoint source states.

Reads the retained R3 evidence ZIP (never modified) and writes, for each of
the 40 arms (2 configurations x 10 fixtures x {FC, BASE}):
  - initial and final app.py bytes (from the scorer's own snapshots),
  - before/after profile, versions and oracle checks,
  - a unified diff initial -> final.
No application is executed. Output goes to a new directory.
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import json
import sys
import zipfile
from pathlib import Path

CONFIGS = ("C3", "C1")
FIXTURES = ("SC-BALANCE", "SC-SORT", "SH-FLAG", "SH-FORMAT", "EC-MISSING",
            "EC-SYMBOL", "EH-API", "EH-RENDERER", "H-RC0", "H-RC2")
ENV_FIXTURES = {"EC-MISSING", "EC-SYMBOL", "EH-API", "EH-RENDERER"}
ROOT = "frozen-package/execution/{c}/guest-metadata/runs/{c}-{f}/"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def snap(side: dict) -> bytes:
    return base64.b64decode(side["source_snapshot_base64"]["app.py"])


def summarize(score: dict) -> dict:
    return {
        "status": score.get("status"),
        "checks": score.get("checks"),
        "passed": score.get("operations_passed"),
        "total": score.get("operations_total"),
        "profile_before": score["before"]["profile"],
        "profile_after": score["after"]["profile"],
        "versions_after": score["after"]["versions"],
        "app_sha256_before": sha(snap(score["before"])),
        "app_sha256_after": sha(snap(score["after"])),
    }


def main(zip_path: str, out_dir: str) -> int:
    zf = zipfile.ZipFile(zip_path)
    out = Path(out_dir)
    (out / "sources").mkdir(parents=True, exist_ok=True)
    (out / "diffs").mkdir(parents=True, exist_ok=True)
    rows = []
    for c in CONFIGS:
        for f in FIXTURES:
            base = ROOT.format(c=c, f=f)
            initial = json.loads(zf.read(base + "initial-score.json"))
            arms = {
                "FC": json.loads(zf.read(base + "final-score.json")),
                "BASE": json.loads(zf.read(base + "derived-base/final-score.json")),
            }
            init_bytes = snap(initial["before"])
            init_name = f"{f}.initial.py"
            (out / "sources" / init_name).write_bytes(init_bytes)
            for arm, score in arms.items():
                final_bytes = snap(score["after"])
                s = summarize(score)
                name = f"{c}-{f}-{arm}.final.py"
                (out / "sources" / name).write_bytes(final_bytes)
                diff = "".join(difflib.unified_diff(
                    init_bytes.decode("utf-8", "replace").splitlines(True),
                    final_bytes.decode("utf-8", "replace").splitlines(True),
                    fromfile=f"{f}/initial/app.py", tofile=f"{c}/{arm}/final/app.py"))
                (out / "diffs" / f"{c}-{f}-{arm}.diff").write_text(diff, encoding="utf-8")
                pass_all = s["passed"] == s["total"]
                rows.append({
                    "configuration": c, "fixture": f, "arm": arm,
                    "axis": "environment" if f in ENV_FIXTURES else (
                        "healthy" if f.startswith("H-") else "source"),
                    "endpoint_pass": pass_all,
                    "initial_app_sha256": sha(init_bytes),
                    "initial_profile": initial["before"]["profile"],
                    "source_changed": sha(init_bytes) != s["app_sha256_after"],
                    "profile_changed": initial["before"]["profile"] != s["profile_after"],
                    "diff_lines_changed": sum(1 for line in diff.splitlines()
                                              if line[:1] in "+-" and not line.startswith(("+++", "---"))),
                    "final_source_file": f"sources/{name}",
                    **s,
                })
    (out / "r3_endpoints.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"arms={len(rows)}")
    for r in rows:
        print(f"{r['configuration']} {r['fixture']:12} {r['arm']:4} pass={int(r['endpoint_pass'])} "
              f"{r['passed']}/{r['total']} src_changed={int(r['source_changed'])} "
              f"prof_changed={int(r['profile_changed'])} dlines={r['diff_lines_changed']} "
              f"profile={r['profile_after']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
