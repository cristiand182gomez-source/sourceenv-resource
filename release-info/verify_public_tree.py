"""Verify a publication tree offline, without importing SourceEnv or running tests."""
from pathlib import Path
import argparse, hashlib, json, zipfile

def sha(data): return hashlib.sha256(data).hexdigest()

def verify(root, archive=None, require_no_git=False):
    root=Path(root).resolve()
    if require_no_git and (root/'.git').exists():
        raise ValueError('Preparation must not contain .git')
    package=root/'SourceEnv'
    if (package/'.git').exists(): raise ValueError('.git must never be inside SourceEnv')
    manifest_path=package/'PACKAGE_MANIFEST.json'
    expected_manifest='a6e4d165738b27cb05ec102ca5c1f695a226c044f14b91fc9431a0e28fa7230d'
    if sha(manifest_path.read_bytes())!=expected_manifest:raise ValueError('Resource manifest identity')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    entries=manifest['files']
    expected={x['path'] for x in entries}|{'PACKAGE_MANIFEST.json','PACKAGE_MANIFEST.sha256'}
    actual={p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    if actual!=expected or len(actual)!=158:raise ValueError('Resource inventory differs: '+str(sorted(actual^expected)))
    if any(p.is_symlink() for p in package.rglob('*')):raise ValueError('Resource symlink not approved')
    for item in entries:
        p=package/item['path'];data=p.read_bytes()
        if len(data)!=item['bytes'] or sha(data)!=item['sha256']:raise ValueError('Resource bytes differ: '+item['path'])
    if (package/'PACKAGE_MANIFEST.sha256').read_text().split()[0]!=expected_manifest:raise ValueError('Resource checksum sidecar')
    paper_manifest_path=root/'release-info/PAPER_MANIFEST.json'
    pm=json.loads(paper_manifest_path.read_text(encoding='utf-8'))
    if (root/'release-info/PAPER_MANIFEST.sha256').read_text().split()[0]!=sha(paper_manifest_path.read_bytes()):raise ValueError('Paper manifest checksum')
    approved=set()
    for item in pm['files']:
        name=item['path'];p=(root/name).resolve()
        if not p.is_relative_to(root) or name in approved:raise ValueError('Unsafe or duplicate paper member')
        approved.add(name)
        data=p.read_bytes()
        if len(data)!=item['bytes'] or sha(data)!=item['sha256']:raise ValueError('Paper bytes differ: '+name)
    approved|={'release-info/PAPER_MANIFEST.json','release-info/PAPER_MANIFEST.sha256'}
    # Git metadata is permitted only at the repository parent after publication.
    current={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
             and '.git' not in p.relative_to(root).parts and p.relative_to(root).parts[0]!='SourceEnv'}
    if current!=approved:raise ValueError('Editorial inventory differs: '+str(sorted(current^approved)))
    if (root/'.gitattributes').read_bytes()!=b'/SourceEnv/** -text\n':raise ValueError('Byte-preservation Git rule differs')
    crc=None
    if archive:
        data=Path(archive).read_bytes()
        if sha(data)!='7a59f1c3cf01e49cbf98356d14de65bf83a7cfb492f0504c9badbe1c57704e28':raise ValueError('Canonical ZIP identity')
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:raise ValueError('Canonical ZIP CRC')
            if set(z.namelist())!={'SourceEnv/'+n for n in expected}:raise ValueError('Canonical ZIP inventory')
            for n in z.namelist():
                if z.read(n)!=(root/n).read_bytes():raise ValueError('ZIP/tree bytes differ: '+n)
        crc='PASS'
    return {'status':'PASS_DOCUMENTARY_LOCAL','resource_version':'1.0.0-rc3','resource_files':158,
            'paper_and_selected_support_files':len(approved),'canonical_archive_crc':crc,
            'resource_core_imported':False,'model_calls':0,'applications':0,'network_requests':0,
            'public_HTTP_verified':False}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path,nargs='?',default=Path(__file__).resolve().parents[1])
    ap.add_argument('--resource-zip',type=Path)
    ap.add_argument('--require-no-git',action='store_true')
    args=ap.parse_args()
    print(json.dumps(verify(args.root,args.resource_zip,args.require_no_git),indent=2))
