"""CONTEXT.PY · 提示词组装 — taste + routines + 环境 + 历史 → system prompt"""
import os
from datetime import datetime
from brain.state import state

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(path):
    p = os.path.join(BASE_DIR, path)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def build_system_prompt(session_id: str = None, weather: str = "", now: datetime = None) -> str:
    """组装上下文 → system prompt（含持久化对话记忆）"""
    if now is None:
        now = datetime.now()

    # ① DJ 人格
    persona = _read("prompts/dj-persona.md")

    # ② 用户语料
    taste = _read("user/taste.md")
    routines = _read("user/routines.md")
    mood_rules = _read("user/mood-rules.md")
    liked = _read("user/liked.md")
    user_corpus = f"## 用户品味\n{taste}\n\n## 点赞记录（这些是用户明确喜欢的歌，必须记住其风格）\n{liked}\n\n## 日常节律\n{routines}\n\n## 情绪规则\n{mood_rules}"

    # ③ Environment context
    days_en = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    env_lines = [
        f"Current time: {now.strftime('%Y-%m-%d %H:%M')} ({days_en[now.weekday()]})",
        f"Current month: {now.strftime('%B')}",
    ]
    if weather:
        env_lines.append(f"Weather: {weather}")
    env_context = "\n".join(env_lines)

    # ④ Recent plays
    play_lines = ["## Recent Plays (avoid repeating)"]
    if session_id:
        plays = state.get_recent_plays(session_id, limit=10)
        for p in plays:
            play_lines.append(f"- {p['artist']} — {p['song_name']}")
    play_context = "\n".join(play_lines)

    # ⑤ Conversation memory
    memory_context = ""
    if session_id:
        msgs = state.get_messages(session_id, limit=30)
        if msgs:
            mem_lines = ["## Your conversation history"]
            mem_lines.append("Below is your recent conversation. Continue naturally, like old friends. If this is your first chat, greet them warmly.")
            mem_lines.append("")
            for m in msgs:
                role = "Claudio" if m["role"] == "assistant" else "Listener"
                text = m["content"]
                if len(text) > 200:
                    text = text[:200] + "…"
                mem_lines.append(f"- [{role}]: {text}")
            memory_context = "\n".join(mem_lines)

    # ⑥ Emoji library
    emoji_lib = _read("prompts/emoji-library.md")

    return f"""{persona}

---
{emoji_lib}

---
{user_corpus}

---
## Current Environment
{env_context}

---
{play_context}

---
{memory_context}
"""
