#!/usr/bin/env pwsh
<#
.SYNOPSIS
  将周报迁移 Skill 配置到业务项目（默认：指针 Rule；可选：项目级 Skill 菜单）。

.PARAMETER SkillRoot
  用户粘贴的 Skill 目录（含 SKILL.md）。

.PARAMETER TargetProject
  业务项目根目录，默认当前目录。

.PARAMETER WithSkillMenu
  额外创建 .cursor/skills/weekly-report-migration junction（设置页与 / 菜单可见）。

.EXAMPLE
  pwsh -File install_to_project.ps1 -SkillRoot "d:\branch\skills\report-migration"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $SkillRoot,

    [string] $TargetProject = (Get-Location).Path,

    [switch] $WithSkillMenu
)

$ErrorActionPreference = "Stop"

function Resolve-FullPath([string]$p) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "路径不存在: $p"
    }
    return (Resolve-Path -LiteralPath $p).Path
}

$SkillRoot = Resolve-FullPath $SkillRoot
$TargetProject = Resolve-FullPath $TargetProject

if (-not (Test-Path (Join-Path $SkillRoot "SKILL.md"))) {
    throw "不是有效的 Skill 目录（缺少 SKILL.md）: $SkillRoot"
}

$ruleScript = Join-Path $SkillRoot "scripts\workflow\install_project_rule.ps1"
$skillScript = Join-Path $SkillRoot "scripts\workflow\install_project_skill.ps1"
if (-not (Test-Path $ruleScript)) {
    throw "缺少安装脚本: $ruleScript"
}

$report = [ordered]@{
    status           = "ok"
    skill_root       = $SkillRoot
    target_project   = $TargetProject
    rule_path        = Join-Path $TargetProject ".cursor\rules\weekly-report-migration.mdc"
    skill_menu_path  = $null
    with_skill_menu  = [bool]$WithSkillMenu
    errors           = @()
}

try {
    & $ruleScript -TargetProject $TargetProject -SkillRoot $SkillRoot
} catch {
    $report.status = "failed"
    $report.errors += "rule: $($_.Exception.Message)"
}

if ($WithSkillMenu) {
  if (Test-Path $skillScript) {
    try {
      & $skillScript -TargetProject $TargetProject -SkillSource $SkillRoot
      $report.skill_menu_path = Join-Path $TargetProject ".cursor\skills\weekly-report-migration"
    } catch {
      $report.status = "partial"
      $report.errors += "skill_menu: $($_.Exception.Message)"
    }
  } else {
    $report.status = "partial"
    $report.errors += "skill_menu: 缺少 $skillScript"
  }
}

if ($report.errors.Count -gt 0 -and $report.status -eq "ok") {
  $report.status = "partial"
}

$report | ConvertTo-Json -Depth 4
if ($report.status -eq "failed") { exit 1 }
exit 0
