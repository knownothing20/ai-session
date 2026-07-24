[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$ValidationPath = Join-Path $RepoRoot "docs\PHASE_1_LOCAL_VALIDATION.json"
$GeneratedTypesPath = Join-Path $RepoRoot "desktop\src\i18n\types.generated.ts"
$ExpectedBranch = "agent/modular-adapters-v0.2"
$AllowedPaths = @(
    "docs/PHASE_1_LOCAL_VALIDATION.json",
    "desktop/src/i18n/types.generated.ts"
)

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "缺少命令：$Name"
    }
}

function Invoke-Git {
    param([string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git 命令失败：git $($Arguments -join ' ')"
    }
}

Set-Location $RepoRoot
Require-Command "git"

$branch = (& git branch --show-current).Trim()
if ($branch -ne $ExpectedBranch) {
    throw "当前分支为 $branch，必须使用 $ExpectedBranch"
}

if (-not (Test-Path -LiteralPath $ValidationPath -PathType Leaf)) {
    throw "缺少阶段 1 本地验证结果：$ValidationPath"
}
if (-not (Test-Path -LiteralPath $GeneratedTypesPath -PathType Leaf)) {
    throw "缺少生成的 i18n 类型文件：$GeneratedTypesPath"
}

try {
    $validation = Get-Content -LiteralPath $ValidationPath -Raw -Encoding UTF8 | ConvertFrom-Json
}
catch {
    throw "无法解析阶段 1 验证结果：$($_.Exception.Message)"
}

if ($validation.stage -ne 1) {
    throw "验证报告阶段错误：$($validation.stage)"
}
if ($validation.status -ne "passed-complete") {
    throw "阶段 1 尚未完整通过，status=$($validation.status)"
}
if ($validation.ui_accepted -ne $true) {
    throw "阶段 1 人工桌面验收尚未确认"
}
if ($validation.github_actions_used -ne $false) {
    throw "验证报告显示使用了 GitHub Actions，拒绝发布"
}
if ($validation.branch -ne $ExpectedBranch) {
    throw "验证报告分支不匹配：$($validation.branch)"
}

$workflowFiles = @(& git ls-files ".github/workflows/*" "desktop/.github/workflows/*")
if ($workflowFiles.Count -gt 0) {
    throw "检测到禁止的 Workflow：$($workflowFiles -join ', ')"
}

$statusLines = @(& git status --porcelain=v1)
$changedPaths = @(
    foreach ($line in $statusLines) {
        if ($line.Length -lt 4) { continue }
        $path = $line.Substring(3).Trim()
        if ($path -match " -> ") {
            $path = ($path -split " -> ")[-1].Trim()
        }
        $path.Replace("\", "/")
    }
)
$unexpected = @($changedPaths | Where-Object { $_ -notin $AllowedPaths })
if ($unexpected.Count -gt 0) {
    throw "存在不属于阶段 1 验收结果的工作区修改，拒绝自动提交：$($unexpected -join ', ')"
}

Invoke-Git @("add", "--", $AllowedPaths[0], $AllowedPaths[1])
$staged = @(& git diff --cached --name-only)
if ($staged.Count -eq 0) {
    Write-Host "阶段 1 验收结果已在远端，无需重复提交。" -ForegroundColor Yellow
    exit 0
}
$unexpectedStaged = @($staged | Where-Object { $_ -notin $AllowedPaths })
if ($unexpectedStaged.Count -gt 0) {
    Invoke-Git @("reset", "--", $AllowedPaths[0], $AllowedPaths[1])
    throw "暂存区包含未授权文件：$($unexpectedStaged -join ', ')"
}

Invoke-Git @("commit", "-m", "Record phase 1 Windows acceptance")
Invoke-Git @("push", "origin", $ExpectedBranch)

Write-Host "`n阶段 1 Windows 验收结果已安全推送。" -ForegroundColor Green
Write-Host "下一步由线上开发助手读取验证 JSON、更新验收报告、关闭 Issue #3，并确认是否进入阶段 2。" -ForegroundColor Cyan
