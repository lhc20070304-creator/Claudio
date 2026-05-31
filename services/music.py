"""网易云音乐服务 - 搜歌、播放、元数据、用户数据（带 cookie）"""

import json
import os
import re
import requests


class MusicService:
    """封装网易云音乐 API 调用"""

    def __init__(self, api_url="http://localhost:3000"):
        self.api_url = api_url
        self.cookie = self._load_cookie()
        self._uid = self._fetch_uid()

    def _load_cookie(self):
        """加载 .netease_cookie 文件，返回完整 cookie 字符串"""
        paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), ".netease_cookie"),
            os.path.join(os.path.dirname(__file__), "..", ".netease_cookie"),
        ]
        for p in paths:
            try:
                p = os.path.abspath(p)
                if os.path.exists(p):
                    with open(p, "r") as f:
                        return f.read().strip()
            except Exception:
                pass
        return ""

    def _fetch_uid(self):
        """用 cookie 获取用户 uid"""
        if not self.cookie:
            return ""
        try:
            data = self._get("/user/account", {"cookie": self.cookie, "timestamp": ""}, need_cookie=True)
            if data.get("code") == 200:
                return str(data.get("profile", {}).get("userId", ""))
        except Exception:
            pass
        return ""

    def _get(self, endpoint, params=None, need_cookie=False):
        params = dict(params or {})
        if need_cookie and self.cookie:
            params["cookie"] = self.cookie
        try:
            r = requests.get(
                f"{self.api_url}{endpoint}",
                params=params,
                timeout=10,
            )
            return r.json()
        except Exception:
            return {"code": -1, "msg": "API 不可用"}

    def search(self, keyword, limit=5):
        """搜索歌曲"""
        data = self._get("/search", {"keywords": keyword, "limit": limit})
        if data.get("code") != 200:
            return []
        songs = data.get("result", {}).get("songs", [])
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "artist": ", ".join(a["name"] for a in s.get("artists", [])),
                "album": s.get("album", {}).get("name", ""),
                "cover": s.get("album", {}).get("picUrl", ""),
            }
            for s in songs
        ]

    def get_song_url(self, song_id, level="standard"):
        """获取播放地址"""
        data = self._get("/song/url/v1", {"id": song_id, "level": level}, need_cookie=True)
        if data.get("code") != 200:
            return None
        urls = data.get("data", [])
        return urls[0].get("url") if urls else None

    def get_song_detail(self, song_id):
        """获取歌曲详情"""
        data = self._get("/song/detail", {"ids": str(song_id)})
        if data.get("code") != 200:
            return None
        songs = data.get("songs", [])
        if not songs:
            return None
        s = songs[0]
        return {
            "id": s["id"],
            "name": s["name"],
            "artist": ", ".join(a["name"] for a in s.get("ar", [])),
            "album": s.get("al", {}).get("name", ""),
            "cover": s.get("al", {}).get("picUrl", ""),
            "duration": s.get("dt", 0) // 1000,
        }

    def get_lyric(self, song_id):
        """获取歌词"""
        data = self._get("/lyric", {"id": song_id})
        if data.get("code") != 200:
            return ""
        lrc = data.get("lrc", {})
        return lrc.get("lyric", "")

    # ── 用户数据（需登录） ──

    def get_user_playlists(self):
        """获取用户歌单"""
        data = self._get("/user/playlist", {"uid": self._uid, "cookie": self.cookie}, need_cookie=True)
        if data.get("code") != 200:
            return []
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "cover": p.get("coverImgUrl", ""),
                "count": p.get("trackCount", 0),
            }
            for p in data.get("playlist", [])
        ]

    def get_playlist_tracks(self, playlist_id, limit=50):
        """获取歌单歌曲"""
        data = self._get("/playlist/track/all", {"id": playlist_id, "limit": limit}, need_cookie=True)
        if data.get("code") != 200:
            return []
        songs = data.get("songs", [])
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "artist": ", ".join(a["name"] for a in s.get("ar", [])),
                "album": s.get("al", {}).get("name", ""),
                "cover": s.get("al", {}).get("picUrl", ""),
            }
            for s in songs
        ]

    def get_daily_recommend(self):
        """获取每日推荐"""
        data = self._get("/recommend/songs", need_cookie=True)
        if data.get("code") != 200:
            return []
        songs = data.get("data", {}).get("dailySongs", [])
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "artist": ", ".join(a["name"] for a in s.get("ar", [])),
                "album": s.get("al", {}).get("name", ""),
                "cover": s.get("al", {}).get("picUrl", ""),
                "reason": s.get("reason", ""),
            }
            for s in songs
        ]

    def get_liked_songs(self, uid=""):
        """获取收藏歌曲"""
        data = self._get("/likelist", {"uid": uid}, need_cookie=True)
        if data.get("code") != 200:
            return []
        return data.get("ids", [])


# 全局单例
music = MusicService()
