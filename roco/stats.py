"""
精灵属性计算：竞技场公式、属性克制倍率、技能查找
"""
import math

from .constants import NATURE_MODIFIERS, TYPE_CHART, TALENT_MAP


def calc_stat_pvp(base: int, stat: str, has_talent: bool, talent: int, nature: str) -> int:
    """
    竞技场属性公式（来自视频，满级固定）：
      L = (种族值 + 个体值/2) / 100
      生命 = (170L + 70) × 性格系数 + 100
      其他 = (110L + 10) × 性格系数 + 50
    has_talent: 该属性是否有天分加成
    talent: 个体值档位 8/9/10，实际值 = talent×6（仅 has_talent=True 时生效）
    """
    actual_talent = TALENT_MAP.get(talent, talent * 6) if has_talent else 0
    L = (base + actual_talent / 2) / 100
    nature_coeff = NATURE_MODIFIERS.get(nature, {}).get(stat, 1.0)
    if stat == "生命":
        return math.floor((170 * L + 70) * nature_coeff + 100)
    else:
        return math.floor((110 * L + 10) * nature_coeff + 50)


def calc_all_stats(spirit: dict, talent: int, talent_stats: list[str], nature: str) -> dict:
    """
    talent_stats: 玩家选择的三个有天分加成的属性，如 ["生命", "物攻", "速度"]
    """
    stat_map = {
        "生命": "种族值_生命", "物攻": "种族值_物攻", "魔攻": "种族值_魔攻",
        "物防": "种族值_物防", "魔防": "种族值_魔防", "速度": "种族值_速度",
    }
    return {
        stat: calc_stat_pvp(int(spirit.get(key, 0) or 0), stat, stat in talent_stats, talent, nature)
        for stat, key in stat_map.items()
    }


def get_type_multiplier(skill_attr: str, defender_attrs: list[str]) -> float:
    chart = TYPE_CHART.get(skill_attr, {"strong": [], "resist": []})
    mult = 1.0
    for da in defender_attrs:
        if da in chart["strong"]:
            mult *= 1.5
        elif da in chart["resist"]:
            mult *= 0.75
    return mult


def parse_attrs(attr_str: str) -> list[str]:
    return [a.strip() for a in attr_str.split("/") if a.strip()]


def find_skill(spirit: dict, skill_name: str) -> dict | None:
    for sk in spirit.get("技能组", []):
        if sk.get("技能名") == skill_name:
            return sk
    return None
