# Modulare Ingestion Architecture für UDS3/Covina - Todo Liste

**Ziel:** Refactoring der bestehenden Covina-Ingestion zu einer granularen, modularen, chunk-basierten Architektur mit sauberer UDS3-Integration.

**Status:** Planung/Vorbereitung  
**Datum:** 29. Oktober 2025

## Übersicht

Die aktuelle Implementierung soll zu einer flexiblen, chunk-basierten, UDS3-gekoppelten Polyglot-Ingestion umgebaut werden, die sicher, idempotent, testbar und OOP-konform arbeitet.

## Status Quo Analyse

### ✅ Vorhandene Basis
- **UDS3 Framework:** Dedizierte Bibliothek (VCC-UDS3) mit SAGA/Orchestrator, Schema-Mixins, Search API, DB-Abstraktionen
- **Modulare Struktur:** `ingestion/` mit handlers/, retrieval/, services/
- **Python Integration:** sitecustomize.py ermöglicht UDS3 Import
- **Geplante Integration:** backend/core/polyglot.py verweist auf UDS3-SAGA

### ❌ Hauptprobleme
- **Hardcoded Konfigurationen:** ChromaRemoteVectorBackend und andere Backends inline initialisiert
- **Monolithisches Design:** backend/ingestion.py (4500+ Zeilen) mischt Bootstrapping und Logik
- **Fehlende Contracts:** Keine standardisierten Writer/Extractor/Classifier Interfaces für UDS3
- **Exception Handling:** Defensive "except Exception" Blöcke können Fehler verschlucken
- **Audit Trail:** Uneinheitliche Provenance-Aufzeichnung für Chunk-Level Entscheidungen
- **Test Coverage:** Contract-Tests gegen UDS3-Adapter fehlen

## Zielarchitektur

**Chunk-First Verarbeitung:** Jedes Dokument wird in semantische Chunks aufgeteilt und einzeln klassifiziert
**UDS3 Integration:** Ausschließliche Nutzung von UDS3 Writer-Adaptern mit definierten JSON-Contracts
**Idempotenz & Provenance:** Deterministische Chunk-IDs, vollständige Audit-Trails
**Modularität:** OOP-Design, testbar, plugin-fähig, konfigurierbar via YAML/ENV
**Separation of Concerns:** Launcher nur für Bootstrapping, Pipeline für Geschäftslogik

## Todo Items

### 🔥 Phase A: Grundlegende Refactorings (Hohe Priorität)
- [ ] **A1: Bootstrapping Extraktion**
  - **Was:** backend/ingestion.py auf FastAPI/uvicorn Launcher reduzieren
  - **Ziel:** Produktionslogik → ingestion/launchers/ oder backends/factory/
  - **Aufwand:** 2-3 Tage
  - **Dateien:** backend/ingestion.py (4500+ Zeilen), ingestion/factory.py (neu)
  - **Tests:** Unit Tests für Pipeline Factory mit Mock

- [ ] **A2: Konfigurationszentralisierung**
  - **Was:** config/ingestion.yaml + config/loader.py mit Environment-Interpolation
  - **Ziel:** Eliminierung hardcoded Endpoints (192.168.178.94, etc.)
  - **Aufwand:** 1-2 Tage  
  - **Dateien:** config/ingestion.yaml (neu), config/loader.py (neu)
  - **Migration:** Alle inline configs in ingestion/ und backend/

- [ ] **A3: Core Interfaces & ChunkRouter**  
  - **Was:** ingestion/core/interfaces.py + ingestion/core/router.py
  - **Ziel:** Chunk, IngestResult, Writer, Extractor, Classifier Protocols
  - **Aufwand:** 2-3 Tage
  - **Dateien:** ingestion/core/interfaces.py (neu), ingestion/core/router.py (neu)
  - **Tests:** Contract Unit Tests für Router mit Mock Writers

