#!/usr/bin/env pwsh
<#
.SYNOPSIS
Stop the PSL Automation Jira Dashboard.

.DESCRIPTION
Finds and terminates the FastAPI application running on port 3000.

.EXAMPLE
.\stop.ps1
#>

$ErrorActionPreference = "SilentlyContinue"

Write-Host "PSL Automation - Stopping Dashboard..." -ForegroundColor Yellow

# Find process on port 3000
$port = 3000
$process = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue

if ($process) {
    $pid = $process.OwningProcess
    $procName = (Get-Process -Id $pid -ErrorAction SilentlyContinue).Name
    Write-Host "Found process on port $port (PID: $pid, Name: $procName)" -ForegroundColor Cyan
    
    Stop-Process -Id $pid -Force
    Write-Host "Process terminated." -ForegroundColor Green
} else {
    Write-Host "No process found on port $port" -ForegroundColor Gray
}

Write-Host "Dashboard stopped." -ForegroundColor Green
