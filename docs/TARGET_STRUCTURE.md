# Covina - Ziel-Struktur & Refactoring-Plan

**Erstellt:** 2025-10-24  
**Zweck:** Detaillierte Ziel-Struktur für Codebase-Refactoring  
**Basis:** docs/CURRENT_STRUCTURE.md (IST-Analyse)  
**Status:** ✅ Task #2 - Target Structure Design Complete

---

## 🎯 Design-Prinzipien

### 1. Separation of Concerns
- **Backend:** Alle Backend-APIs in `backend/`
- **Frontend:** Alle UI-Code in `frontend/`
- **Ingestion:** Alle Datenverarbeitung in `ingestion/`
- **Tests:** Alle Tests in `tests/`
- **Docs:** Alle Dokumentation in `docs/`
- **Config:** Alle Konfiguration in `config/`

### 2. Namenskonventionen
- **Max 30 Zeichen** (ohne Extension)
- **snake_case** für alle Python-Dateien
- **UPPERCASE** nur für Root-Docs (README, CHANGELOG)
- **Keine Versionsnummern** in Dateinamen (phase4, v3_4_9)
- **Keine Suffixe** (_0, _BACKUP, _old) → Archive oder DELETE

### 3. Root Directory Regel
**Max 10 Dateien im Root:**
1. `README.md` - Projekt-Übersicht
2. `QUICKSTART.md` - Quick Start Guide
3. `CHANGELOG.md` - Version History
4. `docker-compose.yml` - Docker Setup
5. `requirements.txt` - Python Dependencies (konsolidiert)
6. `sitecustomize.py` - Python Startup Config
7. `.gitignore` - Git Ignore Rules
8. `pyproject.toml` - Python Project Config (optional)

### 4. Ordner-Hierarchie
- **Max 3 Ebenen Tiefe** (Ordner/Unterordner/Datei)
- **Logische Gruppierung** (nicht alphabetisch)
- **Klare Verantwortlichkeiten** (ein Ordner = eine Aufgabe)

---

## 📁 Ziel-Struktur (Komplett)

