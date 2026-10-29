# 任务：把 Claudio 从 Windows 版本移植到 macOS

> 这份文件本身就是提示词。在 Mac 上 clone 仓库后，把这个文件的内容整段发给
> 你的 Mac agent（或直接说「读 docs/MACOS_PROMPT.md，按它执行」）。

---

你是一名工程师，任务是把 `Claudio`（一个个人 AI 音乐电台桌面应用）从 Windows 版本
移植到 macOS，并让它在真机上完整跑通。

当前仓库处于 Windows 已验证版本，tag 为 `v1.0-windows`。

---

## 第 0 步 · 先读文档，不要直接改代码

按顺序读：

1. `docs/MACOS.md` —— 架构、Windows 专有清单、已知坑、验收标准
2. `docs/API.md` —— 22 个 HTTP 接口 + 1 个 WebSocket 的完整契约

**读完再动手。** 这两份文档描述了当前代码的真实行为，不是设计意图。

关键背景，三句话：

- 这个应用是**三个进程**：Node 的 `NeteaseCloudMusicApi`（:3000）→ Flask（:8080）→ pywebview 窗口。
- 后端（`app.py` / `brain/` / `services/`）是纯 Python，**没有任何 Windows 依赖，一行都不用改**。
- 需要动的只有：桌面壳 `desktop.py`、启动脚本、图标。

---

## 第 1 步 · 环境确认

```bash
python3 --version    # 必须 >= 3.10
node --version       # 必须 >= 18
git --version
```

任何一项不满足，先停下来告诉用户装什么，不要自己装系统级工具。

如果用户用 nvm 管理 node，注意：**双击 `.command` 启动时不会加载 `~/.zshrc`**，
node 会找不到。用终端跑就没这个问题。

---

## 第 2 步 · 装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
```

注意事项：

- **`requirements.txt` 里 `edge-tts>=7.3.1` 是硬要求。** 低于这个版本，微软的
  Edge Read Aloud 会对每个请求返回 403，表现是 FM 页只有文字没有声音。
  **不要因为装不上就降级**，装不上就换镜像：
  `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
- macOS 上 `pywebview` 依赖 `pyobjc-core`、`pyobjc-framework-Cocoa`、
  `pyobjc-framework-WebKit`。正常情况下 pip 会自动带上，装完用
  `pip list | grep pyobjc` 确认一下。

---

## 第 3 步 · 配置

```bash
cp config.example.json config.json
```

然后编辑 `config.json`，填 `deepseek.api_key`。

**API Key 必须向用户要。** 不要从仓库里任何文件猜、不要翻历史记录、不要写进
任何会被 git 跟踪的文件。`config.json` 已被 `.gitignore` 排除，填在里面是安全的。

---

## 第 4 步 · 先让后端跑通（这一步不要开窗口）

严格按顺序，**每一项验证通过再进下一项**。失败就修，不要跳过。

### 4.1 网易云 API

```bash
node node_modules/NeteaseCloudMusicApi/app.js &
curl -s "http://localhost:3000/search?keywords=jay&limit=3" | head -c 300
```

期望：返回 `{"result":{"songs":[...]}}`。返回空或报错就先解决这一步。

### 4.2 Flask

```bash
python app.py &
curl -s http://127.0.0.1:8080/api/taste | head -c 200
```

期望：`{"routines":"...","taste":"..."}`。

### 4.3 登录网易云（否则放不出声音）

没有 `.netease_cookie` 时，搜索能用，但 `/song/url/v1` 大概率返回空直链 ——
症状是「搜得到歌、点了没声音」。

在 Mac 上扫码拿 cookie，写进项目根目录 `.netease_cookie`（单行，无引号）。

### 4.4 推荐链路

```bash
curl -s http://127.0.0.1:8080/api/next | head -c 500
```

期望：`"next"` 数组非空，每首都带 `http` 开头的 `url`。

如果 `next` 是空数组 → 回到 4.3，多半是没登录。

### 4.5 TTS

```bash
curl -s -D /tmp/h.txt "http://127.0.0.1:8080/api/tts?t=hello%20world" -o /tmp/t.mp3
ls -l /tmp/t.mp3
grep -i x-word-boundaries /tmp/h.txt
```

期望：mp3 大于 10 KB；响应头里有 `X-Word-Boundaries`，值是 JSON 数组。

如果返回 500 且响应体为空 → `pip show edge-tts` 版本低于 7.3.1。

