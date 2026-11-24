#requires -version 5.1
<#
.SYNOPSIS
    把 .deb 收录进蜀洮的越狱源。
.DESCRIPTION
    复制 deb 到 debs\，重建索引。同包多版本时索引只保留最高版。
.EXAMPLE
    .\scripts\add-deb.ps1 -Path 'D:\...\plugin-manager\Release\com.shutao.pluginmanager_1.5.5_iphoneos-arm64.deb'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$debs = Join-Path $root 'debs'

if (-not (Test-Path $Path)) { Write-Host "[ERROR] not found: $Path" -ForegroundColor Red; exit 1 }
if ($Path -notlike '*.deb') { Write-Host "[ERROR] not a .deb" -ForegroundColor Red; exit 1 }

$name = Split-Path $Path -Leaf
$dest = Join-Path $debs $name

Write-Host ""
Write-Host "==> Copying $name" -ForegroundColor Cyan
Copy-Item $Path $dest -Force
$size = (Get-Item $dest).Length
Write-Host "    $([math]::Round($size/1KB,1)) KB" -ForegroundColor Green

Write-Host ""
Write-Host "==> Rebuilding index" -ForegroundColor Cyan
& python (Join-Path $PSScriptRoot 'rebuild.py')
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] rebuild failed" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "Done. Now push:" -ForegroundColor Green
Write-Host "  cd '$root'"
Write-Host "  git add -A; git commit -m 'add $name'; git push"
