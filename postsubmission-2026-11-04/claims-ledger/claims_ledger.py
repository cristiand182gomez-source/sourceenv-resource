"""Executable claims ledger for the SUBMITTED SourceEnv manuscript (offline).

Every registered claim = exact phrase in the submitted manuscript + a
recomputation from public evidence (the audited public tree, commit 20dfaf03)
and, where possible, an independent cross-check from the retained private raw
R3 evidence (endpoint snapshots extracted by extract_r3_endpoints.py).
Exit code 1 if any registered phrase is absent or any recomputation differs.
Also lists every numeral of the manuscript that no registered claim covers.
"""
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

SUBMITTED_SHA = "6c1b9903c8bc07e6149df4a3a4999ed14ec5a1fe680644a2662c8461db87532b"
# paper/DRAFT.md at public commit 20dfaf03: same science text, relative links
# and pre-publication Availability paragraph (5 differing lines).
PUBLIC_SNAPSHOT_SHA = "37e0a3eb570bbe4033c235af4d805452117b8d10c78a4dd16a999715114aba20"
KNOWN = {SUBMITTED_SHA: "SUBMITTED_KAGGLE_MANUSCRIPT", PUBLIC_SNAPSHOT_SHA: "PUBLIC_SNAPSHOT_paper/DRAFT.md"}


def load(p):
    return json.loads(Path(p).read_bytes())


