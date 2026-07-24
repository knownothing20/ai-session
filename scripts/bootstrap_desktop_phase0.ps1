[CmdletBinding()]
param(
    [Parameter()]
    [string]$Destination = (Join-Path (Get-Location) "ai-session-desktop"),

    [Parameter()]
    [string]$TargetRepoUrl = "",

    [Parameter()]
    [switch]$InstallDependencies,

    [Parameter()]
    [switch]$RunChecks,

    [Parameter()]
    [switch]$Launch,

    [Parameter()]
    [switch]$Push
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$UpstreamRepo = "https://github.com/jhlee0409/claude-code-history-viewer.git"
$UpstreamCommit = "2e29912c8743c997f203e903e6ae0054865cb8e3"
$PhaseBranch = "phase/0-open-source-baseline"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "缺少命令：$Name。请先安装阶段 0 文档要求的 Windows 开发环境。"
    }
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "命令失败（退出码 $LASTEXITCODE）：$FilePath $($Arguments -join ' ')"
    }
}

function Assert-NoWorkflows {
    $tracked = @(git ls-files ".github/workflows/*")
    if ($LASTEXITCODE -ne 0) {
        throw "无法检查 GitHub Workflow 文件。"
    }
    if ($tracked.Count -gt 0) {
        throw "检测到 GitHub Workflow，拒绝继续：$($tracked -join ', ')"
    }
    if (Test-Path ".github/workflows") {
        $remaining = @(Get-ChildItem ".github/workflows" -File -Recurse -ErrorAction SilentlyContinue)
        if ($remaining.Count -gt 0) {
            throw "工作区仍存在 .github/workflows 文件，拒绝继续。"
        }
    }
}

Require-Command "git"

$Destination = [System.IO.Path]::GetFullPath($Destination)
if (Test-Path $Destination) {
    $items = @(Get-ChildItem -LiteralPath $Destination -Force -ErrorAction SilentlyContinue)
    if ($items.Count -gt 0) {
        throw "目标目录已存在且非空：$Destination"
    }
}

Write-Step "克隆固定 CCHV 上游基线"
Invoke-Checked "git" @("clone", $UpstreamRepo, $Destination)
Set-Location $Destination

Write-Step "切换到固定提交 $UpstreamCommit"
Invoke-Checked "git" @("checkout", "--detach", $UpstreamCommit)
Invoke-Checked "git" @("switch", "-c", $PhaseBranch)

Write-Step "在第一次推送前移除所有 GitHub Actions Workflow"
if (Test-Path ".github/workflows") {
    Remove-Item ".github/workflows" -Recurse -Force
}
Assert-NoWorkflows

Write-Step "配置上游与目标远端"
$originUrl = (git remote get-url origin).Trim()
if ($originUrl -ne $UpstreamRepo) {
    Write-Warning "克隆远端与预期上游不同：$originUrl"
}
Invoke-Checked "git" @("remote", "rename", "origin", "upstream")

if (-not [string]::IsNullOrWhiteSpace($TargetRepoUrl)) {
    Invoke-Checked "git" @("remote", "add", "origin", $TargetRepoUrl)
}

$upstreamNotice = @"
# Upstream

This desktop application is derived from:

- Repository: https://github.com/jhlee0409/claude-code-history-viewer
- Version baseline: v1.22.0
- Commit: $UpstreamCommit
- License: MIT

Local modifications must preserve the upstream MIT license and copyright notice.
GitHub Actions workflows are intentionally excluded from this development fork.
"@
Set-Content -LiteralPath "UPSTREAM.md" -Value $upstreamNotice -Encoding UTF8

$thirdPartyNotice = @"
# Third-Party Notices

## Claude Code History Viewer

AI Session Vault Desktop is derived from Claude Code History Viewer.

- Copyright (c) 2025 JaeHyeok Lee
- Source: https://github.com/jhlee0409/claude-code-history-viewer
- License: MIT

The original LICENSE file and copyright notice must remain included.
Additional dependencies retain their respective licenses.
"@
Set-Content -LiteralPath "THIRD_PARTY_NOTICES.md" -Value $thirdPartyNotice -Encoding UTF8

Write-Step "创建本地无 Actions 基线提交"
Invoke-Checked "git" @("add", "-A")
$hasChanges = -not [string]::IsNullOrWhiteSpace((git status --porcelain))
if ($hasChanges) {
    Invoke-Checked "git" @("commit", "-m", "Import CCHV baseline without GitHub Actions")
}
Assert-NoWorkflows

if ($InstallDependencies -or $RunChecks -or $Launch) {
    Require-Command "node"
    Require-Command "corepack"
    Require-Command "cargo"
    Require-Command "rustc"

    Write-Step "启用 Corepack 并安装依赖"
    Invoke-Checked "corepack" @("enable")
    Invoke-Checked "corepack" @("pnpm", "install", "--frozen-lockfile")
}

if ($RunChecks) {
    Write-Step "执行前端本地构建"
    Invoke-Checked "corepack" @("pnpm", "build")

    Write-Step "执行 Rust/Tauri 本地静态编译检查"
    Invoke-Checked "cargo" @("check", "--manifest-path", "src-tauri/Cargo.toml")
}

if ($Push) {
    if ([string]::IsNullOrWhiteSpace($TargetRepoUrl)) {
        throw "使用 -Push 时必须同时提供 -TargetRepoUrl。"
    }
    Assert-NoWorkflows
    Write-Step "显式推送阶段 0 分支（仓库中无 Workflow）"
    Invoke-Checked "git" @("push", "-u", "origin", $PhaseBranch)
}

if ($Launch) {
    Write-Step "启动 Tauri 本地开发窗口"
    Invoke-Checked "corepack" @("pnpm", "tauri", "dev")
}

Write-Host "`n阶段 0 本地引导完成。" -ForegroundColor Green
Write-Host "目录：$Destination"
Write-Host "分支：$PhaseBranch"
Write-Host "上游提交：$UpstreamCommit"
Write-Host "当前阶段完成后还剩 4 个阶段。"
Write-Host "注意：只有 Windows pnpm build、cargo check、tauri dev 全部通过并保存验收报告后，阶段 0 才算完成。"
