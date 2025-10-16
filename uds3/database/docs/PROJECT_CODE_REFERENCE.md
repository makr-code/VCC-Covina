PROJECT: Covina `database` package

Zweck
-----
Das `database`-Paket stellt eine abstrakte, adaptierbare Schicht für verschiedene
Datenbanktypen (Vektor-, Graph-, Relationale-, Key-Value-, File-Storage-) bereit
und kapselt Adapter-Implementierungen, Governance-Hooks und ein Saga-Orchestrator
für verteilte, fehlertolerante Operationen über heterogene Backends.

Ziel dieser Referenz
--------------------
Diese Datei fasst die wichtigsten Quell-Dateien zusammen, nennt die Haupt-APIs,
kurze Hinweise zur Verwendung, Testabdeckung und aktuellen Status. Nutze das
als schnelles Nachschlagewerk, bevor du tiefer in einzelne Module einsteigst.

Hinweis: Diese Datei wurde automatisch anhand des aktuellen Standes des Repos
erstellt (Datum: 2025-10-01).

Dateien (Top-Level)
-------------------

- `__init__.py`
  - Zweck: Package-Inhalts-Initialisierung. Exportiert zentrale Komponenten des
    `database`-Moduls.
  - Haupt-API: Package-Imports
  - Tests: indirekt durch mehrere Tests genutzt
  - Status: OK

 `adapter_governance.py`
  - Zweck: Implementiert Policy-Checks und Governance-Logik zur Autorisierung
    von Backend-Operationen (z. B. ob `vector.create` erlaubt ist).
  - Haupt-API: `AdapterGovernance` Klasse, Exceptions (`AdapterGovernanceError`)
  - Tests: partiell durch Saga-Tests abgedeckt
  - Status: Produktiv/aktiv
  - Mehr Details: `docs/adapter_governance.md`

- `config.py`
  - Zweck: Zentrale Konfigurations-Provider; bietet `get_database_backend_dict()`
    und Hilfsfunktionen zum Laden von `server_config.json`.
  - Haupt-API: Konfigurations-Dictionary, Factory-Helfer
  - Tests: genutzt in Manager- und Start-Tests
  - Status: OK; sollte Umgebungsoverride-Dokumentation enthalten
  - Mehr Details: `docs/config.md`

- `database_api_base.py`
  - Zweck: Abstrakte Basisklassen für Backends: `DatabaseBackend`, `VectorDatabaseBackend`,
    `GraphDatabaseBackend`, `RelationalDatabaseBackend` usw.; enthält adaptive batch
    processor primitives und UDS3-Integrationspunkte.
  - Haupt-API: Basisklassen und methodenverträge (`connect`, `is_available`, ...)
  - Tests: Verwendet in Unit-Tests zur Adapter-Discovery
  - Status: Kernmodul; erweiterbar
  - Mehr Details: `docs/database_api_base.md`

- `database_api.py`
  - Zweck: (Wrapper/Kompatibilität) Hohe Abstraktionen / alte APIs (falls vorhanden)
  - Haupt-API: Kompatibilitäts-Funktionen
  - Tests: gering
  - Status: Backward-compat
  - Mehr Details: `docs/database_api.md`

- `database_api_chromadb.py`, `database_api_neo4j.py`, `database_api_couchdb.py`,
  `database_api_postgresql.py`, `database_api_sqlite.py`, etc.
  - Zweck: Konkrete Adapter für spezifizierte Backends (Vektor/Graph/Relational/KeyValue).
  - Haupt-API: Concrete Backend-Klassen mit `connect`, `disconnect`, `is_available` und backend-spezifischen Methoden.
  - Tests: Adapter-Instantiation und Basistests vorhanden; volle E2E gegen echte Dienste optional
  - Status: Adapter-spezifisch; viele setzen Migration von import-time init nach `connect()` um.
  - Mehr Details (per Adapter):
    - `docs/database_api_chromadb.md`
    - `docs/database_api_neo4j.md`
    - `docs/database_api_couchdb.md`
    - `docs/database_api_postgresql.md`
    - `docs/database_api_sqlite.md`
    - `docs/database_api_keyvalue_postgresql.md`
    - `docs/database_api_redis.md`
    - `docs/database_api_weaviate.md`
    - `docs/database_api_mongodb.md`

