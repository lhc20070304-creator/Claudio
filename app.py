"""Claudio · 个人AI音乐电台 · 主服务器
施工图四层架构：
  POST /api/chat · GET /api/now · GET /api/next
  GET /api/taste · GET /api/plan/today · WS /stream
"""
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, send_file
from flask_cors import CORS
from flask_sock import Sock

from brain.state import state
from brain.claude import brain
from brain.context import build_system_prompt
from brain.router import route
from brain.scheduler import scheduler
from services.music import music

app = Flask(__name__)
app.secret_key = "claudio-radio-secret"
CORS(app)
sock = Sock(app)


def _sid():
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())[:8]
        session["sid"] = sid
    return sid


def _history(sid, limit=30):
    """从 state 加载对话历史，转为多轮格式 [(role, content), ...]"""
    msgs = state.get_messages(sid, limit=limit)
    history = []
    for m in msgs:
        role = "assistant" if m["role"] == "assistant" else "user"
        history.append((role, m["content"]))
    return history


# ═══════════════════════════════════════════
# HTTP CONTRACT
# ═══════════════════════════════════════════

@app.route("/")
def index():
    desktop = request.args.get("desktop", "0") == "1"
    return render_template("index.html", desktop=desktop)


@app.route("/api/now")
def api_now():
    plays = state.get_recent_plays(_sid(), limit=1)
    return jsonify({"playing": plays[0] if plays else None})


@app.route("/api/memory/status")
def api_memory_status():
    """检查是否有历史对话记忆"""
    msgs = state.get_messages(_sid(), limit=1)
    return jsonify({"has_history": len(msgs) > 0})


@app.route("/api/next")
def api_next():
    """GET /api/next — AI 根据品味推荐关键词 → 搜索 → 播放（不限于已有歌单）"""
    sid = _sid()
    weather = request.args.get("weather", "")
    now = datetime.now()

    system_prompt = build_system_prompt(sid, weather, now)
    recent = state.get_recent_plays(sid, limit=15)
    avoid = "\n".join(f"- {p['artist']} — {p['song_name']}" for p in recent) if recent else "(no recent plays)"
    days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

    user_prompt = (
        f"Time: {now.strftime('%H:%M')} {days[now.weekday()]}\n"
        f"Recently played (do NOT repeat these artists or songs):\n{avoid}\n\n"
        "Recommend 3 songs as a DJ. The listener has complained that you keep playing similar stuff.\n\n"
        "What to do:\n"
        "- Actually read the ENTIRE taste profile — every style, era, and artist in there is fair game. Don't fixate on one corner of it\n"
        "- Be genuinely unpredictable. If you played R&B last time, go somewhere completely different this time. The listener wants to be surprised\n"
        "- IMPORTANT: Do NOT play loud/aggressive music. No death metal, heavy rock, screamo, hardcore, punk, thrash, or harsh distorted guitars. The listener hates this\n"
        "- keyword must be precise: 'Artist Songname' for specific tracks, or 'genre mood descriptor' for discovery searches\n\n"
        "Output JSON: {\"say\": \"...\", \"play\": [{\"keyword\": \"...\", \"reason\": \"...\"}, ...]}"
    )

    result = brain.ask(system_prompt, user_prompt)

    songs = []
    for p in result.get("play", []):
        if isinstance(p, dict) and "keyword" in p:
            sr = music.search(p["keyword"], limit=3)
            if sr:
                # 优先选第一个结果（通常是最热门/最匹配的），避开最近播放过的
                recent_ids = {r.get("song_id", 0) for r in recent}
                picked = sr[0]  # 默认第一个最准
                for candidate in sr:
                    if candidate["id"] not in recent_ids:
                        picked = candidate
                        break
                url = music.get_song_url(picked["id"])
                if url:
                    songs.append({
                        "id": picked["id"],
                        "name": picked["name"],
                        "artist": picked["artist"],
                        "cover": picked.get("cover", ""),
                        "url": url,
                        "reason": p.get("reason", ""),
                    })
                    state.add_play(sid, picked["name"], picked["artist"], picked["id"])

    return jsonify({
        "next": songs,
        "mood": result.get("segue", "") or result.get("reason", ""),
        "say": result.get("say", ""),
        "source": "ai",
    })


@app.route("/api/netease/playlists")
def api_netease_playlists():
    """GET — 用户的网易云歌单列表"""
    return jsonify({"playlists": music.get_user_playlists()})


@app.route("/api/netease/playlist/<int:pl_id>")
def api_netease_playlist(pl_id):
    """GET — 歌单内歌曲"""
    limit = request.args.get("limit", 50, type=int)
    return jsonify({"songs": music.get_playlist_tracks(pl_id, limit)})


