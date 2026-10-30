# Claude Code 接手说明

更新时间：2026-10-30 13:50:35（Asia/Shanghai）。用户因额度即将耗尽交接，暂不继续扩展功能。

## 先读与工作位置

1. 先读 `docs/MACOS_PROMPT.md`，再读 `docs/MACOS.md`、`docs/API.md`。
2. 最新实际验证记录在 `docs/MACOS_VALIDATION.md`，本文为接手摘要。
3. 当前仓库：`/Users/li/Desktop/Claudio`；不要使用最初 Documents 下的旧路径（已移动）。
4. 分支为 `macos`，跟踪 `origin/macos`。交接前 HEAD 为 `482eadc`；本交接文档另有一次提交。远端：https://github.com/lhc20070304-creator/Claudio/tree/macos 。
5. `master` 保持 `a6b1bfb`；不得合并到或直接推 master。工作树在编写交接前干净。

## 用户偏好与硬约束

- 要同时保留 Windows 和 macOS 版本，不能替换 Windows。
- 后续工作尽量在后台，不切换/占用用户主页面。不要擅自重启当前 Claudio；真实 GUI 验收需与用户约好时机。
- DJ 英文回复、FM 英中双语、edge-tts >=7.3.1 保持不变。
- 不提交或输出 config.json、.netease_cookie、state.db*、user/liked.md 等密钥/个人数据；已有 Git 忽略规则不要移除。
- 搭建记录要随结果更新，区分真实 UI、真实接口、隔离/模拟测试。不要把后台测试当作视觉或听感验收完成。
- 用户要应用名和台前调度名都为 Claudio；桌面图标已改为透明，并按要求略微缩小。

## 环境与本机启动

- Apple Silicon，系统查询为 macOS 27.2。
- Homebrew Python 3.12.16：`/opt/homebrew/bin/python3.12`。
- Node 22.23.4：`/opt/homebrew/opt/node@22/bin/node`，npm 10.9.9。
- 项目 `.venv`：pywebview 6.2.1、edge-tts 7.3.1、PyObjC 12.2.2，pip check 通过。
- Node 使用 `npm install --omit=dev`。完整安装的 Electron 下载曾超时；当前桌面壳不依赖 Electron。package.json/package-lock.json 未改。
- 项目配置和网易云 Cookie 已配置在本地忽略文件，无需索要或重新填密钥。
- 用户入口 `/Users/li/Desktop/Claudio.app`，必须保留桌面 Claudio 项目文件夹。
- `.app` 是本机启动包装，不是可分发的独立安装包。启动器源码在 `macos/launcher.swift`。
- 应用内 `Contents/MacOS/Claudio` 是 Python framework 的实际可执行文件副本；不能改为原 Python.app 的符号链接，否则台前调度又会显示 Python。
- Swift 启动器调用 `.command` 并传 `CLAUDIO_APP_PYTHON`；脚本在最终 exec 使用 `__PYVENV_LAUNCHER__` 指向项目 `.venv/bin/python`，既保留 Claudio Bundle 身份又使用项目依赖。
- 启动日志在 `~/Library/Logs/Claudio/launcher.log`；Node 错误日志在项目 `netease_err.log`。不要向聊天输出含凭据的完整请求日志。
- 已在无窗口原生检查中确认 NSBundle 指向 Claudio.app，进程名和系统应用名均为 Claudio；实际窗口菜单也已确认显示 Claudio。
- 桌面透明小图标通过 NSWorkspace 自定义文件图标设置。重新签名之前可能要清除自定义图标资源叉，签名后再恢复；不要修改系统 Python 图标。
- 原透明 PNG 在项目 `static/claudio-macos.png`。缩小桌面图标 PNG 在 `/Users/li/Documents/Codex/2026-10-30/macos-https-github-com-lhc20070304-creator/outputs/Claudio-desktop-small.png`。桌面 .app 本身不在 Git 中。

## 已实现

- Mac 启动脚本支持 Intel/Apple Silicon Homebrew 版本化 Python/Node 路径及 nvm 回退；检查版本，自动装项目依赖。
- Mac Dock 图标及真正的 Claudio Bundle/进程身份。
- `macos/runtime.py` 管理 Node、Flask：保护已占用端口、不强杀其他程序；启动失败打印原因；Node 退出后 watchdog 重启；关闭时清理当前 Node（含替换进程）及 Flask。
- `desktop.py` 仅 darwin 走新 `main_macos()`，保留 Windows 原路径。AppKit 在主线程调用。
- `macos/window.js` 由 Mac 窗口加载后注入，单击头像最小化；共享 JS 的右键退出保留，Windows 原双击最小化不变。
- 后端 app.py / brain / services、人格 prompts 和 Windows 启动器/图标与 master 无差异。
- 运行中的旧实例未因后台修复被重启；下一次重新打开才会加载最新生命周期和单击行为。

## 已验证（细节见搭建记录）

- 真实网易云搜索、扫码登录（803）、AI 推荐 3 首歌全部带 URL。
- 最新 3 首播放地址都可读：HTTP 206、audio/mpeg，各读取 4096 字节；未播放声音。
- WebSocket 完整中文消息得到英文回答。
- FM 双语稿 7 行；首句 TTS 21744 字节、8 个有序词时间戳；hello world 11952 字节、2 个时间戳。
- 隔离副本收藏/取消收藏更新 SQLite 和 user/liked.md；分类 LLM 使用桩，未污染个人收藏。
- 无依赖隔离副本在最小 PATH 下自动安装成功，最终入口替换为无窗口检查；不是 Finder 双击 GUI 测试。
- 真实 Node + Flask 在随机端口跑通搜索、taste、WebSocket，停止后端口释放。
- 6 个 Python 生命周期回归测试通过（含窗口正常结束和失败的模拟清理）。
- JS 逻辑测试验证 Mac 单击、Windows 双击、右键退出，以及 FM 静音开头、暂停、延迟帧和结束清理；使用模拟音频时钟。

可重跑（不启动界面）：
```bash
cd /Users/li/Desktop/Claudio
.venv/bin/python -m unittest discover -s tests -v
/opt/homebrew/opt/node@22/bin/node tests/test_macos_ui_logic.cjs
bash -n 启动Claudio.command
```

## 尚未完成，下一步

需用户允许前台操作后完成：真实头像单击最小化/右键退出，拖动/置顶和实际窗口尺寸，扬声器出声、FM 声音与高亮同步、实际 UI 收藏、Finder 双击从零启动、正常关闭窗口的实机端口清理。代码请求 565×960，但屏幕空间可能让 Cocoa 缩小；不能宣称尺寸实测通过。

后台已有对应验证，不要重复所有安装或索要密钥。下一步优先在用户允许时退出旧实例，双击桌面 Claudio.app，做上述实机验收并更新记录。

已知未纳入本次修复：npm 报 14 项依赖漏洞（2 moderate / 11 high / 1 critical），没有执行可能破坏兼容性的 audit fix；API.md 中记录的 FM 分批时间戳回跳、会话隔离等原有设计/问题未改。

## GitHub 与推送

GitHub CLI 已通过用户设备授权，账号 lhc20070304-creator，凭据在系统 keyring。不需要再索要 Token。第一次授权发生网络 EOF，第二次成功；macos 已推送，master 未变。
最近功能提交：`99b6dce`（生命周期/后台回归），`3c51dbb`（Bundle 身份），`aa58516`（Dock 图标）。
当前交接文档提交后会再推送 macos；以 `git status -sb`、`git log -1` 为准。
