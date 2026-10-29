# Claudio · API 参考

后端是一个 Flask 应用，默认监听 `http://127.0.0.1:8080`。
所有接口只对本机开放（`host="127.0.0.1"`），没有鉴权、没有 API 版本号。

本文档描述**当前代码实际行为**，不是设计意图。移植或重写时以本文为准。

---

## 0. 会话模型（先读这一节）

Claudio 的记忆以 `session_id`（下称 `sid`）为键，存在 SQLite 的 `messages` /
`plays` / `likes` 表里。`sid` 有两种来源，**两条链路互不相通**：

| 链路 | sid 来源 | 说明 |
|------|----------|------|
| HTTP（`/api/*`） | Flask signed cookie，`_sid()` 首次访问生成 8 位 uuid 前缀 | 浏览器/WebView 持久化 cookie，重启后仍在 |
| WebSocket（`/stream`） | **每次连接** 重新 `uuid4()[:8]` | 与 HTTP 侧完全不共享记忆 |

也就是说：通过 `/api/chat` 说过的话，不会出现在 `/stream` 的上下文里，反过来也一样。
这是当前实现的已知行为，不是 bug 报告；移植时保持原样即可，若要统一需要自己改。

`/api/next` 的防重复用的是**全局**播放记录（跨所有 session），不受上述隔离影响。

---

## 1. 数据模型

### `Song`（搜索结果）

```jsonc
{
  "id": 2058264497,          // int，网易云歌曲 ID
  "name": "Some Song",
  "artist": "Artist A, Artist B",  // 多位艺人用 ", " 连接
  "album": "Album Name",
  "cover": "https://p1.music.126.net/....jpg"
}
```

### `Song`（`/api/next` 返回体，注意差异）

```jsonc
{
  "id": 2058264497,
  "name": "Some Song",
  "artist": "Artist A",
  "cover": "https://...",
  "url": "http://m8.music.126.net/....mp3",   // 已解析的播放直链
  "reason": "为什么放这首"                      // DJ 给的理由
}
```

`/api/next` 的歌曲对象**没有 `album`**，但多了 `url` 和 `reason`。

### `Song`（`/api/chat` 返回体）

```jsonc
{
  "id": 2058264497,
  "name": "Some Song",
  "artist": "Artist A",
  "album": "Album Name",
  "cover": "https://...",
  "url": "http://m8.music.126.net/....mp3"
}
```

`/api/chat` 的歌曲对象**没有 `reason`**（理由在响应的顶层字段）。

### `PlayRecord` / `LikeRecord`

```jsonc
{ "song_name": "Some Song", "artist": "Artist A", "song_id": 2058264497 }
```

### `Action` 枚举

| 值 | 含义 | 谁产生 |
|----|------|--------|
| `"play"` | 播放返回的 `songs` | `/api/chat`、`/stream` |
| `"say"` | 只说话，不播放 | `/api/chat`、`/stream` |
| `"stop"` / `"pause"` / `"resume"` / `"next"` / `"prev"` | 播放器控制 | `brain/router.py` 的直连指令 |
| `"none"` | 出错了 | `/stream` 的异常兜底 |

---

## 2. HTTP 接口

### 2.1 页面

#### `GET /`

返回 `templates/index.html`。

| 参数 | 类型 | 说明 |
|------|------|------|
| `desktop` | `"1"` \| 缺省 | 桌面壳启动时传 `?desktop=1`，模板据此切换窗口模式样式 |

---

### 2.2 播放与推荐

#### `GET /api/now`

当前 session 最近播放的一首。

```json
{ "playing": { "song_name": "Some Song", "artist": "Artist A", "song_id": 2058264497 } }
```

没有播放记录时 `"playing": null`。

> 前端目前**不调用**这个接口。

#### `GET /api/next`

让 DJ 推荐 3 首歌并直接解析出可播放直链。这是播放器的核心接口。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `weather` | string | `""` | 注入 system prompt 的天气描述，前端目前不传 |

**响应**