@app.route("/api/netease/daily")
def api_netease_daily():
    """GET — 每日推荐"""
    songs = music.get_daily_recommend()
    # 预取第一首的 url
    if songs:
        songs[0]["url"] = music.get_song_url(songs[0]["id"])
    return jsonify({"songs": songs})


@app.route("/api/netease/login_status")
def api_netease_login_status():
    """GET — 检查网易云登录状态"""
    return jsonify({"logged_in": bool(music.cookie and music._uid)})


@app.route("/api/taste")
def api_taste():
    import os
    d = os.path.dirname(__file__)
    result = {}
    for name, path in [("taste", "user/taste.md"), ("routines", "user/routines.md")]:
        fp = os.path.join(d, path)
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                result[name] = f.read()[:500]
    return jsonify(result)


@app.route("/api/plan/today")
def api_plan_today():
    today = datetime.now().strftime("%Y-%m-%d")
    plan = state.get_plan(today)
    return jsonify({"day": today, "plan": plan, "schedule": [
        {"time": "07:00", "event": "morning-plan"},
        {"time": "09:00", "event": "morning-broadcast"},
        {"time": "hourly", "event": "mood-check"},
    ]})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """POST /api/chat — Context Window 组装 → 模型 → {say,play[],reason,segue}"""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "missing message"}), 400

    sid = _sid()
    user_input = data["message"]
    intent = route(user_input)

    # 控制指令
    if intent["type"] == "direct":
        state.add_message(sid, "user", user_input)
        state.add_message(sid, "assistant", intent["payload"]["say"])
        return jsonify({"reply": intent["payload"]["say"], "action": intent["payload"]["action"]})

    # 自然语言 → AI（点歌、推荐、聊天全部走这里）+ 多轮记忆
    state.add_message(sid, "user", user_input)
    weather = data.get("weather", "")
    system_prompt = build_system_prompt(sid, weather)

    # Detect music intent — OVERRIDE for these commands
    lower = user_input.lower()
    is_play = any(w in lower for w in ["play ", "put on ", "i want to hear", "放", "播"])
    is_add  = any(w in lower for w in ["add ", "queue", "添加", "加点"])
    if is_play:
        user_prompt = f'PLAY COMMAND: {user_input}\n\nReturn JSON with a play array containing the requested song. Example: {{"say":"short DJ intro","play":[{{"keyword":"Artist Songname"}}]}}'
    elif is_add:
        user_prompt = f'ADD COMMAND: {user_input}\n\nReturn JSON with a play array. Current track keeps playing. Example: {{"say":"added!","play":[{{"keyword":"Artist Songname"}}]}}'
    else:
        user_prompt = f"User says: {user_input}\n\nReply in JSON per DJ persona."

    result = brain.ask(system_prompt, user_prompt, history=_history(sid))
    reply = result.get("say", "Hmm… let me think about what to play next.")
    state.add_message(sid, "assistant", reply)

    songs = []
    for p in result.get("play", []):
        if isinstance(p, dict) and "keyword" in p:
            sr = music.search(p["keyword"], limit=3)
            if sr:
                ss = sr[0]
                ss["url"] = music.get_song_url(ss["id"])
                songs.append(ss)
                state.add_play(sid, ss["name"], ss["artist"], ss["id"])

    return jsonify({"reply": reply, "action": "play" if songs else "say",
        "songs": songs, "reason": result.get("reason", ""), "segue": result.get("segue", "")})


# ═══════════════════════════════════════════
# WS /stream
# ═══════════════════════════════════════════

