"""SCHEDULER.PY · 节律调度 — 定时触发规划/播报/情绪检查"""
import threading
import time
from datetime import datetime


class Scheduler:
    def __init__(self):
        self._jobs = []
        self._running = False
        self._thread = None

    def add(self, name: str, cron_hour: int, cron_minute: int, handler):
        """注册定时任务
        handler 签名为 handler(name, now: datetime)
        """
        self._jobs.append({
            "name": name,
            "hour": cron_hour,
            "minute": cron_minute,
            "handler": handler,
            "last_run": None,
        })

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            now = datetime.now()
            for job in self._jobs:
                h_ok = now.hour == job["hour"]
                m_ok = now.minute == job["minute"]
                same_day = job["last_run"] and job["last_run"].date() == now.date()
                if h_ok and m_ok and not same_day:
                    job["last_run"] = now
                    try:
                        job["handler"](job["name"], now)
                    except Exception as e:
                        print(f"[scheduler] {job['name']} failed: {e}")
            time.sleep(30)  # 每 30 秒检查一次


scheduler = Scheduler()
