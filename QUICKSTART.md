# 🚀 Covina - Schnellstart-Anleitung

## Projekt-Struktur (Optimiert - 24. Oktober 2025)

```
C:\VCC\Covina\
│
├── covina_app.py             # 🎨 Haupt-GUI (Frontend)
├── docker-compose.yml        # � Docker Services
├── requirements.txt          # 📦 Dependencies
│
├── backend/                  # Backend Services
│   ├── main.py              # Main Backend (Port 45678)
│   ├── ingestion.py         # Ingestion Backend (Port 45679)
│   ├── core/                # Core Modules (logging, polyglot)
│   └── services/            # Services (compliance, mail)
│
├── config/                   # Configuration
│   ├── app.py               # Global App Config
│   └── automation.yaml      # Automation Config
│
├── tests/                    # Test Suite (147 tests)
│   ├── integration/         # Integration Tests (5)
│   ├── unit/                # Unit Tests (removed fake tests)
│   └── [142 test files]     # Root tests
│
├── docs/                     # Documentation
│   ├── architecture/        # Architecture Docs
│   ├── guides/              # User Guides
│   ├── frontend/            # Frontend Docs
│   └── examples/            # Code Examples
│
├── scripts/                  # Utility Scripts
│   ├── debug/               # Debug Tools (18 scripts)
│   ├── fix/                 # Fix Scripts
│   ├── test/                # Test Scripts
│   └── monitoring/          # Monitoring Scripts
│
├── tools/                    # Development Tools
│   ├── architecture_viewer.py  # Architecture Viewer
│   ├── template_manager.py     # Template Manager
│   └── polyglot_admin.py       # Polyglot Admin UI
│
├── archive/                  # Legacy Files
│   ├── snippets/            # Code Snippets
│   └── old_backups/         # Old Backups
│
└── [Core Modules...]
    ├── ingestion/           # Ingestion Framework
    ├── management_core/     # Management Module
    ├── gap_detection/       # Gap Detection
    ├── ai_judge/            # AI Judge
    ├── security/            # Security Module
    ├── saga/                # SAGA Orchestrator
    └── polyglot_admin/      # Polyglot Admin
```

## ⚡ Schnellstart

### 1. Backend starten (Microservices)
```bash
# Option A: Mit Deployment Script (empfohlen)
.\scripts\deploy_backend_v3_4_9.ps1

# Option B: Manuell
python backend\main.py        # Port 45678 (Queries, DSGVO, Review)
python backend\ingestion.py   # Port 45679 (Upload, UDS3)
```
- **Main Backend**: http://localhost:45678 (API Docs: /docs)
- **Ingestion Backend**: http://localhost:45679 (API Docs: /docs)

### 2. GUI starten (in neuem Terminal)
```bash
python covina_app.py
```

### 3. Tests ausführen
```bash
# Auth Tests (keine Dependencies)
python -m pytest tests/test_auth.py -v

# Integration Tests (benötigt laufende Backends + Datenbanken)
python -m pytest tests/integration/ -v

# Alle Tests (benötigt PostgreSQL, Neo4j, ChromaDB, CouchDB)
python -m pytest tests/ -v
```

## 📋 Voraussetzungen

```bash
# Dependencies installieren
pip install -r requirements.txt

# Optional: Development Dependencies
pip install pytest pytest-asyncio pytest-cov
```

## 🔧 Konfiguration

1. **Environment**: Kopiere `.env.example` nach `.env.production`
2. **App Config**: Passe `config/app.py` an deine Bedürfnisse an
3. **Automation**: Konfiguriere `config/automation.yaml`
4. **Datenbanken**: Konfiguriere in `.env.production`:
   - PostgreSQL (Port 5432)
   - ChromaDB (Port 8000)
   - Neo4j (Port 7687)
   - CouchDB (Port 32931)

## 📚 Weitere Dokumentation

- **Migration Guide**: `docs/MIGRATION.md` (Oktober 2025 Refactoring)
- **Architektur**: `docs/architecture/`
- **Anleitungen**: `docs/guides/`
- **API-Dokumentation**: 
  - Main Backend: http://localhost:45678/docs
  - Ingestion Backend: http://localhost:45679/docs
- **Vollständige README**: siehe `README.md` im Root-Verzeichnis

## 🆘 Hilfe

Bei Problemen siehe:
- `docs/MIGRATION.md` für Refactoring-Details
- `docs/guides/` für Anleitungen
- `scripts/debug/` für Debug-Tools
- GitHub Issues

## ✨ Was ist neu?

## ✨ Was ist neu?

**24. Oktober 2025 - Große Refactoring-Aktion:**

### 🎯 Codebase-Reorganisation (82% Root-Files Reduktion!)
- ✅ **Root-Verzeichnis**: 51 → 9 Dateien (-82%)
- ✅ **Backend**: `main_backend.py` → `backend/main.py`, `ingestion_backend.py` → `backend/ingestion.py`
- ✅ **Config**: `config.py` → `config/app.py`
- ✅ **Scripts**: Reorganisiert in `scripts/debug/`, `scripts/fix/`, `scripts/test/`
- ✅ **Tests**: Reorganisiert in `tests/unit/`, `tests/integration/`
- ✅ **Docs**: Reorganisiert in `docs/guides/`, `docs/architecture/`, `docs/examples/`
- ✅ **Git History**: Alle 53 Moves mit `git mv` (History preserved!)
- ✅ **Duplikate**: 16 Dateien entfernt (*_0.py, commit_message*.txt)
- ✅ **Filenames**: Alle ≤30 Zeichen (vorher: 15+ >40 chars)

### 🧪 Test Suite Validation
- ✅ **Auth Tests**: 13/13 PASSED (JWT, RBAC)
- ✅ **Fake Unit Tests**: 4 Debug-Scripts nach `scripts/debug/` verschoben
- ✅ **Total Tests**: 147 echte Tests gefunden (142 root + 5 integration)

### 📁 Neue Struktur
- **Backend Microservices**: Dual-Backend (Main Port 45678 + Ingestion Port 45679)
- **Config Folder**: Zentrale Konfiguration in `config/`
- **Tools Folder**: Development Tools (`architecture_viewer.py`, `template_manager.py`)
- **Archive Folder**: Legacy Code in `archive/snippets/`, `archive/old_backups/`

### 📚 Migration Guide
Siehe `docs/MIGRATION.md` für:
- Detaillierte Datei-Mapping (Alt → Neu)
- Import-Statement Updates
- Deployment-Script Änderungen
- Rollback-Plan

---

**5. Oktober 2025 - Frühere Updates:**

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