@sock.route("/stream")
def ws_stream(ws):
    sid = str(uuid.uuid4())[:8]
    while True:
        msg = ws.receive()
        if msg is None:
            break
        try:
            data = json.loads(msg)
            user_input = data.get("message", "")
            is_greet = data.get("greet", False)

            # 听众刚打开 Claudio，让 AI 自己打招呼
            if is_greet and not user_input:
                weather = data.get("weather", "")
                system_prompt = build_system_prompt(sid, weather)
                history_msgs = state.get_messages(sid, limit=20)
                import random as _random
                variety_hints = [
                    "Mention the weather or the feeling of this time of day.",
                    "Just say hi — no mention of artists or music.",
                    "Ask how their day has been.",
                    "Share a poetic observation (light, weather, the sound of the night).",
                    "Mention a small interesting thought or anecdote.",
                    "If there's something fun in the chat history, naturally pick up on it.",
                    "Recommend an obscure song (but not one you've recommended before).",
                    "Talk about the current season or month.",
                ]
                hint = _random.choice(variety_hints)
                greet_prompt = (
                    "The listener just opened Claudio Radio. Greet them naturally as a DJ.\n"
                    "1-3 sentences. Don't ask 'what do you want to hear', don't pitch, don't name-drop artists from their taste profile.\n"
                    f"Style suggestion for this greeting: {hint}\n"
                    "Leave the play field empty."
                )
                result = brain.ask(system_prompt, greet_prompt, history=_history(sid))
                reply = result.get("say", "Good evening.")
                state.add_message(sid, "assistant", reply)
                ws.send(json.dumps({"reply": reply, "action": "say", "songs": []}, ensure_ascii=False))
                continue

            intent = route(user_input)

            if intent["type"] == "direct":
                ws.send(json.dumps({"reply": intent["payload"]["say"], "action": intent["payload"]["action"]},
                    ensure_ascii=False))
                continue

            # Natural language → AI (multi-turn memory)
            weather = data.get("weather", "")
            system_prompt = build_system_prompt(sid, weather)
            # Detect music intent — OVERRIDE system prompt for these
            _lower = user_input.lower()
            is_play = any(w in _lower for w in ["play ", "put on ", "i want to hear", "放", "播"])
            is_add  = any(w in _lower for w in ["add ", "queue", "添加", "加点"])
            if is_play:
                user_prompt = f'PLAY COMMAND: {user_input}\n\nReturn JSON with a play array containing the requested song. Example: {{"say":"short DJ intro","play":[{{"keyword":"Artist Songname"}}]}}'
            elif is_add:
                user_prompt = f'ADD COMMAND: {user_input}\n\nReturn JSON with a play array. Current track keeps playing. Example: {{"say":"added!","play":[{{"keyword":"Artist Songname"}}]}}'
            else:
                user_prompt = f"User says: {user_input}\n\nReply in JSON per DJ persona."

            import os as _os2
            _dlog = _os2.path.join(_os2.path.dirname(__file__), "ws_debug.log")
            with open(_dlog, "a", encoding="utf-8") as _f:
                _f.write(f"is_play={is_play} is_add={is_add} input={user_input[:60]}\n")
                _f.write(f"prompt={user_prompt[:200]}\n")
            result = brain.ask(system_prompt, user_prompt, history=_history(sid))
            with open(_dlog, "a", encoding="utf-8") as _f:
                _f.write(f"play={result.get('play', [])} say={result.get('say', '')[:100]}\n\n")
            reply = result.get("say", "")
            state.add_message(sid, "user", user_input)
            state.add_message(sid, "assistant", reply)

            songs = []
            for p in result.get("play", []):
                if isinstance(p, dict) and "keyword" in p:
                    kw = p["keyword"]
                    sr = music.search(kw, limit=3)
                    with open(_dlog, "a", encoding="utf-8") as _f:
                        _f.write(f"search kw={kw} results={len(sr) if sr else 0}\n")
                    if sr:
                        ss = sr[0]
                        url = music.get_song_url(ss["id"])
                        with open(_dlog, "a", encoding="utf-8") as _f:
                            _f.write(f"url for {ss['id']}: {url[:60] if url else 'NONE'}\n")
                        if url:
                            ss["url"] = url
                            songs.append(ss)
                            state.add_play(sid, ss["name"], ss["artist"], ss["id"])

            ws_msg = json.dumps({"reply": reply, "action": "play" if songs else "say",
                "songs": songs, "reason": result.get("reason", ""), "segue": result.get("segue", "")},
                ensure_ascii=False)
            with open(_dlog, "a", encoding="utf-8") as _f:
                _f.write(f"WS sending: action={'play' if songs else 'say'} songs={len(songs)}\n\n")
            ws.send(ws_msg)

        except Exception as e:
            ws.send(json.dumps({"reply": f"Signal lost… {str(e)[:40]}", "action": "none"}, ensure_ascii=False))


# ═══════════════════════════════════════════
# 音乐 API
# ═══════════════════════════════════════════

@app.route("/api/music/search")
def music_search():
    q = request.args.get("q", "")
    return jsonify(music.search(q, limit=10) if q else [])


@app.route("/api/music/url/<int:song_id>")
def music_url(song_id):
    url = music.get_song_url(song_id)
    fallback = music.get_song_url(song_id, level="lossless") if not url else None
    return jsonify({"url": url, "fallback": fallback})


@app.route("/api/music/detail/<int:song_id>")
def music_detail(song_id):
    return jsonify(music.get_song_detail(song_id) or {})


# ═══════════════════════════════════════════
# 收藏 & 喜欢 API
# ═══════════════════════════════════════════

