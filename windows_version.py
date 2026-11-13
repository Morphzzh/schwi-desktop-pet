"""Write PyInstaller's Windows version resource from the application version."""
from pathlib import Path
from platform_support import APP_VERSION

version = tuple(int(part) for part in APP_VERSION.split('.')) + (0,)
output = Path(__file__).resolve().parent / 'build' / 'version-info.txt'
output.parent.mkdir(exist_ok=True)
output.write_text(f'''VSVersionInfo(
  ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, mask=0x3f,
    flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('080404b0', [
    StringStruct('FileDescription', '休比桌宠'),
    StringStruct('FileVersion', '{APP_VERSION}'),
    StringStruct('ProductName', '休比桌宠'),
    StringStruct('ProductVersion', '{APP_VERSION}'),
    StringStruct('OriginalFilename', 'SchwiPet.exe')])]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])])
''', encoding='utf-8')
