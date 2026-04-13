"""
roco/capture.py — 游戏窗口自动截图模块

用法：
    from roco.capture import GameWatcher

    def on_change(img: Image.Image):
        ...  # 画面发生明显变化时回调

    watcher = GameWatcher(on_change, window_title="洛克王国")
    watcher.start()   # 后台线程开始监控
    watcher.stop()    # 停止
"""

import threading
import time
from typing import Callable

import numpy as np
from PIL import Image

# ──────────────────────────────────────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_TITLE      = "洛克王国"
POLL_INTERVAL      = 0.3   # 截图间隔（秒）
DIFF_THRESHOLD     = 8.0   # 平均像素差阈值（0-255），超过则认为场面发生变化
COOLDOWN           = 2.0   # 触发分析后的冷却秒数，防止同一回合重复触发


# ──────────────────────────────────────────────────────────────────────────────
# 窗口查找（Windows only）
# ──────────────────────────────────────────────────────────────────────────────

def find_window(title: str) -> int | None:
    """返回匹配标题的窗口句柄；找不到返回 None。"""
    try:
        import win32gui
        hwnd = win32gui.FindWindow(None, title)
        return hwnd if hwnd else None
    except ImportError:
        return None


def list_windows() -> list[tuple[int, str]]:
    """枚举所有可见窗口，返回 [(hwnd, title), ...]。"""
    result = []
    try:
        import win32gui

        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t:
                    result.append((hwnd, t))

        win32gui.EnumWindows(_cb, None)
    except ImportError:
        pass
    return result


def grab_window(hwnd: int) -> Image.Image | None:
    """
    用 win32gui BitBlt 抓取指定窗口（即使被遮挡也有效）。
    失败时返回 None。
    """
    try:
        import win32gui, win32ui, win32con
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        w, h = right - left, bottom - top
        if w <= 0 or h <= 0:
            return None

        hwnd_dc   = win32gui.GetWindowDC(hwnd)
        mfc_dc    = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc   = mfc_dc.CreateCompatibleDC()
        bmp       = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bmp)
        save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), win32con.SRCCOPY)

        bmp_info = bmp.GetInfo()
        raw = bmp.GetBitmapBits(True)
        img = Image.frombuffer("RGB", (bmp_info["bmWidth"], bmp_info["bmHeight"]),
                               raw, "raw", "BGRX", 0, 1)

        win32gui.DeleteObject(bmp.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)
        return img
    except Exception:
        return None


def grab_screen_region(region: dict) -> Image.Image:
    """
    用 mss 截取屏幕指定区域（mss region 格式：{top, left, width, height}）。
    游戏必须在屏幕可见区域内。
    """
    import mss
    with mss.mss() as sct:
        raw = sct.grab(region)
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def grab_fullscreen() -> Image.Image:
    """截取主显示器全屏。"""
    import mss
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # monitors[0] 是所有屏幕合集，[1] 是主屏
        raw = sct.grab(monitor)
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


# ──────────────────────────────────────────────────────────────────────────────
# 帧差分
# ──────────────────────────────────────────────────────────────────────────────

def frame_diff(a: Image.Image, b: Image.Image) -> float:
    """返回两帧的平均像素差（0-255）。两帧尺寸不同时直接返回 255。"""
    if a.size != b.size:
        return 255.0
    arr_a = np.asarray(a.convert("L"), dtype=np.float32)
    arr_b = np.asarray(b.convert("L"), dtype=np.float32)
    return float(np.abs(arr_a - arr_b).mean())


# ──────────────────────────────────────────────────────────────────────────────
# GameWatcher 主类
# ──────────────────────────────────────────────────────────────────────────────

class GameWatcher:
    """
    后台线程持续截图，帧差分超阈值时调用 on_change 回调。

    参数
    ----
    on_change       : 回调函数，接收 PIL.Image.Image
    window_title    : 游戏窗口标题（精确匹配），None 则截全屏
    poll_interval   : 截图间隔（秒）
    diff_threshold  : 触发阈值（平均像素差）
    cooldown        : 触发后冷却秒数
    """

    def __init__(
        self,
        on_change: Callable[[Image.Image], None],
        window_title: str | None = DEFAULT_TITLE,
        poll_interval: float = POLL_INTERVAL,
        diff_threshold: float = DIFF_THRESHOLD,
        cooldown: float = COOLDOWN,
    ):
        self.on_change      = on_change
        self.window_title   = window_title
        self.poll_interval  = poll_interval
        self.diff_threshold = diff_threshold
        self.cooldown       = cooldown

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_frame: Image.Image | None = None
        self._last_trigger: float = 0.0

        # status 供外部 UI 查询
        self.status: str = "idle"          # idle / watching / window_not_found
        self.hwnd:   int | None = None

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.status = "idle"

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── 内部循环 ──────────────────────────────────────────────────────────────

    def _grab(self) -> Image.Image | None:
        """抓一帧：优先 win32gui 窗口抓图，回退到 mss 全屏。"""
        if self.window_title:
            hwnd = find_window(self.window_title)
            if hwnd:
                self.hwnd = hwnd
                img = grab_window(hwnd)
                if img:
                    return img
            # 窗口不存在或抓图失败：尝试 mss 全屏
        return grab_fullscreen()

    def _loop(self) -> None:
        self.status = "watching"
        while not self._stop_event.is_set():
            try:
                img = self._grab()
                if img is None:
                    self.status = "window_not_found"
                    time.sleep(self.poll_interval)
                    continue

                self.status = "watching"
                now = time.monotonic()
                if self._last_frame is not None:
                    diff = frame_diff(self._last_frame, img)
                    if diff >= self.diff_threshold:
                        if now - self._last_trigger >= self.cooldown:
                            self._last_trigger = now
                            try:
                                self.on_change(img.copy())
                            except Exception as e:
                                print(f"[capture] on_change error: {e}")

                self._last_frame = img

            except Exception as e:
                print(f"[capture] loop error: {e}")

            time.sleep(self.poll_interval)

        self.status = "idle"
