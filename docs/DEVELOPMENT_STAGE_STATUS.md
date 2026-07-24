# AI Session Vault 开发阶段状态

> 总阶段数：5（阶段 0 至阶段 4）  
> 已完成阶段：**阶段 0 — 开源桌面底座导入与基线稳定**  
> 当前阶段：**阶段 1 — 接入现有备份、校验和 Codex 恢复**  
> 当前阶段完成后剩余：**3 个阶段**  
> 当前状态：**进行中**  
> 当前任务包：**阶段 1，第 1 个任务包 — Sidecar 协议与调用骨架**

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
| 1 | 接入现有备份、校验和 Codex 恢复 | 进行中 | Issue #3 |
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

阶段 0 已完成完整源码导入、无 Workflow 检查、最小品牌替换、Windows 前端构建、Cargo 检查、Tauri 窗口启动和线上复核。验收资料：

- `docs/PHASE_0_OPEN_SOURCE_BASELINE.md`
- `docs/PHASE_0_ACCEPTANCE_REPORT.md`
- `docs/PHASE_0_ONLINE_REVIEW.md`

Windows Python 单元测试仍有导入前已存在的平台兼容问题，记录在验收报告中，不是桌面源码导入造成。

## 阶段 1 目标

将现有 Python Vault Core 通过版本化、可验证的本地 Sidecar 协议接入桌面软件，支持：

- 应用发现；
- Vault 和 machine ID 配置；
- inspect、layout、sync、verify；
- Codex 单会话和整库隔离恢复；
- dry-run、任务进度、取消、超时、结构化报告和错误展示。

Doctor、Repair、Handoff 和 AI 分析不属于阶段 1。

## 阶段 1 第 1 个任务包

### 已完成

- [x] 定义 Sidecar JSONL Protocol v1；
- [x] 明确协议威胁模型、终态和错误代码；
- [x] Python CLI 新增 `pretty`、`json`、`jsonl` 输出格式；
- [x] Python JSONL 输出 started、completed、failed 生命周期；
- [x] 保持默认 CLI 输出兼容；
- [x] 新增 Python 协议与 CLI 测试；
- [x] Rust 新增请求模型、参数验证和安全参数数组构造；
- [x] Rust 新增协议事件解析、版本/request ID/sequence 校验；
- [x] Rust 新增 Sidecar 状态和命令预览函数；
- [x] 前端新增 Sidecar TypeScript 类型和 API 客户端骨架；
- [x] 未创建或触发 GitHub Actions。

### 尚未完成

- [ ] 将 Sidecar Tauri 命令注册到运行时 invoke handler；
- [ ] Rust 实际启动 Python/可执行 Sidecar；
- [ ] 把 Core 扫描、复制、快照、校验和恢复阶段连接到 progress 事件；
- [ ] 实现取消、超时和进程清理；
- [ ] 确定并实现 Windows Sidecar 打包方式；
- [ ] 实现 Vault 设置和任务中心 UI；
- [ ] 实现 inspect、sync、verify 和 restore 完整 UI 流程；
- [ ] 完成 Windows 本地 Python、Rust、前端和集成验证。

## 阶段 1 入口资料

- `docs/PHASE_1_BACKUP_RESTORE_INTEGRATION.md`
- `docs/SIDECAR_PROTOCOL_V1.md`
- GitHub Issue #3

## 阶段 1 Definition of Done

- UI 能发现至少当前 v0.3 支持的应用；
- UI 能配置 Vault 和 machine ID；
- UI 能完成一次 dry-run、真实同步和 verify；
- UI 能完成 Codex 单会话和整库隔离恢复；
- UI 与 Python Core 使用版本化结构化协议；
- 任务可取消，失败不会留下被误判为成功的结果；
- 凭据、OAuth、日志和缓存仍被排除；
- 现有 CLI 保持兼容；
- Windows 本地构建与集成验证通过；
- 未创建或触发 GitHub Actions；
- 阶段 1 验收结果已写入仓库。
