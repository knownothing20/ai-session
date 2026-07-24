# AI Session Vault 开发阶段状态

> 总阶段数：5（阶段 0 至阶段 4）  
> 当前阶段：**阶段 0 — 开源桌面底座导入与基线稳定**  
> 当前阶段完成后剩余：**4 个阶段**  
> 状态：**进行中**

## 强制执行规则

每次开始实际开发前，必须先明确输出：

```text
阶段 X / 共 5 阶段：<阶段名称>
当前阶段完成后还剩 Y 个阶段
本次属于阶段 X 的第 N 个任务包
```

每个阶段作为一个独立大任务包管理：

1. 阶段未满足 Definition of Done 前，不进入下一阶段；
2. 阶段内可以拆分多个提交和子任务，但不能把未完成内容描述为已完成；
3. 每次开发结束后更新本文的状态、已完成项、未完成项和验证结果；
4. 不创建、修改或触发 GitHub Actions；
5. 验证优先使用本地静态检查、本地单元测试和本地构建；
6. Windows 专属验收只能在真实 Windows 环境中标记通过。

## 五阶段路线

| 阶段 | 名称 | 状态 |
|---|---|---|
| 0 | 开源桌面底座导入与基线稳定 | 进行中 |
| 1 | 接入现有备份、校验和 Codex 恢复 | 未开始 |
| 2 | 健康检查、安全修复和会话管理增强 | 未开始 |
| 3 | 导出、跨电脑交接和 Vault 搜索增强 | 未开始 |
| 4 | 统一统计、AI 分析和产品化完善 | 未开始 |

## 阶段 0 目标

以 `jhlee0409/claude-code-history-viewer` v1.22.0、提交
`2e29912c8743c997f203e903e6ae0054865cb8e3` 为固定上游基线，建立无 GitHub Actions 的桌面派生仓库，并在 Windows 本地跑通 Tauri 开发环境。

## 阶段 0 交付物

- [x] 锁定上游仓库、版本和提交；
- [x] 明确 MIT 许可证和第三方声明要求；
- [x] 明确桌面端与 Vault Core 的双仓库边界；
- [x] 建立阶段管理规则和状态台账；
- [x] 编写 Windows 无 Actions 引导脚本；
- [x] 编写阶段 0 实施与验收文档；
- [ ] 创建 `knownothing20/ai-session-desktop` 远端派生仓库；
- [ ] 导入固定上游提交；
- [ ] 在第一次推送前删除 `.github/workflows/`；
- [ ] 配置 `origin` 与 `upstream`；
- [ ] 完成最小品牌替换和第三方声明；
- [ ] Windows 本地执行前端构建；
- [ ] Windows 本地执行 Rust `cargo check`；
- [ ] Windows 本地启动 `pnpm tauri dev` 并确认窗口可打开；
- [ ] 保存阶段 0 验收报告。

## 当前限制

当前 GitHub 连接器没有创建或 Fork 仓库的能力，执行环境也没有 GitHub CLI；容器网络无法直接克隆 `github.com`。因此远端桌面仓库创建和真实 Windows Tauri 启动尚未完成，不能将阶段 0 标记为完成。

仓库已提供 `scripts/bootstrap_desktop_phase0.ps1`，用于在 Windows 上完成克隆、锁定提交、移除 Workflow、配置远端和本地验证。

## 阶段 0 Definition of Done

只有全部满足以下条件才算完成：

- 桌面派生仓库已存在；
- 仓库中不包含 `.github/workflows/`；
- `upstream` 指向 CCHV，`origin` 指向用户桌面仓库；
- 基线提交和许可证声明可追踪；
- `pnpm build` 在 Windows 本地通过；
- `cargo check --manifest-path src-tauri/Cargo.toml` 在 Windows 本地通过；
- `pnpm tauri dev` 在 Windows 本地成功打开应用窗口；
- 测试未使用 GitHub Actions；
- 阶段验收结果已写入仓库。
