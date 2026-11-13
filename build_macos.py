"""Build an architecture-specific macOS application on a real macOS host."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from platform_support import APP_VERSION

ROOT = Path(__file__).resolve().parent


def main():
    if sys.platform != 'darwin':
        raise SystemExit('macOS builds must run on macOS. Use the supplied GitHub Actions workflow.')
    arch = platform.machine()
    if arch not in ('arm64', 'x86_64'):
        raise SystemExit(f'Unsupported architecture: {arch}')
    from PIL import Image
    from collect_notices import collect

    staging = ROOT / 'build-macos' / arch
    staging.mkdir(parents=True, exist_ok=True)
    portrait = Image.open(ROOT / 'assets' / 'schwi-portrait.png').convert('RGBA')
    icon = portrait.resize((1024, 1024), Image.Resampling.LANCZOS)
    icon.save(staging / 'SchwiPet.icns')
    collect(staging)
    info = {
        'CFBundleDisplayName': '休比桌宠', 'CFBundleName': '休比桌宠',
        'CFBundleShortVersionString': APP_VERSION, 'CFBundleVersion': APP_VERSION,
        'LSUIElement': True, 'LSMinimumSystemVersion': '14.4',
        'LSApplicationCategoryType': 'public.app-category.entertainment',
        'NSHighResolutionCapable': True,
    }
    # Include notices before signing: modifying Resources afterwards invalidates it.
    spec = f'''a = Analysis([{str(ROOT / 'main.py')!r}], pathex=[{str(ROOT)!r}],
    binaries=[], datas=[({str(ROOT / 'assets')!r}, 'assets'),
    ({str(staging / 'licenses')!r}, 'licenses')],
    hiddenimports=[], hookspath=[], hooksconfig={{}}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SchwiPet',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, argv_emulation=False, target_arch={arch!r}, codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SchwiPet')
app = BUNDLE(coll, name='SchwiPet.app', icon={str(staging / 'SchwiPet.icns')!r},
    bundle_identifier='local.schwi.desktop-pet', info_plist={info!r})
'''
    spec_path = staging / 'SchwiPet-macOS.spec'
    spec_path.write_text(spec, encoding='utf-8')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm',
                    '--distpath', str(ROOT / 'dist-macos'),
                    '--workpath', str(staging / 'pyinstaller'), str(spec_path)], env=env, check=True)
    app = ROOT / 'dist-macos' / 'SchwiPet.app'
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    report = {'version': APP_VERSION, 'arch': arch, 'macos': platform.mac_ver()[0],
              'python': platform.python_version(), 'signed': 'ad-hoc', 'notarized': False,
              'minimum_macos': '14.4', 'app': str(app)}
    (ROOT / 'dist-macos' / 'build-info.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Built and verified {app} ({arch})')


if __name__ == '__main__':
    main()
