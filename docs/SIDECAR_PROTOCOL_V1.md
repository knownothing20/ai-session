# AI Session Vault Sidecar Protocol v1

> 阶段：1 / 共 5 阶段  
> 用途：桌面 Tauri/Rust 与 Python Vault Core 之间的本地进程协议  
> 当前版本：1

## 1. 设计目标

Sidecar 协议用于让桌面程序安全调用现有 Python Vault Core，而不是在 Rust 中重新实现备份、校验和恢复逻辑。

核心原则：

1. Python Core 仍是 `inspect`、`layout`、`sync`、`verify` 和 `restore` 的唯一事实源；
2. Rust 使用参数数组启动进程，不拼接 shell 命令；
3. stdout 只输出一行一个 JSON 事件；
4. stderr 只用于诊断日志，不作为业务结果来源；
5. 每个请求有唯一 `request_id`；
6. 事件带递增 `sequence`；
7. 未知协议版本必须拒绝；
8. 失败必须以 `failed` 事件结束，不能把部分输出误判为成功；
9. 默认 CLI 输出继续兼容现有用户和脚本；
10. 不传递、输出或恢复凭据、OAuth、API Key、日志和缓存。

## 2. 启动方式

当前开发态入口：

```text
python scripts/vault_sync.py ... --output-format jsonl --protocol-version 1
```

推荐参数：

```text
--request-id <uuid>
--output-format jsonl
--protocol-version 1
```

正式安装包中的 Python 运行时或独立可执行 Sidecar 在阶段 1 后续任务中确定。无论打包形式如何，协议保持一致。

## 3. 事件公共字段

每一行都是一个完整 JSON 对象：

```json
{
  "protocol": "ai-session-vault-sidecar",
  "protocol_version": 1,
  "request_id": "a caller supplied UUID",
  "sequence": 1,
  "timestamp": "2026-07-24T00:00:00Z",
  "operation": "sync",
  "event": "started"
}
```

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `protocol` | string | 是 | 固定为 `ai-session-vault-sidecar` |
| `protocol_version` | integer | 是 | 当前为 `1` |
| `request_id` | string | 是 | 一次任务的稳定标识 |
| `sequence` | integer | 是 | 从 1 开始递增 |
| `timestamp` | string | 是 | UTC ISO-8601 |
| `operation` | string | 是 | `list-apps`、`inspect`、`layout`、`sync`、`verify` 或 `restore` |
| `event` | string | 是 | `started`、`progress`、`completed` 或 `failed` |
| `data` | object/array | 否 | 事件数据 |
| `error` | object | 否 | 仅 `failed` 使用 |

## 4. 生命周期

成功任务：

```text
started
→ progress（零个或多个）
→ completed
```

失败任务：

```text
started
→ progress（零个或多个）
→ failed
```

Rust 端只有收到同一 `request_id` 的终态事件后，才可以把任务标记为完成或失败。

进程退出但没有终态事件时，任务状态必须是 `protocol_error`，不能推测成功。

## 5. started

示例：

```json
{
  "protocol": "ai-session-vault-sidecar",
  "protocol_version": 1,
  "request_id": "req-123",
  "sequence": 1,
  "timestamp": "2026-07-24T00:00:00Z",
  "operation": "restore",
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

started 事件只报告非敏感调用元数据。路径和实际结果在完成报告中按已有 Core 结构返回。

## 6. progress

协议已经预留进度事件：

```json
{
  "protocol": "ai-session-vault-sidecar",
  "protocol_version": 1,
  "request_id": "req-123",
  "sequence": 2,
  "timestamp": "2026-07-24T00:00:01Z",
  "operation": "sync",
  "event": "progress",
  "data": {
    "phase": "sessions",
    "current": 12,
    "total": 30,
    "message": "Copying session artifacts"
  }
}
```

阶段 1 后续任务会把 Core 的扫描、复制、快照、校验和恢复步骤连接到 progress 事件。

## 7. completed

completed 的 `data` 直接承载当前 Python Core 返回的结构化报告，避免维护第二套结果定义。

```json
{
  "protocol": "ai-session-vault-sidecar",
  "protocol_version": 1,
  "request_id": "req-123",
  "sequence": 2,
  "timestamp": "2026-07-24T00:00:02Z",
  "operation": "list-apps",
  "event": "completed",
  "data": {
    "adapters": []
  }
}
```

## 8. failed

```json
{
  "protocol": "ai-session-vault-sidecar",
  "protocol_version": 1,
  "request_id": "req-123",
  "sequence": 2,
  "timestamp": "2026-07-24T00:00:01Z",
  "operation": "restore",
  "event": "failed",
  "error": {
    "code": "SYNC_ERROR",
    "message": "--restore-root is required for restore",
    "retryable": false
  }
}
```

v1 错误代码：

| 代码 | 含义 |
|---|---|
| `SYNC_ERROR` | Core 预期内的路径、Vault、校验或能力错误 |
| `INVALID_ARGUMENT` | 调用参数或值无效 |
| `CANCELLED` | 调用方取消或用户中断 |
| `INTERNAL_ERROR` | 未预期的程序异常 |
| `PROTOCOL_ERROR` | 由 Rust 端生成：输出无法解析、版本错误或缺少终态 |
| `PROCESS_ERROR` | 由 Rust 端生成：Sidecar 无法启动或异常退出 |
| `TIMEOUT` | 由 Rust 端生成：任务超过允许时间 |

## 9. CLI 兼容性

现有默认行为不变：

```text
python scripts/vault_sync.py --mode list-apps
```

仍输出格式化 JSON。

其他格式：

```text
--output-format pretty   默认，格式化最终 JSON
--output-format json     紧凑最终 JSON
--output-format jsonl    版本化生命周期事件
```

## 10. 威胁模型与安全规则

### 10.1 命令注入

- Rust 必须使用 `Command::args` 传递数组；
- 禁止通过 `cmd /C`、PowerShell 字符串或 shell 拼接运行；
- operation、scope 等枚举在 Rust 和 Python 两侧验证；
- 含 NUL 的字符串必须拒绝。

### 10.2 路径风险

- UI 选择路径后仍由 Python Core 执行最终安全检查；
- restore 目标必须不存在并与源目录、Vault 目录隔离；
- UI 不直接写入厂商会话目录；
- 不允许从前端传入任意 Python 模块或脚本路径。

### 10.3 输出欺骗

- Rust 验证协议名和版本；
- Rust 验证 request ID、sequence 单调递增和 operation 一致；
- 只有 `completed` 是成功；
- 非零退出码、解析错误、缺少终态都不能标记成功；
- stderr 不作为 JSON 结果解析。

### 10.4 敏感数据

- started 只报告是否提供某类参数，不回显凭据；
- Vault Core 的既有排除列表继续生效；
- UI 日志不保存 auth、OAuth、API Key 或环境变量值；
- 失败信息展示前需要长度限制和路径最小暴露策略。

## 11. 版本演进

- v1 发布后字段只能向后兼容地增加；
- 改变字段含义或删除字段必须升级协议版本；
- Rust 和 Python 各自声明支持版本集合；
- 版本不匹配时立即失败，不自动降级到非结构化输出；
- 协议 fixture 需要同时由 Python 与 Rust 测试读取。
