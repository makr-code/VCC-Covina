#!/usr/bin/env pwsh
# Start Covina Microservices
# =========================
# Startet Main Backend und Ingestion Backend parallel

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Starting Covina Microservices" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    exit 1
}

# Create logs directory
$logsDir = "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# Start Main Backend on Port 45678
Write-Host ""
Write-Host "Starting Main Backend on Port 45678..." -ForegroundColor Green
$mainBackend = Start-Process -FilePath "python" -ArgumentList "backend.py" `
    -NoNewWindow -PassThru -RedirectStandardOutput "logs\main_backend.log" `
    -RedirectStandardError "logs\main_backend_error.log"

Start-Sleep -Seconds 2

# Start Ingestion Backend on Port 45679
Write-Host "Starting Ingestion Backend on Port 45679..." -ForegroundColor Green
$ingestionBackend = Start-Process -FilePath "python" -ArgumentList "ingestion_backend.py" `
    -NoNewWindow -PassThru -RedirectStandardOutput "logs\ingestion_backend.log" `
    -RedirectStandardError "logs\ingestion_backend_error.log"

Write-Host "  Waiting for backends to initialize (10s)..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Health Checks
Write-Host ""
Write-Host "Running Health Checks..." -ForegroundColor Yellow

# Function for health check with retry
function Test-BackendHealth {
    param(
        [string]$Name,
        [string]$Url,
        [int]$MaxRetries = 5,
        [int]$RetryDelay = 2
    )
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $health = Invoke-RestMethod -Uri $Url -TimeoutSec 3 -ErrorAction Stop
            if ($health.status -eq "healthy") {
                Write-Host "  OK  $Name`: healthy" -ForegroundColor Green
                return $health
            } else {
                Write-Host "  WARN $Name`: $($health.status)" -ForegroundColor Yellow
                return $health
            }
        } catch {
            if ($i -lt $MaxRetries) {
                Write-Host "  RETRY $Name`: attempt $i/$MaxRetries..." -ForegroundColor Gray
                Start-Sleep -Seconds $RetryDelay
            }
        }
    }
    
    Write-Host "  FAIL $Name`: not responding after $MaxRetries retries" -ForegroundColor Red
    return $null
}

# Check Main Backend
$mainHealth = Test-BackendHealth -Name "Main Backend" -Url "http://127.0.0.1:45678/health"

# Check Ingestion Backend
$ingestionHealth = Test-BackendHealth -Name "Ingestion Backend" -Url "http://127.0.0.1:45679/health"

if ($ingestionHealth) {
    $ioWorkers = $ingestionHealth.worker_pool.io_workers
    $cpuWorkers = $ingestionHealth.worker_pool.cpu_workers
    Write-Host "      Workers: $ioWorkers I/O, $cpuWorkers CPU" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Covina Microservices Running" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URLs:" -ForegroundColor White
Write-Host "  Main Backend:      http://127.0.0.1:45678" -ForegroundColor White
Write-Host "  Ingestion Backend: http://127.0.0.1:45679" -ForegroundColor White
Write-Host ""
Write-Host "Process IDs:" -ForegroundColor Yellow
Write-Host "  Main Backend PID:      $($mainBackend.Id)" -ForegroundColor Gray
Write-Host "  Ingestion Backend PID: $($ingestionBackend.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "Logs:" -ForegroundColor Yellow
Write-Host "  Main:      logs\main_backend.log" -ForegroundColor Gray
Write-Host "  Ingestion: logs\ingestion_backend.log" -ForegroundColor Gray
Write-Host ""
Write-Host "Stop with: .\scripts\stop_services.ps1" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Cyan
