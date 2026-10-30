"""Owned background services for the macOS shell (no GUI imports)."""
import socket
import subprocess
import threading
import time
from pathlib import Path

from werkzeug.serving import make_server


class Runtime:
    def __init__(self, root, app_factory, node_command=None, ports=(3000, 8080),
                 timeout=30, watch_interval=10):
        self.root = Path(root)
        self.app_factory = app_factory
        self.node_command = node_command or ['node', 'node_modules/NeteaseCloudMusicApi/app.js']
        self.node_port, self.flask_port = ports
        self.timeout = timeout
        self.watch_interval = watch_interval
        self.stopping = threading.Event()
        self.lock = threading.Lock()
        self.node = self.server = self.server_thread = self.watcher = None

    @staticmethod
    def listening(port):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                return True
        except OSError:
            return False

    @staticmethod
    def terminate(proc):
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        proc.wait()

    def start_node(self):
        # Called under lock. stop() sets the event before waiting for this lock.
        if self.stopping.is_set():
            return
        if self.listening(self.node_port):
            raise RuntimeError(f'Port {self.node_port} is occupied; close its owner first.')
        with (self.root / 'netease_err.log').open('a') as log:
            self.node = subprocess.Popen(self.node_command, cwd=self.root,
                                         stdout=subprocess.DEVNULL, stderr=log)
        deadline = time.monotonic() + self.timeout
        while not self.stopping.is_set() and time.monotonic() < deadline:
            if self.node.poll() is not None:
                raise RuntimeError(f'网易云 API exited ({self.node.returncode}); see netease_err.log')
            if self.listening(self.node_port):
                return
            self.stopping.wait(0.1)
        self.terminate(self.node)
        raise RuntimeError('网易云 API startup cancelled or timed out; see netease_err.log')

    def watch(self):
        while not self.stopping.wait(self.watch_interval):
            with self.lock:
                if self.stopping.is_set():
                    return
                if self.node and self.node.poll() is not None:
                    try:
                        self.start_node()
                    except Exception as exc:
                        if not self.stopping.is_set():
                            print(f'[desktop] 网易云 restart failed: {exc}', flush=True)

    def start(self):
        try:
            for port in (self.node_port, self.flask_port):
                if self.listening(port):
                    raise RuntimeError(f'Port {port} is occupied; close its owner first.')
            with self.lock:
                self.start_node()
            self.server = make_server('127.0.0.1', self.flask_port,
                                      self.app_factory(), threaded=True)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.watcher = threading.Thread(target=self.watch, daemon=True)
            self.watcher.start()
            return self
        except BaseException:
            self.stop()
            raise

    def stop(self):
        self.stopping.set()
        with self.lock:
            self.terminate(self.node)
            self.node = None
        if self.watcher and self.watcher is not threading.current_thread():
            self.watcher.join(timeout=self.timeout + 5)
        if self.server:
            if self.server_thread and self.server_thread.is_alive():
                self.server.shutdown()
                self.server_thread.join(timeout=5)
            self.server.server_close()
            self.server = None