```
Covina/
├─ 📄 README.md                      # Projekt-Übersicht, Quick Links
├─ 📄 QUICKSTART.md                  # Getting Started Guide
├─ 📄 CHANGELOG.md                   # Version History
├─ 📄 docker-compose.yml             # Docker Compose Setup
├─ 📄 requirements.txt               # Python Dependencies (konsolidiert)
├─ 📄 sitecustomize.py               # Python Startup Customization
├─ 📄 .gitignore                     # Git Ignore Rules (erweitert)
│
├─ 📁 backend/                       # Main + Ingestion Backends
│  ├─ 📄 main.py                     # Main Backend (Port 45678)
│  ├─ 📄 ingestion.py                # Ingestion Backend (Port 45679)
│  ├─ 📄 main_openapi.json           # Main Backend API Spec
│  ├─ 📄 ingestion_openapi.json      # Ingestion Backend API Spec
│  ├─ 📁 core/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 polyglot.py              # Polyglot Integration Layer
│  │  └─ 📄 logging.py               # Logging Configuration
│  ├─ 📁 services/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 compliance.py            # DSGVO Compliance Service
│  │  ├─ 📄 compliance_api.py        # Compliance REST API
│  │  └─ 📄 mail.py                  # Mail Service
│  └─ 📁 config/
│     ├─ 📄 __init__.py
│     └─ 📄 app.py                   # Backend Configuration
│
├─ 📁 frontend/                      # Frontend Application (v4.0.3)
│  ├─ 📄 main.py                     # Frontend Entry Point
│  ├─ 📄 config.py                   # Frontend Configuration
│  ├─ 📄 README.md                   # Frontend Documentation
│  ├─ 📄 QUICKSTART.md               # Frontend Quick Start
│  ├─ 📁 core/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 event_bus.py             # EventBus System
│  │  ├─ 📄 view_manager.py          # View Manager
│  │  ├─ 📄 task_executor.py         # Task Executor
│  │  ├─ 📄 backend_service.py       # Backend Service Client
│  │  ├─ 📄 chart_threading.py       # Chart Threading
│  │  └─ 📄 chart_workers.py         # Chart Workers
│  ├─ 📁 services/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 api_client.py            # REST API Client
│  │  └─ 📄 websocket_client.py      # WebSocket Client
│  ├─ 📁 views/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 base_view.py             # Base View Class
│  │  ├─ 📄 home_dashboard.py        # Home Dashboard View
│  │  ├─ 📄 ingestion.py             # Ingestion View
│  │  ├─ 📄 saga.py                  # SAGA View
│  │  ├─ 📄 security.py              # Security View
│  │  ├─ 📄 golden_dataset.py        # Golden Dataset View
│  │  ├─ 📄 database_health.py       # Database Health View
│  │  ├─ 📄 system_status.py         # System Status View
│  │  ├─ 📄 uds3.py                  # UDS3 View
│  │  └─ 📄 recovery.py              # Recovery View
│  ├─ 📁 widgets/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 kpi_card.py              # KPI Card Widget
│  │  ├─ 📄 sidebar_left.py          # Left Sidebar
│  │  ├─ 📄 sidebar_right.py         # Right Sidebar
│  │  ├─ 📄 status_bar.py            # Status Bar
│  │  ├─ 📄 top_toolbar.py           # Top Toolbar
│  │  ├─ 📄 saga_monitor.py          # SAGA Monitor Widget
│  │  ├─ 📄 uds3_dataset.py          # UDS3 Dataset Widget
│  │  ├─ 📄 bulk_copy_progress.py    # Bulk Copy Progress Modal
│  │  ├─ 📄 upload_method.py         # Upload Method Dialog
│  │  └─ 📄 ai_terminal.py           # AI Terminal Widget
│  └─ 📁 utils/
│     ├─ 📄 __init__.py
│     ├─ 📄 theme.py                 # UI Theme Configuration
│     └─ 📄 live_updater.py          # Live Update Utilities
│
├─ 📁 polyglot_admin/                # Polyglot Admin GUI (v3.1.0)
│  ├─ 📄 main.py                     # Entry Point
│  ├─ 📄 README.md                   # Polyglot Admin Docs
│  ├─ 📄 CHANGELOG.md                # Version History (v3.1.0)
│  ├─ 📁 controllers/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 search_controller.py     # Hybrid Search Controller
│  │  ├─ 📄 saga_controller.py       # SAGA Controller
│  │  ├─ 📄 document_controller.py   # Document Controller
│  │  ├─ 📄 graph_controller.py      # Graph Controller
│  │  ├─ 📄 vector_controller.py     # Vector Controller
│  │  └─ 📄 backend_factory.py       # Backend Factory
│  ├─ 📁 docs/
│  │  └─ 📄 hybrid_search.md         # Hybrid Search Reference
│  ├─ 📁 tests/
│  │  └─ 📄 test_hybrid_search.py    # Hybrid Search Tests
│  └─ 📁 utils/
│     ├─ 📄 __init__.py
│     └─ 📄 branding.py              # Branding Utilities
│
├─ 📁 ingestion/                     # Ingestion Pipeline
│  ├─ 📄 README.md                   # Ingestion Documentation
│  ├─ 📄 batch_embeddings.py         # Batch Embeddings (Real Embeddings)
│  ├─ 📄 bulk_copy_streaming.py      # Bulk Copy Streaming
│  ├─ 📄 scanner.py                  # Directory Scanner
│  ├─ 📄 discovery_service.py        # Discovery Service
│  ├─ 📄 file_events.py              # File Event Handlers
│  ├─ 📄 geospatial_processor.py     # Geospatial Processing
│  ├─ 📄 job_factory.py              # Job Factory
│  ├─ 📄 job_persistence.py          # Job Persistence (SQLite)
│  ├─ 📄 upload_chunked.py           # Chunked Upload
│  ├─ 📄 upload_websocket.py         # WebSocket Upload
│  ├─ 📄 upload_smb_watcher.py       # SMB Watcher Upload
│  ├─ 📄 hybrid_upload_manager.py    # Hybrid Upload Manager
│  ├─ 📄 saga_executors.py           # SAGA Executors
│  ├─ 📄 metadata_extractor.py       # Advanced Metadata Extractor
│  ├─ 📁 handlers/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 base.py                  # Base Handler
│  │  ├─ 📄 archive.py               # Archive Handler
│  │  ├─ 📄 code.py                  # Code Handler
│  │  ├─ 📄 geo.py                   # Geo Handler
│  │  ├─ 📄 image.py                 # Image Handler
│  │  ├─ 📄 office.py                # Office Handler
│  │  ├─ 📄 text.py                  # Text Handler
│  │  └─ 📄 factory.py               # Handler Factory
│  ├─ 📁 retrieval/
│  │  ├─ 📄 __init__.py
│  │  ├─ 📄 bm25_indexer.py          # BM25 Indexer
│  │  ├─ 📄 fusion.py                # Retrieval Fusion
│  │  └─ 📄 reranker.py              # Reranker
│  └─ 📁 services/
│     ├─ 📄 __init__.py
│     ├─ 📄 handelsregister.py       # Handelsregister Client
│     └─ 📄 classification.py        # Document Classification Service
│
├─ 📁 security/                      # Security Module
│  ├─ 📄 __init__.py
│  ├─ 📄 auth.py                     # Authentication
│  ├─ 📄 secrets.py                  # Secrets Management
│  └─ 📄 tls.py                      # TLS Configuration
│
├─ 📁 utils/                         # Utilities
│  ├─ 📄 __init__.py
│  ├─ 📄 json_logging.py             # JSON Logging
│  ├─ 📄 metrics.py                  # Metrics Collection
│  └─ 📄 pii_redaction.py            # PII Redaction
│
├─ 📁 management_core/               # Management Core Extensions
│  ├─ 📄 __init__.py
│  ├─ 📄 README.md
│  ├─ 📄 management_core.py          # Core Management
│  ├─ 📄 admin_dashboard.py          # Admin Dashboard
│  ├─ 📄 filesystem_mgmt.py          # Filesystem Management
│  ├─ 📄 graph_mgmt.py               # Graph Management
│  ├─ 📄 relational_mgmt.py          # Relational Management
│  ├─ 📄 vector_mgmt.py              # Vector Management
│  ├─ 📄 fuzzy_pattern.py            # Fuzzy Pattern Matching
│  ├─ 📄 lifecycle.py                # Lifecycle Management
│  ├─ 📄 policy.py                   # Policy Management
│  ├─ 📄 registry.py                 # Registry
│  ├─ 📄 review_queue.py             # Review Queue
│  └─ 📁 extensions/
│     ├─ 📄 __init__.py
│     └─ (weitere Extensions)
│
├─ 📁 gap_detection/                 # Gap Detection System
│  ├─ 📄 __init__.py
│  ├─ 📄 core.py                     # Core Gap Detection
│  ├─ 📄 gap_database.py             # Gap Database
│  ├─ 📄 knowledge_gap_gui.py        # GUI
│  ├─ 📄 monitoring_dashboard.py     # Monitoring Dashboard
│  ├─ 📄 nlp_pipeline.py             # NLP Pipeline
│  └─ 📄 vpb_process_mining.py       # VPB Process Mining
│
├─ 📁 automation/                    # Automation System
│  ├─ 📄 README.md
│  ├─ 📁 workers/
│  └─ (weitere Automation-Module)
│
├─ 📁 ai_judge/                      # AI Judge System
│  └─ (AI Judge Module)
│
├─ 📁 saga/                          # SAGA Orchestrator
│  └─ 📄 orchestrator.py             # SAGA Orchestrator (Production Mode)
│
├─ 📁 migrations/                    # Database Migrations
│  ├─ 📄 create_golden_dataset.py    # Golden Dataset Table
│  ├─ 📄 create_governance.py        # Governance Policies Table
│  ├─ 📄 create_graph_golden.py      # Graph Golden Dataset
│  └─ 📄 migrate_secrets.py          # Secrets Migration
│
├─ 📁 config/                        # Configuration Files
│  ├─ 📄 app.py                      # Global App Configuration
│  ├─ 📄 automation.yaml             # Automation Config
│  └─ 📄 pipelines.json              # Pipeline Configs
│
├─ 📁 scripts/                       # Utility Scripts
│  ├─ 📁 deploy/
│  │  ├─ 📄 backend_v3_4_9.ps1       # Backend Deployment
│  │  ├─ 📄 start_services.ps1       # Start Services
│  │  ├─ 📄 stop_services.ps1        # Stop Services
│  │  └─ 📄 restart_services.ps1     # Restart Services
│  ├─ 📁 debug/
│  │  ├─ 📄 analyze_db_apis.py       # Analyze Database APIs
│  │  ├─ 📄 check_golden_table.py    # Check Golden Dataset Table
│  │  ├─ 📄 check_graph_schema.py    # Check Graph Schema
│  │  ├─ 📄 check_jobs.py            # Check Jobs Status
│  │  ├─ 📄 check_last_jobs.py       # Check Last Jobs
│  │  ├─ 📄 debug_graph_post.py      # Debug Graph API
│  │  ├─ 📄 debug_ui_layout.py       # Debug UI Layout
│  │  └─ 📄 debug_statistics.py      # Debug Statistics
│  ├─ 📁 fix/
│  │  ├─ 📄 governance_api.py        # Fix Governance API
│  │  ├─ 📄 graph_api.py             # Fix Graph API
│  │  ├─ 📄 postgres_conn.py         # Fix PostgreSQL Connections
│  │  ├─ 📄 startup_errors.py        # Fix Startup Errors
│  │  ├─ 📄 event_types.py           # Fix Event Types
│  │  ├─ 📄 generated_views.py       # Fix Generated Views
│  │  ├─ 📄 requests_timeout.py      # Fix Requests Timeout
│  │  └─ 📄 bulk_copy_method.py      # Replace Bulk Copy Method
│  ├─ 📁 test/
│  │  ├─ 📄 run_integration.ps1      # Run Integration Tests
│  │  ├─ 📄 run_security_scans.ps1   # Run Security Scans
│  │  ├─ 📄 e2e_handelsregister.py   # E2E Test Handelsregister
│  │  ├─ 📄 company_metadata.py      # Test Company Metadata
│  │  ├─ 📄 json_logging.py          # Test JSON Logging
│  │  ├─ 📄 large_file_perf.py       # Test Large File Performance
│  │  ├─ 📄 metrics.py               # Test Metrics
│  │  ├─ 📄 pii_redaction.py         # Test PII Redaction
│  │  ├─ 📄 pool_metrics.py          # Test Pool Metrics
│  │  ├─ 📄 rate_limiting.py         # Test Rate Limiting
│  │  └─ 📄 review_queue.py          # Test Review Queue
│  ├─ 📁 upload/
│  │  ├─ 📄 chunked_upload.py        # Chunked Upload Client
│  │  ├─ 📄 websocket_upload.py      # WebSocket Upload Client
│  │  └─ 📄 compare_performance.py   # Compare Upload Performance
│  ├─ 📁 migration/
│  │  ├─ 📄 migrate_views.py         # Migrate Views
│  │  └─ 📄 task5_summary.py         # Task 5 Summary
│  └─ 📁 monitoring/
│     ├─ 📄 monitor_gpu.py           # GPU Monitoring
│     └─ 📄 check_schema.py          # Check Database Schema
│
├─ 📁 tests/                         # Test Suite
│  ├─ 📄 conftest.py                 # Pytest Configuration
│  ├─ 📄 README.md                   # Testing Documentation
│  ├─ 📁 unit/
│  │  ├─ 📄 test_db_schema.py        # Database Schema Tests
│  │  ├─ 📄 test_json_serial.py      # JSON Serialization Tests
│  │  ├─ 📄 test_errors.py           # Error Handling Tests
│  │  ├─ 📄 test_auth.py             # Authentication Tests
│  │  └─ 📄 test_secrets.py          # Secrets Tests
│  ├─ 📁 integration/
│  │  ├─ 📄 test_batch_api.py        # Batch API Tests
│  │  ├─ 📄 test_gap_db.py           # Gap Detection DB Tests
│  │  ├─ 📄 test_uds3.py             # UDS3 Import Tests
│  │  ├─ 📄 test_adapter.py          # Adapter Integration Tests
│  │  ├─ 📄 test_auth_endpoints.py   # Auth Endpoints Tests
│  │  ├─ 📄 test_batch_delete.py     # Batch Delete Tests
│  │  ├─ 📄 test_batch_update.py     # Batch Update Tests
│  │  ├─ 📄 test_batch_upsert.py     # Batch Upsert Tests
│  │  ├─ 📄 test_batch_write.py      # Batch Write Integration Tests
│  │  ├─ 📄 test_cleanup.py          # Cleanup Tests
│  │  ├─ 📄 test_connection_pool.py  # Connection Pool Tests
│  │  ├─ 📄 test_couchdb_conn.py     # CouchDB Connection Tests
│  │  ├─ 📄 test_couchdb_integ.py    # CouchDB Integration Tests
│  │  ├─ 📄 test_functional_upload.py # Functional Upload Tests
│  │  ├─ 📄 test_neo4j_integ.py      # Neo4j Integration Tests
│  │  └─ 📄 benchmark_conn_pool.py   # Connection Pool Benchmark
│  ├─ 📁 fixtures/
│  │  ├─ 📄 test_doc.txt             # Test Document
│  │  ├─ 📄 test_pattern.json        # Test Pattern
│  │  └─ 📄 error_output.txt         # Test Error Output
│  ├─ 📁 reports/
│  │  └─ 📄 e2e_report.json          # E2E Test Report
│  └─ 📁 debug/
│     └─ 📄 debug_adapter.py         # Debug Adapter
│
├─ 📁 docs/                          # Documentation
│  ├─ 📄 README.md                   # Documentation Index
│  ├─ 📁 architecture/
│  │  ├─ 📄 overview.md              # System Overview
│  │  ├─ 📄 backend_analysis.md      # Backend Analysis
│  │  ├─ 📄 backend_clarify.md       # Backend Clarification
│  │  ├─ 📄 microservices.md         # Microservices Architecture
│  │  ├─ 📄 polyglot_admin.md        # Polyglot Admin Architecture
│  │  └─ 📄 websocket_integ.md       # WebSocket Integration
│  ├─ 📁 guides/
│  │  ├─ 📄 contributing.md          # Contribution Guide
│  │  ├─ 📄 development.md           # Development Guide
│  │  ├─ 📄 testing.md               # Testing Guide
│  │  └─ 📄 deployment.md            # Deployment Guide
│  ├─ 📁 api/
│  │  ├─ 📄 main_backend.md          # Main Backend API
│  │  ├─ 📄 ingestion_backend.md     # Ingestion Backend API
│  │  ├─ 📄 compliance_api.md        # Compliance API
│  │  └─ 📄 review_queue.md          # Review Queue API
│  ├─ 📁 reports/
│  │  ├─ 📄 backend_refactoring.md   # Backend Refactoring Report
│  │  ├─ 📄 frontend_modern.md       # Frontend Modernization
│  │  ├─ 📄 uds3_migration.md        # UDS3 Migration Summary
│  │  ├─ 📄 saga_production.md       # SAGA Production Complete
│  │  ├─ 📄 recovery_system.md       # Recovery System Complete
│  │  ├─ 📄 performance_tuning.md    # Performance Tuning
│  │  └─ 📄 session_summaries/       # Session Summaries Folder
│  │     ├─ 📄 2025-10-16.md
│  │     ├─ 📄 2025-10-17.md
│  │     └─ ...
│  ├─ 📁 frontend/
│  │  ├─ 📄 architecture.md          # Frontend Architecture
│  │  ├─ 📄 event_bus.md             # EventBus Documentation
│  │  ├─ 📄 view_manager.md          # ViewManager Documentation
│  │  └─ 📄 widgets.md               # Widgets Documentation
│  └─ 📁 examples/
│     ├─ 📄 compliance_demo.py       # Compliance API Demo
│     └─ 📄 mgmt_core_demo.py        # Management Core Demo
│
├─ 📁 tools/                         # Admin Tools & Utilities
│  ├─ 📄 README.md                   # Tools Documentation
│  ├─ 📄 QUICKSTART.md               # Tools Quick Start
│  ├─ 📄 SUMMARY.md                  # Tools Summary
│  ├─ 📄 requirements.txt            # Tools Dependencies
│  ├─ 📄 polyglot_admin.py           # Polyglot Admin Launcher
│  ├─ 📄 ingestion_gui.py            # Ingestion GUI
│  ├─ 📄 architecture_viewer.py      # Architecture Viewer
│  ├─ 📄 template_manager.py         # Template Manager
│  ├─ 📁 admin/
│  │  ├─ 📄 golden_dataset_gui.py    # Golden Dataset Manager
│  │  ├─ 📄 graph_pattern_gui.py     # Graph Pattern Manager
│  │  ├─ 📄 governance_policy_gui.py # Governance Policy Manager
│  │  └─ 📄 launcher_gui.py          # Admin Tools Launcher
│  └─ 📁 scripts/
│     └─ 📄 start_ingestion_gui.ps1  # Start Ingestion GUI
│
├─ 📁 archive/                       # Legacy Code & Backups
│  ├─ 📄 README.md                   # Archive Documentation
│  ├─ 📄 backend_monolith.py         # Old Monolith Backend
│  ├─ 📄 gui_legacy.py               # Old GUI
│  ├─ 📁 snippets/
│  │  ├─ 📄 backend_main.py          # Backend Main Block
│  │  └─ 📄 ingestion_main.py        # Ingestion Main Block
│  └─ 📁 old_backups/
│     ├─ 📄 gap_database_old.py
│     └─ 📄 home_dashboard_BACKUP.py
│
├─ 📁 deploy/                        # Deployment Configs
│  ├─ 📄 README.md                   # Deployment Documentation
│  └─ 📁 pgbouncer/
│     └─ (pgbouncer configs)
│
├─ 📁 data/                          # Runtime Data (NOT IN GIT!)
│  ├─ 📁 secrets/                    # Secrets Storage
│  ├─ 📁 uploads/                    # Upload Temp Files
│  └─ 📁 logs/                       # Log Files
│
├─ 📁 logs/                          # Application Logs (NOT IN GIT!)
│  └─ 📁 security/
│
└─ 📁 pipelines/                     # Processing Pipelines
   └─ 📄 simple_text.json            # Simple Text Pipeline
```

