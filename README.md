## 番茄钟托盘应用（Pomodoro Tray Timer）

一个**跨平台（macOS / Windows）系统托盘常驻**的番茄钟小工具：通过**动态绘制托盘图标**显示剩余分钟数，阶段结束时用**系统原生通知**提醒，并将历史记录持久化到本地 CSV。

支持 **6 种语言**运行时切换（中文、英文、日文、俄文、法文、德文）。

> 🍅 由 **[嗨AI助手](https://hiaipal.com)** 出品 — 你最真诚的 AI 伙伴。关注微信公众号，获取更多实用工具动态。

---

## 整体架构

```
main.py (入口)
  └─ app.py (应用主控制器 — 组件装配 + 信号/槽连接)
       ├─ TimerEngine     — 计时引擎（核心状态机）
       ├─ TrayController  — 系统托盘图标 + 右键菜单
       ├─ Notifier        — 系统原生通知（支持 macOS/Windows）
       ├─ SettingsWindow  — 设置对话框（含语言切换）
       ├─ HistoryWindow   — 历史记录窗口（明细 + 按天统计）
       ├─ CsvStorage      — CSV 文件持久化
       └─ AppConfig       — 配置 JSON 持久化
```

核心设计：**Qt 信号/槽**驱动。`TimerEngine` 发射 `tick` / `phase_changed` / `phase_finished` / `paused_changed` / `stopped` / `language_changed` 信号，UI 层（TrayController、SettingsWindow、HistoryWindow）订阅这些信号做出响应，完全解耦。

---

## 功能说明

### 系统托盘常驻

- **托盘图标动态绘制**：用 `QPainter` 画番茄造型 + 剩余分钟数字。不是静态 `.ico/.png` 资源。
- **颜色区分阶段**：
  - 空闲/待开始：**橙色** `#FFA631`
  - 专注阶段：**红色** `#D7263D`
  - 休息阶段（短休/长休）：**绿色** `#2E8B57`
- **叶子**：绿色 `#00BC12`
- **暂停标记**：暂停时番茄右上角显示半透明黑色圆角矩形 + 两条白色竖杠
- **鼠标悬停提示**：显示当前阶段、剩余分钟、下一阶段建议
- **左键单击托盘图标**：
  - 运行中（倒计时在走）→ **暂停**
  - 已暂停 → **继续**
  - 空闲 + 有 pending → **开始 pending 阶段**（例如恢复被终止的休息）
  - 空闲 + 无 pending → **开始专注**
- **阶段结束后**：应用进入空闲/待开始，**不会自动开始下一阶段**

### 右键菜单

| 菜单项             | 说明                                                          |
| ------------------ | ------------------------------------------------------------- |
| 暂停 / 继续        | 文案随状态动态切换                                            |
| 终止时钟           | 运行中可用；在休息中终止后 pending 保留该休息，下次左键会重开 |
| 开始集中精力       | —                                                            |
| 开始短暂休息       | —                                                            |
| 开始长时间休息     | —                                                            |
| 重新开始番茄钟循环 | 重置周期计数器                                                |
| 打开历史记录       | —                                                            |
| 设置...            | —                                                            |
| 退出               | —                                                            |

### macOS 特别说明

- **默认不显示 Dock 图标**：使用 `NSApplicationActivationPolicyAccessory`（纯菜单栏应用）。
  - 如需显示 Dock 图标，设置环境变量 `POMODORO_MACOS_SHOW_DOCK_ICON=true`。
- **右键菜单**：macOS 上不绑定 `setContextMenu`（否则任意点击都会弹菜单），而是在接收到 `ActivationReason.Context` 时通过 AppKit 的 `activateIgnoringOtherApps_` 激活进程后手动 `menu.exec()`，确保全屏 Space 下稳定显示。

### 系统通知

- **Windows**：通过 `winotify` 库发送 Windows Toast 通知，跟随系统提示音。
- **macOS**：
  1. 优先尝试 `terminal-notifier`（如已安装）
  2. 回退到 `osascript display notification`（系统自带，无需额外依赖）
  3. 通知成功后追加 **Qt Toast**（右上角半透明浮动窗口，4.5 秒自消）+ **托盘气泡**
- **失败回退**：若以上均失败，回退到 `QSystemTrayIcon.showMessage()` 气泡提示。

### 通知内容

阶段结束时通知内容按阶段区分：

| 阶段         | 标题                      |
| ------------ | ------------------------- |
| 专注结束     | "第{n}/{total}次集中精力" |
| 短暂休息结束 | "短暂休息结束"            |
| 长休息结束   | "长休息结束"              |

每则通知同时提示下一阶段建议（"下一阶段：集中精力" / "短暂休息" / "长时间休息"）。

---

## 计时引擎（TimerEngine）— 核心状态机

### Phase 枚举

- `idle` — 空闲
- `focus` — 专注
- `short_break` — 短暂休息
- `long_break` — 长休息

### 关键数据结构

- **TimerConfig**：可配置参数（focus/short_break/long_break 分钟数、long_break_every_focus）
- **PhaseRun**：当前阶段快照（阶段名、总秒数、剩余秒数、开始时间）
- **PhaseFinished**：阶段结束事件（计划分钟、实际秒数、专注编号 focus_index）

### 状态转换

```
idle --[start_focus]--> focus --[倒计时结束]--> idle (pending = 下一个建议阶段)
idle --[start_short_break]--> short_break
idle --[start_long_break]--> long_break
focus/short_break/long_break --[pause]--> 暂停 (timer 停止, paused=True)
focus/short_break/long_break --[stop]--> idle
  - 如果在休息中停止：pending = 该休息（下次左键可恢复）
  - 如果在专注中停止：pending = None
```

### 下一阶段建议规则 (`_suggest_next`)

- 专注结束 → 若 `focus_completed_in_cycle % long_break_every_focus == 0` → 长休息，否则 → 短休息
- 休息结束 → 专注
- 长休息结束后 `focus_completed_in_cycle` 归零（新周期开始）

### 运行时热更新

`update_config()` 可以在倒计时进行中修改时长参数，已用时间保留不变。

---

## 国际化（i18n）

- **Translator 单例**：从 `pomodoro_app/i18n/{lang}.json` 加载翻译
- `_('key')` 为全局翻译函数
- **运行时切换**：`switch_language(lang)` 无需重启，所有 UI 文本即时刷新
- **未翻译回退**：key 在翻译文件中不存在时返回原 key

### 支持语言

| 代码   | 语言 |
| ------ | ---- |
| `zh` | 中文 |
| `en` | 英文 |
| `ja` | 日文 |
| `ru` | 俄文 |
| `fr` | 法文 |
| `de` | 德文 |

---

## 配置（config.json）

### 字段

```json
{
  "focus_minutes": 25,
  "short_break_minutes": 5,
  "long_break_minutes": 15,
  "long_break_every_focus": 4,
  "language": "zh"
}
```

| 字段                       | 类型           | 说明                          |
| -------------------------- | -------------- | ----------------------------- |
| `focus_minutes`          | 正整数         | 专注分钟数                    |
| `short_break_minutes`    | 正整数         | 短暂休息分钟数                |
| `long_break_minutes`     | 正整数         | 长休息分钟数                  |
| `long_break_every_focus` | 正整数         | 每完成 n 次专注触发一次长休息 |
| `language`               | 2 字符语言代码 | 界面语言，默认`"zh"`        |

- 配置文件不存在或格式无效时回退默认值（25/5/15/4/zh）
- 保存前会校验所有字段，避免写入坏数据

---

## 历史记录（CSV）

### 表头

`日期, 集中精力, 短暂休息, 长休息, 开始时间, 结束时间`

### 字段含义

- 每行记录一个完整阶段，仅对应阶段的列写入计划分钟数（整数），其他两列为空
- 时间格式：`YYYY-MM-DD HH:MM:SS`

### 历史记录窗口

- 两个标签页：**记录明细**（逐行展示）+ **每日统计**（按天聚合：专注次数 + 专注总分钟）
- 支持日期范围筛选

---

## 运行时数据目录

### 数据目录策略

| 平台              | 默认数据目录                                                                       |
| ----------------- | ---------------------------------------------------------------------------------- |
| **macOS**   | `~/Library/Application Support/pomodoro-tray-timer/`                             |
| **Windows** | `%APPDATA%\pomodoro-tray-timer\`                                                 |
| **Linux**   | `$XDG_DATA_HOME/pomodoro-tray-timer/` 或 `~/.local/share/pomodoro-tray-timer/` |

- 可通过 `settings.ini` 中的 `[app]` → `DataDir` 自定义数据目录（所有平台均支持）
- 程序启动时自动做**一次性旧数据迁移**：将 `data/` 目录（旧版本）中的 `config.json` / `history.csv` 迁移到新位置

---

## 运行方式

### 环境要求

- **macOS** / **Windows 10/11** / **Linux**
- Python **3.12+**
- 依赖由 `uv` 管理

### 安装与启动

```bash
uv sync
uv run python main.py
```

启动后应用常驻系统托盘，无主窗口。

---

## 测试

```bash
uv run pytest
```

测试文件：

| 文件                           | 测试内容                              |
| ------------------------------ | ------------------------------------- |
| `tests/test_i18n.py`         | Translator 单例、语言切换、未翻译回退 |
| `tests/test_tray_i18n.py`    | 托盘菜单语言切换后文字正确性          |
| `tests/test_history_i18n.py` | 历史窗口语言切换（含往返切换）        |

---

## 打包与发布

### macOS（Nuitka + DMG）

```bash
./scripts/build-macos.sh
```

CI 工作流：`.github/workflows/release-macos.yml`（`v*` tag 触发）

### Windows（Nuitka + Inno Setup）

```powershell
.\scripts\build-windows.ps1
.\scripts\build-installer.ps1
```

CI 工作流：`.github/workflows/release-windows.yml`（`v*` tag 触发）

### 分平台 lock 文件

项目维护分平台 `uv.lock`：

- `uv.lock.macos`
- `uv.lock.windows`

CI 按平台自动选择对应 lock 进行 `uv sync --all-groups`。

---

## 项目结构

- `main.py` — 启动入口
- `pomodoro_app/` — 核心代码
  - `app.py` — 应用装配器（信号/槽连接）
  - `timer_engine.py` — 计时引擎（状态机）
  - `tray.py` — 托盘图标 + 右键菜单
  - `notifications.py` — 系统通知
  - `config_store.py` — 配置管理
  - `storage_csv.py` — CSV 持久化
  - `paths.py` — 跨平台路径
  - `models.py` — 数据模型
  - `settings_window.py` — 设置窗口
  - `history_window.py` — 历史记录窗口
  - `i18n/` — 翻译文件（6 语言）
- `scripts/` — 构建脚本
- `installer/` — Inno Setup 安装器脚本
- `assets/` — 静态图标资源
- `tests/` — 单元测试

---

## 关于嗨AI助手

「**[嗨AI助手](https://github.com/lixianglong1205/)**」是作者维护的个人 IP，真实记录 AI 打磨产品全过程，分享最实用工具动态。你出点子，我来开发，上线就送！

### 关注微信公众号

扫码关注「嗨AI助手」微信公众号，获取更多实用工具动态和免费额度：

<p align="center">
  <picture>
    <source srcset="assets/wechat-channels-qrcode.7c110a33.webp" type="image/webp" />
    <img src="assets/wechat-channels-qrcode.aafdf212.jpg" alt="嗨AI助手微信公众号二维码" width="220" height="220" />
  </picture>
</p>

### 支持作者

如果这个番茄钟工具帮你提升了效率，欢迎请作者喝杯咖啡 ☕️ 你的支持是持续维护和开发新功能的最大动力！

<p align="center">
  <img src="assets/wechat-reward.jpg" alt="微信赞赏码" width="220" height="220" />
</p>

> 🌐 官网：[https://hiaipal.com](https://hiaipal.com)
