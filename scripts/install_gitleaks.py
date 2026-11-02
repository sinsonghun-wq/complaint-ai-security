"""Install a fixed official Gitleaks release after checking its pinned SHA-256."""
from pathlib import Path
import hashlib,platform,sys,tarfile,tempfile,urllib.request,zipfile

VERSION='8.30.1'
ASSETS={
    'Linux':('linux_x64.tar.gz','551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb'),
    'Windows':('windows_x64.zip','d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e'),
}
def main():
    kind=platform.system()
    if kind not in ASSETS or platform.machine().lower() not in ('amd64','x86_64'):
        raise SystemExit('This pinned installer supports Linux/Windows x64.')
    suffix,expected=ASSETS[kind]
    destination=Path(sys.argv[1] if len(sys.argv)>1 else tempfile.gettempdir())
    destination.mkdir(parents=True,exist_ok=True)
    archive=destination/('gitleaks_'+VERSION+'_'+suffix)
    url='https://github.com/gitleaks/gitleaks/releases/download/v'+VERSION+'/'+archive.name
    with urllib.request.urlopen(url,timeout=60) as response:  # nosec B310  # Fixed official HTTPS origin, version and SHA-256 below.
        data=response.read()
    if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('Gitleaks checksum mismatch')
    archive.write_bytes(data)
    name='gitleaks.exe' if kind=='Windows' else 'gitleaks'
    if kind=='Windows':
        with zipfile.ZipFile(archive) as z:payload=z.read(name)
    else:
        with tarfile.open(archive) as tar:
            member=tar.extractfile(name)
            if member is None:raise RuntimeError('Gitleaks binary missing')
            payload=member.read()
    target=destination/name;target.write_bytes(payload);target.chmod(0o755)
    print(target)
if __name__=='__main__':main()
