"""
damage_calc.py — 向后兼容入口
实际逻辑已迁移至 roco/ 包，本文件重导出公共 API 供旧代码/damage_gui.py 直接使用。
"""

# 重导出公共符号，保持向后兼容
from roco.constants import (
    NATURE_MODIFIERS,
    TYPE_CHART,
    WEATHER_BONUS,
    TALENT_MAP,
    COUNTER_BONUS,
    ALL_STATS,
)
from roco.data import load_data, load_skill_db
from roco.stats import (
    calc_stat_pvp,
    calc_all_stats,
    get_type_multiplier,
    parse_attrs,
    find_skill,
)
from roco.calculator import calculate, interactive

__all__ = [
    "NATURE_MODIFIERS", "TYPE_CHART", "WEATHER_BONUS", "TALENT_MAP",
    "COUNTER_BONUS", "ALL_STATS",
    "load_data", "load_skill_db",
    "calc_stat_pvp", "calc_all_stats", "get_type_multiplier", "parse_attrs", "find_skill",
    "calculate", "interactive",
]

if __name__ == "__main__":
    interactive()
