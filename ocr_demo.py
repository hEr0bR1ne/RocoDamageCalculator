"""
OCR 识别调试工具 — Demo 版
支持任意分辨率截图，可拖拽调整识别区域并保存配置。

用法：
    python ocr_demo.py
    python ocr_demo.py <截图路径>

操作：
    - 拖动方框内部   → 移动整个区域
    - 拖动四个角点   → 调整区域大小
    - 💾 保存区域    → 写入 roco_regions.json，下次自动加载
    - ↺ 重置区域    → 恢复内置默认值
"""
import sys
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from PIL import Image, ImageTk

# 区域颜色映射
COLORS = {
    "self_name":  "#7c6af7",
    "enemy_name": "#f7706a",
    "skill1":     "#4ac97e",
    "skill2":     "#4ac97e",
    "skill3":     "#4ac97e",
    "skill4":     "#4ac97e",
}
LABELS = {
    "self_name":  "己方精灵",
    "enemy_name": "对方精灵",
    "skill1": "技能①",
    "skill2": "技能②",
    "skill3": "技能③",
    "skill4": "技能④",
}
REGION_KEYS = ["self_name", "enemy_name", "skill1", "skill2", "skill3", "skill4"]

PREVIEW_W = 900
PREVIEW_H = 506
HANDLE_R  = 6   # 角点把手半径（canvas 像素）