### ⚡ Phase B: UDS3 Adapter & Contract Enforcement (Sehr Wichtig)
- [ ] **B1: UDS3 Writer Adapter Implementation**
  - **Was:** ingestion/writers/uds3_adapter.py mit 4 Writer-Klassen
  - **Ziel:** RelationalUDS3Writer, GraphUDS3Writer, VectorUDS3Writer, BlobUDS3Writer
  - **Aufwand:** 3-4 Tage
  - **Integration:** UDS3 Python Package (preferred) oder HTTP API Gateway
  - **Tests:** Contract Tests mit requests-mock für JSON Payloads + Provenance

- [ ] **B2: Provenance & Idempotenz Enforcement**
  - **Was:** Deterministische Chunk-IDs (sha256(source_id + chunk_index))
  - **Payload:** chunk_id + classifier_reason + commit_hash + timestamp
  - **Aufwand:** 1-2 Tage
  - **Dateien:** ingestion/core/router.py, alle Writer-Adapter
  - **Ziel:** Reconciliation, Deduplication, Audit Trail

### 🔧 Phase C: Chunk Handling & Extractors (Mittel)
- [ ] **C1: Chunk Model & Pipeline Standardisierung**
  - **Was:** ingestion/preprocess.py mit Layout-Aware Chunkern
  - **Features:** DOCX Tables, PDF Pages + Table Detection, Semantic Split
  - **Aufwand:** 3-5 Tage
  - **Ziel:** Konsistente Chunk IDs & Metadata (page, bbox)
  - **Tests:** Unit Tests für Chunking Heuristiken

- [ ] **C2: Classifier Strategy & LLM Fallback**  
  - **Was:** Classifier Interface + HeuristicClassifier + LLMFallbackClassifier
  - **Ziel:** Minimierung LLM Calls, deterministische & auditierbare Entscheidungen
  - **Aufwand:** 2-3 Tage
  - **Dateien:** ingestion/classifiers/ (heuristic.py, ml_wrapper.py, llm_fallback.py)
  - **Tests:** Deterministische Tests für Heuristiken, Mock LLM Responses

- [ ] **C3: Format-Spezifische Extractors**
  - **Ziel:** Strukturierte Daten für UDS3 Writers
  - **Aufwand:** 1-2 Tage pro Extractor (7 total = 7-14 Tage)
  - **Module:**
    - [ ] docx_extractor.py (Tables/Images/Embedded Spreadsheets)
    - [ ] shapefile_extractor.py (Fiona → Attributes + Geometry)  
    - [ ] json_extractor.py (Array Detection, Schema Flatten)
    - [ ] markdown_extractor.py (Headings, Legal Paragraphs)
    - [ ] image_extractor.py (EXIF + OCR)
    - [ ] dbfile_extractor.py (ReadOnly SQLite Schema + Sample Rows)
    - [ ] email_extractor.py (MIME Parse + Recursive Attachments)
  - **Tests:** Unit Tests mit Representative Sample Files (Fixtures)

### 🛡️ Phase D: SAGA, Reconciliation & Observability (Hoch)
- [ ] **D1: UDS3 SAGA Integration**
  - **Was:** ingestion/core/saga_adapter.py als Wrapper für uds3.saga_* Classes
  - **Ziel:** Multi-Store Operations mit Strong Consistency, sonst Best-Effort
  - **Aufwand:** 3-4 Tage
  - **Update:** ChunkRouter für optionale SAGA Usage
  - **Tests:** Integration Test mit UDS3 Stub + Compensation Verification

- [ ] **D2: Audit Log & Dead Letter Queue**
  - **Was:** ingestion/audit.py + ingestion/reconciliation_worker.py
  - **Ziel:** DLQ für Failed Chunks + Reconciliation Worker
  - **Aufwand:** 2-3 Tage
  - **Integration:** UDS3 Audit Endpoints oder Postgres via UDS3 Adapter
  - **Tests:** Unit Tests für Audit + Simulated Failure/Reconciliation

