#!/usr/bin/env pwsh
# Start Covina Microservices (DEBUG MODE)
# ========================================
# Startet Backends in SICHTBAREN Fenstern für Debugging

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Starting Covina Microservices (DEBUG MODE)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backends will start in SEPARATE WINDOWS" -ForegroundColor Yellow
Write-Host "  You can see console output and errors directly" -ForegroundColor Yellow
Write-Host ""

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    exit 1
}

# Create logs directory if it doesn't exist
$LogDir = "C:\VCC\Covina\logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "Created logs directory: $LogDir" -ForegroundColor Gray
}

# Generate log file names with timestamp
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$MainLog = Join-Path $LogDir "main_backend_$Timestamp.log"
$IngestionLog = Join-Path $LogDir "ingestion_backend_$Timestamp.log"

Write-Host "Log files will be created:" -ForegroundColor Gray
Write-Host "  Main:      $MainLog" -ForegroundColor Gray
Write-Host "  Ingestion: $IngestionLog" -ForegroundColor Gray
Write-Host ""

# Stop any existing backends first
Write-Host "Stopping any existing backends..." -ForegroundColor Yellow
& "$PSScriptRoot\stop_services.ps1"
Start-Sleep -Seconds 2

# Start Main Backend in NEW WINDOW (visible console) with application-level logging
Write-Host ""
Write-Host "Starting Main Backend (Port 45678) in new window..." -ForegroundColor Green

# Pass log file targets via environment so the app can write JSON logs to files itself
$env:COVINA_LOG_FILE = $MainLog
$env:COVINA_ERR_FILE = "$MainLog.err"
Start-Process -FilePath "python" -ArgumentList "main.py" `
    -WorkingDirectory "C:\VCC\Covina\backend" `
    -WindowStyle Normal

Start-Sleep -Seconds 3

# Start Ingestion Backend in NEW WINDOW (visible console) with application-level logging
Write-Host "Starting Ingestion Backend (Port 45679) in new window..." -ForegroundColor Green

# Update env for ingestion log targets (inherited by child process)
$env:COVINA_LOG_FILE = $IngestionLog
$env:COVINA_ERR_FILE = "$IngestionLog.err"
Start-Process -FilePath "python" -ArgumentList "ingestion.py" `
    -WorkingDirectory "C:\VCC\Covina\backend" `
    -WindowStyle Normal

Write-Host "  Waiting for backends to initialize (10s)..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Health Checks
Write-Host ""
Write-Host "Running Health Checks..." -ForegroundColor Yellow

# Function for health check
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

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Covina Microservices Running (DEBUG MODE)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URLs:" -ForegroundColor White
Write-Host "  Main Backend:      http://127.0.0.1:45678" -ForegroundColor White
Write-Host "  Ingestion Backend: http://127.0.0.1:45679" -ForegroundColor White
Write-Host ""
Write-Host "Console Windows:" -ForegroundColor Yellow
Write-Host "  Main Backend:      Separate window (visible)" -ForegroundColor Gray
Write-Host "  Ingestion Backend: Separate window (visible)" -ForegroundColor Gray
Write-Host ""
Write-Host "Log Files:" -ForegroundColor Yellow
Write-Host "  Main Backend:      $MainLog" -ForegroundColor Gray
Write-Host "  Main Errors:       $MainLog.err" -ForegroundColor Gray
Write-Host "  Ingestion Backend: $IngestionLog" -ForegroundColor Gray
Write-Host "  Ingestion Errors:  $IngestionLog.err" -ForegroundColor Gray
Write-Host ""
Write-Host "Stop with: .\scripts\stop_services.ps1" -ForegroundColor Red
Write-Host ""
Write-Host "NOTE: You can see all console output in the backend windows!" -ForegroundColor Yellow
Write-Host "      Watch for errors, exceptions, or unexpected shutdowns." -ForegroundColor Yellow
Write-Host "      All output is also logged to the files above." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