class OcrDemo(tk.Tk):
    def __init__(self, init_path: str | None = None):
        super().__init__()
        self.title("OCR 识别 Demo")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)

        self._img_orig: Image.Image | None = None
        self._tk_img: ImageTk.PhotoImage | None = None
        self._db = self._spirit_names = self._skill_names = None
        self._regions: dict = {}          # {key: (l, t, r, b)} 归一化 0~1
        self._game_area: tuple = (0.0, 0.0, 1.0, 1.0)  # 游戏画面裁剪范围
        self._drag: dict | None = None

        self._build_ui()
        self._init_regions()
        self._load_db_async()

        if init_path:
            self.after(200, lambda: self._open(init_path))

    # ── 区域管理 ────────────────────────────────────────────────────────────

    def _init_regions(self):
        from roco.analyzer import load_regions
        self._regions, self._game_area = load_regions()

    def _save_regions(self):
        from roco.analyzer import save_regions
        save_regions(self._regions, self._game_area)
        self._lbl_status.config(text="区域配置已保存至 roco_regions.json", fg="#4ac97e")

    def _reset_regions(self):
        from roco.analyzer import REGIONS_RATIO, _DEFAULT_GAME_AREA
        self._regions   = dict(REGIONS_RATIO)
        self._game_area = _DEFAULT_GAME_AREA
        self._redraw()
        self._lbl_status.config(text="区域已重置为内置默认值", fg="#f9e2af")

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        top = tk.Frame(self, bg="#1e1e2e")
        top.pack(fill="x", padx=12, pady=(12, 6))

        buttons = [
            ("📂  打开截图",    self._open,              "#7c6af7", "white",   False),
            ("📋  剪切板读取",  self._open_clipboard,    "#89b4fa", "#1e1e2e", False),
            ("▶  开始识别",    self._run,               "#4ac97e", "#1e1e2e", True),
            ("💾  保存区域",   self._save_regions,      "#f9e2af", "#1e1e2e", False),
            ("↺  重置区域",    self._reset_regions,     "#585b70", "white",   False),
        ]
        self._btn_run = None
        for text, cmd, bg, fg, disabled in buttons:
            b = tk.Button(top, text=text, command=cmd, bg=bg, fg=fg,
                          relief="flat", font=("微软雅黑", 10), padx=10, pady=5,
                          cursor="hand2",
                          state="disabled" if disabled else "normal")
            b.pack(side="left", padx=(0, 6))
            if disabled:
                self._btn_run = b

        self._lbl_status = tk.Label(top, text="尚未加载截图",
                                    bg="#1e1e2e", fg="#888", font=("微软雅黑", 10))
        self._lbl_status.pack(side="left", padx=8)

        # 画布
        cf = tk.Frame(self, bg="#2a2a3e")
        cf.pack(padx=12, pady=4)
        self._canvas = tk.Canvas(cf, width=PREVIEW_W, height=PREVIEW_H,
                                 bg="#2a2a3e", highlightthickness=0, cursor="crosshair")
        self._canvas.pack()
        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",       self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

        # 提示
        tk.Label(self,
                 text="拖动白色虚框 → 设定游戏画面范围（去除标题栏）· 拖动彩色框 → 调整识别区域 · 💾 保存",
                 bg="#1e1e2e", fg="#585b70", font=("微软雅黑", 9)
                 ).pack()

        # 结果表格
        rf = tk.Frame(self, bg="#1e1e2e")
        rf.pack(fill="x", padx=12, pady=(4, 12))

        cols = ("区域", "OCR 原文", "匹配结果", "置信度")
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Demo.Treeview",
                        background="#2a2a3e", foreground="#cdd6f4",
                        fieldbackground="#2a2a3e", rowheight=26,
                        font=("微软雅黑", 10))
        style.configure("Demo.Treeview.Heading",
                        background="#313244", foreground="#cba6f7",
                        font=("微软雅黑", 10, "bold"))
        style.map("Demo.Treeview", background=[("selected", "#45475a")])

        self._tree = ttk.Treeview(rf, columns=cols, show="headings",
                                  height=6, style="Demo.Treeview")
        for c, w in zip(cols, [90, 260, 160, 70]):
            self._tree.heading(c, text=c)
            self._tree.column(c, width=w, anchor="center" if c != "OCR 原文" else "w")
        self._tree.pack(fill="x")

    # ── 数据加载 ─────────────────────────────────────────────────────────────

    def _load_db_async(self):
        self._lbl_status.config(text="正在加载精灵数据库……", fg="#888")
        self.after(50, self._do_load_db)

    def _do_load_db(self):
        try:
            from roco.analyzer import load_db
            self._db, self._spirit_names, self._skill_names = load_db()
            self._lbl_status.config(
                text=f"已加载 {len(self._db)} 只精灵 · {len(self._skill_names)} 个技能",
                fg="#4ac97e")
        except Exception as e:
            self._lbl_status.config(text=f"数据库加载失败：{e}", fg="#f7706a")

    # ── 打开图片 ─────────────────────────────────────────────────────────────

    def _open(self, path: str | None = None):
        if path is None:
            path = filedialog.askopenfilename(
                title="选择对战截图",
                filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            self._img_orig = Image.open(path).convert("RGB")
        except Exception as e:
            self._lbl_status.config(text=f"打开失败：{e}", fg="#f7706a")
            return

        w, h = self._img_orig.size
        self._lbl_status.config(text=f"{Path(path).name}  ({w}×{h})", fg="#cdd6f4")
        self._btn_run.config(state="normal")
        self._clear_table()
        self._redraw()

    def _open_clipboard(self):
        """从剪切板读取图片（游戏截图后直接 Ctrl+C 粘贴即可）"""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
        except Exception as e:
            self._lbl_status.config(text=f"剪切板读取失败：{e}", fg="#f7706a")
            return

        if img is None:
            self._lbl_status.config(text="剪切板中没有图片，请先截图并复制", fg="#f9e2af")
            return

        if not isinstance(img, Image.Image):
            self._lbl_status.config(text=f"剪切板内容不是图片（{type(img).__name__}）", fg="#f9e2af")
            return

        self._img_orig = img.convert("RGB")
        w, h = self._img_orig.size
        self._lbl_status.config(text=f"剪切板图片  ({w}×{h})", fg="#89b4fa")
        self._btn_run.config(state="normal")
        self._clear_table()
        self._redraw()

        # 读取成功后自动触发识别（数据库已加载的情况下）
        if self._db is not None:
            self.after(100, self._run)

    # ── 画布渲染 ─────────────────────────────────────────────────────────────

    def _redraw(self, ocr_analysis: dict | None = None):
        """重绘底图 + 区域框（+ 可选 OCR 结果叠加）"""
        self._canvas.delete("all")

        # 底图
        if self._img_orig is not None:
            preview = self._img_orig.resize((PREVIEW_W, PREVIEW_H), Image.LANCZOS)
            self._tk_img = ImageTk.PhotoImage(preview)
            self._canvas.create_image(0, 0, anchor="nw", image=self._tk_img)
        else:
            self._canvas.create_text(PREVIEW_W // 2, PREVIEW_H // 2,
                                     text="请打开截图", fill="#585b70",
                                     font=("微软雅黑", 16))

        # game_area 白色虚线框（最先画，在区域框下面）
        ga_l, ga_t, ga_r, ga_b = self._game_area
        gx1 = int(ga_l * PREVIEW_W); gy1 = int(ga_t * PREVIEW_H)
        gx2 = int(ga_r * PREVIEW_W); gy2 = int(ga_b * PREVIEW_H)
        # 遮罩区：用半透明深色覆盖游戏区域外的部分
        for rx1, ry1, rx2, ry2 in [
            (0, 0, PREVIEW_W, gy1),          # 上
            (0, gy2, PREVIEW_W, PREVIEW_H),  # 下
            (0, gy1, gx1, gy2),              # 左
            (gx2, gy1, PREVIEW_W, gy2),      # 右
        ]:
            if rx2 > rx1 and ry2 > ry1:
                self._canvas.create_rectangle(rx1, ry1, rx2, ry2,
                                              fill="#000000", stipple="gray50",
                                              outline="", tags="gamearea_mask")
        # 虚线框边框
        self._canvas.create_rectangle(gx1, gy1, gx2, gy2,
                                      outline="#ffffff", width=2,
                                      dash=(6, 4), tags="gamearea")
        self._canvas.create_text(gx1 + 4, gy1 + 2, text="游戏画面范围",
                                 anchor="nw", fill="#ffffff",
                                 font=("微软雅黑", 8), tags="gamearea")
        # 四角把手
        for cx, cy in [(gx1, gy1), (gx2, gy1), (gx1, gy2), (gx2, gy2)]:
            self._canvas.create_oval(cx - HANDLE_R, cy - HANDLE_R,
                                     cx + HANDLE_R, cy + HANDLE_R,
                                     fill="#ffffff", outline="", tags="gamearea")

        # 区域框
        for key in REGION_KEYS:
            if key not in self._regions:
                continue
            x1, y1, x2, y2 = self._to_canvas(key)
            color = COLORS[key]

            # OCR 结果半透明叠加
            if ocr_analysis and key in ocr_analysis:
                match = ocr_analysis[key]["match"]
                score = ocr_analysis[key]["score"]
                if match:
                    oc = "#a6e3a1" if score >= 0.7 else ("#f9e2af" if score >= 0.4 else "#f38ba8")
                    self._canvas.create_rectangle(x1, y1, x2, y2,
                                                  fill=oc, stipple="gray25",
                                                  outline="", tags="ocr")
                    self._canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                                             text=match, fill="white",
                                             font=("微软雅黑", 9, "bold"), tags="ocr")

            # 边框
            self._canvas.create_rectangle(x1, y1, x2, y2,
                                          outline=color, width=2, tags="region")
            self._canvas.create_text(x1 + 4, y1 + 2, text=LABELS[key],
                                     anchor="nw", fill=color,
                                     font=("微软雅黑", 8), tags="region")

            # 角点把手
            for cx, cy in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
                self._canvas.create_oval(cx - HANDLE_R, cy - HANDLE_R,
                                         cx + HANDLE_R, cy + HANDLE_R,
                                         fill=color, outline="", tags="region")

        # 图例
        ex = 8
        for key, color in COLORS.items():
            lbl = LABELS[key]
            self._canvas.create_rectangle(ex, PREVIEW_H - 20, ex + 12, PREVIEW_H - 8,
                                          fill=color, outline="")
            self._canvas.create_text(ex + 16, PREVIEW_H - 14, text=lbl,
                                     anchor="w", fill=color, font=("微软雅黑", 9))
            ex += len(lbl) * 10 + 28

    def _to_canvas(self, key: str) -> tuple:
        """OCR 区域坐标转成画布坐标（已展开 game_area）"""
        ga_l, ga_t, ga_r, ga_b = self._game_area
        ga_w = ga_r - ga_l; ga_h = ga_b - ga_t
        l, t, r, b = self._regions[key]
        # 展开: 区域比例是相对于 game_area 内部的，转换到整张截图的 canvas 坐标
        ax1 = (ga_l + l * ga_w) * PREVIEW_W
        ay1 = (ga_t + t * ga_h) * PREVIEW_H
        ax2 = (ga_l + r * ga_w) * PREVIEW_W
        ay2 = (ga_t + b * ga_h) * PREVIEW_H
        return int(ax1), int(ay1), int(ax2), int(ay2)

    # ── 拖拽交互 ─────────────────────────────────────────────────────────────

    def _on_press(self, event):
        x, y = event.x, event.y

        # 优先检测 game_area 角点
        ga_l, ga_t, ga_r, ga_b = self._game_area
        gx1 = int(ga_l * PREVIEW_W); gy1 = int(ga_t * PREVIEW_H)
        gx2 = int(ga_r * PREVIEW_W); gy2 = int(ga_b * PREVIEW_H)
        for cx, cy, corner in [(gx1, gy1, "ga_tl"), (gx2, gy1, "ga_tr"),
                               (gx1, gy2, "ga_bl"), (gx2, gy2, "ga_br")]:
            if abs(x - cx) <= HANDLE_R + 3 and abs(y - cy) <= HANDLE_R + 3:
                self._drag = {"key": "_game_area", "mode": corner,
                              "ox": x, "oy": y, "orig": list(self._game_area)}
                return
        # game_area 边框内部整体移动
        if gx1 < x < gx2 and gy1 < y < gy2:
            # 冲突：如果点在某个子区域内则不触发 game_area 移动
            inside_sub = any(
                (self._to_canvas(k)[0] < x < self._to_canvas(k)[2] and
                 self._to_canvas(k)[1] < y < self._to_canvas(k)[3])
                for k in REGION_KEYS if k in self._regions
            )
            if not inside_sub:
                self._drag = {"key": "_game_area", "mode": "move",
                              "ox": x, "oy": y, "orig": list(self._game_area)}
                return

        # 检测子区域角点
        for key in REGION_KEYS:
            if key not in self._regions:
                continue
            x1, y1, x2, y2 = self._to_canvas(key)
            for cx, cy, corner in [(x1, y1, "tl"), (x2, y1, "tr"),
                                   (x1, y2, "bl"), (x2, y2, "br")]:
                if abs(x - cx) <= HANDLE_R + 3 and abs(y - cy) <= HANDLE_R + 3:
                    self._drag = {"key": key, "mode": corner,
                                  "ox": x, "oy": y, "orig": list(self._regions[key])}
                    return
        # 子区域内部移动
        for key in REGION_KEYS:
            if key not in self._regions:
                continue
            x1, y1, x2, y2 = self._to_canvas(key)
            if x1 < x < x2 and y1 < y < y2:
                self._drag = {"key": key, "mode": "move",
                              "ox": x, "oy": y, "orig": list(self._regions[key])}
                return

    def _on_drag(self, event):
        if not self._drag:
            return
        dx = (event.x - self._drag["ox"]) / PREVIEW_W
        dy = (event.y - self._drag["oy"]) / PREVIEW_H
        key  = self._drag["key"]
        mode = self._drag["mode"]

        if key == "_game_area":
            l, t, r, b = self._drag["orig"]
            w, h = r - l, b - t
            if mode == "move":
                nl = max(0.0, min(l + dx, 1.0 - w))
                nt = max(0.0, min(t + dy, 1.0 - h))
                self._game_area = (nl, nt, nl + w, nt + h)
            elif mode == "ga_tl":
                self._game_area = (max(0.0, min(l + dx, r - 0.01)),
                                   max(0.0, min(t + dy, b - 0.01)), r, b)
            elif mode == "ga_tr":
                self._game_area = (l, max(0.0, min(t + dy, b - 0.01)),
                                   min(1.0, max(r + dx, l + 0.01)), b)
            elif mode == "ga_bl":
                self._game_area = (max(0.0, min(l + dx, r - 0.01)), t,
                                   r, min(1.0, max(b + dy, t + 0.01)))
            elif mode == "ga_br":
                self._game_area = (l, t,
                                   min(1.0, max(r + dx, l + 0.01)),
                                   min(1.0, max(b + dy, t + 0.01)))
        else:
            l, t, r, b = self._drag["orig"]
            if mode == "move":
                w, h = r - l, b - t
                nl = max(0.0, min(l + dx, 1.0 - w))
                nt = max(0.0, min(t + dy, 1.0 - h))
                self._regions[key] = (nl, nt, nl + w, nt + h)
            elif mode == "tl":
                self._regions[key] = (max(0.0, min(l + dx, r - 0.01)),
                                      max(0.0, min(t + dy, b - 0.01)), r, b)
            elif mode == "tr":
                self._regions[key] = (l, max(0.0, min(t + dy, b - 0.01)),
                                      min(1.0, max(r + dx, l + 0.01)), b)
            elif mode == "bl":
                self._regions[key] = (max(0.0, min(l + dx, r - 0.01)), t,
                                      r, min(1.0, max(b + dy, t + 0.01)))
            elif mode == "br":
                self._regions[key] = (l, t,
                                      min(1.0, max(r + dx, l + 0.01)),
                                      min(1.0, max(b + dy, t + 0.01)))
        self._redraw()

    def _on_release(self, _event):
        self._drag = None

    # ── 识别 ─────────────────────────────────────────────────────────────────

    def _run(self):
        if self._img_orig is None or self._db is None:
            return
        self._lbl_status.config(text="识别中……", fg="#f9e2af")
        self.update()
        try:
            from roco.analyzer import analyze_image
            analysis = analyze_image(
                self._img_orig, self._db,
                self._spirit_names, self._skill_names,
                regions_ratio=self._regions,
                game_area=self._game_area)
        except Exception as e:
            self._lbl_status.config(text=f"识别失败：{e}", fg="#f7706a")
            return

        self._redraw(ocr_analysis=analysis)
        self._fill_table(analysis)
        self._lbl_status.config(text="识别完成", fg="#4ac97e")

    # ── 表格 ─────────────────────────────────────────────────────────────────

    def _clear_table(self):
        for row in self._tree.get_children():
            self._tree.delete(row)

    def _fill_table(self, analysis: dict):
        self._clear_table()
        for key in REGION_KEYS:
            info  = analysis[key]
            raw   = " / ".join(info["raw"]) if info["raw"] else "—"
            match = info["match"] or "未识别"
            score = f'{info["score"]:.0%}'
            tag   = "ok" if info["score"] >= 0.7 else ("warn" if info["score"] >= 0.4 else "bad")
            self._tree.insert("", "end", values=(LABELS[key], raw, match, score), tags=(tag,))

        self._tree.tag_configure("ok",   foreground="#a6e3a1")
        self._tree.tag_configure("warn", foreground="#f9e2af")
        self._tree.tag_configure("bad",  foreground="#f38ba8")


