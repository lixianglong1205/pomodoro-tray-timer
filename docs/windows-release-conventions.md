# Windows Release/产物命名规范（供 macOS 对齐）

本文档用于记录当前仓库 **Windows GitHub Actions 发布流程**的“风格约定”，以便 macOS workflow 与其保持一致（触发方式、Release 复用、资产命名、覆盖策略）。

## 触发方式（Tag）

- **触发条件**：仅在 `push` 且 tag 匹配 `v*` 时触发。
- **tag 变量**：使用 `github.ref_name` 作为 tag 名（例如 `v1.2.3`）。

对应实现见：`.github/workflows/release-windows.yml`。

## GitHub Release：复用/创建逻辑

Windows 流程使用 GitHub CLI（`gh`）来“复用同名 tag 的 Release，不存在则创建”：

- 先探测：`gh release view <tag>`
- 若不存在：`gh release create <tag> --title <tag> --notes ""`

该逻辑确保：

- 同一个 tag 的 Release 会被 **复用**（重复跑可更新资产）
- 不会为同一 tag 反复创建新的 Release

## Release 资产命名规则（关键）

Windows 构建得到的安装包路径固定为：

- `dist-installer/pomodoro-tray-timer-setup.exe`

但上传到 Release 时会 **显式重命名**，让 Release 资产名带上 tag：

- **Release 资产名**：`pomodoro-tray-timer-setup-<tag>.exe`
  - 例：`pomodoro-tray-timer-setup-v1.2.3.exe`

实现方式是利用 `gh release upload` 的 `path#name` 语法：

- `gh release upload <tag> "dist-installer/pomodoro-tray-timer-setup.exe#pomodoro-tray-timer-setup-<tag>.exe" --clobber`

其中 `#` 后面的部分是 Release 上最终显示的文件名。

## 覆盖策略（可重复发布）

上传命令使用：

- `--clobber`

含义：

- 若 Release 上已存在同名资产，会 **覆盖** 上传（便于修复后重新发 tag 流程或重跑 workflow）。

## Actions Artifact（CI 内部产物）命名约定

Windows workflow 同时会上传 Actions artifact（用于 CI 内部留存/下载）：

- **artifact 名**：`windows-installer-<tag>`（例：`windows-installer-v1.2.3`）
- **包含路径**：
  - `dist/pomodoro-tray-timer/**`
  - `dist-installer/pomodoro-tray-timer-setup.exe`

## macOS workflow 对齐建议（直接套用）

为与 Windows 风格一致，macOS 发布建议采用同样的模式：

- **触发**：`on.push.tags: ["v*"]`
- **Release 逻辑**：`view -> 不存在则 create -> upload`
- **资产命名**：上传时用 `path#assetName` 显式命名，并带上 tag
  - 建议：`pomodoro-tray-timer-<tag>.dmg`
- **覆盖**：`--clobber`
- **Actions artifact 名**：与 Windows 同构
  - 建议：`macos-dmg-<tag>` 或 `macos-installer-<tag>`（二选一，关键是与 Windows “平台-类型-tag” 的结构一致）

