"""Host-side analysis of the CED run, applying PROTOCOLO_CED_POSTHOC.md as sealed.

Reads out-ced/results.json + masking_plan/plan.json; writes ced_analysis.json and
prints a table. Definitions are exactly those of the protocol; nothing tuned here.
"""
import json
import sys
from pathlib import Path

OPS = ("first_command", "second_command", "no_args", "explicit_help",
       "first_command_help", "second_command_help")
ENV = {"EC-MISSING", "EC-SYMBOL", "EH-API", "EH-RENDERER"}


def main(plan_path, results_path, out_path):
    plan = json.loads(Path(plan_path).read_bytes())
    res = {r["id"]: r for r in json.loads(Path(results_path).read_bytes())}
    rows = {r["id"]: r for r in plan["rows"]}
    cases = {}
    for r in plan["rows"]:
        cases.setdefault(r["case_id"], {})
    missing = [i for i in rows if i not in res]

    def sig(rid, op):
        o = res[rid]["operations"][op]
        return (o["exit_code"], o["stdout_sha256"], o["stderr_sha256"])

    out = {"protocol": "PROTOCOLO_CED_POSTHOC.md", "missing_rows": missing, "fixtures": {}, "candidates": []}
    spec_id = {}
    for rid, r in rows.items():
        if r["kind"] == "spec":
            spec_id[r["case_id"]] = rid
    for cid, sid in spec_id.items():
        rep = sid + "#1"
        floor = [op for op in OPS if sig(sid, op) != sig(rep, op)]
        out["fixtures"][cid] = {"spec": sid, "spec_status": res[sid]["status"],
                                "spec_repeat_status": res[rep]["status"], "determinism_floor": floor}
    # group candidate rows by (case, label)
    groups = {}
    for rid, r in rows.items():
        if r["kind"] in ("spec", "spec_repeat"):
            continue
        groups.setdefault((r["case_id"], r["label"], r["sha256"]), []).append(r)
    from collections import OrderedDict
    for (cid, label, h), rs in sorted(groups.items()):
        cases_json = None
        prof = {r["profile"]: res[r["id"]] for r in rs}
        # damaged/restored profiles from spec row and plan rows
        restored = rows[spec_id[cid]]["profile"]
        damaged_rows = [r for r in rs if r["profile"] != restored]
        restored_rows = [r for r in rs if r["profile"] == restored]
        rec = OrderedDict(case_id=cid, label=label, sha256=h, kind=rs[0]["kind"], origin=rs[0]["origin"],
                          axis="environment" if cid in ENV else ("healthy" if cid.startswith("H-") else "source"))
        if damaged_rows:
            rec["omega_damaged"] = res[damaged_rows[0]["id"]]["status"]
            rec["damaged_checks_passed"] = sum(res[damaged_rows[0]["id"]]["checks"].values())
        if restored_rows:
            rid = restored_rows[0]["id"]
            rec["omega_restored"] = res[rid]["status"]
            rec["delta_restored_vs_spec"] = [op for op in OPS if sig(rid, op) != sig(spec_id[cid], op)]
            rec["delta_kinds"] = {op: [k for k, a, b in zip(("exit_code", "stdout", "stderr"), sig(rid, op), sig(spec_id[cid], op)) if a != b]
                                  for op in rec["delta_restored_vs_spec"]}
        cls = None
        if cid in ENV and rec.get("omega_damaged") == "PASS":
            if rec.get("omega_restored") == "FAIL":
                cls = "ENV_COUPLED"
            elif rec.get("delta_restored_vs_spec"):
                cls = "DIVERGENT_UNDER_RESTORATION"
            else:
                cls = "OBSERVATIONALLY_EQUIVALENT"
        elif cid in ENV:
            cls = "DOES_NOT_CLOSE"
        rec["ced_class"] = cls
        out["candidates"].append(rec)
    Path(out_path).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("missing rows:", missing)
    for cid, f in out["fixtures"].items():
        print(f"{cid:12} spec={f['spec_status']}/{f['spec_repeat_status']} floor={f['determinism_floor']}")
    for c in out["candidates"]:
        print(f"{c['case_id']:12} {c['label']:20} dam={c.get('omega_damaged','-'):4} res={c.get('omega_restored','-'):4} "
              f"delta={c.get('delta_restored_vs_spec')} class={c['ced_class']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
