## Übersicht
Diese Repository-Sektion stellt eine modulare, mehrschichtige Datenbank-Abstraktion bereit, die mehrere Backend-Typen (Vector, Graph, Relational, Key-Value, File-Storage) über eine gemeinsame API verwaltet. Ziel ist ein flexibles RAG-Backend (Retrieval-Augmented Generation) mit klaren Integrationspunkten für Embedding-/Vector-Datenbanken, Graph-Datenbanken und klassische relationale/Key-Value-Stores.

## Kernelemente (aktuell im Code)
- Abstrakte Basisklassen: `database_api_base.py` definiert die Basis-Interfaces (VectorDatabaseBackend, GraphDatabaseBackend, RelationalDatabaseBackend).
- Backend-Module: Konkrete Implementierungen befinden sich z.B. in `database_api_chromadb.py`, `database_api_neo4j.py`, `database_api_sqlite.py` etc.; diese werden bei Bedarf dynamisch importiert und instanziiert.
- Konfiguration: `database_config.py` enthält die strukturierte `DatabaseConnection`-Klasse und eine globale `database_manager`-Instanz zur Erzeugung legacy-kompatibler Konfig-Dictionaries.
- Database Manager: `database_manager.py` orchestriert Backend-Initialisierung, Health-Checks, dynamisches Laden und zentrale Operationen.

## Wichtige Komponenten und Features

- KGE-Queue (Lightweight SQLite):
	- In `database_api.py` implementiert als lokale SQLite-Instanz zur Persistenz von KGE-Tasks (`kge_tasks`, `kge_results`, `enrichment_logs`).
	- Funktionen: `kge_enqueue_task`, `kge_fetch_next_pending_task`, `kge_set_task_status`, `kge_store_result`, `kge_get_task_result`, `kge_get_queue_size`.

- Persistent Backup Manager:
	- `PersistentBackupManager` (in `database_api.py`) bietet Multi-Storage-Backups (SQLite + JSON + Cache-SQLite) für Wiederherstellung nach Absturz und kurzzeitiges Caching.

- Adaptive Batch Processor:
	- `AdaptiveBatchProcessor` implementiert adaptives Batching mit asynchroner Verarbeitung, Performance-Metriken, Backup-Integration und dynamischer Skalierung der Batch-Größe.

- Module Status Integration:
	- `database_manager.py` versucht, einen externen `module_status_manager` zu importieren und registriert Module (z.B. `db_manager`, `db_vector`, `db_graph`) falls verfügbar. Status-Updates (INITIALIZING, HEALTHY, ERROR, CRITICAL, OFFLINE) werden dort abgelegt.

- Adapter Governance:
	- `AdapterGovernance` wird in `database_manager.py` verwendet, um Richtlinien (policies) zu verwalten und ggf. strict/lenient Verhalten bei Backends zu steuern.

## Betriebs- und Initialisierungsbeispiel
1. Konfiguration laden (Env-Variablen oder `server_config.json`) via `DatabaseConnection`-Objekte in `database_config.py`.
2. Legacy-kompatible Config erhalten: `from database_config import get_database_config`
3. `DatabaseManager` instanziieren (wird häufig automatisch über `database_manager`-Factory im Code gemacht) und Backends prüfen:

```python
from database_config import database_manager
cfg = database_manager.get_legacy_config()
# Übergabe an den zentralen Manager (Beispiel)
from database_manager import DatabaseManager
dm = DatabaseManager(cfg)
dm.verify_backends()
```

## Hinweise für Entwickler
- Viele Backend-Module versuchen optionale Bibliotheken zu importieren (ChromaDB, Neo4j, Pinecone, Redis, etc.). Nicht vorhandene Libraries sind durch Try/Except abgesichert.
- Die `database_api.py` enthält direkten SQLite-Code für interne Persistenz (KGE-Queue); das ist bewusst leichtgewichtig gehalten und unabhängig von externen Backends.
- Die Dokumentation in `docs/` enthält u.a. `database_manager.md` mit detaillierter Architektur, die ebenfalls gepflegt wurde.

## Weiteres
- Für automatisierte Dokumentation wäre ein Sphinx- oder MkDocs-Setup empfehlenswert, um API-Docs aus Docstrings zu generieren.

---
Letzte Aktualisierung: 30.09.2025
