# Data Transformation Tool Launcher
# Startet das Data Transformation Admin GUI
# Author: GitHub Copilot
# Date: 31. Oktober 2025

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host "="*79 -ForegroundColor Cyan
Write-Host "  Data Transformation Tool - Covina Admin" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host "="*79 -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
Write-Host "[CHECK] Testing backend connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:45678/health" -TimeoutSec 3 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] Backend is running on port 45678" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARNING] Backend not responding on port 45678!" -ForegroundColor Red
    Write-Host "          Please start the backend first:" -ForegroundColor Yellow
    Write-Host "          .\scripts\start_services.ps1" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host ""
Write-Host "[START] Launching Data Transformation Tool..." -ForegroundColor Green
Write-Host ""

# Set Python path
$env:PYTHONPATH = "C:\VCC\Covina;C:\VCC\uds3"

# Launch GUI
python admin_tools\data_transformation_tool.py

Write-Host ""
Write-Host "[DONE] Data Transformation Tool closed" -ForegroundColor Cyan
