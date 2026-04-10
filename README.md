# RocoDamageCalculator

洛克王国手游 PVP 伤害计算器，包含 Python 桌面版、核心计算逻辑，以及一个基于 Next.js 的 Web 版本。

这个仓库的目标不是只做一个界面，而是把公式、数据和展示层拆开：

- `damage_calc.py` 负责核心计算
- `damage_gui.py` 提供桌面版 GUI
- `web/` 提供 Web 版交互界面
- 爬虫脚本负责更新精灵和技能数据

## Features

- 按种族值、性格、天分档位计算竞技场属性
- 支持技能威力、属性克制、本系补正、天气、减伤、攻防增减益等伤害因子
- 内置部分应对技能的特殊威力修正逻辑
- 提供 Python Tkinter 桌面版
- 提供 Next.js Web 版
- 支持从 Wiki 抓取精灵图鉴与技能图鉴数据

## Quick Start

### Python 桌面版

建议环境：Python 3.10+

```bash
pip install -r requirements.txt
python damage_gui.py
```

注意：桌面版入口是 `damage_gui.py`，不是 `gui.py`。

### Web 版

建议环境：Node.js 18+

```bash
cd web
npm install
npm run dev
```

启动后默认访问：`http://localhost:3000`

## Repository Layout

```text
.
|-- damage_calc.py        # 核心伤害计算逻辑
|-- damage_gui.py         # Tkinter 桌面界面
|-- rocom_scraper.py      # 精灵图鉴爬虫
|-- skill_scraper.py      # 技能图鉴爬虫
|-- requirements.txt      # Python 依赖
|-- output/               # 采集后的数据文件
|-- web/                  # Next.js Web 版
```

## Data

当前项目主要使用以下数据文件：

- `output/精灵完整数据.json`
- `output/技能完整数据.json`
- `output/精灵基础数据.csv`
- `output/精灵技能组.csv`
- `output/技能数据.csv`

数据使用方式：

- Python 版直接读取 `output/` 下的数据
- Web 版通过 `web/scripts/sync-data.mjs` 同步数据到 `web/public/data/`

## Update Data

更新精灵图鉴：

```bash
python rocom_scraper.py
```

更新技能图鉴：

```bash
python skill_scraper.py
```

输出结果会写入 `output/` 目录。

## Web Build

构建静态站点：

```bash
cd web
npm run build
```

构建产物位于 `web/out/`，可以直接部署到静态托管平台。

## Formula Notes

项目目前实现的核心逻辑包括：

- 基于种族值、个体值档位和性格修正计算六维属性
- 基于攻击、防御、技能威力、属性克制、天气和减伤计算 PVP 伤害
- 对部分特殊技能增加应对成功后的倍率或加值修正

更详细的公式说明可直接查看 `damage_calc.py` 文件头部注释。

## Tech Stack

Python:

- `requests`
- `beautifulsoup4`
- `tkinter`（标准库）

Web:

- `next`
- `react`
- `typescript`

## Notes

- 爬虫依赖外部 Wiki 页面结构，如果页面改版，解析逻辑可能需要调整
- 部分公式和天气修正仍有待进一步验证，具体以代码注释为准
- 如果只使用桌面版，不需要安装 Node.js
- 如果只使用 Web 版，不需要安装 Python 依赖，但仓库中的数据文件必须存在

## Roadmap

- 增加命令行版本入口
- 为核心公式补充单元测试
- 支持更多技能特殊判定
- 自动化数据同步与发布流程