"""
demo_capture_test.py — 截图方案对比测试

同时用 4 种方案截一张图，并排显示，找出哪种有效。
运行：
    .venv/Scripts/python.exe demo_capture_test.py
"""

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import win32gui, win32ui

WINDOW_TITLE = "洛克王国：世界"

# ── 找到游戏窗口 ──────────────────────────────────────────────────────────────
def find_hwnd(title: str) -> int | None:
    hwnd = win32gui.FindWindow(None, title)
    # FindWindow 要求精确匹配；游戏标题可能带尾随空格，再试一次枚举
    if not hwnd:
        def _cb(h, res):
            if win32gui.IsWindowVisible(h) and title in win32gui.GetWindowText(h):
                res.append(h)
        found = []
        win32gui.EnumWindows(_cb, found)
        hwnd = found[0] if found else None
    return hwnd or None

# ── 方案 A：PrintWindow PW_RENDERFULLCONTENT (0x2) ───────────────────────────
def method_a(hwnd: int) -> Image.Image | None:
    try:
        l, t, r, b = win32gui.GetClientRect(hwnd)
        w, h = r - l, b - t
        if w <= 0 or h <= 0:
            return None
        hdc    = win32gui.GetWindowDC(hwnd)
        mdc    = win32ui.CreateDCFromHandle(hdc)
        sdc    = mdc.CreateCompatibleDC()
        bmp    = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mdc, w, h)
        sdc.SelectObject(bmp)
        ok = ctypes.windll.user32.PrintWindow(hwnd, sdc.GetSafeHdc(), 0x2)
        img = None
        if ok:
            info = bmp.GetInfo()
            raw  = bmp.GetBitmapBits(True)
            img  = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]),
                                    raw, "raw", "BGRX", 0, 1)
        win32gui.DeleteObject(bmp.GetHandle())
        sdc.DeleteDC(); mdc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hdc)
        return img
    except Exception as e:
        print(f"[A] {e}")
        return None

# ── 方案 B：PrintWindow 不带标志 (0x0) ───────────────────────────────────────
def method_b(hwnd: int) -> Image.Image | None:
    try:
        l, t, r, b = win32gui.GetClientRect(hwnd)
        w, h = r - l, b - t
        if w <= 0 or h <= 0:
            return None
        hdc    = win32gui.GetWindowDC(hwnd)
        mdc    = win32ui.CreateDCFromHandle(hdc)
        sdc    = mdc.CreateCompatibleDC()
        bmp    = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mdc, w, h)
        sdc.SelectObject(bmp)
        ok = ctypes.windll.user32.PrintWindow(hwnd, sdc.GetSafeHdc(), 0x0)
        img = None
        if ok:
            info = bmp.GetInfo()
            raw  = bmp.GetBitmapBits(True)
            img  = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]),
                                    raw, "raw", "BGRX", 0, 1)
        win32gui.DeleteObject(bmp.GetHandle())
        sdc.DeleteDC(); mdc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hdc)
        return img
    except Exception as e:
        print(f"[B] {e}")
        return None

# ── 方案 C：mss 按窗口屏幕坐标截图 ──────────────────────────────────────────
def method_c(hwnd: int) -> Image.Image | None:
    try:
        import mss
        cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
        l, t, r, b = win32gui.GetClientRect(hwnd)
        w, h = r - l, b - t
        if w <= 0 or h <= 0:
            return None
        with mss.mss() as sct:
            raw = sct.grab({"left": cx, "top": cy, "width": w, "height": h})
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    except Exception as e:
        print(f"[C] {e}")
        return None

# ── 方案 D：mss GetWindowRect（含标题栏/边框）────────────────────────────────
def method_d(hwnd: int) -> Image.Image | None:
    try:
        import mss
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        w, h = r - l, b - t
        if w <= 0 or h <= 0:
            return None
        with mss.mss() as sct:
            raw = sct.grab({"left": l, "top": t, "width": w, "height": h})
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    except Exception as e:
        print(f"[D] {e}")
        return None

# ── GUI ───────────────────────────────────────────────────────────────────────
METHODS = [
    ("A: PrintWindow 0x2\n(PW_RENDERFULLCONTENT)", method_a),
    ("B: PrintWindow 0x0\n(无标志)",               method_b),
    ("C: mss ClientToScreen\n(客户区坐标)",         method_c),
    ("D: mss GetWindowRect\n(含边框坐标)",          method_d),
]
THUMB_W = 380

root = tk.Tk()
root.title("截图方案对比 — 关闭此窗口结束")
root.configure(bg="#1e1e2e")

# 状态行
status = tk.StringVar(value="正在查找窗口…")
tk.Label(root, textvariable=status, bg="#1e1e2e", fg="#cdd6f4",
         font=("Consolas", 10), padx=8, pady=4).grid(
         row=0, column=0, columnspan=4, sticky="ew")

frames = []
labels = []
canvases = []
_imgs = [None] * 4   # 防 GC

for i, (title, _) in enumerate(METHODS):
    f = tk.Frame(root, bg="#313244", bd=1, relief="flat")
    f.grid(row=1, column=i, padx=6, pady=6)
    tk.Label(f, text=title, bg="#313244", fg="#89b4fa",
             font=("Consolas", 9), justify="center").pack(pady=(4, 0))
    c = tk.Canvas(f, bg="#11111b", width=THUMB_W, height=220,
                  highlightthickness=0)
    c.pack(padx=4, pady=4)
    lbl = tk.Label(f, text="—", bg="#313244", fg="#a6e3a1",
                   font=("Consolas", 9))
    lbl.pack(pady=(0, 4))
    canvases.append(c)
    labels.append(lbl)

def do_capture():
    hwnd = find_hwnd(WINDOW_TITLE)
    if not hwnd:
        status.set(f"未找到窗口「{WINDOW_TITLE}」，请确保游戏正在运行")
        root.after(2000, do_capture)
        return

    l, t, r, b = win32gui.GetClientRect(hwnd)
    wx, wy = win32gui.ClientToScreen(hwnd, (0, 0))
    status.set(f"hwnd={hwnd}  客户区={r-l}×{b-t}  屏幕位置=({wx},{wy})  每 1 秒刷新")

    for i, (_, fn) in enumerate(METHODS):
        img = fn(hwnd)
        if img:
            ratio = THUMB_W / img.width
            ph = max(1, int(img.height * ratio))
            thumb = img.resize((THUMB_W, ph), Image.BILINEAR)
            _imgs[i] = ImageTk.PhotoImage(thumb)
            canvases[i].config(height=ph)
            canvases[i].delete("all")
            canvases[i].create_image(0, 0, anchor="nw", image=_imgs[i])
            # 检测是否全黑
            import numpy as np
            arr = np.asarray(img.convert("L"), dtype=np.float32)
            mean = float(arr.mean())
            labels[i].config(
                text=f"{img.size[0]}×{img.size[1]}  mean={mean:.1f}",
                fg="#a6e3a1" if mean > 5 else "#f38ba8"
            )
        else:
            canvases[i].delete("all")
            canvases[i].create_text(THUMB_W//2, 110, text="失败",
                                    fill="#f38ba8", font=("Consolas", 14))
            labels[i].config(text="None", fg="#f38ba8")

    root.after(1000, do_capture)

root.after(200, do_capture)
root.mainloop()
