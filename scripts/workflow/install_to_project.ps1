#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Install weekly-report-migration pointer Rule (.mdc) into a business project.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install_to_project.ps1 -SkillRoot "d:\branch\skills\report-migration" -TargetProject "D:\my-app"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $SkillRoot,

    [string] $TargetProject = (Get-Location).Path,

    [string] $RuleName = "weekly-report-migration.mdc"
)

$ErrorActionPreference = "Stop"

function Resolve-FullPath([string]$p) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Path not found: $p"
    }
    return (Resolve-Path -LiteralPath $p).Path
}

$SkillRoot = Resolve-FullPath $SkillRoot
$TargetProject = Resolve-FullPath $TargetProject

if ($SkillRoot -eq $TargetProject) {
    throw "TargetProject must not equal SkillRoot; run from a business project root."
}

$skillMd = Join-Path $SkillRoot "SKILL.md"
if (-not (Test-Path $skillMd)) {
    throw "Invalid skill directory (missing SKILL.md): $SkillRoot"
}

$template = Join-Path $SkillRoot "templates\report-migration-pointer.mdc"
if (-not (Test-Path $template)) {
    throw "Missing template: $template"
}

$rulesDir = Join-Path $TargetProject ".cursor\rules"
$dest = Join-Path $rulesDir $RuleName

New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null
$content = Get-Content $template -Raw -Encoding UTF8
$content = $content.Replace("{{SKILL_ROOT}}", $SkillRoot.Replace("\", "/"))
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($dest, $content, $utf8NoBom)

$report = [ordered]@{
    status         = "ok"
    skill_root     = $SkillRoot
    target_project = $TargetProject
    rule_path      = $dest
}

$report | ConvertTo-Json -Depth 4
Write-Host "Installed rule: $dest"
Write-Host "Say weekly-report-migration or @weekly-report-migration to run."
