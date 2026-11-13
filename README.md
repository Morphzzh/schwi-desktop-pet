# 休比桌宠 1.1.0

离线桌面伴侣，提供 Windows 版本和 macOS 构建支持。保留休比的帽兜、酒紫色长发与发尾、金色眼睛、小腿袜；默认平视前方。macOS 的安装、最低系统版本和验证范围见 [README-macOS.md](README-macOS.md)。下面介绍 Windows 版本。

## 使用

将 ZIP 完整解压到一个文件夹，双击 `SchwiPet.exe`。请保留旁边的 `_internal` 文件夹。成品无需安装 Python，也不需要登录或联网。

- 单击休比：随机触发害羞、开心、惊讶、挥手、跳跃、期待。每轮六种都能出现，相邻两次不重复。
- 害羞：闭眼、双手捂脸、脸红，稍稍低头后恢复站姿。
- 双击：跳一下。
- 按住左键拖动：移动休比，松开后恢复站姿。
- 右键：指定动作、调整大小、暂停、开关置顶、视线跟随、小范围散步等。
- 托盘图标：单击显示休比；右键可收起、找回或退出。
- 再次打开程序：显示已经运行的休比，不会重复启动多个角色。

默认开启置顶和偶尔自己做动作，关闭视线跟随和散步。散步需要同时开启“偶尔自己做动作”。程序不会设置开机启动。动画和互动均在本机运行，不含聊天或语音功能。

位置和偏好自动保存在 `%LOCALAPPDATA%\SchwiDesktopPet\settings.json`。日志位于同目录的 `app.log`。退出后删除设置文件即可恢复默认设置；也可直接用右键菜单“找回休比 / 重置位置”。

## 运行源码

使用 Windows x64、Python 3.10 或更高版本。建议把虚拟环境放在较短路径（例如 `C:\dev\schwi-venv`），以避开部分 Qt 文件的 Windows 路径长度限制。

```powershell
py -m venv C:\dev\schwi-venv
& C:\dev\schwi-venv\Scripts\python.exe -m pip install -r requirements.txt
& C:\dev\schwi-venv\Scripts\python.exe main.py
```

运行时仅需要 PySide6-Essentials；PyInstaller 用于打包，Pillow 用于素材处理。`assets` 已包含可直接使用的素材。`artwork` 保存新增表情原图、生成描述及预览；`prepare_assets.py` 是开发时使用的素材整理脚本，它需要额外指定 Pets 插件的 `extract_strip_frames.py`，正常运行及打包无需该脚本。

## 构建和检查

```powershell
.\build.ps1 -Python C:\dev\schwi-venv\Scripts\python.exe
& C:\dev\schwi-venv\Scripts\python.exe -m unittest discover -s tests -v
& .\dist\SchwiPet\SchwiPet.exe --self-test .\qa --data-dir .\qa-settings
```

`--self-test` 在真实 Qt 窗口内检查点击、拖动、双击、动画恢复、害羞停留、暂停、缩放、置顶、菜单和设置保存，并输出 JSON 与截图。测试使用单独的数据目录，不影响正常使用。`--quit-after 10` 可在启动后 10 秒自动退出，用于启动检查。

界面使用 Qt / PySide6，Windows 程序用 PyInstaller 构建。程序目录附有依赖许可原文及来源说明。角色与参考作品相关权利归原权利人；本项目是供个人使用的同人桌宠。
