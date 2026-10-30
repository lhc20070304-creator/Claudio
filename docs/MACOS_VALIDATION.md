# macOS 搭建记录（2026-10-30）

在 Apple Silicon Mac 上搭建；Windows 文件和后端保持不变，改动位于 `macos` 分支。

## 环境与启动

本次通过现有 Homebrew 安装 Python 3.12.16 和 Node.js 22.23.4。
Python 依赖位于项目 `.venv`，包含 edge-tts 7.3.1、pywebview 6.2.1、
PyObjC Core / Cocoa / WebKit 12.2.2。`pip check` 通过。

`启动Claudio.command` 现在识别 Apple Silicon / Intel Homebrew 的
Python 3.12 与 Node 22 版本化路径；找不到 Node 时加载 nvm；启动前检查
Python >=3.10、Node >=18、npm 和虚拟环境版本，并检查 edge-tts 最低版本。
错误会显示原因。脚本保持 LF 和可执行权限。

完整 `npm install` 在下载开发依赖 Electron 时超时；当前 pywebview 壳
不使用 Electron，因此 Mac 启动器改用 `npm install --omit=dev`，安装成功。
package.json、package-lock.json 及 Electron 配置未修改。
若要单独使用 Electron 替代壳，仍需完整安装开发依赖。

首次配置：复制 `config.example.json` 为 `config.json`，填入自己的 API Key，
完成网易云扫码登录并将 Cookie 保存到 `.netease_cookie`。二者均由 Git 忽略。
之后可运行 `./启动Claudio.command`，或双击该文件。

## 已验证

- 网易云 `/search?keywords=jay&limit=3` 返回 3 首歌曲。
- Flask `/api/taste` 返回 taste、routines 字段。
- 网易云扫码登录返回 803，Cookie 已保存在本地忽略文件。
- `/api/next` 返回 3 首推荐，全部含 http 播放地址，DJ 文本为英文。
- `/api/tts?t=hello%20world` 返回 200、11952 字节 MP3，响应头含
  hello / world 两个逐词时间戳。
- `python desktop.py` 及 `./启动Claudio.command` 都加载了桌面页面。
- 原生窗口截图确认无标题栏、圆角；界面显示歌曲、英文 DJ 文本及
  已推进到 0:06 的播放进度。未直接验证扬声器音频输出。
- 启动脚本语法检查通过；最小 PATH 下能解析 Python、Node 和 npm。
- 用户要求暂不打开应用后已停止验证进程，3000 / 8080 均无监听。

## 尚未完成的验收

用户要求暂不打开应用，因此以下项目留待允许再次启动后验证：

- 565×960 实际窗口尺寸、置顶和拖动行为（代码参数已存在，未逐项实测）。
- 头像单击最小化、右键退出。
- 手动发送聊天消息后英文回复。
- 点击下一首并确认声音输出。
- FM 英中双语文本、实际声音与逐词高亮同步。
- 点击喜欢后 user/liked.md 新增行。
- 从无依赖状态双击启动器自动安装并启动。
- 正常关闭窗口后的端口释放回归（停止测试进程后的释放已确认）。

没有在 Windows 真机上重新验证；Windows 启动器、图标、桌面分支、
后端、人格语言规则与 FM 双语逻辑均未修改。

npm 安装报告 14 项依赖漏洞（2 moderate、11 high、1 critical）；
本次未执行可能升级破坏兼容性的 audit fix，依赖审计另行处理。

## 后续回归（进行中）

更新时间：2026-10-30 13:27:46（Asia/Shanghai）。

- 已在实际原生窗口确认应用名称、窗口标题和菜单均为 Claudio。
- 已通过窗口发消息并收到英文回复；自动输入中文时仅标点被录入，完整中文消息另用后台接口验证，不能算中文界面输入通过。
- 用户要求后台完成：停止前台 UI 操作，不切换窗口、不播放测试声音。
- FM 双语/TTS、WebSocket 聊天、收藏写入和进程清理后台检查进行中。
- 上述未完成验收清单仍然有效，后续结果逐项追加。

