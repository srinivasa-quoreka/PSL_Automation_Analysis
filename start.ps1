#!/usr/bin/env pwsh
<#
.SYNOPSIS
Start the PSL Automation Jira Dashboard on port 3000.

.DESCRIPTION
Loads environment variables from .env and starts the FastAPI application.
Make sure .env is configured with your Jira credentials before running.

.EXAMPLE
.\start.ps1
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "PSL Automation - Starting Dashboard..." -ForegroundColor Green
Write-Host "Working directory: $ScriptDir" -ForegroundColor Gray

# Check if .env exists
if (-not (Test-Path "$ScriptDir\.env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure your Jira credentials." -ForegroundColor Yellow
    exit 1
}

# Load .env file into environment
Get-Content "$ScriptDir\.env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $line = $_ -replace '^\s+|\s+$'
    if ($line -match '^([^=]+)=(.*)$') {
        $name = $matches[1]
        $value = $matches[2]
        [System.Environment]::SetEnvironmentVariable($name, $value)
    }
}

# Set port
$port = if ($env:PORT) { $env:PORT } else { "3000" }
$env:PORT = $port

Write-Host "Jira Base URL: $($env:JIRA_BASE_URL)" -ForegroundColor Cyan
Write-Host "Port: $port" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting server..." -ForegroundColor Green

# Run the app
& python -m app.main