```jsonc
{
  "next": [ /* Song（/api/next 形态），最多 3 首，解析失败的会被丢弃 */ ],
  "mood": "",          // 先取 LLM 的 segue，没有则取 reason
  "say": "DJ 说的话",
  "source": "ai"
}
```

**服务端流水线**（`app.py:67`）

1. 拼 system prompt（人格 + 品味 + 时间 + 最近播放 + 历史）
2. 拉全局最近 40 首 → 写进 prompt 的 avoid list
3. 拉 7 天内播放次数 ≥3 的歌 → 写进 prompt 的 overplayed 警告
4. 读取 `prefs.last_recommended_genres` → 要求风格轮换
5. `brain.ask()` 返回 `{"say", "play":[{"keyword","reason","genre"}]}`
6. 逐个 `keyword` 调网易云搜索（limit 5），在结果里挑第一个**不在黑名单**的
7. 调 `/song/url/v1` 拿直链，拿不到就跳过该首
8. 成功一首就 `state.add_play()`

前端调用：`static/player.js:138`。

---

### 2.3 对话

#### `POST /api/chat`

```jsonc
// 请求
{ "message": "放点安静的", "weather": "rainy" }   // weather 可选
```

**响应**

```jsonc
{
  "reply": "DJ 的回复",
  "action": "play",              // "play" | "say"，或直连指令的 action
  "songs": [ /* Song（/api/chat 形态） */ ],
  "reason": "",
  "segue": ""
}
```

**分支逻辑**

1. `brain.router.route()` 先做精确匹配：`停止` `暂停` `播放` `下一首` `跳过`
   `切歌` `上一首` —— 命中则**完全不调 LLM**，直接返回
   `{"reply": <该指令的 say>, "action": <该指令的 action>}`，
   **响应里没有 `songs` / `reason` / `segue` 字段**。
2. 否则：写 user 消息进 DB → 拼 system prompt → 按关键词判断 `is_play` /
   `is_add`（`"play "`、`"放"`、`"播"` / `"add "`、`"queue"`、`"添加"`、`"加点"`）
   选不同的 user prompt → `brain.ask(history=最近30条)` → 写 assistant 消息 →
   搜索 + 解析直链 → 返回。

前端目前**不调用**这个接口（走 WebSocket），它主要给 `smoke.py` 和 curl 调试用。

---

### 2.4 音乐库（网易云）

对 `http://localhost:3000`（NeteaseCloudMusicApi）的薄封装，见 `services/music.py`。

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| GET | `/api/netease/playlists` | — | `{"playlists": [{id,name,cover,count}]}` |
| GET | `/api/netease/playlist/<pl_id:int>` | `?limit=50` | `{"songs": [Song]}` |
| GET | `/api/netease/daily` | — | `{"songs": [Song + reason]}`，首首会预取 `url` |
| GET | `/api/netease/login_status` | — | `{"logged_in": bool}` |
| GET | `/api/music/search` | `?q=<关键词>` | `[Song]`；`q` 为空返回 `[]` |
| GET | `/api/music/url/<song_id:int>` | — | `{"url": str\|null, "fallback": str\|null}`（fallback 是 lossless 重试） |
| GET | `/api/music/detail/<song_id:int>` | — | `{id,name,artist,album,cover,duration}`；失败返回 `{}` |

`/api/netease/playlists`、`/api/netease/playlist/<id>`、`/api/netease/daily`、
`/api/netease/login_status`、`/api/music/search`、`/api/music/url/<id>`、
`/api/music/detail/<id>` —— **前端都不调用**。
歌单/每日推荐的整条链路目前只能手动 curl 触发。

---

### 2.5 品味档案

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| GET | `/api/taste` | — | `{"taste": "前 500 字", "routines": "前 500 字"}` |
| POST | `/api/taste/analyze` | — | `{"ok": true, ...}`，失败 `{"ok": false, "error": "..."}` + 500 |
| POST | `/api/taste/import_apple` | `{"extract_dir": "/path/to/apple-music-export"}` | `{"ok": true, ...}` |

- `/api/taste` 只读 `user/taste.md` 和 `user/routines.md` 的前 500 字符。
- `/api/taste/analyze` 从网易云歌单蒸馏品味档案，会**覆盖** `user/taste.md`。
- `/api/taste/import_apple` 导入 Apple Music 导出的目录，同样会覆盖。

