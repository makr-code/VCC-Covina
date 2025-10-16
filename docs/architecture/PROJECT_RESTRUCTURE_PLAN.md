# Covina Projekt Restrukturierung
## Datum: 5. Oktober 2025

## 🎯 Ziel
Bereinigung der Root-Verzeichnis-Struktur mit klarer Trennung zwischen:
- Backends
- Frontends
- Tests
- Dokumentation
- Scripts
- Konfiguration

## 📁 Neue Projektstruktur

```
C:\VCC\Covina\
│
├── start_backend.py              # Launcher für Backend
├── start_gui.py                  # Launcher für GUI
├── run_tests.py                  # Test Runner
├── README.md                     # Haupt-Dokumentation
├── requirements.txt              # Dependencies
├── requirements-dev.txt          # Dev Dependencies
├── .env                          # Environment Config
├── docker-compose.yml            # Docker Setup
├── Dockerfile                    # Docker Image
├── pyrightconfig.json            # Type Checker Config
├── pytest.ini                    # Pytest Config
├── mkdocs.yml                    # Dokumentation Config
│
├── backends/                     # ALLE Backend-Services
│   ├── __init__.py
│   ├── covina_backend.py         # Haupt-Backend (FastAPI)
│   ├── compliance_dashboard_api.py
│   ├── compliance_dashboard_service.py
│   ├── covina_mail_service_clean.py
│   ├── covina_logging.py
│   ├── core_light.py
│   ├── config.py
│   ├── ingestion_core.py
│   ├── ingestion_cli.py
│   ├── runtime_integrity.py
│   └── uds3_polyglot_integration.py
│
├── frontends/                    # ALLE Frontend-GUIs
│   ├── __init__.py
│   ├── covina_unified_gui_clean.py  # Haupt-GUI (Tkinter)
│   ├── covina_unified_gui.py     # Alternative GUI
│   ├── covina_gui_implementation.py
│   ├── enhanced_covina_gui.py
│   ├── curation_gui.py
│   └── legacy/                   # Legacy GUIs
│       ├── covina_gui_legacy.py
│       └── enhanced_covina_backend_legacy.py
│
├── tests/                        # ALLE Tests
│   ├── __init__.py
│   ├── integration/              # Integration Tests
│   │   ├── test_saga_integration.py
│   │   ├── test_uds3_integration.py
│   │   ├── test_audit_trail_integration.py
│   │   └── e2e_ingestion_test.py
│   ├── unit/                     # Unit Tests
│   │   ├── test_api_debugging.py
│   │   ├── test_chromadb_connection.py
│   │   └── test_neo4j_elementid.py
│   ├── validation/               # Validation Tests
│   │   ├── test_enhanced_saga_validation.py
│   │   └── enhanced_saga_validation.py
│   ├── performance/              # Performance Tests
│   │   └── run_performance_tests.py
│   └── data/                     # Test Data
│       └── test_data/ (existing)
│
├── docs/                         # Dokumentation
│   ├── architecture/
│   │   ├── INGESTION_ARCHITEKTUR.md
│   │   ├── PHASE*.md
│   │   └── SAGA_PATTERN_IMPLEMENTATION.md
│   ├── guides/
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   ├── MAIL_TESTING_GUIDE.md
│   │   └── MACHINE_READABLE_EXPORT_GUIDE.md
│   ├── reports/
│   │   ├── UDS3_INTEGRATION_REPORT.md
│   │   ├── PERFORMANCE_INTEGRATION_SUCCESS.md
│   │   └── *_SUCCESS.md
│   └── api/
│       └── management_core/ (existing)
│
├── scripts/                      # Utility Scripts
│   ├── deployment/
│   │   ├── install_production.sh
│   │   ├── run_migrations.py
│   │   └── setup_*.py
│   ├── maintenance/
│   │   ├── fix_*.py
│   │   └── debug_*.py
│   ├── demos/                    # Demo Scripts
│   │   ├── demo_*.py
│   │   └── run_demo_batch.py
│   └── tools/                    # Development Tools
│       └── devtools/ (existing)
│
├── config/                       # Konfigurationsdateien
│   ├── __init__.py
│   ├── deploy_config.py
│   ├── signing.yaml.example
│   └── sigstore-policy.example.json
│
├── data/                         # Datenverzeichnis
│   ├── sqlite_relational.db
│   ├── assets/
│   └── backups/
│       └── database_backup/ (existing)
│
├── pipelines/                    # Datenverarbeitungs-Pipelines
│   └── (existing content)
│
├── examples/                     # Code-Beispiele
│   └── (existing content)
│
├── ingestion/                    # Ingestion Module
│   └── (existing content)
│
├── management_core/              # Management Module
│   └── (existing content)
│
├── gap_detection/                # Gap Detection Module
│   └── (existing content)
│
├── ai_judge/                     # AI Judge Module
│   └── (existing content)
│
├── uds3/                         # UDS3 Framework
│   └── (existing content)
│
├── tmp/                          # Temporäre Dateien
│   ├── tmp_*.py
│   └── temp_*.db
│
└── logs/                         # Log-Dateien (NEU)
    └── *.log

```

