# `database_api_sqlite.py`

Kurzbeschreibung
-----------------
SQLite-basierter Relational-Adapter. Bietet lokale relationale Persistenz für
Tests, Entwicklung und leichte Produktions-Workloads. Unterstützt schema-
inspektion via `PRAGMA`, convenience methods (`insert_record`, `get_table_schema`).

Analyse
-------
Der Adapter ist bewusst einfach gehalten und eignet sich als Default-Backend
für Unit-Tests (keine externen Abhängigkeiten). In der aktuellen Implementierung
wurde ergänzt:
- `insert` convenience wrapper
- `execute_query` behandelt `PRAGMA` als select-ähnliche Abfrage, um
  Schema-Introspektion zu ermöglichen

Hauptmethoden / API
-------------------
- `connect()` / `_backend_connect()` — Öffnet (lokale) SQLite-Verbindung
- `execute_query(query, params=None)` — Führt SQL aus und gibt Dict-Rows
  zurück; non-select liefert affected_rows
- `insert_record(table, data)` — Insert mit Rückgabe der erzeugten id
- `insert(table, data)` — Convenience-Methode (delegiert an `insert_record`)
- `get_table_schema(table_name)` — Liefert Spalteninformation
- `create_table(table_name, schema)` — Erstellt Tabelle

Tests
-----
- Viele Saga- und Manager-Tests verwenden SQLite als leichtgewichtigen
  relationalen Store und decken die meisten Pfade ab.

Roadmap
-------
- Transactional helpers (context manager für `begin`/`commit`/`rollback`).
- Better type mapping (z. B. JSON/JSONB fallback für Textfelder).
- Optional: Better concurrency support (WAL/timeout tuning) für Parallel-Tests.

Beispiel
-------
```python
from database.database_api_sqlite import SQLiteRelationalBackend
b = SQLiteRelationalBackend({'database_path': './data/test.db'})
b._backend_connect()
b.create_table('mytable', {'id': 'TEXT PRIMARY KEY', 'data': 'TEXT'})
b.insert('mytable', {'id': '1', 'data': 'hello'})
rows = b.execute_query('SELECT * FROM mytable')
```