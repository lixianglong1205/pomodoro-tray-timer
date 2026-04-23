# macOS Release/产物命名规范（供 CI/本地构建对齐）

本文档用于记录当前仓库 **macOS GitHub Actions 发布流程**的“风格约定”，与 Windows 的发布约定保持一致（触发方式、Release 复用、资产命名、覆盖策略），并明确后续“签名/公证”的升级点位。

快速入口（README 里的 macOS 打包说明）：`README.md`

## 触发方式（Tag）

- **触发条件**：仅在 `push` 且 tag 匹配 `v*` 时触发。
- **tag 变量**：使用 `github.ref_name` 作为 tag 名（例如 `v1.2.3`）。

对应实现见：`.github/workflows/release-macos.yml`。

## 产物类型与阶段目标（阶段 1）

阶段 1 的目标是先让 CI 产出可下载的安装介质，**不做签名/不做公证**：

- **Nuitka** 生成 `.app`（`--macos-create-app-bundle`）
- 使用 **create-dmg** 将 `.app` 封装成 `.dmg`

说明：

- 未签名/未公证的 DMG/APP 在用户首次打开时通常会遇到 Gatekeeper 提示（常见操作是右键“打开”一次）。
- 该阶段无需 Apple Developer Program（成本最低、落地最快）。

## 产物路径约定（关键）

- **App bundle 路径（固定）**：`dist/pomodoro-tray-timer.app`
- **DMG 路径（固定）**：`dist-installer/pomodoro-tray-timer.dmg`

其中 `.app` 的构建脚本为：`scripts/build-macos.sh`。

## GitHub Release：复用/创建逻辑

与 Windows 一致，使用 GitHub CLI（`gh`）来“复用同名 tag 的 Release，不存在则创建”：

- 先探测：`gh release view <tag>`
- 若不存在：`gh release create <tag> --title <tag> --notes ""`

## Release 资产命名规则（关键）

与 Windows 一致，上传到 Release 时会 **显式重命名**，让资产名带上 tag：

- **Release 资产名**：`pomodoro-tray-timer-<tag>.dmg`
  - 例：`pomodoro-tray-timer-v1.2.3.dmg`

实现方式：`gh release upload` 的 `path#name` 语法，并使用 `--clobber` 覆盖。

## 覆盖策略（可重复发布）

上传命令使用：

- `--clobber`

含义：若 Release 上已存在同名资产，会覆盖上传（便于修复后重跑 workflow）。

## CI 里 DMG 生成的稳定性处理

在 GitHub Actions 上，`hdiutil`（create-dmg 内部依赖）偶发会报 “resource busy”等波动错误，因此 workflow 对 create-dmg 增加了简单重试。

## 后续升级点位：签名与公证（不在阶段 1 强制）

当你加入 Apple Developer Program 并希望降低安装阻力时，推荐升级流程为：

- **codesign（Developer ID Application）**：
  - 对 `.app` 内的可执行文件/Frameworks/PlugIns 进行签名
  - 建议启用 hardened runtime
- **notarytool 公证**：
  - `xcrun notarytool submit --wait`
  - `xcrun stapler staple`（把公证票据贴到 `.app`/`.dmg`）
- （可选）对 `.dmg` 进行签名/公证后再发布

这些步骤通常需要：

- CI 临时 keychain 导入 Developer ID 证书
- notarytool 的凭据（Apple ID / App-specific password 或 App Store Connect API key）

