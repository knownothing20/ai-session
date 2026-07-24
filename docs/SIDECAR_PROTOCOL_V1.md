# AI Session Vault Sidecar Protocol v1

> 阶段：1 / 共 5 阶段  
> 用途：桌面 Tauri/Rust 与 Python Vault Core 之间的本地进程协议  
> 当前版本：1

## 1. 设计目标

Sidecar 协议让桌面程序调用现有 Python Vault Core，而不是在 Rust 中重新实现备份、校验和恢复逻辑。

核心原则：

1. Python Core 是 `inspect`、`layout`、`sync`、`verify` 和 `restore` 的唯一事实源；
2. Rust 使用 `Command::args`，不拼接 shell 命令；
3. stdout 只输出一行一个 JSON 事件；
4. stderr 只用于有限诊断，不作为业务结果；
5. 每个请求有唯一 `request_id`；
6. `sequence` 从 1 严格递增；
7. 协议名、版本、request ID、operation 和终态必须校验；
8. 失败、取消、超时和异常退出不能误报成功；
9. 默认 CLI 输出继续兼容；
10. 凭据、OAuth、API Key、日志和缓存不进入 Vault 或 started 元数据。

## 2. 启动方式

开发态和阶段 1 Windows 验收：

```text
python scripts/vault_sync.py ... \
  --output-format jsonl \
  --protocol-version 1 \
  --request-id <uuid>
```

运行时覆盖：

```text
AI_SESSION_VAULT_PYTHON=<python executable>
AI_SESSION_VAULT_SIDECAR=<script or executable>
```

阶段 1 使用受控系统 Python；正式免 Python 的独立可执行 Sidecar 在阶段 4 产品化时完成。

## 3. 公共字段

每一行是一个完整 JSON 对象：

