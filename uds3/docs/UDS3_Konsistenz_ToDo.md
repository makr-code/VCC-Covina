# UDS3 Konsistenzanalyse und ToDo-Plan

*Stand: 28.09.2025*

Dieses Dokument fasst den aktuellen Umsetzungsstand der UDS3-Module (`uds3_core.py` u.a.) im Hinblick auf das "Konzept zur datenbankübergreifenden Konsistenz" zusammen und leitet priorisierte ToDos für eine konsistente Erweiterung ab.

## 1. Abgleich mit dem Konzept

### 1.1 Polyglot-Persistence-Ansatz
- **Status im Code**: `UnifiedDatabaseStrategy` beschreibt Rollen, Schemas und CRUD-Strategien für Vector-, Graph-, Relational- und File-Storage-Datenbanken. Über `SagaDatabaseCRUD` werden reale Adapter aus `database/` via `DatabaseManager` angebunden; fehlende optionale Backends (Vector/Graph/File) werden als `skipped` markiert und sauber kompensiert. Die relationale Persistenz (`documents_metadata`) ist standardmäßig aktiv, da `config` seit 27.09.2025 das SQLite-Backend einschaltet. Die Cross-DB-Mapping-Struktur (`self.document_mapping`) synchronisiert Backend-IDs in den Identity-Service.
- **Gap zum Konzept**: Es fehlen programmatische Guardrails, um die Rollenverteilung (kein Content im Graph usw.) strikt durchzusetzen, sowie weitergehende Governance-Regeln und persistente Konsistenzmetriken. Dokument-Mappings werden derzeit nur im Identity-Service abgelegt; ein separates Reporting-Backend steht noch aus.

### 1.2 UUID/Aktenzeichen-Mapping
- **Status im Code**: Sicherheitsmanager (`uds3_security.py`) generiert UUID-basierte `document_id`s. Fallback in `UnifiedDatabaseStrategy._generate_document_id` erzeugt jedoch Hash-basierte IDs. Eine persistente Mapping-Tabelle existiert nicht; `document_mapping` wird nicht gespeichert. Aktenzeichen werden nirgendwo extrahiert oder geführt.
- **Gap zum Konzept**: Das duale Identitätskonzept (UUID ↔ Aktenzeichen) fehlt vollständig. Die relationale Schema-Definition enthält keine Tabelle `identities` bzw. `aktenzeichen_mapping`. Es gibt keine APIs, um Aktenzeichen zu registrieren oder abzurufen.

### 1.3 SAGA/Verteilte Transaktionen
- **Status im Code**: `uds3_saga_orchestrator.py` stellt einen persistenten Saga-Orchestrator mit Event-Logging und Kompensationslogik bereit. `create_secure_document`, `update_secure_document` und `delete_secure_document` nutzen definierte Schrittfolgen (Security & Identity, Vector, Graph, Relational, File, Identity-Mapping, Validation). Aktionen und Kompensationen verwenden `SagaDatabaseCRUD`; optionale Backends werden als `skipped` dokumentiert, Validation & Cleanup berücksichtigen diesen Status. Bei fehlendem Orchestrator greift eine lokale Saga-Engine identischer Struktur. Details siehe `docs/SAGA_PATTERN_IMPLEMENTATION.md`.
- **Gap zum Konzept**: Erweiterte Observability (Audit-Pipeline, Retry-Strategien, Metriken) und proaktive Governance-Regeln für Saga-Abhängigkeiten stehen noch aus.

## 2. Priorisierte ToDo-Liste für eine konsistente Erweiterung