前端不调用前两个；`import_apple` 是 macOS 上唯一比 Windows 更好用的入口。

---

### 2.6 收藏

| 方法 | 路径 | 请求体 | 响应 |
|------|------|--------|------|
| POST | `/api/like` | `{"song_name","artist","song_id"}` | `{"ok": true}` |
| POST | `/api/unlike` | `{"song_id"}` | `{"ok": true}` |
| GET | `/api/likes` | — | `{"likes": [PlayRecord]}` |
| GET | `/api/liked/<song_id:int>` | — | `{"liked": bool}` |

`POST /api/like` 除了写 DB，还会：
1. 调一次 LLM 让模型用 1–2 个词返回流派
2. 把 `- Artist — Song  [genre]` 追加进 `user/liked.md`（按 artist+song 去重）

`POST /api/unlike` 会删 DB 行，然后**从 DB 整体重建** `user/liked.md`
（此时流派标签会丢失）。

前端调用：`/api/liked/<id>`、`/api/like`、`/api/unlike`（`player.js:284,359,362,391,394`）。

---

### 2.7 计划

#### `GET /api/plan/today`

```json
{
  "day": "2026-10-30",
  "plan": null,
  "schedule": [
    { "time": "07:00", "event": "morning-plan" },
    { "time": "09:00", "event": "morning-broadcast" },
    { "time": "hourly", "event": "mood-check" }
  ]
}
```

`plan` 读 `plan` 表，但**没有任何代码往里写**，永远是 `null`。
`schedule` 是硬编码的展示用常量。前端不调用。

---

### 2.8 FM 电台脚本

#### `GET /api/fm/script`

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `song` | string | `""` | 当前播放的歌，会注入 prompt |
| `weather` | string | `""` | 同 `/api/next` |
| `n` | int | `0` | 前端传入的**累计行号**，只用于 prompt 文本 |

**响应**

```jsonc
{
  "title": "本期电台标题",
  "subtitle": "副标题",
  "song": "当前歌曲名或空串",
  "lines": [
    { "en": "English line, 6-12 words", "zh": "中文翻译", "time": "0:00" },
    { "en": "...", "zh": "...", "time": "0:05" }
  ]
}
```

**时间戳算法**（`app.py:652`）：

```python
sec = 0                                  # ← 每次请求都从 0 重新开始
for line in lines:
    dur = max(4, min(10, len(en.split()) * 0.7))
    line["time"] = f"{sec//60}:{sec%60:02d}"
    sec += dur
```

⚠️ **已知缺陷**：`n` 被写进 prompt 但**没有参与时间戳计算**。前端分批请求
（每次追加几行）时，第二批的时间戳又从 `0:00` 开始，转录区会出现
`0:43 → 0:20` 的回跳。修法有两种，任选其一：

- 服务端把 `n` 折算成起始秒数再累加；或
- 前端自己按行号重算时间戳，服务端不再返回 `time`。

前端调用：`player.js:1101`（带 `?t=<cachebuster>&n=<fmLineCount>&song=<urlencoded>`）。

---

### 2.9 TTS

#### `GET /api/tts`

| 参数 | 类型 | 说明 |
|------|------|------|
| `t` | string | 要朗读的文本，必填 |

**成功**：`200`，`Content-Type: audio/mpeg`，响应体是 MP3 字节流。

额外响应头：

```json
X-Word-Boundaries: [{"text":"Some","offset":1030000,"duration":3500000}, ...]
```

> `offset` / `duration` 是 **100 纳秒（ticks）** 单位，除以 `1e7` 得到秒。
> 由 `brain/tts_worker.py` 请求 edge-tts 的 `boundary="WordBoundary"` 得到。
> 前端用它驱动 FM 页的逐词高亮。

**失败**：`500`，**空响应体**（不返回错误信息）。`t` 为空返回 `400` 空体。

