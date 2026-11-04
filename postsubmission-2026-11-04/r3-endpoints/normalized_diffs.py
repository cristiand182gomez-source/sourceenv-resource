"""Line-ending-normalized diff statistics for extracted R3 endpoints (offline)."""
import difflib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = json.loads((root / "r3_endpoints.json").read_text(encoding="utf-8"))
out = []
for r in rows:
    init = (root / "sources" / f"{r['fixture']}.initial.py").read_bytes()
    fin = (root / r["final_source_file"]).read_bytes()
    a = init.decode().replace("\r\n", "\n").splitlines()
    b = fin.decode().replace("\r\n", "\n").splitlines()
    # ignore pure blank-line differences as well
    a2 = [x.rstrip() for x in a if x.strip()]
    b2 = [x.rstrip() for x in b if x.strip()]
    d = [x for x in difflib.unified_diff(a2, b2, lineterm="", n=0)
         if x[:1] in "+-" and not x.startswith(("+++", "---"))]
    r2 = {k: r[k] for k in ("configuration", "fixture", "arm", "axis", "endpoint_pass")}
    r2.update({
        "crlf_initial": b"\r\n" in init, "crlf_final": b"\r\n" in fin,
        "semantic_lines_removed": [x[1:] for x in d if x.startswith("-")],
        "semantic_lines_added": [x[1:] for x in d if x.startswith("+")],
    })
    r2["only_whitespace_or_eol"] = not d
    out.append(r2)
(root / "r3_normalized_diffs.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
for r in out:
    if r["arm"] == "BASE":
        continue
    print(f"{r['configuration']} {r['fixture']:12} pass={int(r['endpoint_pass'])} ws_only={int(r['only_whitespace_or_eol'])} "
          f"-{len(r['semantic_lines_removed'])} +{len(r['semantic_lines_added'])} crlf {int(r['crlf_initial'])}->{int(r['crlf_final'])}")
    for x in r["semantic_lines_removed"]:
        print("     -", x)
    for x in r["semantic_lines_added"]:
        print("     +", x)
