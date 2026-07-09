#!/usr/bin/env pwsh
<#
.SYNOPSIS
  将 weekly-report-migration 安装为「项目级」Cursor Skill（目录联接）。

.DESCRIPTION
  在目标业务项目的 .cursor/skills/weekly-report-migration/ 创建 junction，
  指向本 Skill 仓库根目录。不写入全局 ~/.cursor/skills/。

.EXAMPLE
  # 在业务项目根目录执行：
  pwsh -File d:\branch\skills\report-migration\scripts\workflow\install_project_skill.ps1

.EXAMPLE
  pwsh -File install_project_skill.ps1 -TargetProject D:\my-app -SkillSource d:\branch\skills\report-migration
#>
[CmdletBinding()]
param(
    [Parameter()]
    [string] $TargetProject = (Get-Location).Path,

    [Parameter()]
    [string] $SkillSource = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"

$skillsDir = Join-Path $TargetProject ".cursor\skills"
$dest = Join-Path $skillsDir "weekly-report-migration"

if (-not (Test-Path $SkillSource)) {
    Write-Error "Skill 源码目录不存在: $SkillSource"
}
if (-not (Test-Path (Join-Path $SkillSource "SKILL.md"))) {
    Write-Error "不是有效的 Skill 目录（缺少 SKILL.md）: $SkillSource"
}

New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null

if (Test-Path $dest) {
    $item = Get-Item $dest -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Remove-Item $dest -Force
    } else {
        Write-Error "已存在且不是联接目录，请手动处理: $dest"
    }
}

New-Item -ItemType Junction -Path $dest -Target $SkillSource | Out-Null

Write-Host "已安装项目级 Skill:" -ForegroundColor Green
Write-Host "  目标项目: $TargetProject"
Write-Host "  联接路径: $dest"
Write-Host "  指向源码: $SkillSource"
Write-Host ""
Write-Host "请重新打开该项目工作区，然后在对话中使用 /weekly-report-migration 或说「周报迁移」。"
