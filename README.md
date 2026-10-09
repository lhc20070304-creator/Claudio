# Claudio · Personal AI Music Radio

> 🎧 24 小时私人 AI 音乐电台 — 一个懂你品味、记得你故事的桌面 DJ

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-backend-black)
![AI](https://img.shields.io/badge/AI-DeepSeek-purple)

---

## 🎵 一句话

像个在电脑角落常驻的深夜电台 DJ，自动根据时间、天气和你的品味播放音乐。想换歌时聊一句就行。

---

## ✨ 核心能力

### 🗣️ 自然语言控制
| 能力 | 示例 |
|------|------|
| 基础指令 | "放点安静的" "换一首" "添加这首歌" |
| 模糊搜索 | "找写代码的 BGM" "适合下雨天的歌" |

### 🧠 品味引擎
| 能力 | 说明 |
|------|------|
| 时段感知 | 当前时间/月份注入 System Prompt，配合日常节律切换风格 |
| 心境判断 | "我有点低落" → 按情绪规则选择陪你沉或把你拉出来 |
| 防重复推荐 | 跨 session 去重 + 7 天内高频歌曲降权 + 强制风格轮换 |
| 品味蒸馏 | 分析网易云歌单 / Apple Music 数据 → AI 生成品味档案 |

### 🎙️ DJ 人格化
| 能力 | 说明 |
|------|------|
| DJ 口吻 | 温柔文艺，像深夜电台主持人 |
| 推荐理由 | 每次推歌附带"为什么" |
| 对话记忆 | SQLite 持久化，跨重启记得聊过什么 |

### 🪽 陪伴体验
| 能力 | 说明 |
|------|------|
| FM 电台 | AI 撰写中英双语电台播报 + TTS 朗读 |
| 收藏与喜欢 | 点赞自动归类风格写回 `user/liked.md`，参与后续推荐 |
| 桌面置顶 | 始终浮在屏幕一角，办公时伴在身边 |

---

## 🗺️ 路线图

以下能力已在设计文档中定义，**当前版本尚未实现**：

- [ ] **歌曲介绍与歌曲故事** — 把当前播放曲目的歌词/元数据接入对话上下文（`music.get_lyric()` 已写好但尚未接入）
- [ ] **天气联动** — 雨天推荐爵士、晴天推荐 Bossa Nova（后端已预留接收字段，缺前端天气来源）
- [ ] **历史回响** — "这是你 2018 年冬天常听的"（需要按年/季节的历史查询）
- [ ] **场景模式** — "写代码模式"一键切换风格预设
- [ ] **音乐日记** — AI 生成每日听歌小结
- [ ] **词级时间戳** — TTS 逐词高亮（现为整句播报）

---

## 🏗️ 技术架构

```
┌──────────────────────────────────────────┐
│  桌面窗口 (pywebview)                     │
│  ├── HTML/CSS/JS 单页前端                 │
│  ├── 播放器 (audio API / 队列 / 进度)      │
│  ├── 聊天面板 (WebSocket 实时对话)         │
│  └── FM 电台页 (TTS 播报 + 转录)           │
├──────────────────────────────────────────┤
│  Flask 后端 (Python, port 8080)           │
│  ├── /api/chat     AI 对话 (DeepSeek)     │
│  ├── /api/next     AI 推荐下一首           │
│  ├── /api/tts      Edge TTS 语音合成      │
│  ├── /api/taste    品味引擎               │
│  └── /stream       WebSocket 实时通信     │
├──────────────────────────────────────────┤
│  网易云音乐 API (Node.js, port 3000)       │
│  ├── 搜索 / 播放 URL / 歌单 / 每日推荐     │
├──────────────────────────────────────────┤
│  数据层 (SQLite)                          │
│  ├── 对话记忆 / 播放记录 / 收藏 / 偏好     │
└──────────────────────────────────────────┘
```

> **关于桌面壳：** 实际运行的是 **pywebview**（`desktop.py`，由 `启动Claudio.bat` 和 `launch.vbs` 调用）。
> `electron/main.js` 是一份已写完但**未被任何启动器调用**的替代实现，可通过 `npm start` 手动运行。
> 两者都启动同一套后端，只是窗口层不同。

### 前置要求
- **Python 3.10+**
- **Node.js 18+**
- **DeepSeek API Key**（或其他兼容 OpenAI 格式的 API）

### 方式一：一键启动（推荐）

```bash
双击 → 启动Claudio.bat
```

自动完成：Python 虚拟环境 → pip 依赖 → npm 依赖 → 启动

### 方式二：手动启动

```bash
# 1. 安装依赖
pip install flask flask-cors flask-sock requests websockets pywebview edge-tts
cd Claudio && npm install

# 2. 配置 API Key
# 复制 config.example.json → config.json，填入你的 DeepSeek API Key

# 3. 启动网易云 API (port 3000)
node node_modules/NeteaseCloudMusicApi/app.js &

# 4. 启动 Flask (port 8080)
python app.py &

# 5. 启动桌面窗口
python desktop.py
```

### 创建桌面快捷方式

```bash
双击 → 创建桌面快捷方式.bat
```

---

## 🎮 窗口操作

| 操作 | 方式 |
|------|------|
| 🔽 最小化 | 双击左上角头像 |
| ❌ 退出 | 右键左上角头像 |
| 📌 始终置顶 | 自动（点其他地方不消失） |

---

## 📁 项目结构

```
Claudio/
├── 启动Claudio.bat          # 一键启动脚本
├── config.example.json      # 配置模板
├── requirements.txt         # Python 依赖
├── package.json             # Node 依赖
├── app.py                   # Flask 主服务器
├── desktop.py               # 桌面窗口 (pywebview)
├── brain/                   # AI 大脑
│   ├── claude.py            #   多模型适配器 (DeepSeek/Claude/OpenAI)
│   ├── context.py           #   System Prompt 组装
│   ├── state.py             #   SQLite 状态持久化
│   ├── taste.py             #   品味蒸馏引擎
│   ├── apple_import.py      #   Apple Music 数据导入
│   ├── tts.py               #   TTS 语音合成
│   ├── tts_worker.py        #   TTS 子进程（避开 asyncio 冲突）
│   ├── router.py            #   意图路由
│   └── scheduler.py         #   定时任务
├── services/
│   └── music.py             # 网易云 API 封装
├── templates/
│   └── index.html           # 单页前端
├── static/
│   ├── player.js            #   播放器 + 聊天 + FM
│   ├── style.css            #   深色主题样式
│   ├── dot-grid.js          #   背景粒子
│   ├── sw.js                #   Service Worker 离线缓存
│   ├── manifest.json        #   PWA 清单
│   ├── ryan.png             #   DJ 头像
│   └── avatar-user.jpg      #   用户头像（可自行替换）
├── prompts/                 # DJ 人格 Prompt
│   ├── dj-persona.md        #   人设
│   ├── emoji-library.md     #   表情库
│   ├── voice-prompt.md      #   电台播报风格
│   └── avatar-prompt.md     #   头像生成提示词
├── user/                    # 用户语料
│   ├── taste.md             #   音乐品味档案
│   ├── routines.md          #   日常节律
│   ├── mood-rules.md        #   情绪规则
│   └── liked.md             #   点赞记录（运行时生成）
├── electron/
│   └── main.js              # Electron 桌面壳（替代实现，需 npm start 手动运行）
└── ROADMAP.md               # 路线图与设计文档
```

---

## 🤖 AI 协作

本项目全程使用 **Claude Code** 辅助开发：

- `app.py` — Flask 路由设计 + WebSocket + FM 脚本生成
- `brain/claude.py` — 多模型适配层
- `brain/context.py` — 动态 System Prompt 组装
- `brain/taste.py` — AI 品味蒸馏
- `brain/tts.py` — Edge TTS 语音合成
- `services/music.py` — 网易云 API 封装
- `templates/index.html` — HTML 结构
- `static/player.js` — 51KB 播放器逻辑
- `static/style.css` — 22KB 深色主题样式
- `desktop.py` — pywebview 桌面窗口 + DWM

详见 [AI协作报告.md](AI协作报告.md)

---

## 📄 许可证

MIT License
