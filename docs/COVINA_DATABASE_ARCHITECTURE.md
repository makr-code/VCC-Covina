# Covina Database Architecture
**Letzte Aktualisierung:** 25. Oktober 2025

## Übersicht

Covina nutzt ein **2-Layer Database System**:

1. **UDS3 Core Databases** - Multi-Database Framework (Vector, Graph, Relational, File)
2. **Covina Application Databases** - Specialized databases für Covina-Features

---

## 1. UDS3 Core Databases

**Zweck:** Polyglot Persistence für Dokumenten-Management  
**Konfiguration:** `uds3/config_local.py` → `DATABASES_LEGACY`  
**API:** `uds3/database/database_manager.py` → `DatabaseManager`

### Datenbanken

| Type       | Backend    | Host             | Port  | Database     | Beschreibung                    |
|------------|------------|------------------|-------|--------------|----------------------------------|
| `vector`   | ChromaDB   | 192.168.178.94   | 8000  | -            | Semantic Search (Embeddings)    |
| `graph`    | Neo4j      | 192.168.178.94   | 7687  | neo4j        | Knowledge Graph (Relationships) |
| `relational` | PostgreSQL | 192.168.178.94 | 5432  | veritas_db   | Master Data (Metadata)          |
| `file`     | CouchDB    | 192.168.178.94   | 32770 | -            | Full Document Content           |

**Usage (Backend):**
```python
# Ingestion Backend
backend_config = {
    "vector": {"enabled": True},
    "graph": {"enabled": True},
    "relational": {"enabled": True},
    "file": {"enabled": True}
}
uds3_strategy = UDS3PolyglotManager(backend_config)

# Access backends
db_manager = uds3_strategy.db_manager
postgres = db_manager.get_relational_backend()
chromadb = db_manager.get_vector_backend()
neo4j = db_manager.get_graph_backend()
couchdb = db_manager.get_file_backend()
```

---

## 2. Covina Application Databases

**Zweck:** Specialized features (Compliance, Review Queue, Job Storage, etc.)  
**Konfiguration:** `uds3/config_local.py` → `COVINA_DATABASES`  
**API:** Helper Functions (`get_covina_database()`, `get_postgresql_connection_string()`)

### 2.1 Main Backend Databases

#### **Knowledge Gaps Database**
- **Provider:** PostgreSQL (via UDS3 Relational Backend)
- **Database:** `postgres` (uses UDS3 relational backend)
- **Tables:** `knowledge_gaps`, `gap_relations`, `gap_history`
- **Module:** `gap_detection/gap_database.py`
- **Zweck:** Gap Detection & Management System

**Code:**
```python
from gap_detection.gap_database import KnowledgeGapDB

# CURRENT (uses UDS3 relational backend):
postgres_backend = uds3_strategy.db_manager.get_relational_backend()
gap_db = KnowledgeGapDB(postgres_backend)  # ✅ Already centralized!
```

#### **Review Queue Database**
- **Provider:** PostgreSQL
- **Database:** `postgres`
- **Tables:** `review_tasks`
- **Module:** `management_core/review_queue.py`
- **Zweck:** Data Quality Task Queue

**Code:**
```python
from management_core.review_queue import ReviewQueue

# CURRENT (uses UDS3 relational backend):
postgres_backend = uds3_strategy.db_manager.get_relational_backend()
review_queue = ReviewQueue(postgres_backend)  # ✅ Already centralized!
```

#### **Compliance Database**
- **Provider:** PostgreSQL
- **Database:** `postgres`
- **Tables:** `compliance_logs`, `dsgvo_consents`
- **Module:** `compliance_service.py`
- **Zweck:** DSGVO & Compliance Management

**Code:**
```python
from compliance_service import get_compliance_service

# CURRENT (uses UDS3 relational backend):
postgres_backend = uds3_strategy.db_manager.get_relational_backend()
compliance_service = get_compliance_service(postgres_backend)  # ✅ Already centralized!
```

---

### 2.2 Ingestion Backend Databases

#### **Job Storage Database**
- **Provider:** SQLite (local file)
- **Path:** `data/ingestion_jobs.db`
- **Tables:** `jobs`, `scan_jobs`, `job_files`
- **Module:** `ingestion/job_persistence.py`
- **Zweck:** Persistent Upload Job Tracking (Crash Recovery)

