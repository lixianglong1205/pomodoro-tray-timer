## Windows10 番茄钟托盘应用（Pomodoro Tray）

一个 **Windows 系统托盘（notification area）常驻** 的番茄钟小工具：通过 **动态绘制托盘图标** 显示剩余分钟数，阶段结束时用 **Windows Toast** 提醒，并将历史记录持久化到本地 CSV。

## 功能说明

- **系统托盘常驻**
  - 专注/休息阶段通过托盘图标展示剩余 **分钟**（每分钟刷新一次）
  - 专注阶段图标偏红色，休息阶段图标偏绿色（便于一眼区分）
  - 鼠标悬停托盘图标显示当前阶段与剩余时间等提示信息
  - 阶段结束后应用会进入 **空闲/待开始**，不会自动进入并开始下一阶段
  - 空闲/待开始时，托盘提示信息会显示“下一阶段”（建议的下一阶段）
  - **左键单击托盘图标**：
    - 运行中（倒计时在走）→ **暂停**
    - 已暂停 → **继续**
    - 空闲/待开始：若存在“下一阶段”提示 → **开始下一阶段**；否则 → **开始集中精力**
- **右键菜单快捷操作**
  - 暂停 / 继续（文案随状态动态切换）
  - 终止时钟
  - 开始集中精力
  - 开始短暂休息
  - 开始长时间休息
  - 重新开始番茄钟循环
  - 设置...
  - 打开历史记录
  - 退出
- **系统通知**
  - 阶段结束（专注/短休/长休）触发 Windows Toast 通知
  - Toast 通知会尝试**跟随系统提示音**播放结束音效（依赖 Windows 通知设置，见下文“通知音效说明/FAQ”）
  - 若 Toast 发送失败，会尽力回退到 Qt 的气泡提示（取决于系统环境）
- **历史记录（CSV）**
  - 每完成一个阶段写入一行记录（专注/短休/长休）
  - 支持在“历史记录”窗口查看明细与按天汇总（如每日专注次数/专注总分钟）

## 时长设置（UI）

你可以在应用内直接修改三个阶段的默认分钟数（集中精力 / 短暂休息 / 长休息）。

### 入口

- **右键托盘图标** → 选择 **设置...**

### 可配置项

- **集中精力分钟数**
- **短暂休息分钟数**
- **长休息分钟数**

保存后会**立即生效**（下一次开始/切换阶段将使用新时长）。配置会持久化到本地 JSON 文件，下次启动自动加载。

## 运行方式（uv）

### 环境要求

- **Windows 10/11**
- Python **3.12+**（见 `pyproject.toml` 的 `requires-python`）
- 依赖由 `uv` 管理（项目已包含 `uv.lock`）

### 安装依赖

在项目根目录执行：

```bash
uv sync
```

### 启动应用

```bash
uv run python main.py
```

启动后不会出现主窗口，应用会常驻系统托盘。通过托盘图标右键菜单进行操作。
另外，阶段结束后会进入空闲/待开始：

- **左键单击托盘图标**：优先开始“下一阶段”（若有提示）；否则开始“集中精力”
- **运行中/暂停中左键单击**：可在“暂停 / 继续”之间切换（暂停时倒计时停止）

## 运行时数据目录（重要）

为避免安装到 `C:\Program Files\...` 后因“程序目录不可写”导致配置/历史写入失败，本项目从较新版本起将**运行时数据**默认写入用户目录：