---

## 第 5 步 · 桌面窗口

```bash
python desktop.py
```

`desktop.py` 已经做了 `IS_WIN` 平台守卫，macOS 分支会跳过 DWM 圆角、
用 `lsof`/`kill` 清理端口、让 pywebview 自动选 Cocoa 后端。

**但这部分没有在真机上验证过。** 以下是排查顺序：

1. `ModuleNotFoundError: webview` → 虚拟环境没激活，或 pywebview 没装上
2. pyobjc 相关报错 → `pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit`
3. 窗口起得来但没有边框/拖不动 → 检查 `create_window()` 里
   `frameless=True`、`easy_drag=True`、`on_top=True` 三个参数在当前的
   pywebview 版本上是否都被支持，逐个试，记录哪个组合能工作
4. 窗口起了但白屏 → 确认 8080 已经起来了（`curl 127.0.0.1:8080`），
   再用 `?desktop=1` 手动在浏览器打开看看前端本身是不是好的
5. 窗口起来但立刻退出 → 看终端输出，多半是 `start_netease()` 或
   `wait_port(8080)` 超时

**如果 pywebview 路线彻底走不通**：降级方案是不做窗口，用 `bash start.sh`
起后端，浏览器打开 `http://localhost:8080`。把这个结果如实告诉用户，
不要假装窗口能用。

---

## 第 6 步 · 启动器与收尾

1. 仓库里已经有 `启动Claudio.command`，确认它可执行：
   ```bash
   chmod +x 启动Claudio.command
   ./启动Claudio.command
   ```
   双击也要能启动。
2. 如果双击报 `bad interpreter: /bin/bash^M`，说明换行符是 CRLF ——
   `.gitattributes` 里已经声明了 `*.command text eol=lf`，
   检查一下 checkout 是否正常。
3. （可选，不影响运行）把 `Claudio图标.png` 转成 `.icns`，让 Dock 图标好看点。

---

## 第 7 步 · 功能回归

窗口起来之后，逐项确认并记录实际结果：

- [ ] 左上角头像单击最小化、右键退出
- [ ] 聊天发一句话，DJ 用**英文**回复
- [ ] 点「下一首」，出歌并且能出声
- [ ] FM 页有播报文本，有声音，**逐词高亮跟着朗读走**
- [ ] 点喜欢，`user/liked.md` 出现新行
- [ ] 关掉窗口，3000 和 8080 两个端口都被释放

---

## 硬性约束（违反任何一条都算没做完）

1. **不要改 `prompts/dj-persona.md` 的语言规则。** DJ 说英文是产品设定，
   不是 bug。用户用中文输入，回复仍然是英文。
2. **不要把 FM 页的中英双语改成单语。** `/api/fm/script` 同时生成英文原文和
   中文翻译，这是设计。
3. **不要降级 `edge-tts`。** 见第 2 步。
4. **不要提交任何密钥或个人数据**：`config.json`、`.env`、`.netease_cookie`、
   `state.db*`、`user/liked.md` 都在 `.gitignore` 里，别去掉。
5. **不要删 Windows 的东西。** `启动Claudio.bat`、`launch.vbs`、
   `创建桌面快捷方式.bat`、`Claudio.ico` 都保留 —— 这个仓库要同时容纳两个平台。
6. **改 `desktop.py` 时保住 Windows 分支。** 所有 Windows 逻辑必须在
   `IS_WIN` 判断之内，不能因为适配 macOS 把 Windows 路径弄坏。
7. **不要用 `sys.exit()` 掩盖启动失败。** 出了问题要打印原因。

---

## 工作方式

- 在分支 `macos` 上干活，不要直接推 `master`
- 一次只改一件事，改完立刻验证
- 任何一步验证失败，先修好再往下，不要攒到最后一起 debug
- 你无法验证的东西（比如「Windows 上还正常吗」），不要声称验证过
- 完成后给一份简短报告：改了哪些文件、每项验证的实际结果、
  哪些是推测、哪些坑还没解决

---

## 完成标准

全部满足才算完成：

1. `python desktop.py` 在 macOS 上开出窗口，尺寸 565×960，无边框，置顶
2. 第 7 步的 6 项功能回归全部通过
3. 双击 `启动Claudio.command` 能从零启动（会自动装依赖）
4. 改动推到了 `macos` 分支，`master` 上的 Windows 版本没有被破坏
