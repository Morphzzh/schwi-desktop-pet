"""Archive an already-tested .app, preserving symlinks and executable modes."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from platform_support import APP_VERSION

if sys.platform != 'darwin':
    raise SystemExit('Run this packaging script on macOS.')
root = Path(__file__).resolve().parent
arch = platform.machine()
dist = root / 'dist-macos'
app = dist / 'SchwiPet.app'
subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)], check=True)
stage = dist / f'SchwiPet-macOS-{arch}'
stage.mkdir(exist_ok=True)
target = stage / 'SchwiPet.app'
if target.exists():
    raise SystemExit(f'Package staging path already exists: {target}')
subprocess.run(['/usr/bin/ditto', str(app), str(target)], check=True)
shutil.copy2(root / 'README-macOS.md', stage / '使用说明.md')
shutil.copy2(dist / 'build-info.json', stage / 'build-info.json')
archive = dist / f'SchwiPet-{APP_VERSION}-macOS-{arch}.zip'
subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                str(stage), str(archive)], check=True)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(archive.with_suffix('.sha256')).write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
print(archive)
