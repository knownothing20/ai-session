# AI Session Vault 开发阶段状态

> 总阶段数：5（阶段 0 至阶段 4）  
> 已完成阶段：**阶段 0 — 开源桌面底座导入与基线稳定**  
> 下一阶段：**阶段 1 — 接入现有备份、校验和 Codex 恢复**  
> 剩余阶段：**4 个**  
> 当前状态：**阶段 1 待开始**

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

| 阶段 | 名称 | 状态 | 跟踪 |
|---|---|---|---|
| 0 | 开源桌面底座导入与基线稳定 | 已完成 | Issue #2 |
| 1 | 接入现有备份、校验和 Codex 恢复 | 待开始 | Issue #3 |
| 2 | 健康检查、安全修复和会话管理增强 | 未开始 | 待创建 |
| 3 | 导出、跨电脑交接和 Vault 搜索增强 | 未开始 | 待创建 |
| 4 | 统一统计、AI 分析和产品化完善 | 未开始 | 待创建 |

## 单仓库结构

```text
knownothing20/ai-session/
├── desktop/                  CCHV 派生的 Tauri/React/Rust 桌面端
├── scripts/session_vault/    Python Vault Core
├── tests/                    Core 测试
├── docs/                     产品、阶段与验收文档
└── references/               适配器与恢复依据
```

桌面上游版本由 `desktop/UPSTREAM.lock.json` 锁定；后续同步采用临时分支或导入脚本，不依赖第二个仓库。

## 阶段 0 完成记录

固定基线：

```text
上游：jhlee0409/claude-code-history-viewer
版本：v1.22.0
提交：2e29912c8743c997f203e903e6ae0054865cb8e3
```

交付物：

- [x] 固定上游仓库、版本和提交；
- [x] 保留 MIT License 和第三方声明；
- [x] 使用单仓库 `desktop/ + Vault Core` 结构；
- [x] 导入完整桌面源码；
- [x] 根目录和 `desktop/` 均不存在 GitHub Workflow；
- [x] 完成最小品牌替换；
- [x] Windows `pnpm install` 通过；
- [x] Windows `pnpm build` 通过；
- [x] Windows `cargo check` 通过；
- [x] Windows `pnpm tauri dev` 成功打开应用窗口；
- [x] Python compileall 通过；
- [x] 保存阶段 0 本地验收报告；
- [x] 完成线上配置与许可证复核；
- [x] 未创建或触发 GitHub Actions。

验收资料：

- `docs/PHASE_0_OPEN_SOURCE_BASELINE.md`
- `docs/PHASE_0_ACCEPTANCE_REPORT.md`
- `docs/PHASE_0_ONLINE_REVIEW.md`

说明：Windows Python 单元测试仍有导入前已存在的平台兼容问题，记录在验收报告中，不是桌面源码导入造成。

## 阶段 1 入口

阶段 1 的统一任务包：

- `docs/PHASE_1_BACKUP_RESTORE_INTEGRATION.md`
- GitHub Issue #3

下一次开始实际开发时，必须先声明：

```text
阶段 1 / 共 5 阶段：接入现有备份、校验和 Codex 恢复
当前阶段完成后还剩 3 个阶段
本次属于阶段 1 的第 1 个任务包
```