---

## 🔄 Datei-Mapping (ALT → NEU)

### Root → backend/

| Alt (Root)                    | Neu (backend/)                  | Begründung |
|-------------------------------|---------------------------------|------------|
| `main_backend.py`             | `backend/main.py`               | Main Backend Entry |
| `ingestion_backend.py`        | `backend/ingestion.py`          | Ingestion Backend Entry |
| `openapi.json`                | `backend/main_openapi.json`     | Main Backend API Spec |
| `ingestion_openapi.json`      | `backend/ingestion_openapi.json`| Ingestion API Spec |
| `polyglot_integration.py`     | `backend/core/polyglot.py`      | Core Integration |
| `covina_logging.py`           | `backend/core/logging.py`       | Logging Config |
| `compliance_api.py`           | `backend/services/compliance_api.py` | Compliance REST API |
| `compliance_service.py`       | `backend/services/compliance.py`| Compliance Service |
| `mail_service.py`             | `backend/services/mail.py`      | Mail Service |
| `config.py`                   | `config/app.py`                 | Global Config → config/ |

---

### Root → frontend/

| Alt (Root)                    | Neu (frontend/)                 | Begründung |
|-------------------------------|---------------------------------|------------|
| `covina_app_phase4.py`        | **DELETE** (integriert in frontend/main.py) | Duplikat vermeiden |

