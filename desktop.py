"""Claudio Desktop — pywebview window"""
import sys
import time
import socket
import subprocess
import threading
import os
import ctypes
from ctypes import wintypes

import webview

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREATE_NO_WINDOW = 0x08000000

# DWM constants
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
WM_SETICON = 0x0080
ICON_BIG = 1
ICON_SMALL = 0

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_BORDER = 0x00800000
WS_EX_CLIENTEDGE = 0x00000200
WS_EX_STATICEDGE = 0x00020000
WS_EX_DLGMODALFRAME = 0x00000001
WS_EX_WINDOWEDGE = 0x00000100

def nuke_borders():
    """通过 DwmExtendFrameIntoClientArea 让 DWM 圆角覆盖整个窗口"""
    try:
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi

        # 查找 Claudio 窗口
        hwnd = None
        for _ in range(30):
            found = []
            def enum_callback(h, _):
                try:
                    l = user32.GetWindowTextLengthW(h)
                    if l == 0: return True
                    b = ctypes.create_unicode_buffer(l + 1)
                    user32.GetWindowTextW(h, b, l + 1)
                    if "Claudio" in b.value:
                        found.append(h)
                        return False
                except Exception:
                    pass
                return True
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
            if found:
                hwnd = found[0]
                break
            time.sleep(0.15)

        if not hwnd:
            return

        # 设置窗口图标（任务栏和标题栏）
        icon_path = os.path.join(BASE_DIR, "Claudio.ico")
        if os.path.exists(icon_path):
            hicon = user32.LoadImageW(0, icon_path, ICON_BIG, 0, 0, 0x10 | 0x40)
            if hicon:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
            hicon_sm = user32.LoadImageW(0, icon_path, ICON_SMALL, 0, 0, 0x10 | 0x40)
            if hicon_sm:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_sm)

        # 窗口置顶
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

        class MARGINS(ctypes.Structure):
            _fields_ = [("left", ctypes.c_int), ("right", ctypes.c_int),
                        ("top", ctypes.c_int), ("bottom", ctypes.c_int)]
        margins = MARGINS(-1, -1, -1, -1)  # -1 = extend to entire window
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

        # 设置圆角
        corner = ctypes.c_int(DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner), ctypes.sizeof(corner))

        sys.stdout.write("[desktop] DWM extended frame + rounding applied\n")
        sys.stdout.flush()
    except Exception as e:
        print(f"[desktop] nuke error: {e}")


def wait_port(port, timeout=30):
    for _ in range(timeout):
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1)
            s.close()
            return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(1)
    return False


def start_netease():
    return subprocess.Popen(
        ["node", "node_modules/NeteaseCloudMusicApi/app.js"],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def start_flask():
    from app import app
    app.run(host="127.0.0.1", port=8080, debug=False)


class WindowAPI:
    """暴露给 JS 的窗口控制 API"""
    def __init__(self):
        self._window = None
    def set_window(self, w):
        self._window = w
    def minimize(self):
        if self._window:
            self._window.minimize()
    def quit(self):
        if self._window:
            self._window.destroy()


def main():
    # Start both services in parallel
    netease_proc = start_netease()
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Wait for both ports in parallel
    results = {}
    def wait(n, port):
        results[port] = wait_port(port)

    t1 = threading.Thread(target=wait, args=(0, 3000), daemon=True)
    t2 = threading.Thread(target=wait, args=(0, 8080), daemon=True)
    t1.start(); t2.start()
    t1.join(timeout=30); t2.join(timeout=30)

    if not results.get(3000):
        print("[desktop] ERROR: Netease failed")
        netease_proc.kill(); sys.exit(1)
    if not results.get(8080):
        print("[desktop] ERROR: Flask failed")
        netease_proc.kill(); sys.exit(1)

    # Apply DWM rounded corners after a short delay
    threading.Timer(0.5, nuke_borders).start()

    api = WindowAPI()
    window = webview.create_window(
        title="Claudio",
        url="http://127.0.0.1:8080?desktop=1",
        js_api=api,
        width=565, height=960,
        min_size=(565, 700),
        resizable=True,
        frameless=True,
        easy_drag=True,
        on_top=True,
        transparent=False,
        background_color="#000000",
    )
    api.set_window(window)
    webview.start(gui="edgechromium")

    print("[desktop] shutting down...")
    netease_proc.kill()
    print("[desktop] done")


if __name__ == "__main__":
    main()
