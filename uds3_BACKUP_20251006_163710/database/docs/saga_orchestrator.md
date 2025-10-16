# `saga_orchestrator.py`

Kurzbeschreibung
-----------------
Orchestrator für Saga-Ausführung: verwaltet Saga-Lifecycle (create, execute,
resume, compensate, abort). Nutzt `SagaDatabaseCRUD` für Event-Persistence und
`adapter_governance` für Policy-Checks.

Analyse
-------
Die Orchestrator-Logik kontrolliert die sequentielle Ausführung der Steps,
schreibt vorher PENDING-Events, führt die Remote-Operationen aus (über
`DatabaseManager`-Backends) und schreibt anschliessend SUCCESS/FAIL. Bei Fehlern
wird eine Kompensation in umgekehrter Reihenfolge aufgerufen.

Haupt-APIs
----------
- `create_saga(name, steps, trace_id=None) -> saga_id`
- `execute_saga(saga_id, max_retries=3, start_at=None) -> Dict` — führt eine Saga aus
- `resume_saga(saga_id)` — Wiederaufnahme halb ausgeführter Sagas
- `compensate_saga(saga_id, executed_steps=None)` — führt Kompensationen aus
- `abort_saga(saga_id, reason='')` — markiert Saga als aborted und schreibt Event

Wichtige Verhaltensweisen
------------------------
- Vor Ausführung eines Steps wird ein PENDING-Event persistiert (Write-Ahead).
- Idempotency: wenn `idempotency_key` vorhanden ist, wird eine vorherige
  Ausführung erkannt und Schritt übersprungen.
- Locking: einfache Relational/Advisory-Locks werden für konkurrierende
  Executions genutzt.

Tests
-----
- `tests/test_saga_orchestrator_basic.py` deckt Happy-Path und Failure+Compensation ab
- `tests/test_saga_resume.py` prüft das Resume-Verhalten

Roadmap
-------
- dokumentierte Step-Contract-Definition (Swagger/JSON Schema)
- bessere Lock-Implementierung: Advisory locks für Postgres, row-locks für
  relationale Backends
- Hook mechanism: pre_step/post_step hooks für Observability & metrics

Beispiel
-------
```python
from database.saga_orchestrator import SagaOrchestrator
from database.database_manager import DatabaseManager
mgr = DatabaseManager(config.get_database_backend_dict())
orch = SagaOrchestrator(manager=mgr)
saga_id = orch.create_saga('create_doc', steps)
res = orch.execute_saga(saga_id)
```