@echo off
REM Covina System Startup Script
REM =============================
REM Startet Backend und Frontend der Covina Document Processing Platform

echo.
echo  🏛️ Covina Document Processing System
echo  ====================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python ist nicht installiert oder nicht im PATH!
    echo Bitte installieren Sie Python 3.8+ von https://www.python.org/
    pause
    exit /b 1
)

echo ✅ Python gefunden

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Erstelle virtuelle Umgebung...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Fehler beim Erstellen der virtuellen Umgebung!
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo 🔧 Aktiviere virtuelle Umgebung...
call venv\Scripts\activate.bat

REM Install/Update dependencies
echo 📚 Installiere/Aktualisiere Abhängigkeiten...
pip install -r requirements.txt
pip install fastapi uvicorn requests aiosmtplib

REM Check if backend is already running
echo 🔍 Prüfe Backend-Status...
curl -s http://127.0.0.1:8001/health >nul 2>&1
if not errorlevel 1 (
    echo ⚠️ Backend läuft bereits auf Port 8001
    set BACKEND_RUNNING=1
) else (
    set BACKEND_RUNNING=0
)

REM Start backend if not running
if %BACKEND_RUNNING%==0 (
    echo 🚀 Starte Covina Backend...
    start "Covina Backend" cmd /k "call venv\Scripts\activate.bat && python backend.py"
    
    REM Wait for backend to start
    echo ⏳ Warte auf Backend-Start...
    timeout /t 3 /nobreak >nul
    
    REM Verify backend is running
    for /l %%i in (1,1,10) do (
        curl -s http://127.0.0.1:8001/health >nul 2>&1
        if not errorlevel 1 (
            echo ✅ Backend erfolgreich gestartet!
            goto backend_ready
        )
        echo Warte... %%i/10
        timeout /t 2 /nobreak >nul
    )
    
    echo ❌ Backend konnte nicht gestartet werden!
    pause
    exit /b 1
) else (
    echo ✅ Backend bereits aktiv
)

:backend_ready

REM Start GUI
echo 🎨 Starte Covina GUI...
python gui.py

echo.
echo 👋 Covina System beendet
pause