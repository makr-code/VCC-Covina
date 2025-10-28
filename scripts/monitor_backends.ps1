#!/usr/bin/env pwsh
# Monitor Covina Backend Status
# ==============================
# Überwacht kontinuierlich den Status der Backends

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Covina Backend Monitor" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Monitoring backends every 5 seconds..." -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

$iteration = 0

while ($true) {
    $iteration++
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    Write-Host "[$timestamp] Check #$iteration" -ForegroundColor Gray
    
    # Check Main Backend (Port 45678)
    try {
        $mainHealth = Invoke-RestMethod -Uri "http://127.0.0.1:45678/health" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  Main Backend:      " -NoNewline
        Write-Host "✅ HEALTHY" -ForegroundColor Green
    } catch {
        Write-Host "  Main Backend:      " -NoNewline
        Write-Host "❌ DOWN - $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Check Ingestion Backend (Port 45679)
    try {
        $ingestionHealth = Invoke-RestMethod -Uri "http://127.0.0.1:45679/health" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  Ingestion Backend: " -NoNewline
        Write-Host "✅ HEALTHY" -ForegroundColor Green
        
        # Show worker pool status
        $ioWorkers = $ingestionHealth.worker_pool.io_workers
        $cpuWorkers = $ingestionHealth.worker_pool.cpu_workers
        Write-Host "    Workers: $ioWorkers I/O, $cpuWorkers CPU" -ForegroundColor Gray
        
    } catch {
        Write-Host "  Ingestion Backend: " -NoNewline
        Write-Host "❌ DOWN - $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Check for Python processes
    $pythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
    if ($pythonProcesses) {
        $processCount = ($pythonProcesses | Measure-Object).Count
        $totalMemoryMB = [math]::Round(($pythonProcesses | Measure-Object -Property WorkingSet64 -Sum).Sum / 1MB, 2)
        Write-Host "  Python Processes:  $processCount processes, ${totalMemoryMB} MB total memory" -ForegroundColor Gray
    } else {
        Write-Host "  Python Processes:  " -NoNewline
        Write-Host "⚠️  NO PYTHON PROCESSES RUNNING!" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Start-Sleep -Seconds 5
}
