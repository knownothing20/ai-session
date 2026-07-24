# 阶段 1 本地完成流程

> 阶段：1 / 共 5 阶段  
> 阶段 1 完成后剩余：3 个阶段

阶段 1 的线上实现、测试代码、验收脚本和静态审计已经完成。真实 Windows 构建、Tauri 窗口与用户操作不能由线上环境代替。

## 一条命令完成本地验收与结果推送

在 Windows PowerShell 中执行：

```powershell
Set-Location "D:\GitHub\ai-session"
git pull --ff-only
powershell -ExecutionPolicy Bypass `
  -File .\scripts\complete_phase1.ps1
```

脚本依次执行：

1. 确认分支为 `agent/modular-adapters-v0.2`；
2. 确认根目录和 `desktop/` 均不存在 GitHub Workflow；
3. Python 语法编译与全量单元测试；
4. 完整 Sidecar 端到端冒烟；
5. pnpm 依赖、翻译校验和翻译类型生成；
6. Vault 前端 API 与控制台测试；
7. TypeScript/Vite 构建；
8. Rust 格式检查、Vault Sidecar 单元测试和 `cargo check`；
9. 启动 Tauri；
10. 人工完成“设置 → 会话保险箱”操作矩阵；
11. 关闭窗口后要求输入大写 `YES`；
12. 写入 `docs/PHASE_1_LOCAL_VALIDATION.json`；
13. 只允许暂存验证 JSON 和生成的 i18n 类型；
14. 检测到其他本地修改或 Workflow 时拒绝提交；
15. 提交并推送到 `agent/modular-adapters-v0.2`。

## 人工操作矩阵

至少确认：

- Vault Core 显示可用；
- 应用列表正常发现；
- inspect 与 layout 正常；
- backup dry-run 不写文件；
- real backup 成功并显示进度和报告；
- verify 成功；
- 破坏测试副本后 verify 显示失败而不是成功；
- 长任务可以取消；
- 取消后重新运行不会被残留锁阻塞；
- Codex 单会话 restore dry-run 不写目录；
- Codex 单会话恢复为隔离目录；
- Codex 整库隔离恢复成功；
- 恢复目录不包含 `auth.json` 或旧 state SQLite。

## 成功条件

生成的验证文件必须包含：

```json
{
  "stage": 1,
  "status": "passed-complete",
  "ui_accepted": true,
  "github_actions_used": false
}
```

完成推送后，线上助手仍需：

1. 读取验证 JSON；
2. 核对提交和分支；
3. 更新 `docs/PHASE_1_ACCEPTANCE_REPORT.md`；
4. 将 `docs/DEVELOPMENT_STAGE_STATUS.md` 切换为阶段 1 已完成；
5. 关闭 Issue #3；
6. 明确声明阶段 2 / 共 5 阶段、完成后还剩 2 个阶段；
7. 才能开始阶段 2。
