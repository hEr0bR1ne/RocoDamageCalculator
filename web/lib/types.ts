export type StatName = "生命" | "物攻" | "魔攻" | "物防" | "魔防" | "速度";

export type SkillCategory = "物攻" | "魔攻" | "状态" | string;

export interface Skill {
  来源?: string;
  习得等级?: string;
  技能名?: string;
  能耗?: number | string;
  类别?: SkillCategory;
  威力?: number | string;
  效果?: string;
  技能属性?: string;
  [key: string]: unknown;
}

export interface Spirit {
  编号?: string;
  名称: string;
  属性?: string;
  特性名称?: string;
  特性效果?: string;
  技能组?: Skill[];
  [key: string]: unknown;
}

export interface DamageInput {
  attacker: Spirit;
  defender: Spirit;
  attackerNature: string;
  defenderNature: string;
  attackerTalent: number;
  defenderTalent: number;
  attackerTalentStats: StatName[];
  defenderTalentStats: StatName[];
  skillName: string;
  atkUpPct: number;
  atkDownPct: number;
  defUpPct: number;
  defDownPct: number;
  powerAdd: number;
  powerBuff: number;
  traitPowerPct: number;
  weather: string;
  defReducePct: number;
  counterHit: boolean;
}

export interface DamageResult {
  damage: number;
  damagePct: number;
  koTurns: number;
  attackerStatLabel: "物攻" | "魔攻";
  defenderStatLabel: "物防" | "魔防";
  attackerStat: number;
  defenderStat: number;
  attackerHp: number;
  defenderHp: number;
  attackerSpeed: number;
  defenderSpeed: number;
  speedTag: string;
  typeMult: number;
  stabMult: number;
  weatherMult: number;
  abilityLevel: number;
  effectivePower: number;
  skillPower: number;
  skillCost: number;
  skillCategory: string;
  skillAttr: string;
  skillEffect: string;
  counterNote: string;
}
