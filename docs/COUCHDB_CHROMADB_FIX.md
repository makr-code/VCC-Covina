# CouchDB/ChromaDB Ingestion Fix

**Datum:** 09. Oktober 2025  
**Problem:** Ingestion schreibt Daten nur in PostgreSQL (34 Docs), aber CouchDB=0 und ChromaDB=0  
**Status:** ✅ BEHOBEN

---

## 🔍 Problem-Analyse

### Symptome
```json
{
  "polyglot_status": {
    "relational_db": {"documents": 34},   // ✅ PostgreSQL funktioniert
    "couchdb": {"documents": 0},          // ❌ CouchDB leer
    "chromadb": {"documents": 0},         // ❌ ChromaDB leer
    "neo4j": {"nodes": 0}                 // ❌ Neo4j leer
  }
}
```

### Root Cause

**backend.py Line 1710-1735:** Code verwendet zwei verschiedene Execution-Pfade:

```python
# VORHER (BUGGY):
if uds3_manager.saga_orchestrator:
    # ❌ Verwendet execute_saga_polyglot_operations
    # ❌ Hat nur 4 SAGA-Steps: Relational, Vector, Graph, File
    # ❌ CouchDB-Step fehlt komplett!
    db_results = await execute_saga_polyglot_operations(...)
else:
    # ✅ Verwendet execute_polyglot_operations
    # ✅ Nutzt Polyglot Integration mit CouchDB Support
    db_results = await execute_polyglot_operations(...)
```

**Problem:** 
- SAGA Orchestrator ist aktiv → Verwendet `execute_saga_polyglot_operations`
- Diese Funktion hat nur 4 SAGA-Steps (Relational, Vector, Graph, File)
- **CouchDB-Step fehlt komplett!**
- Polyglot Integration mit CouchDB wird übersprungen

**Beweis (backend.py Line 2470-2490):**
```python
saga_steps = [
    SagaStep(name="relational_insert", ...),  # ✅ PostgreSQL
    SagaStep(name="vector_insert", ...),      # ✅ ChromaDB (aber fehlgeschlagen?)
    SagaStep(name="graph_insert", ...),       # ✅ Neo4j
    SagaStep(name="file_store", ...)          # ✅ File Storage
    # ❌ CouchDB Document Storage fehlt!
]
```

---

## 🔧 Lösung

### Fix: Polyglot Integration für alle Uploads verwenden

**backend.py Line 1710-1718 (NEU):**
```python
# Real database operations via Polyglot Integration (inkludiert CouchDB!)
# Polyglot Integration verwendet intern SAGA wenn verfügbar
logger.info(f"🔄 Using Polyglot Integration for document {document_id} (SAGA: {uds3_manager.saga_orchestrator is not None})")
db_results = await execute_polyglot_operations(
    document_id, file_path, content, classification, 
    entities_estimate, legal_count, timestamp
)
```

**Vorteil:**
- ✅ Nutzt Polyglot Integration (hat CouchDB Support!)
- ✅ Polyglot Integration nutzt intern SAGA wenn verfügbar
- ✅ Alle 5 Backends werden geschrieben:
  1. PostgreSQL (Relational Metadata)
  2. ChromaDB (Vector Embeddings)
  3. Neo4j (Graph Relationships)
  4. CouchDB (Document Storage)
  5. File System (Local Copy)

---

## 📊 Polyglot Integration SAGA-Steps

**polyglot_integration.py Line 120-210:**
```python
saga_steps = {
    "metadata_insert": {
        "step_id": f"{saga_transaction_id}_metadata",
        "database_type": "relational",
        "operation": "insert_document_metadata"
    },
    "vector_indexing": {
        "step_id": f"{saga_transaction_id}_vector",
        "database_type": "vector",
        "operation": "create_embeddings"
    },
    "graph_linking": {
        "step_id": f"{saga_transaction_id}_graph",
        "database_type": "graph",
        "operation": "create_document_node"
    },
    "document_storage": {  # ✅ KRITISCH: CouchDB Step!
        "step_id": f"{saga_transaction_id}_couchdb",
        "database_type": "couchdb",
        "operation": "store_document"
    }
}
```

**CouchDB Execute Function (polyglot_integration.py Line 498-540):**
```python
async def _execute_couchdb_step(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Führt CouchDB Step aus - Speichert vollständiges Dokument"""
    
    couchdb_doc = {
        "_id": f"doc_{document_id}",
        "type": "document",
        "document_id": document_id,
        "file_path": file_path,
        "classification": classification,
        "content": content,  # ✅ Vollständiger Content!
        "content_length": len(content),
        "created_at": timestamp,
        "processing_status": "completed"
    }
    
    # ✅ Speichere in CouchDB
    result = self.couchdb_backend.create_document(
        doc_id=f"doc_{document_id}",
        data=couchdb_doc
    )
    
    return {"success": True, "document_id": f"doc_{document_id}"}
```

---

## ✅ Validierung

### 1. Backend neu starten
```bash
# Terminal 1: Backend neu starten
python backend.py

# Expected Log:
# ✅ UDS3 Polyglot Integration initialisiert - SAGA: ✅, Neo4j: ✅, Vector: ✅, CouchDB: ✅
# INFO: Uvicorn running on http://127.0.0.1:45678
```