def main():
    init = sys.argv[1] if len(sys.argv) > 1 else None
    app  = OcrDemo(init_path=init)
    app.mainloop()


if __name__ == "__main__":
    main()


class OcrDemo(tk.Tk):
    def __init__(self, init_path: str | None = None):
        super().__init__()
        self.title("OCR 识别 Demo")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)

        self._img_orig: Image.Image | None = None
        self._tk_img: ImageTk.PhotoImage | None = None
        self._db = self._spirit_names = self._skill_names = None

        self._build_ui()
        self._load_db_async()

        if init_path:
            self.after(200, lambda: self._open(init_path))

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        top = tk.Frame(self, bg="#1e1e2e")
        top.pack(fill="x", padx=12, pady=(12, 6))

        btn_open = tk.Button(
            top, text="📂  打开截图", command=self._open,
            bg="#7c6af7", fg="white", relief="flat",
            font=("微软雅黑", 11), padx=14, pady=6, cursor="hand2",
        )
        btn_open.pack(side="left")

        self._btn_run = tk.Button(
            top, text="▶  开始识别", command=self._run,
            bg="#4ac97e", fg="#1e1e2e", relief="flat",
            font=("微软雅黑", 11, "bold"), padx=14, pady=6, cursor="hand2",
            state="disabled",
        )
        self._btn_run.pack(side="left", padx=(8, 0))

        self._lbl_status = tk.Label(
            top, text="尚未加载截图", bg="#1e1e2e", fg="#888",
            font=("微软雅黑", 10),
        )
        self._lbl_status.pack(side="left", padx=12)

        # 预览画布
        canvas_frame = tk.Frame(self, bg="#2a2a3e", bd=0)
        canvas_frame.pack(padx=12, pady=4)

        self._canvas = tk.Canvas(
            canvas_frame, width=PREVIEW_W, height=PREVIEW_H,
            bg="#2a2a3e", highlightthickness=0,
        )
        self._canvas.pack()

        # 结果表格
        result_frame = tk.Frame(self, bg="#1e1e2e")
        result_frame.pack(fill="x", padx=12, pady=(6, 12))

        cols = ("区域", "OCR 原文", "匹配结果", "置信度")
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Demo.Treeview",
            background="#2a2a3e", foreground="#cdd6f4",
            fieldbackground="#2a2a3e", rowheight=26,
            font=("微软雅黑", 10),
        )
        style.configure(
            "Demo.Treeview.Heading",
            background="#313244", foreground="#cba6f7",
            font=("微软雅黑", 10, "bold"),
        )
        style.map("Demo.Treeview", background=[("selected", "#45475a")])

        self._tree = ttk.Treeview(
            result_frame, columns=cols, show="headings",
            height=6, style="Demo.Treeview",
        )
        for c, w in zip(cols, [90, 240, 160, 70]):
            self._tree.heading(c, text=c)
            self._tree.column(c, width=w, anchor="center" if c != "OCR 原文" else "w")
        self._tree.pack(fill="x")

    # ── 数据加载 ─────────────────────────────────────────────────────────────

    def _load_db_async(self):
        self._lbl_status.config(text="正在加载精灵数据库……")
        self.after(50, self._do_load_db)

    def _do_load_db(self):
        try:
            from roco.analyzer import load_db
            self._db, self._spirit_names, self._skill_names = load_db()
            self._lbl_status.config(
                text=f"已加载 {len(self._db)} 只精灵 · {len(self._skill_names)} 个技能",
                fg="#4ac97e",
            )
        except Exception as e:
            self._lbl_status.config(text=f"数据库加载失败：{e}", fg="#f7706a")

    # ── 打开图片 ─────────────────────────────────────────────────────────────

    def _open(self, path: str | None = None):
        if path is None:
            path = filedialog.askopenfilename(
                title="选择对战截图",
                filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp"), ("所有文件", "*.*")],
            )
        if not path:
            return
        try:
            self._img_orig = Image.open(path).convert("RGB")
        except Exception as e:
            self._lbl_status.config(text=f"打开失败：{e}", fg="#f7706a")
            return

        self._lbl_status.config(
            text=f"{Path(path).name}  ({self._img_orig.width}×{self._img_orig.height})",
            fg="#cdd6f4",
        )
        self._btn_run.config(state="normal")
        self._draw_preview(annotate=False)
        self._clear_table()

    # ── 预览绘制 ─────────────────────────────────────────────────────────────

    def _draw_preview(self, annotate: bool = False, analysis: dict | None = None):
        if self._img_orig is None:
            return
        preview = self._img_orig.copy()
        sw = preview.width  / 2560
        sh = preview.height / 1440

        from roco.analyzer import REGION_2560
        draw = ImageDraw.Draw(preview)
        for key, (l, t, r, b) in REGION_2560.items():
            sl = int(l * sw); st = int(t * sh)
            sr = int(r * sw); sb = int(b * sh)
            color = COLORS.get(key, "#ffffff")
            draw.rectangle([sl, st, sr, sb], outline=color, width=max(2, int(preview.width / 500)))
            if annotate and analysis and analysis[key]["match"]:
                draw.text((sl + 2, st + 2), analysis[key]["match"], fill=color)

        preview = preview.resize((PREVIEW_W, PREVIEW_H), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(preview)
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

        # 图例
        x = 8
        for key, color in COLORS.items():
            lbl = LABELS[key]
            self._canvas.create_rectangle(x, PREVIEW_H - 20, x + 12, PREVIEW_H - 8, fill=color, outline="")
            self._canvas.create_text(x + 16, PREVIEW_H - 14, text=lbl, anchor="w", fill=color, font=("微软雅黑", 9))
            x += len(lbl) * 10 + 28

    # ── 识别 ─────────────────────────────────────────────────────────────────

    def _run(self):
        if self._img_orig is None or self._db is None:
            return
        self._lbl_status.config(text="识别中……", fg="#f9e2af")
        self.update()
        try:
            from roco.analyzer import analyze_image
            analysis = analyze_image(
                self._img_orig, self._db,
                self._spirit_names, self._skill_names,
            )
        except Exception as e:
            self._lbl_status.config(text=f"识别失败：{e}", fg="#f7706a")
            return

        self._draw_preview(annotate=True, analysis=analysis)
        self._fill_table(analysis)
        self._lbl_status.config(text="识别完成", fg="#4ac97e")

    # ── 表格 ─────────────────────────────────────────────────────────────────

    def _clear_table(self):
        for row in self._tree.get_children():
            self._tree.delete(row)

    def _fill_table(self, analysis: dict):
        self._clear_table()
        for key in ("self_name", "enemy_name", "skill1", "skill2", "skill3", "skill4"):
            info  = analysis[key]
            raw   = " / ".join(info["raw"]) if info["raw"] else "—"
            match = info["match"] or "未识别"
            score = f'{info["score"]:.0%}'
            tag   = "ok" if info["score"] >= 0.7 else ("warn" if info["score"] >= 0.4 else "bad")
            self._tree.insert("", "end", values=(LABELS[key], raw, match, score), tags=(tag,))

        self._tree.tag_configure("ok",   foreground="#a6e3a1")
        self._tree.tag_configure("warn", foreground="#f9e2af")
        self._tree.tag_configure("bad",  foreground="#f38ba8")


def main():
    init = sys.argv[1] if len(sys.argv) > 1 else None
    app  = OcrDemo(init_path=init)
    app.mainloop()


if __name__ == "__main__":
    main()
