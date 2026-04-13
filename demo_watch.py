"""
demo_watch.py — 自动监控功能调试 Demo

直接运行：
    .venv/Scripts/python.exe -u demo_watch.py

实时显示截图预览窗口 + 终端帧差值，按 Ctrl+C 或关闭预览窗口退出。
"""

import time
import tkinter as tk
from PIL import Image, ImageTk

# ── 配置 ──────────────────────────────────────────────────────────────────────
WINDOW_TITLE   = "洛克王国：世界"   # 游戏窗口须在屏幕可见范围内（mss 截屏坐标）
POLL_INTERVAL  = 0.3    # 截图间隔（秒）
DIFF_THRESHOLD = 8.0    # 触发阈值
COOLDOWN       = 2.0    # 触发后冷却秒数
PREVIEW_W      = 640    # 预览窗口宽度

# ── 导入截图工具 ──────────────────────────────────────────────────────────────
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

from roco.capture import grab_screen_region, frame_diff

# ── 固定截图区域：左上角 1920×1080 ───────────────────────────────────────────
REGION = {"left": 0, "top": 40, "width": 1920, "height": 1080}
print(f"固定区域: {REGION}")


# ── 预览窗口 ──────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("demo_watch — 截图预览")

info_var = tk.StringVar(value="初始化中…")
tk.Label(root, textvariable=info_var, font=("Consolas", 10), anchor="w",
         justify="left", bg="#1e1e2e", fg="#cdd6f4", padx=8, pady=4,
         ).pack(fill="x")

canvas = tk.Canvas(root, bg="#11111b", width=PREVIEW_W, height=360,
                   highlightthickness=0)
canvas.pack()
_tk_img = None   # 防止被 GC

prev_frame: Image.Image | None = None
last_trigger = 0.0
frame_count = 0

def _poll():
    global prev_frame, last_trigger, frame_count, _tk_img

    t0 = time.perf_counter()

    img = grab_screen_region(REGION)
    src = f"固定区域 0,0  1920×1080"

    elapsed_ms = (time.perf_counter() - t0) * 1000
    frame_count += 1

    diff = frame_diff(prev_frame, img) if prev_frame is not None else 0.0
    now  = time.monotonic()

    triggered = diff >= DIFF_THRESHOLD and now - last_trigger >= COOLDOWN
    if triggered:
        last_trigger = now

    flag = "  ★ 触发！" if triggered else ""
    info_var.set(
        f"帧 {frame_count:5d}  |  {img.size[0]}×{img.size[1]}"
        f"  |  耗时 {elapsed_ms:5.1f}ms  |  帧差 {diff:6.2f}"
        f"  |  {src}{flag}"
    )
    print(info_var.get(), flush=True)

    # 缩放后显示到 canvas
    ratio = PREVIEW_W / img.width
    ph = int(img.height * ratio)
    thumb = img.resize((PREVIEW_W, ph), Image.BILINEAR)
    _tk_img = ImageTk.PhotoImage(thumb)
    canvas.config(height=ph)
    canvas.delete("all")
    canvas.create_image(0, 0, anchor="nw", image=_tk_img)

    prev_frame = img
    root.after(int(POLL_INTERVAL * 1000), _poll)

root.after(100, _poll)
root.mainloop()
