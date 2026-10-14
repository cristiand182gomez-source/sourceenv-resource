"""Bounded offline release installation, without importing candidate packages."""

import argparse
import base64
from email.parser import BytesParser
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import sys
import venv
import zipfile

ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def trusted_entry():
    require(sys.flags.isolated and sys.flags.no_site,
            "Use /usr/bin/python3 -I -S from the trusted evaluator, not candidate Python")
    require(Path(sys.executable).resolve() == Path('/usr/bin/python3').resolve(),
            "This profile requires trusted /usr/bin/python3")


def policy():
    return json.loads((ROOT / 'policy.json').read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def payload(profile_name):
    p = policy()
    require(profile_name in p['profiles'], 'Release combination is not permitted')
    profile = p['profiles'][profile_name]
    names = [*[w for w in p['common_wheels'] if w not in profile.get('excluded_wheels', [])], f"click-{profile['click']}-py3-none-any.whl"]
    if profile['typer'] is not None:
        names.append(f"typer-{profile['typer']}-py3-none-any.whl")
    manifest = json.loads((ROOT / 'wheel_sha256.json').read_text())
    files, versions = {}, {}
    for name in names:
        wheel = ROOT / 'wheelhouse' / name
        require(wheel.is_file() and not wheel.is_symlink(), 'Missing regular wheel: ' + name)
        require(sha256(wheel.read_bytes()).hexdigest() == manifest[name], 'Wheel digest mismatch: ' + name)
        with zipfile.ZipFile(wheel) as bundle:
            for member in bundle.infolist():
                relative = PurePosixPath(member.filename)
                require(not relative.is_absolute() and '..' not in relative.parts
                        and not any(part.endswith('.data') for part in relative.parts)
                        and (member.external_attr >> 16) & 0o170000 != 0o120000,
                        'Unsupported wheel path or layout')
                if member.is_dir():
                    continue
                require(member.filename not in files, 'Overlapping wheel member')
                data = bundle.read(member)
                files[member.filename] = data
                if member.filename.endswith('.dist-info/METADATA'):
                    metadata = BytesParser().parsebytes(data)
                    versions[metadata['Name'].lower().replace('_', '-')] = metadata['Version']
    return files, versions


def tree_digest(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(), 'Workspace contains a symlink: ' + str(path))
        if path.is_file():
            result[str(path.relative_to(directory))] = sha256(path.read_bytes()).hexdigest()
    return result


def apply_profile(state, profile_name):
    """Explicit repair operation: install, verify, then switch active environment.

    The controller owns state/active.json and environments/. Only workspace/
    and the selected environment are mounted for the application. No source
    file is reset or changed here. Integration must bind state to the episode;
    an agent does not choose an arbitrary host path.
    """
    trusted_entry()
    state = Path(state).resolve()
    require((state / 'workspace' / 'app.py').is_file(), 'State must already have an application')
    before = tree_digest(state / 'workspace')
    files, versions = payload(profile_name)
    folder = state / 'environments' / ('env-' + secrets.token_hex(8))
    folder.parent.mkdir(parents=True, exist_ok=True)
    venv.EnvBuilder(with_pip=False, system_site_packages=False, symlinks=True).create(folder)
    site = folder / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    site.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        destination = site / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    hashes = {name: sha256(data).hexdigest() for name, data in files.items()}
    require(tree_digest(site) == hashes, 'Installed wheel payload mismatch')
    require(tree_digest(state / 'workspace') == before, 'Installation changed application source')
    record = {'profile': profile_name, 'directory': folder.name,
              'site_relative': str(site.relative_to(folder)), 'versions': versions,
              'pyvenv_cfg_sha256': sha256((folder / 'pyvenv.cfg').read_bytes()).hexdigest(),
              'payload_sha256': sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
              'source_unchanged': True}
    # Retain earlier environments; changing versions is never an implicit cleanup.
    write_json(state / 'active.json', record)
    return inspect_state(state)


def inspect_state(state):
    trusted_entry()
    state = Path(state).resolve()
    selected = json.loads((state / 'active.json').read_text())
    require(selected['profile'] in policy()['profiles'], 'Active profile is outside the catalogue')
    require(selected['directory'].startswith('env-') and '/' not in selected['directory']
            and '..' not in selected['directory'], 'Invalid managed environment path')
    environment = state / 'environments' / selected['directory']
    require(environment.is_dir() and not environment.is_symlink(), 'Environment is not a regular directory')
    site = environment / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    require(site.resolve().is_relative_to(environment) and not site.is_symlink()
            and not (environment / 'lib').is_symlink(), 'Managed package directory escaped environment')
    files, versions = payload(selected['profile'])
    hashes = {name: sha256(data).hexdigest() for name, data in files.items()}
    require(tree_digest(site) == hashes, 'Environment differs from hash-verified releases')
    config = (environment / 'pyvenv.cfg').read_text()
    require(sha256((environment / 'pyvenv.cfg').read_bytes()).hexdigest() == selected['pyvenv_cfg_sha256'],
            'Environment startup configuration changed')
    require('include-system-site-packages = false' in config, 'System packages are enabled')
    require((environment / 'bin' / 'python').resolve() == Path('/usr/bin/python3').resolve(),
            'Candidate environment changed the base interpreter')
    return {'profile': selected['profile'], 'versions': versions,
            'environment': str(environment), 'site': str(site),
            'workspace': str(state / 'workspace'), 'source_files': tree_digest(state / 'workspace'),
            'source_snapshot_base64': {str(path.relative_to(state / 'workspace')):
                                      base64.b64encode(path.read_bytes()).decode('ascii')
                                      for path in sorted((state / 'workspace').rglob('*')) if path.is_file()},
            'environment_configuration': config,
            'trusted_base_interpreter_sha256': sha256(Path('/usr/bin/python3').resolve().read_bytes()).hexdigest(),
            'installed_payload_sha256': sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
            'source_unchanged_by_install': selected.get('source_unchanged', False)}


def prepare(state, source, profile_name='typer0153_click820'):
    trusted_entry()
    state = Path(state)
    require(not state.exists(), 'Refuse to overwrite an existing state')
    (state / 'workspace').mkdir(parents=True)
    (state / 'workspace' / 'app.py').write_bytes(Path(source).read_bytes())
    return apply_profile(state, profile_name)


def main():
    trusted_entry()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--profile', required=True, choices=policy()['profiles'])
    args = parser.parse_args()
    print(json.dumps(apply_profile(args.state, args.profile), sort_keys=True))


if __name__ == '__main__':
    main()
