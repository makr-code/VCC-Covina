# SAGA Orchestrator Design

Ziel: Definiere einen schlanken, robusten Orchestrator für SAGA-Workflows
(Polyglot-Persistence). Fokus: einfache API, write-ahead event logging, kompensierende
Handler, idempotency und Recovery.

## API (Schnittstelle)

1. create_saga(saga_name: str, steps: List[StepSpec], trace_id: Optional[str] = None) -> saga_id
   - Legt einen Eintrag in `uds3_sagas` an (status = "created") und schreibt initiale PENDING-Events für alle Steps.

2. execute_saga(saga_id: str) -> { success: bool, events: List }
   - Führt Steps in definierter Reihenfolge aus.
   - Vor jedem Step: schreibe `uds3_saga_events` mit status=PENDING (write-ahead).
   - Führe Operation via `SagaDatabaseCRUD` / `DatabaseManager` aus.
   - Nach erfolgreichem Step: update event -> status=SUCCESS.
   - Bei Exception: update event -> status=FAIL, schreibe Fehler, setze saga status=failed und starte Compensation.

3. compensate_saga(saga_id: str) -> { compensated: bool }
   - Führt Kompensations-Handler in umgekehrter Reihenfolge der erfolgreichen Steps aus.
   - Handler werden aus einer Registry geholt und dürfen idempotent sein.

4. abort_saga(saga_id: str, reason: str) -> None
   - Markiert Saga als aborted, schreibt Audit und optional triggert Compensation.

5. resume_saga(saga_id: str) -> { resumed: bool }
   - Rekonstruiert State aus `uds3_saga_events` und fährt fort (oder kompensiert) je nach Event-Status.

## StepSpec (Contract)

- step_id: str
- backend: one of (vector|graph|relational|file|key_value)
- operation: str (z. B. 'create', 'update', 'delete', 'add_documents', 'create_node')
- payload: dict (operation-spezifisch)
- compensation: Optional[str] (Name eines registrierten Kompensationshandlers)
- idempotency_key: Optional[str] (zur Duplikat-/Replay-Abwehr)
- retry_policy: Optional[dict] (max_retries, backoff_ms)

Beispiel in YAML/JSON siehe `examples/`.

## Event Modell (uds3_saga_events)

- event_id, saga_id, trace_id, step_name, event_type, status (PENDING|SUCCESS|FAIL|COMPENSATED), duration_ms, payload, created_at

Regeln:
- WRITE-AHEAD: PENDING Event muss vor Ausführung persistiert werden.
- Event Update muss atomar sein (UPDATE row + commit) bevor nächste Operation beginnt.

## Compensation Registry

- Zentrale Registry (`saga_compensations.py`) mit API:
  - register(name: str, handler: Callable[[payload, ctx], bool])
  - get(name) -> handler

- Handler-Contract: handler(payload: dict, ctx: dict) -> bool (True=ok)
- Default-Handler: relational_delete, graph_delete_node, vector_delete_chunks

## Idempotency & Locking

- Jeder Step kann `idempotency_key` setzen. Orchestrator prüft ob ein erfolgreiches Event mit diesem Key bereits existiert.
- Locking: einfache DB-basierte advisory-lock (z. B. relational `SELECT ... FOR UPDATE`) oder per `uds3_sagas` row flag.

## Recovery

- `resume_saga` liest alle events:
  - Falls last event PENDING: retry step
  - Falls last event FAIL: trigger compensation
  - Falls incomplete: continue

## Metrics & Observability

- Jeder Step erzeugt metric-Events in `uds3_saga_metrics` (attempt, success, duration_ms, error)
- Audit-Einträge in `uds3_audit_log` bei Abbruch/Kompensation

## Sicherheit

- Secrets via ENV
- Governance: `_enforce_governance` wird vor Operationen aufgerufen; Orchestrator muss Governance-Blockierungen als FAIL behandeln und Audit schreiben.

## Examples
- Siehe `examples/saga_example_create_document.yaml`
- Siehe `examples/saga_example_compensate.yaml`


---
Design-Author: automated assistant
Date: 2025-09-30
