# 休比桌宠 1.0.3

离线桌面伴侣，提供 Windows 版本和 macOS 构建支持。保留休比的帽兜、酒紫色长发与发尾、金色眼睛、小腿袜；默认平视前方。macOS 的安装、最低系统版本和验证范围见 [README-macOS.md](README-macOS.md)。下面介绍 Windows 版本。

## 使用

推荐双击 MSI 安装包，按向导完成当前用户安装，然后从桌面或开始菜单打开“休比桌宠”。可在 Windows“设置 → 应用 → 已安装的应用”中卸载；卸载保留个人设置，不会设置开机启动。

也可使用免安装 ZIP：完整解压到一个文件夹，双击 `SchwiPet.exe`，并保留旁边的 `_internal` 文件夹。两种方式均无需安装 Python，也不需要登录或联网。

- 单击休比：随机触发害羞、开心、惊讶、挥手、跳跃、期待、兴奋、打瞌睡。每轮八种都能出现，相邻两次不重复。
- 双击：跳一下。
- 按住左键拖动：移动休比，转向跟随最近的鼠标移动方向，松开后恢复站姿。
- 右键：指定动作、调整大小、暂停、开关置顶、视线跟随、小范围散步等。
- 托盘图标：单击显示休比；右键可收起、找回或退出。
- 再次打开程序：显示已经运行的休比，不会重复启动多个角色。

默认开启置顶和偶尔自己做动作，关闭视线跟随和散步。散步需要同时开启“偶尔自己做动作”。程序不会设置开机启动。动画和互动均在本机运行，不含聊天或语音功能。

待机动作默认间隔 10 秒，散步默认间隔 24 秒。右键菜单的“待机动作间隔”和“散步间隔”可选择常用秒数，或通过“自定义…”输入 2–300 秒；设置会自动保存。正在播放动作、拖动或操作菜单时，自动动作会稍后执行，不会互相打断。视线跟随可以与待机动作同时开启，动作结束后恢复跟随。

位置和偏好自动保存在 `%LOCALAPPDATA%\SchwiDesktopPet\settings.json`。日志位于同目录的 `app.log`。退出后删除设置文件即可恢复默认设置；也可直接用右键菜单“找回休比 / 重置位置”。

本版动作素材为每帧 576×624 像素，显示大小与旧版相同，可在高分屏和放大显示时保留更多细节。跑动前后摆臂各占半个周期，切换方向时继续当前步伐。

1.0.3 测试版已直接按 1.0 原图分别统一头发、耳片、衣服、肤色、眼睛和鞋袜配色，从干净原帧重新校色，减少面部、帽兜等位置的填色斑块，保留高光和腮红；全部动作使用按底稿统一的圆头鞋型和鞋袜分界，并为八种互动各补充两帧过渡动作。

散步默认 24 秒来自 20 秒加上最长自动待机动作 3.56 秒后向上取整。两个计时器独立运行，动作和散步互相等待，避免到时碰在一起时打断对方。

## 运行源码

使用 Windows x64、Python 3.10 或更高版本。建议把虚拟环境放在较短路径（例如 `C:\dev\schwi-venv`），以避开部分 Qt 文件的 Windows 路径长度限制。

```powershell
py -m venv C:\dev\schwi-venv
& C:\dev\schwi-venv\Scripts\python.exe -m pip install -r requirements.txt
& C:\dev\schwi-venv\Scripts\python.exe main.py
```

运行时仅需要 PySide6-Essentials；PyInstaller 用于打包，Pillow 用于素材处理，NumPy 仅用于重新运行底稿校色脚本。`assets` 已包含可直接使用的素材。`artwork/release-1.0.3` 保存本版底稿、动作原图和生成描述；`prepare_release_assets.py` 用于整理整套素材，需要通过 `--source` 指定动作原图目录、通过 `--extractor` 指定 Pets 插件的 `extract_strip_frames.py`。正常运行及打包无需该脚本。需要重新校色时先运行 `calibrate_palette.py`，再将 `prepare_release_assets.py` 的 `--source` 指向 `artwork/release-1.0.3/calibrated/source`；随后运行 `rebuild_continuity.py`，以保存的 `palette-reference-v1.png` 连续校色，并从 `shoe-style` 中读取已生成的统一鞋型，按原脚踝位置合成；再运行 `prepare_icon.py` 和 `record_assets.py` 更新图标与素材清单。旧的分区校色脚本不再用于本版素材，原图保持可回查。

## 构建和检查

```powershell
.\build.ps1 -Python C:\dev\schwi-venv\Scripts\python.exe
& C:\dev\schwi-venv\Scripts\python.exe -m unittest discover -s tests -v
& .\dist\SchwiPet\SchwiPet.exe --self-test .\qa --data-dir .\qa-settings
```

`--self-test` 在真实 Qt 窗口内检查点击、拖动、双击、动画恢复、害羞停留、暂停、缩放、置顶、菜单和设置保存，并输出 JSON 与截图。测试使用单独的数据目录，不影响正常使用。`--quit-after 10` 可在启动后 10 秒自动退出，用于启动检查。

`build_msi.py` 使用 WiX 4.0.6 和同版本的 UI 扩展，将 `dist/SchwiPet` 打包为中文安装向导。通过 `--wix` 和 `--ui-extension` 指定两个构建工具 DLL 的路径；依赖仅用于制作安装包，安装者无需安装 .NET 或 WiX。MSI 的升级标识固定，每个版本使用独立产品标识，支持后续升级与卸载。

界面使用 Qt / PySide6，Windows 程序用 PyInstaller 构建。程序目录附有依赖许可原文及来源说明。角色与参考作品相关权利归原权利人；本项目是供个人使用的同人桌宠。
