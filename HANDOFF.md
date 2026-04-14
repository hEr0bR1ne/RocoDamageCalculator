# RocoDamageCalculator — 交接文档

> 更新：2026-04-15

---

## 项目背景

洛克王国对战伤害计算器。核心流程：

```
自动截图游戏画面
  → classify_frame 识别战斗阶段
  → PaddleOCR 识别精灵名 / 技能名 / 威力 / 血量
  → 查精灵数据库计算伤害
  → 结果输出到悬浮监控窗 WatchWindow
```

---

## 已完成功能

| 模块 | 状态 | 说明 |
|---|---|---|
| Launcher GUI | ✅ | 工具卡片入口，子进程管理 |
| WatchWindow | ✅ | 悬浮监控窗，字体缩放，位置/尺寸持久化 |
| GeometryCalibrator | ✅ | 半透明拖拽校准 WatchWindow 位置 |
| 伤害计算公式 | ✅ | `roco/calculator.py` |
| 精灵/技能数据库 | ✅ | `data/精灵完整数据.json`，爬虫在 `roco/scraper/` |
| classify_frame | ✅ | 按比例识别出招/释放/其他阶段，适配任意分辨率 |
| REGIONS_RATIO | ✅ | 按 **1920×1080** 标定，`scale_regions(w,h)` 乘以实际尺寸 |
| 敌方 HP% OCR | ✅ | `enemy_hp` 区域，WatchWindow 带颜色显示 |
| `get_window_rect()` | ✅ | `win32gui.ClientToScreen + GetClientRect`，正确排除标题栏/边框 |
| 游戏窗口标定按钮 | ✅ | WatchWindow 内「🎯 标定游戏窗口」，保存到 `data/game_window_rect.json` |

---

## 当前截图方案及核心问题

### 现有实现

**文件**：`roco/capture.py`

```python
def grab_window(hwnd):
    cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
    l, t, r, b = win32gui.GetClientRect(hwnd)
    return grab_screen_region({"left": cx, "top": cy, "width": r-l, "height": b-t})

def grab_screen_region(region):
    with mss.mss() as sct:
        raw = sct.grab(region)
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
```

### 问题

`mss` 是**屏幕截图**，截的是该坐标区域当前显示的内容。  
游戏被其他窗口遮挡时，截到的是遮挡窗口，不是游戏画面。

验证（已跑）：

```
grab_window 与 grab_screen_region 像素差 = 0.00
```

两者完全相同，证明底层都走同一个 mss 坐标截图，并非从进程帧缓冲读取。

### 正确方案

用 `PrintWindow(hwnd, hdc, PW_CLIENTONLY)` 直接从进程 DC 读帧缓冲，不依赖窗口可见性。

**方案 A — win32ui + win32con（纯 pywin32，无额外依赖）**

```python
import win32gui, win32ui
from PIL import Image

def grab_window_dc(hwnd: int) -> Image.Image:
    l, t, r, b = win32gui.GetClientRect(hwnd)
    w, h = r - l, b - t

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc  = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bmp     = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc_dc, w, h)
    save_dc.SelectObject(bmp)

    # PW_CLIENTONLY = 1，只截客户区，不含标题栏
    win32gui.PrintWindow(hwnd, save_dc.GetSafeHdc(), 1)

    bmp_info = bmp.GetInfo()
    raw = bmp.GetBitmapBits(True)
    img = Image.frombuffer("RGB", (bmp_info["bmWidth"], bmp_info["bmHeight"]),
                           raw, "raw", "BGRX", 0, 1)

    win32gui.DeleteObject(bmp.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)
    return img
```

**方案 B — dxcam（DXGI Desktop Duplication，帧率更高）**

```python
import dxcam
camera = dxcam.create()
frame = camera.grab()  # numpy array，全屏
```

> 注意：`dxcam` 对最小化窗口同样无效，但被遮挡时可正常工作。

---

## 待解决任务

1. **截图方案替换**  
   将 `grab_window` 改为基于 `PrintWindow` 的 `grab_window_dc`，测试被遮挡时能否正确截图。

2. **OCR 链路验证**  
   游戏设为 1920×1080 窗口化，跑完整 OCR 流程，确认 `REGIONS_RATIO` 坐标正确。

3. **标定流程收尾**  
   `_calibrate()` 已接入 WatchWindow（`launcher.py`），截图方案修好后可端到端测试。

---

## 环境

- Python 3.13，venv 在 `.venv/`
- 关键依赖：`pillow`, `mss`, `pywin32`, `paddleocr`, `numpy`, `opencv-python`
- 完整依赖见 `requirements.txt`

## Git 分支

| 分支 | 说明 |
|---|---|
| `main` | 最新稳定，含所有 GUI 修复 + 标定按钮 |
| `feature/multi-resolution` | 已 merge 进 main |
