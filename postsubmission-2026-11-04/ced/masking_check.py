"""Post-hoc counterfactual-environment scoring of retained source states.

Runs ONLY inside the trusted Debian guest, through the unchanged rc3 oracle,
dispatcher and Bubblewrap launcher (imported read-only from the extracted
package). Each plan row is one fresh endpoint: exact candidate bytes + one
allowed profile, scored by grade_case. No model, no FC/BASE episode, no retry,
no fallback. Raw captures are retained; scoring precedes any cleanup (none).

Usage (guest):  /usr/bin/python3 -I -S masking_check.py PACKAGE_ROOT PLAN_DIR OUTPUT WHEELHOUSE
"""
import hashlib
import json
import os
import platform
import shutil
import socket
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(package_root, plan_dir, output, wheelhouse):
    root = Path(package_root).resolve()
    plan_dir = Path(plan_dir).resolve()
    output = Path(output).resolve()
    if output == root or output.is_relative_to(root) or root.is_relative_to(output):
        raise RuntimeError("OUTPUT_MUST_BE_OUTSIDE_PACKAGE")
    sys.path[:0] = [str(root), str(root / "source"), str(root / "cases-package/frozen_runtime"),
                    str(root / "cases-package")]
    import validate_fixture as vf
    vf.entry_gate()  # Debian, /usr/bin/python3 -I -S, unprivileged, bwrap present
    plan = json.loads((plan_dir / "plan.json").read_bytes())
    for c in plan["candidates"]:
        if digest(plan_dir / c["file"]) != c["sha256"]:
            raise RuntimeError("CANDIDATE_BYTES:" + c["file"])
    output.mkdir(parents=True, exist_ok=False)
    vf.save(output / "plan.json", plan)
    import reproduce
    from interface import Dispatcher, worker
    from scoring import grade_case
    offline, judge, oracle = reproduce.offline, reproduce.judge, reproduce.oracle
    manifest = reproduce.verify()
    if manifest != plan["rc3_package_manifest_sha256"]:
        raise RuntimeError("PACKAGE_IDENTITY")
    components_before = vf.component_hashes(root)
    vf.save(output / "environment.json", {
        "python_version": platform.python_version(),
        "python_sha256": digest(Path(sys.executable).resolve()),
        "debian_version": Path("/etc/debian_version").read_text().strip(),
        "kernel": platform.release(), "uid": os.getuid(),
        "bubblewrap_sha256": digest(Path(shutil.which("bwrap"))),
        "package_manifest_sha256": manifest, "plan_sha256": digest(plan_dir / "plan.json")})
    reproduce.prepare_runtime(output, Path(wheelhouse))
    limits = plan["limits"]
    cost = dict.fromkeys(limits, 0)
    started = time.monotonic()
    original_capture, original_install = judge.capture, offline.apply_profile
    ledger = []

    def captured(argv, *a, **k):
        if not (Path(argv[0]).resolve() == Path(shutil.which("bwrap")).resolve()
                and "--unshare-all" in argv and "--cap-drop" in argv):
            raise RuntimeError("SANDBOX_ONLY_NO_FALLBACK")
        kind = "workers" if "/file_worker.py" in argv else "probes" if "/probe.py" in argv else "applications"
        if cost[kind] >= limits[kind] or time.monotonic() - started > limits["machine_seconds"]:
            raise RuntimeError("CAPTURE_BUDGET_EXHAUSTED")
        cost[kind] += 1
        item = {"index": len(ledger) + 1, "kind": kind, "returned": False}
        ledger.append(item)
        try:
            result = original_capture(argv, *a, **k)
            item.update(returned=True, error=result.get("error"), exit_code=result.get("exit_code"))
            if result.get("error") is not None or result.get("utf8_valid") is not True:
                raise RuntimeError("INCOMPLETE_CAPTURE:" + kind)
            if result.get("stderr", "").startswith("bwrap:"):
                raise RuntimeError("BUBBLEWRAP_LAUNCH_ERROR")
            return result
        finally:
            vf.save(output / "capture_ledger.json", ledger)
            vf.save(output / "costs.json", cost)

    def installed(*a, **k):
        if cost["offline_installs"] >= limits["offline_installs"]:
            raise RuntimeError("INSTALL_BUDGET_EXHAUSTED")
        cost["offline_installs"] += 1
        return original_install(*a, **k)

    judge.capture, offline.apply_profile = captured, installed
    cases, _, _ = vf.read_catalog(root)
    results = []
    try:
        for row in plan["rows"]:
            out = output / "rows" / row["id"].replace("/", "__").replace("@", "__").replace("#", "__r")
            out.mkdir(parents=True, exist_ok=False)
            cost["fresh_states"] += 1
            if cost["fresh_states"] > limits["fresh_states"]:
                raise RuntimeError("STATE_BUDGET_EXHAUSTED")
            source = plan_dir / row["source"]
            state = out / "state"
            snapshot = offline.prepare(state, source, row["profile"])
            if snapshot["source_files"] != {"app.py": row["sha256"]}:
                raise RuntimeError("PREPARED_SOURCE_BYTES:" + row["id"])
            paths = {n: out / n for n in ("home", "tmp", "cache")}
            for p in paths.values():
                p.mkdir()
            records = []
            gate = judge.native_preflight(snapshot)
            vf.save(out / "isolation.json", gate)
            if gate.get("available") is not True:
                raise RuntimeError("NATIVE_ISOLATION_BLOCKED")
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen()
                props = worker(snapshot, paths, judge, "native_properties", {
                    "parent_pid": os.getpid(), "pid_namespace": os.readlink("/proc/self/ns/pid"),
                    "net_namespace": os.readlink("/proc/self/ns/net"),
                    "listener_port": listener.getsockname()[1],
                    "private_paths": [str(root), str(plan_dir), str(out / "isolation.json")]}, records)
            vf.save(out / "writable_properties.json", props)
            if not (props.get("ok") is True and props.get("checks") and all(props["checks"].values())):
                raise RuntimeError("WRITABLE_ISOLATION_BLOCKED")
            gate["writable_properties_passed"] = True
            d = Dispatcher(state, paths, offline, judge, gate, records, row["case_id"])
            score = grade_case(d, cases[row["case_id"]], offline.policy(), oracle, out / "score.json")
            if score["before"] != snapshot or score["after"] != snapshot:
                raise RuntimeError("ENDPOINT_STATE_CHANGED:" + row["id"])
            ops = {op: {"exit_code": v.get("exit_code"),
                        "stdout_sha256": hashlib.sha256(v.get("stdout", "").encode()).hexdigest(),
                        "stderr_sha256": hashlib.sha256(v.get("stderr", "").encode()).hexdigest()}
                   for op, v in score["operations"].items()}
            res = {"id": row["id"], "status": score["status"], "checks": score["checks"],
                   "operations": ops, "score_sha256": digest(out / "score.json"),
                   "scored_before_cleanup": score["scored_before_cleanup"]}
            results.append(res)
            vf.save(output / "results.json", results)
            print(json.dumps({"id": row["id"], "status": score["status"]}), flush=True)
        if vf.component_hashes(root) != components_before or reproduce.verify() != manifest:
            raise RuntimeError("PACKAGE_CHANGED_DURING_RUN")
        cost["machine_seconds"] = time.monotonic() - started
        vf.save(output / "costs.json", cost)
        vf.save(output / "closure.json", {"status": "COMPLETED", "rows": len(results),
                "model_calls": 0, "automatic_retries": 0, "cleanup_performed": False,
                "kind": plan["kind"], "package_manifest_sha256": manifest})
    except BaseException as exc:
        cost["machine_seconds"] = time.monotonic() - started
        vf.save(output / "costs.json", cost)
        vf.save(output / "failure.json", {"error": str(exc), "traceback": traceback.format_exc(),
                "completed": len(results), "no_retry": True, "cleanup_performed": False})
        raise


if __name__ == "__main__":
    main(*sys.argv[1:5])
