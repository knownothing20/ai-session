# 阶段 1 验收报告

> 阶段：1 / 共 5 阶段  
> 阶段 1 完成后剩余：3 个阶段  
> 当前状态：**线上实现进行中，本地验收待执行**

## 1. 实现范围

- [x] Sidecar JSONL Protocol v1；
- [x] Python CLI 兼容输出与 started/progress/completed/failed；
- [x] 扫描、复制、SQLite 快照、校验和恢复进度；
- [x] Rust 参数验证和无 shell 命令构造；
- [x] Rust 子进程启动、JSONL 解析、取消、超时和异常清理；
- [x] Tauri 主 handler 注册；
- [x] Vault 设置和任务控制台；
- [x] 应用发现、inspect、layout、sync dry-run、sync、verify；
- [x] Codex 单会话/整库恢复预演和真实恢复；
- [x] 结果、错误、事件和报告位置展示；
- [x] 五种语言资源；
- [x] Windows SQLite 文件锁与路径兼容修复；
- [x] Sidecar 端到端冒烟脚本；
- [x] Windows 一键验证脚本；
- [x] 未创建或触发 GitHub Actions。

## 2. 运行时方案

阶段 1 使用系统 Python 运行时：

- 默认解释器：`python`；
- 覆盖解释器：`AI_SESSION_VAULT_PYTHON`；
- 覆盖 Sidecar：`AI_SESSION_VAULT_SIDECAR`；
- 正式免 Python 可执行 Sidecar 在阶段 4 产品化时完成。

详见 `docs/PHASE_1_RUNTIME_STRATEGY.md`。

## 3. 自动验证

在 Windows 仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1
```

自动检查项目：

| 检查 | 状态 |
|---|---|
| 当前分支 | 待执行 |
| 无 GitHub Workflow | 待执行 |
| Python compileall | 待执行 |
| Python 全量 unittest | 待执行 |
| Sidecar 端到端冒烟 | 待执行 |
| pnpm install | 待执行 |
| i18n validate | 待执行 |
| i18n 类型生成 | 待执行 |
| Vault 前端定向测试 | 待执行 |
| pnpm build | 待执行 |
| cargo fmt --check | 待执行 |
| cargo test vault_sidecar | 待执行 |
| cargo check | 待执行 |

机器可读结果写入：

```text
docs/PHASE_1_LOCAL_VALIDATION.json
```

## 4. 人工桌面验收

执行：

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

在桌面应用中进入：

```text
设置 → 会话保险箱
```

验收矩阵：

| 操作 | 预期 | 状态 |
|---|---|---|
| Vault Core 状态 | 显示可用 | 待确认 |
| 应用发现 | 显示 v0.3 支持应用 | 待确认 |
| inspect | 显示源目录、会话数和排除项 | 待确认 |
| layout | 显示计划 Vault 路径 | 待确认 |
| backup dry-run | 不写文件，显示计划报告 | 待确认 |
| backup | 增量写入并显示进度和报告 | 待确认 |
| verify | 哈希与 SQLite quick_check 通过 | 待确认 |
| 取消 | 任务终止，不误报成功 | 待确认 |
| 取消后重试 | 残留锁自动回收 | 待确认 |
| Codex session dry-run | 不创建恢复目录 | 待确认 |
| Codex session restore | 隔离恢复单会话 | 待确认 |
| Codex full restore | 隔离恢复整库 | 待确认 |
| 恢复安全 | 不恢复 auth 和旧 SQLite | 待确认 |

## 5. Definition of Done

阶段 1 只有在以下全部满足后才能标记完成：

- [ ] 自动验证全部通过；
- [ ] 人工桌面验收全部通过；
- [ ] 本报告填写实际 Windows、Python、Node、pnpm、Rust 版本；
- [ ] 失败、取消和超时没有被误判为成功；
- [ ] 凭据、OAuth、日志和缓存仍然被排除；
- [ ] PR、Issue #3 和阶段状态台账同步；
- [ ] 未使用 GitHub Actions。

## 6. 实际验收环境

- Windows：待填写
- Python：待填写
- Node：待填写
- pnpm：待填写
- rustc：待填写
- cargo：待填写
- 分支：`agent/modular-adapters-v0.2`
- 提交：待填写
- 是否允许进入阶段 2：**否，等待本地验收**