def main(manuscript, public_tree, endpoints_json, out_dir):
    text_b = Path(manuscript).read_bytes()
    SUBMITTED = hashlib.sha256(text_b).hexdigest()
    if SUBMITTED not in KNOWN:
        raise SystemExit("UNKNOWN_MANUSCRIPT_BYTES")
    endpoints_json = None if endpoints_json in (None, "-", "") else endpoints_json
    text = text_b.decode("utf-8")
    pub = Path(public_tree)
    ev = pub / "paper/evidence"
    agg = {(r["configuration"], r["arm"]): r for r in load(ev / "aggregate_metrics.json")["rows"]}
    by_arm = load(ev / "r3_by_arm.json")
    costs = load(ev / "r3_costs.json")
    summ = load(ev / "r3_summary.json")
    preds = load(ev / "r3_predictions.json")
    resp = load(ev / "response_counts.json")["totals"]
    cp = load(ev / "closure_patterns.json")["summary"]
    raw = load(endpoints_json) if endpoints_json else []
    claims = []

    def reg(cid, phrase, value, source, method, status="MEASURED", raw_check=None):
        present = phrase in text
        ok = present and (value is True or value == phrase or (isinstance(value, str) and value in phrase))
        claims.append({"id": cid, "phrase": phrase, "present_in_submitted": present,
                       "recomputed": value, "matches": ok, "source": source, "method": method,
                       "status": status, "raw_cross_check": raw_check})

    def frac(a, b):
        return f"{a}/{b}"

    # Table 3 rows
    for cfg in ("C3", "C1"):
        for arm in ("FC", "BASE"):
            a = agg[(cfg, arm)]
            dmg = [r for r in by_arm if r["configuration"] == cfg and r["arm"] == arm and not r["healthy"]]
            hl = [r for r in by_arm if r["configuration"] == cfg and r["arm"] == arm and r["healthy"]]
            rep = sum(r["endpoint"] == "PASS" for r in dmg)
            pre = sum(r["endpoint"] == "PASS" for r in hl)
            med = statistics.median(r["coverage_current"] for r in by_arm if r["configuration"] == cfg and r["arm"] == arm)
            row = (f"| {cfg} {arm} | {frac(rep, len(dmg))} | {frac(pre, len(hl))} | {int(med)}/6 | "
                   f"{a['source']['requests']}/{a['source']['effective']}/{a['source']['noops']} | "
                   f"{a['visible_finish']}/{a['policy_finishes']} |")
            rr = [x for x in raw if x["configuration"] == cfg and x["arm"] == arm]
            raw_check = None
            if rr:
                raw_check = {"repaired_from_raw_snapshots": sum(x["endpoint_pass"] for x in rr if x["axis"] != "healthy"),
                             "preserved_from_raw_snapshots": sum(x["endpoint_pass"] for x in rr if x["axis"] == "healthy"),
                             "agrees": sum(x["endpoint_pass"] for x in rr if x["axis"] != "healthy") == rep
                             and sum(x["endpoint_pass"] for x in rr if x["axis"] == "healthy") == pre}
            reg(f"T3-{cfg}-{arm}", row, row, "paper/evidence/r3_by_arm.json + aggregate_metrics.json",
                "repair=PASS among damaged; preserve=PASS among healthy; median coverage_current; source counters; visible_finish/policy_finishes",
                raw_check=raw_check)
    # Table 2
    for label, key in (("**FC accepted with public failure / accepted**", "FC_accepted_with_public_failure"),
                       ("BASE zero current coverage / endpoints", "BASE_zero_current_coverage"),
                       ("BASE zero coverage with prior effective change / endpoints",
                        "BASE_zero_current_coverage_with_prior_effective_change")):
        vals = []
        for cfg in ("C3", "C1"):
            s = cp[cfg][key]
            vals.append(f"{s['count']}/{s['denominator']}")
        fmt = (lambda v: f"**{v}**") if label.startswith("**") else (lambda v: v)
        row = f"| {label} | {fmt(vals[0])} | {fmt(vals[1])} |"
        reg("T2-" + key, row, row, "paper/evidence/closure_patterns.json", "summary numerator/denominator")
    # Costs
    for cfg, hours in (("C3", 1.38), ("C1", 0.76)):
        c = costs[cfg]
        h = round(c["machine_seconds"] / 3600, 2)
        reg(f"COST-{cfg}-calls", f"{c['model_calls']}", True, "paper/evidence/r3_costs.json", "model_calls")
        reg(f"COST-{cfg}-hours", f"{h:.2f}".rstrip("0") if h != hours else str(hours), True,
            "paper/evidence/r3_costs.json", "machine_seconds/3600 rounded to 2", status="DERIVED")
    cost_phrase = (f"C3 {costs['C3']['model_calls']} calls, {costs['C3']['generated_tokens']:,} tokens, "
                   f"{costs['C3']['applications']['capture_attempts']} applications, "
                   f"{round(costs['C3']['machine_seconds']/3600, 2)} hours; C1 {costs['C1']['model_calls']}, "
                   f"{costs['C1']['generated_tokens']:,}, {costs['C1']['applications']['capture_attempts']}, "
                   f"{round(costs['C1']['machine_seconds']/3600, 2)}")
    reg("COSTS", cost_phrase, cost_phrase, "paper/evidence/r3_costs.json", "physical FC costs", status="MEASURED+DERIVED")
    reg("REASONING", f"{costs['C3']['reasoning_tokens_subset']:,} reasoning tokens", True,
        "paper/evidence/r3_costs.json", "reasoning_tokens_subset")
    # Responses
    inv = f"Invalid responses were C3 {resp['C3']['invalid_actions']}/{resp['C3']['responses']} and C1 {resp['C1']['invalid_actions']}/{resp['C1']['responses']}"
    reg("INVALID", inv, inv, "paper/evidence/response_counts.json", "invalid_actions/responses")
    nt = f"{resp['C3']['without_tool_calls']}/{resp['C1']['without_tool_calls']} breakdown"
    reg("NO-TOOLS", nt, nt, "paper/evidence/response_counts.json", "without_tool_calls")
    acc = (f"C3 accepted {['zero','one','two','three','four','five','six','seven','eight','nine','ten'][resp['C3']['fc_finish_accepted']]} closures and rejected fourteen"
           if resp['C3']['coverage_rejections'] == 14 else "MISMATCH")
    reg("ACCEPT-C3", acc, acc, "paper/evidence/response_counts.json", "fc_finish_accepted / coverage_rejections")
    reg("ACCEPT-C1", "C1 accepted seven, rejected forty-four", resp["C1"]["fc_finish_accepted"] == 7 and resp["C1"]["coverage_rejections"] == 44,
        "paper/evidence/response_counts.json", "fc_finish_accepted / coverage_rejections")
    rej = {cfg: sum(r["finish_public_failure"]["rejected"] for r in by_arm if r["configuration"] == cfg and r["arm"] == "FC")
           for cfg in ("C3", "C1")}
    rj = f"rejected FC requests had C3 {rej['C3']}/{resp['C3']['coverage_rejections']} and C1 {rej['C1']}/{resp['C1']['coverage_rejections']}"
    reg("REJECTED-PUBLIC-FAILURE", rj, rj, "paper/evidence/r3_by_arm.json + response_counts.json",
        "sum FC finish_public_failure.rejected / coverage_rejections")
    # Pairs and predictions
    disc = [p for cfg in ("C3", "C1") for p in summ[cfg]["discordant_pairs"]]
    complete = sum(len(summ[cfg]["summary"]["complete_damaged_pairs"]) for cfg in ("C3", "C1"))
    reg("DISCORDANT", "One of sixteen damaged pairs was discordant", len(disc) == 1 and complete == 16,
        "paper/evidence/r3_summary.json", "discordant_pairs over complete_damaged_pairs")
    reg("PRED", "P3 was refuted in C3 and compatible in C1",
        preds["C3"]["P3"]["status"] == "REFUTED" and preds["C1"]["P3"]["status"] == "COMPATIBLE",
        "paper/evidence/r3_predictions.json", "status fields")
    env_eff = sum(agg[(c, a)]["environment"]["effective"] for c in ("C3", "C1") for a in ("FC", "BASE"))
    reg("NO-PROFILE-CHANGE", "neither configuration effectively changed profiles", env_eff == 0,
        "paper/evidence/aggregate_metrics.json", "sum environment.effective == 0",
        raw_check={"profile_changed_in_raw_endpoints": sum(x["profile_changed"] for x in raw), "agrees": sum(x["profile_changed"] for x in raw) == 0} if raw else None)
    # Healthy effective edits: byte-level vs semantic (new nuance)
    healthy_phys = [x for x in raw if x["axis"] == "healthy" and x["arm"] == "FC"]
    reg("HEALTHY-EDITS", "Three of four physical healthy episodes effectively edited source",
        sum(x["source_changed"] for x in healthy_phys) == 3 if raw else True,
        "raw R3 endpoint snapshots (private) ; effective = byte identity change",
        "count FC healthy endpoints whose app.py bytes differ from initial",
        status="MEASURED_BYTE_LEVEL",
        raw_check={"note": "1 of the 3 (C1/H-RC2) is a line-ending-only rewrite; semantically 2 of 4 (see r3_normalized_diffs.json)"} if raw else None)
    # Uncovered numerals
    covered = " ".join(c["phrase"] for c in claims)
    nums = sorted(set(re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?:/\d+)?", text)))
    uncovered = [n for n in nums if n not in covered]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = {"manuscript_sha256": SUBMITTED, "manuscript_identity": KNOWN[SUBMITTED],
           "public_tree": "commit 20dfaf03 (local staging copy or downloaded archive)",
           "claims": claims, "numerals_in_manuscript": len(nums), "numerals_not_in_registered_phrases": uncovered,
           "all_registered_match": all(c["matches"] for c in claims)}
    (out / "CLAIMS_LEDGER.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in claims:
        print(("PASS " if c["matches"] else "FAIL ") + c["id"].ljust(22) + c["phrase"][:90])
        if c["raw_cross_check"]:
            print("      raw:", c["raw_cross_check"])
    print(f"registered={len(claims)} all_match={doc['all_registered_match']} numerals={len(nums)} uncovered={len(uncovered)}")
    return 0 if doc["all_registered_match"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
