# Covina Compliance & Automation - Entwickler-Dokumentation

## 🛠️ Entwicklungsumgebung einrichten

### Voraussetzungen

- Python 3.9+
- Git
- Visual Studio Code (empfohlen)

### Lokales Setup

1. **Repository klonen:**
   ```bash
   git clone https://github.com/makr-code/VCC-Covina.git
   cd VCC-Covina
   ```

2. **Virtuelle Umgebung erstellen:**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Optional: Dev-Abhängigkeiten
   ```

4. **Umgebungsvariablen konfigurieren:**
   ```bash
   cp .env.example .env
   # .env editieren und anpassen
   ```

## 📁 Projektstruktur

```
Covina/
├── .github/           # GitHub Actions, Workflows
├── docs/              # Erweiterte Dokumentation
├── src/               # Quellcode
│   ├── main.py        # Haupteinstiegspunkt
│   ├── config/        # Konfigurationsdateien
│   ├── models/        # Datenmodelle
│   └── utils/         # Hilfsfunktionen
├── tests/             # Unit- und Integrationstests
├── scripts/           # Hilfs-Skripte
├── .env.example       # Umgebungsvariablen-Vorlage
├── .gitignore         # Git-Ignore-Datei
├── requirements.txt   # Python-Abhängigkeiten
└── README.md          # Projekt-Übersicht
```

## 🧪 Tests ausführen

```bash
# Alle Tests
pytest

# Mit Coverage
pytest --cov=src tests/

# Spezifischer Test
pytest tests/test_specific.py
```

## 🔍 Code-Qualität

### Linting
```bash
# Flake8
flake8 src/

# Black (Code Formatting)
black src/

# MyPy (Type Checking)
mypy src/
```

## 🐛 Debugging

### Logging

Logging-Konfiguration:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📦 Build und Deployment

### Docker
```bash
# Image bauen
docker build -t vcc-covina .

# Container starten
docker run -p 8000:8000 vcc-covina
```

## 🤝 Beitragen

### Workflow

1. **Branch erstellen:**
   ```bash
   git checkout -b feature/neue-funktion
   ```

2. **Änderungen committen:**
   ```bash
   git add .
   git commit -m "feat: Neue Funktion hinzugefügt"
   ```

3. **Push und Pull Request:**
   ```bash
   git push origin feature/neue-funktion
   # Dann Pull Request auf GitHub erstellen
   ```

### Commit-Konventionen

- `feat:` - Neue Features
- `fix:` - Bug-Fixes
- `docs:` - Dokumentations-Änderungen
- `refactor:` - Code-Refactoring
- `test:` - Test-Änderungen
- `chore:` - Wartungsaufgaben

---

*Letzte Aktualisierung: 16.10.2025*