### 后台进展 · 13:29（Asia/Shanghai）

- WebSocket `/stream` 完整中文输入成功，返回英文问候（真实 DeepSeek）。
- `/api/fm/script` 返回 7 行英中双语文本。
- 首句 TTS 返回 21744 字节 MP3、8 个逐词时间戳；offset 有序，duration 为正。仅验证音频数据，未播放声音。
- 发现 macOS 旧退出流程只清理原 Node 进程，watchdog 重启后的进程可能残留；正在增加独立生命周期管理与自动化回归。

### 后台进展 · 13:32（Asia/Shanghai）

- 独立副本从无 `.venv` / `node_modules` 状态自动安装依赖成功；最小 PATH 环境通过，pip check 通过。最终启动替换为无窗口检查，因此这不是 Finder 双击 GUI 验证。
- 独立副本测试 `/api/like`、`/api/liked`、`/api/unlike` 与 `user/liked.md` 写入/删除通过；流派分类 LLM 使用桩，未修改个人收藏。
- 5 项 macOS 生命周期测试通过：Node 启动失败快速报告、Flask 加载失败清理、占用端口保护、Node 重启后清理和 WebSocket、启动超时清理。
- JavaScript 逻辑测试通过：Mac 单击最小化、Windows 原双击最小化、右键退出绑定；FM 高亮跟随音频时钟，覆盖静音开头、暂停、延迟帧和结束清理。测试使用模拟时钟，不等同于真实声音与视觉同步验收。
- 文档要求头像单击，原共享前端实际为双击；现在由 macOS 专用 `macos/window.js` 补齐单击行为，不改变共享前端或 Windows 行为。
- GitHub 网络已恢复，最终检查后重试推送。

### 后台回归阶段完成 · 13:35:22（Asia/Shanghai）

- 真实 Node + Flask 在隔离随机端口启动成功，搜索、taste、WebSocket 暂停指令通过；停止后两个端口均释放。
- 共 6 项 Python 自动化测试通过，包含正常窗口关闭/窗口创建或事件循环失败的清理路径（窗口桩，不打开 GUI）。
- 新一轮 `/api/next` 返回 3 首歌曲；全部播放地址响应 HTTP 206、audio/mpeg，各读取 4096 字节成功。未播放出声。
- 已修复：macOS 退出清理持有当前 Node（包括 watchdog 重启后的实例）；显式关闭 Flask；启动异常打印原因；端口冲突不杀其他进程；头像单击最小化。
- 已核对 `app.py`、`brain/`、`services/`、`prompts/`、Windows 启动器和图标与 master 无差异。Windows 真机未实测。
- 当前运行实例未重启，仍是旧代码；新修复下次重新打开 Claudio.app 生效。

当前验收边界：后台可验证项目已通过；用户要求不占用主页面，因此未将以下项目标为完成：真实鼠标单击/右键、窗口拖动/置顶及实际尺寸、扬声器出声、FM 视觉与声音同步、Finder 双击从零启动。已有对应按钮/高亮逻辑和自动安装检查，但它们不能代替这些实机观感确认。

Git 状态：本次修复提交 `99b6dce` 与后续记录已成功推送到远端 `macos` 分支。GitHub 登录账号为仓库所有者，master 未修改。

### 推送完成 · 2026-10-30 13:48:42（Asia/Shanghai）

GitHub 授权成功，远端 macos 分支已创建并设置跟踪。后台修复已交付；前述真实声音和界面观感验收仍待用户允许前台操作后完成，不能因推送成功视为全部验收通过。

## Claude Code 交接 · 2026-10-30 13:50:35（Asia/Shanghai）

用户因额度即将用尽要求交接，暂停继续改动。完整接手说明见 `docs/HANDOFF_CLAUDE_CODE.md`：含实际路径、macos 分支、应用包装、验证命令、已通过项目和未完成实机验收。后台修复已推送；本次仅补交接文档，不重启应用、不新增功能。