- **基础目录（应用根目录）**：`%APPDATA%\pomodoro-tray-timer\`
- **数据目录（最终写入位置）**：
  - **默认**：若不存在 `settings.ini`，数据目录就是上面的“基础目录”
  - **安装包版本（可配置）**：若存在 `%APPDATA%\pomodoro-tray-timer\settings.ini`，则读取：
    - `[app]`
    - `DataDir=C:\...\somewhere`
    - 程序会把 `config.json` / `history.csv` 写入该 `DataDir`

因此你实际会看到下面两种常见位置之一：

- **未安装/便携运行（默认）**：
  - `%APPDATA%\pomodoro-tray-timer\config.json`
  - `%APPDATA%\pomodoro-tray-timer\history.csv`
- **通过安装器安装（默认 DataDir 为 data 子目录）**：
  - `%APPDATA%\pomodoro-tray-timer\data\config.json`
  - `%APPDATA%\pomodoro-tray-timer\data\history.csv`

### 兼容旧版本（一次性迁移）

如果你以前用过旧版本（数据在项目相对目录 `data/` 下），程序会在首次启动/首次写入时尝试把下面文件迁移到 `%APPDATA%`：

- 若你没有通过安装器配置 `DataDir`：迁移到 `%APPDATA%\pomodoro-tray-timer\`
- 若你通过安装器配置了 `DataDir`：迁移到 `DataDir\`（例如默认的 `%APPDATA%\pomodoro-tray-timer\data\`）

## 数据与 CSV 格式定义

### 默认数据位置

- **CSV 路径**：默认写入 `%APPDATA%\pomodoro-tray-timer\history.csv`；若安装器设置了 `DataDir`，则写入 `DataDir\history.csv`
- 如果文件不存在，会在首次写入时自动创建，并写入表头。

## 配置文件（config.json）

### 默认位置

- **配置路径**：默认写入 `%APPDATA%\pomodoro-tray-timer\config.json`；若安装器设置了 `DataDir`，则写入 `DataDir\config.json`
- 若文件不存在或内容格式不正确：会回退为默认值（25/5/15）。

### 字段定义

```json
{
  "focus_minutes": 25,
  "short_break_minutes": 5,
  "long_break_minutes": 15
}
```

- **focus_minutes**：集中精力分钟数（正整数）
- **short_break_minutes**：短暂休息分钟数（正整数）
- **long_break_minutes**：长休息分钟数（正整数）

你也可以在应用退出时手动编辑该文件，但请确保三项都是**正整数**，否则会被当作无效配置并回退默认值。

## Windows 打包与安装（Nuitka + Inno Setup）

本项目提供了可直接运行的构建脚本：

- **打包 one-dir（可运行目录）**：输出到 `dist\pomodoro-tray-timer\`
- **生成安装器**：输出到 `dist-installer\pomodoro-tray-timer-setup.exe`

### 通过打 tag 自动构建并发布安装包（GitHub Actions）

当你推送形如 `v*` 的 tag（例如 `v0.1.0`）到远端后，GitHub Actions 会在 Windows runner 上自动完成：

- 构建 one-dir：`dist/pomodoro-tray-timer/**`
- 构建安装包：`dist-installer/pomodoro-tray-timer-setup.exe`
- 自动创建/更新同名 tag 的 GitHub Release，并上传安装包资产：
  - 资产名：`pomodoro-tray-timer-setup-<tag>.exe`（例如 `pomodoro-tray-timer-setup-v0.1.0.exe`）

触发工作流文件：`.github/workflows/release-windows.yml`（`on: push: tags: ["v*"]`）。

#### CI 产物在哪里（Actions / Releases）

- **Actions 的构建产物（Artifacts）**：
  - 在 GitHub 仓库页面进入 **Actions** → 打开对应 tag 的 workflow run
  - 你会看到上传的构建产物（artifact），其中包含：
    - `dist/pomodoro-tray-timer/**`（one-dir 可运行目录）
    - `dist-installer/pomodoro-tray-timer-setup.exe`（安装器 exe，未改名的原始产物）
- **最终对外发布的安装器（Releases）**：
  - workflow 会创建/更新同名 tag 的 GitHub Release，并上传重命名后的资产：
    - `pomodoro-tray-timer-setup-<tag>.exe`

#### CI 里 Inno Setup 是怎么用的（ISCC / .iss）

- **Inno Setup 脚本**：`installer/pomodoro-tray-timer.iss`
- **编译方式**：CI 会安装 Inno Setup，并使用其命令行编译器 **ISCC.exe** 编译 `.iss` 生成安装器
- **关键输入/输出路径约定**：
  - `.iss` 会引用 one-dir 产物目录 `dist/pomodoro-tray-timer/`（因此 **必须先成功打包**，再编译安装器）
  - 编译输出默认写到 `dist-installer/` 下

#### CI 常见失败点（快速自查）

- **找不到 `installer/pomodoro-tray-timer.iss`**：说明仓库内容/路径不匹配（检查是否改名或移动）
- **找不到 `dist/pomodoro-tray-timer/`**：说明 Nuitka 打包没产出 one-dir（先看前面的 build step 日志）
- **ISCC 诊断命令返回非 0**：
  - 在某些环境里执行 `ISCC /?` 可能返回非 0（即使只是输出帮助/诊断信息）
  - 如果你在 workflow 里增加了类似“ISCC diagnostics”的步骤，请确保该诊断步骤不会因为退出码导致整个 job 失败（详见 `.github/workflows/release-windows.yml`）

#### 如何发布（打 tag 并触发 CI）

在仓库根目录执行：

```bash
git tag v0.1.0
git push origin v0.1.0
```

或一次性推送全部本地 tag：

```bash
git push --tags
```

#### 去哪里下载安装包

构建完成后，到 GitHub 仓库的 **Releases** 页面下载对应版本的安装包资产（文件名形如 `pomodoro-tray-timer-setup-v0.1.0.exe`）。

### 环境要求（打包机）

- **Windows 10/11**
- **Python 3.12+**
- **uv**（用于安装/锁定依赖与运行构建）
- **C/C++ 编译环境（用于 Nuitka）**
  - 推荐安装 **Visual Studio Build Tools 2022**，勾选 “Desktop development with C++”
- （可选但推荐）**干净的打包环境**：尽量在无中文路径/权限限制较少的目录中构建，减少 Qt 依赖/杀软误报带来的干扰

### 1) 打包 exe（one-dir）

在项目根目录执行（PowerShell）：

```powershell
.\scripts\build-windows.ps1
```

默认会执行：

- `uv sync --all-groups` 安装/同步依赖（包含 `dev` 组里的 Nuitka）
- `uv run python -m nuitka ... main.py` 生成 one-dir

你也可以指定输出目录或 exe 名称（可选）：

```powershell
.\scripts\build-windows.ps1 -OutputDir dist -AppName pomodoro-tray-timer
```

产物目录示例：

- `dist\pomodoro-tray-timer\pomodoro-tray-timer.exe`
- 同目录下包含 Qt/依赖 DLL、平台插件等运行时文件

### 2) 生成安装包（Inno Setup）

先安装 **Inno Setup 6**，确保编译器 `ISCC.exe` 可用（脚本会自动在常见安装路径里查找，也支持把 `ISCC.exe` 加入 `PATH`）。

然后在项目根目录执行：

```powershell
.\scripts\build-installer.ps1
```

默认会编译 `installer\pomodoro-tray-timer.iss`，并生成：

- `dist-installer\pomodoro-tray-timer-setup.exe`

#### 本地从零构建（推荐顺序）

如果你希望在本机从依赖安装开始完整构建一遍（便于排查环境问题），建议按下面顺序：

```powershell
uv sync --all-groups
.\scripts\build-windows.ps1
.\scripts\build-installer.ps1
```

#### 安装器会做什么（数据目录/快捷方式）

- **安装程序文件**：把 `dist\pomodoro-tray-timer\` 目录下的内容递归安装到 `{app}`（默认 `C:\Program Files\pomodoro-tray-timer\`）
- **创建快捷方式**：
  - 开始菜单：默认创建
  - 桌面：可选（安装向导里勾选“创建桌面快捷方式”）
- **引导选择“数据保存目录”**（关键）：
  - 安装向导会让你选择 `config.json` / `history.csv` 的保存位置（默认：`%APPDATA%\pomodoro-tray-timer\data`）
  - 选择结果会写入：`%APPDATA%\pomodoro-tray-timer\settings.ini`
  - 程序启动时会读取该 `settings.ini` 的 `DataDir`，并把数据写到你选择的位置

### 常见坑与排查

#### 1) “运行后无法保存配置/历史”或安装后异常

原因通常是把数据写进了不可写目录。请确认你的数据文件位于：

- 未安装/便携运行（默认）：
  - `%APPDATA%\pomodoro-tray-timer\config.json`
  - `%APPDATA%\pomodoro-tray-timer\history.csv`
- 通过安装器安装（默认 DataDir）：
  - `%APPDATA%\pomodoro-tray-timer\data\config.json`
  - `%APPDATA%\pomodoro-tray-timer\data\history.csv`
- 或你在安装向导里选择的 `DataDir` 目录下

如果你之前的旧数据还在项目目录 `data/` 下，程序会尝试自动迁移；若迁移失败，可以手动把文件复制过去。

#### 2) Nuitka 打包失败：找不到编译器/链接器

现象常见为提示缺少 `cl.exe`、`link.exe` 或编译工具链。

- 请安装 **Visual Studio Build Tools 2022**，并确保勾选了 C++ 桌面开发组件
- 安装后重新打开终端再运行 `.\scripts\build-windows.ps1`

#### 3) 运行时报 Qt 平台插件错误（如 “Could not load the Qt platform plugin 'windows'”）

这通常是 Qt 插件/依赖未被正确收集导致。当前打包脚本已启用：

- `--enable-plugins=pyside6`

如果你改动了打包参数、升级了 PySide6，或手动移动了 dist 目录导致插件缺失，请先回到仓库根目录重新执行打包脚本，确保 `dist\pomodoro-tray-timer\` 内完整。

#### 5) 打包脚本提示“Repo path contains non-ASCII chars”

这是正常行为。为了避免少数工具链/Qt 在“包含中文/非 ASCII 路径”下出现收集失败或运行时找不到插件，`scripts\build-windows.ps1` 会自动把仓库复制到临时目录（例如 `%TEMP%\pomodoro-tray-timer-build`）中构建，构建完成后再把产物复制回仓库的 `dist\...`。

#### 4) 安装包/可执行文件被杀软拦截或误报

Nuitka/独立打包的可执行文件在部分环境可能触发误报（尤其是新产物/无签名）。建议：

- 在可信环境构建，尽量减少“再压缩/再打包”
- 必要时把 `dist\pomodoro-tray-timer\` 和安装器加入白名单

### 表头（固定）

CSV 表头在代码中固定为：

- `日期`
- `集中精力`
- `短暂休息`
- `长休息`
- `开始时间`
- `结束时间`

对应源码常量：`pomodoro_app/models.py` 的 `CSV_HEADER`。

### 字段含义

- **日期**：以阶段开始时间的本地日期为准，格式 `YYYY-MM-DD`
- **集中精力 / 短暂休息 / 长休息**：
  - 仅当前阶段对应的列会写入“计划分钟数”（整数）
  - 其他两列为空字符串
- **开始时间 / 结束时间**：格式 `YYYY-MM-DD HH:MM:SS`（精确到秒）

### 示例

```csv
日期,集中精力,短暂休息,长休息,开始时间,结束时间
2026-03-17,25,,,2026-03-17 09:00:00,2026-03-17 09:25:00
2026-03-17,,5,,2026-03-17 09:25:00,2026-03-17 09:30:00
2026-03-17,,,15,2026-03-17 11:00:00,2026-03-17 11:15:00
```

## 常见问题（FAQ）

### 1) 托盘图标“拖拽/排序”怎么实现？

**不需要应用实现。** Windows 系统托盘区域由系统管理，用户可以在托盘区域自行拖动图标排序或在“任务栏设置”里调整显示/隐藏。应用侧不会、也不应该自行控制托盘图标的位置。

### 2) 收不到通知 / Toast 不弹出怎么办？

请按下面顺序排查：

- **检查系统通知开关**：Windows 设置 → 系统 → 通知，确认已开启通知。
- **检查应用通知权限**：在通知列表中找到本应用（或相关条目），确保允许通知。
- **检查专注助手（Focus Assist）**：如果开启了“仅优先通知/仅闹钟/全屏时隐藏”等模式，Toast 可能被静默。
- **检查通知声音开关**：Windows 设置 → 系统 → 通知 →（本应用条目）→ 确认允许播放声音；以及系统层面的通知声音未被关闭/静音。
- **首次运行/被系统拦截**：部分环境首次弹 Toast 可能需要系统授权或在通知中心出现历史通知。

如果 Toast 仍不可用，应用会尝试回退到 Qt 的 `QSystemTrayIcon.showMessage()` 气泡提示，但在 Win10/11 上可能存在系统级限制/不稳定，属于已知兼容性问题。

### 3) Toast 弹出了但没有声音？

本应用的结束音效采用“**跟随 Windows Toast 系统提示音**”的方式实现，因此是否有声音取决于系统通知设置与当前系统模式：

- **系统通知声音被关闭**：请在 Windows 通知设置中开启通知声音。
- **专注助手（Focus Assist）静默**：开启专注助手时，通知可能被静音或延后显示。
- **系统/设备静音**：检查系统音量、输出设备、应用音量混音器等。

补充：当 Toast 发送失败触发 fallback 时，应用会在 Windows 下尽力发出一次轻量的系统提示音（如果系统允许）。

### 4) `history.csv` 能否手动编辑？

可以，但请注意：

- **表头字段必须保持不变**（顺序/名称都要一致）
- 时间格式必须是 `YYYY-MM-DD HH:MM:SS`
- 空值用空字符串即可（不要写 `null`）

## 项目结构（概览）

- `main.py`：启动入口
- `pomodoro_app/`：核心代码
- `scripts/`：构建脚本（Windows 打包/安装器）
- `installer/`：Inno Setup 安装器脚本（`.iss`）
- `data/`：**旧版本**运行时数据目录（当前版本默认改为写入 `%APPDATA%\pomodoro-tray-timer\`）
