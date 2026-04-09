import type {
  DamageInput,
  DamageResult,
  Skill,
  Spirit,
  StatName,
} from "@/lib/types";

export const ALL_STATS: StatName[] = ["生命", "物攻", "魔攻", "物防", "魔防", "速度"];
export const WEATHER_OPTIONS = ["无", "雨天", "晴天", "沙暴", "冰雹"] as const;
export const TALENT_OPTIONS = [8, 9, 10] as const;

type NatureModifiers = Record<string, Partial<Record<StatName, number>>>;
type TypeChart = Record<string, { strong: string[]; resist: string[] }>;
type CounterInfo = { type: "multiply" | "add"; value: number; note: string };
type CounterMap = Record<string, CounterInfo>;

export const NATURE_MODIFIERS: NatureModifiers = {
  保守: { 物攻: 0.9, 魔攻: 1.2 },
  稳重: { 物防: 0.9, 魔攻: 1.2 },
  马虎: { 魔防: 0.9, 魔攻: 1.2 },
  冷静: { 速度: 0.9, 魔攻: 1.2 },
  认真: { 生命: 0.9, 魔攻: 1.2 },
  固执: { 物攻: 1.2, 魔攻: 0.9 },
  孤僻: { 物攻: 1.2, 物防: 0.9 },
  调皮: { 物攻: 1.2, 魔防: 0.9 },
  勇敢: { 物攻: 1.2, 速度: 0.9 },
  坦率: { 物攻: 1.2, 生命: 0.9 },
  沉着: { 物攻: 0.9, 魔防: 1.2 },
  慎重: { 魔攻: 0.9, 魔防: 1.2 },
  温顺: { 物防: 0.9, 魔防: 1.2 },
  狂妄: { 速度: 0.9, 魔防: 1.2 },
  实干: { 生命: 0.9, 魔防: 1.2 },
  大胆: { 物攻: 0.9, 物防: 1.2 },
  淘气: { 魔攻: 0.9, 物防: 1.2 },
  悠闲: { 速度: 0.9, 物防: 1.2 },
  懒散: { 魔防: 0.9, 物防: 1.2 },
  害羞: { 生命: 0.9, 物防: 1.2 },
  胆小: { 物攻: 0.9, 速度: 1.2 },
  开朗: { 魔攻: 0.9, 速度: 1.2 },
  急躁: { 物防: 0.9, 速度: 1.2 },
  天真: { 魔防: 0.9, 速度: 1.2 },
  浮躁: { 生命: 0.9, 速度: 1.2 },
  沉默: { 物攻: 0.9, 生命: 1.2 },
  平和: { 魔攻: 0.9, 生命: 1.2 },
  理智: { 物防: 0.9, 生命: 1.2 },
  犹豫: { 魔防: 0.9, 生命: 1.2 },
  紧张: { 速度: 0.9, 生命: 1.2 },
  无: {},
};

const TYPE_CHART: TypeChart = {
  普通: { strong: [], resist: ["地", "幽", "机械"] },
  草: { strong: ["水", "光", "地"], resist: ["火", "龙", "毒", "虫", "翼", "机械"] },
  火: { strong: ["草", "冰", "虫", "机械"], resist: ["水", "地", "龙"] },
  水: { strong: ["火", "地", "机械"], resist: ["草", "冰", "龙"] },
  光: { strong: ["幽", "恶"], resist: ["草", "冰"] },
  地: { strong: ["火", "冰", "电", "毒"], resist: ["草", "武"] },
  冰: { strong: ["草", "地", "龙", "翼"], resist: ["火", "冰", "机械"] },
  龙: { strong: ["龙"], resist: ["机械"] },
  电: { strong: ["水", "翼"], resist: ["草", "地", "龙", "电"] },
  毒: { strong: ["草", "萌"], resist: ["地", "毒", "幽", "机械"] },
  虫: { strong: ["草", "恶", "幻"], resist: ["火", "毒", "武", "翼", "萌", "幽", "机械"] },
  武: { strong: ["普通", "地", "冰", "恶", "机械"], resist: ["毒", "虫", "翼", "萌", "幽", "幻"] },
  翼: { strong: ["草", "虫", "武"], resist: ["地", "龙", "电", "机械"] },
  萌: { strong: ["龙", "武", "恶"], resist: ["火", "毒", "机械"] },
  幽: { strong: ["光", "幽", "幻"], resist: ["普通", "恶"] },
  恶: { strong: ["毒", "萌", "幽"], resist: ["光", "武", "恶"] },
  机械: { strong: ["地", "冰", "萌"], resist: ["火", "水", "电", "机械"] },
  幻: { strong: ["毒", "武"], resist: ["光", "机械", "幻"] },
};

