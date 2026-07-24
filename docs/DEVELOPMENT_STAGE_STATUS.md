# AI Session Vault 开发阶段状态

> 总阶段数：5（阶段 0 至阶段 4）  
> 已完成阶段：**阶段 0 — 开源桌面底座导入与基线稳定**  
> 当前阶段：**阶段 1 — 接入现有备份、校验和 Codex 恢复**  
> 当前阶段完成后剩余：**3 个阶段**  
> 当前状态：**进行中：线上实现完成，Windows 本地验收待执行**

## 强制执行规则

每次开始实际开发前，必须先明确输出：

```text
阶段 X / 共 5 阶段：<阶段名称>
当前阶段完成后还剩 Y 个阶段
本次属于阶段 X 的第 N 个任务包
```

执行规则：

1. 当前阶段未满足 Definition of Done，不得进入下一阶段；
2. 不得把计划、脚本或未验证代码描述为已完成功能；
3. 阶段内连续开发，不在子任务或任务包边界停止；
4. 每次开发结束后更新阶段台账；
5. 每个阶段使用一个 GitHub 大任务 Issue 跟踪；
6. 不创建、修改或触发 GitHub Actions；
7. 验证优先使用本地静态检查、本地单元测试和本地构建；
8. Windows 专属功能必须在真实 Windows 环境验证后才能标记通过。

## 五阶段路线

| 阶段 | 名称 | 状态 | 跟踪 |
|---|---|---|---|
| 0 | 开源桌面底座导入与基线稳定 | 已完成 | Issue #2 |
| 1 | 接入现有备份、校验和 Codex 恢复 | 进行中：待本地验收 | Issue #3 |
| 2 | 健康检查、安全修复和会话管理增强 | 未开始 | 待创建 |
| 3 | 导出、跨电脑交接和 Vault 搜索增强 | 未开始 | 待创建 |
| 4 | 统一统计、AI 分析和产品化完善 | 未开始 | 待创建 |

## 单仓库结构

```text
knownothing20/ai-session/
├── desktop/                  CCHV 派生的 Tauri/React/Rust 桌面端
├── scripts/session_vault/    Python Vault Core
├── tests/                    Core、协议和安全测试
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

阶段 0 已完成完整源码导入、无 Workflow 检查、最小品牌替换、Windows 前端构建、Cargo 检查、Tauri 窗口启动和线上复核。验收资料：

- `docs/PHASE_0_OPEN_SOURCE_BASELINE.md`
- `docs/PHASE_0_ACCEPTANCE_REPORT.md`
- `docs/PHASE_0_ONLINE_REVIEW.md`

## 阶段 1 目标

将现有 Python Vault Core 通过版本化、可验证的本地 Sidecar 协议接入桌面软件，支持：

- 应用发现；
- Vault 和 machine ID 配置；
- inspect、layout、sync、verify；
- Codex 单会话和整库隔离恢复；
- dry-run、实时进度、取消、超时、结构化报告和错误展示。

Doctor、Repair、Handoff 和 AI 分析不属于阶段 1。

## 阶段 1 线上实现记录

### 协议与 Python Core

- [x] Sidecar JSONL Protocol v1；
- [x] started、progress、completed、failed 生命周期；
- [x] 默认 CLI 输出兼容；
- [x] 应用发现、检查和目录预览进度；
- [x] 会话扫描、复制、跳过、冲突和重复检测进度；
- [x] SQLite 快照和索引进度；
- [x] 哈希与 SQLite 校验进度；
- [x] 校验错误使用 `VERIFY_FAILED` 终态；
- [x] Codex session/full restore 进度；
- [x] 取消残留锁按 PID 自动回收；
- [x] Windows SQLite 句柄和路径兼容修复。

### Rust / Tauri

- [x] operation、scope、输入和超时验证；
- [x] 无 shell 命令参数数组；
- [x] Python/Sidecar 可用性检测；
- [x] 子进程启动和 JSONL 实时解析；
- [x] 协议、版本、request ID、operation、sequence 和终态校验；
- [x] 任务注册表；
- [x] 取消、超时、kill 和异常清理；
- [x] stderr 64 KiB 上限和截断标记；
- [x] 协议异常立即终止子进程；
- [x] 5 个 Tauri 命令注册；
- [x] CCHV 上游运行时保持独立，构建时注入 Vault 命令；
- [x] 上游 handler 结构变化时构建明确失败。

### 桌面 UI

- [x] 设置菜单“会话保险箱”入口；
- [x] Vault Root、machine ID、source override 本地持久化；
- [x] 应用发现和恢复能力显示；
- [x] inspect、layout；
- [x] 备份 dry-run 和真实同步；
- [x] verify；
- [x] Codex 单会话和整库恢复预演与真实恢复；
- [x] 写入确认；
- [x] 实时进度、取消、事件、错误、结果、命令预览和报告位置；
- [x] 英文、韩文、日文、简体中文和繁体中文。

### 测试与验收设施

- [x] Python 协议、锁、安全排除、校验失败测试；
- [x] Windows 安全的 Core、Adapter 和 Restore 测试；
- [x] Tauri handler 注入静态测试；
- [x] Rust Vault Sidecar 单元测试；
- [x] 前端 API 和 Vault 控制台测试；
- [x] 完整 Sidecar 端到端冒烟；
- [x] Windows 一键自动验证与明确人工确认；
- [x] 阶段 1 验收报告模板；
- [x] 未创建或触发 GitHub Actions。

## 当前唯一剩余门槛

当前在线执行环境不能访问 GitHub 工作树运行构建，也没有 Rust/Tauri 工具链和 Windows 桌面。因此以下结果尚未产生，阶段 1不能标记完成：

```powershell
Set-Location "D:\GitHub\ai-session"
git pull --ff-only
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

脚本会：

- 运行 Python 全量测试；
- 运行完整 Sidecar 冒烟；
- 校验翻译并生成类型；
- 运行 Vault 前端测试与构建；
- 运行 Rust 格式、单测和 `cargo check`；
- 启动 Tauri；
- 要求验收者在完整 UI 操作后输入大写 `YES`；
- 写入 `docs/PHASE_1_LOCAL_VALIDATION.json`。

## 阶段 1 资料

- `docs/PHASE_1_BACKUP_RESTORE_INTEGRATION.md`
- `docs/SIDECAR_PROTOCOL_V1.md`
- `docs/PHASE_1_RUNTIME_STRATEGY.md`
- `docs/PHASE_1_ACCEPTANCE_REPORT.md`
- `scripts/phase1_smoke.py`
- `scripts/validate_phase1.ps1`
- GitHub Issue #3

## 阶段 1 Definition of Done

- [x] UI 能发现当前 v0.3 支持的应用；
- [x] UI 能配置 Vault 和 machine ID；
- [x] UI 已实现 dry-run、真实同步和 verify；
- [x] UI 已实现 Codex 单会话和整库隔离恢复；
- [x] UI 与 Python Core 使用版本化结构化协议；
- [x] 任务支持取消与超时，失败不会被误判为成功；
- [x] 取消残留锁可安全回收；
- [x] 凭据、OAuth、日志和缓存仍被排除；
- [x] 现有 CLI 保持兼容；
- [ ] Windows 自动测试与构建通过；
- [ ] Windows 人工桌面操作矩阵通过；
- [ ] 实际验收结果写入报告；
- [x] 未创建或触发 GitHub Actions。
