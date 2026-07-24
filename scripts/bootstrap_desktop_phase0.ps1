[CmdletBinding()]
param(
    [Parameter()]
    [string]$RepositoryRoot = "",

    [Parameter()]
    [switch]$InstallDependencies,

    [Parameter()]
    [switch]$RunChecks,

    [Parameter()]
    [switch]$Launch,

    [Parameter()]
    [switch]$ForceReimport,

    [Parameter()]
    [switch]$Commit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$UpstreamRepo = "https://github.com/jhlee0409/claude-code-history-viewer.git"
$UpstreamVersion = "v1.22.0"
$UpstreamCommit = "2e29912c8743c997f203e903e6ae0054865cb8e3"
$DesktopFolderName = "desktop"

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
        [string[]]$Arguments,
        [string]$WorkingDirectory = ""
    )

    $previous = Get-Location
    try {
        if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
            Set-Location $WorkingDirectory
        }
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "命令失败（退出码 $LASTEXITCODE）：$FilePath $($Arguments -join ' ')"
        }
    }
    finally {
        Set-Location $previous
    }
}

function Assert-NoWorkflows {
    param([string]$Root)

    $workflowRoots = @(
        (Join-Path $Root ".github\workflows"),
        (Join-Path $Root "desktop\.github\workflows")
    )

    foreach ($workflowRoot in $workflowRoots) {
        if (Test-Path $workflowRoot) {
            $remaining = @(Get-ChildItem $workflowRoot -File -Recurse -ErrorAction SilentlyContinue)
            if ($remaining.Count -gt 0) {
                throw "检测到 GitHub Workflow，拒绝继续：$($remaining.FullName -join ', ')"
            }
        }
    }

    $tracked = @(git -C $Root ls-files ".github/workflows/*" "desktop/.github/workflows/*")
    if ($LASTEXITCODE -ne 0) {
        throw "无法检查 GitHub Workflow 文件。"
    }
    if ($tracked.Count -gt 0) {
        throw "检测到已跟踪的 GitHub Workflow，拒绝继续：$($tracked -join ', ')"
    }
}

function Set-JsonProperty {
    param(
        [string]$Path,
        [scriptblock]$Mutator
    )

    $json = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    & $Mutator $json
    $json | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $Path -Encoding UTF8
}

Require-Command "git"

if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $RepositoryRoot = Split-Path -Parent $PSScriptRoot
}
$RepositoryRoot = [System.IO.Path]::GetFullPath($RepositoryRoot)

if (-not (Test-Path (Join-Path $RepositoryRoot ".git"))) {
    throw "不是 Git 仓库根目录：$RepositoryRoot"
}

$DesktopRoot = Join-Path $RepositoryRoot $DesktopFolderName
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-session-cchv-" + [Guid]::NewGuid().ToString("N"))

Write-Step "阶段 0 / 共 5 阶段：将固定 CCHV 基线导入当前仓库 desktop/"
Write-Host "当前阶段完成后还剩 4 个阶段。"

Assert-NoWorkflows -Root $RepositoryRoot

try {
    Write-Step "克隆固定上游到临时目录"
    Invoke-Checked "git" @("clone", "--filter=blob:none", "--no-tags", $UpstreamRepo, $TempRoot)
    Invoke-Checked "git" @("checkout", "--detach", $UpstreamCommit) $TempRoot

    $actualCommit = (git -C $TempRoot rev-parse HEAD).Trim()
    if ($actualCommit -ne $UpstreamCommit) {
        throw "上游提交不匹配：预期 $UpstreamCommit，实际 $actualCommit"
    }

    Write-Step "在导入前移除上游 GitHub Actions Workflow"
    $upstreamWorkflow = Join-Path $TempRoot ".github\workflows"
    if (Test-Path $upstreamWorkflow) {
        Remove-Item $upstreamWorkflow -Recurse -Force
    }
    if (Test-Path (Join-Path $TempRoot ".git")) {
        Remove-Item (Join-Path $TempRoot ".git") -Recurse -Force
    }

    if (Test-Path $DesktopRoot) {
        $existing = @(Get-ChildItem $DesktopRoot -Force -ErrorAction SilentlyContinue)
        $isPlaceholder = (-not (Test-Path (Join-Path $DesktopRoot "package.json"))) -and
            (Test-Path (Join-Path $DesktopRoot "UPSTREAM.lock.json"))

        if ($existing.Count -gt 0 -and -not $isPlaceholder -and -not $ForceReimport) {
            throw "desktop/ 已包含源码。重新导入请显式使用 -ForceReimport。"
        }
        Remove-Item $DesktopRoot -Recurse -Force
    }

    New-Item -ItemType Directory -Path $DesktopRoot -Force | Out-Null
    Get-ChildItem $TempRoot -Force | ForEach-Object {
        Copy-Item $_.FullName -Destination $DesktopRoot -Recurse -Force
    }

    Write-Step "写入上游锁定和第三方许可证声明"
    $lock = [ordered]@{
        repository = "jhlee0409/claude-code-history-viewer"
        source_url = "https://github.com/jhlee0409/claude-code-history-viewer"
        version = $UpstreamVersion
        commit = $UpstreamCommit
        license = "MIT"
        integration = "vendored-monorepo"
        imported_at_utc = [DateTime]::UtcNow.ToString("o")
    }
    $lock | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $DesktopRoot "UPSTREAM.lock.json") -Encoding UTF8

    $upstreamNotice = @"
# Upstream

The `desktop/` application is derived from Claude Code History Viewer.

