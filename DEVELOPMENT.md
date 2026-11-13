# 开发、构建与验证

## 运行源码

使用 Windows x64、Python 3.10 或更高版本。建议把虚拟环境放在较短路径（例如 `C:\dev\schwi-venv`），以避开部分 Qt 文件的 Windows 路径长度限制。

```powershell
py -m venv C:\dev\schwi-venv
& C:\dev\schwi-venv\Scripts\python.exe -m pip install -r requirements.txt
& C:\dev\schwi-venv\Scripts\python.exe main.py
```

运行时仅需要 PySide6-Essentials；PyInstaller 用于打包，Pillow 和 NumPy 用于素材处理。`assets` 已包含可直接使用的素材。源码包中的 `artwork/redraw-1.0.3` 保存固定底稿、已检查的完整人物图、生成描述和检查记录。`assemble_redraw.py` 将这些完整图等比例缩放、定位并组装成播放素材；正常运行和打包无需执行它。历史校色和鞋型拼接脚本不适用于本次重画素材。

## 构建和检查

```powershell
.\build.ps1 -Python C:\dev\schwi-venv\Scripts\python.exe
& C:\dev\schwi-venv\Scripts\python.exe -m unittest discover -s tests -v
& .\dist\SchwiPet\SchwiPet.exe --self-test .\qa --data-dir .\qa-settings
```

`--self-test` 在真实 Qt 窗口内检查点击、拖动、双击、动画恢复、害羞停留、暂停、缩放、置顶、菜单和设置保存，并输出 JSON 与截图。测试使用单独的数据目录，不影响正常使用。`--quit-after 10` 可在启动后 10 秒自动退出，用于启动检查。

`build_msi.py` 使用 WiX 4.0.6 和同版本的 UI 扩展，将 `dist/SchwiPet` 打包为中文安装向导。通过 `--wix` 和 `--ui-extension` 指定两个构建工具 DLL 的路径；依赖仅用于制作安装包，安装者无需安装 .NET 或 WiX。MSI 的升级标识固定，每个版本使用独立产品标识，支持后续升级与卸载。

界面使用 Qt / PySide6，Windows 程序用 PyInstaller 构建。程序目录附有依赖许可原文及来源说明。角色与参考作品相关权利归原权利人；本项目是供个人使用的同人桌宠。


## macOS 构建与验证

## 签名与验证范围

本构建采用本地临时签名（ad-hoc），没有 Apple Developer ID 签名，也未进行 Apple 公证。因此首次打开可能被 macOS 拦截。这不等于已通过 Apple 审核。如果愿意信任本软件，可按 Apple 官方的“打开来自身份不明开发者的 Mac App”说明，在系统设置中对这一个应用选择“仍要打开”：
https://support.apple.com/zh-cn/guide/mac-help/mh40616/mac

自动测试会检查原生 Cocoa 窗口中的点击、拖动、动画、菜单、托盘恢复、重复启动、设置保存，并在 ZIP 解压后再运行。每个包有对应的测试报告；只在检查通过后保存成品。自动检查无法替代不同 Mac 上的人工体验，多显示器、全屏应用、不同桌面空间和长期运行仍需实际使用验证。

## 不持有 Mac 时如何构建

仓库中的 `.github/workflows/macos.yml` 使用 GitHub 托管的 macOS 运行器，分别构建 Apple 芯片和 Intel 版本。进入仓库的 Actions，选择 `Build and test macOS desktop pet`，点击 `Run workflow`。完成后下载对应的 `SchwiPet-macOS-*` artifact；里面的 ZIP 才是实际分发包，应保留它的目录结构。

工作流仅手动触发，不在每次提交时自动运行。私有仓库使用账号的 Actions 配额；本项目不会更改计费设置或公开仓库。

有 Mac 时也可本地构建：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python build_macos.py
python verify_macos.py
python package_macos.py
```

构建必须在 macOS 上进行。依据：

- PyInstaller 平台说明：https://pyinstaller.org/en/stable/
- Qt 6.12 的 macOS 版本要求：https://doc.qt.io/qt-6/macos.html
- GitHub macOS 运行器：https://docs.github.com/en/actions/reference/runners/github-hosted-runners

角色及参考作品相关权利归原权利人；本项目为个人使用的同人桌宠。
