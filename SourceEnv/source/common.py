"""Trusted file utilities; candidate code is never imported."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def require(value, message):
    if not value:
        raise RuntimeError(message)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':'))

def sha(value):
    return hashlib.sha256(value).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_bytes())

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)

def verify_package(package):
    package = Path(package).resolve()
    frozen = read_json(ROOT / 'frozen_inputs.json')
    require(sha((package / 'manifest.json').read_bytes()) == frozen['package_manifest_sha256'], 'PACKAGE_MANIFEST_CHANGED')
    declared = set()
    for row in frozen['files']:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts and row['path'] not in declared, 'MANIFEST_PATH')
        path = package / relative
        require(not path.is_symlink() and path.is_file() and path.stat().st_size == row['bytes']
                and sha(path.read_bytes()) == row['sha256'], 'PACKAGE_FILE_CHANGED:' + row['path'])
        declared.add(relative.as_posix())
    actual = {p.relative_to(package).as_posix() for p in package.rglob('*')
              if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts}
    require(actual == declared, 'PACKAGE_INVENTORY_CHANGED')
    contract = read_json(package / 'contract.json')
    require(contract['authorized_new_model_episodes'] == 0 and contract['agent_gate'] == 'BLOCKED', 'FROZEN_GATE_CHANGED')
    return contract

def verify_release():
    release = read_json(ROOT / 'release.json')
    for row in release['files']:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'RELEASE_PATH')
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == row['sha256']
                and path.stat().st_size == row['bytes'], 'CONTROLLER_CHANGED:' + row['path'])
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.name != 'release.json'}
    require(actual == {row['path'] for row in release['files']}, 'CONTROLLER_INVENTORY_CHANGED')
    from variant_metadata import verify_all_diff_metadata
    verify_all_diff_metadata()
    return sha((ROOT / 'release.json').read_bytes())

def exact_messages(case_id):
    require(case_id in read_json(ROOT / 'prompt_hashes.json'), 'CASE_REJECTED')
    messages = read_json(ROOT / 'prompts' / (case_id + '.messages.json'))
    require(sha(canonical(messages).encode()) == read_json(ROOT / 'prompt_hashes.json')[case_id], 'PROMPT_CHANGED')
    return messages
