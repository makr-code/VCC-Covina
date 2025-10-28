#!/usr/bin/env pwsh
# Quick Backend Stability Test
# =============================
# Sendet Requests an Backends und prüft ob sie stabil bleiben

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Backend Stability Test" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Checks (10x)
Write-Host "Test 1: Health Checks (10 iterations)..." -ForegroundColor Yellow
for ($i = 1; $i -le 10; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:45679/health" -TimeoutSec 2
        Write-Host "  Iteration $i/10: " -NoNewline
        Write-Host "✅ OK" -ForegroundColor Green
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Host "  Iteration $i/10: " -NoNewline
        Write-Host "❌ FAILED - $($_.Exception.Message)" -ForegroundColor Red
        break
    }
}

Write-Host ""

# Test 2: Get Jobs (check if endpoint works)
Write-Host "Test 2: Jobs Endpoint..." -ForegroundColor Yellow
try {
    $jobs = Invoke-RestMethod -Uri "http://127.0.0.1:45679/jobs" -TimeoutSec 2
    $jobCount = ($jobs | Measure-Object).Count
    Write-Host "  ✅ Jobs endpoint works - $jobCount jobs found" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Jobs endpoint failed - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 3: Worker Pool Status
Write-Host "Test 3: Worker Pool Status..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:45679/health" -TimeoutSec 2
    Write-Host "  I/O Workers:  $($health.worker_pool.io_workers)" -ForegroundColor Gray
    Write-Host "  CPU Workers:  $($health.worker_pool.cpu_workers)" -ForegroundColor Gray
    Write-Host "  ✅ Worker pool active" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Worker pool check failed - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 4: Process Stability
Write-Host "Test 4: Process Stability (30s monitoring)..." -ForegroundColor Yellow
Write-Host "  Monitoring Python processes for 30 seconds..." -ForegroundColor Gray

$startProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
$startCount = ($startProcesses | Measure-Object).Count
Write-Host "  Start: $startCount Python processes" -ForegroundColor Gray

for ($i = 1; $i -le 6; $i++) {
    Start-Sleep -Seconds 5
    $currentProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
    $currentCount = ($currentProcesses | Measure-Object).Count
    
    if ($currentCount -ne $startCount) {
        Write-Host "  ⚠️  Process count changed: $startCount → $currentCount" -ForegroundColor Yellow
    } else {
        Write-Host "  ${i}×5s: $currentCount processes (stable)" -ForegroundColor Gray
    }
}

$endProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
$endCount = ($endProcesses | Measure-Object).Count

Write-Host ""
if ($endCount -eq $startCount) {
    Write-Host "  ✅ Process count stable: $startCount processes" -ForegroundColor Green
} else {
    Write-Host "  ❌ Process count unstable: $startCount → $endCount" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Test Complete" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If backends are unstable, check the console windows for errors!" -ForegroundColor Yellow
Write-Host ""
