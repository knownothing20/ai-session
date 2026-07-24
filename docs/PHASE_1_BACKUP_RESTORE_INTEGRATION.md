# 阶段 1：接入现有备份、校验和 Codex 恢复

> 阶段：1 / 共 5 阶段  
> 本阶段完成后剩余：3 个阶段  
> 状态：进行中  
> 当前进度：线上实现已形成完整闭环，等待 Windows 本地自动验证与人工桌面验收

## 阶段目标

将现有 Python Vault Core 以受控 Sidecar 方式接入 `desktop/` Tauri 应用，使用户可以在桌面界面中执行和查看：

- 应用与存储发现；
- Vault 路径和机器标识配置；
- 增量备份；
- 完整性校验；
- Codex 单会话隔离恢复；
- Codex 整库隔离恢复；
- 任务进度、取消、超时、结构化报告和错误信息。

本阶段不开发 Doctor、Repair、跨电脑交接或 AI 分析，这些属于后续阶段。

## 核心边界

```text
Desktop UI (React)
    ↓ Tauri Command / Event
Rust Sidecar Bridge
    ↓ JSONL over stdout
Python Vault Core
    ↓
AgentSessionVault / Recovery Directory
```

原则：

1. 不复制一套新的备份实现到 Rust；
2. Python Core 仍是备份、校验和恢复的唯一事实源；
3. UI 不直接修改厂商原生会话目录；
4. 所有写入操作支持 dry-run 或预检；
5. 任务输出采用版本化 JSONL 事件协议；
6. 进程使用参数数组启动，不通过 shell；
7. 只有 `completed` 终态可判定成功；
8. 不创建或触发 GitHub Actions。

## Sidecar Protocol v1

协议定义见：

- `docs/SIDECAR_PROTOCOL_V1.md`
- Python：`scripts/session_vault/protocol.py`
- Rust：`desktop/src-tauri/src/commands/vault_sidecar.rs`
- TypeScript：`desktop/src/types/vaultSidecar.ts`

生命周期：

```text
started
→ progress（零个或多个）
→ completed / failed
```

默认 CLI 继续输出格式化 JSON；桌面调用显式使用：

```text
--output-format jsonl
--protocol-version 1
--request-id <uuid>
```

## 当前实现

### Python Vault Core

- [x] `pretty`、`json`、`jsonl` 输出模式；
- [x] started、progress、completed、failed；
- [x] 应用发现进度；
- [x] inspect 和 layout 进度；
- [x] 会话扫描、复制、跳过、冲突和重复检测进度；
- [x] SQLite Backup API 和索引快照进度；
- [x] 哈希与 SQLite `quick_check` 校验进度；
- [x] Codex session/full restore 验证、复制、索引和发布进度；
- [x] 默认 CLI 行为兼容；
- [x] 取消后残留锁按 PID 自动回收；
- [x] Windows SQLite 句柄显式关闭。

### Rust / Tauri

- [x] operation、scope、路径字符串和超时验证；
- [x] `Command::args` 无 shell 参数构造；
- [x] Sidecar 状态与 Python 可用性检测；
- [x] 子进程启动、stdout JSONL 逐行解析和 stderr 收集；
- [x] 协议名、版本、request ID、operation、sequence 和终态校验；
- [x] 任务注册表；
- [x] 取消、超时、kill 和进程清理；
- [x] 异常退出和缺失终态合成 failed 事件；
- [x] 5 个 Tauri Command 注册；
- [x] CCHV 上游运行时保持在 `lib_upstream.rs`，由 `build.rs` 在编译时注入 Vault Command；
- [x] 上游 handler 结构变化时构建明确失败。

### React UI

- [x] 设置菜单“会话保险箱”入口；
- [x] Vault Root、machine ID、source override 持久化；
- [x] 应用发现与能力显示；
- [x] inspect、layout；
- [x] sync dry-run 和真实增量备份；
- [x] verify；
- [x] Codex 单会话和整库 restore dry-run；
- [x] Codex 单会话和整库真实恢复；
- [x] 写入操作确认；
- [x] 实时进度、事件、结果、错误、命令预览和报告位置；
- [x] 取消按钮和运行任务恢复；
- [x] 英文、韩文、日文、简体中文、繁体中文。

## 运行时方案

阶段 1 使用受控系统 Python：

```text
默认：python
解释器覆盖：AI_SESSION_VAULT_PYTHON
Sidecar 覆盖：AI_SESSION_VAULT_SIDECAR
```

这满足阶段 1 的 Python 运行时方案。正式安装后免 Python 的独立可执行 Sidecar、代码签名和 Tauri `externalBin` 属于阶段 4 产品化，详见：

- `docs/PHASE_1_RUNTIME_STRATEGY.md`

## 测试与验收

已加入：

- `tests/test_sidecar_protocol.py`；
- `tests/test_locking.py`；
- `tests/test_tauri_handler_injection.py`；
- Windows 安全的 Core、Adapter 和 Restore 测试；
- `desktop/src/test/vaultSidecarApi.test.ts`；
- `desktop/src/test/VaultConsoleModal.test.tsx`；
- `scripts/phase1_smoke.py` 完整 Sidecar 冒烟；
- `scripts/validate_phase1.ps1` Windows 一键验证；
- `docs/PHASE_1_ACCEPTANCE_REPORT.md`。

本地自动验证：

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1
```

正式人工验收：

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

当前在线环境不能运行 Windows、Cargo、Tauri 和真实桌面窗口，因此测试文件已提交不等于测试通过。阶段 1 保持“进行中”，直到 Windows 自动验证与人工操作矩阵全部通过。

## 阶段 1 Definition of Done

- UI 能发现至少当前 v0.3 支持的应用；
- UI 能配置 Vault 和 machine ID；
- UI 能完成一次 dry-run、真实同步和 verify；
- UI 能完成 Codex 单会话和整库隔离恢复；
- UI 与 Python Core 使用版本化结构化协议；
- 任务可取消，失败不会留下被误判为成功的结果；
- 取消造成的残留锁可安全回收；
- 凭据、OAuth、日志和缓存仍被排除；
- 现有 CLI 保持兼容；
- Windows 本地自动验证通过；
- Windows 人工桌面操作矩阵通过；
- 未创建或触发 GitHub Actions；
- 阶段 1 验收结果已写入仓库。
