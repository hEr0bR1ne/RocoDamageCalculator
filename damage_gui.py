"""
RocoDamageCalculator - 图形界面
"""
import tkinter as tk
from tkinter import ttk, font
import sys, math
from damage_calc import (
    load_data, calc_all_stats, get_type_multiplier, parse_attrs,
    find_skill, NATURE_MODIFIERS, TALENT_MAP, COUNTER_BONUS,
    WEATHER_BONUS, ALL_STATS,
)

# ── 颜色主题 ─────────────────────────────────────────────────────────────────
BG       = "#1e1e2e"
PANEL    = "#2a2a3e"
ACCENT   = "#7c6af7"
TEXT     = "#cdd6f4"
SUBTEXT  = "#a6adc8"
GREEN    = "#a6e3a1"
RED      = "#f38ba8"
YELLOW   = "#f9e2af"
BORDER   = "#45475a"

DB: dict = {}
SKILL_DB: dict = {}


def load_skill_db():
    import json
    from pathlib import Path
    p = Path(__file__).parent / "output" / "技能完整数据.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            raw = json.load(f)
        return {s["技能名"]: s for s in raw if s.get("技能名")}
    return {}


# ── 主窗口 ───────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RocoDamageCalculator")
        self.configure(bg=BG)
        self.resizable(True, True)

        global DB, SKILL_DB
        DB = load_data()
        SKILL_DB = load_skill_db()
        self.spirit_names = sorted(DB.keys())

        self._build_ui()
        self.minsize(1000, 680)

    def _build_ui(self):
        # ── 顶部标题 ──
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(hdr, text="RocoDamageCalculator", bg=BG, fg=ACCENT,
                 font=("微软雅黑", 16, "bold")).pack(side="left")
        tk.Label(hdr, text=f"已加载 {len(DB)} 只精灵", bg=BG, fg=SUBTEXT,
                 font=("微软雅黑", 10)).pack(side="left", padx=12)

        # ── 天气行 ──
        wrow = tk.Frame(self, bg=BG)
        wrow.pack(fill="x", padx=16, pady=4)
        tk.Label(wrow, text="天气：", bg=BG, fg=TEXT, font=("微软雅黑", 10)).pack(side="left")
        self.weather_var = tk.StringVar(value="无")
        for w in ["无", "雨天", "晴天", "沙暴", "冰雹"]:
            tk.Radiobutton(wrow, text=w, variable=self.weather_var, value=w,
                           bg=BG, fg=TEXT, selectcolor=PANEL,
                           activebackground=BG, font=("微软雅黑", 10)).pack(side="left", padx=6)

        # ── 左右面板 ──
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=4)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self.atk_panel = SpiritPanel(body, "攻击方", self.spirit_names, is_attacker=True)
        self.atk_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.def_panel = SpiritPanel(body, "防御方", self.spirit_names, is_attacker=False)
        self.def_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # ── 计算按钮 ──
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=16, pady=6)
        tk.Button(btn_row, text="  计  算  ", command=self._calculate,
                  bg=ACCENT, fg="white", font=("微软雅黑", 12, "bold"),
                  relief="flat", padx=20, pady=6, cursor="hand2").pack(side="left")

        # ── 结果区 ──
        self.result_frame = ResultPanel(self)
        self.result_frame.pack(fill="x", padx=16, pady=(0, 12))

    def _calculate(self):
        try:
            result = self._do_calc()
            self.result_frame.show(result)
        except Exception as e:
            self.result_frame.show_error(str(e))

    def _do_calc(self) -> dict:
        ap = self.atk_panel
        dp = self.def_panel

        atk_name = ap.name_var.get().strip()
        def_name = dp.name_var.get().strip()
        if atk_name not in DB:
            raise ValueError(f"未找到攻击方精灵「{atk_name}」")
        if def_name not in DB:
            raise ValueError(f"未找到防御方精灵「{def_name}」")

        atk_spirit = DB[atk_name]
        def_spirit = DB[def_name]

        atk_talent       = int(ap.talent_var.get())
        atk_talent_stats = ap.get_talent_stats()
        atk_nature       = ap.nature_var.get()
        skill_name       = ap.skill_var.get().strip()
        atk_up           = float(ap.atk_up_var.get() or 0)
        atk_down         = float(ap.atk_down_var.get() or 0)
        trait_power_pct  = float(ap.trait_pct_var.get() or 0)
        power_add        = float(ap.power_add_var.get() or 0)
        power_buff       = float(ap.power_buff_var.get() or 1)
        counter_hit      = ap.counter_var.get()

        def_talent       = int(dp.talent_var.get())
        def_talent_stats = dp.get_talent_stats()
        def_nature       = dp.nature_var.get()
        def_up           = float(dp.def_up_var.get() or 0)
        def_down         = float(dp.def_down_var.get() or 0)
        def_reduce       = float(dp.def_reduce_var.get() or 0)

        weather = self.weather_var.get()

        # 属性计算
        atk_stats = calc_all_stats(atk_spirit, atk_talent, atk_talent_stats, atk_nature)
        def_stats = calc_all_stats(def_spirit, def_talent, def_talent_stats, def_nature)

        # 技能
        skill = find_skill(atk_spirit, skill_name)
        if not skill:
            avail = [s["技能名"] for s in atk_spirit.get("技能组", [])]
            raise ValueError(f"技能「{skill_name}」不存在\n可用：{avail}")

        skill_power    = int(skill.get("威力", 0) or 0)
        skill_category = skill.get("类别", "")
        skill_attr     = skill.get("技能属性", "")
        skill_cost     = int(skill.get("能耗", 0) or 0)

        if skill_category == "物攻":
            atk_val, def_val = atk_stats["物攻"], def_stats["物防"]
            atk_label, def_label = "物攻", "物防"
        elif skill_category == "魔攻":
            atk_val, def_val = atk_stats["魔攻"], def_stats["魔防"]
            atk_label, def_label = "魔攻", "魔防"
        else:
            raise ValueError(f"「{skill_name}」是非攻击技能，无伤害输出")

        def_attrs      = parse_attrs(def_spirit.get("属性", ""))
        atk_attrs_list = parse_attrs(atk_spirit.get("属性", ""))
        type_mult      = get_type_multiplier(skill_attr, def_attrs)
        if counter_hit and skill_name == "虫击":
            type_mult = max(type_mult, 1.0)
        stab_mult    = 1.25 if skill_attr in atk_attrs_list else 1.0
        weather_mult = WEATHER_BONUS.get(weather, {}).get(skill_attr, 1.0)

        ability_level = (1.0 + atk_up / 100.0 + def_down / 100.0) / \
                        (1.0 + atk_down / 100.0 + def_up / 100.0)

        counter_info = COUNTER_BONUS.get(skill_name)
        counter_mult, counter_add = 1.0, 0.0
        if counter_hit and counter_info:
            if counter_info["type"] == "multiply":
                counter_mult = counter_info["value"]
            else:
                counter_add = counter_info["value"]

        effective_power = (skill_power * counter_mult + power_add + counter_add) * (1.0 + trait_power_pct / 100.0)

        base_dmg = atk_val / def_val * 0.9 * effective_power * ability_level * power_buff * stab_mult * type_mult * weather_mult
        if def_reduce > 0:
            base_dmg *= (1.0 - def_reduce / 100.0)
        base_dmg = math.floor(base_dmg)

        dmg_low  = base_dmg
        dmg_high = base_dmg
        def_hp   = def_stats["生命"]
        pct_low  = dmg_low  / def_hp * 100 if def_hp else 0
        pct_high = dmg_high / def_hp * 100 if def_hp else 0
        ko_min   = math.ceil(100 / pct_high) if pct_high > 0 else 999
        ko_max   = math.ceil(100 / pct_low)  if pct_low  > 0 else 999

        atk_spd, def_spd = atk_stats["速度"], def_stats["速度"]
        if atk_spd > def_spd:
            speed_tag = f"先手 ✓ ({atk_spd} > {def_spd})"
            speed_color = GREEN
        elif atk_spd < def_spd:
            speed_tag = f"后手 ✗ ({atk_spd} < {def_spd}，差{def_spd-atk_spd})"
            speed_color = RED
        else:
            speed_tag = f"同速 ({atk_spd}，随机)"
            speed_color = YELLOW

        return dict(
            atk_name=atk_name, atk_attrs=atk_spirit.get("属性",""),
            atk_label=atk_label, atk_val=atk_val, atk_hp=atk_stats["生命"], atk_spd=atk_spd,
            atk_trait=atk_spirit.get("特性名称",""), atk_trait_eff=atk_spirit.get("特性效果",""),
            def_name=def_name, def_attrs="/".join(def_attrs),
            def_label=def_label, def_val=def_val, def_hp=def_hp, def_spd=def_spd,
            skill_name=skill_name, skill_attr=skill_attr, skill_category=skill_category,
            skill_power=skill_power, skill_cost=skill_cost, skill_effect=skill.get("效果",""),
            effective_power=effective_power,
            counter_hit=counter_hit, counter_info=counter_info,
            type_mult=type_mult, stab_mult=stab_mult, weather_mult=weather_mult,
            ability_level=ability_level, power_buff=power_buff,
            trait_power_pct=trait_power_pct, def_reduce=def_reduce,
            base_dmg=base_dmg, dmg_low=dmg_low, dmg_high=dmg_high,
            pct_low=pct_low, pct_high=pct_high, ko_min=ko_min, ko_max=ko_max,
            speed_tag=speed_tag, speed_color=speed_color,
        )


