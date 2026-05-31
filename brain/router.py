"""ROUTER.PY · 意图分流 — 仅控制指令直连 · 其余全走 AI"""
import re


# 纯控制指令 → 直接执行，不经过 AI（只保留播放控制）
CONTROL_COMMANDS = {
    "停止": {"action": "stop", "say": ""},
    "暂停": {"action": "pause", "say": ""},
    "播放": {"action": "resume", "say": ""},
    "下一首": {"action": "next", "say": ""},
    "跳过": {"action": "next", "say": ""},
    "切歌": {"action": "next", "say": ""},
    "上一首": {"action": "prev", "say": ""},
}


def route(user_input: str) -> dict:
    """分流用户输入 → 控制指令 / 自然语言（全部走 AI）"""
    text = user_input.strip()

    # 精确匹配控制指令
    for cmd, response in CONTROL_COMMANDS.items():
        if text == cmd:
            return {"type": "direct", "payload": response}

    # 其余所有输入 → 走 AI
    # 不再用正则拦截点歌、推荐、问候 —— 让 AI 自己理解
    return {"type": "chat", "payload": {"message": text}}
