# 阶段 1 在线实现审计

> 阶段：1 / 共 5 阶段  
> 阶段 1 完成后剩余：3 个阶段  
> 审计结论：线上实现闭环已完成；真实 Windows 自动验证与人工桌面验收仍是完成阶段的必要条件。

## 1. 审计范围

基线：阶段 0 在线收尾提交 `f6ab54b716735b123348ca78bf54e6ba3f959e57`。

审计内容：

- Python Vault Core；
- JSONL Protocol v1；
- Rust Sidecar 进程桥；
- Tauri handler 注册；
- React Vault 控制台；
- 五种语言；
- Python、Rust、前端和端到端测试；
- Windows 一键验收；
- README、Skill、Issue、PR 和阶段文档。

## 2. 架构审计

结论：通过静态审计。

- Python Core 仍是备份、校验和恢复的唯一事实源；
- Rust 未复制文件同步或恢复业务规则；
- React 只通过 Tauri Command 调用 Rust；
- Rust 只通过参数数组调用 Sidecar，不使用 shell；
- CCHV 上游运行时独立保留为 `lib_upstream.rs`；
- `build.rs` 只在唯一 handler 锚点注入 5 个 Vault Command；
- 锚点不存在或出现多个时构建立即失败；
- 阶段 1 未加入 Doctor、Repair、Handoff 或 AI 分析。

## 3. 协议审计

结论：通过静态审计。

- 固定协议名 `ai-session-vault-sidecar`；
- 固定版本 1；
- request ID 绑定任务；
- sequence 严格递增；
- operation 双侧校验；
- started/progress/completed/failed 生命周期；
- failed 必须带 error；
- 非 failed 不得带 error；
- completed 是唯一成功终态；
- verify `ok: false` 使用 `VERIFY_FAILED`；
- 异常退出、协议错误、缺失终态、取消和超时均生成 failed；
- stderr 最多保留 64 KiB，并标记是否截断。

## 4. 进程与取消审计

结论：通过静态审计，等待 Windows 运行验证。

- Rust 维护进程内任务注册表；
- 同一 request ID 不允许并发复用；
- 子进程 stdout/stderr 被独立读取；
- 协议读取或解析失败会设置取消标记并 kill；
- 超时会 kill 并发出 timeout；
- UI 可取消运行任务；
- 任务终止后从注册表清理；
- Python Vault Lock 存储 PID；
- 被 kill 的 Sidecar 留下的锁，在 PID 已死亡时由下一次运行立即回收；
- 活跃 PID 的锁仍然拒绝并发写入。

## 5. 写入与恢复安全审计

结论：通过静态审计。

- 活动厂商目录保持只读；
- 写入操作有 dry-run 或预检；
- UI 对真实 sync 和 restore 二次确认；
- Vault 文件使用原子复制和原子 JSON 发布；
- SQLite 使用 Backup API；
- SQLite 句柄在 Windows 发布文件前显式关闭；
- 校验执行 SHA-256 与 `PRAGMA quick_check`；
- Codex 恢复目标必须不存在；
- 恢复目录与活动源、Vault 隔离；
- 恢复使用临时目录和原子发布；
- 不发布 auth、凭据或旧 state SQLite；
- 单个 archived session 恢复为 active session；
- 全库恢复保留原集合结构并生成启动脚本和报告。

## 6. 敏感数据审计

结论：通过静态审计与新增测试设计。

- Adapter 继续使用精确 include pattern；
- Codex 排除 `auth.json`、日志数据库和其他运行时文件；
- Gemini OAuth 文件不属于会话集合；
- started 只输出 `has_*` 布尔值，不回显路径；
- UI 不保存 auth、OAuth、API Key 或环境变量值；
- `tests/test_sensitive_exclusions.py` 创建带伪凭据的文件，并要求 Vault 完全不包含伪凭据字节。

## 7. UI 审计

结论：功能闭环已实现，等待真实窗口验收。

入口：

```text
设置 → 会话保险箱
```

覆盖：

- Sidecar 状态；
- 应用发现；
- Vault Root、machine ID、source override；
- inspect；
- layout；
- backup dry-run；
- real sync；
- verify；
- Codex session/full restore dry-run；
- Codex session/full real restore；
- 实时进度；
- 取消；
- 错误和报告；
- 命令参数预览；
- 五种语言。

仍需真实验证：

- 窗口布局；
- 所有按钮实际可点击；
- Tauri 事件实时刷新；
- 长任务取消；
- 取消后重试；
- 真机 Codex 会话路径；
- 恢复结果可由 Codex 启动脚本恢复。

## 8. 测试审计

已加入但尚未在当前在线环境执行：

- Python 全量测试；
- Sidecar 协议和 progress；
- verify failed 终态；
- 锁回收；
- 敏感排除；
- Windows SQLite；
- Codex restore；
- Tauri handler 注入；
- Rust Sidecar；
- 前端 API；
- Vault 控制台；
- Sidecar 全闭环冒烟；
- i18n 校验和类型生成；
- pnpm build；
- cargo fmt/test/check。

当前执行容器：

- 无法解析 `github.com`，不能拉取私有工作树；
- 没有 Rust 工具链；
- 不是 Windows；
- 无法显示 Tauri 窗口。

因此不能把静态审计描述为测试通过。

## 9. GitHub Actions 审计

结论：符合项目禁令。

- 差异中没有 `.github/workflows/`；
- 没有新增 Workflow；
- 没有触发、重跑或启用 Actions；
- `tests/test_no_github_actions.py` 把禁令加入本地测试；
- `scripts/validate_phase1.ps1` 同时检查 Git 索引和物理目录。

## 10. 唯一剩余验收

在真实 Windows checkout：

```powershell
Set-Location "D:\GitHub\ai-session"
git pull --ff-only
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

必须满足：

```text
docs/PHASE_1_LOCAL_VALIDATION.json
status = passed-complete
ui_accepted = true
```

本地验证会生成或更新 `desktop/src/i18n/types.generated.ts`；验证结果和生成文件需要提交并推送到当前分支，随后才能关闭 Issue #3、将阶段 1 标记完成并进入阶段 2。
