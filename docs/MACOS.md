# Claudio · macOS 移植指南

> 这份文档写给 **Mac 上的 agent**，以及准备在 Mac 上跑这个项目的人。
>
> 本仓库当前是 **Windows 版本**（Windows 11 上开发和验证）。
> macOS 版本需要你基于本文 + [API.md](API.md) 搭建。
> 后端（Flask / AI / 网易云）**几乎不用改**，真正要做事的只有桌面壳和三处平台分支。

---

## 1. 先理解架构：三个进程

Claudio 不是单进程应用。启动后一定有 3 个进程同时活着：

```
┌─────────────────────────────────────────────────────┐
│ ① NeteaseCloudMusicApi   Node.js   :3000            │
│    网易云音乐 API 的本地镜像（npm 依赖，纯 JS）        │
│    services/music.py 通过 http://localhost:3000 调它  │
└─────────────────────────────────────────────────────┘
                       ↑ HTTP
┌─────────────────────────────────────────────────────┐
│ ② Flask 后端             Python    :8080            │
│    app.py · 22 个 HTTP 接口 + 1 个 WebSocket         │
│    依赖 ① 才能搜歌/拿播放直链                          │
└─────────────────────────────────────────────────────┘
                       ↑ HTTP + WS
┌─────────────────────────────────────────────────────┐
│ ③ 桌面窗口              pywebview                   │
│    desktop.py 起一个无边框置顶窗口，加载                │
│    http://127.0.0.1:8080?desktop=1                  │
│    窗口里跑的就是 ② 返回的单页前端                     │
└─────────────────────────────────────────────────────┘
```

**启动顺序必须是 ① → ② → ③。** `desktop.py:main()` 已经把这个顺序和
端口就绪等待写好了（`wait_port()` 轮询 3000 和 8080）。

> 如果只想验证后端，不想要窗口：`bash start.sh` 会起 ① 和 ②，
> 然后用浏览器打开 `http://localhost:8080` 即可。**这是 macOS 上最快的兜底方案**，
> `start.sh` 本来就是 bash，不需要改。

---

## 2. 哪些代码已经跨平台（不用动）

以下目录/文件是纯 Python / JS / HTML，**没有任何 Windows 依赖**，直接可用：

| 路径 | 说明 |
|------|------|
| `app.py` | Flask 主服务器，22 个路由 + WS |
| `brain/` | 大脑：多模型适配、prompt 组装、SQLite、品味蒸馏、TTS、意图路由 |
| `services/music.py` | 网易云 API 封装 |
| `prompts/` | DJ 人格等 Markdown |
| `templates/index.html` | 单页前端 |
| `static/` | player.js / style.css / 图片 |
| `user/` | 语料与运行时数据 |
| `brain/tts.py` | 用 `sys.executable` 起子进程，天然跨平台 |
| `brain/state.py` | 用 `os.path` 拼路径，DB 放在项目根 `state.db` |

`app.py` 里唯一的平台相关内容是文件路径，全部用 `os.path.dirname(__file__)`，
没有硬编码盘符。**后端一行都不用改。**

---

## 3. Windows 专有清单

按"必须处理"→"可以忽略"排序。带 ✅ 的表示本仓库已经改好。

### 3.1 ✅ `desktop.py` —— 已做平台守卫

原版在模块顶层 `import ctypes` / `from ctypes import wintypes`，
在 macOS 上**连 import 都会失败**（`ctypes.wintypes` 非 Windows 抛 `ValueError`）。

现在改成：

```python
IS_WIN = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0

if IS_WIN:
    import ctypes
    from ctypes import wintypes
    ...
```

三处平台分支：

| 位置 | Windows 行为 | macOS 行为 |
|------|--------------|------------|
| `nuke_borders()` | DWM 圆角 + 任务栏图标 + 置顶 | 函数第一行 `return`，全跳过 |
| `kill_port()` | `netstat`/`findstr` + `taskkill` | `lsof -ti tcp:<port>` + `kill -9` |
| `webview.start()` | `gui="edgechromium"` | `webview.start()`，pywebview 自动选 Cocoa/WebKit |

`start_netease()` 里的 `creationflags=CREATE_NO_WINDOW` 在 macOS 上等于 `0`，
`subprocess` 接受 —— 注意 POSIX 上这个参数传非 0 值会抛 `ValueError`。

⚠️ **验证状态**：Windows 分支已在本机编译 + 导入验证通过。
**macOS 分支没有在真机上跑过。** 如果窗口起不来，优先检查：

1. `pip show pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit` 是否装上
   （`pip install pywebview` 在 macOS 上应该自动带这些依赖）
2. `frameless=True` + `easy_drag=True` + `on_top=True` 三个参数在 macOS 上是否都支持
   （pywebview 文档说支持，但不同版本行为有差异）
3. 是否有 `pywebview` 版本问题 —— `requirements.txt` 要求 `>=5.0`

