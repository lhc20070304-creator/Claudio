import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path

from flask import Flask
from flask_sock import Sock
from websockets.sync.client import connect
from macos.runtime import Runtime


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def app_factory():
    app = Flask(__name__)
    sock = Sock(app)
    @app.get('/')
    def index():
        return 'ready'
    @sock.route('/stream')
    def echo(ws):
        ws.send(ws.receive())
    return app


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ports = (free_port(), free_port())
        command = [sys.executable, '-m', 'http.server', str(self.ports[0]), '--bind', '127.0.0.1']
        self.runtime = Runtime(self.tmp.name, app_factory, command, self.ports,
                               timeout=3, watch_interval=0.1)

    def tearDown(self):
        self.runtime.stop()
        self.tmp.cleanup()

    def test_restart_then_stop_releases_both_ports(self):
        self.runtime.start()
        old = self.runtime.node
        old.kill()
        old.wait()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.runtime.node is not old and Runtime.listening(self.ports[0]):
                break
            time.sleep(0.05)
        replacement = self.runtime.node
        self.assertIsNot(replacement, old)
        self.assertTrue(Runtime.listening(self.ports[0]))
        with connect(f'ws://127.0.0.1:{self.ports[1]}/stream') as ws:
            ws.send('中文 WebSocket')
            self.assertEqual(ws.recv(timeout=3), '中文 WebSocket')
        self.runtime.stop()
        self.assertIsNotNone(replacement.poll())
        self.assertFalse(any(Runtime.listening(p) for p in self.ports))
        self.runtime.stop()  # idempotent

    def test_occupied_port_is_not_killed(self):
        with socket.socket() as other:
            other.bind(('127.0.0.1', self.ports[0]))
            other.listen()
            with self.assertRaisesRegex(RuntimeError, 'occupied'):
                self.runtime.start()
            self.assertTrue(Runtime.listening(self.ports[0]))
            self.assertIsNone(self.runtime.node)

    def test_failed_node_exits_fast(self):
        self.runtime.node_command = [sys.executable, '-c', 'raise SystemExit(7)']
        start = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, 'exited'):
            self.runtime.start()
        self.assertLess(time.monotonic() - start, 2)
        self.assertFalse(any(Runtime.listening(p) for p in self.ports))

    def test_flask_failure_cleans_node(self):
        def fail():
            raise ValueError('bad app configuration')
        self.runtime.app_factory = fail
        with self.assertRaisesRegex(ValueError, 'bad app'):
            self.runtime.start()
        self.assertFalse(any(Runtime.listening(p) for p in self.ports))

    def test_startup_timeout_cleans_node(self):
        self.runtime.timeout = 0.3
        self.runtime.node_command = [sys.executable, '-c', 'import time; time.sleep(60)']
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            self.runtime.start()
        self.assertIsNone(self.runtime.node)


class DesktopCleanupTests(unittest.TestCase):
    def test_window_close_and_window_failure_both_stop_runtime(self):
        from unittest.mock import MagicMock, patch
        import desktop
        for error in (None, RuntimeError('window failed')):
            runtime = MagicMock()
            with patch('macos.runtime.Runtime', return_value=runtime), \
                 patch.object(desktop.webview, 'create_window'), \
                 patch.object(desktop.webview, 'start', side_effect=error), \
                 patch.object(desktop, 'set_macos_dock_icon'):
                if error:
                    with self.assertRaisesRegex(RuntimeError, 'window failed'):
                        desktop.main_macos()
                else:
                    desktop.main_macos()
                runtime.stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
