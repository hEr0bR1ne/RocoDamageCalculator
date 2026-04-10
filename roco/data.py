"""
数据加载：精灵数据库与技能数据库 JSON 文件读取
"""
import json
from pathlib import Path

DATA_PATH       = Path(__file__).parent.parent / "output" / "精灵完整数据.json"
SKILL_DATA_PATH = Path(__file__).parent.parent / "output" / "技能完整数据.json"


def load_data() -> dict[str, dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return {d["名称"]: d for d in raw if d.get("名称")}


def load_skill_db() -> dict[str, dict]:
    if not SKILL_DATA_PATH.exists():
        return {}
    with open(SKILL_DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return {s["技能名"]: s for s in raw if s.get("技能名")}