const WEATHER_BONUS: Record<string, Record<string, number>> = {
  无: {},
  雨天: { 水: 1.5 },
  晴天: { 火: 1.5 },
  沙暴: { 地: 1.3 },
  冰雹: { 冰: 1.3 },
};

const TALENT_MAP: Record<number, number> = { 8: 48, 9: 54, 10: 60 };

const COUNTER_BONUS: CounterMap = {
  突袭: { type: "multiply", value: 3, note: "应对状态：威力×3" },
  偷袭: { type: "multiply", value: 3, note: "应对状态：威力×3" },
  闪燃: { type: "multiply", value: 4, note: "应对状态：威力×4" },
  虫击: { type: "multiply", value: 2, note: "应对状态：威力×2，无视系别抵抗" },
  无影脚: { type: "multiply", value: 2, note: "应对状态：威力×2" },
  技巧打击: { type: "multiply", value: 10, note: "应对状态：威力×10" },
  爆冲: { type: "multiply", value: 5, note: "应对状态：威力×5" },
  龙卷风: { type: "multiply", value: 1.5, note: "应对状态：威力×1.5" },
  暗突袭: { type: "multiply", value: 2, note: "应对状态：威力×2（含吸血50%）" },
  地陷: { type: "multiply", value: 2, note: "应对状态：威力×2" },
  吹炎: { type: "multiply", value: 2, note: "应对状态：威力×2" },
  滚雪球: { type: "multiply", value: 2, note: "应对状态：威力×2（+2层冻结）" },
  炙热波动: { type: "multiply", value: 2, note: "应对状态：威力×2" },
  连续爪击: { type: "multiply", value: 2, note: "应对状态：2连击→4连击，威力×2" },
  追打: { type: "multiply", value: 3, note: "应对状态：1连击→3连击，威力×3" },
  散手: { type: "multiply", value: 3, note: "应对状态：2连击→6连击，威力×3" },
  气势一击: { type: "add", value: 180, note: "上回合应对成功：威力+180" },
};

export function parseAttrs(attr: string | undefined): string[] {
  if (!attr) return [];
  return attr.split("/").map((s) => s.trim()).filter(Boolean);
}

export function findSkill(spirit: Spirit, skillName: string): Skill | undefined {
  return (spirit.技能组 ?? []).find((skill) => skill.技能名 === skillName);
}

