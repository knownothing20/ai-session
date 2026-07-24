# 阶段 0：开源桌面底座导入与基线稳定

> 阶段：0 / 共 5 阶段  
> 本阶段完成后剩余：4 个阶段  
> 状态：进行中

## 1. 阶段目标

在现有 `knownothing20/ai-session` 仓库中新增 `desktop/`，以
`jhlee0409/claude-code-history-viewer` v1.22.0、提交
`2e29912c8743c997f203e903e6ae0054865cb8e3` 为固定基线，在不使用
GitHub Actions 的前提下完成 Windows 本地 Tauri 开发环境验证。

本阶段只建立可持续开发基线，不正式接入 Vault Core 业务功能。Vault Core 的 UI
接入属于阶段 1。

## 2. 单仓库结构

```text
knownothing20/ai-session/
├── desktop/                  CCHV 派生桌面端
│   ├── src/                  React + TypeScript
│   ├── src-tauri/            Rust + Tauri
│   ├── public/
│   ├── UPSTREAM.lock.json
│   ├── UPSTREAM.md
│   └── THIRD_PARTY_NOTICES.md
├── scripts/session_vault/    Python Vault Core
├── scripts/vault_sync.py
├── tests/
├── docs/
└── references/
```

采用单仓库的原因：

- 不需要创建第二个 GitHub 仓库；
- Python Core 和桌面端可以在同一 PR 中联调；
- Sidecar 打包路径更明确；
- 文档、版本、Issue 和阶段台账集中管理；
- 用户最终只面对一个项目和一个安装包。

代价是上游同步不能直接依赖 Fork 对比，因此必须通过固定提交、锁定文件和导入脚本
保持可追踪性。

## 3. 固定上游基线

```text
上游仓库：https://github.com/jhlee0409/claude-code-history-viewer
版本：v1.22.0
提交：2e29912c8743c997f203e903e6ae0054865cb8e3
许可证：MIT
导入位置：desktop/
```

禁止直接追踪浮动的 `main`。每次上游更新必须：

1. 记录旧提交和新提交；
2. 在临时目录或临时分支拉取上游；
3. 删除上游 `.github/workflows/`；
4. 本地检查差异和冲突；
5. 执行本地构建与测试；
6. 更新 `desktop/UPSTREAM.lock.json`；
7. 手动提交，不使用 GitHub Actions。

## 4. 无 GitHub Actions 规则

仓库中禁止存在：

```text
.github/workflows/
desktop/.github/workflows/
```

检查命令：

```powershell
git ls-files ".github/workflows/*" "desktop/.github/workflows/*"
```

输出必须为空。

阶段 0 不允许：

- 新建或保留 Workflow；
- 手动触发或重跑 Actions；
- 使用 Actions 构建 Windows 安装包；
- 添加 `push`、`pull_request`、`schedule`、`cron` 或 `workflow_dispatch`。

## 5. Windows 前置环境

Windows 10/11 x64 需要：

- Git；
- Node.js 20 LTS；
- Corepack / pnpm 10；
- Rust stable 与 Cargo；
- Visual Studio Build Tools，并勾选“使用 C++ 的桌面开发”；
- Microsoft Edge WebView2 Runtime；
- Tauri 2 所需系统组件。

本阶段只使用本地命令，不使用远端 CI。

## 6. 单仓库导入脚本

仓库提供：

```text
scripts/bootstrap_desktop_phase0.ps1
```

在 `ai-session` 仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\bootstrap_desktop_phase0.ps1 `
  -InstallDependencies `
  -RunChecks
