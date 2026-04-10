"""
OCR 对战截图分析器
用法（通过根目录入口 battle_analyzer.py 调用，或直接运行本模块）：
    python -m roco.analyzer               # 监听剪切板
    python -m roco.analyzer --once <图片>  # 分析单张截图
"""
import argparse
import time
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path

from PIL import Image

from .constants import ALL_STATS
from .data import DATA_PATH
from .calculator import calculate

# ── OCR 区域定义（针对 2560×1440 截图）─────────────────────────────────────
# 格式：(left, top, right, bottom)
REGION_2560 = {
    "self_name":  (40,   35,  420,  115),
    "enemy_name": (2050, 35,  2490, 115),
    "skill1":     (250,  500, 540,  650),
    "skill2":     (250,  680, 540,  835),
    "skill3":     (250,  845, 540,  1010),
    "skill4":     (320,  1020, 640, 1210),
}

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


def scale_regions(img_width: int, img_height: int) -> dict:
    sw = img_width  / 2560
    sh = img_height / 1440
    return {
        k: (int(l * sw), int(t * sh), int(r * sw), int(b * sh))
        for k, (l, t, r, b) in REGION_2560.items()
    }


def analyze_image(img: Image.Image, db: dict, spirit_names: list, skill_names: list) -> dict:
    regions = scale_regions(img.width, img.height)
    result = {}
    for key, box in regions.items():
        texts      = ocr_region(img, box)
        candidates = spirit_names if "name" in key else skill_names
        match, score = best_match(texts, candidates)
        result[key] = {"match": match, "score": score, "raw": texts}
    return result


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
        tag  = "✓" if info["score"] >= 0.8 else ("?" if info["score"] >= 0.4 else "✗")
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


def main_once(path: str, db: dict, spirit_names: list, skill_names: list) -> None:
    img = Image.open(path)
    print(f"分析图片：{path}  ({img.size[0]}×{img.size[1]})")
    analysis = analyze_image(img, db, spirit_names, skill_names)
    print_analysis(analysis, db, spirit_names, interactive=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="洛克王国对战截图分析器")
    parser.add_argument("--once", metavar="IMAGE", help="分析单张截图后退出")
    args = parser.parse_args()

    print("加载精灵数据库……")
    db, spirit_names, skill_names = load_db()
    print(f"已加载 {len(db)} 只精灵，{len(skill_names)} 个技能。\n")

    if args.once:
        main_once(args.once, db, spirit_names, skill_names)
    else:
        main_loop(db, spirit_names, skill_names)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已退出。")
