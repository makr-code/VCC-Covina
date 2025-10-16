@echo off
REM Curation GUI mit KI-Unterstützung starten
REM ==========================================

echo.
echo  🤖 Covina Kuratierungs-GUI mit KI-Unterstützung
echo  ===============================================
echo.

REM Prüfe ob Python verfügbar ist
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python ist nicht installiert!
    echo Bitte installieren Sie Python 3.8+ von https://www.python.org/
    pause
    exit /b 1
)

echo ✅ Python gefunden

REM Prüfe ob spaCy installiert ist
python -c "import spacy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️ spaCy nicht gefunden. Installiere Abhängigkeiten...
    pip install -r requirements-curation-nlp.txt
    
    echo.
    echo 📥 Lade deutsches Sprachmodell (~567MB, einmalig)...
    python -m spacy download de_core_news_lg
)

REM Prüfe ob deutsches Modell verfügbar ist
python -c "import spacy; spacy.load('de_core_news_lg')" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️ Deutsches Sprachmodell nicht gefunden
    echo 📥 Installiere de_core_news_lg...
    python -m spacy download de_core_news_lg
)

echo.
echo 🚀 Starte Kuratierungs-GUI...
echo.

REM Starte GUI
python curation_gui.py

echo.
echo 👋 Curation GUI beendet
pause