# ── 精灵面板 ─────────────────────────────────────────────────────────────────
class SpiritPanel(tk.Frame):
    def __init__(self, parent, title, spirit_names, is_attacker):
        super().__init__(parent, bg=PANEL, bd=0, highlightthickness=1,
                         highlightbackground=BORDER)
        self.spirit_names = spirit_names
        self.is_attacker  = is_attacker
        self._build(title)

    def _lbl(self, parent, text, fg=SUBTEXT, font_size=9):
        return tk.Label(parent, text=text, bg=PANEL, fg=fg,
                        font=("微软雅黑", font_size))

    def _entry(self, parent, var, width=8):
        e = tk.Entry(parent, textvariable=var, width=width,
                     bg=BG, fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=("微软雅黑", 10),
                     highlightthickness=1, highlightbackground=BORDER)
        return e

    def _row(self, parent, pady=2):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill="x", padx=10, pady=pady)
        return f

    def _build(self, title):
        # 标题
        tk.Label(self, text=title, bg=PANEL, fg=ACCENT,
                 font=("微软雅黑", 12, "bold")).pack(anchor="w", padx=10, pady=(8,4))

        # 精灵名（带自动补全下拉）
        r = self._row(self)
        self._lbl(r, "精灵名：").pack(side="left")
        self.name_var = tk.StringVar()
        self._selecting = False  # 防止选中时重复触发过滤
        self.name_entry = ttk.Combobox(r, textvariable=self.name_var,
                                       values=self.spirit_names, width=16,
                                       font=("微软雅黑", 10))
        self.name_entry.pack(side="left", padx=4)
        self.name_entry.bind("<KeyRelease>", self._filter_names)
        self.name_entry.bind("<<ComboboxSelected>>", self._on_spirit_select)

        # 属性/特性显示
        self.info_var = tk.StringVar(value="")
        self._lbl(self, "").pack()  # spacer
        self.info_label = tk.Label(self, textvariable=self.info_var, bg=PANEL,
                                   fg=YELLOW, font=("微软雅黑", 9), wraplength=340, justify="left")
        self.info_label.pack(anchor="w", padx=10)

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x", padx=10, pady=6)

        # 个体值档位
        r = self._row(self)
        self._lbl(r, "个体档位：").pack(side="left")
        self.talent_var = tk.StringVar(value="10")
        for v in ["8", "9", "10"]:
            tk.Radiobutton(r, text=v, variable=self.talent_var, value=v,
                           bg=PANEL, fg=TEXT, selectcolor=BG,
                           activebackground=PANEL, font=("微软雅黑", 10)).pack(side="left", padx=4)

        # 天分属性（3个复选框）
        r = self._row(self)
        self._lbl(r, "天分属性：").pack(side="left")
        self.talent_stat_vars = {}
        for stat in ALL_STATS:
            v = tk.BooleanVar(value=False)
            self.talent_stat_vars[stat] = v
            tk.Checkbutton(r, text=stat, variable=v, bg=PANEL, fg=TEXT,
                           selectcolor=BG, activebackground=PANEL,
                           font=("微软雅黑", 9)).pack(side="left", padx=2)

        # 性格
        r = self._row(self)
        self._lbl(r, "性格：").pack(side="left")
        self.nature_var = tk.StringVar(value="无")
        # 下拉列表显示"性格 (+加 -减)"
        def _nature_label(name):
            mods = NATURE_MODIFIERS.get(name, {})
            up   = [s for s, v in mods.items() if v > 1]
            down = [s for s, v in mods.items() if v < 1]
            if not up and not down:
                return name
            return f"{name} (+{up[0]} -{down[0]})"
        nature_labels = [_nature_label(n) for n in NATURE_MODIFIERS.keys()]
        nature_name_map = {_nature_label(n): n for n in NATURE_MODIFIERS.keys()}
        nature_cb = ttk.Combobox(r, values=nature_labels, width=18,
                                  font=("微软雅黑", 10), state="readonly")
        nature_cb.set(_nature_label("无"))
        nature_cb.pack(side="left", padx=4)

        def _on_nature_select(event=None):
            self.nature_var.set(nature_name_map.get(nature_cb.get(), "无"))
        nature_cb.bind("<<ComboboxSelected>>", _on_nature_select)
        _on_nature_select()

        # 性格效果标签
        self.nature_info_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.nature_info_var, bg=PANEL,
                 fg=GREEN, font=("微软雅黑", 8)).pack(anchor="w", padx=10)

        def _update_nature_label(*_):
            name = self.nature_var.get()
            mods = NATURE_MODIFIERS.get(name, {})
            up   = [s for s, v in mods.items() if v > 1]
            down = [s for s, v in mods.items() if v < 1]
            if up and down:
                self.nature_info_var.set(f"↑{up[0]}×1.2   ↓{down[0]}×0.9")
            else:
                self.nature_info_var.set("")
        self.nature_var.trace_add("write", _update_nature_label)

        sep2 = tk.Frame(self, bg=BORDER, height=1)
        sep2.pack(fill="x", padx=10, pady=6)

        if self.is_attacker:
            self._build_attacker_fields()
        else:
            self._build_defender_fields()

    def _build_attacker_fields(self):
        # 技能选择
        r = self._row(self)
        self._lbl(r, "技能：").pack(side="left")
        self.skill_var = tk.StringVar()
        self.skill_cb = ttk.Combobox(r, textvariable=self.skill_var,
                                      values=[], width=16,
                                      font=("微软雅黑", 10))
        self.skill_cb.pack(side="left", padx=4)
        self.skill_cb.bind("<<ComboboxSelected>>", self._on_skill_select)

        # 技能效果显示
        self.skill_info_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.skill_info_var, bg=PANEL, fg=SUBTEXT,
                 font=("微软雅黑", 8), wraplength=340, justify="left").pack(anchor="w", padx=10)

        # 应对成功
        self.counter_var = tk.BooleanVar(value=False)
        self.counter_chk = tk.Checkbutton(self, text="应对成功", variable=self.counter_var,
                                           bg=PANEL, fg=YELLOW, selectcolor=BG,
                                           activebackground=PANEL, font=("微软雅黑", 10))
        self.counter_chk.pack(anchor="w", padx=10, pady=2)
        self.counter_note_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.counter_note_var, bg=PANEL, fg=YELLOW,
                 font=("微软雅黑", 8)).pack(anchor="w", padx=24)

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x", padx=10, pady=6)

        # 攻击buff
        r = self._row(self)
        self._lbl(r, "攻击提升%：").pack(side="left")
        self.atk_up_var = tk.StringVar(value="0")
        self._entry(r, self.atk_up_var, 5).pack(side="left", padx=4)
        self._lbl(r, "攻击降低%：").pack(side="left", padx=(8,0))
        self.atk_down_var = tk.StringVar(value="0")
        self._entry(r, self.atk_down_var, 5).pack(side="left", padx=4)

        # 特性威力加成
        r = self._row(self)
        self._lbl(r, "特性威力+%：").pack(side="left")
        self.trait_pct_var = tk.StringVar(value="0")
        self._entry(r, self.trait_pct_var, 5).pack(side="left", padx=4)
        self._lbl(r, "威力加值：").pack(side="left", padx=(8,0))
        self.power_add_var = tk.StringVar(value="0")
        self._entry(r, self.power_add_var, 5).pack(side="left", padx=4)

        r = self._row(self)
        self._lbl(r, "威力buff×：").pack(side="left")
        self.power_buff_var = tk.StringVar(value="1")
        self._entry(r, self.power_buff_var, 5).pack(side="left", padx=4)

    def _build_defender_fields(self):
        # 防御buff
        r = self._row(self)
        self._lbl(r, "防御提升%：").pack(side="left")
        self.def_up_var = tk.StringVar(value="0")
        self._entry(r, self.def_up_var, 5).pack(side="left", padx=4)
        self._lbl(r, "防御降低%：").pack(side="left", padx=(8,0))
        self.def_down_var = tk.StringVar(value="0")
        self._entry(r, self.def_down_var, 5).pack(side="left", padx=4)

        # 应对减伤
        r = self._row(self)
        self._lbl(r, "应对减伤%：").pack(side="left")
        self.def_reduce_var = tk.StringVar(value="0")
        self._entry(r, self.def_reduce_var, 5).pack(side="left", padx=4)
        self._lbl(r, "（硬门100 / 听桥80 / 防御70）", fg=SUBTEXT, font_size=8).pack(side="left", padx=4)

    def _filter_names(self, event=None):
        # 忽略方向键/回车等非输入按键
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        val = self.name_var.get()
        filtered = [n for n in self.spirit_names if val in n]
        self.name_entry["values"] = filtered[:40]
        if filtered and val:
            self.name_entry.event_generate("<Button-1>")  # 自动弹出下拉

    def _on_spirit_select(self, event=None):
        self._on_spirit_change()

    def _on_spirit_change(self):
        name = self.name_var.get()
        if name not in DB:
            return
        spirit = DB[name]
        attr  = spirit.get("属性", "")
        trait = spirit.get("特性名称", "")
        trait_eff = spirit.get("特性效果", "")
        self.info_var.set(f"[{attr}]  特性：{trait} — {trait_eff}")

        if self.is_attacker:
            skills = spirit.get("技能组", [])
            skill_names = [s["技能名"] for s in skills if s.get("类别") in ("物攻","魔攻")]
            self.skill_cb["values"] = skill_names
            if skill_names:
                self.skill_var.set(skill_names[0])
                self._on_skill_select()

    def _on_skill_select(self, event=None):
        skill_name = self.skill_var.get()
        spirit_name = self.name_var.get()
        if spirit_name not in DB:
            return
        skill = find_skill(DB[spirit_name], skill_name)
        if skill:
            effect = skill.get("效果", "")
            power  = skill.get("威力", "?")
            cost   = skill.get("能耗", "?")
            self.skill_info_var.set(f"威力:{power}  能耗:{cost}  {effect}")

        # 应对加成提示
        info = COUNTER_BONUS.get(skill_name)
        if info:
            self.counter_note_var.set(info["note"])
            self.counter_chk.config(state="normal")
        else:
            self.counter_note_var.set("")
            self.counter_var.set(False)
            self.counter_chk.config(state="disabled")

    def get_talent_stats(self) -> list:
        return [s for s, v in self.talent_stat_vars.items() if v.get()]