```

脚本会：

1. 检查当前目录是 `ai-session` Git 仓库；
2. 检查根目录和 `desktop/` 中没有 Workflow；
3. 克隆固定 CCHV 上游到系统临时目录；
4. 切换到固定提交；
5. 在复制前删除上游 `.github/workflows/` 和 `.git/`；
6. 将完整源码复制到当前仓库 `desktop/`；
7. 写入 `UPSTREAM.lock.json`、`UPSTREAM.md` 和第三方声明；
8. 完成应用名、包名和 Tauri identifier 的最小替换；
9. 可选安装依赖并执行本地构建；
10. 生成阶段 0 Windows 验收报告模板。

如果 `desktop/` 已包含正式源码，重新导入必须显式加入：

```powershell
-ForceReimport
```

需要自动创建本地提交时可以加入：

```powershell
-Commit
```

脚本不会自动推送，不会创建或运行 GitHub Actions。

## 7. 本地验证命令

所有桌面命令都在 `desktop/` 目录执行：

```powershell
cd .\desktop
corepack enable
corepack pnpm install --frozen-lockfile
corepack pnpm build
cargo check --manifest-path src-tauri/Cargo.toml
corepack pnpm tauri dev
```

验收含义：

- `pnpm build`：前端 TypeScript 和 Vite 构建通过；
- `cargo check`：Rust/Tauri 后端静态编译检查通过；
- `pnpm tauri dev`：桌面窗口能够打开并加载会话界面；
- 本阶段不要求生成正式安装包。

## 8. 最小品牌改造

阶段 0 只做不会大幅增加上游冲突的修改：

- 应用显示名改为 `AI Session Vault`；
- npm 包名改为 `ai-session-vault-desktop`；
- Rust 根包名改为 `ai-session-vault-desktop`；
- Tauri identifier 改为 `com.aisession.vault`；
- HTML 标题改为 `AI Session Vault`；
- 保留原始 MIT License；
- 增加上游锁定和第三方声明。

默认简体中文、Logo、完整视觉重设计和界面功能调整在源码成功运行后处理，不作为首次
导入的前置条件。

## 9. 上游同步策略

单仓库不配置永久 `upstream` Git remote。采用“临时克隆 + 固定提交导入”：

```text
临时克隆上游
→ checkout 固定提交
→ 删除 Workflow
→ 对比 desktop/ 当前版本
→ 本地构建与测试
→ 更新 UPSTREAM.lock.json
→ 手动提交
```

这样不会把两个完全不同历史的仓库强行合并，也不会污染现有 Python Core 的 Git 历史。

## 10. 阶段 0 验收报告

报告位置：

```text
docs/phase-reports/PHASE_0_WINDOWS_REPORT.md
```

至少包含：

```markdown
# 阶段 0 Windows 验收报告

- 仓库：knownothing20/ai-session
- 桌面目录：desktop/
- 上游提交：2e29912c8743c997f203e903e6ae0054865cb8e3
- Windows 版本：
- Node 版本：
- pnpm 版本：
- rustc / cargo 版本：
- `.github/workflows/`：不存在
- `desktop/.github/workflows/`：不存在
- `pnpm build`：通过 / 失败
- `cargo check`：通过 / 失败
- `pnpm tauri dev`：通过 / 失败
- 应用窗口截图：
- 已知问题：
- 是否允许进入阶段 1：是 / 否
```

## 11. 当前执行状态

已完成：

- 锁定 CCHV 上游版本和提交；
- 完成开源许可证评估；
- 将架构改为单仓库；
- 建立 `desktop/` 上游锁定占位结构；
- 编写单仓库导入脚本、阶段台账和验收标准。

尚未完成：

- 当前容器无法解析 `github.com`，不能在本环境克隆并导入完整上游源码；
- 当前环境不是 Windows，不能完成真实 Tauri 窗口验收；
- 因此阶段 0 仍为进行中。

## 12. 阶段 0 Definition of Done

- [ ] 固定上游完整源码已导入当前仓库 `desktop/`；
- [ ] 根目录和 `desktop/` 均不存在 GitHub Workflow；
- [ ] `desktop/UPSTREAM.lock.json` 与实际源码一致；
- [ ] MIT 与第三方声明完整；
- [ ] 最小品牌改造完成；
- [ ] Windows `pnpm build` 通过；
- [ ] Windows `cargo check` 通过；
- [ ] Windows `pnpm tauri dev` 成功打开窗口；
- [ ] 验收报告已保存；
- [ ] 未创建或触发 GitHub Actions。
