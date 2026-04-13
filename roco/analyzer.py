"""
OCR 对战截图分析器
用法（通过根目录入口 battle_analyzer.py 调用，或直接运行本模块）：
    python -m roco.analyzer               # 监听剪切板
    python -m roco.analyzer --once <图片>  # 分析单张截图
"""
import argparse
import re
import time
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path

from PIL import Image

from .constants import ALL_STATS
from .data import DATA_PATH
from .calculator import calculate
from .stats import calc_all_stats as _calc_stats, find_skill as _find_skill

# ── OCR 区域定义（归一化比例，适用于任意分辨率）───────────────────────────────
# 格式：(left, top, right, bottom)，值为 0.0~1.0 相对比例
# 默认值由 2560×1440 实测坐标推导
REGIONS_RATIO = {
    "self_name":  ( 40/2560,  20/1440,  560/2560,  160/1440),
    "enemy_name": (1980/2560,  20/1440, 2490/2560,  160/1440),
    "skill1":     ( 250/2560, 500/1440,  540/2560,  650/1440),
    "skill2":     ( 250/2560, 680/1440,  540/2560,  835/1440),
    "skill3":     ( 250/2560, 845/1440,  540/2560, 1010/1440),
    "skill4":     ( 320/2560,1020/1440,  640/2560, 1210/1440),
    # 技能卡上方的「显示威力」数字区域（位于技能名上方约 25px）
    "skill1_power": ( 250/2560, 520/1440,  540/2560,  580/1440),
    "skill2_power": ( 250/2560, 715/1440,  540/2560,  770/1440),
    "skill3_power": ( 250/2560, 910/1440,  540/2560,  975/1440),
    "skill4_power": ( 320/2560,1090/1440,  640/2560, 1155/1440),
}

# 自定义区域配置文件（OCR Demo 保存后自动加载）
import sys as _sys
_REGIONS_CONFIG = ((Path(_sys.executable).parent if getattr(_sys, "frozen", False)
                    else Path(__file__).parent.parent) / "roco_regions.json")

# 游戏画面裁剪区域默认值（相对于整张截图的比例）
# 全屏模式 = (0,0,1,1)；窗口模式时调小 top 以去掉标题栏
_DEFAULT_GAME_AREA = (0.0, 0.0, 1.0, 1.0)
_GAME_AREA_KEY     = "_game_area"


def load_regions() -> tuple[dict, tuple]:
    """加载自定义区域比例与游戏画面区域；配置文件不存在时返回内置默认值。
    返回 (regions_dict, game_area_tuple)。
    """
    if _REGIONS_CONFIG.exists():
        import json
        try:
            with open(_REGIONS_CONFIG, encoding="utf-8") as f:
                data = json.load(f)
            regions = {k: tuple(v) for k, v in data.items()
                       if k in REGIONS_RATIO}
            game_area = tuple(data.get(_GAME_AREA_KEY, _DEFAULT_GAME_AREA))
            # 填充旧配置文件中缺少的新字段（如 skill*_power）
            for k, v in REGIONS_RATIO.items():
                if k not in regions:
                    regions[k] = v
            base_keys = {"self_name", "enemy_name", "skill1", "skill2", "skill3", "skill4"}
            if base_keys.issubset(set(regions.keys())):
                return regions, game_area
        except Exception:
            pass
    return dict(REGIONS_RATIO), _DEFAULT_GAME_AREA


