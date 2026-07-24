# 阶段 1：接入现有备份、校验和 Codex 恢复

> 阶段：1 / 共 5 阶段  
> 本阶段完成后剩余：3 个阶段  
> 状态：进行中  
> 当前任务包：第 1 个任务包 — Sidecar 协议与调用骨架

## 阶段目标

将现有 Python Vault Core 以受控 Sidecar 方式接入 `desktop/` Tauri 应用，使用户可以在桌面界面中执行和查看：

- 应用与存储发现；
- Vault 路径和机器标识配置；
- 增量备份；
- 完整性校验；
- Codex 单会话隔离恢复；
- Codex 整库隔离恢复；
- 任务进度、结构化报告和错误信息。

本阶段不开发 Doctor、Repair、跨电脑交接或 AI 分析，这些属于后续阶段。

## 核心边界

```text
Desktop UI (React)
    ↓ Tauri Command
Rust Sidecar Bridge
    ↓ JSONL over stdin/stdout
Python Vault Core
    ↓
AgentSessionVault / Recovery Directory
```

原则：

1. 不复制一套新的备份实现到 Rust；
2. Python Core 仍是备份、校验和恢复的唯一事实源；
3. UI 不直接修改厂商原生会话目录；
4. 所有写入操作必须支持 dry-run 或预检；
5. 任务输出采用版本化 JSONL 事件协议；
6. 不创建或触发 GitHub Actions。

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

## 主要交付物

- [x] 定义 Sidecar JSONL 协议与 schema 版本；
- [x] 为 `vault_sync.py` 增加适合桌面调用的机器可读终态输出；
- [ ] 生成 Windows 可执行 Sidecar 或确定 Python 运行时打包方式；
- [ ] Rust 侧实现 Sidecar 启动、参数校验、取消和超时；
- [ ] React 侧新增 Vault 设置与任务中心；
- [ ] UI 支持 inspect、layout、sync、verify；
- [ ] UI 支持 Codex session/full restore；
- [ ] UI 显示报告路径、警告、排除项和验证结果；
- [ ] 所有危险操作有确认和 dry-run；
- [ ] 完成本地 Python、Rust、前端和端到端测试；
- [ ] 更新阶段 1 验收报告。

说明：Rust 参数验证、命令预览和协议解析骨架已经加入 `commands::vault_sidecar` 并参与 Rust 编译，但尚未加入主 Tauri `invoke_handler`。因此前端 API 客户端当前只是类型与调用约定，运行时调用将在本任务包的下一步注册后才可用。

## 任务包顺序

### 第 1 个任务包：协议与调用骨架（进行中）

- [x] 协议和威胁模型；
- [x] Python Core started/completed/failed JSONL；
- [x] Python 协议测试；
- [x] Rust 请求验证、参数数组和事件解析；
- [x] 前端共享类型和 API 客户端骨架；
- [ ] Tauri invoke handler 注册；
- [ ] Windows 本地静态与协议测试。

### 第 2 个任务包：进程执行与任务生命周期

- Rust 安全启动 Sidecar；
- stdout 逐行解析；
- stderr 限长收集；
- progress 事件；
- 取消、超时、进程清理；
- 任务状态存储。

### 第 3 个任务包：Vault 设置与备份校验 UI

- Vault 路径和 machine ID；
- app discovery；
- inspect / layout；
- sync dry-run / apply；
- verify；
- 报告与错误展示。

### 第 4 个任务包：Codex 恢复 UI

- session / full restore；
- restore 路径预检；
- 危险操作确认；
- 启动器和报告展示。

### 第 5 个任务包：打包、集成测试和阶段验收

- Windows Sidecar 打包；
- 本地 Python、Rust、前端和端到端验证；
- 阶段 1 验收报告。

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