- Repository: https://github.com/jhlee0409/claude-code-history-viewer
- Version baseline: $UpstreamVersion
- Commit: $UpstreamCommit
- License: MIT

The original MIT license and copyright notice are retained. GitHub Actions
workflows are intentionally excluded from this monorepo import.
"@
    Set-Content -LiteralPath (Join-Path $DesktopRoot "UPSTREAM.md") -Value $upstreamNotice -Encoding UTF8

    $thirdPartyNotice = @"
# Third-Party Notices

## Claude Code History Viewer

AI Session Vault Desktop is derived from Claude Code History Viewer.

- Copyright (c) 2025 JaeHyeok Lee
- Source: https://github.com/jhlee0409/claude-code-history-viewer
- License: MIT

The original `LICENSE` file and copyright notice remain included. Additional
dependencies retain their respective licenses.
"@
    Set-Content -LiteralPath (Join-Path $DesktopRoot "THIRD_PARTY_NOTICES.md") -Value $thirdPartyNotice -Encoding UTF8

    Write-Step "执行阶段 0 最小品牌替换"
    $packageJson = Join-Path $DesktopRoot "package.json"
    if (Test-Path $packageJson) {
        Set-JsonProperty -Path $packageJson -Mutator {
            param($json)
            $json.name = "ai-session-vault-desktop"
        }
    }

    $tauriConfig = Join-Path $DesktopRoot "src-tauri\tauri.conf.json"
    if (Test-Path $tauriConfig) {
        Set-JsonProperty -Path $tauriConfig -Mutator {
            param($json)
            $json.productName = "AI Session Vault"
            $json.identifier = "com.aisession.vault"
        }
    }

    foreach ($relativePath in @("src-tauri\Cargo.toml", "src-tauri\Cargo.lock")) {
        $path = Join-Path $DesktopRoot $relativePath
        if (Test-Path $path) {
            $text = Get-Content -LiteralPath $path -Raw
            $text = $text -replace 'name = "claude-code-history-viewer"', 'name = "ai-session-vault-desktop"'
            Set-Content -LiteralPath $path -Value $text -Encoding UTF8
        }
    }

    $indexHtml = Join-Path $DesktopRoot "index.html"
    if (Test-Path $indexHtml) {
        $text = Get-Content -LiteralPath $indexHtml -Raw
        $text = $text -replace "Claude Code History Viewer", "AI Session Vault"
        Set-Content -LiteralPath $indexHtml -Value $text -Encoding UTF8
    }

    Assert-NoWorkflows -Root $RepositoryRoot

    if ($InstallDependencies -or $RunChecks -or $Launch) {
        Require-Command "node"
        Require-Command "corepack"
        Require-Command "cargo"
        Require-Command "rustc"

        Write-Step "安装桌面端依赖"
        Invoke-Checked "corepack" @("enable") $DesktopRoot
        Invoke-Checked "corepack" @("pnpm", "install", "--frozen-lockfile") $DesktopRoot
    }

    if ($RunChecks) {
        Write-Step "执行前端本地构建"
        Invoke-Checked "corepack" @("pnpm", "build") $DesktopRoot

        Write-Step "执行 Rust/Tauri 本地静态检查"
        Invoke-Checked "cargo" @("check", "--manifest-path", "src-tauri/Cargo.toml") $DesktopRoot
    }

    $reportDirectory = Join-Path $RepositoryRoot "docs\phase-reports"
    New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
    $reportPath = Join-Path $reportDirectory "PHASE_0_WINDOWS_REPORT.md"
    if (-not (Test-Path $reportPath)) {
        $report = @"
# 阶段 0 Windows 验收报告

- 仓库：knownothing20/ai-session
- 桌面目录：desktop/
- 上游版本：$UpstreamVersion
- 上游提交：$UpstreamCommit
- `.github/workflows/`：不存在
- Node 版本：待填写
- pnpm 版本：待填写
- rustc / cargo 版本：待填写
- `pnpm build`：待验证
- `cargo check --manifest-path src-tauri/Cargo.toml`：待验证
- `pnpm tauri dev`：待验证
- 应用窗口截图：待补充
- 已知问题：
- 是否允许进入阶段 1：否
"@
        Set-Content -LiteralPath $reportPath -Value $report -Encoding UTF8
    }

    if ($Commit) {
        Write-Step "创建阶段 0 单仓库导入提交"
        Invoke-Checked "git" @("add", "desktop", "docs/phase-reports/PHASE_0_WINDOWS_REPORT.md") $RepositoryRoot
        $changes = git -C $RepositoryRoot status --porcelain
        if (-not [string]::IsNullOrWhiteSpace(($changes -join "`n"))) {
            Invoke-Checked "git" @("commit", "-m", "Import CCHV desktop baseline into monorepo") $RepositoryRoot
        }
    }

    if ($Launch) {
        Write-Step "启动 Tauri 本地开发窗口"
        Invoke-Checked "corepack" @("pnpm", "tauri", "dev") $DesktopRoot
    }

    Write-Host "`n阶段 0 单仓库导入流程执行完成。" -ForegroundColor Green
    Write-Host "仓库：$RepositoryRoot"
    Write-Host "桌面目录：$DesktopRoot"
    Write-Host "上游提交：$UpstreamCommit"
    Write-Host "注意：只有 Windows build、cargo check、tauri dev 全部通过并更新验收报告后，阶段 0 才算完成。"
}
finally {
    if (Test-Path $TempRoot) {
        Remove-Item $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
