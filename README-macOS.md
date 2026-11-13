# 休比桌宠 1.0.3 · macOS 版

## 选择版本与运行

- Apple 芯片 Mac（M1、M2、M3 等）：选择 `arm64` 包。
- Intel Mac：选择 `x86_64` 包。
- 当前依赖要求 macOS 14.4 或更新版本。程序不支持在 iPhone 或 iPad 上运行。

推荐打开 DMG，将 `SchwiPet.app` 拖到旁边的 `Applications` 文件夹，再从“应用程序”打开。也可解压 ZIP 后自行移动应用。程序包含 Python 和所需素材，正常使用不需要安装开发工具或联网。卸载时退出桌宠，再将应用移到废纸篓即可；个人设置会保留。

单击休比会随机播放害羞、开心、惊讶、挥手、跳跃、期待、兴奋或打瞌睡。双击跳跃，按住拖动，右键（触控板双指点按）打开菜单。

待机动作默认间隔 10 秒，散步默认间隔 24 秒。在右键菜单的“待机动作间隔”和“散步间隔”中选择秒数，也可自定义 2–300 秒；设置自动保存。正在播放动作、拖动或操作菜单时会稍后执行。视线跟随与自动动作可以同时开启，动作结束后恢复跟随；拖动转向按最近的鼠标移动方向立即更新。

Mac 顶部菜单栏的休比图标可显示、收起和退出桌宠。默认开启置顶与偶尔自己做动作，关闭视线跟随和散步；散步需要同时打开“偶尔自己做动作”。不会设置开机启动。设置保存在 `~/Library/Application Support/SchwiDesktopPet/settings.json`，同目录的 `app.log` 用于排查错误。

本版使用 576×624 像素的动作帧，在相同显示大小下保留更多细节。默认散步间隔按最长自动待机动作 3.56 秒，从 20 秒加到 24 秒；两个计时器仍独立运行，发生冲突时等待当前动作结束。

本次重画版以固定底稿重新绘制整套动作，按 1.0 参考图统一配色，保留高光和腮红。119 个播放帧位包含过渡、停留、返回和左右镜像；完整绘制手部、腿部和鞋袜，未拼接替换肢体。下载时请选择本次重画构建的包。

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