### 3.2 ❌ 启动器：`启动Claudio.bat` / `launch.vbs` / `创建桌面快捷方式.bat`

三个都是 Windows 专用，macOS 上**直接忽略，不要删**（Windows 版还要用）。

macOS 需要一个等价物。最小可用版本，存成 `启动Claudio.command`，然后
`chmod +x 启动Claudio.command`，双击即可运行：

```bash
#!/bin/bash
cd "$(dirname "$0")"

# Homebrew / nvm 用户按需添加 PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# node 依赖（NeteaseCloudMusicApi）
if [ ! -d node_modules/NeteaseCloudMusicApi ]; then
  echo "安装 Node 依赖…"
  npm install
fi

# Python 虚拟环境
if [ ! -x .venv/bin/python ]; then
  echo "创建虚拟环境…"
  python3 -m venv .venv
fi

# Python 依赖
if ! .venv/bin/python -c "import webview, flask, flask_sock, edge_tts" 2>/dev/null; then
  echo "安装 Python 依赖…"
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/python desktop.py
```

> 注意：`.venv/bin/python` 是 macOS/Linux 的路径，Windows 是
> `.venv\Scripts\python.exe`。移植时所有启动脚本都要改这个。

如果用户装了 nvm，双击启动时 shell 是非交互的，nvm 的初始化脚本不会被加载，
`node` 会找不到。这种情况下在脚本开头加：

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
```

### 3.3 ⚪ 图标：`Claudio.ico`

Windows 用 `.ico`，macOS 用 `.icns`（或者直接不管，Dock 图标会用 Python 的默认图标）。

- 不影响运行，**可以先跳过**
- 想要好看：把 `Claudio图标.png`（2279×2279）转成 `.icns`，放进 app bundle，
  或者在 `desktop.py` 里用 pyobjc 设 `NSApplication.sharedApplication().setApplicationIconImage_()`

### 3.4 ⚪ `electron/`

`electron/main.js` 是一份**没有被任何启动器调用**的替代桌面壳
（README 里已注明）。macOS 上不用管它。如果 Mac agent 想走 Electron 路线，
它可以作为起点，但 pywebview 路线更省事。

---

## 4. macOS 搭建步骤

### 4.1 前置

- Python **3.10+**（`python3 --version` 确认）
- Node.js **18+**
- 一个 DeepSeek / OpenAI / Anthropic 的 API Key

### 4.2 拉代码

```bash
git clone https://github.com/lhc20070304-creator/Claudio.git
cd Claudio
```

### 4.3 Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` 内容（当前）：

```
flask>=3.0
flask-cors>=4.0
flask-sock>=0.7
requests>=2.31
edge-tts>=7.3.1
pywebview>=5.0
websockets>=12.0
```

> **`edge-tts>=7.3.1` 是硬要求，不要降级。** 见第 5.1 节。

中国网络环境如果 pip 超时，换镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4.4 Node 依赖

```bash
npm install
```

会装三样：`NeteaseCloudMusicApi`（必需）、`dotenv`、`playwright`（**实际上没人用**，
可以不管；想瘦身就在 `package.json` 里删掉再 `npm install`）。

### 4.5 配置文件

```bash
cp config.example.json config.json
```

编辑 `config.json`，填 `deepseek.api_key`（或换 `backend` 用 Claude/OpenAI）。
`config.json` 已被 `.gitignore` 排除，**不会进仓库**。

### 4.6 网易云登录（强烈建议）

没有 `.netease_cookie` 时，搜索能work，但 `/song/url/v1` 很可能返回空直链，
表现是"能搜到歌但放不出声音"。

macOS 上拿 cookie 的方式：

```bash
# 起 API 服务
node node_modules/NeteaseCloudMusicApi/app.js &

# 二维码登录（用手机网易云 App 扫码）
curl http://localhost:3000/login/qr/key
# 拿 key 去生成二维码、轮询状态，最后拿到 cookie 字符串
# 或者直接浏览器访问 http://localhost:3000/login 页面扫码
```

拿到 cookie 后，把完整 cookie 字符串写进项目根目录的 `.netease_cookie`
（单行，无引号）。该文件已被 `.gitignore` 排除。

### 4.7 启动

```bash
python desktop.py
```

或者用第 3.2 节的 `.command` 脚本。

---

## 5. 已知坑（按严重程度）

### 5.1 🔴 edge-tts 版本低于 7.3.1 → TTS 全部 403

2026 年 10 月微软把 Edge Read Aloud 的鉴权 token 升到了 `Sec-MS-GEC v2`，
并把合成端点迁到 `api.msedgeservices.com`。**7.2.8 及以下每个请求都会被 403 拒绝**，
异常是 `WSServerHandshakeError 403`。

症状链：

```
/api/fm/script 正常返回文本 → /api/tts 返回 500 空体 → FM 页只有字没有声音
```

