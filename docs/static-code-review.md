# 静态代码审核报告

> 审核日期：2026-04-27 | 分支：feature/macos-support | 提交：e84a42e
> 审核范围：所有源码、脚本及 CI 配置文件

---

## 修复状态

| 编号 | 问题 | 严重度 | 状态 |
|------|------|--------|------|
| H-01 | `legacy_data_dir()` 相对路径 | High | ✅ 已修复 |
| M-01 | 死代码 `parse_dt_local` | Medium | ✅ 已移除 |
| M-02 | 死代码 `_play_sound_macos` | Medium | ✅ 已移除 |
| M-03 | 死代码 `if __name__` 块 | Medium | ✅ 已移除 |
| M-04 | CSV 列名隐式耦合 | Medium | ✅ 改用列索引 |
| M-05 | 多余 `type: ignore` | Medium | ✅ 已移除 |
| L-01 | 缺少 lint/type-check | Low | ✅ 已配置 ruff + mypy |
| L-02 | pyproject.toml 描述占位符 | Low | ✅ 已更新 |
| L-05 | `__import__` 非常规调用 | Low | ✅ 改用 direct import |
| S-04 | Popen 已随死代码移除 | — | ✅ 已清理 |

遗留问题（设计使然/已知权衡）：S-01（盲异常捕获）、S-02（`os._exit` macOS workaround）、L-03（中文 i18n）、L-04（测试访问私有成员）

---

