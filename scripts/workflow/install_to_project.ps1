#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Install weekly-report-migration pointer Rule (.mdc) into a business project.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $SkillRoot,

    [string] $TargetProject = (Get-Location).Path,

    [string] $RuleName = "weekly-report-migration.mdc"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    $py = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $py) {
    throw "Python not found in PATH"
}

& $py.Source (Join-Path $scriptDir "install_to_project.py") `
    --skill-root $SkillRoot `
    --target-project $TargetProject `
    --rule-name $RuleName
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
