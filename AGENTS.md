# AI Session Vault 开发执行规则

## 阶段制开发

本项目共 5 个大阶段，编号 0–4。每个阶段是一个独立大任务包。

每次开始实际开发前，必须先向用户明确：

```text
阶段 X / 共 5 阶段：<阶段名称>
当前阶段完成后还剩 Y 个阶段
本次属于阶段 X 的第 N 个任务包
```

当前阶段及完成情况以 `docs/DEVELOPMENT_STAGE_STATUS.md` 为唯一状态源。

规则：

1. 当前阶段未满足 Definition of Done，不得进入下一阶段；
2. 不得把计划、脚本或未验证代码描述为已完成功能；
3. 每次开发结束后更新阶段台账；
4. 每个阶段使用一个 GitHub 大任务 Issue 跟踪；
5. 阶段内允许多个提交和子任务，但必须保持同一阶段目标；
6. Windows 专属功能必须在真实 Windows 环境验证后才能标记通过。

## 五阶段路线

0. 开源桌面底座导入与基线稳定；
1. 接入现有备份、校验和 Codex 恢复；
2. 健康检查、安全修复和会话管理增强；
3. 导出、跨电脑交接和 Vault 搜索增强；
4. 统一统计、AI 分析和产品化完善。

## GitHub Actions 禁令

未经用户单独明确授权，禁止：

- 创建或修改 `.github/workflows/`；
- 新增 GitHub Actions；
- 触发、重跑或启用 Workflow；
- 添加 `push`、`pull_request`、`schedule`、`cron` 或 `workflow_dispatch`；
- 使用 Actions 构建安装包或代替本地测试。

开发验证使用本地静态检查、本地单元测试和本地构建。

## 当前阶段

当前为阶段 0。详细任务、限制和验收标准见：

- `docs/DEVELOPMENT_STAGE_STATUS.md`
- `docs/PHASE_0_OPEN_SOURCE_BASELINE.md`
- GitHub Issue #2
