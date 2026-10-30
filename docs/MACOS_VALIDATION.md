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
