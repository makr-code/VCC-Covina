# `database_api_postgresql.py`

Kurzbeschreibung
-----------------
PostgreSQL-Adapter (auch verwendet für JSONB-basierte Key-Value-Backends).
Bietet Verbindung, Schema-Management und JSONB-Operationen für flexible
Speicherung.

Analyse
-------
Postgres ist ein wichtiges relationales Backend im Projekt; Adapter sollte
Transaktionen, Prepared Statements und JSONB-Operationen robust nutzen.

Wichtige API-Methoden
---------------------
- `connect()` / `disconnect()` — baut Verbindung via `psycopg` auf
- `execute_query(sql, params)` — führt Queries aus, gibt Rows zurück
- `insert_record(table, data)` — Insert-Helper; bei JSONB-only-Tabellen
  sollte `insert_record` fallback auf JSON-insert bieten
- JSONB helper methods (serialize/normalize payloads)

Tests
-----
- Unit-tests prüfen das Verhalten der Postgres-Helper (wo möglich mit test-
  doubles). E2E-Tests gegen echten Postgres sind optional; Integration via
  Docker empfohlen.

Roadmap
-------
- Unterstützung für `CREATE INDEX CONCURRENTLY` in Migrations-Scripts (Prod)
- Optional: Connection pooling via `psycopg_pool` oder externe Pooler.
- Exakte Typ-Mapping-Dokumentation (TIMESTAMP, JSONB, UUID, SERIAL etc.).

Beispiel
-------
```python
from database.database_api_postgresql import PostgresRelationalBackend
b = PostgresRelationalBackend({'host':'localhost','port':5432,'database':'covina','username':'covina','password':'covina'})
if b.connect():
    b.execute_query('SELECT now()')
```