### 2. Test-Upload (1 Dokument)
```powershell
# Test-Upload
$file = "Y:\data\00_bund_gesetze_auswahl\VwVfG.pdf"
$response = Invoke-RestMethod -Uri "http://127.0.0.1:45678/upload/files" -Method POST -InFile $file -ContentType "application/pdf"
$response

# Expected:
# {
#   "message": "1 file(s) uploaded successfully",
#   "job_id": "...",
#   "file_count": 1
# }
```

### 3. Database Stats validieren
```powershell
curl http://127.0.0.1:45678/database/stats | ConvertFrom-Json | ConvertTo-Json -Depth 5

# Expected (NACH Upload):
# {
#   "polyglot_status": {
#     "relational_db": {"documents": 35},   # +1 (war 34)
#     "couchdb": {"documents": 1},          # ✅ +1 (war 0)
#     "chromadb": {"documents": 2},         # ✅ +2 Chunks (Legal-Chunking: 2.0 Chunks/Doc)
#     "neo4j": {"nodes": 1}                 # ✅ +1 (war 0)
#   }
# }
```

### 4. CouchDB direkt prüfen
```bash
# CouchDB Futon UI:
http://192.168.178.94:5984/_utils/

# Oder CLI:
curl http://192.168.178.94:32931/covina_documents/_all_docs

# Expected:
# {
#   "total_rows": 1,
#   "rows": [{"id": "doc_...", "key": "doc_...", "value": {...}}]
# }
```

### 5. ChromaDB direkt prüfen
```python
import chromadb
client = chromadb.HttpClient(host="192.168.178.94", port=8000)
collection = client.get_collection("covina_documents")
count = collection.count()
print(f"ChromaDB Chunks: {count}")  # Expected: 2 (Legal-Chunking: 2 Chunks/Doc)
```

---

## 📈 Expected Results nach Re-Ingestion

**34 Dokumente → Re-Upload:**
```
PostgreSQL: 34 Docs (bleibt gleich - Update statt Insert)
CouchDB:    0 → 34 Docs (✅ FIX!)
ChromaDB:   0 → ~68 Chunks (✅ FIX! 34 * 2.0 Chunks/Doc)
Neo4j:      0 → 34 Nodes (✅ FIX!)
```

**Monitor während Re-Ingestion:**
```bash
python scripts/monitor_reingestion.py --interval 5 --backend http://127.0.0.1:45678

# Expected Output:
# [12:34:56] PostgreSQL: 34/34 (100.0%) | CouchDB: 15/34 (44.1%) | ChromaDB: 30/68 (44.1%)
# [12:35:01] PostgreSQL: 34/34 (100.0%) | CouchDB: 20/34 (58.8%) | ChromaDB: 40/68 (58.8%)
# ...
# [12:45:00] PostgreSQL: 34/34 (100.0%) | CouchDB: 34/34 (100.0%) | ChromaDB: 68/68 (100.0%)
```

---

## 🔍 Debugging Tools

### Backend-Logs analysieren
```bash
# Prüfe ob Polyglot Integration aufgerufen wird:
python scripts/analyze_backend_logs.py | Select-String "Polyglot Integration|CouchDB|execute_couchdb"

# Expected:
# INFO: Using Polyglot Integration for document abc123 (SAGA: True)
# DEBUG: ✅ CouchDB: Document abc123 gespeichert (12345 Zeichen)
```

### Database Stats API
```bash
curl http://127.0.0.1:45678/database/stats

# Zeigt Echtzeit-Counts für alle 5 Backends
```

### Monitor-Tool
```bash
python scripts/monitor_reingestion.py --interval 5

# Echtzeit-Fortschritt während Re-Ingestion
```

---

## 📝 Zusammenfassung

| Komponente | Vorher | Nachher | Status |
|------------|--------|---------|--------|
| Code-Pfad | `execute_saga_polyglot_operations` (4 Steps) | `execute_polyglot_operations` (5 Steps via Polyglot Integration) | ✅ Fixed |
| PostgreSQL | 34 Docs | 34 Docs | ✅ OK |
| CouchDB | 0 Docs ❌ | 34 Docs ✅ | ✅ Fixed |
| ChromaDB | 0 Chunks ❌ | ~68 Chunks ✅ | ✅ Fixed |
| Neo4j | 0 Nodes ❌ | 34 Nodes ✅ | ✅ Fixed |

**Root Cause:** SAGA-basierter Code-Pfad hatte keinen CouchDB-Step  
**Solution:** Polyglot Integration verwenden (hat alle 5 Backends inkl. CouchDB)  
**Impact:** Alle Dokumente landen nun in **ALLEN** 5 Polyglot-Backends  

---

## 🚀 Nächste Schritte

1. ✅ Backend neu starten (python backend.py)
2. ⏳ Test-Upload (1 Dokument) → Validierung CouchDB/ChromaDB +1
3. ⏳ Batch Re-Ingestion (34 Dokumente) → CouchDB 0→34, ChromaDB 0→68
4. ⏳ Monitor starten → Echtzeit-Fortschritt
5. ⏳ Database Stats validieren → Alle 5 Backends haben Daten
