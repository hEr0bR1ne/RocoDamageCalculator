"""
RocoDamageCalculator — 启动器
统一入口，点击按钮启动各个工具。
"""
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

_IS_FROZEN = getattr(sys, "frozen", False)

# ── 监控窗口位置/尺寸持久化 ────────────────────────────────────────────────────
_WATCH_GEO_FILE = Path(__file__).parent / "data" / "watch_geometry.json"


def _geo_load() -> str | None:
    """读取上次保存的 WatchWindow geometry 字符串，如 '460x900+2080+50'。"""
    try:
        import json
        return json.loads(_WATCH_GEO_FILE.read_text(encoding="utf-8")).get("geometry")
    except Exception:
        return None


def _geo_save(geometry: str) -> None:
    """将 WatchWindow geometry 字符串写入持久化文件。"""
    try:
        import json
        _WATCH_GEO_FILE.parent.mkdir(parents=True, exist_ok=True)
        _WATCH_GEO_FILE.write_text(
            json.dumps({"geometry": geometry}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


# ── DPI 感知（必须在任何 Tk 窗口创建之前设置）──────────────────────────────────
# PROCESS_SYSTEM_DPI_AWARE = 1：让 Windows 以物理像素汇报坐标，
# 避免 Windows 对进程做虚拟化缩放，杜绝窗口偶发跳变。
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


_CJK_FONT_CACHE: tuple[str, int] | None = None


def _pick_cjk_font() -> tuple[str, int]:
    """
    选一个系统中支持中文的等宽/近等宽字体，找不到则退回 Consolas。
    结果缓存在模块级变量中，保证 Tk() 初始化只执行一次，
    避免在已有 Tk 根窗口的情况下反复创建/销毁临时 Tk() 导致现有窗口几何信息丢失。
    """
    global _CJK_FONT_CACHE
    if _CJK_FONT_CACHE is not None:
        return _CJK_FONT_CACHE
    from tkinter import font as _tkfont
    try:
        # 如果 Tk 根已存在（在主窗口生命周期内），直接查询字体列表，无需创建第二个 Tk()
        available = set(_tkfont.families())
    except Exception:
        # Tk 尚未初始化时才创建临时根（仅在模块最早一次调用时触发）
        import tkinter as _tk
        _r = _tk.Tk()
        _r.withdraw()
        available = set(_tkfont.families())
        _r.destroy()
    for name in ("Noto Sans Mono CJK SC", "Sarasa Mono SC", "Cascadia Code",
                 "Microsoft YaHei Mono", "Noto Sans SC",
                 "Microsoft YaHei UI", "Microsoft JhengHei UI", "Consolas"):
        if name in available:
            _CJK_FONT_CACHE = (name, 9)
            return _CJK_FONT_CACHE
    _CJK_FONT_CACHE = ("TkFixedFont", 9)
    return _CJK_FONT_CACHE


def _tool_dispatch() -> None:
    """
    打包为 exe 后，以 RocoLauncher.exe --tool <name> [args...] 方式启动时，
    直接运行对应工具模块，然后退出。
    供 launcher 通过 subprocess 调用子工具时使用（无需额外 Python 环境）。
    """
    if not _IS_FROZEN:
        return
    if len(sys.argv) < 3 or sys.argv[1] != "--tool":
        return

    tool = sys.argv[2]
    sys.argv = [sys.argv[0]] + sys.argv[3:]   # 其余参数交给工具自己解析

    if tool == "damage-gui":
        import damage_gui
        app = damage_gui.App()
        app.mainloop()

    elif tool == "analyzer":
        from roco.analyzer import main as _main
        try:
            _main()
        except KeyboardInterrupt:
            pass

    elif tool == "analyzer-watch":
        import sys as _s
        _s.argv = [_s.argv[0], "--watch", "--window", "洛克王国：世界",
                   "--region", "0,40,1920,1080"]
        from roco.analyzer import main as _main
        try:
            _main()
        except KeyboardInterrupt:
            pass

    elif tool == "damage-calc":
        # GUI 子系统进程，需显式分配控制台窗口才能交互
        import ctypes
        ctypes.windll.kernel32.AllocConsole()
        sys.stdin  = open("CONIN$",  "r")
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = sys.stdout
        from roco.calculator import interactive
        interactive()

    elif tool == "spirit-scraper":
        from roco.scraper.spirits import main as _main
        _main()

    elif tool == "skill-scraper":
        from roco.scraper.skills import main as _main
        _main()

    sys.exit(0)


_tool_dispatch()  # 必须在 Tk 初始化之前执行


def _resolve_root_and_python() -> tuple[Path, str]:
    """
    打包为 exe 后 sys.executable 指向 exe 自身，需要找到 .venv 里的真实 Python。
    搜索顺序：exe 所在目录 → 上一级目录（dist/ 的情况）。
    未打包时直接用 sys.executable。
    """
    if not getattr(sys, "frozen", False):
        return Path(__file__).parent, sys.executable

    exe_dir = Path(sys.executable).parent
    for candidate in [exe_dir, exe_dir.parent]:
        venv_py = candidate / ".venv" / "Scripts" / "python.exe"
        if venv_py.exists():
            return candidate, str(venv_py)

    # 找不到 venv，回退到系统 python（会提示错误，但至少不会死循环）
    return exe_dir, "python"


ROOT, PYTHON = _resolve_root_and_python()

# ── 配色（与 damage_gui.py 一致）─────────────────────────────────────────────
BG      = "#1e1e2e"
PANEL   = "#2a2a3e"
ACCENT  = "#7c6af7"
TEXT    = "#cdd6f4"
SUBTEXT = "#a6adc8"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
YELLOW  = "#f9e2af"
BORDER  = "#45475a"
ORANGE  = "#fab387"


class ToolCard(tk.Frame):
    """单个工具的卡片：标题 + 描述 + 启动按钮 + 状态指示"""

    def __init__(self, parent, title: str, desc: str, action, btn_text="启动", btn_color=ACCENT):
        super().__init__(parent, bg=PANEL, highlightthickness=1,
                         highlightbackground=BORDER)
        self._proc: subprocess.Popen | None = None
        self._action = action

        # 左侧文字
        info = tk.Frame(self, bg=PANEL)
        info.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        tk.Label(info, text=title, bg=PANEL, fg=TEXT,
                 font=("微软雅黑", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(info, text=desc, bg=PANEL, fg=SUBTEXT,
                 font=("微软雅黑", 9), anchor="w", wraplength=420,
                 justify="left").pack(fill="x")

        # 右侧按钮 + 状态
        right = tk.Frame(self, bg=PANEL)
        right.pack(side="right", padx=12, pady=10)

        self._status_var = tk.StringVar(value="●  未运行")
        self._status_lbl = tk.Label(right, textvariable=self._status_var,
                                    bg=PANEL, fg=SUBTEXT,
                                    font=("微软雅黑", 8))
        self._status_lbl.pack(anchor="e")

        self._btn = tk.Button(right, text=btn_text, command=self._launch,
                              bg=btn_color, fg="white", relief="flat",
                              font=("微软雅黑", 10, "bold"),
                              padx=16, pady=4, cursor="hand2",
                              activebackground=btn_color)
        self._btn.pack(pady=(4, 0))

    def _launch(self):
        self._action(self)

    def set_running(self, running: bool):
        if running:
            self._status_var.set("● 运行中")
            self._status_lbl.config(fg=GREEN)
            self._btn.config(text="停止", bg=RED,
                             command=self._stop, activebackground=RED)
        else:
            self._status_var.set("●  未运行")
            self._status_lbl.config(fg=SUBTEXT)
            self._btn.config(text="启动", bg=ACCENT,
                             command=self._launch, activebackground=ACCENT)

    def _stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
        self.set_running(False)

    def watch_proc(self, proc: subprocess.Popen):
        """后台线程监视进程，结束后自动更新状态。"""
        self._proc = proc
        self.set_running(True)

        def _watch():
            proc.wait()
            self._proc = None
            self.after(0, lambda: self.set_running(False))

        threading.Thread(target=_watch, daemon=True).start()


class OutputWindow(tk.Toplevel):
    """悬浮输出窗口，显示子进程的 stdout/stderr。"""

    # ── 文字着色规则（前缀匹配，优先级从高到低）──────────────────────────────
    _TAG_RULES: list[tuple[str, str, dict]] = [
        # (匹配串, tag名, tag配置)
        ("=",   "header",  {"foreground": ACCENT,  "font": ("", 10, "bold")}),
        ("─",   "sep",     {"foreground": BORDER}),
        ("  己方精灵", "self_lbl", {"foreground": SUBTEXT}),
        ("  对方精灵", "emy_lbl",  {"foreground": SUBTEXT}),
        (" [√]","ok",      {"foreground": GREEN}),
        (" [?]","warn",    {"foreground": YELLOW}),
        (" [×]","err",     {"foreground": RED}),
        (" ->", "result",  {"foreground": ORANGE, "font": ("", 10, "bold")}),
        ("  ->","result",  {"foreground": ORANGE, "font": ("", 10, "bold")}),
        ("  [自动","info", {"foreground": SUBTEXT}),
        ("  [error","errmsg",{"foreground": RED}),
        ("  [capture","cap",{"foreground": SUBTEXT}),
    ]

    def __init__(self, parent, title: str, geometry: str | None = None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG)
        self.geometry(geometry or "760x420")
        self.resizable(True, True)

        # ── 标题栏 ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=ACCENT, height=28)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        tk.Label(hdr, text=title, bg=ACCENT, fg="white",
                 font=("微软雅黑", 9, "bold"), anchor="w",
                 padx=10).pack(side="left", fill="y")

        tk.Button(hdr, text="✕", bg=ACCENT, fg="white", relief="flat",
                  font=("微软雅黑", 10), padx=8, pady=0, cursor="hand2",
                  activebackground=RED, activeforeground="white",
                  command=self.destroy).pack(side="right", fill="y")

        # ── 文本区 ────────────────────────────────────────────────────────────
        _fname, _fsize = _pick_cjk_font()
        _font_normal = (_fname, 10)

        self.text = scrolledtext.ScrolledText(
            self, bg="#11111b", fg=TEXT, font=_font_normal,
            insertbackground=TEXT, relief="flat", borderwidth=0,
            wrap="word", padx=8, pady=6,
            selectbackground=ACCENT, selectforeground="white",
        )
        self.text.pack(fill="both", expand=True, padx=0, pady=0)
        self.text.config(state="disabled")

        # 注册着色 tag
        for _, tag, cfg in self._TAG_RULES:
            full = dict(cfg)
            if "font" in full:
                fn, fs, *fw = full["font"]
                full["font"] = (_fname if fn == "" else fn, fs, *fw)
            self.text.tag_configure(tag, **full)

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")

    def append(self, line: str):
        # \x0c (form-feed) 是清屏哨兵
        if "\x0c" in line:
            self.clear()
            line = line.replace("\x0c", "")
            if not line:
                return

        # 选择着色 tag
        tag = None
        stripped = line.rstrip("\n")
        for prefix, t, _ in self._TAG_RULES:
            if stripped.startswith(prefix) or stripped.lstrip().startswith(prefix.lstrip()):
                tag = t
                break

        self.text.config(state="normal")
        if tag:
            self.text.insert("end", line, tag)
        else:
            self.text.insert("end", line)
        self.text.see("end")
        self.text.config(state="disabled")


# ─────────────────────────────────────────────────────────────────────────────
# 监控窗口位置校准器
# ─────────────────────────────────────────────────────────────────────────────

class GeometryCalibrator(tk.Toplevel):
    """
    半透明占位窗口：拖动/缩放到合适位置后点击「保存」，
    结果写入 data/watch_geometry.json，下次 WatchWindow 直接复用。
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("校准监控窗口位置")
        self.configure(bg=ACCENT)
        self.attributes("-alpha", 0.55)
        self.resizable(True, True)

        # 先用保存值，否则用默认值
        saved = _geo_load()
        if saved:
            self.geometry(saved)
        else:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            win_w = max(440, int(sw * 0.18))
            win_h = min(sh - 40, int(sh * 0.90))
            win_x = sw - win_w - 8
            win_y = (sh - win_h) // 2
            self.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")

        # 提示文字
        tk.Label(
            self,
            text="拖动 / 缩放此窗口到理想位置\n然后点击「保存」",
            bg=ACCENT, fg="white",
            font=("微软雅黑", 13, "bold"),
            justify="center",
        ).pack(expand=True)

        btn_row = tk.Frame(self, bg=ACCENT)
        btn_row.pack(pady=12)
        tk.Button(
            btn_row, text="✔  保存",
            bg="white", fg=ACCENT,
            font=("微软雅黑", 11, "bold"),
            relief="flat", padx=18, pady=6, cursor="hand2",
            command=self._save,
        ).pack(side="left", padx=8)
        tk.Button(
            btn_row, text="✕  取消",
            bg=RED, fg="white",
            font=("微软雅黑", 11, "bold"),
            relief="flat", padx=18, pady=6, cursor="hand2",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _save(self):
        geo = self.geometry()          # e.g. "460x900+2080+50"
        _geo_save(geo)
        self.destroy()
        # 弹出提示
        import tkinter.messagebox as mb
        mb.showinfo("已保存", f"监控窗口位置已保存：\n{geo}\n\n下次开启自动监控将自动应用。")


# ─────────────────────────────────────────────────────────────────────────────
# 自动监控 GUI 窗口
# ─────────────────────────────────────────────────────────────────────────────

class WatchWindow(tk.Toplevel):
    """
    自动监控专用悬浮窗：进程内直接运行 GameWatcher，结果以卡片形式展示。
    无需子进程/stdout解析，结果完全结构化、可交互。
    """

    _SCORE_COLOR = [
        (0.8, GREEN),
        (0.4, YELLOW),
        (0.0, RED),
    ]

    # 常用分辨率预设：(label, width, height)
    _RES_PRESETS = [
        ("自动",    None,  None),
        ("1280×720",  1280,  720),
        ("1600×900",  1600,  900),
        ("1920×1080", 1920, 1080),
        ("2560×1440", 2560, 1440),
    ]

    def __init__(self, parent, card: "ToolCard"):
        super().__init__(parent)
        self._card    = card
        self._watcher = None
        self._db = self._spirit_names = self._skill_names = None
        # 目标分辨率：None=自动（保持原始尺寸），或 (width, height)
        self._game_res: tuple[int,int] | None = None

        self.title("对战分析 — 自动监控")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._set_geometry()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        threading.Thread(target=self._load_db, daemon=True).start()

    # 基准窗口宽：2560×1440 环境下 18% 屏宽≈460px，字号就是基于这个宽度设计的
    _BASE_WIN_W = 460

    def _set_geometry(self):
        # 优先使用用户校准过的值
        saved = _geo_load()
        if saved:
            self.geometry(saved)
            try:
                win_w = int(saved.split("x")[0])
            except Exception:
                win_w = self._BASE_WIN_W
        else:
            # 默认值：贴右边缘
            self.update_idletasks()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            win_w = max(440, int(sw * 0.18))
            win_h = min(sh - 40, int(sh * 0.90))
            win_x = sw - win_w - 8
            win_y = (sh - win_h) // 2
            self.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
        # 字号缩放比（限制在合理范围）
        self._fscale = max(0.65, min(1.5, win_w / self._BASE_WIN_W))

    def _build_ui(self):
        fn, _ = _pick_cjk_font()
        sc = self._fscale  # 字号缩放比

        def F(size, bold=False):
            s = max(8, round(size * sc))
            return (fn, s, "bold") if bold else (fn, s)

        # ── 顶栏 ─────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=ACCENT, height=max(32, round(48 * sc)))
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚔  对战分析  自动监控", bg=ACCENT, fg="white",
                 font=F(20, True), anchor="w", padx=10).pack(side="left", fill="y")
        self._status_dot = tk.Label(hdr, text="● 等待中", bg=ACCENT, fg="white",
                                    font=F(16), padx=6)
        self._status_dot.pack(side="left", fill="y")
        tk.Button(hdr, text="✕", bg=ACCENT, fg="white", relief="flat",
                  font=F(18), padx=10, cursor="hand2",
                  activebackground=RED, activeforeground="white",
                  command=self._on_close).pack(side="right", fill="y")

        # ── 游戏分辨率设置行 ──────────────────────────────────────────────────
        res_row = tk.Frame(self, bg=PANEL)
        res_row.pack(fill="x", padx=8, pady=(4, 0))
        tk.Label(res_row, text="游戏分辨率：", bg=PANEL, fg=SUBTEXT,
                 font=F(10)).pack(side="left", padx=(6, 2))

        self._res_var = tk.StringVar(value="自动")
        self._res_btns: list[tk.Button] = []

        def _make_res_btn(label, w, h):
            def _select():
                self._game_res = (w, h) if w else None
                self._res_var.set(label)
                for b in self._res_btns:
                    b.config(relief="flat",
                             bg=ACCENT if b.cget("text") == label else PANEL,
                             fg="white" if b.cget("text") == label else SUBTEXT)
                self._log_append(f"分辨率设为: {label}")
            btn = tk.Button(res_row, text=label, command=_select,
                            bg=ACCENT if label == "自动" else PANEL,
                            fg="white" if label == "自动" else SUBTEXT,
                            font=F(9), relief="flat",
                            padx=6, pady=2, cursor="hand2",
                            activebackground=ACCENT, activeforeground="white")
            btn.pack(side="left", padx=2)
            self._res_btns.append(btn)

        for lbl, w, h in self._RES_PRESETS:
            _make_res_btn(lbl, w, h)

        # 自定义输入
        tk.Label(res_row, text="自定义:", bg=PANEL, fg=SUBTEXT,
                 font=F(9)).pack(side="left", padx=(8, 2))
        self._custom_w = tk.Entry(res_row, width=5, bg="#11111b", fg=TEXT,
                                  font=F(9), insertbackground=TEXT, relief="flat")
        self._custom_w.pack(side="left")
        self._custom_w.insert(0, "1920")
        tk.Label(res_row, text="×", bg=PANEL, fg=SUBTEXT,
                 font=F(9)).pack(side="left")
        self._custom_h = tk.Entry(res_row, width=5, bg="#11111b", fg=TEXT,
                                  font=F(9), insertbackground=TEXT, relief="flat")
        self._custom_h.pack(side="left")
        self._custom_h.insert(0, "1080")
        tk.Button(res_row, text="✔", command=self._apply_custom_res,
                  bg=PANEL, fg=GREEN, font=F(9), relief="flat",
                  padx=4, cursor="hand2",
                  activebackground=GREEN, activeforeground="white").pack(side="left", padx=(2, 0))

        # 实际检测尺寸标签
        self._detected_var = tk.StringVar(value="")
        tk.Label(res_row, textvariable=self._detected_var,
                 bg=PANEL, fg=SUBTEXT, font=F(9)).pack(side="right", padx=6)

        # ── 精灵信息行 ────────────────────────────────────────────────────────
        spirit_row = tk.Frame(self, bg=PANEL, pady=6)
        spirit_row.pack(fill="x", padx=8, pady=(6, 0))

        # 左侧：己方
        self_col = tk.Frame(spirit_row, bg=PANEL)
        self_col.pack(side="left", padx=8)
        self._self_var = tk.StringVar(value="己方：—")
        tk.Label(self_col, textvariable=self._self_var,
                 bg=PANEL, fg=GREEN, font=F(16, True)).pack(anchor="w")

        # 右侧：敌方（名称 + 血量）
        enemy_col = tk.Frame(spirit_row, bg=PANEL)
        enemy_col.pack(side="left", padx=8)
        self._enemy_var = tk.StringVar(value="敌方：—")
        tk.Label(enemy_col, textvariable=self._enemy_var,
                 bg=PANEL, fg=RED, font=F(16, True)).pack(anchor="w")
        self._enemy_hp_var   = tk.StringVar(value="")
        self._enemy_hp_label = tk.Label(enemy_col, textvariable=self._enemy_hp_var,
                                        bg=PANEL, fg=GREEN, font=F(20, True))
        self._enemy_hp_label.pack(anchor="w")

        # ── 技能卡区域 ────────────────────────────────────────────────────────
        skills_frame = tk.Frame(self, bg=BG)
        skills_frame.pack(fill="both", expand=True, padx=8, pady=6)
        skills_frame.columnconfigure(0, weight=1)

        self._skill_cards: list[dict] = []
        for i in range(4):
            skills_frame.rowconfigure(i, weight=1)
            cf = tk.Frame(skills_frame, bg=PANEL,
                          highlightthickness=1, highlightbackground=BORDER)
            cf.grid(row=i, column=0, sticky="nsew", pady=2)

            top_row = tk.Frame(cf, bg=PANEL)
            top_row.pack(fill="x", padx=10, pady=(6, 2))

            tk.Label(top_row, text=f"技能 {i+1}",
                     bg=PANEL, fg=SUBTEXT, font=F(20, True)).pack(side="left")

            name_var = tk.StringVar(value="—")
            name_lbl = tk.Label(top_row, textvariable=name_var,
                                bg=PANEL, fg=TEXT, font=F(14))
            name_lbl.pack(side="left", padx=(6, 0))

            cat_var = tk.StringVar(value="")
            tk.Label(top_row, textvariable=cat_var,
                     bg=PANEL, fg=SUBTEXT, font=F(14)).pack(side="left", padx=(6, 0))

            conf_var = tk.StringVar(value="")
            tk.Label(top_row, textvariable=conf_var,
                     bg=PANEL, fg=SUBTEXT, font=F(14)).pack(side="right")

            dmg_row = tk.Frame(cf, bg=PANEL)
            dmg_row.pack(fill="x", padx=10, pady=(0, 6))

            dmg_var = tk.StringVar(value="")
            tk.Label(dmg_row, textvariable=dmg_var,
                     bg=PANEL, fg=ORANGE, font=F(32, True)).pack(side="left")

            pct_var = tk.StringVar(value="")
            tk.Label(dmg_row, textvariable=pct_var,
                     bg=PANEL, fg=YELLOW, font=F(18)).pack(side="left", padx=(8, 0))

            meta_var = tk.StringVar(value="")
            tk.Label(dmg_row, textvariable=meta_var,
                     bg=PANEL, fg=SUBTEXT, font=F(14)).pack(side="right")

            self._skill_cards.append({
                "name": name_var, "name_lbl": name_lbl,
                "cat": cat_var,   "conf": conf_var,
                "dmg": dmg_var,   "pct": pct_var,  "meta": meta_var,
            })

        # ── 底部日志栏 ────────────────────────────────────────────────────────
        self._log = tk.Text(self, bg="#11111b", fg=SUBTEXT, font=F(11),
                            height=3, relief="flat", state="disabled",
                            wrap="word", padx=6, pady=4)
        self._log.pack(fill="x")

    # ── 数据库加载 ────────────────────────────────────────────────────────────

    def _load_db(self):
        try:
            self._log_append("正在加载精灵数据库…")
            from roco.analyzer import load_db, analyze_image, best_match, calc_quick_damage
            self._db, self._spirit_names, self._skill_names = load_db()
            self._analyze_image = analyze_image
            self._best_match    = best_match
            self._calc_quick    = calc_quick_damage
            self._log_append(f"已加载 {len(self._db)} 只精灵，开始监控…")
            self.after(0, self._start_watcher)
        except Exception as e:
            self._log_append(f"[错误] 数据库加载失败：{e}")

    def _apply_custom_res(self):
        """读取自定义宽高输入框，应用为目标分辨率。"""
        try:
            w = int(self._custom_w.get().strip())
            h = int(self._custom_h.get().strip())
            assert w > 0 and h > 0
        except Exception:
            self._log_append("[错误] 分辨率格式无效，请输入正整数（如 1920 × 1080）")
            return
        self._game_res = (w, h)
        self._res_var.set(f"{w}×{h}")
        for b in self._res_btns:
            b.config(relief="flat", bg=PANEL, fg=SUBTEXT)
        self._log_append(f"分辨率设为自定义: {w}×{h}")

    def _normalize_frame(self, img):
        """按目标分辨率缩放帧；None=保持原尺寸（自动模式）。"""
        if self._game_res is None:
            return img
        tw, th = self._game_res
        if img.size == (tw, th):
            return img
        return img.resize((tw, th), resample=1)  # BILINEAR

    def _start_watcher(self):
        from roco.capture import GameWatcher
        # 不传固定 region，让 grab_window 自动按实际窗口大小截取
        # 分辨率，从而支持任意窗口尺寸和全屏/窗口化模式
        self._watcher = GameWatcher(
            on_change=self._on_frame,
            window_title="洛克王国：世界",
        )
        self._watcher.start()
        self._card.set_running(True)
        self._poll_status()

    # ── 帧回调（后台线程）────────────────────────────────────────────────────

    def _on_frame(self, img):
        if self._db is None:
            return
        try:
            # 更新实际检测到的尺寸显示
            raw_w, raw_h = img.size
            self.after(0, lambda: self._detected_var.set(f"检测到: {raw_w}×{raw_h}"))

            # 按目标分辨率归一化（自动模式保持原尺寸）
            img = self._normalize_frame(img)

            skill_keys = ["skill1", "skill2", "skill3", "skill4"]
            analysis = self._analyze_image(
                img, self._db, self._spirit_names, self._skill_names)

            self_name  = analysis["self_name"]["match"] or "未识别"
            raw_enemy  = analysis["enemy_name"]["raw"]
            enemy_name, enemy_score = self._best_match(raw_enemy, self._spirit_names)
            if enemy_score < 0.7:
                enemy_name = None
            enemy_display = enemy_name or ("、".join(raw_enemy) or "未识别")

            # 敌方血量百分比
            enemy_hp = analysis.get("enemy_hp", {}).get("match")  # int 0-100 或 None

            rows = self._calc_quick(
                self_name, enemy_name or "", analysis, skill_keys, self._db)

            self.after(0, lambda sn=self_name, en=enemy_display, hp=enemy_hp, rw=rows:
                       self._update_ui(sn, en, hp, rw))
        except Exception as e:
            import traceback
            self._log_append(f"[错误] {e}\n{traceback.format_exc()}")

    # ── UI 更新（主线程）─────────────────────────────────────────────────────

    def _update_ui(self, self_name: str, enemy_name: str, enemy_hp: int | None, rows: list):
        self._self_var.set(f"⚔ {self_name}")
        self._enemy_var.set(f"🛡 {enemy_name}")

        # 血量显示并配色
        if enemy_hp is not None:
            hp = max(0, min(100, enemy_hp))
            if hp > 60:
                hp_color = GREEN
            elif hp > 30:
                hp_color = YELLOW
            else:
                hp_color = RED
            self._enemy_hp_var.set(f"🟥 {hp}% HP")
            self._enemy_hp_label.config(fg=hp_color)
        else:
            self._enemy_hp_var.set("")

        for r, c in zip(rows, self._skill_cards):
            score = r.get("score", 0)
            color = next(col for thr, col in self._SCORE_COLOR if score >= thr)
            c["name"].set(r["name"])
            c["name_lbl"].config(fg=color)
            c["conf"].set(f"{score:.0%}")
            c["cat"].set(r["cat"])

            if r["dmg"] is not None:
                c["dmg"].set(str(r["dmg"]))
                c["pct"].set(f"{r['pct_hp']:.1f}% HP")
                meta = []
                if r["power"]:       meta.append(f"威力 {r['power']}")
                if r["hits"] > 1:    meta.append(f"{r['hits']}连击")
                if r["reduce_pct"]:  meta.append(f"减伤{r['reduce_pct']:.0f}%")
                c["meta"].set("  ".join(meta))
            else:
                c["dmg"].set("—")
                c["pct"].set("")
                c["meta"].set("")

        ts = __import__("datetime").datetime.now().strftime("%H:%M:%S")
        self._log_append(f"[{ts}] {self_name} vs {enemy_name}")

    # ── 状态轮询 ──────────────────────────────────────────────────────────────

    def _poll_status(self):
        if self._watcher is None:
            return
        dot, col = {
            "watching":         ("● 监控中",    GREEN),
            "window_not_found": ("● 未找到窗口", YELLOW),
            "idle":             ("● 已停止",    SUBTEXT),
        }.get(self._watcher.status, ("● …", SUBTEXT))
        self._status_dot.config(text=dot, fg=col)
        self.after(1000, self._poll_status)

    # ── 日志 ──────────────────────────────────────────────────────────────────

    def _log_append(self, msg: str):
        def _do():
            self._log.config(state="normal")
            self._log.insert("end", msg.rstrip("\n") + "\n")
            self._log.see("end")
            lines = int(self._log.index("end-1c").split(".")[0])
            if lines > 50:
                self._log.delete("1.0", f"{lines-50}.0")
            self._log.config(state="disabled")
        self.after(0, _do)

    # ── 关闭 ──────────────────────────────────────────────────────────────────

    def _on_close(self):
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        self._card.set_running(False)
        self.destroy()


def _launch_subprocess(card: ToolCard, args: list[str],
                       out_win: OutputWindow | None = None):
    """启动子进程并监视；如有 out_win 则实时输出到其中。"""
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE if out_win else subprocess.DEVNULL,
        stderr=subprocess.STDOUT if out_win else subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=ROOT,
    )
    card.watch_proc(proc)

    if out_win:
        def _read():
            for line in proc.stdout:
                out_win.after(0, lambda l=line: out_win.append(l))
        threading.Thread(target=_read, daemon=True).start()


def _launch_in_new_terminal(args: list[str]):
    """在新 PowerShell 窗口中运行（交互式工具）。"""
    cmd = " ".join(f'"{a}"' if " " in a else a for a in args)
    subprocess.Popen(
        ["powershell", "-NoExit", "-Command", cmd],
        cwd=ROOT,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


# ── 各工具动作 ────────────────────────────────────────────────────────────────

def action_gui(card: ToolCard):
    args = ([sys.executable, "--tool", "damage-gui"] if _IS_FROZEN
            else [PYTHON, str(ROOT / "damage_gui.py")])
    _launch_subprocess(card, args)


def action_analyzer_clipboard(card: ToolCard):
    out = OutputWindow(card.winfo_toplevel(), "对战截图分析器 — 剪切板监听")
    args = ([sys.executable, "--tool", "analyzer"] if _IS_FROZEN
            else [PYTHON, str(ROOT / "battle_analyzer.py")])
    _launch_subprocess(card, args, out)


def action_analyzer_watch(card: ToolCard):
    WatchWindow(card.winfo_toplevel(), card)


def action_analyzer_once(card: ToolCard):
    from tkinter import filedialog
    path = filedialog.askopenfilename(
        title="选择截图", filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp"), ("全部", "*.*")]
    )
    if not path:
        return
    out = OutputWindow(card.winfo_toplevel(), f"截图分析：{Path(path).name}")
    args = ([sys.executable, "--tool", "analyzer", "--once", path] if _IS_FROZEN
            else [PYTHON, str(ROOT / "battle_analyzer.py"), "--once", path])
    _launch_subprocess(card, args, out)


def action_cli_calc(card: ToolCard):
    if _IS_FROZEN:
        subprocess.Popen(
            [sys.executable, "--tool", "damage-calc"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=ROOT,
        )
    else:
        _launch_in_new_terminal([PYTHON, str(ROOT / "damage_calc.py")])


def action_spirit_scraper(card: ToolCard):
    out = OutputWindow(card.winfo_toplevel(), "精灵图鉴爬虫")
    args = ([sys.executable, "--tool", "spirit-scraper"] if _IS_FROZEN
            else [PYTHON, str(ROOT / "rocom_scraper.py")])
    _launch_subprocess(card, args, out)


def action_skill_scraper(card: ToolCard):
    out = OutputWindow(card.winfo_toplevel(), "技能图鉴爬虫")
    args = ([sys.executable, "--tool", "skill-scraper"] if _IS_FROZEN
            else [PYTHON, str(ROOT / "skill_scraper.py")])
    _launch_subprocess(card, args, out)


# ── 主窗口 ────────────────────────────────────────────────────────────────────

class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RocoDamageCalculator — 启动器")
        self.configure(bg=BG)
        self.resizable(False, False)
        # 关闭 Tk 内部自动 DPI 缩放（坐标已由 SetProcessDpiAwareness 处理）
        try:
            self.tk.call("tk", "scaling", "-displayof", ".",
                         96.0 / 72.0)  # 1× base: 96 DPI → 96/72 pt-per-px
        except Exception:
            pass

        # 标题栏
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(hdr, text="RocoDamageCalculator", bg=BG, fg=ACCENT,
                 font=("微软雅黑", 18, "bold")).pack(side="left")
        tk.Label(hdr, text="启动器", bg=BG, fg=SUBTEXT,
                 font=("微软雅黑", 12)).pack(side="left", padx=8)

        tk.Button(
            hdr, text="📐 校准监控窗口位置",
            bg=PANEL, fg=SUBTEXT,
            font=("微软雅黑", 9),
            relief="flat", padx=8, pady=2, cursor="hand2",
            activebackground=ACCENT, activeforeground="white",
            command=lambda: GeometryCalibrator(self),
        ).pack(side="right")

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x", padx=20, pady=4)

        # 工具卡片
        cards_cfg = [
            ("图形计算器",
             "可视化伤害计算界面，支持双方精灵、技能、天气、Buff 等参数。",
             action_gui, "启动 GUI", ACCENT),
            ("截图分析 — 自动监控",
             "自动检测游戏窗口画面变化，场面切换时立即 OCR 分析，无需手动截图。",
             action_analyzer_watch, "开始监控", GREEN),
            ("截图分析 — 剪切板监听",
             "截图后复制到剪切板，自动 OCR 识别双方精灵和技能并计算伤害。",
             action_analyzer_clipboard, "开始监听", ACCENT),
            ("截图分析 — 选择图片",
             "打开文件选择器，分析指定截图文件。",
             action_analyzer_once, "选择图片", YELLOW),
            ("命令行计算器",
             "交互式命令行伤害计算器，在新终端窗口中运行。",
             action_cli_calc, "打开终端", ORANGE),
            ("精灵数据更新",
             "爬取 wiki 精灵图鉴，更新 data/精灵完整数据.json（需联网）。",
             action_spirit_scraper, "开始爬取", RED),
            ("技能数据更新",
             "爬取 wiki 技能图鉴，更新 data/技能完整数据.json（需联网）。",
             action_skill_scraper, "开始爬取", RED),
        ]

        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        for title, desc, action, btn_text, btn_color in cards_cfg:
            card = ToolCard(container, title, desc, action, btn_text, btn_color)
            card.pack(fill="x", pady=4)

        # 底部提示
        tk.Label(self, text="提示：爬虫运行时请勿关闭输出窗口",
                 bg=BG, fg=SUBTEXT, font=("微软雅黑", 8)).pack(pady=(0, 10))

        # 布局完成后锁定尺寸，防止后续 Toplevel 开启时 Tk 重排导致主窗口跳变
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        # 居中偏左放置（不遮挡游戏画面右侧区域）
        x = max(0, (sw // 2 - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    app = Launcher()
    app.mainloop()
