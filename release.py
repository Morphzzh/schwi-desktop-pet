"""Create portable and source ZIPs from the tested application build."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from platform_support import APP_VERSION

root = Path(__file__).resolve().parent
outputs = root.parent / 'outputs' / ('休比桌宠-' + APP_VERSION)
outputs.mkdir(parents=True, exist_ok=True)
app = outputs / '休比桌宠'
shutil.copytree(root / 'dist' / 'SchwiPet', app, dirs_exist_ok=True)
(app / '使用说明.txt').write_text(
    f'休比桌宠 {APP_VERSION}\n\n'
    '双击 SchwiPet.exe 开始。请保留 _internal 文件夹。\n'
    '无需安装 Python，无需联网或登录。\n\n'
    '单击：随机表情或动作。\n双击：跳一下。\n按住左键：拖动。\n'
    '右键：指定动作、调整大小、暂停或退出。\n'
    '托盘图标：单击显示，右键收起或退出。\n\n'
    '默认平视，关闭视线跟随和散步；可从菜单开启。\n'
    '待机动作默认间隔 10 秒，散步默认间隔 24 秒；右键菜单可调整或自定义间隔。\n'
    '位置与设置自动保存，不会设置开机启动。\n'
    '完整说明见 README.md。\n', encoding='utf-8-sig')

def archive(path, files):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for source, name in files:
            z.write(source, name)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        count = len(z.namelist())
    return {'path': path.name, 'files': count, 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'zip_crc_ok': True}

reports = []
reports.append(archive(outputs / '休比桌宠-Windows-x64.zip',
    [(p, str(Path('休比桌宠') / p.relative_to(app))) for p in sorted(app.rglob('*')) if p.is_file()]))
source_files = []
for p in sorted(root.rglob('*')):
    rel = p.relative_to(root)
    if rel.parts[0]=='artwork':
        if len(rel.parts)<2:
            continue
        if rel.parts[1]=='redraw-'+APP_VERSION:
            if len(rel.parts)>2 and rel.parts[2] in {'candidates','rejected','frames','assembled','sequence-qa'}:
                continue
            if len(rel.parts)>2 and rel.parts[2] in {'raw','qa'} and p.suffix!='.json':
                continue
        elif rel.as_posix() not in {'artwork/release-'+APP_VERSION+'/palette-reference-v1.png','artwork/icon-crop.json'}:
            continue
    art_review = rel.parts[0]=='artwork' and p.suffix=='.json'
    if p.is_file() and (art_review or not any(part.startswith('qa') for part in rel.parts)) and not set(rel.parts).intersection({'.git', 'build', 'dist', 'build-msi', 'build-macos', 'dist-macos', 'extract-check', '__pycache__'}) and p.suffix != '.pyc':
        source_files.append((p, str(Path('休比桌宠-源码') / rel)))
reports.append(archive(outputs / '休比桌宠-源码.zip', source_files))
qa = outputs / '休比桌宠-验证'
qa.mkdir(exist_ok=True)
(qa / 'packages.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(reports, ensure_ascii=False, indent=2))
