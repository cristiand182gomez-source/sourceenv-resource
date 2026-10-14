"""Fetch only the ten pinned wheels from PyPI, with mandatory SHA256 checks."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import argparse, hashlib, json, os, urllib.parse, urllib.request, uuid
ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition: raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024): h.update(chunk)
    return h.hexdigest()


class PyPIRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(urllib.parse.urlsplit(newurl).hostname in {'pypi.org', 'files.pythonhosted.org'} and
                urllib.parse.urlsplit(newurl).scheme == 'https', 'UNEXPECTED_DOWNLOAD_REDIRECT')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(directory, opener=None):
    directory = Path(directory).resolve()
    require(not directory.is_relative_to(ROOT) and not ROOT.is_relative_to(directory), 'WHEELHOUSE_MUST_BE_OUTSIDE_PACKAGE')
    directory.mkdir(parents=True, exist_ok=True)
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), PyPIRedirect())
    hashes = json.loads((ROOT / 'cases-package/frozen_runtime/wheel_sha256.json').read_bytes())
    require(len(hashes) == 10, 'EXPECTED_TEN_WHEELS')
    receipts = []
    for name, expected in sorted(hashes.items()):
        require(Path(name).name == name and name.endswith('.whl'), 'WHEEL_FILENAME')
        destination = directory / name
        if destination.exists() or destination.is_symlink():
            require(destination.is_file() and not destination.is_symlink() and sha(destination) == expected, 'CACHED_WHEEL_SHA256_MISMATCH:' + name)
            receipts.append({'file': name, 'sha256': expected, 'bytes': destination.stat().st_size, 'downloaded': False})
            continue
        distribution, version = name.split('-')[:2]
        url = 'https://pypi.org/pypi/' + urllib.parse.quote(distribution) + '/' + urllib.parse.quote(version) + '/json'
        with opener.open(url, timeout=60) as response:
            data = response.read(2 * 1024 * 1024 + 1)
        require(len(data) <= 2 * 1024 * 1024, 'PYPI_METADATA_TOO_LARGE')
        metadata = json.loads(data)
        matches = [row for row in metadata['urls'] if row['filename'] == name]
        require(len(matches) == 1 and matches[0]['digests']['sha256'] == expected, 'PYPI_METADATA_SHA256_MISMATCH:' + name)
        row = matches[0]; download_url = row['url']; parsed = urllib.parse.urlsplit(download_url)
        require(parsed.scheme == 'https' and parsed.hostname == 'files.pythonhosted.org', 'UNEXPECTED_WHEEL_ORIGIN')
        require(type(row['size']) is int and 0 < row['size'] <= 32 * 1024 * 1024, 'WHEEL_SIZE')
        temporary = directory / ('.' + name + '.' + str(uuid.uuid4()) + '.part')
        try:
            h = hashlib.sha256(); size = 0
            with opener.open(download_url, timeout=60) as response, temporary.open('xb') as f:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    require(size <= row['size'], 'WHEEL_SIZE_EXCEEDED:' + name)
                    h.update(chunk); f.write(chunk)
            require(size == row['size'] and h.hexdigest() == expected, 'DOWNLOADED_WHEEL_SHA256_MISMATCH:' + name)
            require(not destination.exists(), 'WHEEL_DESTINATION_CHANGED')
            os.replace(temporary, destination)
            receipts.append({'file': name, 'sha256': expected, 'bytes': size, 'downloaded': True, 'source': download_url})
        finally:
            if temporary.exists(): temporary.unlink()
    return {'source': 'PyPI', 'wheels_verified': len(receipts), 'automatic_retries': 0, 'files': receipts}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('directory', type=Path); args = p.parse_args()
    receipt = fetch(args.directory)
    (args.directory / 'fetch_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'wheels_verified': receipt['wheels_verified'], 'downloaded': sum(r['downloaded'] for r in receipt['files'])}))


if __name__ == '__main__': main()
