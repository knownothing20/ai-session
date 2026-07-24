# 阶段 0：开源桌面底座导入与基线稳定

> 阶段：0 / 共 5 阶段  
> 本阶段完成后剩余：4 个阶段  
> 状态：进行中

## 1. 阶段目标

创建 `knownothing20/ai-session-desktop` 桌面派生仓库，以
`jhlee0409/claude-code-history-viewer` v1.22.0、提交
`2e29912c8743c997f203e903e6ae0054865cb8e3` 为固定基线，在不使用 GitHub Actions 的前提下完成 Windows 本地 Tauri 开发环境验证。

本阶段只建立可持续开发基线，不接入 Vault Core 的正式业务功能。Vault Core 接入属于阶段 1。

## 2. 为什么采用独立桌面仓库

推荐双仓库：

```text
knownothing20/ai-session
  Python Vault Core
  备份、校验、快照、恢复、Doctor、Repair、Handoff

knownothing20/ai-session-desktop
  CCHV 派生桌面端
  Tauri、React、Rust Provider、搜索、查看、统计、导出
```

这样可以：

- 保留现有 Python Core 的稳定历史；
- 更容易同步 CCHV 上游更新；
- 避免 Rust/React 与 Python Core 的依赖和发布流程相互污染；
- 后续通过 Sidecar JSONL 协议连接两个仓库；
- 用户最终仍安装和使用一个桌面软件。

## 3. 固定上游基线

```text
上游仓库：https://github.com/jhlee0409/claude-code-history-viewer
版本：v1.22.0
提交：2e29912c8743c997f203e903e6ae0054865cb8e3
许可证：MIT
```

禁止直接追踪浮动的 `main` 作为初始基线。后续更新必须：

1. 记录上游起止提交；
2. 单独建立上游同步分支；
3. 本地检查冲突和行为变化；
4. 不通过 GitHub Actions 验证；
5. 合并后更新 `UPSTREAM.md`。

## 4. 无 GitHub Actions 导入规则

第一次推送到用户仓库前必须删除：

```text
.github/workflows/
```

并执行检查：

```powershell
git ls-files .github/workflows
```

输出必须为空。

阶段 0 不允许：

- 新建 Workflow；
- 保留上游 Workflow 后再推送；
- 手动触发或重跑 Actions；
- 使用 Actions 构建 Windows 安装包；
- 添加 `push`、`pull_request`、`schedule` 或 `workflow_dispatch` 触发器。

## 5. Windows 前置环境

需要在 Windows 10/11 x64 安装：

- Git；
- Node.js 20 LTS；
- Corepack / pnpm 10；
- Rust stable 与 Cargo；
- Visual Studio Build Tools，勾选“使用 C++ 的桌面开发”；
- Microsoft Edge WebView2 Runtime；
- Tauri 2 所需系统组件。

本阶段只使用本地命令，不使用远端 CI。

## 6. 一键引导脚本

仓库提供：

```text
scripts/bootstrap_desktop_phase0.ps1
```

### 6.1 只准备本地派生目录

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_desktop_phase0.ps1 `
  -Destination "D:\Develop\ai-session-desktop"
```

脚本会：

- 克隆固定上游；
- 切换到固定提交；
- 建立 `phase/0-open-source-baseline` 分支；
- 删除 `.github/workflows/`；
- 将原远端改名为 `upstream`；
- 写入 `UPSTREAM.md` 与 `THIRD_PARTY_NOTICES.md`；
- 检查仓库中不存在 Workflow；
- 创建本地基线提交。

### 6.2 配置用户远端仓库

远端 `knownothing20/ai-session-desktop` 创建后：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_desktop_phase0.ps1 `
  -Destination "D:\Develop\ai-session-desktop" `
  -TargetRepoUrl "https://github.com/knownothing20/ai-session-desktop.git" `
  -InstallDependencies `
  -RunChecks
```

只有显式加入 `-Push` 才会推送：

```powershell
... -Push
```

推送前脚本会再次确认 `.github/workflows/` 为空。

## 7. 本地验证命令

```powershell
corepack enable
pnpm install --frozen-lockfile
pnpm build
cargo check --manifest-path src-tauri/Cargo.toml
pnpm tauri dev
```

验收含义：

- `pnpm build`：前端 TypeScript 和 Vite 构建通过；
- `cargo check`：Rust/Tauri 后端静态编译检查通过；
- `pnpm tauri dev`：桌面窗口能打开并加载会话界面；
- 不要求本阶段生成正式安装包。

## 8. 最小品牌改造

阶段 0 只进行不会妨碍上游同步的最小改造：

- 应用显示名改为 `AI Session Vault`；
- 包名和 Tauri identifier 使用项目自有名称；
- 默认语言优先简体中文；
- 增加“关于 / 开源许可”入口；
- 保留 CCHV 和原作者版权声明；
- 新增 `UPSTREAM.md`；
- 新增 `THIRD_PARTY_NOTICES.md`。

Logo 和大规模视觉重设计不属于阶段 0，避免在基线尚未稳定时制造大量冲突。

## 9. 阶段 0 验收报告模板

```markdown
# 阶段 0 验收报告

- 桌面仓库：
- 上游提交：2e29912c8743c997f203e903e6ae0054865cb8e3
- 开发分支：phase/0-open-source-baseline
- Windows 版本：
- Node 版本：
- pnpm 版本：
- rustc / cargo 版本：
- `.github/workflows/`：不存在
- `pnpm build`：通过 / 失败
- `cargo check`：通过 / 失败
- `pnpm tauri dev`：通过 / 失败
- 应用窗口截图：
- 已知问题：
- 是否允许进入阶段 1：是 / 否
```

## 10. 当前执行状态

已完成：

- 锁定 CCHV 上游版本和提交；
- 完成开源许可证评估；
- 确定双仓库结构；
- 编写本阶段文档、台账和 Windows 引导脚本。

尚未完成：

- 当前工具无法创建/Fork 新 GitHub 仓库；
- 当前容器无法解析 `github.com`，不能完成本地克隆；
- 当前环境不是 Windows，不能验证 Tauri Windows 窗口；
- 因此阶段 0 仍为进行中。

## 11. 阶段 0 Definition of Done

- [ ] 用户桌面仓库已创建；
- [ ] 固定上游提交已导入；
- [ ] `.github/workflows/` 不存在；
- [ ] `origin` 和 `upstream` 正确；
- [ ] MIT 与第三方声明完整；
- [ ] 最小品牌改造完成；
- [ ] Windows `pnpm build` 通过；
- [ ] Windows `cargo check` 通过；
- [ ] Windows `pnpm tauri dev` 成功打开窗口；
- [ ] 验收报告已保存；
- [ ] 未创建或触发 GitHub Actions。