**Note:** `frontend/` bereits gut strukturiert, nur Duplikate löschen:
- `frontend/core/event_bus_0.py` → DELETE
- `frontend/core/task_executor_0.py` → DELETE
- `frontend/core/view_manager_0.py` → DELETE
- `frontend/services/api_client_0.py` → DELETE
- `frontend/views/*_0.py` (7 Dateien) → DELETE
- `frontend/widgets/top_toolbar_0.py` → DELETE

---

### Root → scripts/

#### scripts/debug/

| Alt (Root)                    | Neu (scripts/debug/)            | Begründung |
|-------------------------------|---------------------------------|------------|
| `analyze_database_apis.py`    | `scripts/debug/analyze_db_apis.py` | Max 30 chars |
| `check_golden_dataset_table.py` | `scripts/debug/check_golden_table.py` | Max 30 chars |
| `check_graph_table_schema.py` | `scripts/debug/check_graph_schema.py` | Max 30 chars |
| `check_jobs.py`               | `scripts/debug/check_jobs.py`   | Keine Änderung |
| `check_last_jobs.py`          | `scripts/debug/check_last_jobs.py` | Keine Änderung |
| `debug_graph_post.py`         | `scripts/debug/graph_post.py`   | Prefix entfernen |
| `debug_ui_layout.py`          | `scripts/debug/ui_layout.py`    | Prefix entfernen |
| `debug_statistics.py` (in scripts/) | `scripts/debug/statistics.py` | Prefix entfernen |

