#!/usr/bin/env pwsh
# Auto-Restart Backend Service
# =============================
# Überwacht Backends und startet sie automatisch neu bei Crash

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Covina Backend Auto-Restart Service" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Monitoring backends and auto-restarting on crash..." -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

$restartCount = 0
$maxRestarts = 10  # Prevent infinite restart loop

while ($restartCount -lt $maxRestarts) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    # Check Main Backend
    $mainDown = $false
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:45678/health" -TimeoutSec 2 -ErrorAction Stop
    } catch {
        $mainDown = $true
    }
    
    # Check Ingestion Backend
    $ingestionDown = $false
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:45679/health" -TimeoutSec 2 -ErrorAction Stop
    } catch {
        $ingestionDown = $true
    }
    
    # Restart if needed
    if ($mainDown -or $ingestionDown) {
        $restartCount++
        Write-Host "[$timestamp] ❌ Backend(s) down! Restarting... (attempt $restartCount/$maxRestarts)" -ForegroundColor Red
        
        # Stop all backends
        & "$PSScriptRoot\stop_services.ps1" | Out-Null
        Start-Sleep -Seconds 2
        
        # Restart in debug mode
        & "$PSScriptRoot\start_services_debug.ps1" | Out-Null
        Start-Sleep -Seconds 10
        
        Write-Host "[$timestamp] ✅ Backends restarted" -ForegroundColor Green
    } else {
        Write-Host "[$timestamp] ✅ Backends healthy" -ForegroundColor Green
    }
    
    Start-Sleep -Seconds 10
}

Write-Host ""
Write-Host "⚠️  Max restart limit reached ($maxRestarts restarts)" -ForegroundColor Yellow
Write-Host "   Backends are crashing repeatedly - manual intervention required!" -ForegroundColor Yellow
Write-Host ""
