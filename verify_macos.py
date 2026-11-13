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
    process = subprocess.Popen([str(binary), '--self-test', str(output / 'gui'),
                                '--data-dir', str(output / 'gui-settings')], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        try:
            log,_ = process.communicate(timeout=55)
        except subprocess.TimeoutExpired:
            sample=subprocess.run(['/usr/bin/sample',str(process.pid),'3','-file',str(output/'native-stack.txt')],
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
            (output/'sample-process.log').write_text(sample.stdout,encoding='utf-8')
            try:
                subprocess.run(['/usr/sbin/screencapture','-x',str(output/'desktop.png')],
                               stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8)
            except subprocess.TimeoutExpired:pass
            log,_ = process.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        process.kill()
        log,_=process.communicate()
        (output/'gui-process.log').write_text(log+'\nSelf-test timed out.\n',encoding='utf-8')
        raise
    (output / 'gui-process.log').write_text(log, encoding='utf-8')
    assert process.returncode == 0, log
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