#### scripts/fix/

| Alt (Root)                    | Neu (scripts/fix/)              | Begründung |
|-------------------------------|---------------------------------|------------|
| `fix_governance_policy_api.py`| `scripts/fix/governance_api.py` | Prefix entfernen |
| `fix_graph_golden_api.py`     | `scripts/fix/graph_api.py`      | Prefix entfernen |
| `fix_postgres_connects.py`    | `scripts/fix/postgres_conn.py`  | Max 30 chars |
| `fix_startup_errors.py`       | `scripts/fix/startup_errors.py` | Prefix entfernen |

#### scripts/test/

| Alt (Root)                    | Neu (scripts/test/)             | Begründung |
|-------------------------------|---------------------------------|------------|
| `run_integration_tests.py`    | `scripts/test/run_integration.ps1` | PowerShell besser |
| `start_ui_test.py`            | `scripts/test/start_ui_test.ps1` | PowerShell besser |

#### scripts/monitoring/

| Alt (Root)                    | Neu (scripts/monitoring/)       | Begründung |
|-------------------------------|---------------------------------|------------|
| `monitor_gpu.py`              | `scripts/monitoring/monitor_gpu.py` | Kategorie |

---

### Root → tests/

#### tests/unit/

| Alt (Root)                    | Neu (tests/unit/)               | Begründung |
|-------------------------------|---------------------------------|------------|
| `test_db_schema.py`           | `tests/unit/test_db_schema.py`  | Unit Test |
| `test_detailed_error.py`      | `tests/unit/test_errors.py`     | Umbenennen |
| `test_json_serialization.py`  | `tests/unit/test_json_serial.py`| Max 30 chars |
| `test_simple_endpoint.py`     | `tests/unit/test_endpoint.py`   | Kürzen |