**Code:**
```python
from ingestion.job_persistence import PersistentJobStorage

# BEFORE (hardcoded):
job_storage = PersistentJobStorage(db_path="data/ingestion_jobs.db")

# AFTER (central config):
from config_local import get_sqlite_path
db_path = get_sqlite_path("job_storage")
job_storage = PersistentJobStorage(db_path=db_path)
```

#### **SAGA State Database**
- **Provider:** PostgreSQL
- **Database:** `postgres` (uses UDS3 relational backend)
- **Tables:** `saga_transactions`, `saga_steps`
- **Module:** `saga/saga_orchestrator_production.py`
- **Zweck:** SAGA Transaction State Tracking

**Code:**
```python
from saga.saga_orchestrator_production import SagaOrchestrator

# CURRENT (uses UDS3 relational backend):
postgres_backend = uds3_strategy.db_manager.get_relational_backend()
orchestrator = SagaOrchestrator(
    saga_id=saga_id,
    state_backend=postgres_backend  # ✅ Already centralized!
)
```

---

## 3. Configuration Reference

### UDS3 Core Config (`DATABASES_LEGACY`)
```python
# uds3/config_local.py
DATABASES_LEGACY = {
    "vector": {
        "host": "192.168.178.94",
        "port": 8000,
        ...
    },
    "graph": {
        "host": "192.168.178.94",
        "port": 7687,
        ...
    },
    "relational": {
        "host": "192.168.178.94",
        "port": 5432,
        "database": "veritas_db",
        ...
    },
    "file": {
        "host": "192.168.178.94",
        "port": 32770,
        ...
    }
}
```

### Covina Application Config (`COVINA_DATABASES`)
```python
# uds3/config_local.py
COVINA_DATABASES = {
    "knowledge_gaps": {
        "provider": "postgresql",
        "host": "192.168.178.94",
        "port": 5432,
        "database": "postgres",
        ...
    },
    "job_storage": {
        "provider": "sqlite",
        "path": "data/ingestion_jobs.db",
        ...
    },
    ...
}
```

---

## 4. Migration Guide

### Aktuelle Situation ✅

**Already Centralized:**
- ✅ KnowledgeGapDB (uses UDS3 relational backend) 🆕
- ✅ ReviewQueue (uses UDS3 relational backend)
- ✅ ComplianceService (uses UDS3 relational backend)
- ✅ SAGA Orchestrator (uses UDS3 relational backend)

**Needs Migration:**
- ⚠️  PersistentJobStorage (hardcoded path, aber SQLite ist lokal - Optional)

### Migration Steps

#### ✅ KnowledgeGapDB (Main Backend) - COMPLETE!

**File:** `gap_detection/gap_database.py`

**BEFORE:**
```python
def __init__(self, db_path: str = "./data/knowledge_gaps.db"):
    self.config = {
        'host': '192.168.178.94',  # ← Hardcoded!
        'port': 5432,
        'database': 'postgres',
        'user': 'postgres',
        'password': 'postgres'
    }
    self.connection = psycopg2.connect(**self.config)
```

**AFTER:**
```python
def __init__(self, postgres_backend=None):
    if postgres_backend is None:
        raise RuntimeError("postgres_backend required")
    
    self.postgres_backend = postgres_backend  # ✅ Uses UDS3 Backend!
    self._initialize_tables()
```

**Main Backend Startup:**
```python
# UDS3 initialisieren
uds3_strategy = UDS3PolyglotManager(backend_config)
postgres_backend = uds3_strategy.db_manager.get_relational_backend()

# KnowledgeGapDB mit UDS3 Backend initialisieren
gap_db = KnowledgeGapDB(postgres_backend)  # ✅ Centralized!
```

#### 2. PersistentJobStorage (Ingestion Backend) - OPTIONAL

**File:** `ingestion/job_persistence.py`

**Status:** SQLite ist lokal - Migration OPTIONAL (low priority)

**BEFORE:**
```python
def __init__(self, db_path: str = "data/ingestion_jobs.db"):
    self.db_path = Path(db_path)  # ← Hardcoded default!
```