实现细节：`brain/tts.py` 用 `sys.executable` **起子进程**跑
`brain/tts_worker.py`（避免 edge-tts 的 asyncio 事件循环和 Flask 冲突），
音频写进 `tempfile.mkstemp()` 出来的临时文件，响应关闭时删除。

前端调用：`player.js:856,987`。

---

## 3. WebSocket `/stream`

`flask_sock`，路径 `/stream`，**无鉴权**。

### 3.1 客户端 → 服务端

**打招呼**（连接后前端立即发，见 `player.js:463`）

```json
{ "message": "", "greet": true, "weather": "" }
```

服务端从 8 条开场白风格提示里随机选一条，让 LLM 生成 1–3 句问候，`play` 字段留空。

**普通消息**

```json
{ "message": "放点安静的", "weather": "" }
```

### 3.2 服务端 → 客户端

```json
{
  "reply": "DJ 的回复",
  "action": "play",
  "songs": [ /* Song（/api/chat 形态） */ ],
  "reason": "",
  "segue": ""
}
```

- 问候响应只有 `{reply, action:"say", songs:[]}`，没有 `reason` / `segue`。
- 直连指令响应只有 `{reply, action}`，**没有 `songs`**。
- 异常兜底：`{"reply": "Signal lost… <前40字符>", "action": "none"}`。

### 3.3 与 `/api/chat` 的关系

`ws_stream` 是 `/api/chat` 的**复制粘贴版本**：prompt 拼装、防重复黑名单、
搜索、解析直链、返回结构几乎逐行相同，只是多了打招呼分支和
`ws_debug.log` 调试写入。改其中一边时**必须同步改另一边**。

> 移植建议：抽一个 `_recommend(sid, user_input, weather, history)` 出来给两边共用。
> 这是这个项目里最值得顺手做掉的重复代码。

---

## 4. 前端实际使用的接口

只有这 7 个（`static/player.js`）：

| 接口 | 位置 |
|------|------|
| `GET /api/next` | `player.js:138` |
| `GET /api/liked/<id>` | `player.js:284` |
| `POST /api/like` | `player.js:362,370,394` |
| `POST /api/unlike` | `player.js:359,391` |
| `WS /stream` | `player.js:456` |
| `GET /api/tts` | `player.js:856,987` |
| `GET /api/fm/script` | `player.js:1101` |

其余接口是给调试、curl、`smoke.py` 和未来功能留的。移植时**可以完全不实现**
未列出的接口而不影响界面 —— 但建议保留，删掉要改 `app.py`。

---

## 5. 外部依赖接口

### NeteaseCloudMusicApi（Node，端口 3000）

`services/music.py` 只用到这几个：

| 上游路径 | 用途 |
|----------|------|
| `GET /search?keywords=&limit=` | 搜歌 |
| `GET /song/url/v1?id=&level=standard\|lossless` | 播放直链 |
| `GET /song/detail?ids=` | 歌曲详情 |
| `GET /lyric?id=` | 歌词（当前无调用方） |
| `GET /user/account?cookie=` | 用 cookie 换 uid |
| `GET /user/playlist?uid=&cookie=` | 用户歌单 |
| `GET /playlist/track/all?id=&limit=` | 歌单内歌曲 |
| `GET /recommend/songs` | 每日推荐 |
| `GET /likelist?uid=` | 喜欢列表（当前无调用方） |

base URL 硬编码为 `http://localhost:3000`（`services/music.py:12`）。
cookie 从项目根目录 `.netease_cookie` 读取，缺失时大部分接口仍可用，
但 `/song/url/v1` 很可能返回空直链（未登录拿不到音源）。

### LLM（DeepSeek / Claude / OpenAI）

`brain/claude.py` 读 `config.json` 的 `backend` 字段选后端：

| backend | URL | 默认 model |
|---------|-----|-----------|
| `deepseek` | `{base_url}/chat/completions` | `deepseek-chat` |
| `claude` | `{base_url}/v1/messages` | `claude-sonnet-4-6` |
| `openai` | `{base_url}/v1/chat/completions` | `gpt-4o` |

`brain.ask()` 期望模型返回 JSON；解析失败时走容错分支（见 `brain/claude.py`）。