#### tests/integration/

| Alt (Root)                    | Neu (tests/integration/)        | Begründung |
|-------------------------------|---------------------------------|------------|
| `test_batch_api.py`           | `tests/integration/test_batch_api.py` | Integration |
| `test_gap_db_connection.py`   | `tests/integration/test_gap_db.py` | Kürzen |
| `test_uds3_imports.py`        | `tests/integration/test_uds3.py`| Kürzen |

#### tests/fixtures/

| Alt (Root)                    | Neu (tests/fixtures/)           | Begründung |
|-------------------------------|---------------------------------|------------|
| `test_doc.txt`                | `tests/fixtures/test_doc.txt`   | Fixture |
| `test_pattern.json`           | `tests/fixtures/test_pattern.json` | Fixture |
| `test_error_output.txt`       | `tests/fixtures/error_output.txt` | Kürzen |

#### tests/reports/

| Alt (Root)                    | Neu (tests/reports/)            | Begründung |
|-------------------------------|---------------------------------|------------|
| `e2e_test_report.json`        | `tests/reports/e2e_report.json` | Kürzen |

---

### Root → docs/

#### docs/guides/

| Alt (Root)                    | Neu (docs/guides/)              | Begründung |
|-------------------------------|---------------------------------|------------|
| `CONTRIBUTING.md`             | `docs/guides/contributing.md`   | Lowercase |
| `DEVELOPMENT.md`              | `docs/guides/development.md`    | Lowercase |

#### docs/architecture/