- [ ] **D3: Observability & Metrics**
  - **Was:** ingestion/metrics.py mit Prometheus Integration
  - **Metriken:** ingest_latency_histogram, routed_counters, partial_errors
  - **Aufwand:** 1-2 Tage
  - **Integration:** Router & Writers, Dashboard Docs
  - **Tests:** Smoke Test für Metrics Export Endpoint

### 🔒 Phase E: Security & Configuration (Mittel)
- [ ] **E1: Hardcoded Credentials Audit**
  - **Was:** Codebase-Audit für hardcoded IPs/Credentials (192.168.178.94, etc.)
  - **Ersatz:** Config Loader + Environment Variables + Secrets Manager
  - **Aufwand:** 1-2 Tage
  - **Tools:** Grep Search + Static Code Scanning
  - **Tests:** Environment Variable Tests

- [ ] **E2: Secure UDS3 Communications**
  - **Was:** UDS3 Python Client mit mTLS Support
  - **Features:** TLS + Token Auth + Retry/Backoff + Circuit Breaker
  - **Aufwand:** 1-2 Tage
  - **Dateien:** ingestion/writers/uds3_adapter.py
  - **Tests:** Integration mit TLS Stub + Unit Tests für Retry Logic

### ✅ Phase F: Tests & CI (Hoch)
- [ ] **F1: UDS3 Contract Tests**
  - **Was:** tests/ingestion/test_uds3_contracts.py mit HTTP Mock Server
  - **Ziel:** JSON Body Validation gegen UDS3 Contract Schemas
  - **Aufwand:** 2-3 Tage
  - **Validation:** Provenance Keys + external_id = deterministic_chunk_id
  - **Tools:** responses oder requests-mock

- [ ] **F2: Integration Smoke Tests**  
  - **Was:** dev/docker-compose.ingest-test.yml für Test Environment
  - **Stack:** UDS3 Stub + PostgreSQL + Neo4j + Vector Stub
  - **Aufwand:** 2-3 Tage
  - **Tests:** End-to-End Ingestion (Word Doc + Shapefile)
  - **CI:** Automatisierte Pipeline Integration

## Migration & Rollout Plan

### Phase 0: Vorbereitung (1-2 Tage)
- Neue ingestion/core Interfaces & Writer Adapters hinzufügen (non-invasiv)
- Config Template erstellen

### Phase 1: Parallel Run (2-4 Tage)  
- ChunkRouter & Factory verdrahten, alte Handler NICHT ersetzen
- Feature Flag: `INGEST_NEW_ROUTER=false`
- Kleiner Prozentsatz der Ingests zur neuen Pipeline routen
- Audits aufzeichnen und Outputs vergleichen

### Phase 2: Handler Migration (1-3 Wochen)
- Handler-by-Handler auf Extractor/Writer Protocol migrieren
- Compatibility Layer bis alle migriert
- Provenance Output sicherstellen

### Phase 3: SAGA Aktivierung (1-3 Tage)
- UDS3 SAGA für Multi-Store Writes aktivieren
- Integration Tests ausführen

### Phase 4: Decommission (1 Tag)
- Alte Code Paths entfernen
- Cleanup durchführen

### Phase 5: Monitor & Iterate (Ongoing)
- Metrics überwachen
- Edge Cases für Formate behandeln
- ML Classifier Dataset erweitern

## Pull Request Breakdown

**Ziel:** Kleine, reviewbare PRs für inkrementelle Integration

- **PR 1:** Core Interfaces + ChunkRouter + Tests (1-2 Tage)
  - `ingestion/core/interfaces.py`
  - `ingestion/core/router.py`  
  - Unit Tests für Router

- **PR 2:** UDS3 Adapter + Config + Contract Tests (1-2 Tage)
  - `ingestion/writers/uds3_adapter.py`
  - `config/ingestion.yaml`
  - Contract Tests

- **PR 3:** Preprocess Chunker + DOCX Extractor (2-4 Tage)
  - `ingestion/preprocess.py`
  - `ingestion/extractors/docx_extractor.py`
  - Unit Tests + Fixtures

