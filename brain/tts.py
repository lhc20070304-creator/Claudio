"""TTS.PY · Christopher via isolated subprocess — returns (mp3_path, word_boundaries_json)"""
import os, subprocess, tempfile, hashlib, json

import sys as _sys
_PYTHON = _sys.executable
_WORKER = os.path.join(os.path.dirname(__file__), "tts_worker.py")

# Load API keys from env vars (set by user before running Flask)
# Also fallback to brain/.env if it exists
_ENV = {}
_ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_ENV_FILE):
    for _line in open(_ENV_FILE):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _ENV[_k] = _v
# Environment variables override file
for _k in ["DASHSCOPE_API_KEY", "ALIBABA_ACCESS_KEY_ID", "ALIBABA_ACCESS_KEY_SECRET"]:
    if _k in os.environ:
        _ENV[_k] = os.environ[_k]


def synthesize(text):
    """Generate temp mp3 + word boundaries. Returns (mp3_path, word_boundaries_list) or (None, None)."""
    if not text or not text.strip():
        return None, None
    thash = hashlib.md5(text.encode()).hexdigest()[:8]
    fd, tmp_mp3 = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    fd2, tmp_meta = tempfile.mkstemp(suffix=".json")
    os.close(fd2)
    with open(tmp_mp3, "wb") as f:
        f.write(b"")
    try:
        env = os.environ.copy()
        for _k, _v in _ENV.items():
            env[_k] = _v
        env["TTS_VOICE"] = "en-US-GuyNeural"
        r = subprocess.run(
            [_PYTHON, _WORKER, text, tmp_mp3, tmp_meta],
            capture_output=True, text=True, timeout=30, env=env
        )
        size = os.path.getsize(tmp_mp3)
        if r.returncode != 0 or size < 100:
            print(f"[tts] FAIL hash={thash} rc={r.returncode} size={size}")
            print(f"[tts] STDERR: {r.stderr}")
            print(f"[tts] STDOUT: {r.stdout}")
            os.remove(tmp_mp3)
            if os.path.exists(tmp_meta):
                os.remove(tmp_meta)
            return None, None
        # read word boundaries
        boundaries = []
        if os.path.exists(tmp_meta) and os.path.getsize(tmp_meta) > 0:
            with open(tmp_meta, "r") as f:
                boundaries = json.load(f)
            os.remove(tmp_meta)
        print(f"[tts] OK {size}B hash={thash} words={len(boundaries)} | {text[:60]}")
        return tmp_mp3, boundaries
    except Exception as e:
        print(f"[tts] EXCEPTION hash={thash}: {e}")
        try:
            os.remove(tmp_mp3)
        except:
            pass
        try:
            os.remove(tmp_meta)
        except:
            pass
        return None, None


# alias for app.py import
speak = synthesize
