param(
    [switch]$VerboseLogs
)

$ErrorActionPreference = 'Stop'

Write-Host "[Restart] Stopping services..."
& "$PSScriptRoot\stop_services.ps1"

Write-Host "[Restart] Starting services..."
& "$PSScriptRoot\start_services.ps1" @()

if ($VerboseLogs) {
    Write-Host "[Restart] Done. Check logs in terminal windows or service outputs."
}