| Alt (Root)                    | Neu (docs/architecture/)        | Begründung |
|-------------------------------|---------------------------------|------------|
| `SYSTEM_OVERVIEW.md`          | `docs/architecture/overview.md` | Kürzen |
| `BACKEND_ANALYSIS.md`         | `docs/architecture/backend_analysis.md` | Kategorisieren |
| `BACKEND_CLARIFICATION.md`    | `docs/architecture/backend_clarify.md` | Kürzen |

#### docs/reports/

| Alt (Root)                    | Neu (docs/reports/)             | Begründung |
|-------------------------------|---------------------------------|------------|
| `BACKEND_REFACTORING_COMPLETE.md` | `docs/reports/backend_refactoring.md` | Kürzen |
| `FRONTEND_MODERNIZATION_README.md` | `docs/frontend/modernization.md` | Frontend-Kategorie |

#### docs/examples/

| Alt (Root)                    | Neu (docs/examples/)            | Begründung |
|-------------------------------|---------------------------------|------------|
| `compliance_api_demo.py`      | `docs/examples/compliance_demo.py` | Demo Code |
| `management_core_extensions_demo.py` | `docs/examples/mgmt_core_demo.py` | Kürzen (19 chars) |

---

### Root → config/

| Alt (Root)                    | Neu (config/)                   | Begründung |
|-------------------------------|---------------------------------|------------|
| `config.py`                   | `config/app.py`                 | Umbenennen |
| `automation.yaml`             | `config/automation.yaml`        | Kategorie |

---

### Root → tools/

| Alt (Root)                    | Neu (tools/)                    | Begründung |
|-------------------------------|---------------------------------|------------|
| `covina_architecture.py`      | `tools/architecture_viewer.py`  | Prefix entfernen |
| `curation_template_manager.py`| `tools/template_manager.py`     | Kürzen (16 chars) |

#### admin_tools/ → tools/admin/

| Alt (admin_tools/)            | Neu (tools/admin/)              | Begründung |
|-------------------------------|---------------------------------|------------|
| `admin_tools/*`               | `tools/admin/*`                 | Konsistente Struktur |

---

### Root → archive/

| Alt (Root)                    | Neu (archive/)                  | Begründung |
|-------------------------------|---------------------------------|------------|
| `backend_monolith_backup.py`  | `archive/backend_monolith.py`   | Legacy Code |
| `_backend_main_block.py`      | `archive/snippets/backend_main.py` | Code Snippet |
| `_ingestion_main_block.py`    | `archive/snippets/ingestion_main.py` | Code Snippet |
| `covina_gui.py`               | `archive/gui_legacy.py`         | Legacy GUI |

---

### Root → DELETE

| Datei                         | Aktion                          | Begründung |
|-------------------------------|---------------------------------|------------|
| `commit_message.txt`          | **DELETE**                      | Git Artifact |
| `commit_message_final.txt`    | **DELETE**                      | Git Artifact |
| `commit_message_governance.txt` | **DELETE**                    | Git Artifact |
| `FRONTEND_MODERNIZATION_README_0.md` | **DELETE**           | Duplikat |
| `frontend/core/event_bus_0.py` | **DELETE**                     | Duplikat |
| `frontend/core/task_executor_0.py` | **DELETE**                 | Duplikat |
| `frontend/core/view_manager_0.py` | **DELETE**                  | Duplikat |
| `frontend/services/api_client_0.py` | **DELETE**                | Duplikat |
| `frontend/views/__init___0.py` | **DELETE**                     | Duplikat |
| `frontend/views/base_view_0.py` | **DELETE**                    | Duplikat |
| `frontend/views/home_view_0.py` | **DELETE**                    | Duplikat |
| `frontend/views/ingestion_view_migrated_0.py` | **DELETE**      | Duplikat |
| `frontend/views/system_status_view_migrated_0.py` | **DELETE** | Duplikat |
| `frontend/views/uds3_view_0.py` | **DELETE**                    | Duplikat |
| `frontend/widgets/top_toolbar_0.py` | **DELETE**                | Duplikat |

---

## 📝 Namenskonventionen - Detailliert

### Python Files

**Regel:** Max 30 Zeichen, snake_case, keine Versionsnummern

**Vorher → Nachher:**

