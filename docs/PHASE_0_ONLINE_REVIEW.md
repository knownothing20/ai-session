# 阶段 0 线上复核记录

- 复核分支：`agent/modular-adapters-v0.2`
- 本地验收报告：`docs/PHASE_0_ACCEPTANCE_REPORT.md`
- 完整桌面源码：已推送至 `desktop/`
- PR 变更文件：899 个（复核时）
- GitHub Workflow：根目录和 `desktop/` 均未发现 `.github/workflows/` 文件
- Tauri 产品名：`AI Session Vault`
- Tauri identifier：`com.aisession.vault`
- Rust 包名：`ai-session-vault-desktop`
- 上游版本锁定：CCHV v1.22.0 / `2e29912c8743c997f203e903e6ae0054865cb8e3`
- 上游 MIT License：已保留
- 第三方声明：已保留

## 线上复核修正

- 修复 `desktop/src-tauri/Cargo.toml` 的乱码描述；
- 将 Rust package repository 改为当前项目仓库；
- 暂时关闭继承自 CCHV 的自动更新源，避免派生应用误接收上游安装包；
- 停止生成 updater artifacts，待项目建立自己的签名和发布通道后再启用；
- 重写 Tauri 配置测试，使其匹配当前品牌、端口和禁用更新策略；
- 同步阶段台账、Issue 和 PR 状态。

## 验证边界

Windows 本地 `pnpm build`、`cargo check` 和 `pnpm tauri dev` 已在导入提交上通过。以上线上收尾修改仅涉及包元数据、Tauri 更新配置、对应配置测试和阶段文档；最新远端提交尚未在 Windows 再次执行完整本地构建，因此后续在本地重新拉取时应补跑：

```powershell
cd D:\GitHub\ai-session\desktop
corepack pnpm build
cargo check --manifest-path .\src-tauri\Cargo.toml
corepack pnpm test -- src-tauri/tests/tauriConfig.test.ts
```

该补充验证不阻止线上开始阶段 1 的协议与代码开发，但正式发布安装包前必须完成。
