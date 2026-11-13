"""Build a per-user x64 MSI from the completed Windows app using WiX 4.0.6."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import xml.etree.ElementTree as ET

from platform_support import APP_VERSION

ROOT = Path(__file__).resolve().parent
NS = 'http://wixtoolset.org/schemas/v4/wxs'
UI_NS = NS + '/ui'
ET.register_namespace('', NS)
ET.register_namespace('ui', UI_NS)
UPGRADE_CODE = 'F76598CB-C4EF-5AF3-A1E5-2BEAB7B2BCF0'
COMPONENT_NAMESPACE = uuid.UUID('6454a24c-2823-4dca-957f-a8f3419fb572')

def element(parent, name, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + name, attrs)

def identifier(prefix, path):
    return prefix + hashlib.sha256(str(path).replace('\\', '/').lower().encode()).hexdigest()[:24]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wix', type=Path, required=True)
    parser.add_argument('--ui-extension', type=Path, required=True)
    parser.add_argument('--app', type=Path, default=ROOT / 'dist' / 'SchwiPet')
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'outputs' / f'休比桌宠-{APP_VERSION}-Windows-x64.msi')
    args = parser.parse_args()
    app = args.app.resolve()
    assert (app / 'SchwiPet.exe').is_file(), 'Build the Windows application first.'
    build = ROOT / 'build-msi'
    build.mkdir(exist_ok=True)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # A rebuilt MSI is a new major-upgrade product, even when its visible
    # version remains 1.0.3. Reusing a ProductCode with a changed PackageCode
    # causes Windows Installer error 1638 on a normal double-click install.
    # The stable UpgradeCode connects these packages and removes the old one.
    product_code = str(uuid.uuid4()).upper()
    wix = ET.Element('{' + NS + '}Wix')
    package = element(wix, 'Package', Name='休比桌宠', Manufacturer='Schwi Desktop Pet',
                      Version=APP_VERSION, Language='2052', Codepage='936',
                      UpgradeCode=UPGRADE_CODE, ProductCode=product_code,
                      Scope='perUser', InstallerVersion='500')
    element(package, 'SummaryInformation', Description='休比离线桌宠安装程序', Codepage='936')
    # The previous 1.0.1 release was accidentally packaged as 1.1.0.
    # Permit that specific migration while still blocking other newer versions.
    if tuple(map(int, APP_VERSION.split('.'))) < (1, 1, 0):
        element(package, 'MajorUpgrade', AllowDowngrades='yes', Schedule='afterInstallInitialize')
        upgrade = element(package, 'Upgrade', Id=UPGRADE_CODE)
        element(upgrade, 'UpgradeVersion', Minimum=APP_VERSION, IncludeMinimum='no',
                Maximum='1.1.0', IncludeMaximum='no', OnlyDetect='yes', Property='NEWER_BELOW_LEGACY')
        element(upgrade, 'UpgradeVersion', Minimum='1.1.0', IncludeMinimum='no',
                OnlyDetect='yes', Property='NEWER_ABOVE_LEGACY')
        element(package, 'Launch', Condition='NOT NEWER_BELOW_LEGACY AND NOT NEWER_ABOVE_LEGACY',
                Message='已安装更新版本的休比桌宠。')
    else:
        element(package, 'MajorUpgrade', DowngradeErrorMessage='已安装更新版本的休比桌宠。',
                AllowSameVersionUpgrades='yes', Schedule='afterInstallInitialize')
    element(package, 'MediaTemplate', EmbedCab='yes', CompressionLevel='high')
    icon_id = 'SchwiIcon_' + APP_VERSION.replace('.', '_')
    element(package, 'Icon', Id=icon_id, SourceFile=str(ROOT / 'assets' / 'schwi.ico'))
    element(package, 'Property', Id='ARPPRODUCTICON', Value=icon_id)
    previous_path = element(package, 'Property', Id='INSTALLFOLDER')
    element(previous_path, 'RegistrySearch', Id='InstalledDirectory', Root='HKCU',
            Key='Software\\SchwiDesktopPet', Name='InstallPath', Type='raw', Bitness='always64')
    element(package, 'Property', Id='WIXUI_EXITDIALOGOPTIONALTEXT', Value='安装完成后，可从桌面或开始菜单打开休比桌宠。')
    element(package, 'Launch', Condition='Installed OR VersionNT64', Message='需要 64 位 Windows。')
    local = element(package, 'StandardDirectory', Id='LocalAppDataFolder')
    programs = element(local, 'Directory', Id='UserPrograms', Name='Programs')
    install = element(programs, 'Directory', Id='INSTALLFOLDER', Name='SchwiDesktopPet')
    start = element(package, 'StandardDirectory', Id='ProgramMenuFolder')
    element(start, 'Directory', Id='ApplicationProgramsFolder', Name='休比桌宠')
    element(package, 'StandardDirectory', Id='DesktopFolder')
    feature = element(package, 'Feature', Id='MainFeature', Title='休比桌宠', Level='1')
    directories = {Path('.'): install}
    all_dirs = sorted({p.parent.relative_to(app) for p in app.rglob('*') if p.is_file()}, key=lambda p: (len(p.parts), str(p)))
    for directory in all_dirs:
        for depth in range(1, len(directory.parts) + 1):
            part = Path(*directory.parts[:depth])
            if part not in directories:
                directories[part] = element(directories[part.parent], 'Directory', Id=identifier('D', part), Name=part.name)
    cleaned = set()
    files = sorted(p for p in app.rglob('*') if p.is_file())
    for source in files:
        rel = source.relative_to(app)
        component_id = identifier('C', rel)
        component = element(directories[rel.parent], 'Component', Id=component_id,
                            Guid=str(uuid.uuid5(COMPONENT_NAMESPACE, rel.as_posix().lower())).upper(), Bitness='always64')
        element(component, 'File', Id=identifier('F', rel), Source=str(source))
        element(component, 'RegistryValue', Root='HKCU', Key='Software\\SchwiDesktopPet\\InstallerComponents',
                Name=component_id, Value='[INSTALLFOLDER]' + str(rel), Type='string', KeyPath='yes')
        if rel.parent not in cleaned:
            element(component, 'RemoveFolder', Id=identifier('R', rel.parent), On='uninstall')
            cleaned.add(rel.parent)
        if rel.as_posix() == 'SchwiPet.exe':
            element(component, 'RegistryValue', Root='HKCU', Key='Software\\SchwiDesktopPet',
                    Name='InstallPath', Value='[INSTALLFOLDER]', Type='string')
            for location, shortcut_id in (('DesktopFolder', 'DesktopShortcut'), ('ApplicationProgramsFolder', 'StartMenuShortcut')):
                element(component, 'Shortcut', Id=shortcut_id, Directory=location, Name='休比桌宠',
                        Target='[INSTALLFOLDER]SchwiPet.exe', WorkingDirectory='INSTALLFOLDER', Icon=icon_id)
            element(component, 'RemoveFolder', Id='RemoveStartMenuFolder', Directory='ApplicationProgramsFolder', On='uninstall')
        element(feature, 'ComponentRef', Id=component_id)
    ET.SubElement(package, '{' + UI_NS + '}WixUI', {'Id': 'WixUI_InstallDir', 'InstallDirectory': 'INSTALLFOLDER'})
    ui = element(package, 'UI')
    # This personal companion has no custom EULA. Skip the library placeholder.
    element(ui, 'Publish', Dialog='WelcomeDlg', Control='Next', Event='NewDialog', Value='InstallDirDlg', Order='2', Condition='NOT Installed')
    element(ui, 'Publish', Dialog='InstallDirDlg', Control='Back', Event='NewDialog', Value='WelcomeDlg', Order='2')
    element(package, 'UIRef', Id='WixUI_ErrorProgressText')
    ET.indent(wix)
    authoring = build / 'SchwiPet.wxs'
    ET.ElementTree(wix).write(authoring, encoding='utf-8', xml_declaration=True)
    subprocess.run(['dotnet', str(args.wix.resolve()), 'build', str(authoring), '-arch', 'x64',
                    '-ext', str(args.ui_extension.resolve()), '-culture', 'zh-CN', '-out', str(output),
                    '-pdbtype', 'none', '-intermediatefolder', str(build / 'obj')], check=True)
    result = {'version': APP_VERSION, 'product_code': product_code, 'upgrade_code': UPGRADE_CODE,
              'files': len(files), 'bytes': output.stat().st_size,
              'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'path': str(output)}
    (build / 'installer.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
