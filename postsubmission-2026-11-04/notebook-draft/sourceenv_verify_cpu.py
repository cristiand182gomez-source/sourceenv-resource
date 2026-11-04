# %% [markdown]
# # SourceEnv: CPU verification of the paper's numbers (draft, NOT published)
#
# Standard library only; no model, no GPU, no sandboxed application run.
# 1. Fetch the audited public tree (commit 20dfaf03) and the rc3 release ZIP;
#    check the ZIP's SHA-256.
# 2. Run the executable claims ledger: every registered manuscript phrase is
#    recomputed from `paper/evidence/*.json`. Exit status reported as PASS/FAIL.
#
# Scripted controls (reproduce.py, validate_fixture.py) need Debian + Bubblewrap
# and are NOT run here; see SourceEnv/CLEAN_MACHINE.md.

# %%
import hashlib, io, json, subprocess, sys, tarfile, urllib.request, zipfile
from pathlib import Path

COMMIT = "20dfaf03122d62888d8550f558dcc25e5f66f002"
REPO = "cristiand182gomez-source/sourceenv-resource"
ZIP_URL = f"https://github.com/{REPO}/releases/download/v1.0.0-rc3/SourceEnv-1.0.0-rc3.zip"
ZIP_SHA = "7a59f1c3cf01e49cbf98356d14de65bf83a7cfb492f0504c9badbe1c57704e28"
WORK = Path("sourceenv_verify")
LOCAL_TREE = None   # set to a local checkout path to run offline
LOCAL_ZIP = None    # set to a local copy of the release ZIP to run offline
LEDGER = Path("claims_ledger.py")  # shipped next to this notebook

# %%
WORK.mkdir(exist_ok=True)
if LOCAL_TREE is None:
    raw = urllib.request.urlopen(f"https://codeload.github.com/{REPO}/tar.gz/{COMMIT}", timeout=60).read()
    with tarfile.open(fileobj=io.BytesIO(raw)) as t:
        t.extractall(WORK, filter="data")
    tree = next(WORK.glob("sourceenv-resource-*"))
else:
    tree = Path(LOCAL_TREE)
zbytes = Path(LOCAL_ZIP).read_bytes() if LOCAL_ZIP else urllib.request.urlopen(ZIP_URL, timeout=60).read()
zsha = hashlib.sha256(zbytes).hexdigest()
print("rc3 ZIP sha256:", zsha, "MATCH" if zsha == ZIP_SHA else "MISMATCH")
with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
    print("ZIP CRC:", "PASS" if z.testzip() is None else "FAIL", "| members:", len(z.namelist()))

# %%
out = WORK / "claims"
r = subprocess.run([sys.executable, "-I", str(LEDGER), str(tree / "paper/DRAFT.md"), str(tree), "-", str(out)],
                   capture_output=True, text=True)
print(r.stdout[-4000:], r.stderr[-2000:])
print("REPRODUCE:", "PASS" if (r.returncode == 0 and zsha == ZIP_SHA) else "FAIL")
