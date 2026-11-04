"""Guest-side driver: execute the PUBLIC rc3 ZIP's no-model checks once.

Run as the ordinary account with /usr/bin/python3 -I -S from BASE (this file's
parent's parent). Every step is attempted once, recorded with argv, timing and
exit code; stdout/stderr retained. Outputs stay outside the extracted package.
"""
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EVID = BASE / "evidence"
EVID.mkdir(exist_ok=True)
STEPS = EVID / "steps.json"
PY = "/usr/bin/python3"
ZIP_URL = "https://github.com/cristiand182gomez-source/sourceenv-resource/releases/download/v1.0.0-rc3/SourceEnv-1.0.0-rc3.zip"
ZIP_SHA = "7a59f1c3cf01e49cbf98356d14de65bf83a7cfb492f0504c9badbe1c57704e28"
FIX = ["EH-API", "SC-BALANCE", "EC-MISSING", "SH-FLAG", "EH-RENDERER", "SC-SORT", "EC-SYMBOL", "SH-FORMAT"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def save(p, v):
    Path(p).write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def step(name, argv, cwd, timeout=7200, must_pass=True):
    hist = json.loads(STEPS.read_bytes()) if STEPS.exists() else []
    if any(s["name"] == name for s in hist):
        raise RuntimeError("STEP_ALREADY_ATTEMPTED:" + name)
    rec = {"name": name, "argv": argv, "cwd": str(cwd), "status": "STARTED",
           "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    hist.append(rec)
    save(STEPS, hist)
    t = time.monotonic()
    with open(EVID / (name + ".stdout"), "wb") as o, open(EVID / (name + ".stderr"), "wb") as e:
        try:
            r = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=o, stderr=e, timeout=timeout)
            rec.update(returncode=r.returncode, status="PASS" if r.returncode == 0 else "FAIL")
        except Exception as exc:  # retained, never retried
            rec.update(status="FAIL", error=repr(exc))
    rec["elapsed_seconds"] = time.monotonic() - t
    save(STEPS, hist)
    print(json.dumps({k: rec.get(k) for k in ("name", "status", "returncode", "elapsed_seconds")}), flush=True)
    if must_pass and rec["status"] != "PASS":
        raise RuntimeError("STEP_FAILED:" + name)
    return rec


def main(phase):
    if os.getuid() == 0 or not sys.flags.isolated or not sys.flags.no_site:
        raise RuntimeError("ORDINARY_ISOLATED_PYTHON_REQUIRED")
    pkg = BASE / "rc3" / "SourceEnv"
    if phase == "fetch":
        save(EVID / "system-identity.json", {
            "uid": os.getuid(), "python": sys.version, "kernel": platform.release(),
            "debian_version": Path("/etc/debian_version").read_text().strip(),
            "origin_marker": Path("/etc/sourceenv-clean-origin").read_text(),
            "bwrap_sha256": sha("/usr/bin/bwrap"), "python_sha256": sha(PY),
            "new_installation": False,
            "note": "qcow2 overlay of the 2026-10-13 fresh-install disk (used for the rc2 clean check)"})
        step("download-public-rc3", ["curl", "-fsSL", "--retry", "0", "-o", str(BASE / "SourceEnv-1.0.0-rc3.zip"), ZIP_URL], BASE, 600)
        got = sha(BASE / "SourceEnv-1.0.0-rc3.zip")
        save(EVID / "zip-identity.json", {"url": ZIP_URL, "sha256": got, "expected": ZIP_SHA, "match": got == ZIP_SHA})
        if got != ZIP_SHA:
            raise RuntimeError("PUBLIC_ZIP_IDENTITY")
        with zipfile.ZipFile(BASE / "SourceEnv-1.0.0-rc3.zip") as z:
            bad = z.testzip()
            if bad:
                raise RuntimeError("ZIP_CRC:" + bad)
            z.extractall(BASE / "rc3")
        return
    if phase == "controls":
        step("verify-before", [PY, "-I", "-S", "reproduce.py", "--verify-only"], pkg)
        for t in ("test_portable", "test_validate_fixture", "test_context", "test_costs"):
            step("tests-" + t, [PY, "-I", "-S", "tests/%s.py" % t], pkg, 1800, must_pass=False)
        step("fetch-wheels", [PY, "-I", "-S", "fetch_wheels.py", "../../wheels"], pkg, 1800)
        step("reproduce-16", [PY, "-I", "-S", "reproduce.py", "--wheelhouse", "../../wheels",
                              "--output", "../../out-reproduce"], pkg, must_pass=False)
        step("validator-plan", [PY, "-I", "-S", "validate_fixture.py", "--write-plan", "../../validator-plan.json",
                                "--selection", "new-coverage"], pkg)
        step("validator-24", [PY, "-I", "-S", "validate_fixture.py", "--execute-plan", "../../validator-plan.json",
                              "--output", "../../out-validator", "--wheelhouse", "../../wheels"], pkg, must_pass=False)
        for c in ("reference", "noop"):
            step("runner-" + c, [PY, "-I", "-S", "run_agent.py", "--backend", "scripted", "--control", c,
                                 "--fixtures", *FIX, "--wheelhouse", "../../wheels", "--output", "../../out-runner-" + c],
                 pkg, must_pass=False)
            step("analyze-" + c, [PY, "-I", "-S", "analyze.py", "../../out-runner-" + c, "--output",
                                  "../../analysis-" + c + ".json"], pkg, must_pass=False)
        step("verify-after-controls", [PY, "-I", "-S", "reproduce.py", "--verify-only"], pkg)
        return
    if phase == "ced":
        step("ced-61", [PY, "-I", "-S", str(BASE / "admin/masking_check.py"), str(pkg), str(BASE / "masking_plan"),
                        str(BASE / "out-ced"), str(BASE / "wheels")], BASE, 5400, must_pass=False)
        step("verify-after-ced", [PY, "-I", "-S", "reproduce.py", "--verify-only"], pkg)
        return
    raise RuntimeError("UNKNOWN_PHASE")


if __name__ == "__main__":
    main(sys.argv[1])
