# 🚀 Covina - Schnellstart-Anleitung

## Projekt-Struktur (Optimiert - 5. Oktober 2025)

```
C:\VCC\Covina\
│
├── backend.py                # 🚀 Backend (FastAPI)
├── gui.py                    # 🎨 Haupt-GUI
├── run_tests.py              # 🧪 Test-Runner
│
├── backends/                 # Service-Layer & APIs
├── frontends/                # Alternative GUIs
│
├── tests/                    # Test-Suite
│   ├── integration/         # Integration Tests
│   ├── unit/                # Unit Tests
│   ├── validation/          # Validation Tests
│   └── performance/         # Performance Tests
│
├── docs/                     # Dokumentation
│   ├── architecture/        # Architektur-Docs
│   ├── guides/              # Anleitungen
│   └── reports/             # Reports
│
├── scripts/                  # Utility Scripts
│   ├── demos/               # Demo-Skripte
│   ├── maintenance/         # Wartungsskripte
│   └── deployment/          # Deployment-Tools
│
└── [Module...]
    ├── uds3/                # UDS3 Framework
    ├── ingestion/           # Ingestion Module
    ├── management_core/     # Management Module
    ├── gap_detection/       # Gap Detection
    └── ai_judge/            # AI Judge
```

## ⚡ Schnellstart

### 1. Backend starten
```bash
python backend.py
```
Backend läuft auf: **http://localhost:8001**

### 2. GUI starten (in neuem Terminal)
```bash
python gui.py
```

### 3. Tests ausführen
```bash
# Alle Tests
python run_tests.py

# Nur Integration Tests
python run_tests.py integration

# Nur Unit Tests
python run_tests.py unit
```

## 📋 Voraussetzungen

```bash
# Dependencies installieren
pip install -r requirements.txt

# Development Dependencies
pip install -r requirements-dev.txt
```

## 🔧 Konfiguration

1. Kopiere `.env.example` nach `.env` (falls vorhanden)
2. Passe `backends/config.py` an deine Bedürfnisse an
3. Konfiguriere Datenbank-Verbindungen in der GUI oder config/

## 📚 Weitere Dokumentation

- **Architektur**: `docs/architecture/`
- **Anleitungen**: `docs/guides/`
- **API-Dokumentation**: Nach Backend-Start unter `/docs`
- **Vollständige README**: siehe `README.md` im Root-Verzeichnis

## 🆘 Hilfe

Bei Problemen siehe:
- `docs/guides/DEPLOYMENT_GUIDE.md`
- `docs/reports/` für System-Reports
- GitHub Issues

## ✨ Was ist neu?

**5. Oktober 2025 - Updates:**

### Kuratierungs-GUI mit KI 🤖
```bash
# Starte KI-unterstütztes Kuratierungs-GUI
python curation_gui.py
# ODER
start_curation_gui.bat
```

**Features:**
- ✅ Lokale KI-Analyse (spaCy, kein Internet nötig)
- ✅ Automatische Metadaten-Vorschläge
- ✅ Dokumenttyp-Klassifikation
- ✅ Keyword-Extraktion
- ✅ Named Entity Recognition
- ✅ Juridische Entitäten (Gesetze, §§, Gerichte)
- ✅ Ein-Klick Übernahme von Vorschlägen
- ✅ 70% Zeitersparnis

**Dokumentation:** `CURATION_KI_DOKUMENTATION.md`

### Dynamisches Template-System 📋
```bash
# Template-Manager testen
python curation_template_manager.py

# Template-basierte KI-Analyse testen
python test_template_analysis.py
```

**Features:**
- ✅ 6 dokumenttypspezifische Templates (GESETZ, RECHTSPRECHUNG, VERWALTUNGSAKT, VERTRAG, GUTACHTEN, SONSTIGES)
- ✅ **~100 template-basierte KI-Prompts** (feldspezifisch) ⭐
- ✅ **15+ intelligente Extraktions-Methoden** ⭐
- ✅ Automatische Dokumentklassifikation (75% Genauigkeit)
- ✅ Validierungsregeln (min/max, enum, pattern)
- ✅ Dynamische Feld-Gruppierung für UI
- ✅ Vollständigkeits-Scoring
- ✅ Nächste-Felder-Vorschläge
- ✅ **Template-spezifische Feld-Extraktion** (Titel, Aktenzeichen, Fundstellen, etc.) ⭐

**Dokumentation:** 
- API-Referenz: `docs/CURATION_TEMPLATES_DOKUMENTATION.md`
- Success Report: `docs/TEMPLATE_PROMPTS_SUCCESS.md` ⭐
- Integration: `docs/TEMPLATE_INTEGRATION_COMPLETE.md`

### Projekt-Restrukturierung
- ✅ Vereinfachte Dateinamen (backend.py, gui.py)
- ✅ Klare Trennung: Backends, Frontends, Tests, Docs
- ✅ Bessere Organisation der Test-Suite
- ✅ Zentrale Dokumentation
- ✅ SAGA Integration mit GUI-Feedback