```python
# LANG (>30 chars):
management_core_extensions_demo.py (36) → mgmt_core_demo.py (19)
check_golden_dataset_table.py     (29) → check_golden_table.py (18)
analyze_database_apis.py          (24) → analyze_db_apis.py (16)

# PRÄFIX entfernen:
debug_ui_layout.py                (18) → ui_layout.py (11)
debug_graph_post.py               (19) → graph_post.py (13)
debug_statistics.py               (19) → statistics.py (10)
fix_governance_policy_api.py      (28) → governance_api.py (16)
fix_graph_golden_api.py           (23) → graph_api.py (12)
fix_postgres_connects.py          (24) → postgres_conn.py (14)
fix_startup_errors.py             (21) → startup_errors.py (15)

# VERSION entfernen:
covina_app_phase4.py              (20) → DELETE (in frontend/main.py)
deploy_backend_v3_4_9.ps1         (25) → backend_v3_4_9.ps1 (17) ODER backend.ps1 (7)

# SUFFIX entfernen:
test_detailed_error.py            (22) → test_errors.py (12)
test_simple_endpoint.py           (23) → test_endpoint.py (13)
test_json_serialization.py        (26) → test_json_serial.py (17)
test_gap_db_connection.py         (25) → test_gap_db.py (12)
e2e_test_report.json              (20) → e2e_report.json (14)
```

---

### Markdown Files

**Regel:** UPPERCASE nur für Root-Docs, sonst lowercase

**Root (behalten):**
- `README.md` ✅
- `QUICKSTART.md` ✅
- `CHANGELOG.md` ✅

**Root → docs/ (lowercase):**
- `CONTRIBUTING.md` → `docs/guides/contributing.md`
- `DEVELOPMENT.md` → `docs/guides/development.md`
- `SYSTEM_OVERVIEW.md` → `docs/architecture/overview.md`
- `BACKEND_ANALYSIS.md` → `docs/architecture/backend_analysis.md`
- `BACKEND_CLARIFICATION.md` → `docs/architecture/backend_clarify.md`
- `BACKEND_REFACTORING_COMPLETE.md` → `docs/reports/backend_refactoring.md`
- `FRONTEND_MODERNIZATION_README.md` → `docs/frontend/modernization.md`

**Duplikate (DELETE):**
- `FRONTEND_MODERNIZATION_README_0.md` → DELETE
- `docs/*_0.md` (15+ Dateien) → DELETE

---

### PowerShell Scripts

**Regel:** Max 30 Zeichen, snake_case oder kebab-case

**Beispiele:**
- `deploy_backend_v3_4_9.ps1` (25) → `deploy-backend.ps1` (15) ODER behalten
- `start_services.ps1` (16) → behalten ✅
- `stop_services.ps1` (15) → behalten ✅
- `restart_services.ps1` (18) → behalten ✅
- `start_ingestion_gui.ps1` (21) → behalten ✅

---

## 🔒 .gitignore Erweiterungen

**Hinzufügen:**

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Runtime Data
data/secrets/
data/uploads/
data/logs/
logs/

# Temporary Files
*.tmp
*.temp
*.bak
*~

# OS
.DS_Store
Thumbs.db
```

---

## 📦 Requirements Konsolidierung

**Aktuell:**
- `requirements.txt` (minimal - 1KB)
- `requirements-dev.txt` (Dev Dependencies)
- `requirements-curation-nlp.txt` (NLP Dependencies)

**Option 1: Konsolidieren (Empfohlen)**

```
requirements.txt              # Alle Dependencies (Production + Dev + NLP)
```

**Option 2: Kategorisieren**

```
requirements/
├─ base.txt                   # Base Dependencies
├─ dev.txt                    # Dev Dependencies
├─ nlp.txt                    # NLP Dependencies
└─ production.txt             # Production (base + nlp)
```

**Empfehlung:** Option 1 (einfacher für kleine Projekte)

---

## ✅ Validation Rules

### Nach Refactoring prüfen:

1. **Root Directory:**
   - Max 10 Dateien ✅
   - Nur README, QUICKSTART, CHANGELOG, docker-compose, requirements, sitecustomize ✅

2. **Dateinamen:**
   - Max 30 Zeichen (ohne Extension) ✅
   - snake_case für Python ✅
   - Keine Versionsnummern (_v3_4_9, _phase4) ✅
   - Keine Duplikat-Suffixe (_0, _BACKUP, _old) ✅

3. **Imports:**
   - Alle funktionieren nach Umzug ✅
   - `python -m py_compile` für alle .py Dateien ✅

4. **Tests:**
   - `pytest tests/` → All PASS ✅
   - Keine Pfad-Fehler ✅

5. **Git History:**
   - `git log --follow` zeigt komplette History ✅
   - Alle Renames mit `git mv` ✅

---

## 🚀 Nächste Schritte

1. **Task #2:** ✅ COMPLETE - Target Structure erstellt
2. **Task #3:** Create Rename Mapping (CSV mit allen 51 Root-Dateien + Git Commands)
3. **Task 4-11:** Consolidation Phase
4. **Task 12:** Git Operations (batch git mv)
5. **Task 13:** Import Updates (automated + manual)
6. **Task 14:** Archive & Cleanup
7. **Task 15-17:** Validation & Deployment

---

**Dokumentiert:** 2025-10-24  
**Autor:** GitHub Copilot  
**Status:** ✅ COMPLETE - Ready for Task #3 (Create Rename Mapping)
