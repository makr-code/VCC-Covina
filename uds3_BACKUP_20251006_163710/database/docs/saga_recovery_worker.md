# `saga_recovery_worker.py`

Kurzbeschreibung
-----------------
Ein Worker, der offene Sagas (in `uds3_sagas`) findet und mittels
`SagaOrchestrator.resume_saga` versucht, diese wiederaufzunehmen. Implementiert
Retry-Policy und Backoff.

Analyse
-------
Der Worker ist dafür gedacht, periodisch ausgeführt zu werden (Cron, Daemon).
Er ist robust gegenüber einzelnen Fehlern und versucht, Sagas mehrfach mit
exponentiellem Backoff zu reaktivieren.

API / Verhalten
----------------
- `run_once(max_retries=3)` — listet offene Sagas und versucht Resume
  (gibt Map `saga_id` -> result zurück)
- `main()` — CLI entry-point für ad-hoc-Ausführungen

Testabdeckung
-------------
- `tests/test_saga_recovery_worker.py` testet `run_once` Verhalten in
  vereinfachten Szenarios (z. B. keine Steps vorhanden).

Roadmap
-------
- Implementiere optionale Concurrency-Limiting (max parallel resumes)
- Metrics: expose counts (resumed, failed, in_progress) für Monitoring
- Add CLI flags (dry-run, max-age, limit)

Beispiel
-------
```python
from database.saga_recovery_worker import SagaRecoveryWorker
w = SagaRecoveryWorker(manager)
results = w.run_once()
```