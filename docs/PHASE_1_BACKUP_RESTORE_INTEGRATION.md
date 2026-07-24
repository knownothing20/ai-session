# 阶段 1：接入现有备份、校验和 Codex 恢复

> 阶段：1 / 共 5 阶段  
> 本阶段完成后剩余：3 个阶段  
> 状态：待开始

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

## 主要交付物

- [ ] 定义 Sidecar JSONL 协议与 schema 版本；
- [ ] 为 `vault_sync.py` 增加适合桌面调用的机器可读输出；
- [ ] 生成 Windows 可执行 Sidecar 或确定 Python 运行时打包方式；
- [ ] Rust 侧实现 Sidecar 启动、参数校验、取消和超时；
- [ ] React 侧新增 Vault 设置与任务中心；
- [ ] UI 支持 inspect、layout、sync、verify；
- [ ] UI 支持 Codex session/full restore；
- [ ] UI 显示报告路径、警告、排除项和验证结果；
- [ ] 所有危险操作有确认和 dry-run；
- [ ] 完成本地 Python、Rust、前端和端到端测试；
- [ ] 更新阶段 1 验收报告。

## 建议任务顺序

1. 协议和威胁模型；
2. Python Core 结构化事件输出；
3. Rust Sidecar 桥接；
4. UI 设置与任务中心；
5. 备份和校验流程；
6. Codex 恢复流程；
7. 取消、重试和错误恢复；
8. 本地集成测试与阶段验收。

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