```json
{
  "protocol": "ai-session-vault-sidecar",
  "protocol_version": 1,
  "request_id": "req-123",
  "sequence": 1,
  "timestamp": "2026-07-24T00:00:00Z",
  "operation": "sync",
  "event": "started"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `protocol` | string | 是 | 固定 `ai-session-vault-sidecar` |
| `protocol_version` | integer | 是 | 当前为 `1` |
| `request_id` | string | 是 | 一次任务的稳定标识 |
| `sequence` | integer | 是 | 从 1 严格递增 |
| `timestamp` | string | 是 | UTC ISO-8601 |
| `operation` | string | 是 | `list-apps`、`inspect`、`layout`、`sync`、`verify`、`restore` |
| `event` | string | 是 | `started`、`progress`、`completed`、`failed` |
| `data` | object/array | 否 | 事件数据 |
| `error` | object | 否 | 仅 failed 使用 |

## 4. 生命周期

成功：

```text
started → progress* → completed
```

失败：

```text
started → progress* → failed
```

Rust 只有收到同一请求的 `completed` 才能判定成功。进程成功退出但没有终态，必须合成 `missing_terminal_event` 失败。

## 5. started

started 只报告非敏感调用元数据：

```json
{
  "event": "started",
  "data": {
    "app_id": "codex",
    "dry_run": true,
    "restore_scope": "session",
    "has_vault_root": true,
    "has_source_override": false,
    "has_restore_root": true,
    "has_session_id": true
  }
}
```

不在 started 中回显完整路径、环境变量或凭据。

## 6. progress

实际进度格式：

```json
{
  "event": "progress",
  "data": {
    "stage": "sessions",
    "message": "Processed session artifact 12 of 30",
    "current": 12,
    "total": 30,
    "details": {
      "native_session_id": "...",
      "collection": "sessions",
      "action": "copied"
    }
  }
}
```

字段：

- `stage`：稳定的机器可读阶段名；
- `message`：面向用户的简短状态；
- `current` / `total`：可选非负计数，`current <= total`；
- `details`：可选结构化细节，不得包含凭据。

当前 stage 包括：

```text
discover
inspect
layout
prepare
sessions
metadata
publish
verify
complete
restore-prepare
restore-verify
restore-plan
restore-copy
restore-indexes
restore-launchers
restore-publish
restore-complete
```

## 7. completed

completed 的 `data` 直接承载 Python Core 原有报告，避免第二套结果定义：

```json
{
  "event": "completed",
  "data": {
    "app_id": "codex",
    "sessions_copied": 10,
    "report_path": "D:/Vault/.../reports/sync-....json"
  }
}
```

重要结果字段示例：

- `machine_root`；
- `report_path`；
- `warnings`；
- `sessions_copied` / `sessions_skipped`；
- `metadata_updated` / `metadata_failed`；
- `ok`、`errors`、`details`；
- `sessions_restored`、`indexes_restored`；
- `database_rebuild_required`。

## 8. failed

Python 失败示例：

```json
{
  "event": "failed",
  "error": {
    "code": "SYNC_ERROR",
    "message": "--restore-root is required for restore",
    "retryable": false
  }
}
```

Python 端代码：

| 代码 | 含义 |
|---|---|
| `SYNC_ERROR` | 路径、Vault、校验或能力错误 |
| `INVALID_ARGUMENT` | 参数无效 |
| `CANCELLED` | Python 收到用户中断 |
| `INTERNAL_ERROR` | 未预期 Python 异常 |

Rust 进程层合成代码：

| 代码 | 含义 |
|---|---|
| `protocol_error` | JSON、协议、版本、请求、operation 或 sequence 无效 |
| `missing_terminal_event` | 进程退出但没有 completed/failed |
| `process_exit` | Sidecar 非零退出且未发终态 |
| `process_wait_failed` | Rust 等待子进程失败 |
| `process_ended` | 子进程状态异常结束 |
| `timeout` | 超过任务允许时间 |
| `cancelled` | Rust 调用方取消并终止子进程 |

## 9. 取消与超时

- Rust 维护进程内任务注册表；
- 每个任务有 operation、request ID、开始时间和超时；
- 取消会设置标记并 kill 子进程；
- 超时会执行同样清理并合成 failed；
- 已发出 Python 终态时，Rust 不再生成第二个终态；
- kill 可能跳过 Python `finally`，因此 Vault Lock 会读取锁内 PID；PID 已不存在时下一次运行立即回收锁。

## 10. CLI 兼容

```text
--output-format pretty   默认，格式化最终 JSON
--output-format json     紧凑最终 JSON
--output-format jsonl    版本化生命周期事件
```

不传新参数时，现有 CLI 行为保持不变。

## 11. 安全规则

### 命令注入

- Rust 只使用程序名和参数数组；
- 不调用 `cmd /C`、PowerShell 字符串、`sh -c`；
- operation 和 restore scope 双侧验证；
- NUL 字符拒绝；
- Sidecar 路径不能由普通 UI 请求任意指定。

### 路径与写入

- Python Core 执行最终路径安全检查；
- restore 目录必须不存在，并与活动源和 Vault 隔离；
- UI 不直接写入厂商原生目录；
- sync 使用原子复制和原子 JSON 发布；
- SQLite 使用 Backup API 和 `PRAGMA quick_check`；
- Codex 恢复不发布旧 state SQLite。

### 输出验证

- Rust 验证协议、版本、request ID、operation、sequence；
- failed 必须有 error；
- 非 failed 不得带 error；
- 只有 completed 是成功；
- stderr 仅进入限量诊断 details，不作为结果解析。

### 敏感数据

- 既有 Adapter 排除规则继续生效；
- started 不回显实际参数值；
- UI 不保存环境变量值、auth、OAuth、API Key；
- 备份和恢复仍然能力门控。

## 12. 版本演进

- v1 字段只能向后兼容增加；
- 删除字段或改变含义必须升级版本；
- 版本不匹配立即失败；
- Python、Rust、TypeScript 共享协议常量和测试；
- `scripts/phase1_smoke.py` 验证真实完整生命周期。
