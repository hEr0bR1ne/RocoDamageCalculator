# Web 版说明

该目录是基于 React + Next.js 的网页版本，实现了：

- 纯静态站点（`next.config.mjs` 中 `output: "export"`）
- 浏览器直接拉取 `public/data/精灵完整数据.json`
- 迁移 `damage_calc.py` 的核心 PVP 伤害公式
- 提供攻击方/防御方参数输入和结果展示 UI

## 本地运行

```bash
cd web
npm install
npm run dev
```

默认地址：`http://localhost:3000`

## 构建静态文件

```bash
cd web
npm run build
```

构建产物在 `web/out/`，可直接部署到静态托管平台。

## 关键文件

- `app/page.tsx`：前端页面与交互
- `lib/calc.ts`：计算逻辑（公式、性格、克制、天气、应对加成）
- `public/data/精灵完整数据.json`：前端直接拉取的数据文件
- `scripts/sync-data.mjs`：从 `../output/精灵完整数据.json` 同步数据到 `public/data`
