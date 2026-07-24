# AI Session Vault Desktop

本目录用于导入并维护基于 Claude Code History Viewer 的 Tauri/React/Rust 桌面端。

当前状态：阶段 0 进行中，完整上游源码尚未导入。

固定上游：

- Repository: `jhlee0409/claude-code-history-viewer`
- Version: `v1.22.0`
- Commit: `2e29912c8743c997f203e903e6ae0054865cb8e3`
- License: MIT

在 Windows 的仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\bootstrap_desktop_phase0.ps1 `
  -InstallDependencies `
  -RunChecks
```

该脚本会用固定上游源码替换本占位目录，并确保导入内容不包含 GitHub Actions Workflow。
