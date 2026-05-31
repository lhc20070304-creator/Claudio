"""APPLE_IMPORT.PY · 解析 Apple Music 导出数据 → 合并进品味蒸馏"""
import csv
import json
import os
from collections import Counter
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_apple_export(extract_dir):
    """解析 Apple 隐私导出目录，返回结构化数据

    extract_dir: 解压后的 ZIP 根目录（包含 Apple Media Services/ 等文件夹）
    """
    result = {
        "top_artists": Counter(),
        "top_songs": Counter(),
        "play_history": [],  # 按时间排序的播放记录
        "liked_artists": [],
        "liked_songs": [],
        "playlists": [],
        "total_plays": 0,
    }

    base = os.path.join(extract_dir, "Apple Media Services")

    # ── 播放活动（CSV） ──
    activity_dir = os.path.join(base, "Apple Music Activity")
    if os.path.isdir(activity_dir):
        for fname in os.listdir(activity_dir):
            if not fname.endswith(".csv"):
                continue
            path = os.path.join(activity_dir, fname)
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        artist = (row.get("Artist Name") or row.get("Artist") or "").strip()
                        song = (row.get("Song Name") or row.get("Content Name") or "").strip()
                        # 跳过 Apple Music Radio / 非音乐内容
                        if not artist or not song:
                            continue
                        if artist in ("Apple Music", "Apple Music Radio"):
                            continue

                        key = f"{artist} — {song}"
                        result["top_songs"][key] += 1
                        result["top_artists"][artist] += 1
                        result["total_plays"] += 1

                        # 尝试解析日期用于排序
                        date_str = (row.get("Event Start Timestamp") or
                                    row.get("Play Date") or
                                    row.get("Date") or "")
                        result["play_history"].append({
                            "artist": artist,
                            "song": song,
                            "date": date_str,
                        })
            except Exception as e:
                print(f"  [warn] 无法解析 {fname}: {e}")

    # ── 喜欢/不喜欢 ──
    likes_dir = os.path.join(base, "Apple Music Likes and Dislikes")
    if os.path.isdir(likes_dir):
        for fname in os.listdir(likes_dir):
            if not fname.endswith(".csv"):
                continue
            path = os.path.join(likes_dir, fname)
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        artist = (row.get("Artist Name") or row.get("Artist") or "").strip()
                        item = (row.get("Item Name") or row.get("Title") or "").strip()
                        reaction = (row.get("Reaction") or row.get("Preference") or "").lower()
                        if "like" in reaction or "favorite" in reaction:
                            if artist:
                                result["liked_artists"].append(artist)
                            if item:
                                result["liked_songs"].append(f"{artist} — {item}" if artist else item)
            except Exception as e:
                print(f"  [warn] 无法解析 {fname}: {e}")

    # ── 播放列表 ──
    pl_dir = os.path.join(base, "Apple Music Playlists")
    if os.path.isdir(pl_dir):
        for fname in sorted(os.listdir(pl_dir)):
            if not fname.endswith(".csv"):
                continue
            path = os.path.join(pl_dir, fname)
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    songs = []
                    for row in reader:
                        artist = (row.get("Artist Name") or "").strip()
                        title = (row.get("Song Name") or row.get("Title") or "").strip()
                        if artist and title:
                            songs.append(f"{artist} — {title}")
                    if songs:
                        result["playlists"].append({
                            "name": fname.replace(".csv", ""),
                            "count": len(songs),
                            "songs": songs[:30],  # 采样前 30 首
                        })
            except Exception as e:
                print(f"  [warn] 无法解析 {fname}: {e}")

    return result


def merge_with_netease(apple_data, netease_playlists, netease_tracks):
    """将 Apple Music 数据与网易云数据合并"""
    # Apple top artists (with play counts)
    apple_artists = dict(apple_data["top_artists"].most_common(30))

    # 网易云艺人权重
    netease_artists = Counter()
    for t in netease_tracks:
        netease_artists[t.get("artist", "")] += 1

    # 合并：Apple 权重 x2（因为代表最近真实收听）
    merged_artists = Counter()
    for a, c in netease_artists.items():
        merged_artists[a] += c
    for a, c in apple_artists.items():
        merged_artists[a] += c * 2

    return {
        "apple_total_plays": apple_data["total_plays"],
        "apple_top_artists": apple_data["top_artists"].most_common(30),
        "apple_top_songs": apple_data["top_songs"].most_common(50),
        "apple_liked": apple_data["liked_songs"],
        "apple_playlists": apple_data["playlists"],
        "merged_top_artists": merged_artists.most_common(35),
        "netease_playlists": netease_playlists,
    }


