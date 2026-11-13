"""Run the bundled app with Cocoa and preserve an honest test report."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', type=Path, default=Path('dist-macos/SchwiPet.app'))
    parser.add_argument('--output', type=Path, default=Path('qa-macos'))
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise SystemExit('This check requires macOS.')
    app, output = args.app.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    binary = app / 'Contents' / 'MacOS' / 'SchwiPet'
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'):
        env.pop(key, None)
    env['QT_QPA_PLATFORM'] = 'cocoa'
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    arches = subprocess.check_output(['/usr/bin/lipo', '-archs', str(binary)], text=True).strip()
    assert platform.machine() in arches.split(), arches
    try:
        result = subprocess.run([str(binary), '--self-test', str(output / 'gui'),
                                 '--data-dir', str(output / 'gui-settings')], env=env, timeout=120,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except subprocess.TimeoutExpired as exc:
        log=exc.stdout or ''
        if isinstance(log,bytes):
            log=log.decode('utf-8',errors='replace')
        (output / 'gui-process.log').write_text(log+'\nSelf-test timed out after 120 seconds.\n',encoding='utf-8')
        raise
    (output / 'gui-process.log').write_text(result.stdout, encoding='utf-8')
    assert result.returncode == 0, result.stdout
    gui = json.loads((output / 'gui' / 'smoke-test.json').read_text(encoding='utf-8'))
    assert gui['ok'] and gui['qt_platform'] == 'cocoa' and gui['platform'] == 'darwin'
    runner = Path(__file__).parent / 'tests' / 'check_packaged.py'
    subprocess.run([sys.executable, str(runner), str(binary), str(output / 'integration')],
                   env=env, check=True, timeout=35)
    report = {'ok': True, 'platform': 'darwin', 'arch': platform.machine(),
              'macos': platform.mac_ver()[0], 'qt_platform': gui['qt_platform'],
              'gui_checks': len(gui['checks']), 'tray_available': gui['tray_available'],
              'ad_hoc_signature_verified': True, 'notarized': False,
              'manual_desktop_review': False,
              'notes': 'Cocoa automated tests; no manual full-screen, Spaces, or multi-display review.'}
    (output / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
