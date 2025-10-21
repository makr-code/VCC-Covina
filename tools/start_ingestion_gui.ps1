# Covina Ingestion GUI Tool - PowerShell Launcher
# Starts the GUI tool with proper error handling

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Covina Ingestion GUI Tool v1.0" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found! Please install Python 3.8+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Check if dependencies are installed
try {
    python -c "import tkinter" 2>&1 | Out-Null
    Write-Host "[OK] tkinter found" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] tkinter not found!" -ForegroundColor Red
    Write-Host "Note: tkinter is usually included with Python" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Check if requests is installed
try {
    python -c "import requests" 2>&1 | Out-Null
    Write-Host "[OK] requests found" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Yellow
    
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    pip install -r "$scriptDir\requirements.txt"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host "[OK] Dependencies installed" -ForegroundColor Green
}

Write-Host ""

# Check backend availability
Write-Host "[INFO] Checking backend connection..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:45679/health" -TimeoutSec 2 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] Backend online" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Backend unhealthy (Status: $($response.StatusCode))" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[WARNING] Ingestion Backend not reachable!" -ForegroundColor Yellow
    Write-Host "Please start backend: .\scripts\start_services.ps1" -ForegroundColor Yellow
    Write-Host ""
    
    $continue = Read-Host "Continue anyway? (Y/N)"
    if ($continue -ne "Y" -and $continue -ne "y") {
        exit 1
    }
}

Write-Host ""

# Start GUI
Write-Host "[INFO] Starting GUI..." -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$scriptDir\ingestion_gui.py"

# Check exit code
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] GUI crashed! Check logs above." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[INFO] GUI closed normally" -ForegroundColor Green
