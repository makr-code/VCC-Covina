# `database_api_base.py`

Kurzbeschreibung
-----------------
Definiert die abstrakten Basisklassen und Contracts für alle Backends. Enthält
auch Hilfsmechanik für Adaptive Batch Processing und (optionale) UDS3-
Integrationspunkte.

Analyse
-------
Dieses Modul ist das Herz der Adapter-Architektur: es definiert die Methoden,
die alle konkreten Adapter implementieren müssen (`connect`, `disconnect`,
`is_available`, `get_backend_type`) und bietet Komfortfunktionen (UDS3,
adaptive batching). Änderungen hier haben projektweite Auswirkungen.

Kernklassen
-----------
- `DatabaseBackend` (ABC)
  - Basis für alle Adapter. Bietet adaptive batch processor scaffolding,
    UDS3-Integration und generische Helper (is_duplicate, get_uds3_metadata).
- `VectorDatabaseBackend`, `GraphDatabaseBackend`, `RelationalDatabaseBackend`
  - Spezialisierte Basisklassen mit zusätzlichen abstract methods.

Wichtige Hinweise
-----------------
- Wenn du neue Adapter schreibst, implementiere das minimale Contract-Set und
  nutze `get_table_schema`, `execute_query` etc. für maximale Interoperabilität.
- Adaptive Batch Processor ist pluggable — backends können eigene batch-
  executors anbieten.

Tests
-----
- Basistests prüfen, dass concrete subclasses discovery funktioniert und
  Abstraktions-Verträge nicht verletzt werden.

Roadmap
-------
- Detaillierte Dokumentation der Methodensignaturen + Beispiel-Adapter.
- Einheitliche Exception-Typen/Fehlercodes across adapters.
- Optional: typing.Protocol-Interfaces für bessere Statische Analyse.