@app.route("/api/like", methods=["POST"])
def api_like():
    data = request.get_json()
    if not data:
        return jsonify({"error": "missing data"}), 400
    sid = _sid()
    song_name = data.get("song_name", "")
    artist = data.get("artist", "")
    song_id = data.get("song_id", 0)
    state.add_like(sid, song_name, artist, song_id)
    _update_liked_md(song_name, artist, song_id)
    return jsonify({"ok": True})


@app.route("/api/unlike", methods=["POST"])
def api_unlike():
    data = request.get_json()
    if not data or "song_id" not in data:
        return jsonify({"error": "missing song_id"}), 400
    sid = _sid()
    state.remove_like(sid, data["song_id"])
    _rebuild_liked_md()
    return jsonify({"ok": True})


def _update_liked_md(song_name, artist, song_id):
    """Append a liked song to user/liked.md with AI genre classification."""
    import os as _os
    liked_path = _os.path.join(_os.path.dirname(__file__), "user", "liked.md")
    _os.makedirs(_os.path.dirname(liked_path), exist_ok=True)

    # Get genre classification from AI
    genre = ""
    try:
        prompt = f"Song: {artist} — {song_name}\n\nWhat genre is this? Reply with ONLY 1-2 words, nothing else. Example replies: R&B, indie rock, jazz, lo-fi, synthpop, hip-hop."
        result = brain.ask(
            "You are a music classifier. Reply with ONLY the genre name. No other text.",
            prompt,
            raw=True
        )
        raw_genre = result.get("say", "") if isinstance(result, dict) else str(result)
        # Clean up — take first line, strip quotes/markdown
        genre = raw_genre.strip().split("\n")[0].strip('"').strip("'").strip()
        if len(genre) > 50:  # Probably an error message
            genre = ""
    except Exception:
        pass

    # Read existing likes
    existing = []
    if _os.path.exists(liked_path):
        with open(liked_path, "r", encoding="utf-8") as f:
            existing = f.read().splitlines()

    # Rebuild with new like
    header = "# Liked Songs — Claudio's Learned Preferences"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_line = f"- {artist} — {song_name}" + (f"  [{genre}]" if genre else "")

    # Inject new line
    lines = [header, f"<!-- Last updated: {now_str} -->", ""]
    found = False
    for line in existing:
        if line.startswith("#") or line.startswith("<!--"):
            continue
        if line.strip() == new_line.strip():
            found = True
        if line.strip():
            lines.append(line)
    if not found:
        lines.append(new_line)

    with open(liked_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _rebuild_liked_md():
    """Rebuild liked.md from database after an unlike."""
    import os as _os
    liked_path = _os.path.join(_os.path.dirname(__file__), "user", "liked.md")
    _os.makedirs(_os.path.dirname(liked_path), exist_ok=True)

    # Query all likes directly
    rows = state.conn.execute(
        "SELECT DISTINCT artist, song_name FROM likes ORDER BY id DESC"
    ).fetchall()

    header = "# Liked Songs — Claudio's Learned Preferences"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [header, f"<!-- Last updated: {now_str} -->", ""]
    for r in rows:
        lines.append(f"- {r[0]} — {r[1]}")
    with open(liked_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


@app.route("/api/likes")
def api_likes():
    sid = _sid()
    return jsonify({"likes": state.get_likes(sid)})


@app.route("/api/liked/<int:song_id>")
def api_is_liked(song_id):
    sid = _sid()
    return jsonify({"liked": state.is_liked(sid, song_id)})


# ═══════════════════════════════════════════
# FM RADIO SCRIPT
# ═══════════════════════════════════════════

@app.route("/api/fm/script")
def api_fm_script():
    """GET — AI 为 FM 电台生成一段播报稿"""
    sid = _sid()
    now = datetime.now()
    weather = request.args.get("weather", "")

    system_prompt = build_system_prompt(sid, weather)
    recent = state.get_recent_plays(sid, limit=5)
    current_song = recent[0] if recent else None
    history_msgs = state.get_messages(sid, limit=15)
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history_msgs)

    frontend_song = request.args.get("song", "")
    song_info = ""
    if frontend_song:
        song_info = f"当前正在播放: {frontend_song}"
    elif current_song:
        song_info = f"当前正在播放: {current_song['artist']} — {current_song['song_name']}"

    import random as _random
    topics = [
        "聊聊最近听到的一首好歌背后的故事或情感",
        "说说现在这个时间段给人的感觉，以及适合听什么样的音乐",
        "分享一段关于音乐人的趣闻或冷知识",
        "聊聊今晚的情绪——安静、思念、松弛，还是期待",
        "谈谈为什么某首歌能让人反复循环",
        "讲一个关于夜晚、城市和音乐的小故事",
        "推荐一张最近在听的专辑，说说它特别在哪",
        "用诗意的语言描述当下的氛围，像深夜电台一样",
        "聊聊音乐和生活的关系——某首歌如何陪伴了某段时光",
        "给听众一些温柔的建议，像老朋友一样",
    ]
    topic = _random.choice(topics)
    line_num = request.args.get("n", 0, type=int)

    user_prompt = (
        f"当前时间: {now.strftime('%H:%M')}，{['周一','周二','周三','周四','周五','周六','周日'][now.weekday()]}\n"
        f"当前是播报的第 {line_num} 行\n"
        f"{song_info}\n"
        f"近期对话:\n{history_text}\n\n"
        f"你是 Claudio，一个深夜电台 DJ。现在你正在 FM 电台上做一段播报。\n"
        f"这是第 {line_num} 行开始的新内容，不要重复之前说过的话。\n"
        f"{topic}\n\n"
        "请用英文写一段 30-60 秒的电台独白，5-8 句话，语气温暖、松弛、有深夜电台的感觉。\n"
        "每句话一行。每一行英文下面附一行中文翻译。\n\n"
        "输出 JSON:\n"
        '{"title": "本期电台标题", "subtitle": "简短副标题", "song": "当前歌曲名（如果有）或空字符串", '
        '"lines": [{"en": "英文原文", "zh": "中文翻译"}, ...]}\n'
        "注意：line 不要带时间戳，前端会自动计算时间。每句话保持在 6-12 个英文单词左右，适合朗读。"
    )

    result = brain.ask(system_prompt, user_prompt)

    # 确保 lines 存在
    if not result.get("lines"):
        result["lines"] = [
            {"en": "This is Claudio.", "zh": "我是 Claudio。"},
            {"en": result.get("say", "Let the music speak."), "zh": "让音乐说话。"},
        ]

    # 自动分配时间戳（按每句约 5-7 秒估算）
    sec = 0
    for line in result["lines"]:
        words = len(line.get("en", "").split())
        dur = max(4, min(10, words * 0.7))  # 每句 4-10 秒
        line["time"] = f"{int(sec//60)}:{int(sec%60):02d}"
        sec += dur

    return jsonify(result)


# ═══════════════════════════════════════════
# TASTE ANALYSIS
# ═══════════════════════════════════════════

@app.route("/api/taste/analyze", methods=["POST"])
def api_taste_analyze():
    """POST — 触发品味蒸馏"""
    try:
        from brain.taste import run_taste_analysis
        result = run_taste_analysis()
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/taste/import_apple", methods=["POST"])
def api_taste_import_apple():
    """POST {extract_dir: ...} — 导入 Apple Music 数据并重新蒸馏"""
    data = request.get_json()
    if not data or "extract_dir" not in data:
        return jsonify({"ok": False, "error": "请提供 extract_dir"}), 400
    try:
        from brain.apple_import import run_apple_analysis
        result = run_apple_analysis(data["extract_dir"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ═══════════════════════════════════════════
# ═══════════════════════════════════════════
# TTS
# ═══════════════════════════════════════════

@app.route("/api/tts")
def api_tts():
    """GET ?t=<text> — speak with Christopher, zero cache"""
    import os, json
    from brain.tts import speak
    text = request.args.get("t", "")
    if not text: return "", 400
    print(f"[tts] request: {text[:80]}...")
    path, boundaries = speak(text)
    if not path: return "", 500
    size = os.path.getsize(path)
    print(f"[tts] generated {size} bytes, {len(boundaries)} word boundaries")
    resp = send_file(path, mimetype="audio/mpeg")
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Word-Boundaries"] = json.dumps(boundaries)
    @resp.call_on_close
    def _(): os.remove(path)
    return resp


# ═══════════════════════════════════════════
# SCHEDULER
# ═══════════════════════════════════════════

def morning_plan(name, now):
    print(f"[scheduler] {name} at {now}")

scheduler.add("morning-plan", 7, 0, morning_plan)
scheduler.add("morning-broadcast", 9, 0, morning_plan)
scheduler.add("mood-check-14", 14, 0, morning_plan)
scheduler.add("mood-check-20", 20, 0, morning_plan)
scheduler.start()


# ═══════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 50)
    print(" Claudio · 个人AI音乐电台")
    print(" 施工图架构 · 6 HTTP + 1 WS")
    print(" http://localhost:8080")
    print("=" * 50)
    app.run(host="127.0.0.1", port=8080, debug=True)
