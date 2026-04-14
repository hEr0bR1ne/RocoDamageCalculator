# Agent Handoff — 2026-04-14

## 项目简介

**RocoDamageCalculator** — 洛克王国 PVP 伤害计算器 + 对战实时监控 GUI。
仓库：https://github.com/hEr0bR1ne/RocoDamageCalculator
语言：Python 3.13（主体）+ Next.js 15（Web 版）
Python 环境：`D:\Program Files\RocoDamageCalculator\.venv`

---

## 今日完成的工作（2026-04-14）

### 1. 帧分类器 + GameWatcher（`roco/capture.py`）

截图流三态分类：

```
skill_panel 区域 (150,380,470,500) std >= 25  →  'skill_select'   出招选择中
banner 区域 (1500,220,1780,248)  mean > 60    →  'skill_release'  招式释放动画
其他                                            →  'other'
```

- `classify_frame(img)` 用 numpy 灰度统计实现
- `GameWatcher.__init__` 新增 `on_release` 回调参数
- `_last_release_trigger` 冷却防重复触发
- `skill_release` 帧自动保存 `sample/_release_YYYYMMDD_HHMMSS.png`
- **待做**：`skill_release` 帧的后续分析逻辑（截图已保存，数据处理尚未实现）

### 2. 结构化伤害 API（`roco/analyzer.py`）

新增 `calc_quick_damage(self_name, enemy_name, analysis, skill_keys, db) -> list[dict]`，每项结构：

```python
{
  'num': 1,           # 技能序号
  'name': '十万伏特', # 技能名
  'score': 0.85,      # OCR 置信度
  'cat': '特殊',      # 物理/特殊/变化
  'power': 95,        # 技能威力
  'hits': 1,          # 连击数
  'reduce_pct': 0.0,  # 减伤倍率
  'dmg': 312,         # 估算伤害值
  'pct_hp': 18.4      # 占敌方 HP 百分比
}
```

`BattleAnalyzer._quick_damage()` 改为委托给它，向后兼容。

### 3. WatchWindow 实时监控 GUI（`launcher.py`）

进程内 `tk.Toplevel`，**不开子进程**。布局：

| 区块 | 内容 | 字号 |
|---|---|---|
| 顶栏 48px 紫色 `#2D1B69` | 标题 + 状态点 + ✕ 按钮 | 20 / 16 / 18 bold |
| 精灵行 | 己方 `#00FF88` / 敌方 `#FF4444` | 22 bold |
| 4 个技能卡 | 序号(20 bold) + 名称(14) + 类别/置信(14) | — |
| 伤害区 | 伤害数字(32 bold `#FF8C00`) + HP%(18 `#FFD700`) | — |
| 日志条 | 最近 50 行 | 14 |

**窗口几何**（2048×1152 分辨率标定）：

```python
_RX = 1525/2048   # 窗口左边 x 比例
_RW = 440/2048    # 宽比例
_RH = 870/1152    # 高比例
```

**关键方法**：
- `_load_db()` — 后台线程加载数据库
- `_start_watcher()` — 进程内启动 `GameWatcher`
- `_on_frame(img)` — 后台线程回调，`self.after(0, ...)` 转主线程
- `_update_ui(results, analysis)` — 更新 4 个技能卡
- `_poll_status()` — 1 秒轮询 watcher.status 更新状态点
- `_on_close()` — 停止 watcher，恢复启动卡片

置信度着色规则：绿 `#00FF88` ≥ 70% / 黄 `#FFD700` ≥ 40% / 红 `#FF4444` < 40%

### 4. PyInstaller 打包

```powershell
.\.venv\Scripts\pyinstaller.exe launcher.spec
# 输出：dist/RocoLauncher.exe（95 MB，单文件，含 RapidOCR 模型）
```

发行 zip（exe + data/，90.9 MB）：
```powershell
Compress-Archive -Path "dist\RocoLauncher.exe","data" -DestinationPath "dist\RocoDamageCalculator-v0.0.3-windows.zip" -Force
```

### 5. GitHub Release v0.0.3

- Tag：`v0.0.3`，分支：`main`，commit：`f711753`
- Release 页：https://github.com/hEr0bR1ne/RocoDamageCalculator/releases/tag/v0.0.3
- zip 下载：https://github.com/hEr0bR1ne/RocoDamageCalculator/releases/download/v0.0.3/RocoDamageCalculator-v0.0.3-windows.zip

---

## 当前 Git 状态

```
main 分支，最新 commit：f711753  docs: update README for v0.0.3
已推送到 origin/main
```

**本地有用户手动编辑、尚未提交的文件**（内容未知，请先 `git diff` 确认）：
- `launcher.py`
- `roco/calculator.py`

---

## 重要技术坑

### PowerShell 5 中文编码问题
凡是涉及中文内容写 GitHub API，**必须用 Python 脚本**，PowerShell 5 默认 GBK 会把 UTF-8 变乱码。

Python 获取 GitHub token 的正确方式：
```python
import subprocess
proc = subprocess.run(
    ['git', 'credential', 'fill'],
    input="protocol=https\nhost=github.com\n\n",
    capture_output=True, text=True, encoding='utf-8'
)
token = next((l[9:] for l in proc.stdout.splitlines() if l.startswith('password=')), None)
```

调用 API 时：
```python
import json, urllib.request
payload = json.dumps({'name': title, 'body': body}, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(url, data=payload, method='PATCH',
    headers={..., 'Content-Type': 'application/json; charset=utf-8'})
```

### 远程桌面分辨率
实际逻辑分辨率是 **2048×1152**，不是 1920×1080。`winfo_screenwidth()` 在远程桌面下不可靠，WatchWindow 改用硬编码比例常量。

### 截图工具
`mss` 替代 `BitBlt`，解决远程桌面截图全黑问题。见 `roco/capture.py`。

---

## 已知问题 / 下一步建议

| 优先级 | 任务 | 位置 |
|---|---|---|
| 高 | `skill_release` 帧的后续处理（OCR+伤害记录） | `roco/capture.py` `_loop()` |
| 中 | WatchWindow 多分辨率适配（当前仅 2048×1152 标定） | `launcher.py` `_set_geometry()` |
| 中 | 确认并提交用户本地未提交的编辑 | `launcher.py`、`roco/calculator.py` |
| 低 | 对方精灵手动修正输入框 | `launcher.py` WatchWindow |
| 低 | HP 血条进度条可视化 | `launcher.py` WatchWindow |

---

## 常用命令速查

```powershell
# 激活环境
& "d:\Program Files\RocoDamageCalculator\.venv\Scripts\Activate.ps1"

# 运行启动器
python launcher.py

# 重新打包 exe
.\.venv\Scripts\pyinstaller.exe launcher.spec

# 查看未提交改动
git diff

# 推送
git push
```