| Prio | Aufgabe | Beschreibung & Deliverables | Betroffene Module |
|------|---------|-----------------------------|--------------------|
| 1 | [x] **Identity Service & Mapping-Tabelle** | Neues Modul `uds3_identity_service.py` implementieren. Relationale Tabelle `administrative_identities (uuid PRIMARY KEY, aktenzeichen TEXT, status, created_at, updated_at)` anlegen. Service-API für `create_uuid()`, `register_aktenzeichen()`, `resolve_by_uuid()/aktenzeichen`. Migration der bisherigen `document_id`-Erzeugung auf diesen Service. | `uds3_core.py`, `uds3_security.py`, `database/database_api_*`, neuer Service |
| 1 | [x] **Relationale Schema-Anpassung** | `UnifiedDatabaseStrategy._create_relational_schema` erweitern um Mapping-Tabelle, Audit-Log und Foreign Keys. Synchronisation mit `database/database_api_postgresql.py` sicherstellen. | `uds3_core.py`, `database/database_api_postgresql.py` |
| 1 | [x] **Aktenzeichen-Extraction in Ingestion** | `CoreIngestHandler` ruft jetzt `ingestion.services.aktenzeichen` auf, erkennt Aktenzeichen in Analyse-/Preview-Texten, generiert UUID-basierte Fallbacks und registriert alles beim Identity Service. Metadaten werden angereichert, Identity-Payloads persistiert; Regressionstests (`tests/test_core_ingest_aktenzeichen.py`) sichern beide Pfade ab. | `ingestion_core.py`, `ingestion/services/aktenzeichen.py`, Identity Service |
| 2 | [x] **Persistentes Cross-DB-Mapping** | `document_mapping` als `administrative_identities`-Erweiterung persistieren (Spalten für vector_id, graph_id, relational_id, file_storage_id). Update-Methoden in CRUD-Flows einbauen. | `uds3_core.py`, relational DB |
| 2 | [x] **Saga-Orchestrator Basis** | Neues Modul `uds3_saga_orchestrator.py` erstellen. Einbettung in vorhandenen Core-Orchestrator (ggf. Integration mit `uds3_follow_up_orchestrator`). Funktionen: Saga-Definition, State Store (relationale Tabelle `uds3_sagas`), Kompensations-Callbacks. | Neuer Orchestrator, `uds3_core.py`, `database/` |
| 2 | [x] **Saga-Definition "NeuesDokumentErfassen"** | Schrittfolge implementiert (Security/Identity → Vector → Graph → Relational → File → Identity-Mapping → Validation) und mit `SagaDatabaseCRUD` an echte Adapter angebunden. Optional fehlende Backends werden als `skipped` markiert; Kompensationen berücksichtigen den Status. Tests (Dummy-Orchestrator & CRUD-Fakes) vorhanden. | `uds3_saga_orchestrator.py`, `uds3_core.py`, `database/` |
| 2 | [x] **Saga-Definitionen für Update/Delete** | Neue Sagas `update_secure_document` und `delete_secure_document` inklusive Kompensationen und Identity-Hand-off implementiert; orchestratorische Pfade laufen über `UDS3SagaOrchestrator`, Tests (`tests/test_saga_orchestrator.py`) prüfen Update- und Delete-Flows mit Stub-CRUD. | `uds3_core.py`, `tests/test_saga_orchestrator.py` |
| 3 | **Adapter-Härtung & Governance Enforcement** | 1) Adapter-Konfiguration zentralisieren (`database_manager`) und nur freigegebene Operationen exposed; 2) Validatoren implementieren, die Payloads vor Persistierung prüfen (keine Volltexte im Graph, keine Binärdaten im Relational-Store); 3) Governance-Checks in `UnifiedDatabaseStrategy` verankern (Warnings → Exceptions). **Status:** Basis-Governance via `SagaDatabaseCRUD` & `AdapterGovernance` aktiv, Observability protokolliert Governance-Blocks; automatisierte Payload-Tests folgen. | `uds3_core.py`, `database/database_manager.py`, Adapter |
| 3 | **Audit & Monitoring** | 1) Relationale Tabellen `uds3_audit_log`, `uds3_saga_metrics` entwerfen (Status: Schema Draft in Arbeit, Anforderungen gesammelt); 2) Saga-Orchestrator mit strukturiertem Logging + korrelierten Trace-IDs ausstatten; 3) Exportpfad in bestehende Monitoring-Pipeline (OpenTelemetry/ELK) vorbereiten. | Neuer Audit-Mechanismus, `uds3_saga_orchestrator.py`, Observability |
| 3 | **Test- & Validierungs-Setup** | 1) End-to-End-Tests für Identity ↔ Saga ↔ Adapter-Kette (inkl. Kompensation) erstellen; 2) Contract-Tests für jeden Adapter schreiben; 3) CI-Workflow um Schema-Diff-Check & Smoke-Test (`pytest -m smoke`) erweitern. | `tests/`, CI-Pipeline |