## 目录
1. [发现概览](#1-发现概览)
2. [Bug 与风险](#2-bug-与风险)
3. [代码质量](#3-代码质量)
4. [安全与健壮性](#4-安全与健壮性)
5. [可维护性与工程实践](#5-可维护性与工程实践)
6. [构建与 CI/CD](#6-构建与-cicd)
7. [评分汇总](#7-评分汇总)

---

## 1. 发现概览

| 严重度 | 数量 | 说明 |
|--------|------|------|
| **High** | 1 | 逻辑风险：相对路径依赖运行时工作目录 |
| **Medium** | 4 | 死代码、不一致、潜在歧义 |
| **Low** | 6 | 风格、可维护性、工程配置 |

---

## 2. Bug 与风险

### H-01: `legacy_data_dir()` 返回相对路径 — 依赖 CWD

**文件**: `pomodoro_app/paths.py:159-161`

```python
def legacy_data_dir() -> Path:
    # 兼容旧版本相对路径 data/
    return Path("data")
```

**问题**: `legacy_data_dir()` 返回 `Path("data")`，这是一个**相对路径**，解析结果完全依赖进程的当前工作目录 (CWD)。当用户通过快捷方式、LaunchAgent 或不同目录启动应用时，CWD 可能不等于项目根目录，导致：

- 遗留迁移逻辑 (`_try_one_time_migrate_legacy_dirs` / `_migrate_legacy_if_needed`) 找不到旧数据
- 数据丢失或重复创建

**缓解**: 在 `paths.py:75` 处 `legacy.resolve()` 做了一次绝对化。但 `config_store.py:48` 和 `storage_csv.py:27` 调用的是 `legacy_config_path()` / `legacy_history_path()`，它们直接返回 `Path("data") / "config.json"`，此时 `.resolve()` 调用在 `_try_one_time_migrate_legacy_dirs` 内部才发生，而 `_migrate_legacy_if_needed` 中**没有 resolve**。

**建议**: 
- 将 `legacy_data_dir()` 改为 `return Path(__file__).resolve().parent.parent / "data"`，或
- 在 `_migrate_legacy_if_needed` 中对 `legacy` 路径调用 `.resolve()`

---

## 3. 代码质量

### M-01: 死代码 — `parse_dt_local` 未被使用

**文件**: `pomodoro_app/models.py:75-76`

```python
def parse_dt_local(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
```

该函数已定义但代码库中没有任何导入或调用。可能是早期版本的遗留产物，或为将来预留但未实现调用方。建议移除或补充使用场景。

### M-02: 死代码 — `Notifier._play_sound_macos` 未被调用

**文件**: `pomodoro_app/notifications.py:138-161`

`_play_sound_macos` 方法定义完善，支持通过环境变量 `POMODORO_SOUND` 启用，但没有任何地方调用它。注释说明 "Disabled by default"，但从未被 `notify()` 或其他方法触发。

### M-03: 死代码 — `app.py` 中重复的 `if __name__` 块

**文件**: `pomodoro_app/app.py:122-124`

```python
if __name__ == "__main__":
    raise SystemExit(run())
```

`app.py` 是作为包模块被 `main.py` 导入的，永远不会以 `__main__` 方式运行。该入口块是无意义死代码。

### M-04: CSV 列名与渲染逻辑的隐式耦合

**文件**: `pomodoro_app/history_window.py:161-162` / `pomodoro_app/models.py:9`

```python
# models.py
CSV_HEADER = ["日期", "集中精力", "短暂休息", "长休息", "开始时间", "结束时间"]

# history_window.py
if col in ("集中精力", "短暂休息", "长休息"):  # 硬编码中文列名
    item.setTextAlignment(...)
```

渲染逻辑用硬编码的中文字符串集合判断对齐方式。如果 `CSV_HEADER` 的列名或顺序变更，对齐可能失效。建议在 `SessionRecord` 上定义列角色常量，或使用列索引而非字符串匹配。

### M-05: `storage_csv.py` 中多余的 `type: ignore`

**文件**: `pomodoro_app/storage_csv.py:59`

```python
record = SessionRecord.from_csv_row(row)  # type: ignore[arg-type]
```

`csv.DictReader` 按行返回 `dict[str, str]`，`from_csv_row` 签名为 `def from_csv_row(row: dict[str, str])`，类型完全匹配，无需 suppression。

---

## 4. 安全与健壮性

### S-01: 链中的 `except Exception` 可能隐藏真实故障

代码库中大量使用裸 `except Exception: return`（如 `config_store.py:67,80`、`notifications.py:45,62,136,200,211,219` 等）。虽然这提供了"尽力而为"的健壮性（在通知/fspath 等非关键路径上合理），但会产生以下后果：

- 配置解析失败时静默回退默认值，用户可能无感知
- 通知链中任一步骤抛异常即被吞掉，调试困难
- `_show_qt_toast_macos` 在渲染失败时不会报错

**建议**: 对至少关键的异常路径（如配置加载/保存）增加 `logging.warning`，或在开发模式下允许异常传播。

### S-02: `os._exit(0)` 绕过清理

**文件**: `pomodoro_app/app.py:76,118`

在 macOS 上使用 `os._exit()` 强制终止，绕过 Python 退出处理器、`atexit` 注册、`__del__` 等方法。代码注释充分说明了原因（PyObjC/NSRunLoop 问题），这是已知的必要 workaround。但风险在于：

- 如果有动态创建的临时文件需要在退出时清理，将不会执行
- `CsvStorage` 可能正在写文件（虽然逻辑上在 `phase_finished` 信号中已写入）

### S-03: `json.dumps` 正确防止 AppleScript 注入

**文件**: `pomodoro_app/notifications.py:191`

```python
script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
```

使用 `json.dumps` 对字符串进行转义再嵌入 AppleScript 是正确做法，防止标题/消息中包含引号或特殊字符导致的注入。这是很好的防御性编程。

### S-04: ~~`subprocess.Popen` 安全调用~~（已随死代码移除）

**文件**: 原 `notifications.py:155`，该代码随 `_play_sound_macos` 一起移除。

---

## 5. 可维护性与工程实践

### L-01: 缺少类型检查与 Lint ✅ 已修复

**文件**: `Makefile:9-12` / `pyproject.toml:23-37`

```makefile
lint:
    uv run python -m compileall pomodoro_app main.py
    uv run ruff check pomodoro_app main.py scripts/
    uv run mypy pomodoro_app main.py
```

已配置 ruff（规则集：E, F, W, I, N, UP, S, SLF, BLE）和 mypy（strict 模式），`make lint` 一并通过。测试脚本中 `assert` / 私有访问豁免配置在 `per-file-ignores` 中。

### L-02: `pyproject.toml` 描述为占位符 ✅ 已修复

```toml
description = "A pomodoro timer that lives in your system tray — cross-platform (macOS / Windows) with native notifications"
```

### L-05: `smoke_test_macos.py` 中非常规的 `__import__` 调用 ✅ 已修复

改用标准函数内部 `import`。

---

## 6. 构建与 CI/CD

### C-01: Release 协调机制健壮

macOS 和 Windows 两个 workflow 在独立 runner 上并行构建，通过 draft release + 双端 asset 检查后自动 publish 的模式设计良好，避免了"不可变 release"策略下的竞态问题。

### C-02: Nuitka 构建脚本防御性强

- Windows 脚本预处理非 ASCII 路径（Nuitka 已知问题）
- macOS 脚本对 `.app` bundle 路径做 fallback 查找
- 两个脚本都检查 `uv` 可用性

### C-03: Inno Setup 安装体验细致

`installer/pomodoro-tray-timer.iss` 允许用户在安装时自定义数据目录，写入 `settings.ini`，降低首次使用门槛。

---

## 7. 评分汇总

| 维度 | 评级 | 主要问题 |
|------|------|----------|
| 正确性 | A | 已修复相对路径风险与死代码 |
| 健壮性 | B | 过多的静默异常捕获（设计使然） |
| 安全性 | A | 无注入漏洞，shell 调用安全 |
| 可维护性 | B+ | 已集成 ruff + mypy |
| 文档与工程配置 | A- | 已更新描述、新增 lint 配置 |
| CI/CD | A | 协调设计优秀、防御性强 |

**总体评级**: **B+**（已修复全部 Medium+ 问题）

---

## 快速修复建议（按优先级）

已全部修复。遗留项目均为设计使然的已知权衡：
- S-01 — `except Exception` 链（非关键路径的尽力而为模式）
- S-02 — `os._exit`（PyObjC/NSRunLoop 必要 workaround）
- L-03 — 中文 UI 字符串（个人项目，无 i18n 需求）
- L-04 — 测试直接访问私有成员（常见测试模式）
