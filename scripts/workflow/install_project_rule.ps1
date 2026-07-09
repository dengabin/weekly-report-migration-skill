#!/usr/bin/env pwsh
<#
.SYNOPSIS
  在业务项目安装「周报迁移指针 Rule」（不复制 Skill 本体）。

.EXAMPLE
  pwsh -File install_project_rule.ps1 -TargetProject D:\my-app -SkillRoot d:\branch\skills\report-migration
#>
[CmdletBinding()]
param(
    [string] $TargetProject = (Get-Location).Path,
    [string] $SkillRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string] $RuleName = "weekly-report-migration.mdc"
)

$ErrorActionPreference = "Stop"
$template = Join-Path $SkillRoot "templates\report-migration-pointer.mdc"
$rulesDir = Join-Path $TargetProject ".cursor\rules"
$dest = Join-Path $rulesDir $RuleName

if (-not (Test-Path $template)) { Write-Error "缺少模板: $template" }
if (-not (Test-Path (Join-Path $SkillRoot "SKILL.md"))) { Write-Error "无效的 SkillRoot: $SkillRoot" }

New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null
$content = Get-Content $template -Raw -Encoding UTF8
$content = $content.Replace("{{SKILL_ROOT}}", $SkillRoot.Replace("\", "/"))
Set-Content -Path $dest -Value $content -Encoding UTF8 -NoNewline

Write-Host "已安装指针 Rule:" -ForegroundColor Green
Write-Host "  $dest"
Write-Host "  SKILL_ROOT -> $SkillRoot"
Write-Host ""
Write-Host "在业务项目里说「周报迁移」或 @weekly-report-migration 即可。"
Write-Host "若需设置页 / 斜杠菜单出现 Skill，另见 install_project_skill.ps1。"
