"""
伤害计算核心：calculate() 函数 + 交互式 CLI 入口
"""
import math

from .constants import (
    NATURE_MODIFIERS, TALENT_MAP, COUNTER_BONUS, WEATHER_BONUS, ALL_STATS,
)
from .data import load_data
from .stats import calc_all_stats, get_type_multiplier, parse_attrs, find_skill


def calculate(
    attacker_name: str,
    attacker_nature: str,
    attacker_talent: int,              # 个体值档位：8/9/10
    attacker_talent_stats: list[str],  # 攻击方天分加成的三个属性
    skill_name: str,
    defender_name: str,
    defender_nature: str,
    defender_talent: int,              # 个体值档位：8/9/10
    defender_talent_stats: list[str],  # 防御方天分加成的三个属性
    # 能力等级参数（百分比，如力量增效+30填30）
    atk_up_pct:      float = 0.0,   # 我方攻击提升%
    atk_down_pct:    float = 0.0,   # 我方攻击降低%
    def_up_pct:      float = 0.0,   # 敌方防御提升%
    def_down_pct:    float = 0.0,   # 敌方防御降低%
    # 威力相关
    power_add:       float = 0.0,   # 威力加成（固定加值，如极寒领域+60）
    power_buff:      float = 1.0,   # 威力提升buff乘数（如翻倍填2.0）
    trait_power_pct: float = 0.0,   # 特性威力加成%（如勇敢+40，顺风+50）
    # 其他
    weather:         str   = "无",
    def_reduce_pct:  float = 0.0,
    current_energy:  int   = -1,
    counter_hit:     bool  = False,  # 应对成功
):
    db = load_data()

    atk_spirit = db.get(attacker_name)
    def_spirit = db.get(defender_name)
    if not atk_spirit:
        matches = [n for n in db if attacker_name in n]
        print(f"未找到「{attacker_name}」，相似：{matches[:5]}")
        return
    if not def_spirit:
        matches = [n for n in db if defender_name in n]
        print(f"未找到「{defender_name}」，相似：{matches[:5]}")
        return

    skill = find_skill(atk_spirit, skill_name)
    if not skill:
        print(f"{attacker_name} 没有技能「{skill_name}」")
        print(f"可用技能：{[s['技能名'] for s in atk_spirit.get('技能组', [])]}")
        return

    skill_power    = int(skill.get("威力", 0) or 0)
    skill_category = skill.get("类别", "")
    skill_attr     = skill.get("技能属性", "")
    skill_cost     = int(skill.get("能耗", 0) or 0)

    atk_stats = calc_all_stats(atk_spirit, attacker_talent, attacker_talent_stats, attacker_nature)
    def_stats = calc_all_stats(def_spirit, defender_talent, defender_talent_stats, defender_nature)

    if skill_category == "物攻":
        atk_val = atk_stats["物攻"]
        def_val = def_stats["物防"]
        atk_label, def_label = "物攻", "物防"
    elif skill_category == "魔攻":
        atk_val = atk_stats["魔攻"]
        def_val = def_stats["魔防"]
        atk_label, def_label = "魔攻", "魔防"
    else:
        print(f"技能类别「{skill_category}」为非攻击技能，无伤害输出")
        return

    def_attrs      = parse_attrs(def_spirit.get("属性", ""))
    atk_attrs_list = parse_attrs(atk_spirit.get("属性", ""))
    type_mult      = get_type_multiplier(skill_attr, def_attrs)
    if counter_hit and skill_name == "虫击":
        type_mult = max(type_mult, 1.0)
    stab_mult    = 1.25 if skill_attr in atk_attrs_list else 1.0
    weather_mult = WEATHER_BONUS.get(weather, {}).get(skill_attr, 1.0)

    ability_level = (1.0 + atk_up_pct / 100.0 + def_down_pct / 100.0) / \
                    (1.0 + atk_down_pct / 100.0 + def_up_pct / 100.0)

    counter_info = COUNTER_BONUS.get(skill_name)
    counter_mult = 1.0
    counter_add  = 0.0
    if counter_hit and counter_info:
        if counter_info["type"] == "multiply":
            counter_mult = counter_info["value"]
        elif counter_info["type"] == "add":
            counter_add  = counter_info["value"]

    effective_power = (skill_power * counter_mult + power_add + counter_add) * (1.0 + trait_power_pct / 100.0)

    base_dmg = atk_val / def_val * 0.9 * effective_power * ability_level * power_buff * stab_mult * type_mult * weather_mult
    if def_reduce_pct > 0:
        base_dmg *= (1.0 - def_reduce_pct / 100.0)
    base_dmg = math.floor(base_dmg)

    dmg_low  = base_dmg
    dmg_high = base_dmg
    def_hp   = def_stats["生命"]
    pct_low  = dmg_low  / def_hp * 100 if def_hp else 0
    pct_high = dmg_high / def_hp * 100 if def_hp else 0

    atk_spd = atk_stats["速度"]
    def_spd = def_stats["速度"]
    if atk_spd > def_spd:
        speed_result = f"先手 ✓  ({atk_spd} > {def_spd})"
    elif atk_spd < def_spd:
        speed_result = f"后手 ✗  ({atk_spd} < {def_spd}，差{def_spd - atk_spd}点)"
    else:
        speed_result = f"同速 (均为{atk_spd}，随机决定)"

    energy_note = ""
    if current_energy >= 0:
        if current_energy >= skill_cost:
            energy_note = f"✓ 可释放 (当前{current_energy}，消耗{skill_cost}，剩余{current_energy - skill_cost})"
        else:
            energy_note = f"✗ 能量不足 (当前{current_energy}，需要{skill_cost})"

    W = 58
    atk_attrs = atk_spirit.get("属性", "")
    actual_atk_talent = TALENT_MAP.get(attacker_talent, attacker_talent * 6)
    actual_def_talent = TALENT_MAP.get(defender_talent, defender_talent * 6)
    atk_talent_str = "/".join(attacker_talent_stats)
    def_talent_str = "/".join(defender_talent_stats)

    print("=" * W)
    print(f"  攻击方：{attacker_name} [{atk_attrs}]  个体:{attacker_talent}({actual_atk_talent})→[{atk_talent_str}]  {attacker_nature}")
    print(f"    {atk_label}:{atk_val}  生命:{atk_stats['生命']}  速度:{atk_spd}")
    print()
    print(f"  防御方：{defender_name} [{'/'.join(def_attrs)}]  个体:{defender_talent}({actual_def_talent})→[{def_talent_str}]  {defender_nature}")
    print(f"    {def_label}:{def_val}  生命:{def_hp}  速度:{def_spd}")
    print()
    print(f"  技能：{skill_name}  [{skill_attr}系/{skill_category}]  威力:{skill_power}  能耗:{skill_cost}")
    if skill.get("效果"):
        print(f"  效果：{skill['效果']}")
    atk_trait     = atk_spirit.get("特性名称", "")
    atk_trait_eff = atk_spirit.get("特性效果", "")
    if atk_trait:
        print(f"  特性：{atk_trait} — {atk_trait_eff}")
    if counter_hit and counter_info:
        print(f"  ★应对成功：{counter_info['note']}  → 实际威力:{effective_power:.0f}")
    elif counter_hit and not counter_info:
        print(f"  (应对成功，但该技能无伤害加成)")
    print()
    print(f"  先后手：{speed_result}")
    if energy_note:
        print(f"  能量：{energy_note}")
    print()

    mults = []
    type_tag = "★克制" if type_mult > 1 else ("▼不克制" if type_mult < 1 else "普通")
    mults.append(f"属性克制×{type_mult:.2f}({type_tag})")
    if stab_mult != 1.0:
        mults.append(f"本系补正×{stab_mult:.2f}")
    if weather_mult != 1.0:
        mults.append(f"天气({weather})×{weather_mult:.2f}")
    if ability_level != 1.0:
        mults.append(f"能力等级×{ability_level:.3f}")
    if power_buff != 1.0:
        mults.append(f"威力buff×{power_buff:.2f}")
    if trait_power_pct:
        mults.append(f"特性威力+{trait_power_pct:.0f}%")
    if power_add:
        mults.append(f"威力加成+{power_add:.0f}")
    if def_reduce_pct:
        mults.append(f"减伤×{(1 - def_reduce_pct / 100):.2f}")
    print(f"  加成：{'  '.join(mults)}")
    print()

    ko_min   = math.ceil(100 / pct_high) if pct_high > 0 else 999
    ko_max   = math.ceil(100 / pct_low)  if pct_low  > 0 else 999
    one_shot = "★一击必杀" if pct_low >= 100 else ("可能一击" if pct_high >= 100 else "")

    print(f"  ┌{'─' * (W - 4)}┐")
    print(f"  │  伤害：{dmg_low} ~ {dmg_high}  ({pct_low:.1f}% ~ {pct_high:.1f}% 血量)  {one_shot:<8}│")
    print(f"  │  对方血量：{def_hp}  需要 {ko_min}~{ko_max} 次击倒{' ' * (W - 28 - len(str(def_hp)) - len(str(ko_min)) - len(str(ko_max)))}│")
    print(f"  └{'─' * (W - 4)}┘")
    print()

    formula = f"floor({atk_val}/{def_val} × 0.9 × {effective_power:.0f}"
    if stab_mult != 1.0:
        formula += f" × {stab_mult:.2f}(本系)"
    if ability_level != 1.0:
        formula += f" × {ability_level:.3f}(能力等级)"
    if power_buff != 1.0:
        formula += f" × {power_buff:.2f}(威力buff)"
    if type_mult != 1.0:
        formula += f" × {type_mult:.2f}(克制)"
    if weather_mult != 1.0:
        formula += f" × {weather_mult:.2f}(天气)"
    if def_reduce_pct:
        formula += f" × {1 - def_reduce_pct / 100:.2f}(减伤)"
    formula += f") = {base_dmg}"
    print(f"  公式：{formula}")
    print("=" * W)