排查：

```bash
pip show edge-tts | grep Version      # 必须 >= 7.3.1
```

这个 bug 已经在 Windows 侧修过，`requirements.txt` 已锁 `>=7.3.1`。
Mac 上除非手动装老版本，否则不会踩。**不要因为"装不上"而降级。**

### 5.2 🟡 `.venv` 不能跨平台复制

Windows 的 `.venv/Scripts/` 和 macOS 的 `.venv/bin/` 结构不同。
`.venv/` 在 `.gitignore` 里，clone 下来本来就没有，**在 Mac 上重新创建即可**。

### 5.3 🟡 端口占用

`desktop.py:main()` 启动时会**杀**掉占用 3000 和 8080 的进程
（`kill_port()`）。macOS 分支用的是 `lsof -ti tcp:<port>` + `kill -9`。

如果 Mac 上有别的东西占这两个端口，会被无提示杀掉。启动前可以自己确认：

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

> macOS 的 **AirPlay 接收器** 默认占 **5000** 端口 —— 本项目不用 5000，不受影响。

### 5.4 🟡 `node` 不在 PATH（nvm 用户）

见 3.2 节。双击 `.command` 启动时 shell 不加载 `~/.zshrc`/`~/.bash_profile`，
nvm 装的 node 会找不到，表现为 `start_netease()` 三次重试全失败 → 进程直接 `sys.exit(1)`。

### 5.5 🟢 TTS 子进程

`brain/tts.py` 每次请求都 `subprocess.run([sys.executable, tts_worker.py, ...])`，
冷启动约 2 秒。macOS 上一样。不是 bug。

### 5.6 🟢 Gatekeeper

如果从压缩包解压而不是 `git clone`，`.command` 可能被 quarantine，
双击提示"无法打开"。解决：右键 → 打开，或 `xattr -d com.apple.quarantine 启动Claudio.command`。

---

## 6. 验收清单

按顺序做，每步都应该通过再进下一步：

```bash
# ① 网易云 API 单独可用
node node_modules/NeteaseCloudMusicApi/app.js &
curl -s "http://localhost:3000/search?keywords=jay&limit=3" | head -c 300
# → 期望：{"result":{"songs":[...]}}

# ② Flask 能起
python app.py &
curl -s http://127.0.0.1:8080/api/taste | head -c 200
# → 期望：{"routines":"...","taste":"..."}

# ③ 推荐链路通（会真的调 LLM + 搜歌）
curl -s http://127.0.0.1:8080/api/next | head -c 500
# → 期望：{"next":[{"id":...,"url":"http://..."}],"say":"..."}
# 如果 next 是空数组：多半是没有 .netease_cookie，拿不到播放直链

# ④ TTS 出声
curl -s -D /tmp/h.txt "http://127.0.0.1:8080/api/tts?t=hello%20world" -o /tmp/t.mp3
ls -l /tmp/t.mp3                      # → 应该 > 10 KB
grep -i x-word-boundaries /tmp/h.txt  # → 应该有 header，值是 JSON 数组

# ⑤ 桌面窗口
python desktop.py
# → 期望：无边框置顶窗口，尺寸 565×960，加载出 FM 首页
```

窗口起来后，在前端功能层面确认：

- [ ] 左上角头像单击最小化、右键退出（`WindowAPI.minimize/quit` 是 pywebview 的 `js_api`）
- [ ] 聊天发一句话，DJ 回英文
- [ ] 点"下一首"，能出歌并且能出声
- [ ] FM 页有播报文本，且**有声音、逐词高亮跟着走**
- [ ] 点喜欢，`user/liked.md` 出现新行

---

## 7. 移植时不要动的东西

- **不要在 macOS 版里改 `prompts/dj-persona.md` 的语言规则。** DJ 说英文是产品设定。
- **不要把 FM 页的中英双语改成单语。** `/api/fm/script` 生成"英文原文 + 中文翻译"
  是设计，不是 bug。
- **不要降级 `edge-tts`。**
- **不要把 `config.json`、`state.db`、`.netease_cookie`、`user/liked.md` 提交进 git。**
  `.gitignore` 已经排除了，别去掉。

---

## 8. 下一步（可选优化）

移植跑通之后，这些是 Windows 版也知道、但没做的：

| 优先级 | 事项 | 位置 |
|--------|------|------|
| 高 | 抽出 `/api/chat` 和 `/stream` 的重复推荐逻辑 | `app.py:224` 与 `app.py:310` |
| 中 | FM 转录区时间戳分批回跳 | `app.py:652`，见 API.md 2.8 |
| 中 | 把"当前播放的歌"注入 LLM 上下文 | `brain/context.py`，这样"这首歌讲什么"才有指代 |
| 低 | `import re` / `import json` 未使用 | `brain/router.py:2`、`brain/taste.py:2` |
| 低 | `playwright` 死依赖 | `package.json:17` |
