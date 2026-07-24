[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$ValidationScript = Join-Path $PSScriptRoot "validate_phase1.ps1"
$PublishScript = Join-Path $PSScriptRoot "publish_phase1_validation.ps1"
$ValidationPath = Join-Path $RepoRoot "docs\PHASE_1_LOCAL_VALIDATION.json"

Set-Location $RepoRoot

Write-Host "阶段 1 / 共 5 阶段：接入现有备份、校验和 Codex 恢复" -ForegroundColor Cyan
Write-Host "当前阶段完成后还剩 3 个阶段。" -ForegroundColor Cyan
Write-Host "本脚本会运行自动检查、启动 Tauri、要求明确人工验收，并只在全部通过后安全推送结果。" -ForegroundColor Yellow

& powershell -NoProfile -ExecutionPolicy Bypass -File $ValidationScript -Launch
if ($LASTEXITCODE -ne 0) {
    throw "阶段 1 验证脚本失败，未发布任何验收结果。"
}

if (-not (Test-Path -LiteralPath $ValidationPath -PathType Leaf)) {
    throw "阶段 1 验证未生成结果文件：$ValidationPath"
}

$validation = Get-Content -LiteralPath $ValidationPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($validation.status -ne "passed-complete" -or $validation.ui_accepted -ne $true) {
    throw "阶段 1 尚未完整通过：status=$($validation.status), ui_accepted=$($validation.ui_accepted)"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $PublishScript
if ($LASTEXITCODE -ne 0) {
    throw "阶段 1 验收已通过，但安全发布脚本失败。请保留工作区并检查错误。"
}

Write-Host "`n阶段 1 验收结果已推送到 agent/modular-adapters-v0.2。" -ForegroundColor Green
Write-Host "线上开发助手将读取结果、更新验收报告、关闭 Issue #3，然后进入阶段 2。" -ForegroundColor Cyan
