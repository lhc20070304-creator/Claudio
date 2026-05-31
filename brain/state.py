"""STATE.DB · 状态记忆 — messages / plays / plan / prefs 跨重启持久"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "state.db")


class State:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS plays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                song_name TEXT,
                artist TEXT,
                song_id INTEGER,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL UNIQUE,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS prefs (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                song_name TEXT,
                artist TEXT,
                song_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_plays_session ON plays(session_id);
            CREATE INDEX IF NOT EXISTS idx_likes_session ON likes(session_id);
        """)
        self.conn.commit()

    # ── messages ──
    def add_message(self, session_id: str, role: str, content: str):
        self.conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?,?,?)",
            (session_id, role, content),
        )
        self.conn.commit()

    def get_messages(self, session_id: str, limit: int = 30):
        rows = self.conn.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    # ── plays ──
    def add_play(self, session_id: str, song_name: str, artist: str, song_id: int = 0):
        self.conn.execute(
            "INSERT INTO plays (session_id, song_name, artist, song_id) VALUES (?,?,?,?)",
            (session_id, song_name, artist, song_id),
        )
        self.conn.commit()

    def get_recent_plays(self, session_id: str, limit: int = 20):
        rows = self.conn.execute(
            "SELECT song_name, artist, song_id FROM plays WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"song_name": r[0], "artist": r[1], "song_id": r[2]} for r in rows]

    # ── plan ──
    def set_plan(self, day: str, summary: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO plan (day, summary) VALUES (?,?)",
            (day, summary),
        )
        self.conn.commit()

    def get_plan(self, day: str):
        row = self.conn.execute(
            "SELECT summary FROM plan WHERE day=?", (day,)
        ).fetchone()
        return row[0] if row else None

    # ── prefs ──
    def set_pref(self, key: str, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO prefs (key, value) VALUES (?,?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        self.conn.commit()

    # ── likes ──
    def add_like(self, session_id: str, song_name: str, artist: str, song_id: int = 0):
        self.conn.execute(
            "INSERT INTO likes (session_id, song_name, artist, song_id) VALUES (?,?,?,?)",
            (session_id, song_name, artist, song_id),
        )
        self.conn.commit()

    def remove_like(self, session_id: str, song_id: int):
        self.conn.execute(
            "DELETE FROM likes WHERE session_id=? AND song_id=?", (session_id, song_id)
        )
        self.conn.commit()

    def get_likes(self, session_id: str, limit: int = 50):
        rows = self.conn.execute(
            "SELECT song_name, artist, song_id FROM likes WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"song_name": r[0], "artist": r[1], "song_id": r[2]} for r in rows]

    def is_liked(self, session_id: str, song_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM likes WHERE session_id=? AND song_id=?", (session_id, song_id)
        ).fetchone()
        return row is not None

    def get_pref(self, key: str, default=None):
        row = self.conn.execute(
            "SELECT value FROM prefs WHERE key=?", (key,)
        ).fetchone()
        return json.loads(row[0]) if row else default


# singleton
state = State()
