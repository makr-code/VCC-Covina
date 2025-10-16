#!/usr/bin/env pwsh
# Stop Covina Microservices
# =========================
# Stoppt Main Backend und Ingestion Backend

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Red
Write-Host "   Stopping Covina Microservices" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Red

# Stop Main Backend on Port 45678
Write-Host ""
Write-Host "Stopping Main Backend on Port 45678..." -ForegroundColor Yellow

try {
    $mainConnection = Get-NetTCPConnection -LocalPort 45678 -State Listen -ErrorAction SilentlyContinue
    if ($mainConnection) {
        $processId = $mainConnection.OwningProcess
        Stop-Process -Id $processId -Force
        Write-Host "  OK  Main Backend stopped (PID: $processId)" -ForegroundColor Green
    } else {
        Write-Host "  WARN Main Backend not running (Port 45678 free)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARN Main Backend not running" -ForegroundColor Yellow
}

# Stop Ingestion Backend on Port 45679
Write-Host "Stopping Ingestion Backend on Port 45679..." -ForegroundColor Yellow

try {
    $ingestionConnection = Get-NetTCPConnection -LocalPort 45679 -State Listen -ErrorAction SilentlyContinue
    if ($ingestionConnection) {
        $processId = $ingestionConnection.OwningProcess
        Stop-Process -Id $processId -Force
        Write-Host "  OK  Ingestion Backend stopped (PID: $processId)" -ForegroundColor Green
    } else {
        Write-Host "  WARN Ingestion Backend not running (Port 45679 free)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARN Ingestion Backend not running" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   All services stopped" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
