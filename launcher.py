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


def _pick_cjk_font() -> tuple[str, int]:
    """选一个系统中支持中文的等宽/近等宽字体，找不到则退回 Consolas。"""
    from tkinter import font as _tkfont
    import tkinter as _tk
    _r = _tk.Tk(); _r.withdraw()
    available = set(_tkfont.families())
    _r.destroy()
    for name in ("Noto Sans Mono CJK SC", "Sarasa Mono SC", "Cascadia Code",
                 "Microsoft YaHei Mono", "Noto Sans SC",
                 "Microsoft YaHei UI", "Microsoft JhengHei UI", "Consolas"):
        if name in available:
            return (name, 9)
    return ("TkFixedFont", 9)


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

    def __init__(self, parent, title: str, geometry: str | None = None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG)
        self.geometry(geometry or "760x420")
        self.resizable(True, True)

        _font = _pick_cjk_font()
        self.text = scrolledtext.ScrolledText(
            self, bg="#11111b", fg=TEXT, font=_font,
            insertbackground=TEXT, relief="flat", borderwidth=0,
            wrap="word",
        )
        self.text.pack(fill="both", expand=True, padx=6, pady=6)
        self.text.config(state="disabled")

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")

    def append(self, line: str):
        # \x0c (form-feed) is a clear-screen sentinel emitted before each analysis
        if "\x0c" in line:
            self.clear()
            line = line.replace("\x0c", "")
            if not line:  # nothing left after stripping sentinel
                return
        self.text.config(state="normal")
        self.text.insert("end", line)
        self.text.see("end")
        self.text.config(state="disabled")


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
    top = card.winfo_toplevel()
    # 以 1920×1080 为基准计算（远程桌面/DPI 缩放环境下 winfo_screen* 不可靠）
    sw, sh = 1920, 1080
    win_w = 480
    win_x = 1520                 # 1360 + 160
    win_h = 653                  # (sh-100) * 2/3 ≈ 653
    out = OutputWindow(top, "对战截图分析器 — 自动监控",
                       geometry=f"{win_w}x{win_h}+{win_x}+0")
    args = ([sys.executable, "--tool", "analyzer-watch"] if _IS_FROZEN
            else [PYTHON, "-u", "-X", "utf8", str(ROOT / "battle_analyzer.py"),
                  "--watch", "--window", "洛克王国：世界",
                  "--region", "0,40,1920,1080"])
    _launch_subprocess(card, args, out)


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

        # 标题栏
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(hdr, text="RocoDamageCalculator", bg=BG, fg=ACCENT,
                 font=("微软雅黑", 18, "bold")).pack(side="left")
        tk.Label(hdr, text="启动器", bg=BG, fg=SUBTEXT,
                 font=("微软雅黑", 12)).pack(side="left", padx=8)

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


if __name__ == "__main__":
    app = Launcher()
    app.mainloop()
