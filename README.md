<div align="center">

# RocoDamageCalculator

**洛克王国 PVP 伤害计算器**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

精确计算竞技场伤害 · 截图 OCR 自动识别 · 支持桌面版与 Web 版

</div>

---

## ✨ Features

| 功能 | 说明 |
|------|------|
| 伤害计算 | 按种族值、性格、天分档位计算竞技场六维属性与实际伤害 |
| 完整修正 | 技能威力、属性克制、本系补正、天气、减伤、攻防增减益 |
| 特殊技能 | 内置部分应对技能的威力修正逻辑（如特定反制倍率） |
| OCR 分析 | 对战截图自动识别我方 / 敌方精灵名与可用技能列表 |
| 图形启动器 | 一键启动所有工具，实时显示运行输出 |
| 数据爬取 | 从 Wiki 自动抓取精灵图鉴与技能图鉴，写入本地 `data/` |

---

## 🚀 Quick Start

### 桌面版（Python）

> 要求：Python 3.10+

```bash
git clone https://github.com/hEr0bR1ne/RocoDamageCalculator.git
cd RocoDamageCalculator
pip install -r requirements.txt
python launcher.py          # 图形化启动器（推荐）
python damage_gui.py        # 直接启动 GUI 计算器
```

### Web 版（Next.js）

> 要求：Node.js 18+

```bash
cd web
npm install
npm run dev
```

访问 `http://localhost:3000`

---

## 📁 Repository Layout

```text
RocoDamageCalculator/
├── damage_calc.py          # 核心伤害计算（→ roco/calculator.py）
├── damage_gui.py           # Tkinter 桌面 GUI
├── battle_analyzer.py      # 对战截图 OCR 分析器（→ roco/analyzer.py）
├── launcher.py             # 图形化工具启动器
├── rocom_scraper.py        # 精灵图鉴爬虫（→ roco/scraper/spirits.py）
├── skill_scraper.py        # 技能图鉴爬虫（→ roco/scraper/skills.py）
├── requirements.txt
├── data/                   # 本地数据文件（由爬虫生成）
│   ├── 精灵完整数据.json
│   ├── 技能完整数据.json
│   └── *.csv
├── roco/                   # 核心逻辑包
│   ├── constants.py        # 游戏常量（性格 / 属性 / 天气 / 应对表）
│   ├── data.py             # 数据加载
│   ├── stats.py            # 属性计算
│   ├── calculator.py       # 伤害计算 + 交互式 CLI
│   ├── analyzer.py         # 截图 OCR 分析
│   └── scraper/
│       ├── spirits.py      # 精灵 Wiki 爬虫
│       └── skills.py       # 技能 Wiki 爬虫
└── web/                    # Next.js Web 版
    ├── public/data/        # 前端静态数据
    └── scripts/
        └── sync-data.mjs   # 从 data/ 同步到 public/data/
```

---

## 📊 Data

数据文件位于 `data/`，由爬虫脚本生成：

```bash
python rocom_scraper.py   # 更新精灵图鉴
python skill_scraper.py   # 更新技能图鉴
```

| 文件 | 内容 |
|------|------|
| `精灵完整数据.json` | 所有精灵的种族值、属性、技能组等完整信息 |
| `技能完整数据.json` | 技能威力、属性、效果等完整信息 |
| `精灵基础数据.csv` | 精灵基础属性表格 |
| `精灵技能组.csv` | 精灵可学技能列表 |
| `技能数据.csv` | 技能数据表格 |

- Python 版直接读取 `data/` 下的 JSON 文件
- Web 版通过 `scripts/sync-data.mjs` 同步到 `web/public/data/`

---

## ⚙️ Tech Stack

**Python**

| 包 | 用途 |
|----|------|
| `requests` · `beautifulsoup4` | Wiki 数据爬取 |
| `rapidocr-onnxruntime` | 截图文字识别 |
| `Pillow` | 图像处理 |
| `tkinter` | 桌面 GUI（标准库） |

**Web**

| 包 | 用途 |
|----|------|
| `Next.js 15` · `React` | 前端框架 |
| `TypeScript` | 类型安全 |

---

## 📐 Formula Notes

核心伤害公式：

$$
\text{伤害} = \left\lfloor \frac{\text{攻击} \times \text{威力}}{\text{防御}} \times \text{属性克制} \times \text{本系补正} \times \text{天气} \times \text{减伤修正} \right\rfloor
$$

| 修正项 | 说明 |
|--------|------|
| 属性克制 | 由技能属性 vs 目标属性决定，最高 2.0×，最低 0.5× |
| 本系补正 | 技能属性与使用者属性相同时 ×1.5 |
| 天气 | 晴天 / 雨天等对特定属性技能 ×1.5 或 ×0.5 |
| 减伤修正 | 应对技能成功后的专属倍率或加值 |

详细实现见 [`roco/calculator.py`](roco/calculator.py)。

---

## 🗺️ Roadmap

- [x] 核心伤害计算公式
- [x] Tkinter 桌面 GUI
- [x] 爬虫自动更新数据
- [x] 对战截图 OCR 分析
- [x] 图形化工具启动器
- [x] Next.js Web 版
- [ ] 单元测试覆盖核心公式
- [ ] 支持更多特殊技能判断
- [ ] 自动化数据同步 CI / CD

### 🥧 未来计划

#### 📋 剪切板读取完善
- 更稳定的剪切板监听机制，支持截图软件直接触发分析
- 识别失败时的错误提示与手动纠错入口
- 识别结果缓存，避免同一张截图重复 OCR

#### ⚔️ 战局实时分析
- **伤害计算分析**：基于当前血量与伤害区间，自动判断当前回合是否能击倒对方
- **对方应对技能预测**：根据对方已知技能组与当前场面，列出对方最可能打出的技能及对己方的威胁程度
- **对方换场精灵分析**：根据对方已上场精灵和剩余阵容（若已侦测），评估对方换场概率及换场后的场面优劣

#### 📊 数据记录与数据集整理
- 对战结果自动记录（双方精灵、技能、输出伤害、胜负）
- 导出标准化 CSV / JSON 数据集，供后续训练或统计分析使用
- 历史战局回放与统计面板（胜率、常用精灵、克制关系热图）

#### 🧩 配队分析
- **队伍打击面分析**：基于队伍全员属性，计算对全属性类型的覆盖情况，标出薄弱打击面
- **队伍成员功能性分析**：识别队伍中各精灵承担的角色（先手、承受、输出、辅助、破盾等），检测角色重叠或缺失，给出配队优化建议

#### 📸 自动截图与录像
- **自动截图**：后台定时检测游戏窗口状态，战斗回合切换时自动触发截图，无需手动操作
- **自动录像**：对战全程帧序列录制，生成可回放的视频文件，方便赛后复盘与分享

---

## 📝 Notes

- 爬虫依赖 Wiki 页面结构，若页面改版解析逻辑需同步更新
- OCR 区域坐标基于 **2560×1440** 分辨率截图，其他分辨率需调整 `roco/analyzer.py` 中的 `REGION_2560`
- 仅使用桌面版不需要安装 Node.js；仅使用 Web 版不需要安装 Python 依赖，但 `data/` 中的 JSON 文件必须存在