## 📋 Kategorisierung der Dateien

### Backend Files → `backends/`
- covina_backend.py
- compliance_dashboard_api.py
- compliance_dashboard_service.py
- covina_mail_service_clean.py
- covina_logging.py
- core_light.py
- config.py
- ingestion_core.py
- ingestion_cli.py
- runtime_integrity.py
- uds3_polyglot_integration.py
- uds3_production_integration.py
- covina_uds3_adapter.py
- uds3_adapter.py
- enhanced_covina_backend_api_legacy.py (→ legacy/)
- covina_mail_service_legacy.py (→ legacy/)

### Frontend Files → `frontends/`
- covina_unified_gui_clean.py
- covina_unified_gui.py
- covina_gui_implementation.py
- enhanced_covina_gui.py
- curation_gui.py
- curation_cli.py
- covina_gui_legacy.py (→ legacy/)

### Test Files → `tests/`
- test_*.py (alle Test-Dateien)
- enhanced_saga_validation.py → tests/validation/
- e2e_*.py → tests/integration/
- run_*_tests.py → tests/

### Documentation → `docs/`
- *.md (außer README.md, CHANGELOG.md)
- CHANGELOG.md → Root (bleibt)
- README.md → Root (bleibt)

### Scripts → `scripts/`
- demo_*.py → scripts/demos/
- fix_*.py → scripts/maintenance/
- debug_*.py → scripts/maintenance/
- setup_*.py → scripts/deployment/
- run_*.py (außer run_tests.py) → scripts/
- scan_*.py → scripts/tools/

### Config → `config/`
- deploy_config.py
- signing.yaml.example
- sigstore-policy.example.json

### Logs → `logs/`
- *.log (alle Log-Dateien)

### Temporary → `tmp/`
- tmp_*.py
- temp_*.db

### Root bleiben:
- start_backend.py (NEU)
- start_gui.py (NEU)
- run_tests.py (BLEIBT)
- README.md
- requirements.txt
- requirements-dev.txt
- .env
- docker-compose.yml
- Dockerfile
- pyrightconfig.json
- pytest.ini
- mkdocs.yml
- CHANGELOG.md

## 🚀 Launcher-Skripte

### start_backend.py
```python
#!/usr/bin/env python3
"""Covina Backend Launcher"""
import sys
from pathlib import Path

# Add backends to path
sys.path.insert(0, str(Path(__file__).parent / "backends"))

from backends.covina_backend import *

if __name__ == "__main__":
    # Start backend
    pass
```

### start_gui.py
```python
#!/usr/bin/env python3
"""Covina GUI Launcher"""
import sys
from pathlib import Path

# Add frontends to path
sys.path.insert(0, str(Path(__file__).parent / "frontends"))

from frontends.covina_unified_gui_clean import MainApp

if __name__ == "__main__":
    app = MainApp()
    app.run()
```

## ⚠️ Import-Anpassungen notwendig

Nach dem Verschieben müssen Imports aktualisiert werden:
- `from config import ...` → `from backends.config import ...`
- `import covina_backend` → `from backends import covina_backend`
- Relative Imports in Tests anpassen

## 📝 Migration Steps

1. ✅ Struktur-Plan erstellen
2. ⏳ Verzeichnisse erstellen
3. ⏳ Dateien verschieben
4. ⏳ Imports aktualisieren
5. ⏳ Launcher-Skripte erstellen
6. ⏳ Tests ausführen
7. ⏳ Dokumentation aktualisieren
