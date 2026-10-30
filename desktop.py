"""Claudio Desktop — pywebview window

Windows 上额外做三件事：DWM 圆角 / 任务栏图标 / edgechromium 内核。
macOS 上这三件事由系统或 pywebview 自己处理，代码里全部跳过，
所以这个文件在两个平台上都能直接跑。
"""
import sys
import time
import socket
import subprocess
import threading
import os

import webview

IS_WIN = sys.platform == "win32"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# creationflags 只在 Windows 有意义；POSIX 上传非 0 值 subprocess 会抛 ValueError
CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0

if IS_WIN:
    import ctypes
    from ctypes import wintypes

    # DWM constants
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_ROUND = 2
    WM_SETICON = 0x0080
    ICON_BIG = 1
    ICON_SMALL = 0


def nuke_borders():
    """Windows only — 通过 DWM 让圆角覆盖整个无边框窗口"""
    if not IS_WIN:
        return
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


def kill_port(port):
    """杀掉占用指定端口的进程"""
    try:
        if IS_WIN:
            r = subprocess.run(
                f'netstat -ano | findstr :{port} | findstr LISTENING',
                shell=True, capture_output=True, text=True, timeout=5,
                creationflags=CREATE_NO_WINDOW,
            )
            for line in r.stdout.strip().split('\n'):
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    subprocess.run(['taskkill', '/F', '/PID', pid],
                        capture_output=True, creationflags=CREATE_NO_WINDOW)
        else:
            r = subprocess.run(
                ['lsof', '-ti', f'tcp:{port}'],
                capture_output=True, text=True, timeout=5,
            )
            for pid in r.stdout.split():
                subprocess.run(['kill', '-9', pid], capture_output=True)
    except Exception:
        pass


def wait_port(port, timeout=60):
    for _ in range(timeout):
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1)
            s.close()
            return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(1)
    return False


def start_netease():
    """启动网易云 API，失败自动重试"""
    err_log = os.path.join(BASE_DIR, "netease_err.log")
    for attempt in range(3):
        proc = subprocess.Popen(
            ["node", "node_modules/NeteaseCloudMusicApi/app.js"],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=open(err_log, "a") if attempt == 0 else subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        # 等它起来
        for _ in range(40):
            try:
                s = socket.create_connection(("127.0.0.1", 3000), timeout=1)
                s.close()
                return proc
            except (socket.error, ConnectionRefusedError):
                time.sleep(1)
        # 超时，杀掉重试
        proc.kill()
        time.sleep(1)
    return None


def start_flask():
    from app import app
    app.run(host="127.0.0.1", port=8080, debug=False)


def watchdog(proc_ref):
    """守护线程：Netease 挂了自动重启"""
    while True:
        time.sleep(10)
        p = proc_ref[0]
        if p and p.poll() is not None:
            proc_ref[0] = start_netease()
            if proc_ref[0] is None:
                break


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



def set_macos_dock_icon():
    """Use Claudio's icon for this process only; leave the Python installation alone."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSImage

        icon_path = os.path.join(BASE_DIR, "static", "claudio-macos.png")
        icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
        if icon is None:
            raise RuntimeError(f"Cannot load Dock icon: {icon_path}")
        NSApplication.sharedApplication().setApplicationIconImage_(icon)
    except Exception as exc:
        print(f"[desktop] macOS Dock icon could not be set: {exc}")


def main():
    # 0. 清理可能残留的旧进程
    kill_port(3000)
    kill_port(8080)
    time.sleep(1)

    # 1. 启动网易云 API（带重试，最多等 60 秒）
    netease_proc = start_netease()
    if netease_proc is None:
        sys.exit(1)

    # 2. 并行启动 Flask
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # 3. 等 Flask
    if not wait_port(8080, timeout=30):
        netease_proc.kill()
        sys.exit(1)

    # 4. 启动 Netease 守护
    netease_ref = [netease_proc]
    threading.Thread(target=watchdog, args=(netease_ref,), daemon=True).start()

    # Apply DWM rounded corners after a short delay (no-op off Windows)
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
    # Windows 指定 EdgeChromium 内核；macOS 交给 pywebview 自动选择（Cocoa/WebKit）
    if IS_WIN:
        webview.start(gui="edgechromium")
    else:
        # AppKit must run on the main thread, before the Cocoa event loop starts.
        set_macos_dock_icon()
        webview.start()

    print("[desktop] shutting down...")
    netease_proc.kill()
    print("[desktop] done")


if __name__ == "__main__":
    main()
