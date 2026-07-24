[CmdletBinding()]
param(
    [Parameter()]
    [switch]$Launch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$DesktopRoot = Join-Path $RepoRoot "desktop"
$ReportPath = Join-Path $RepoRoot "docs\PHASE_1_LOCAL_VALIDATION.json"
$Results = [System.Collections.Generic.List[object]]::new()
$UiAccepted = $false

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "缺少命令：$Name"
    }
}

function Invoke-External {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "命令失败（退出码 $LASTEXITCODE）：$FilePath $($Arguments -join ' ')"
    }
}

function Read-Version {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )
    try {
        $output = (& $FilePath @Arguments 2>&1 | Select-Object -First 1)
        return [string]$output
    }
    catch {
        return "unavailable: $($_.Exception.Message)"
    }
}

function Invoke-ValidationStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Step $Name
    $started = Get-Date
    try {
        & $Action
        $Results.Add([ordered]@{
            name = $Name
            status = "passed"
            seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
            error = $null
        })
    }
    catch {
        $Results.Add([ordered]@{
            name = $Name
            status = "failed"
            seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
            error = $_.Exception.Message
        })
        throw
    }
}

function Write-Report {
    param([string]$OverallStatus)
    $branch = (& git branch --show-current).Trim()
    $head = (& git rev-parse HEAD).Trim()
    $payload = [ordered]@{
        schema_version = 1
        stage = 1
        status = $OverallStatus
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        repository = $RepoRoot
        branch = $branch
        head = $head
        environment = [ordered]@{
            windows = [System.Environment]::OSVersion.VersionString
            powershell = $PSVersionTable.PSVersion.ToString()
            git = Read-Version "git" @("--version")
            python = Read-Version "python" @("--version")
            node = Read-Version "node" @("--version")
            pnpm = Read-Version "corepack" @("pnpm", "--version")
            rustc = Read-Version "rustc" @("--version")
            cargo = Read-Version "cargo" @("--version")
        }
        results = $Results
        launch_requested = [bool]$Launch
        ui_accepted = $UiAccepted
        github_actions_used = $false
    }
    $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
    Write-Host "`n本地验证报告：$ReportPath" -ForegroundColor Yellow
}

Set-Location $RepoRoot
Require-Command "git"
Require-Command "python"
Require-Command "node"
Require-Command "corepack"
Require-Command "cargo"
Require-Command "rustc"

$overall = "failed"
try {
    Invoke-ValidationStep "确认开发分支" {
        $branch = (& git branch --show-current).Trim()
        if ($branch -ne "agent/modular-adapters-v0.2") {
            throw "当前分支为 $branch，必须使用 agent/modular-adapters-v0.2"
        }
        $porcelain = @(& git status --porcelain)
        if ($porcelain.Count -gt 0) {
            Write-Warning "工作区存在未提交修改；验证会继续，但报告会保留当前 HEAD。"
        }
    }

    Invoke-ValidationStep "确认不存在 GitHub Actions Workflow" {
        $tracked = @(& git ls-files ".github/workflows/*" "desktop/.github/workflows/*")
        if ($tracked.Count -gt 0) {
            throw "检测到禁止的 Workflow：$($tracked -join ', ')"
        }
        $physical = @(
            Get-ChildItem (Join-Path $RepoRoot ".github\workflows") -File -Recurse -ErrorAction SilentlyContinue
            Get-ChildItem (Join-Path $DesktopRoot ".github\workflows") -File -Recurse -ErrorAction SilentlyContinue
        )
        if ($physical.Count -gt 0) {
            throw "工作区存在禁止的 Workflow 文件。"
        }
    }

    Invoke-ValidationStep "Python 语法编译" {
        Invoke-External "python" @("-m", "compileall", "-q", "scripts", "tests")
    }

    Invoke-ValidationStep "Python 全量单元测试" {
        Invoke-External "python" @("-m", "unittest", "discover", "-s", "tests", "-v")
    }

    Invoke-ValidationStep "阶段 1 Sidecar 端到端冒烟" {
        Invoke-External "python" @("scripts/phase1_smoke.py")
    }

    Push-Location $DesktopRoot
    try {
        Invoke-ValidationStep "安装前端依赖" {
            Invoke-External "corepack" @("pnpm", "install", "--frozen-lockfile")
        }

        Invoke-ValidationStep "翻译完整性校验" {
            Invoke-External "corepack" @("pnpm", "i18n:validate")
        }

        Invoke-ValidationStep "生成翻译类型" {
            Invoke-External "corepack" @("pnpm", "generate:i18n-types")
        }

        Invoke-ValidationStep "Vault 前端定向测试" {
            Invoke-External "corepack" @(
                "pnpm", "exec", "vitest", "run",
                "src/test/vaultSidecarApi.test.ts",
                "src/test/VaultConsoleModal.test.tsx"
            )
        }

        Invoke-ValidationStep "前端 TypeScript 与 Vite 构建" {
            Invoke-External "corepack" @("pnpm", "build")
        }

        Invoke-ValidationStep "Rust 格式检查" {
            Invoke-External "cargo" @(
                "fmt", "--manifest-path", "src-tauri/Cargo.toml", "--", "--check"
            )
        }

        Invoke-ValidationStep "Rust Vault Sidecar 单元测试" {
            Invoke-External "cargo" @(
                "test", "--manifest-path", "src-tauri/Cargo.toml", "vault_sidecar"
            )
        }

        Invoke-ValidationStep "Rust/Tauri 静态编译检查" {
            Invoke-External "cargo" @(
                "check", "--manifest-path", "src-tauri/Cargo.toml"
            )
        }

        if ($Launch) {
            Invoke-ValidationStep "启动 Tauri 进行人工 UI 验收" {
                Write-Host "请在窗口中打开：设置 → 会话保险箱。" -ForegroundColor Yellow
                Write-Host "依次验证应用发现、检查、目录预览、备份预演、真实备份、校验、取消后重试、Codex 单会话和整库恢复。" -ForegroundColor Yellow
                Write-Host "完成后关闭 Tauri 窗口，脚本会要求明确确认。" -ForegroundColor Yellow
                Invoke-External "corepack" @("pnpm", "tauri", "dev")
                $confirmation = Read-Host "全部人工验收项是否真实通过？输入 YES 确认"
                if ($confirmation -cne "YES") {
                    throw "人工桌面验收未确认通过"
                }
                $script:UiAccepted = $true
            }
        }
    }
    finally {
        Pop-Location
    }

    $overall = if ($Launch -and $UiAccepted) {
        "passed-complete"
    }
    elseif ($Launch) {
        "failed-ui-acceptance"
    }
    else {
        "passed-automated"
    }
}
finally {
    Write-Report $overall
}

Write-Host "`n阶段 1 验证结果：$overall" -ForegroundColor Green
if (-not $Launch) {
    Write-Host "阶段 1 尚未完成：还需再次使用 -Launch，并明确输入 YES 确认完整 Vault 控制台流程。" -ForegroundColor Yellow
}
