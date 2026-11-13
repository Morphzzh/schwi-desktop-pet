"""Check packaged startup, single-instance IPC and persisted preferences."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

def main(executable, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    data = output / 'settings'
    data.mkdir(exist_ok=True)
    (data / 'settings.json').write_text(json.dumps({'scale': 1.5, 'random_idle': False}), encoding='utf-8')
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'):
        env.pop(key, None)
    args = [str(Path(executable).resolve()), '--data-dir', str(data), '--quit-after', '12']
    process_options = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
    first = subprocess.Popen(args, env=env, **process_options)
    checks = []
    try:
        lock = data / 'instance.lock'
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline:
            if lock.exists():
                break
            if first.poll() is not None:
                raise AssertionError('First process exited unexpectedly')
            time.sleep(.1)
        assert lock.exists() and first.poll() is None
        assert int(lock.read_text(encoding='utf-8').splitlines()[0]) == first.pid
        time.sleep(.5)
        checks.append('packaged application starts with a clean Python/Qt environment')
        # A second full instance would run for 12 seconds and exceed this timeout.
        second = subprocess.run(args, env=env, timeout=6, **process_options)
        assert second.returncode == 0 and first.poll() is None
        assert int(lock.read_text(encoding='utf-8').splitlines()[0]) == first.pid
        checks.append('second launch exits while the original instance remains running')
        returncode = first.wait(timeout=15)
        assert returncode == 0, f'First instance exited with status {returncode}'
        assert not lock.exists(), 'Instance lock remains after normal exit'
        stored = json.loads((data / 'settings.json').read_text(encoding='utf-8'))
        assert stored['scale'] == 1.5 and stored['random_idle'] is False
        assert isinstance(stored['x'], int) and isinstance(stored['y'], int)
        checks.append('normal shutdown saves restored preferences and releases the instance lock')
        log = data / 'app.log'
        assert not log.exists() or not log.read_text(encoding='utf-8').strip()
        checks.append('no application errors were logged')
        result = {'ok': True, 'checks': checks}
    except Exception as exc:
        result = {'ok': False, 'checks': checks, 'error': repr(exc), 'traceback': traceback.format_exc(),
                  'first_returncode': first.poll()}
        if first.poll() is None:
            first.terminate()
            first.wait(timeout=5)
    (output / 'packaged-integration.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
