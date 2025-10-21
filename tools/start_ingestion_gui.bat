@echo off
REM Covina Ingestion GUI Tool - Windows Launcher
REM Starts the GUI tool with proper error handling

echo ========================================
echo  Covina Ingestion GUI Tool v1.0
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if dependencies are installed
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] tkinter not found! Installing...
    echo Note: tkinter is usually included with Python
    pause
    exit /b 1
)

echo [OK] tkinter found
echo.

REM Check if requests is installed
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo [OK] Dependencies installed
echo.

REM Check backend availability
echo [INFO] Checking backend connection...
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:45679/health | findstr "200" >nul
if errorlevel 1 (
    echo [WARNING] Ingestion Backend not reachable!
    echo Please start backend: scripts\start_services.ps1
    echo.
    echo Continue anyway? (Y/N)
    choice /c YN /n
    if errorlevel 2 exit /b 1
)

echo [OK] Backend online
echo.

REM Start GUI
echo [INFO] Starting GUI...
echo.
python "%~dp0ingestion_gui.py"

REM Check exit code
if errorlevel 1 (
    echo.
    echo [ERROR] GUI crashed! Check logs above.
    pause
    exit /b 1
)

echo.
echo [INFO] GUI closed normally
