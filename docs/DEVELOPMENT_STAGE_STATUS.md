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

## 单仓库结构决策

项目采用一个 GitHub 仓库：

```text
knownothing20/ai-session/
├── desktop/                  CCHV 派生的 Tauri/React/Rust 桌面端
├── scripts/session_vault/    Python Vault Core
├── tests/                    Core 测试
├── docs/                     统一产品和阶段文档
└── references/               适配器与恢复依据
```

不再创建 `ai-session-desktop` 独立仓库。桌面端的上游版本通过
`desktop/UPSTREAM.lock.json` 锁定；后续上游同步采用临时分支或导入脚本，
不依赖第二个仓库。

## 阶段 0 目标

以 `jhlee0409/claude-code-history-viewer` v1.22.0、提交
`2e29912c8743c997f203e903e6ae0054865cb8e3` 为固定上游基线，导入当前仓库
`desktop/`，移除上游 GitHub Actions，完成最小品牌替换，并在 Windows 本地跑通
Tauri 开发环境。

## 阶段 0 交付物

- [x] 锁定上游仓库、版本和提交；
- [x] 明确 MIT 许可证和第三方声明要求；
- [x] 将架构调整为单仓库 `desktop/ + Vault Core`；
- [x] 建立阶段管理规则和状态台账；
- [x] 编写单仓库 Windows 导入脚本；
- [x] 编写阶段 0 实施与验收文档；
- [x] 建立 `desktop/` 上游锁定占位结构；
- [ ] 将固定上游完整源码导入 `desktop/`；
- [ ] 确认仓库不存在 `.github/workflows/` 和 `desktop/.github/workflows/`；
- [ ] 完成最小品牌替换和第三方声明；
- [ ] Windows 本地执行前端构建；
- [ ] Windows 本地执行 Rust `cargo check`；
- [ ] Windows 本地启动 `pnpm tauri dev` 并确认窗口可打开；
- [ ] 保存阶段 0 验收报告。

## 当前限制

当前连接器可以修改现有 `ai-session` 仓库，因此“创建新仓库”的阻塞已经取消。
但当前执行容器无法解析 `github.com`，无法在这里克隆上游完整源码；当前环境也不是
Windows，不能真实打开 Tauri 窗口。

仓库提供 `scripts/bootstrap_desktop_phase0.ps1`，它会在 Windows 上把固定上游提交
直接导入当前仓库的 `desktop/`，并在导入前删除 Workflow、写入许可证声明、执行最小
品牌替换及本地验证。

## 阶段 0 Definition of Done

只有全部满足以下条件才算完成：

- `desktop/` 已包含固定上游提交的完整源码；
- 根目录和 `desktop/` 中均不存在 GitHub Workflow；
- `desktop/UPSTREAM.lock.json` 可追踪上游版本和提交；
- 原始 MIT License 与第三方声明完整；
- 最小品牌改造完成；
- `pnpm build` 在 Windows 本地通过；
- `cargo check --manifest-path src-tauri/Cargo.toml` 在 Windows 本地通过；
- `pnpm tauri dev` 在 Windows 本地成功打开应用窗口；
- 测试未使用 GitHub Actions；
- 阶段验收结果已写入仓库。