# ── 结果面板 ─────────────────────────────────────────────────────────────────
class ResultPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=PANEL, bd=0,
                         highlightthickness=1, highlightbackground=BORDER)
        self._build()

    def _build(self):
        self.canvas = tk.Canvas(self, bg=PANEL, height=160, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=10)
        self._draw_placeholder()

    def _draw_placeholder(self):
        self.canvas.delete("all")
        self.canvas.create_text(400, 70, text="填写双方信息后点击「计算」",
                                 fill=SUBTEXT, font=("微软雅黑", 12))

    def show_error(self, msg):
        self.canvas.delete("all")
        self.canvas.create_text(400, 70, text=f"错误：{msg}",
                                 fill=RED, font=("微软雅黑", 11), width=700)

    def show(self, r: dict):
        c = self.canvas
        c.delete("all")
        W = c.winfo_width() or 960
        H = 160

        # ── 伤害数字（大字居中）──
        one_shot = r["pct_low"] >= 100
        maybe    = r["pct_high"] >= 100 and not one_shot
        dmg_color = GREEN if one_shot else (YELLOW if maybe else TEXT)

        c.create_text(W//2, 32, text=f"{r['dmg_low']} ~ {r['dmg_high']}",
                      fill=dmg_color, font=("微软雅黑", 28, "bold"), anchor="center")
        c.create_text(W//2, 62, text=f"{r['pct_low']:.1f}% ~ {r['pct_high']:.1f}% 血量",
                      fill=dmg_color, font=("微软雅黑", 12), anchor="center")

        if one_shot:
            c.create_text(W//2, 82, text="★ 一击必杀", fill=GREEN,
                          font=("微软雅黑", 11, "bold"), anchor="center")
        elif maybe:
            c.create_text(W//2, 82, text="▲ 可能一击", fill=YELLOW,
                          font=("微软雅黑", 11), anchor="center")
        else:
            c.create_text(W//2, 82,
                          text=f"需要 {r['ko_min']}~{r['ko_max']} 次击倒  对方血量 {r['def_hp']}",
                          fill=SUBTEXT, font=("微软雅黑", 10), anchor="center")

        # ── 左侧：攻击方信息 ──
        lx = 16
        c.create_text(lx, 10, text=f"攻击方：{r['atk_name']} [{r['atk_attrs']}]",
                      fill=TEXT, font=("微软雅黑", 10, "bold"), anchor="w")
        c.create_text(lx, 28, text=f"{r['atk_label']}:{r['atk_val']}  生命:{r['atk_hp']}  速度:{r['atk_spd']}",
                      fill=SUBTEXT, font=("微软雅黑", 9), anchor="w")
        c.create_text(lx, 44, text=f"技能：{r['skill_name']} [{r['skill_attr']}系]  威力:{r['skill_power']}→{r['effective_power']:.0f}  能耗:{r['skill_cost']}",
                      fill=SUBTEXT, font=("微软雅黑", 9), anchor="w")
        if r["atk_trait"]:
            c.create_text(lx, 60, text=f"特性：{r['atk_trait']}",
                          fill=YELLOW, font=("微软雅黑", 8), anchor="w")

        # ── 右侧：防御方信息 ──
        rx = W - 16
        c.create_text(rx, 10, text=f"防御方：{r['def_name']} [{r['def_attrs']}]",
                      fill=TEXT, font=("微软雅黑", 10, "bold"), anchor="e")
        c.create_text(rx, 28, text=f"{r['def_label']}:{r['def_val']}  生命:{r['def_hp']}  速度:{r['def_spd']}",
                      fill=SUBTEXT, font=("微软雅黑", 9), anchor="e")

        # ── 先后手 ──
        c.create_text(rx, 44, text=r["speed_tag"],
                      fill=r["speed_color"], font=("微软雅黑", 9, "bold"), anchor="e")

        # ── 加成标签行 ──
        tags = []
        tm = r["type_mult"]
        tags.append(("★克制×" + f"{tm:.2f}" if tm > 1 else ("▼抵抗×" + f"{tm:.2f}" if tm < 1 else "无克制"), GREEN if tm > 1 else (RED if tm < 1 else SUBTEXT)))
        if r["stab_mult"] != 1.0:
            tags.append((f"本系×{r['stab_mult']:.1f}", YELLOW))
        if r["ability_level"] != 1.0:
            tags.append((f"能力等级×{r['ability_level']:.2f}", TEXT))
        if r["weather_mult"] != 1.0:
            tags.append((f"天气×{r['weather_mult']:.1f}", TEXT))
        if r["power_buff"] != 1.0:
            tags.append((f"威力buff×{r['power_buff']:.1f}", TEXT))
        if r["trait_power_pct"]:
            tags.append((f"特性威力+{r['trait_power_pct']:.0f}%", YELLOW))
        if r["def_reduce"]:
            tags.append((f"减伤×{1-r['def_reduce']/100:.2f}", RED))
        if r["counter_hit"] and r["counter_info"]:
            tags.append((r["counter_info"]["note"].split("：")[0] + "✓", YELLOW))

        tx = 16
        ty = H - 28
        for tag_text, tag_color in tags:
            tw = len(tag_text) * 9 + 12
            c.create_rectangle(tx, ty-2, tx+tw, ty+16, fill=BG, outline=BORDER)
            c.create_text(tx+6, ty+7, text=tag_text, fill=tag_color,
                          font=("微软雅黑", 8), anchor="w")
            tx += tw + 6

        # ── 公式 ──
        formula = f"floor({r['atk_val']}/{r['def_val']} × 0.9 × {r['effective_power']:.0f}"
        if r["stab_mult"] != 1.0:
            formula += f" × {r['stab_mult']:.1f}(本系)"
        if r["ability_level"] != 1.0:
            formula += f" × {r['ability_level']:.3f}(能力等级)"
        if r["type_mult"] != 1.0:
            formula += f" × {r['type_mult']:.2f}(克制)"
        if r["weather_mult"] != 1.0:
            formula += f" × {r['weather_mult']:.1f}(天气)"
        if r["def_reduce"]:
            formula += f" × {1-r['def_reduce']/100:.2f}(减伤)"
        formula += f") = {r['base_dmg']}"
        c.create_text(16, H - 10, text=formula, fill=SUBTEXT,
                      font=("微软雅黑", 8), anchor="w")


if __name__ == "__main__":
    app = App()
    app.mainloop()
