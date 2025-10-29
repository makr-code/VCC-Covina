# UDS3 Writer Adapter – Architektur & Usage

Letzte Aktualisierung: 29.10.2025

---

## Überblick

Der UDS3 Writer Adapter (`ingestion/writers/uds3_adapter.py`) ist die dünne Integrationsschicht zwischen der modularen Ingestion-Pipeline und dem bestehenden UDS3 Multi-Datenbank-Framework. Statt vier separater Writer (PostgreSQL, ChromaDB, Neo4j, CouchDB) zu implementieren, delegiert der Adapter alle Schreib- und Health-Checks an den zentralen `DatabaseManager` von UDS3.

Vorteile:
- Kein doppelter Code – Wiederverwendung der produktionsreifen UDS3-Backends
- Einheitliche Konfiguration – identisch zu `ingestion.py`
- Einfache Fehlerbehandlung – konsolidierte Logs und Status
- Zukunftssicher – neue Backends werden automatisch über den `DatabaseManager` erreichbar

---

## Architektur

```
Ingestion Pipeline → UDS3Writer (Adapter) → DatabaseManager
                                      ├─ relational_backend  (PostgreSQL)
                                      ├─ vector_backend      (ChromaDB)
                                      ├─ graph_backend       (Neo4j)
                                      └─ file_backend        (CouchDB)
```

- Der Adapter erzeugt bei `initialize()` eine `DatabaseManager`-Instanz und nutzt dessen Backend-Properties.
- Es gibt keinerlei eigene DB-Clients im Adapter – alle Aufrufe sind reine Delegation.

---

## Konfiguration

Der Adapter übernimmt 1:1 dasselbe Konfig-Format wie die produktive Ingestion (`ingestion.py`):

```python
backend_config = {
    "relational": {"enabled": True},   # PostgreSQL
    "vector": {"enabled": True},       # ChromaDB
    "graph": {"enabled": True},        # Neo4j
    "file": {"enabled": True},         # CouchDB
}
```

- Zugangsdaten werden im UDS3-Ökosystem zentral aus `config.py`/ENV bezogen – keine Duplikation im Adapter.
- Optional kann pro Backend `enabled=False` gesetzt werden; der Adapter erkennt die Verfügbarkeit automatisch.

---

## Verwendung

### Initialisierung

```python
from ingestion.writers.uds3_adapter import UDS3Writer

writer = UDS3Writer(config=backend_config)
await writer.initialize()
```

### Einzel-Schreibvorgang

```python
ok = await writer.write(chunk)
# True, wenn mindestens ein Backend erfolgreich geschrieben hat
```

- Der Adapter erzeugt eine `chunk_id` aus `source_file` + `chunk_index`.
- Delegierte Operationen:
  - PostgreSQL: `relational_backend.insert_document(...)`
  - ChromaDB: `vector_backend.add_documents([{id, content, metadata}])`
  - Neo4j: `graph_backend.execute_query(...)` (MERGE/CREATE von Dokument- und Chunk-Knoten)
  - CouchDB: `file_backend.add_documents([{_id, content, metadata}])`

### Batch-Schreibvorgang

```python
result = await writer.write_batch(list_of_chunks)
# {"success": bool, "written": int, "failed": int, "errors": List[str]}
```

- Aktuell werden Chunks nacheinander via `write()` geschrieben (Backends bieten keine gemeinsamen Batch-APIs). 
- Sobald echte Batch-Methoden in UDS3 verfügbar sind, kann diese Stelle zentral umgestellt werden.

### Health-Check

```python
healthy = await writer.health_check()
# True, wenn alle aktivierten Backends gesund sind
```

- PostgreSQL: `get_document_count()`
- ChromaDB/CouchDB: `is_available()`
- Neo4j: `execute_query("RETURN 1", {})`

### Backend-Status

```python
writer.backend_status
# {"postgresql": bool, "chromadb": bool, "neo4j": bool, "couchdb": bool}
```

---

## Fehlerbehandlung & Logging

- Der Adapter loggt pro Backend Erfolg/Fehlschlag mit klaren Emojis (✅/❌) und Kontext (Datei, Index).
- Ein einzelner Backend-Fehler blockiert andere Backends nicht – mindestens ein Erfolg genügt für `True`.
- Bei Batch schreibt der Adapter alle Chunks und sammelt Fehler in `errors`.

---

## Migration (Alt → Neu)

Entfernt (Redundanz):
- `ingestion/writers/postgresql_writer.py`
- `ingestion/writers/chromadb_writer.py`
- `ingestion/writers/neo4j_writer.py`
- `ingestion/writers/couchdb_writer.py`

Neu:
- `ingestion/writers/uds3_adapter.py` – zentrale Delegation an UDS3 `DatabaseManager`.

Tests:
- `tests/writers/test_uds3_writer.py` (9 Tests, 100% grün)

---

## Edge Cases

- Leerer Text wird durch das `Chunk`-Datamodell abgefangen (`__post_init__`).
- Deaktivierte Backends werden automatisch übersprungen; `backend_status` zeigt aktive Backends an.
- Bei Netzwerk-/Backend-Fehlern wird pro Backend sauber geloggt; andere Pfade laufen weiter.

---

## Beispiel-Ende-zu-Ende

```python
writer = UDS3Writer({"relational": {"enabled": True}, "vector": {"enabled": True}})
await writer.initialize()

results = await writer.write_batch(chunks)
if not results["success"]:
    print("Batch hatte Fehler:", results["errors"])

if not await writer.health_check():
    print("Mindestens ein Backend ist ungesund")
```

---

## Hinweise

- Die Implementierung entspricht dem produktiven Nutzungsmuster aus `ingestion.py` (UDS3 Polyglot Manager → DatabaseManager). 
- Aktivierte Backends und Credentials werden zentral in UDS3 konfiguriert – keine Kopie im Adapter.
