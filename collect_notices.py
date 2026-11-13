"""Copy dependency notices from the exact build environment into the app folder."""
import importlib.metadata
from pathlib import Path
import shutil
import sys

def collect(destination):
    dest = Path(destination) / 'licenses'
    dest.mkdir(parents=True, exist_ok=True)
    bundled = Path(__file__).resolve().parent / 'third_party_licenses'
    if bundled.exists():
        shutil.copytree(bundled, dest, dirs_exist_ok=True)
    for package in ('PySide6-Essentials', 'shiboken6', 'PyInstaller'):
        dist = importlib.metadata.distribution(package)
        (dest / package).mkdir(parents=True, exist_ok=True)
        (dest / package / 'PACKAGE-METADATA.txt').write_text(dist.read_text('METADATA') or '', encoding='utf-8')
        for file in dist.files or ():
            name = str(file).replace('\\', '/')
            if '/licenses/' in name or ('.dist-info/' in name and ('license' in file.name.lower() or 'copying' in file.name.lower())):
                target = dest / package / file.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dist.locate_file(file), target)
    python_licenses = (Path(sys.base_prefix) / 'LICENSE.txt',
                       Path(sys.base_prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'LICENSE.txt')
    for python_license in python_licenses:
        if python_license.exists():
            shutil.copy2(python_license, dest / 'Python-LICENSE.txt')
            break
    (dest / 'SOURCES.txt').write_text(
        'Build dependencies and corresponding upstream sources:\n'
        'Python ' + sys.version.split()[0] + '\nhttps://www.python.org/downloads/source/\n\n'
        'PySide6-Essentials / Shiboken 6.12.0 (Qt for Python)\n'
        'https://code.qt.io/cgit/pyside/pyside-setup.git/\n'
        'Qt 6.12.0\nhttps://code.qt.io/cgit/qt/qtbase.git/\n'
        'Qt libraries are dynamically loaded from the app bundle on macOS,\n'
        'or _internal/PySide6 on Windows.\n\n'
        'PyInstaller 6.22.3 (bootloader exception in bundled license)\n'
        'https://github.com/pyinstaller/pyinstaller/tree/v6.22.3\n', encoding='utf-8')

if __name__ == '__main__':
    collect(sys.argv[1])
