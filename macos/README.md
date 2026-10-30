# macOS 应用启动入口

`launcher.swift` 是 Claudio.app 的启动器源码。它调用项目启动脚本，
通过 `CLAUDIO_APP_PYTHON` 指定应用包内 `Contents/MacOS/Claudio`。
该文件使用本机 Python framework 的 `Resources/Python.app/Contents/MacOS/Python`
可执行文件副本；不能使用指向原 Python.app 的符号链接，否则 Cocoa 仍识别为 Python。

启动脚本仅在 `.app` 启动时设置 `__PYVENV_LAUNCHER__`，复用项目 `.venv`
中的依赖。直接运行 `.command` 和 Windows 启动逻辑保持原样。

应用包的 CFBundleName / CFBundleDisplayName 均应为 Claudio，图标为
Claudio-transparent.icns。编译启动器后需要重新签名应用；Finder 自定义
图标应在签名之后设置，避免资源叉干扰签名。

2026-10-30 验证：独立运行入口的 NSBundle 指向桌面 Claudio.app；
NSProcessInfo.processName 和 NSRunningApplication.localizedName 均返回 Claudio；
虚拟环境依赖导入、shell 语法和应用签名检查通过。未重启用户正在运行的旧实例，
台前调度实际显示留待重启后确认。桌面 .app 依赖本机 Python 和桌面项目文件夹，
不是可直接分发到其他 Mac 的独立安装包。
