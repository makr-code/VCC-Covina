# `saga_crud.py`

Kurzbeschreibung
-----------------
Bietet Saga-orientierte CRUD-Helfer und Observability-Mechanismen. Diese
Komponente ist verantwortlich für:
- standardisierte `CrudResult` Rückgaben für Saga-Schritte
- Schreib-/Insert-Logik für `uds3_saga_events` und Audit-/Observability-Tabellen
- Idempotency- und Schema-sensitives `_safe_insert`, kompatibel mit unterschiedlichen relationalen Backends

Analyse
-------
`saga_crud.py` ist in der Saga-Architektur zentral, weil es die Persistenz der
Sage-Events gewährleistet. Das Modul ist robust gegen Abweichungen in
relationalen Backends (z. B. Tabellen mit nur einem `data` JSON-Feld). Es
integriert außerdem Observability (Traces, Metrics) in das relational Backend.

Wichtige Bestandteile
---------------------
- `CrudResult` (dataclass)
  - Standardisiertes Result-Objekt, `to_payload()` für Serialisierung
- `SagaDatabaseCRUD` Klasse
  - `_enforce_governance()` - ruft `DatabaseManager`-Governance Hooks auf
  - `_safe_insert()` - schema-aware Insert, nutzt `insert_record`/`insert` oder generisches `execute_query`
  - `_record_identity_observability()` - schreibt Traces und Metriken
  - `write_saga_event(saga_id, step_name, status, payload, error=None)` - zentrale Methode

Testabdeckung
-------------
- `tests/test_saga_events.py` testet `write_saga_event` Flow (PENDING -> SUCCESS)
- Saga-Tests nutzen `_safe_insert` in verschiedenen Pfaden

Roadmap / Verbesserungen
------------------------
- Exponiere `_safe_insert` als Utility/Helper für Migrationen oder externe Werkzeuge
- Zusätzliche Validierungen (payload-schema) und Size-Limits, alternativ Payload-Compression
- Unterstütze native JSONB-Felder für Backends wie Postgres ohne String-Serialisierung

Beispiel
-------
```python
from database.saga_crud import SagaDatabaseCRUD
crud = SagaDatabaseCRUD(manager=manager)
crud.write_saga_event('sid', 'step1', 'PENDING', {'document_id':'d1'})
```