def distill_with_apple(merged_data, force=False):
    """用 AI 蒸馏合并后的品味（Apple + 网易云）"""
    from brain.claude import brain

    artists_apple = "\n".join(
        f"- {a}（{c}次播放）" for a, c in merged_data["apple_top_artists"][:15]
    )
    songs_apple = "\n".join(
        f"- {s}" for s, c in merged_data["apple_top_songs"][:30]
    )
    liked = "\n".join(f"- {s}" for s in merged_data["apple_liked"][:20])
    merged = "\n".join(f"- {a}（合并权重{c}）" for a, c in merged_data["merged_top_artists"][:20])

    system_prompt = """你是一个音乐品味分析师。根据用户 Apple Music 和网易云的合并数据，生成一份详细的音乐品味档案。

输出纯 Markdown，格式：

# 我的音乐品味

## 最近在听（Apple Music 高频）
- 基于实际播放次数整理

## 喜欢的风格
- genre（从 Apple Music + 网易云合并推断）

## 高频艺人
### Apple Music 近期最爱
### 网易云长期收藏

## 场景偏好
## 数据来源

要求：基于真实数据，重点体现 Apple Music 反映的「近期」偏好，网易云反映的「长期」收藏。"""

    user_prompt = f"""## Apple Music 播放数据
总播放次数: {merged_data['apple_total_plays']}

### 高频艺人（播放次数）
{artists_apple}

### 高频歌曲
{songs_apple}

### 喜欢的曲目
{liked}

### Apple Music 播放列表
{chr(10).join(f"- {p['name']}（{p['count']}首）" for p in merged_data.get('apple_playlists', [])[:10])}

## 合并权重（Apple x2 + 网易云 x1）
{merged}

请生成完整的品味档案 Markdown。"""

    result = brain.ask(system_prompt, user_prompt, raw=True)
    taste_md = result.get("say", "") if isinstance(result, dict) else ""

    if not taste_md or len(taste_md) < 100:
        taste_md = _fallback_apple(merged_data)

    header = f"<!-- AUTO-GENERATED from Apple Music + Netease -->\n<!-- 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} -->\n<!-- Apple Music 播放: {merged_data['apple_total_plays']}次 -->\n\n"
    return header + taste_md


def _fallback_apple(data):
    lines = [
        "# 我的音乐品味",
        "",
        "## 最近在听（Apple Music）",
    ]
    for a, c in data["apple_top_artists"][:12]:
        lines.append(f"- {a}（{c}次）")
    lines += ["", "## 长期收藏（网易云）"]
    for a, c in data["merged_top_artists"][10:22]:
        lines.append(f"- {a}")
    return "\n".join(lines)


def run_apple_analysis(extract_dir):
    """一键：解析 Apple 数据 → 合并网易云 → 蒸馏 → 保存"""
    from services.music import music
    from brain.taste import save_taste

    print("[1] 解析 Apple Music 导出数据...")
    apple_data = parse_apple_export(extract_dir)

    if apple_data["total_plays"] == 0:
        return {"ok": False, "error": f"在 {extract_dir} 中未找到 Apple Music 播放数据，请确认解压路径正确"}

    print(f"    找到 {apple_data['total_plays']} 次播放记录")
    print(f"    高频艺人: {len(apple_data['top_artists'])}")
    print(f"    喜欢曲目: {len(apple_data['liked_songs'])}")

    # 获取网易云数据
    print("[2] 获取网易云数据...")
    netease_pls = music.get_user_playlists() if music.cookie else []
    netease_tracks = []
    for pl in (netease_pls or [])[:10]:
        if pl.get("count", 0) >= 3:
            tracks = music.get_playlist_tracks(pl["id"], limit=30)
            netease_tracks.extend(tracks)

    # 合并
    print("[3] 合并数据...")
    merged = merge_with_netease(apple_data, netease_pls, netease_tracks)

    # 蒸馏
    print("[4] AI 蒸馏...")
    markdown = distill_with_apple(merged)
    path = save_taste(markdown)

    return {
        "ok": True,
        "path": path,
        "apple_plays": apple_data["total_plays"],
        "apple_artists": len(apple_data["top_artists"]),
        "merged_artists": len(merged["merged_top_artists"]),
    }


# ── 命令行入口 ──
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python apple_import.py <Apple导出目录>")
        print("例如: python apple_import.py ~/Downloads/Apple-Export")
        sys.exit(1)

    result = run_apple_analysis(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
