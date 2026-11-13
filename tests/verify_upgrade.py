"""Verify an explicitly requested upgrade of an existing per-user installation.

Requires a before.json snapshot and backup prepared before running this script.
Does not uninstall the resulting application or change personal preferences.
"""
import hashlib
import ctypes
import json
import msilib
from pathlib import Path
import subprocess
import sys
import winreg

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def product_state(code):
    query=ctypes.windll.msi.MsiQueryProductStateW
    query.argtypes=[ctypes.c_wchar_p]
    query.restype=ctypes.c_int
    return query(code)

def product_version(code):
    query=ctypes.windll.msi.MsiGetProductInfoW
    query.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint)]
    query.restype=ctypes.c_uint
    value=ctypes.create_unicode_buffer(256)
    size=ctypes.c_uint(len(value))
    assert query(code,'VersionString',value,ctypes.byref(size))==0
    return value.value

def main(msi_path, output_path):
    root = Path(__file__).resolve().parents[1]
    msi, output = Path(msi_path).resolve(), Path(output_path).resolve()
    before = json.loads((output/'before.json').read_text(encoding='utf-8'))
    assert (output/'backup/installed-app/SchwiPet.exe').is_file()
    previous = before['previous_product_code']
    db = msilib.OpenDatabase(str(msi), msilib.MSIDBOPEN_READONLY)
    view = db.OpenView('SELECT `Property`, `Value` FROM `Property`')
    view.Execute(None)
    properties = {}
    while (record := view.Fetch()) is not None:
        properties[record.GetString(1)] = record.GetString(2)
    view.Close()
    current = properties['ProductCode']
    assert current != previous
    assert properties['UpgradeCode'] == '{F76598CB-C4EF-5AF3-A1E5-2BEAB7B2BCF0}'
    assert product_state(previous)==5
    assert product_version(previous)==properties['ProductVersion']
    checks = ['new product identity with stable upgrade family and unchanged visible version']
    result = {'ok': False, 'previous_product': previous, 'current_product': current,
              'version': properties['ProductVersion'], 'checks': checks}
    try:
        for name in ('upgrade', 'repeat-same-package'):
            run = subprocess.run(['msiexec.exe','/i',str(msi),'/qn','/norestart',
                                  '/L*v',str(output/(name+'.log'))], timeout=180,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
            assert run.returncode in (0,3010), (name,run.returncode)
            checks.append(name+' exits successfully without manual uninstall')
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\SchwiDesktopPet') as key:
            installed = Path(winreg.QueryValueEx(key,'InstallPath')[0]).resolve()
        assert installed == Path(before['install_path']).resolve()
        checks.append('original installation directory preserved')
        assert product_state(previous)!=5 and product_state(current)==5
        checks.append('old product registration removed and new product registered')
        files = [p for p in (root/'dist/SchwiPet').rglob('*') if p.is_file()]
        for source in files:
            target = installed/source.relative_to(root/'dist/SchwiPet')
            assert target.is_file() and digest(target)==digest(source), str(target)
        checks.append(f'all {len(files)} installed files match the new build')
        settings = Path(before['settings_path'])
        assert (digest(settings) if settings.exists() else None)==before['settings_sha256']
        checks.append('personal settings preserved byte for byte')
        run = subprocess.run([str(installed/'SchwiPet.exe'),'--self-test',str(output/'gui'),
                              '--data-dir',str(output/'test-settings')],timeout=120,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        assert run.returncode==0
        gui=json.loads((output/'gui/smoke-test.json').read_text(encoding='utf-8'))
        assert gui['ok']
        result['gui_checks']=len(gui['checks'])
        checks.append('upgraded installed application passes native GUI checks')
        result['ok']=True
    except Exception as exc:
        result['error']=repr(exc)
    (output/'upgrade-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    return 0 if result['ok'] else 1

if __name__=='__main__':
    raise SystemExit(main(sys.argv[1],sys.argv[2]))
