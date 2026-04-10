"""
技能图鉴爬虫：爬取 wiki.biligame.com/rocom 技能图鉴
输出：技能名、属性、类别、能耗、威力、效果、可学习精灵
"""
import csv
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL        = "https://wiki.biligame.com"
SKILL_INDEX_URL = "https://wiki.biligame.com/rocom/%E6%8A%80%E8%83%BD%E5%9B%BE%E9%89%B4"
import sys as _sys
OUTPUT_DIR = ((Path(_sys.executable).parent if getattr(_sys, "frozen", False)
               else Path(__file__).parent.parent.parent) / "data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://wiki.biligame.com/rocom/",
}


def make_session() -> requests.Session:
    s = requests.Session()
    s.get("https://wiki.biligame.com/rocom/", headers=HEADERS, timeout=15)
    return s


def fetch(session: requests.Session, url: str, retries: int = 3) -> BeautifulSoup | None:
    for i in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"  [重试 {i + 1}/{retries}] {e}")
            time.sleep(2)
    return None


def parse_skill_index(soup: BeautifulSoup) -> list[dict]:
    skills, seen = [], set()
    for entry in soup.find_all("div", class_="divsort"):
        a_tag = entry.find("a", title=True)
        if not a_tag:
            continue
        name = a_tag["title"]
        if name in seen:
            continue
        seen.add(name)
        skills.append({
            "技能名": name,
            "属性":   entry.get("data-param2", ""),
            "类别":   entry.get("data-param1", ""),
            "_url":   BASE_URL + a_tag["href"],
        })
    return skills


def parse_skill_detail(soup: BeautifulSoup) -> dict:
    data = {}
    box  = soup.find("div", class_="rocom_skill_template_box")
    if not box:
        return data

    name_div = box.find("div", class_="rocom_skill_template_skillName")
    if name_div:
        data["技能名"] = name_div.get_text(strip=True)

    attr_div = box.find("div", class_="rocom_skill_template_skillAttribute")
    if attr_div:
        data["属性"] = attr_div.get_text(strip=True)

    consume_div = box.find("div", class_="rocom_skill_template_skillConsume")
    if consume_div:
        span = consume_div.find("span")
        if span:
            data["能耗"] = span.get_text(strip=True)

    sort_div = box.find("div", class_="rocom_skill_template_skillSort")
    if sort_div:
        data["类别"] = sort_div.get_text(strip=True)

    power_div = box.find("div", class_="rocom_skill_template_skillPower")
    if power_div:
        b_tag = power_div.find("b")
        if b_tag:
            data["威力"] = b_tag.get_text(strip=True)

    effect_div = box.find("div", class_="rocom_skill_template_skillEffect")
    if effect_div:
        data["效果"] = effect_div.get_text(strip=True).lstrip("✦").strip()

    canlearn_box = soup.find("div", class_="rocom_canlearn_box")
    learnable = []
    if canlearn_box:
        for a in canlearn_box.find_all("a", title=True):
            learnable.append(a["title"])
    data["可学习精灵"]  = learnable
    data["可学习精灵数"] = len(learnable)

    return data


def save_json(data, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  -> {path.name} ({len(data)} 条)")


def save_csv(records: list[dict], path: Path):
    flat = [{k: v for k, v in r.items() if not isinstance(v, list)} for r in records]
    if not flat:
        return
    keys = list(flat[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)
    print(f"  -> {path.name} ({len(flat)} 条)")


def main():
    print("=== 洛克王国技能图鉴爬虫 ===\n")

    session = make_session()

    print("Step 1: 获取技能图鉴主页...")
    index_soup = fetch(session, SKILL_INDEX_URL)
    if not index_soup:
        print("主页获取失败")
        return

    index = parse_skill_index(index_soup)
    print(f"发现 {len(index)} 个技能\n")

    print("Step 2: 逐个爬取技能详情...")
    results, failed = [], []

    for i, entry in enumerate(index, 1):
        print(f"[{i:>3}/{len(index)}] {entry['技能名']}", end=" ... ", flush=True)
        soup = fetch(session, entry["_url"])
        if not soup:
            print("失败")
            failed.append(entry)
            continue
        detail = parse_skill_detail(soup)
        if not detail.get("技能名"):
            detail["技能名"] = entry["技能名"]
        if not detail.get("属性"):
            detail["属性"] = entry["属性"]
        if not detail.get("类别"):
            detail["类别"] = entry["类别"]
        results.append(detail)
        print(f"OK  威力:{detail.get('威力','?')}  能耗:{detail.get('能耗','?')}  可学:{detail.get('可学习精灵数',0)}只")
        time.sleep(0.6)

    print(f"\n成功: {len(results)}  失败: {len(failed)}\n")

    print("Step 3: 保存结果...")
    save_json(results, OUTPUT_DIR / "技能完整数据.json")
    save_csv(results,  OUTPUT_DIR / "技能数据.csv")
    if failed:
        save_json(failed, OUTPUT_DIR / "技能_failed.json")

    print(f"\n完成！文件保存在 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