- `database_manager.py`
  - Zweck: Zentraler Manager für Backend-Instanzen; erstellt Adapter-Instanzen aus
    `config`, kann Backends starten/stoppen, sammelt Status, stellt Governance-Hooks
    bereit und bietet `start_all_backends` zur gesteuerten Initialisierung.
  - Haupt-API: `DatabaseManager` (Konstruktor, `start_all_backends`, `get_*_backend`, `test_operation`, `stop_all_backends`), `get_database_manager()` globale Factory
  - Tests: umfangreiche Unit-Tests und Integrationstests vorhanden (`tests/test_database_manager.py`)
  - Status: Aktiv; autostart-Feature und ThreadPool-Start implementiert
  - Mehr Details: `docs/database_manager.md`

- `saga_crud.py`
  - Zweck: Saga-freundliche CRUD-Helfer; standardisierte `CrudResult`-Antworten,
    Observability-Helpers (identity traces/metrics) und `write_saga_event`.
  - Haupt-API: `SagaDatabaseCRUD` Klasse, Methoden für vector/relational CRUD
  - Tests: `tests/test_saga_events.py` und weitere Saga-Tests
  - Status: Implementiert; resilient gegen verschiedene relational backends
  - Mehr Details: `docs/saga_crud.md`

- `saga_compensations.py`
  - Zweck: Registry von Kompensations-Handlern und Standard-Implementierungen
    (z. B. relational_delete).
  - Haupt-API: `register(name, handler)`, `get(name)` und Default-Handler
  - Tests: `tests/test_saga_compensations.py`
  - Status: Implementiert
  - Mehr Details: `docs/saga_compensations.md`

- `saga_orchestrator.py`
  - Zweck: Orchestriert Saga-Ausführung: `create_saga`, `execute_saga`, `resume_saga`,
    `compensate_saga`, `abort_saga` samt Locking/Idempotency.
  - Haupt-API: `SagaOrchestrator` Klasse
  - Tests: Integration-Tests unter `tests/` (happy/failure/resume)
  - Status: Implementiert und getestet (local SQLite)
  - Mehr Details: `docs/saga_orchestrator.md`

- `saga_recovery_worker.py`
  - Zweck: Background/CLI-Worker zum periodischen Wiederaufnehmen offener Sagas.
  - Haupt-API: `SagaRecoveryWorker.run_once()`
  - Tests: `tests/test_saga_recovery_worker.py`
  - Status: Implementiert
  - Mehr Details: `docs/saga_recovery_worker.md`

- `scripts/`
  - Zweck: Hilfsskripte (z. B. `run_saga_migrations.py`) zum idempotenten Anlegen
    der notwendigen Tabellen/Indizes.
  - Status: Ergänzend; empfohlen vor E2E Tests oder Prod-Runs
  - Mehr Details: `docs/scripts_run_saga_migrations.md`

- `tests/`
  - Zweck: pytest-Suite mit Unit- und Integration-Tests für Manager, Saga,
    Adapter-Discovery und Basis-Funktionalität.
  - Status: Gut abgedeckt für core features; E2E für externe Dienste optional

Docs / Empfehlungen
-------------------
- `docs/PROJECT_CODE_REFERENCE.md` (diese Datei) bietet einen Schnelleinstieg.
- Nächster Schritt: Falls gewünscht, splitte diese Referenz automatisch in
  Einzeldokumente pro Datei unter `docs/` und erweitere mit API-Signaturen.

Anmerkungen
-----------
- Viele Adapter vermeiden jetzt treiber-lastige Importe beim Modul-Import und
  initialisieren erst in `connect()`; das ist testfreundlich und reduziert
  Import-Zeit-Fehler.
- Einige Tests (z. B. die Saga-Suite) hängen an idempotenten Migrations-Helfern;
  `db_migrations.py` stellt nun einfache, idempotente Helpers bereit.

"Try it" (lokal)
-----------------
Im Projekt-Root:

```powershell
python -m pytest database/tests -q
```

Wenn du möchtest, splitte ich diese Datei in eine Sammlung einzelner `docs/*.md`
Dateien (z. B. `docs/database_manager.md`, `docs/saga_orchestrator.md`) und
füge kurze Codebeispiele und Signaturen hinzu.
