# macOS 排障：菜单栏不显示番茄钟图标（但进程在运行）

## 现象

- 执行 `make run`（等价于 `uv run python main.py`）后，终端里看起来“服务/进程已启动”，但 **菜单栏（menu bar）** 里没有番茄钟图标。
- 同样代码在 Windows 上运行时，任务栏托盘图标能正常出现。

## 根因（一个容易忽略的系统设置）

本项目在开发态是以 **`python3.12` 进程**运行的。macOS 会对“某个应用/进程的菜单栏图标”做显示/隐藏管理。

如果你在 **系统设置**里把 `python3.12` 的菜单栏显示关掉了，那么：

- 程序仍然会运行（Qt 事件循环也可能在跑）
- 但对应的菜单栏图标会被系统隐藏，于是你看不到番茄钟图标

## 解决方法

到 macOS 的系统设置里把 `python3.12` 的菜单栏显示重新打开：

- **系统设置 → 控制中心（Control Center） → 菜单栏（Menu Bar）相关设置**
- 找到 `python3.12`（或你实际运行时的 Python 进程名），把它设置为“在菜单栏显示”

> 不同 macOS 版本菜单项名称略有差异，但关键点是：**允许 `python3.12` 在菜单栏显示其图标**。

## 备注

- 若你运行后在终端看到类似“系统托盘（菜单栏图标）不可用”的提示，那属于另一类问题（通常是非图形桌面会话、或系统托盘不可用），可先对照 `pomodoro_app/app.py` 中的 `_report_tray_unavailable()` 提示排查。

## 排障：设置窗口无法弹出 / 左右键菜单行为（含全屏应用）

### 现象

- 点击菜单栏图标菜单中的 **“设置...”** 没有弹出窗口（或窗口一闪而过）。
- 期望行为：**左键** 触发默认动作（开始/暂停），**右键** 才弹出菜单。
- 实际异常：
  - macOS 上左键/右键都会弹出菜单（无法区分）
  - 或者在 **全屏应用 / 不同 Space** 下，右键触发了但 **菜单不出现**

### 根因

- **设置窗口无法弹出**：在 `pomodoro_app/app.py` 中，`on_open_settings()` 若用局部变量创建 `SettingsWindow`，函数返回后对象可能被回收，导致窗口无法稳定显示。
- **左右键无法区分**：macOS 上如果对 `QSystemTrayIcon` 使用 `setContextMenu()` 绑定原生菜单，系统会把菜单绑定到状态栏图标，导致“任意点击”都弹出菜单，Qt 层无法区分左右键。
- **全屏下右键菜单不出现**：macOS 的菜单栏处于更高层级/独立空间，直接用 Qt 的 `QMenu.popup()` 往往会被系统吞掉（看起来像“触发了但没显示”）。

### 修复方式（代码层面）

- `pomodoro_app/app.py`
  - 将 `SettingsWindow` 持有为长期引用（例如 `settings: SettingsWindow | None`），重复打开时复用同一个实例。
  - macOS 上建议默认使用 **Accessory** activation policy（不显示 Dock 图标），更符合托盘应用形态，也便于后续“静默激活”弹出菜单。
    - 需要显示 Dock 图标时可设置：`POMODORO_MACOS_SHOW_DOCK_ICON=1`
- `pomodoro_app/tray.py`
  - macOS 上不调用 `setContextMenu()` 绑定菜单（否则左键也会弹菜单，无法区分）。
  - 在 `activated` 回调中用 `reason` 区分：
    - 右键（`ActivationReason.Context`）：走 `v0.2.11` 同款方案，先用 AppKit `activateIgnoringOtherApps_` 静默激活，再 `QMenu.exec(QCursor.pos())` 弹出菜单，保证在 **全屏/不同 Space** 下也能显示且不“闪桌面”。
    - 左键（`ActivationReason.Trigger/DoubleClick`）：只执行默认动作（开始/暂停），不弹菜单。

