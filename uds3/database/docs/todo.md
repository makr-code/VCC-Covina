# TODO: SAGA-Orchestrator Implementierung (Polyglot Persistence)

Ziel: Vollständige Implementierung eines robusten Saga-Orchestrators, der
Polyglot-Persistence (Vector, Graph, Relational, File, Key-Value) und die
Adapter-Governance integriert. Die Aufgaben sind priorisiert; das erste Item
ist in-progress und dient als Design-Phase.

1) Design: Saga Orchestrator & Contract (in-progress)
   - Entwurf einer stabilen API / Datenstruktur für Sagas:
     - create_saga(saga_name, steps, trace_id=None) -> saga_id
     - execute_saga(saga_id)
     - abort_saga(saga_id)
     - compensate_saga(saga_id)
   - Step-Contract:
     - { step_id, backend, operation, payload, compensation, idempotency_key }
   - Acceptance: Schnittstellendefinition (Markdown/Swagger-like) + 2 Beispiel-Sagas

2) Implement: Event Write Helper (completed)
    - Datei: `saga_crud.py`
    - API: `write_saga_event(saga_id, step_id, status, payload, error=None)`
    - Implementierung: atomare Insert-Logik mit Schema-sensitivem `_safe_insert`, tolerant
       gegenüber abweichenden relationalen Backends (z. B. Tabellen mit alternativem
       PK-Namen oder nur einem JSON-`data`-Feld). Schreibt bei Abschluss auch Audit-Einträge.
    - Weitere Änderungen: Vereinheitlichung von Imports (package-style `database.*`) und
       defensive Test-Wrapper um Tracebacks anzuzeigen.
    - Acceptance: `tests/test_saga_events.py::test_write_saga_event_creates_rows` vorhanden und lokal ausgeführt (grün).

    - Quick run (workspace root):
       ```
       pytest -q tests/test_saga_events.py::test_write_saga_event_creates_rows
       pytest -q tests/test_saga_compensations.py::test_relational_delete_handler
       ```

3) Implement: Compensation Registry & Default Handlers (completed)
   - Datei: `saga_compensations.py`
   - Registry API: `register(name, handler_callable)`, `get(name)`.
   - Default Handlers implemented:
     - `relational_delete` (idempotent-aware),
     - `graph_delete_node` (best-effort multi-backend),
     - `vector_delete_chunks` (best-effort multi-backend).
   - Acceptance: `tests/test_saga_compensations.py` enthält tests für relational + graph/vector stubs and passed locally.

4) Implement: SagaOrchestrator Core (completed)
   - Datei: `saga_orchestrator.py`
   - Funktionen: create_saga, execute_saga, abort_saga, compensate_saga
   - Ablauf: vor jedem Step -> write event PENDING; ausführen; update event SUCCESS/FAIL
   - Bei Fehler: stoppe, schreibe error, rufe Kompensationen in reverse order auf
   - Acceptance: Integrationstest mit Mock-Backends (happy + failure + compensate)

5) Implement: Write-Ahead & Recovery Hooks (completed)
   - Sicherstellen: PENDING-Event wird persistiert bevor Remote-Operation ausgeführt
   - Recovery API: resume_saga(saga_id) zur Wiederaufnahme nach Crash
   - Acceptance: Provenance via uds3_saga_events ermöglicht Restart/Replay

6) Implement: Recovery Worker (Retry/Backoff) (completed)
   - Datei: `saga_recovery_worker.py` (CLI + optional daemon)
   - Configurable: max_retries (default 3), backoff strategy (exponential)
   - Acceptance: Worker kann eine gescheiterte Saga kompensieren oder neu anstoßen

7) Implement: Idempotency & Locking (completed)
   - Idempotency: idempotency_key pro Step, geprüft vor Ausführung
   - Locking: relational row-lock or advisory lock für identity_key
   - Acceptance: Simulierter Parallel-Run zeigt deterministisches Verhalten

8) Tests: Unit & Integration (partially completed)
   - Framework: pytest
   - Minimalsuite: orchestrator_happy.py, orchestrator_failure_compensate.py, event_write_test.py
   - Acceptance: Tests laufen lokal (SQLite) ohne externe Dienste

9) Docs & Usage Examples (not-started)
   - Ergänze diese Datei und `docs/` mit Beispielen, ENV-Variablen und Anleitungen
   - Acceptance: README Abschnitt mit End-to-End Beispiel

---

Konfiguration & Hinweise
- ENV: PROJECT_PREFIX (z.B. `vcc`), ENV (z.B. `dev`/`prod`)
- Retry-Policy: konfigurierbar via ENV oder `config.py` settings
- Sicherheit: Secrets (DB-PW, S3 keys) werden via Umgebungsvariablen gesetzt; keine Hardcoding.

Nächste Schritte
- Ich setze jetzt die Design-Phase um (Task 1): erstelle Schnittstellendefinitionen und 2 Beispiel-Sagas.
- Bestätige kurz, ob Default-Policy max_retries=3 und ENV default `prod` so bleiben sollen.

Migrations-CLI
----------------
Ein idempotentes Migrations-Skript liegt unter `scripts/run_saga_migrations.py`.
Das Skript ruft die Funktionen `ensure_saga_schema` und `ensure_idempotency_column`
auf dem konfigurierten relationalen Backend auf. Es liest `server_config.json` im
Projektroot und akzeptiert einfache Overrides über die Umgebungsvariable
`SAGA_REL_HOST`.

PowerShell-Beispiele

- Lokale Ausführung (nutzt `server_config.json`):

```powershell
# aus dem Projekt-Root
python .\database\scripts\run_saga_migrations.py
```

- Remote-Host mit env-override (schnell testen):

```powershell
# Setze die DB-Host-Override (z.B. Postgres auf 192.168.178.94)
$env:SAGA_REL_HOST = '192.168.178.94'
python .\database\scripts\run_saga_migrations.py
```

- Empfehlung für Produktion (via SSH / Remote-Host):

```powershell
# Auf dem Deployment-/Ops-Host ausführen (erst Staging testen!)
ssh ops@192.168.178.94 "cd /path/to/repo && SAGA_REL_HOST=192.168.178.94 python3 ./database/scripts/run_saga_migrations.py"
```

Hinweise & Sicherheit
- Das Skript ist idempotent und loggt Fehler statt sie ohne Kontrolle zu werfen.
- Backup vor Änderungen in Produktionsdatenbanken wird dringend empfohlen.
- Für Postgres in Produktion empfehlen wir manuelle Nutzung von
   `CREATE INDEX CONCURRENTLY` für grosse Tabellen; das Skript vermeidet
   `CONCURRENTLY` für Kompatibilität mit SQLite.

Fehlerbehandlung
- Falls kein relationales Backend gefunden wird, bricht das Skript ab und
   gibt Hinweise im Log aus. Stelle sicher, dass `server_config.json` oder
   die Umgebungsvariablen korrekt gesetzt sind.

Optional
- Soll ich eine Postgres-only Variante mit `CONCURRENTLY` ergänzen, die
   nur läuft, wenn das Backend als Postgres erkannt wird? Ich kann das
   ergänzen wenn gewünscht.