def save_regions(regions: dict, game_area: tuple = _DEFAULT_GAME_AREA) -> None:
    """将区域比例和游戏画面区域保存到配置文件，供下次启动自动加载。"""
    import json
    data = {k: list(v) for k, v in regions.items()}
    data[_GAME_AREA_KEY] = list(game_area)
    with open(_REGIONS_CONFIG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── 默认竞技场参数（OCR 无法识别的字段使用默认值）───────────────────────────
DEFAULT_TALENT       = 10
DEFAULT_TALENT_STATS = ["生命", "物攻", "速度"]
DEFAULT_NATURE       = "无"

TMP_IMG = Path(__file__).parent.parent / "sample" / "_ocr_tmp.png"
TMP_IMG.parent.mkdir(exist_ok=True)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def load_db():
    import json
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    db = {d["名称"]: d for d in raw if d.get("名称")}
    spirit_names = list(db.keys())
    skill_names = sorted({
        s["技能名"]
        for d in raw
        for s in d.get("技能组", [])
        if s.get("技能名")
    })
    return db, spirit_names, skill_names


def ocr_region(img: Image.Image, box: tuple) -> list[str]:
    crop = img.crop(box)
    crop.save(TMP_IMG)
    result, _ = _get_engine()(str(TMP_IMG))
    return [r[1] for r in (result or [])]


def best_match(texts: list[str], candidates: list[str], min_score: float = 0.4) -> tuple[str | None, float]:
    for t in texts:
        if t in candidates:
            return t, 1.0
    for t in texts:
        m = get_close_matches(t, candidates, n=1, cutoff=0.4)
        if m:
            score = SequenceMatcher(None, t, m[0]).ratio()
            if score >= min_score:
                return m[0], score
    best_name, best_score = None, 0.0
    for t in texts:
        for c in candidates:
            s = SequenceMatcher(None, t, c).ratio()
            if s > best_score:
                best_score, best_name = s, c
    if best_score >= min_score:
        return best_name, best_score
    return None, best_score


def scale_regions(img_width: int, img_height: int,
                  regions_ratio: dict | None = None) -> dict:
    if regions_ratio is None:
        regions_ratio, _ = load_regions()
    return {
        k: (int(l * img_width),  int(t * img_height),
            int(r * img_width),  int(b * img_height))
        for k, (l, t, r, b) in regions_ratio.items()
    }


def analyze_image(img: Image.Image, db: dict, spirit_names: list, skill_names: list,
                  regions_ratio: dict | None = None,
                  game_area: tuple | None = None) -> dict:
    """分析截图。
    game_area: (left, top, right, bottom) 相对比例，指定实际游戏画面范围。
    全屏时传 None 或 (0,0,1,1)；窗口模式时设置以排除标题栏等边框。
    """
    if game_area is None:
        game_area = _DEFAULT_GAME_AREA
    ga_l, ga_t, ga_r, ga_b = game_area
    # 先裁剪到游戏画面区域
    w, h = img.size
    img = img.crop((int(ga_l * w), int(ga_t * h),
                    int(ga_r * w), int(ga_b * h)))
    regions = scale_regions(img.width, img.height, regions_ratio)
    result = {}
    for key, box in regions.items():
        texts = ocr_region(img, box)
        if key.endswith("_power"):
            # 只提取数字，不做模糊匹配
            num = None
            for t in texts:
                m = re.search(r'\d+', t)
                if m:
                    num = int(m.group())
                    break
            result[key] = {"match": num, "score": 1.0 if num is not None else 0.0, "raw": texts}
        else:
            candidates = spirit_names if "name" in key else skill_names
            match, score = best_match(texts, candidates)
            result[key] = {"match": match, "score": score, "raw": texts}
    return result


def parse_skill_meta(effect: str) -> tuple[int, float]:
    """从技能效果文本提取 (连击数, 减伤率%).
    例：'造成物伤，3连击。' → (3, 0.0)
         '减伤70%，应对攻击。' → (1, 70.0)
    """
    m = re.search(r'(\d+)连击', effect)
    hits = int(m.group(1)) if m else 1
    m = re.search(r'减伤(\d+)%', effect)
    reduce_pct = float(m.group(1)) if m else 0.0
    return hits, reduce_pct


def find_skills_for_spirit(spirit_name: str, skill_keys: list[str], analysis: dict, db: dict) -> list[dict]:
    spirit = db.get(spirit_name)
    if not spirit:
        return []
    spirit_skill_names = {s["技能名"] for s in spirit.get("技能组", [])}
    skills = []
    for sk in skill_keys:
        matched = analysis[sk]["match"]
        if matched and matched in spirit_skill_names:
            skill = next(s for s in spirit["技能组"] if s["技能名"] == matched)
            skills.append(skill)
        elif matched:
            skills.append({"技能名": matched, "_unconfirmed": True})
        else:
            skills.append(None)
    return skills


def run_damage_for_skill(atk_name: str, skill_info: dict, def_name: str, db: dict) -> None:
    if not skill_info or skill_info.get("_unconfirmed"):
        name = skill_info["技能名"] if skill_info else "?"
        print(f"  [{name}]  技能未在精灵技能组中确认，跳过计算")
        return
    calculate(
        attacker_name=atk_name,
        attacker_nature=DEFAULT_NATURE,
        attacker_talent=DEFAULT_TALENT,
        attacker_talent_stats=DEFAULT_TALENT_STATS,
        skill_name=skill_info["技能名"],
        defender_name=def_name,
        defender_nature=DEFAULT_NATURE,
        defender_talent=DEFAULT_TALENT,
        defender_talent_stats=DEFAULT_TALENT_STATS,
    )


def prompt_spirit_name(prompt: str, db: dict, spirit_names: list) -> str | None:
    while True:
        raw = input(prompt).strip()
        if not raw:
            return None
        if raw in db:
            return raw
        candidates = get_close_matches(raw, spirit_names, n=5, cutoff=0.3)
        if not candidates:
            candidates = [n for n in spirit_names if raw in n][:5]
        if candidates:
            print(f"  未找到「{raw}」，相近结果：")
            for i, c in enumerate(candidates, 1):
                print(f"    {i}. {c}")
            sel = input("  请输入序号选择，或重新输入名称：").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(candidates):
                return candidates[int(sel) - 1]
            if sel in db:
                return sel
        else:
            print(f"  未找到「{raw}」，请重新输入（留空跳过）。")
            return None


def _quick_damage(self_name: str, enemy_name: str, analysis: dict,
                  skill_keys: list, db: dict) -> None:
    """简易公式快速伤害估算：攻÷防×0.9×显示威力×连击×(1-减伤)。"""
    import math
    atk_sp = db.get(self_name, {})
    def_sp = db.get(enemy_name, {})
    if not atk_sp or not def_sp:
        return

    atk_stats = _calc_stats(atk_sp, DEFAULT_TALENT, DEFAULT_TALENT_STATS, DEFAULT_NATURE)
    def_stats = _calc_stats(def_sp, DEFAULT_TALENT, DEFAULT_TALENT_STATS, DEFAULT_NATURE)
    def_hp    = def_stats["生命"]

    lines = []
    for i, sk in enumerate(skill_keys, 1):
        pk = f"skill{i}_power"
        display_power = analysis.get(pk, {}).get("match")
        if display_power is None:
            continue
        skill_match = analysis[sk].get("match")
        skill_data  = _find_skill(atk_sp, skill_match) if skill_match else None
        effect      = skill_data.get("效果", "") if skill_data else ""
        hits, reduce_pct = parse_skill_meta(effect)

        if skill_data and skill_data.get("类别") == "魔攻":
            atk_val, def_val, cat = atk_stats["魔攻"], def_stats["魔防"], "魔"
        else:
            atk_val, def_val, cat = atk_stats["物攻"], def_stats["物防"], "物"

        dmg = math.floor(atk_val / def_val * 0.9 * display_power * hits * (1 - reduce_pct / 100))
        pct = dmg / def_hp * 100 if def_hp else 0

        hit_s    = f"x{hits}连" if hits > 1 else ""
        reduce_s = f"  减伤{reduce_pct:.0f}%" if reduce_pct else ""
        name_s   = skill_match or "?"
        lines.append(f"  技能{i} {name_s}  [{cat}攻]  威力={display_power}{hit_s}{reduce_s}"
                     f"  ->  {dmg} ({pct:.1f}% HP)")

    if lines:
        print()
        print("  -- 简易伤害估算 (攻/防x0.9x威力x连击x(1-减伤%)) --")
        for line in lines:
            print(line)


def print_analysis(analysis: dict, db: dict, spirit_names: list, interactive: bool = True) -> None:
    print()
    print("=" * 60)
    print("  对战截图分析结果")
    print("=" * 60)

    self_name       = analysis["self_name"]["match"]
    raw_enemy_texts = analysis["enemy_name"]["raw"]
    raw_enemy       = " / ".join(raw_enemy_texts) or "（未读到文字）"

    auto_enemy_match, auto_enemy_score = best_match(raw_enemy_texts, spirit_names)

    print(f"  己方精灵：{self_name or '未识别'}  (置信度 {analysis['self_name']['score']:.0%})")
    if auto_enemy_match and auto_enemy_score >= 0.7:
        print(f"  对方精灵：{auto_enemy_match}  (置信度 {auto_enemy_score:.0%})  OCR: {raw_enemy_texts}")
    else:
        print(f"  对方精灵：OCR 原文「{raw_enemy}」—— 无法自动匹配物种，需手动输入")
    print()

    skill_keys = ["skill1", "skill2", "skill3", "skill4"]
    for i, sk in enumerate(skill_keys, 1):
        info = analysis[sk]
        tag  = "√" if info["score"] >= 0.8 else ("?" if info["score"] >= 0.4 else "×")
        print(f"  技能{i} [{tag}] {info['match'] or '未识别':12s}  (置信度 {info['score']:.0%})  OCR: {info['raw']}")

    print()
    print("─" * 60)

    if not self_name:
        print("  己方精灵名识别失败，无法继续。")
        print("  请检查截图分辨率是否为 2560×1440。")
        return

    if interactive:
        confirmed_self = input(f"  确认己方精灵「{self_name}」？（回车确认，或输入正确名称）: ").strip()
        if confirmed_self and confirmed_self in db:
            self_name = confirmed_self
        elif confirmed_self:
            m = get_close_matches(confirmed_self, spirit_names, n=1, cutoff=0.4)
            if m:
                self_name = m[0]
                print(f"  已匹配为：{self_name}")

    if auto_enemy_match and auto_enemy_score >= 0.7:
        enemy_name = auto_enemy_match
        if interactive:
            confirmed = input(f"  确认对方精灵「{enemy_name}」？（回车确认，或输入正确名称）: ").strip()
            if confirmed:
                resolved, _ = best_match([confirmed], spirit_names)
                if resolved:
                    enemy_name = resolved
                    print(f"  已匹配为：{enemy_name}")
    elif interactive:
        enemy_name = prompt_spirit_name("  请输入对方精灵名称（支持模糊搜索）: ", db, spirit_names)
    else:
        enemy_name = None

    if not enemy_name:
        print("  未提供对方精灵名，跳过伤害计算。")
        return

    # ── 简易伤害估算 ──────────────────────────────────────────
    _quick_damage(self_name, enemy_name, analysis, skill_keys, db)

    skills = find_skills_for_spirit(self_name, skill_keys, analysis, db)

    print()
    print(f"  以 {self_name} 攻击 {enemy_name}，计算四个技能伤害：")
    print()

    for i, (sk, skill_info) in enumerate(zip(skill_keys, skills), 1):
        print(f"【技能 {i}】")
        run_damage_for_skill(self_name, skill_info, enemy_name, db)


def clipboard_image() -> "Image.Image | None":
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            return img
    except Exception as e:
        print(f"  [clipboard] {e}")
    return None


def main_loop(db: dict, spirit_names: list, skill_names: list) -> None:
    print("正在监听剪切板……按 Ctrl+C 退出。")
    print("截图后复制到剪切板，即可自动分析。\n")
    last_hash = None
    while True:
        img = clipboard_image()
        if img is not None:
            try:
                h = hash(img.tobytes())
            except Exception:
                h = None
            if h != last_hash:
                last_hash = h
                print(f"\n  检测到新图像  {img.size[0]}×{img.size[1]}")
                try:
                    analysis = analyze_image(img, db, spirit_names, skill_names)
                    print_analysis(analysis, db, spirit_names, interactive=True)
                except Exception as e:
                    print(f"  [error] 分析失败：{e}")
        time.sleep(1.5)


def main_watch(db: dict, spirit_names: list, skill_names: list,
               window_title: str | None, threshold: float,
               region: dict | None = None) -> None:
    """mss + 帧差分自动监控模式。"""
    from .capture import GameWatcher

    # 保存截图的目录
    _save_dir = Path(__file__).parent.parent / "sample"
    _save_dir.mkdir(exist_ok=True)
    _save_path = _save_dir / "_last_capture.png"

    def _on_change(img):
        import traceback
        print(f"\n  [自动截图] 检测到场面变化  {img.size[0]}×{img.size[1]}")
        # 保存截图，方便调试
        try:
            img.save(_save_path)
            print(f"  [debug]   截图已保存 → {_save_path}")
        except Exception as e:
            print(f"  [debug]   截图保存失败：{e}")
        try:
            analysis = analyze_image(img, db, spirit_names, skill_names)
            print_analysis(analysis, db, spirit_names, interactive=False)
        except Exception:
            print(f"  [error] 分析失败，完整错误：")
            traceback.print_exc()

    watcher = GameWatcher(
        on_change=_on_change,
        window_title=window_title,
        diff_threshold=threshold,
        region=region,
    )

    if region:
        loc_hint = f"固定区域 {region['left']},{region['top']}  {region['width']}×{region['height']}"
    else:
        loc_hint = f'窗口"{window_title}"' if window_title else "全屏"
    print(f"自动监控模式  {loc_hint}  阈值={threshold}")
    print("场面发生明显变化时自动触发分析，按 Ctrl+C 退出。\n")
    watcher.start()
    try:
        while True:
            time.sleep(0.5)
            if watcher.status == "window_not_found":
                print(f"  [capture] 未找到窗口 {loc_hint!r}，继续等待……", end="\r")
    finally:
        watcher.stop()


def main_once(path: str, db: dict, spirit_names: list, skill_names: list) -> None:
    img = Image.open(path)
    print(f"分析图片：{path}  ({img.size[0]}×{img.size[1]})")
    analysis = analyze_image(img, db, spirit_names, skill_names)
    print_analysis(analysis, db, spirit_names, interactive=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="洛克王国对战截图分析器")
    parser.add_argument("--once",      metavar="IMAGE",  help="分析单张截图后退出")
    parser.add_argument("--watch",     action="store_true", help="自动监控游戏窗口（mss + 帧差分）")
    parser.add_argument("--window",    metavar="TITLE",  default="洛克王国：世界",
                        help="游戏窗口标题（--watch 模式用）")
    parser.add_argument("--threshold", metavar="N",      type=float, default=8.0,
                        help="帧差分触发阈值，默认 8.0")
    parser.add_argument("--region",    metavar="L,T,W,H",
                        help="固定截图区域，格式：left,top,width,height（如 0,0,1920,1080）")
    args = parser.parse_args()

    print("加载精灵数据库……")
    db, spirit_names, skill_names = load_db()
    print(f"已加载 {len(db)} 只精灵，{len(skill_names)} 个技能。\n")

    if args.once:
        main_once(args.once, db, spirit_names, skill_names)
    elif args.watch:
        _region = None
        if args.region:
            try:
                l, t, w, h = [int(x) for x in args.region.split(",")]
                _region = {"left": l, "top": t, "width": w, "height": h}
            except ValueError:
                print(f"[warn] --region 格式无效（应为 L,T,W,H），忽略")
        main_watch(db, spirit_names, skill_names,
                   window_title=args.window or None,
                   threshold=args.threshold,
                   region=_region)
    else:
        main_loop(db, spirit_names, skill_names)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已退出。")