**AFTER (Optional):**
```python
def __init__(self, db_path: str = None):
    if db_path is None:
        # Load from central config
        from config_local import get_sqlite_path
        db_path = get_sqlite_path("job_storage")
    
    self.db_path = Path(db_path)
```

**Note:** Da SQLite eine lokale Datei ist (kein Remote-Server), ist diese Migration optional. Die aktuelle Implementierung funktioniert bereits gut.

---

## 5. Benefits

### Vorher (Scattered Config)
```
❌ KnowledgeGapDB.__init__() → Hardcoded config
❌ PersistentJobStorage.__init__() → Hardcoded path
❌ Main Backend → ENV variables
❌ Ingestion Backend → ENV variables
```

### Nachher (Central Config)
```
✅ All configs in uds3/config_local.py
✅ Single source of truth
✅ Easy environment switching (dev/staging/prod)
✅ No ENV variables needed
✅ Type-safe config access
```

---

## 6. API Reference

### UDS3 Core API
```python
from uds3.core.polyglot_manager import UDS3PolyglotManager

# Initialize with DB requirements
backend_config = {"vector": {"enabled": True}, "relational": {"enabled": True}}
uds3 = UDS3PolyglotManager(backend_config)

# Access backends
db_manager = uds3.db_manager
postgres = db_manager.get_relational_backend()
chromadb = db_manager.get_vector_backend()
```

### Covina Database API
```python
from config_local import get_covina_database, get_postgresql_connection_string, get_sqlite_path

# Get full config
config = get_covina_database("knowledge_gaps")
# → {"provider": "postgresql", "host": "192.168.178.94", ...}

# Get PostgreSQL connection string
conn_str = get_postgresql_connection_string("knowledge_gaps")
# → "host=192.168.178.94 port=5432 dbname=postgres user=postgres password=postgres"

# Get SQLite path
db_path = get_sqlite_path("job_storage")
# → "data/ingestion_jobs.db"
```

---

## 7. Database Ownership

| Database            | Owner             | Shared? | Purpose                      |
|---------------------|-------------------|---------|------------------------------|
| ChromaDB            | UDS3 Core         | Yes     | Vector search (all backends) |
| Neo4j               | UDS3 Core         | Yes     | Knowledge graph              |
| PostgreSQL:veritas_db | UDS3 Core       | Yes     | Master metadata              |
| CouchDB             | UDS3 Core         | Yes     | Full content storage         |
| PostgreSQL:postgres | Covina Apps       | Yes     | Shared for all Covina features |
| SQLite:job_storage  | Ingestion Backend | No      | Local job tracking           |

**Note:** PostgreSQL `postgres` database is shared by:
- KnowledgeGapDB
- ReviewQueue
- ComplianceService
- SAGA State Storage

Each uses separate tables (no conflicts).

---

## 8. Testing

```python
# Test UDS3 Core Config Loading
from uds3.database.config import DatabaseManager
mgr = DatabaseManager()
print(f"Databases: {len(mgr.databases)}")
for db in mgr.databases:
    print(f"  {db.db_type.value}: {db.host}:{db.port}")

# Expected Output:
# Databases: 4
#   vector: 192.168.178.94:8000
#   graph: 192.168.178.94:7687
#   relational: 192.168.178.94:5432
#   file: 192.168.178.94:32770

# Test Covina Database Config
from config_local import get_covina_database, get_postgresql_connection_string
gap_config = get_covina_database("knowledge_gaps")
print(f"Knowledge Gaps: {gap_config['host']}:{gap_config['port']}/{gap_config['database']}")
conn_str = get_postgresql_connection_string("saga_state")
print(f"SAGA Connection: {conn_str}")
```

---

## 9. Summary

**Architecture:**
- ✅ **1 zentrale Config-Datei** (`uds3/config_local.py`)
- ✅ **2 Config-Sections** (`DATABASES_LEGACY` + `COVINA_DATABASES`)
- ✅ **0 ENV Variables** (alle Credentials in config_local.py)
- ✅ **Type-Safe Access** (Helper functions mit Validation)

**Next Steps:**
1. ✅ UDS3 Core Config - COMPLETE
2. ✅ Covina Database Config - COMPLETE
3. ⏸️  Migrate KnowledgeGapDB
4. ⏸️  Migrate PersistentJobStorage
5. ⏸️  Test Integration
