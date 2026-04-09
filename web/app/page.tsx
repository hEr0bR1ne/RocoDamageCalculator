"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ALL_STATS,
  NATURE_MODIFIERS,
  TALENT_OPTIONS,
  WEATHER_OPTIONS,
  calculateDamage,
} from "@/lib/calc";
import type { DamageResult, Skill, Spirit, StatName } from "@/lib/types";

const DEFAULT_ATK_STATS: StatName[] = ["生命", "物攻", "速度"];
const DEFAULT_DEF_STATS: StatName[] = ["生命", "物防", "魔防"];

function toNumber(value: string, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export default function Page() {
  const [spirits, setSpirits] = useState<Spirit[]>([]);
  const [names, setNames] = useState<string[]>([]);
  const [loadError, setLoadError] = useState("");

  const [weather, setWeather] = useState<string>("无");

  const [atkName, setAtkName] = useState("");
  const [defName, setDefName] = useState("");

  const [atkTalent, setAtkTalent] = useState<number>(10);
  const [defTalent, setDefTalent] = useState<number>(10);
  const [atkNature, setAtkNature] = useState<string>("无");
  const [defNature, setDefNature] = useState<string>("无");
  const [atkTalentStats, setAtkTalentStats] = useState<StatName[]>(DEFAULT_ATK_STATS);
  const [defTalentStats, setDefTalentStats] = useState<StatName[]>(DEFAULT_DEF_STATS);

  const [skillName, setSkillName] = useState("");
  const [atkUpPct, setAtkUpPct] = useState("0");
  const [atkDownPct, setAtkDownPct] = useState("0");
  const [defUpPct, setDefUpPct] = useState("0");
  const [defDownPct, setDefDownPct] = useState("0");
  const [powerAdd, setPowerAdd] = useState("0");
  const [powerBuff, setPowerBuff] = useState("1");
  const [traitPowerPct, setTraitPowerPct] = useState("0");
  const [defReducePct, setDefReducePct] = useState("0");
  const [counterHit, setCounterHit] = useState(false);

  const [calcError, setCalcError] = useState("");
  const [result, setResult] = useState<DamageResult | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/data/精灵完整数据.json")
      .then((r) => {
        if (!r.ok) throw new Error(`读取静态数据失败：${r.status}`);
        return r.json() as Promise<Spirit[]>;
      })
      .then((data) => {
        if (!active) return;
        setSpirits(data);
        const loaded = data
          .map((s) => s.名称)
          .filter(Boolean)
          .sort((a, b) => a.localeCompare(b, "zh-CN"));
        setNames(loaded);
        setAtkName((prev) => prev || loaded[0] || "");
        setDefName((prev) => prev || loaded[1] || loaded[0] || "");
      })
      .catch((err: unknown) => {
        if (!active) return;
        setLoadError(err instanceof Error ? err.message : "读取静态数据失败");
      });
    return () => {
      active = false;
    };
  }, []);

  const atkSpirit = useMemo(
    () => spirits.find((s) => s.名称 === atkName) ?? null,
    [spirits, atkName],
  );
  const defSpirit = useMemo(
    () => spirits.find((s) => s.名称 === defName) ?? null,
    [spirits, defName],
  );

  const attackSkills = useMemo(
    () => (atkSpirit?.技能组 ?? []).filter((s): s is Skill => Boolean(s.技能名)),
    [atkSpirit],
  );

  useEffect(() => {
    if (!attackSkills.length) {
      setSkillName("");
      return;
    }
    if (!attackSkills.some((s) => s.技能名 === skillName)) {
      setSkillName(String(attackSkills[0].技能名 ?? ""));
    }
  }, [attackSkills, skillName]);

  const natureOptions = useMemo(() => Object.keys(NATURE_MODIFIERS), []);

  function toggleTalentStat(
    current: StatName[],
    stat: StatName,
    setter: (next: StatName[]) => void,
  ) {
    if (current.includes(stat)) {
      setter(current.filter((s) => s !== stat));
      return;
    }
    if (current.length >= 3) return;
    setter([...current, stat]);
  }

  function handleCalculate() {
    setCalcError("");
    setResult(null);
    if (!atkSpirit || !defSpirit) {
      setCalcError("请先选择攻击方和防御方精灵。");
      return;
    }
    if (!skillName) {
      setCalcError("请选择技能。");
      return;
    }
    try {
      const next = calculateDamage({
        attacker: atkSpirit,
        defender: defSpirit,
        attackerNature: atkNature,
        defenderNature: defNature,
        attackerTalent: atkTalent,
        defenderTalent: defTalent,
        attackerTalentStats: atkTalentStats,
        defenderTalentStats: defTalentStats,
        skillName,
        atkUpPct: toNumber(atkUpPct),
        atkDownPct: toNumber(atkDownPct),
        defUpPct: toNumber(defUpPct),
        defDownPct: toNumber(defDownPct),
        powerAdd: toNumber(powerAdd),
        powerBuff: toNumber(powerBuff, 1),
        traitPowerPct: toNumber(traitPowerPct),
        weather,
        defReducePct: toNumber(defReducePct),
        counterHit,
      });
      setResult(next);
    } catch (err: unknown) {
      setCalcError(err instanceof Error ? err.message : "计算失败");
    }
  }

  return (
    <main className="container">
      <header className="header">
        <h1>洛克王国 PVP 伤害计算器（Web）</h1>
        <p>纯静态站点：浏览器直接读取 /data/精灵完整数据.json，并在前端完成伤害计算。</p>
      </header>

      {loadError ? <p className="error">{loadError}</p> : null}

      <section className="weather">
        <label>天气</label>
        <select value={weather} onChange={(e) => setWeather(e.target.value)}>
          {WEATHER_OPTIONS.map((w) => (
            <option key={w} value={w}>
              {w}
            </option>
          ))}
        </select>
      </section>

      <section className="grid two">
        <div className="panel">
          <h2>攻击方</h2>
          <div className="field">
            <label>精灵</label>
            <select value={atkName} onChange={(e) => setAtkName(e.target.value)}>
              {names.map((n) => (
                <option key={`atk-${n}`} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>属性</label>
            <div className="readonly">{String(atkSpirit?.属性 ?? "-")}</div>
          </div>
          <div className="field">
            <label>个体档位</label>
            <select value={atkTalent} onChange={(e) => setAtkTalent(Number(e.target.value))}>
              {TALENT_OPTIONS.map((n) => (
                <option key={`atk-talent-${n}`} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>性格</label>
            <select value={atkNature} onChange={(e) => setAtkNature(e.target.value)}>
              {natureOptions.map((n) => (
                <option key={`atk-nature-${n}`} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>天分属性（选 3 个）</label>
            <div className="chips">
              {ALL_STATS.map((s) => (
                <button
                  type="button"
                  key={`atk-stat-${s}`}
                  className={atkTalentStats.includes(s) ? "chip active" : "chip"}
                  onClick={() => toggleTalentStat(atkTalentStats, s, setAtkTalentStats)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>防御方</h2>
          <div className="field">
            <label>精灵</label>
            <select value={defName} onChange={(e) => setDefName(e.target.value)}>
              {names.map((n) => (
                <option key={`def-${n}`} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>属性</label>
            <div className="readonly">{String(defSpirit?.属性 ?? "-")}</div>
          </div>
          <div className="field">
            <label>个体档位</label>
            <select value={defTalent} onChange={(e) => setDefTalent(Number(e.target.value))}>
              {TALENT_OPTIONS.map((n) => (
                <option key={`def-talent-${n}`} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>性格</label>
            <select value={defNature} onChange={(e) => setDefNature(e.target.value)}>
              {natureOptions.map((n) => (
                <option key={`def-nature-${n}`} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>天分属性（选 3 个）</label>
            <div className="chips">
              {ALL_STATS.map((s) => (
                <button
                  type="button"
                  key={`def-stat-${s}`}
                  className={defTalentStats.includes(s) ? "chip active" : "chip"}
                  onClick={() => toggleTalentStat(defTalentStats, s, setDefTalentStats)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>技能与参数</h2>
        <div className="grid three">
          <div className="field">
            <label>技能</label>
            <select value={skillName} onChange={(e) => setSkillName(e.target.value)}>
              {attackSkills.map((s) => {
                const name = String(s.技能名 ?? "");
                const category = String(s.类别 ?? "?");
                const power = String(s.威力 ?? "?");
                const attr = String(s.技能属性 ?? "?");
                return (
                  <option key={`skill-${name}`} value={name}>
                    {name} [{attr}/{category}] 威力:{power}
                  </option>
                );
              })}
            </select>
          </div>
          <div className="field">
            <label>我方攻击提升%</label>
            <input value={atkUpPct} onChange={(e) => setAtkUpPct(e.target.value)} />
          </div>
          <div className="field">
            <label>我方攻击降低%</label>
            <input value={atkDownPct} onChange={(e) => setAtkDownPct(e.target.value)} />
          </div>
          <div className="field">
            <label>敌方防御提升%</label>
            <input value={defUpPct} onChange={(e) => setDefUpPct(e.target.value)} />
          </div>
          <div className="field">
            <label>敌方防御降低%</label>
            <input value={defDownPct} onChange={(e) => setDefDownPct(e.target.value)} />
          </div>
          <div className="field">
            <label>威力加值</label>
            <input value={powerAdd} onChange={(e) => setPowerAdd(e.target.value)} />
          </div>
          <div className="field">
            <label>威力 Buff 乘数</label>
            <input value={powerBuff} onChange={(e) => setPowerBuff(e.target.value)} />
          </div>
          <div className="field">
            <label>特性威力加成%</label>
            <input value={traitPowerPct} onChange={(e) => setTraitPowerPct(e.target.value)} />
          </div>
          <div className="field">
            <label>减伤%</label>
            <input value={defReducePct} onChange={(e) => setDefReducePct(e.target.value)} />
          </div>
        </div>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={counterHit}
            onChange={(e) => setCounterHit(e.target.checked)}
          />
          应对成功
        </label>
        <button type="button" className="calcBtn" onClick={handleCalculate}>
          计算伤害
        </button>
      </section>

      {calcError ? <p className="error">{calcError}</p> : null}

      <section className="panel result">
        <h2>结果</h2>
        {result ? (
          <div className="resultGrid">
            <p className="big">{result.damage}</p>
            <p>伤害占比：{result.damagePct.toFixed(1)}%</p>
            <p>击倒回合：约 {result.koTurns} 回合</p>
            <p>
              攻防值：{result.attackerStatLabel} {result.attackerStat} / {result.defenderStatLabel}{" "}
              {result.defenderStat}
            </p>
            <p>
              双方生命：{result.attackerHp} / {result.defenderHp}
            </p>
            <p>
              速度：{result.attackerSpeed} vs {result.defenderSpeed}（{result.speedTag}）
            </p>
            <p>
              技能：{skillName} [{result.skillAttr}/{result.skillCategory}] 威力 {result.skillPower} →{" "}
              {result.effectivePower.toFixed(0)}
            </p>
            <p>
              乘区：克制×{result.typeMult.toFixed(2)} 本系×{result.stabMult.toFixed(2)} 天气×
              {result.weatherMult.toFixed(2)} 能力等级×{result.abilityLevel.toFixed(3)}
            </p>
            {result.counterNote ? <p>应对加成：{result.counterNote}</p> : null}
            {result.skillEffect ? <p>技能效果：{result.skillEffect}</p> : null}
          </div>
        ) : (
          <p className="placeholder">填写参数后点击“计算伤害”。</p>
        )}
      </section>
    </main>
  );
}