## 3. Empfohlene Folgeaktionen
- **Architektur-Review** mit Stakeholdern (IT, Fachbereich, Rechtsabteilung) zur Abnahme der Saga-Flows und Governance-Regeln.
- **Roadmap-Planung**: Aufgaben in Sprints priorisieren (zuerst Identity/Mappings, dann Saga-Orchestrator, anschließend Adapter-Härtung).
- **Dokumentation & Schulung**: Bedien- und Betriebsdokumente für Identity-Service und SAGA-Orchestrator bereitstellen; Übergabe an DevOps/Operations.

## 4. Umsetzungsstand (28.09.2025)
- ✅ Identity-Service (`uds3_identity_service.py`) erstellt – umfasst UUID-/Aktenzeichen-Management, Mapping-Persistenz und Audit-Logging.
- ✅ Relationale Schemaerweiterung – neue Tabellen `administrative_identities`, `administrative_identity_mappings`, `administrative_identity_audit` in Strategie & SQLite-Backend.
- ✅ UDS3 Core Integration – `create_secure_document` nutzt Identity-Service, persistiert Backend-IDs und liefert Identity-Metadaten.
- ✅ Ingestion Aktenzeichen-Handling – `CoreIngestHandler` nutzt `ingestion.services.aktenzeichen`, erkennt Aktenzeichen, generiert Fallbacks und registriert alles beim Identity-Service; Metadaten & Identity-Payloads werden konsistent gesetzt.
- ✅ Tests – `tests/test_identity_service.py` validiert Identity-Logik; `tests/test_core_ingest_aktenzeichen.py` prüft Aktenzeichen-Erkennung und Fallback-Generierung end-to-end.
- ✅ Saga-Orchestrator – Modul `uds3_saga_orchestrator.py` implementiert, inkl. relationaler Persistenz (`uds3_sagas`, `uds3_saga_events`) und Kompensationslogik.
- ✅ Saga-gestützte Dokumenterstellung – `create_secure_document` führt Schritte über den Orchestrator aus; Fallback-Engine für Umgebungen ohne Orchestrator vorhanden.
- ✅ Update-/Delete-Sagas – `update_secure_document` und `delete_secure_document` orchestrieren End-to-End-Flows (Graph, Vector, Relational, File) samt Kompensation und Identity-Hand-off.
- ✅ Tests (SAGA) – `tests/test_saga_orchestrator.py` prüft Ausführung, Kompensation und Core-Integration via Dummy-Orchestrator für Create-, Update- und Delete-Pfade.
- ✅ Observability-Governance – `SagaDatabaseCRUD` markiert Governance-Verstöße (`governance_blocked`) und schreibt Identitätsmetriken (`*.attempt`, `*.error`, `*.governance_blocked`); Tests (`tests/test_saga_crud.py`) decken Happy Path, Fehler- und Governance-Fälle ab.
- 📄 SAGA-Pattern-Dokumentation – `docs/SAGA_PATTERN_IMPLEMENTATION.md` beschreibt Komponenten, Schrittfolge, Optional-Handling und Testbefehle.
- 📄 Design-Referenz `docs/UDS3_Identity_Service_Design.md` beschreibt Architektur und Schnittstellen.

## 5. Kurzfristige Arbeitsplanung (KW 40–41/2025)
- **Adapter-Governance**: Proof-of-Concept für Validierungs-Layer im `database_manager` implementieren, anschließend Feature-Flag in `UnifiedDatabaseStrategy` aktivieren.
- **Observability**: Datenbank-Migrationsskript für `uds3_audit_log`/`uds3_saga_metrics` vorbereiten und Logging-Hooks in `uds3_saga_orchestrator.py` verdrahten.
	- *Update:* Identitätsbezogene Governance-Metriken sind implementiert; nächster Schritt ist Audit-/Saga-Metrikpersistenz.
	- *ToDo:* Schema-Draft für `uds3_saga_metrics` (Spalten `identity_key`, `saga_name`, `stage`, `status`, `duration_ms`, `observed_at`) und `uds3_audit_log` (Audit-ID, Identitätskontext, Aktion, Actor, Payload-Hash) finalisieren; Migration + Testplan vorbereiten.
- **Testautomatisierung**: Neues Pytest-Marker-Set (`smoke`, `contracts`) definieren und GitHub Actions Workflow um entsprechende Jobs erweitern.
- **Review & Abnahme**: Ergebnisse in Technical Steering am 03.10.2025 vorstellen, Feedback für Folgeiteration einsammeln.

---
*Vorbereitet von GitHub Copilot (Assistenz).*
