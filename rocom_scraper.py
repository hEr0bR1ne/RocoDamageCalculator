"""
洛克王国手游 - 精灵图鉴完整爬虫
输出：编号、名称、进化阶段、属性、种族值、特性、技能组
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import re
from pathlib import Path

BASE_URL = "https://wiki.biligame.com"
INDEX_URL = "https://wiki.biligame.com/rocom/%E7%B2%BE%E7%81%B5%E5%9B%BE%E9%89%B4"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://wiki.biligame.com/",
}


def fetch(url: str, retries: int = 3) -> BeautifulSoup | None:
    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"  [重试 {i+1}/{retries}] {e}")
            time.sleep(2)
    return None


def parse_index(soup: BeautifulSoup) -> list[dict]:
    """从图鉴主页提取所有精灵的编号、名称、进化阶段、属性、详情页链接"""
    spirits = []
    for entry in soup.find_all("div", class_="divsort"):
        # 编号
        no_span = entry.find("span", style=lambda s: s and "font-size:10px" in s)
        number = no_span.get_text(strip=True) if no_span else ""

        # 名称 + 链接（取 title 属性最准确）
        a_tag = entry.find("a", title=True)
        if not a_tag:
            continue
        name = a_tag["title"]
        href = a_tag["href"]

        # 进化阶段
        stage = entry.get("data-param1", "")

        # 属性（可能多属性）
        attrs = []
        for img in entry.find_all("img", class_="rocom_pet_icon"):
            m = re.search(r"属性\s+(\S+?)(?:\.png)?$", img.get("alt", ""))
            if m:
                attrs.append(m.group(1))

        spirits.append({
            "编号": number,
            "名称": name,
            "进化阶段": stage,
            "属性": "/".join(attrs),
            "_url": BASE_URL + href,  # 内部用，不写入最终输出
        })
    return spirits


def parse_detail(url: str) -> dict:
    """爬取精灵详情页，返回完整数据（不含URL字段）"""
    soup = fetch(url)
    if not soup:
        return {}

    data: dict = {}

    # 编号 & 名称
    name_div = soup.find("div", class_="rocom_sprite_grament_name")
    if name_div:
        text = name_div.get_text(strip=True)
        m = re.match(r"(NO\d+)[.\s]*(.+)", text)
        if m:
            data["编号"] = m.group(1)
            data["名称"] = m.group(2)
        else:
            data["名称"] = text

    # 属性
    attr_div = soup.find("div", class_="rocom_sprite_grament_attributes")
    if attr_div:
        attrs = []
        for img in attr_div.find_all("img"):
            m = re.search(r"属性\s+(\S+?)(?:\.png)?$", img.get("alt", ""))
            if m:
                attrs.append(m.group(1))
        data["属性"] = "/".join(attrs)

    # 种族值
    qual_div = soup.find("div", class_="rocom_sprite_info_qualification")
    if qual_div:
        for li in qual_div.find_all("li"):
            name_p = li.find("p", class_="rocom_sprite_info_qualification_name")
            val_p = li.find("p", class_="rocom_sprite_info_qualification_value")
            if name_p and val_p:
                data[f"种族值_{name_p.get_text(strip=True)}"] = val_p.get_text(strip=True)

    # 种族值总和
    stat_keys = ["种族值_生命", "种族值_物攻", "种族值_魔攻", "种族值_物防", "种族值_魔防", "种族值_速度"]
    total = sum(int(data[k]) for k in stat_keys if data.get(k, "").isdigit())
    if total:
        data["种族值_总和"] = total

    # 特性
    char_div = soup.find("div", class_="rocom_sprite_characteristic")
    if char_div:
        title_p = char_div.find("p", class_="rocom_sprite_info_characteristic_title")
        text_p = char_div.find("p", class_="rocom_sprite_info_characteristic_text")
        if title_p:
            data["特性名称"] = title_p.get_text(strip=True)
        if text_p:
            data["特性效果"] = text_p.get_text(strip=True)

    # 简介
    info_content = soup.find("div", class_="rocom_sprite_info_content")
    if info_content:
        data["简介"] = info_content.get_text(strip=True)

    # 技能组（三个标签页：精灵技能 / 血脉技能 / 可学技能石）
    def parse_skill_boxes(boxes, tab_name):
        result = []
        for box in boxes:
            skill = {"来源": tab_name}

            lv = box.find("div", class_="rocom_sprite_skill_level")
            if lv:
                skill["习得等级"] = lv.get_text(strip=True)

            attr_img = box.find("img", class_="rocom_sprite_skill_attr")
            if attr_img:
                m = re.search(r"属性\s+(\S+?)(?:\.png)?$", attr_img.get("alt", ""))
                if m:
                    skill["技能属性"] = m.group(1)

            inner = box.find("div", class_="rocom_sprite_skill_inner")
            if inner:
                for cls, key in [
                    ("rocom_sprite_skillName",    "技能名"),
                    ("rocom_sprite_skillDamage",  "能耗"),
                    ("rocom_sprite_skillType",    "类别"),
                    ("rocom_sprite_skill_power",  "威力"),
                    ("rocom_sprite_skillContent", "效果"),
                ]:
                    el = inner.find("div", class_=cls)
                    if el:
                        skill[key] = el.get_text(strip=True)

            if skill.get("技能名"):
                result.append(skill)
        return result

    skills = []
    tabber = soup.find("div", class_="tabber")
    if tabber:
        for panel in tabber.find_all("div", class_="tabbertab"):
            tab_name = panel.get("title", "")
            boxes = panel.find_all("div", class_="rocom_sprite_skill_box")
            skills.extend(parse_skill_boxes(boxes, tab_name))
    else:
        # 兼容旧版无标签页结构
        skill_skillbox = soup.find("div", class_="rocom_sprite_skill_skillBox")
        if skill_skillbox:
            boxes = skill_skillbox.find_all("div", class_="rocom_sprite_skill_box")
            skills.extend(parse_skill_boxes(boxes, "精灵技能"))

    data["技能组"] = skills
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


def save_skills_csv(records: list[dict], path: Path):
    rows = []
    for spirit in records:
        for skill in spirit.get("技能组", []):
            row = {"编号": spirit.get("编号", ""), "精灵名称": spirit.get("名称", "")}
            row.update(skill)
            rows.append(row)
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  -> {path.name} ({len(rows)} 条技能记录)")


def main():
    print("=== 洛克王国精灵图鉴爬虫 ===\n")

    print("Step 1: 获取图鉴主页...")
    index_soup = fetch(INDEX_URL)
    if not index_soup:
        print("主页获取失败")
        return

    index = parse_index(index_soup)
    print(f"发现 {len(index)} 只精灵\n")

    print("Step 2: 逐个爬取详情页...")
    results = []
    failed = []

    for i, entry in enumerate(index, 1):
        print(f"[{i:>3}/{len(index)}] {entry['编号']} {entry['名称']}", end=" ... ", flush=True)
        detail = parse_detail(entry["_url"])

        if not detail.get("名称"):
            print("失败")
            failed.append(entry)
            continue

        # 用主页的进化阶段补充（详情页没有这个字段）
        detail["进化阶段"] = entry.get("进化阶段", "")
        results.append(detail)
        print(f"OK  种族值总和={detail.get('种族值_总和', '?')}  技能数={len(detail.get('技能组', []))}")
        time.sleep(0.6)

    print(f"\n成功: {len(results)}  失败: {len(failed)}\n")

    print("Step 3: 保存结果...")
    save_json(results, OUTPUT_DIR / "精灵完整数据.json")
    save_csv(results, OUTPUT_DIR / "精灵基础数据.csv")
    save_skills_csv(results, OUTPUT_DIR / "精灵技能组.csv")

    if failed:
        save_json(failed, OUTPUT_DIR / "failed.json")
        print(f"  -> failed.json ({len(failed)} 条失败)")

    print(f"\n完成！文件保存在 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