def interactive():
    db = load_data()
    print("RocoDamageCalculator（竞技场版）")
    print(f"已加载 {len(db)} 只精灵  |  竞技场默认满级满培养")
    print()
    print("性格：" + "  ".join(NATURE_MODIFIERS.keys()))
    print("个体值档位：8=48  9=54  10=60（最高）")
    print("天分属性：生命 物攻 魔攻 物防 魔防 速度（选3个，空格分隔）")
    print("天气：无  雨天  晴天  沙暴  冰雹")
    print()

    def input_talent_stats(prompt: str) -> list[str]:
        while True:
            raw = input(prompt).strip()
            if not raw:
                return []
            parts = [p.strip() for p in raw.split() if p.strip()]
            invalid = [p for p in parts if p not in ALL_STATS]
            if invalid:
                print(f"  无效属性：{invalid}，可选：{ALL_STATS}")
                continue
            if len(parts) != 3:
                print(f"  请选择恰好3个属性（当前{len(parts)}个）")
                continue
            return parts

    while True:
        try:
            print("─" * 50)
            atk_name = input("攻击方精灵（q退出）: ").strip()
            if atk_name.lower() == "q":
                break
            if atk_name not in db:
                print(f"相似：{[n for n in db if atk_name in n][:6]}")
                continue

            atk_talent       = int(input("个体值档位 8/9/10 [10]: ").strip() or "10")
            atk_talent_stats = input_talent_stats("天分属性（3个，空格分隔，如：生命 物攻 速度）: ")
            atk_nat          = input("性格 [无]: ").strip() or "无"
            atk_up           = float(input("我方攻击提升% [0]: ").strip() or "0")
            atk_down         = float(input("我方攻击降低% [0]: ").strip() or "0")

            atk_trait     = db[atk_name].get("特性名称", "")
            atk_trait_eff = db[atk_name].get("特性效果", "")
            if atk_trait:
                print(f"  特性：{atk_trait} — {atk_trait_eff}")
            trait_power    = float(input("特性威力加成% [0]: ").strip() or "0")
            energy         = input("当前能量 (不填则不检查): ").strip()
            current_energy = int(energy) if energy else -1

            skills = db[atk_name].get("技能组", [])
            print(f"\n  {atk_name} 的技能：")
            for sk in skills:
                print(f"    [{sk.get('类别','?')}] {sk.get('技能名',''):12} 威力:{sk.get('威力','?'):>4}  能耗:{sk.get('能耗','?')}")

            skill_name = input("\n使用技能: ").strip()

            def_name = input("防御方精灵: ").strip()
            if def_name not in db:
                print(f"相似：{[n for n in db if def_name in n][:6]}")
                continue

            def_talent       = int(input("个体值档位 8/9/10 [10]: ").strip() or "10")
            def_talent_stats = input_talent_stats("天分属性（3个，空格分隔）: ")
            def_nat          = input("性格 [无]: ").strip() or "无"
            def_up           = float(input("敌方防御提升% [0]: ").strip() or "0")
            def_down         = float(input("敌方防御降低% [0]: ").strip() or "0")
            power_add        = float(input("威力加成（固定加值）[0]: ").strip() or "0")
            power_buff       = float(input("威力提升buff乘数（翻倍填2，无填1）[1]: ").strip() or "1")
            def_reduce       = float(input("应对减伤% (硬门=100，听桥=80，防御=70，无=0) [0]: ").strip() or "0")
            weather          = input("天气 (无/雨天/晴天/沙暴/冰雹) [无]: ").strip() or "无"

            counter_hit = False
            if skill_name in COUNTER_BONUS:
                info = COUNTER_BONUS[skill_name]
                ans  = input(f"应对成功？({info['note']}) [y/N]: ").strip().lower()
                counter_hit = ans == "y"

            print()
            calculate(
                attacker_name=atk_name,
                attacker_nature=atk_nat,
                attacker_talent=atk_talent,
                attacker_talent_stats=atk_talent_stats,
                skill_name=skill_name,
                defender_name=def_name,
                defender_nature=def_nat,
                defender_talent=def_talent,
                defender_talent_stats=def_talent_stats,
                atk_up_pct=atk_up,
                atk_down_pct=atk_down,
                def_up_pct=def_up,
                def_down_pct=def_down,
                power_add=power_add,
                power_buff=power_buff,
                trait_power_pct=trait_power,
                weather=weather,
                def_reduce_pct=def_reduce,
                current_energy=current_energy,
                counter_hit=counter_hit,
            )
        except (KeyboardInterrupt, EOFError):
            break
        except ValueError as e:
            print(f"输入错误：{e}")


if __name__ == "__main__":
    interactive()