- **PR 4:** Factory Integration via Feature Flag (1 Tag)
  - `backend/ingestion.py` Update (non-invasiv)
  - `ingestion/factory.py`

- **PR 5-11:** Extractors (je 1-2 Tage)
  - Shapefile, JSON, Markdown, Image, DBFile, Email
  - Jeweils eigene PRs

- **PR 12:** SAGA Adapter + Reconciliation Worker (3-7 Tage)
  - `ingestion/core/saga_adapter.py`
  - `ingestion/reconciliation_worker.py`
  - Integration Tests

- **PR 13:** Metrics + Prometheus + Docker-Compose (2-4 Tage)
  - `ingestion/metrics.py`
  - `dev/docker-compose.ingest-test.yml`
  - CI Update

## Aufwandsschätzung

### Minimal Safe MVP
**Umfang:** Interfaces + Router + UDS3 Adapters + Config + Unit Tests  
**Aufwand:** 3-7 Personentage  
**Deliverables:**
- Core Contracts definiert
- UDS3 Integration funktional
- Konfiguration externalisiert

### Full Migration
**Umfang:** Alle Handler + Extractors + SAGA + Integration Tests + Schema Review UI  
**Aufwand:** 3-6 Wochen (abhängig von Handler-Anzahl und Dokumenten-Komplexität)  
**Deliverables:**
- Vollständige Extractor-Suite
- SAGA Orchestration
- Production-Ready Pipeline

## Kritische Herausforderungen & QA

### 🔴 Schema Inference
- **Problem:** Messy Tables/DOCX erfordern LLM Fallback
- **Lösung:** Human Review Queue, kein Auto-Commit bei Ambiguität
- **Tests:** Mock LLM Responses + Manual Review Workflow

### 🗺️ Shapefile CRS
- **Problem:** Fehlende .prj Files
- **Lösung:** Manual Intervention Required + Schema Review
- **Tests:** CRS Detection + Transformation Tests

### 💾 DB Files  
- **Problem:** SQL Injection Risk
- **Lösung:** ReadOnly Mode + Schema Export + Whitelisted Tables
- **Tests:** SQLite Readonly Tests + Schema Extraction

### 📧 Email Recursion
- **Problem:** Unbegrenzte Attachment Depth
- **Lösung:** Depth Limit + Resource Caps
- **Tests:** Recursive Email Fixtures

### 🔒 PII Handling
- **Problem:** PII in Embeddings
- **Lösung:** Configurable Redaction/Pseudonymization vor Embedding
- **Tests:** PII Detection + Redaction Validation

### ⚡ Performance
- **Problem:** Large Tables/Documents
- **Lösung:** Batch Embeddings + Vector Upserts + COPY/Bulk UDS3 Endpoints
- **Tests:** Load Tests mit Large Datasets

### 📋 Contract Drift
- **Problem:** UDS3 API Changes
- **Lösung:** docs/uds3_contracts.md + Contract Test Suite in CI
- **Tests:** Schema Validation gegen Versioned Contracts

## Nächste Schritte

### Option A: Quick Start PR (Empfohlen)
**Umfang:** Non-invasive PR mit Core Interfaces + Router + UDS3 Adapter Stub  
**Aufwand:** 1-2 Tage  
**Dateien:**
- `ingestion/core/interfaces.py`
- `ingestion/core/router.py`  
- `ingestion/writers/uds3_adapter.py` (Stub)
- Unit Tests

**Vorteil:** Definiert Contracts, klein genug für schnelles Review, keine Breaking Changes

### Option B: Architecture Document
**Umfang:** Detaillierte Architektur + Sequence Diagrams + Top-10 QA Tests  
**Aufwand:** 2-3 Tage  
**Deliverables:**
- Architecture Decision Records (ADRs)
- UML Sequence Diagrams
- Test Strategy Document

---

**Empfehlung:** Starte mit Option A für schnellen, messbaren Fortschritt. Option B parallel als Living Documentation.