# 阶段 1：Vault Core Sidecar 运行时策略

> 阶段：1 / 共 5 阶段  
> 当前阶段完成后剩余：3 个阶段  
> 决策：阶段 1 使用受控 Python 运行时；免 Python 的独立 Sidecar 打包放在阶段 4 产品化中完成。

## 1. 决策

阶段 1 的目标是验证桌面端与现有 Vault Core 的完整业务闭环，而不是提前完成安装器和自动更新发布体系。

当前运行方式：

```text
Tauri / Rust
  → python scripts/vault_sync.py
  → JSONL Protocol v1
```

要求：

- Windows 本地安装 Python 3.10 或更高版本；
- 默认命令为 `python`；
- 可通过 `AI_SESSION_VAULT_PYTHON` 指定解释器绝对路径；
- 可通过 `AI_SESSION_VAULT_SIDECAR` 指定替代脚本或未来独立可执行文件；
- Rust 只使用 `Command` 参数数组，不调用 shell；
- UI 启动前检测 Sidecar 入口与 Python 程序是否可用。

这满足阶段 1 交付物中的“Windows Sidecar 打包或 Python 运行时方案”。

## 2. 路径解析

开发态默认入口由 Rust 根据 `CARGO_MANIFEST_DIR` 解析：

```text
<repo>/scripts/vault_sync.py
```

覆盖优先级：

1. `AI_SESSION_VAULT_SIDECAR`；
2. 单仓库开发态 `scripts/vault_sync.py`。

Python 优先级：

1. `AI_SESSION_VAULT_PYTHON`；
2. PATH 中的 `python`。

## 3. 为什么阶段 1 不直接打包 PyInstaller

阶段 1 仍需要频繁修改：

- Adapter；
- JSONL 协议；
- 进度事件；
- 取消与超时行为；
- Codex 恢复规则；
- Windows 文件锁兼容性。

此时固定 PyInstaller、Tauri externalBin、代码签名和安装器路径会增加重复构建成本，并把阶段 4 的发布问题提前带入核心集成阶段。

## 4. 阶段 4 产品化目标

阶段 4 再完成：

- Python Core 独立可执行文件；
- Tauri `externalBin`；
- Windows 安装器随应用分发；
- 自有代码签名；
- 自有更新通道和更新公钥；
- 安装后无需系统 Python；
- Sidecar 版本与桌面版本兼容检查。

协议仍保持 `ai-session-vault-sidecar` v1 或后续兼容版本，因此阶段 1 UI 和 Rust 桥接不需要重写。

## 5. 阶段 1 验收

在 `D:\GitHub\ai-session` 执行：

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

验收时必须确认：

- Vault Core 状态显示可用；
- 应用列表可发现；
- inspect、layout、sync dry-run、sync、verify 可用；
- Codex session/full restore dry-run 与真实恢复可用；
- 任务进度实时更新；
- 取消任务后下一次同步不会被残留锁阻塞；
- 不存在 GitHub Actions Workflow。