function toNumber(value: unknown): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  if (typeof value === "string") {
    const n = Number(value.trim());
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

function calcStatPvp(
  base: number,
  stat: StatName,
  hasTalent: boolean,
  talentTier: number,
  nature: string,
): number {
  const actualTalent = hasTalent ? (TALENT_MAP[talentTier] ?? talentTier * 6) : 0;
  const l = (base + actualTalent / 2) / 100;
  const natureCoeff = NATURE_MODIFIERS[nature]?.[stat] ?? 1;
  const raw = stat === "生命" ? (170 * l + 70) * natureCoeff + 100 : (110 * l + 10) * natureCoeff + 50;
  return Math.floor(raw);
}

function calcAllStats(spirit: Spirit, talentTier: number, talentStats: StatName[], nature: string): Record<StatName, number> {
  const statMap: Record<StatName, string> = {
    生命: "种族值_生命",
    物攻: "种族值_物攻",
    魔攻: "种族值_魔攻",
    物防: "种族值_物防",
    魔防: "种族值_魔防",
    速度: "种族值_速度",
  };
  const computed = {} as Record<StatName, number>;
  for (const stat of ALL_STATS) {
    const base = toNumber(spirit[statMap[stat]]);
    computed[stat] = calcStatPvp(base, stat, talentStats.includes(stat), talentTier, nature);
  }
  return computed;
}

function getTypeMultiplier(skillAttr: string, defenderAttrs: string[]): number {
  const chart = TYPE_CHART[skillAttr] ?? { strong: [], resist: [] };
  let mult = 1;
  for (const attr of defenderAttrs) {
    if (chart.strong.includes(attr)) mult *= 1.5;
    else if (chart.resist.includes(attr)) mult *= 0.75;
  }
  return mult;
}

export function calculateDamage(input: DamageInput): DamageResult {
  if (input.attackerTalentStats.length !== 3 || input.defenderTalentStats.length !== 3) {
    throw new Error("攻击方和防御方都必须勾选 3 个天分属性。");
  }

  const skill = findSkill(input.attacker, input.skillName);
  if (!skill) {
    throw new Error(`未找到技能「${input.skillName}」。`);
  }

  const atkStats = calcAllStats(input.attacker, input.attackerTalent, input.attackerTalentStats, input.attackerNature);
  const defStats = calcAllStats(input.defender, input.defenderTalent, input.defenderTalentStats, input.defenderNature);

  const skillPower = toNumber(skill.威力);
  const skillCost = toNumber(skill.能耗);
  const skillCategory = String(skill.类别 ?? "");
  const skillAttr = String(skill.技能属性 ?? "");
  const skillEffect = String(skill.效果 ?? "");

  let attackerStatLabel: "物攻" | "魔攻";
  let defenderStatLabel: "物防" | "魔防";
  let attackerStat: number;
  let defenderStat: number;
  if (skillCategory === "物攻") {
    attackerStatLabel = "物攻";
    defenderStatLabel = "物防";
    attackerStat = atkStats.物攻;
    defenderStat = defStats.物防;
  } else if (skillCategory === "魔攻") {
    attackerStatLabel = "魔攻";
    defenderStatLabel = "魔防";
    attackerStat = atkStats.魔攻;
    defenderStat = defStats.魔防;
  } else {
    throw new Error(`技能类别「${skillCategory}」不是攻击技能。`);
  }

  const defAttrs = parseAttrs(String(input.defender.属性 ?? ""));
  const atkAttrs = parseAttrs(String(input.attacker.属性 ?? ""));
  let typeMult = getTypeMultiplier(skillAttr, defAttrs);
  if (input.counterHit && input.skillName === "虫击") {
    typeMult = Math.max(typeMult, 1);
  }
  const stabMult = atkAttrs.includes(skillAttr) ? 1.25 : 1;
  const weatherMult = WEATHER_BONUS[input.weather]?.[skillAttr] ?? 1;

  const denominator = 1 + input.atkDownPct / 100 + input.defUpPct / 100;
  if (denominator <= 0) {
    throw new Error("能力等级分母小于等于 0，请检查增减益参数。");
  }
  const abilityLevel = (1 + input.atkUpPct / 100 + input.defDownPct / 100) / denominator;

  const counterInfo = COUNTER_BONUS[input.skillName];
  let counterMult = 1;
  let counterAdd = 0;
  if (input.counterHit && counterInfo) {
    if (counterInfo.type === "multiply") counterMult = counterInfo.value;
    else counterAdd = counterInfo.value;
  }

  const effectivePower = (skillPower * counterMult + input.powerAdd + counterAdd) * (1 + input.traitPowerPct / 100);
  let damage = (attackerStat / defenderStat) * 0.9 * effectivePower * abilityLevel * input.powerBuff * stabMult * typeMult * weatherMult;
  if (input.defReducePct > 0) {
    damage *= 1 - input.defReducePct / 100;
  }
  damage = Math.floor(damage);

  const defenderHp = defStats.生命;
  const damagePct = defenderHp > 0 ? (damage / defenderHp) * 100 : 0;
  const koTurns = damagePct > 0 ? Math.ceil(100 / damagePct) : 999;

  let speedTag = "同速";
  if (atkStats.速度 > defStats.速度) {
    speedTag = `先手 (${atkStats.速度} > ${defStats.速度})`;
  } else if (atkStats.速度 < defStats.速度) {
    speedTag = `后手 (${atkStats.速度} < ${defStats.速度})`;
  }

  return {
    damage,
    damagePct,
    koTurns,
    attackerStatLabel,
    defenderStatLabel,
    attackerStat,
    defenderStat,
    attackerHp: atkStats.生命,
    defenderHp,
    attackerSpeed: atkStats.速度,
    defenderSpeed: defStats.速度,
    speedTag,
    typeMult,
    stabMult,
    weatherMult,
    abilityLevel,
    effectivePower,
    skillPower,
    skillCost,
    skillCategory,
    skillAttr,
    skillEffect,
    counterNote: input.counterHit && counterInfo ? counterInfo.note : "",
  };
}
