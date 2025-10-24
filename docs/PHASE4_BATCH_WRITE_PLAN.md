# Phase 4: Batch WRITE Operations - Complete Implementation Plan

**Date:** 21. Oktober 2025  
**Version:** 1.0.0  
**Status:** 🎯 Planning Phase  
**Author:** Covina System

---

## 📋 Executive Summary

### Objective

Implement **Batch WRITE Operations** (UPDATE, DELETE, UPSERT) as API endpoints in Covina Main Backend to enable efficient bulk document management operations.

### Scope Clarification

**✅ Already Implemented (Ingestion Backend):**
- `ChromaBatchInserter` - Batch vector INSERT (100 vectors/call, -93% API calls)
- `Neo4jBatchCreator` - Batch relationship CREATE (1000 rels/query, ~100x speedup)
- **Location:** `database/batch_operations.py` (469 lines)
- **Usage:** Ingestion pipeline (Upload → Processing → Database Write)
- **Status:** Code complete, ENV-activated (`ENABLE_CHROMA_BATCH_INSERT`, `ENABLE_NEO4J_BATCHING`)

**❌ Missing (Main Backend API - This Phase):**
- Batch UPDATE API endpoint
- Batch DELETE API endpoint
- Batch UPSERT API endpoint
- **Location:** `main_backend.py` (new endpoints)
- **Usage:** API-based document management (Frontend → Backend → Database)
- **Status:** Not implemented

### Key Performance Targets

| Operation | Sequential | Batch Target | Expected Speedup |
|-----------|-----------|--------------|------------------|
| UPDATE (50 docs) | ~1000ms | ~15ms | **67x faster** |
| UPDATE (200 docs) | ~4000ms | ~50ms | **80x faster** |
| DELETE (100 docs) | ~2000ms | ~20ms | **100x faster** |
| UPSERT (100 docs) | ~2500ms | ~30ms | **83x faster** |

**Rationale:** Similar to Phase 3 Batch READ performance (8-97x speedup validated in production)

---

## 🏗️ Architecture Overview

### Current System State (After Phase 3)

```
Covina Main Backend (Port 45678)
├─ Phase 3: Batch READ Operations ✅ COMPLETE
│  ├─ POST /api/v1/batch/get (8-97x speedup)
│  ├─ POST /api/v1/batch/exists (20x speedup)
│  ├─ POST /api/v1/batch/search (3-4x speedup)
│  └─ GET /api/v1/batch/status
│
├─ Phase 4: Batch WRITE Operations ⏸️ PENDING
│  ├─ POST /api/v1/batch/update (Target: 67-80x speedup)
│  ├─ POST /api/v1/batch/delete (Target: 100x speedup)
│  └─ POST /api/v1/batch/upsert (Target: 83x speedup)
│
└─ Existing Endpoints (34 routes)
   ├─ DSGVO Compliance
   ├─ Review Queue
   ├─ Golden Datasets
   └─ Governance Policies
```

### Database Layer Architecture

```
Phase 4 Batch WRITE Operations
├─ PostgreSQL (Relational Master Data)
│  ├─ UPDATE: SET ... WHERE document_id IN (...)
│  ├─ DELETE: DELETE FROM documents WHERE document_id IN (...)
│  └─ UPSERT: INSERT ... ON CONFLICT DO UPDATE
│
├─ ChromaDB (Vector Embeddings)
│  ├─ UPDATE: Delete + Re-insert (no native update)
│  ├─ DELETE: collection.delete(ids=[...])
│  └─ UPSERT: Add with upsert=True parameter
│
├─ Neo4j (Knowledge Graph)
│  ├─ UPDATE: SET node.property = value WHERE id IN [...]
│  ├─ DELETE: DETACH DELETE node WHERE id IN [...]
│  └─ UPSERT: MERGE (n {id: ...}) ON CREATE/MATCH SET
│
└─ CouchDB (Full Content Storage)
   ├─ UPDATE: _bulk_docs with _rev
   ├─ DELETE: _bulk_docs with _deleted: true
   └─ UPSERT: _bulk_docs (auto-creates if missing)
```

---

## 🎯 Phase 4 Endpoints Specification

### Endpoint 1: Batch UPDATE

**Purpose:** Update metadata/properties for multiple documents simultaneously

**Endpoint:** `POST /api/v1/batch/update`

**Request Model:**
```python
class BatchUpdateRequest(BaseModel):
    updates: List[DocumentUpdate] = Field(
        ...,
        description="List of document updates to apply"
    )
    update_mode: str = Field(
        default="partial",
        description="Update mode: 'partial' (merge) or 'full' (replace)"
    )
    databases: Optional[List[str]] = Field(
        default=None,
        description="Target databases (default: all)"
    )

class DocumentUpdate(BaseModel):
    document_id: str = Field(..., description="Document ID to update")
    fields: Dict[str, Any] = Field(..., description="Fields to update")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata updates"
    )
```

**Request Example:**
```json
{
  "updates": [
    {
      "document_id": "doc_0001",
      "fields": {
        "classification": "VERTRAG_IMPORTANT",
        "quality_score": 0.95,
        "processing_status": "reviewed"
      },
      "metadata": {
        "reviewed_by": "admin",
        "review_date": "2025-10-21"
      }
    },
    {
      "document_id": "doc_0002",
      "fields": {
        "classification": "RECHNUNG",
        "quality_score": 0.88
      }
    }
  ],
  "update_mode": "partial",
  "databases": ["postgresql", "neo4j"]
}
```

**Response Model:**
```python
class BatchUpdateResponse(BaseModel):
    success: bool
    updated: int
    failed: int
    errors: List[UpdateError]
    execution_time_ms: float
    performance_note: str
    results: List[UpdateResult]

class UpdateResult(BaseModel):
    document_id: str
    status: str  # "success" or "failed"
    databases_updated: List[str]
    error: Optional[str] = None

class UpdateError(BaseModel):
    document_id: str
    database: str
    error_message: str
```

**Response Example:**
```json
{
  "success": true,
  "updated": 2,
  "failed": 0,
  "errors": [],
  "execution_time_ms": 15.23,
  "performance_note": "67x faster than sequential updates",
  "results": [
    {
      "document_id": "doc_0001",
      "status": "success",
      "databases_updated": ["postgresql", "neo4j"],
      "error": null
    },
    {
      "document_id": "doc_0002",
      "status": "success",
      "databases_updated": ["postgresql", "neo4j"],
      "error": null
    }
  ]
}
```

**Performance Targets:**
- 50 updates: Sequential ~1000ms → Batch ~15ms (**67x speedup**)
- 200 updates: Sequential ~4000ms → Batch ~50ms (**80x speedup**)

**Implementation Strategy:**
1. **PostgreSQL:** Single UPDATE query with CASE/WHEN for different values
   ```sql
   UPDATE documents 
   SET 
     classification = CASE 
       WHEN document_id = 'doc_0001' THEN 'VERTRAG_IMPORTANT'
       WHEN document_id = 'doc_0002' THEN 'RECHNUNG'
       ELSE classification
     END,
     quality_score = CASE 
       WHEN document_id = 'doc_0001' THEN 0.95
       WHEN document_id = 'doc_0002' THEN 0.88
       ELSE quality_score
     END
   WHERE document_id IN ('doc_0001', 'doc_0002')
   ```

2. **Neo4j:** UNWIND-based batch update
   ```cypher
   UNWIND $updates AS update
   MATCH (n {id: update.document_id})
   SET n += update.fields
   RETURN n.id as updated_id
   ```

3. **ChromaDB:** Batch delete + re-insert (no native update)
   ```python
   # Delete old vectors
   collection.delete(ids=document_ids)
   # Re-insert with updated metadata
   collection.add(ids=document_ids, embeddings=vectors, metadatas=updated_metadata)
   ```

4. **CouchDB:** _bulk_docs API
   ```python
   bulk_docs = [
       {"_id": doc_id, "_rev": rev, "fields": updated_fields}
       for doc_id, rev, updated_fields in updates
   ]
   db.update(bulk_docs)
   ```

**Batch Size Limits:**
- Recommended: 50-200 updates per request
- Maximum: 1000 updates (to prevent timeout)

---

### Endpoint 2: Batch DELETE

**Purpose:** Delete multiple documents simultaneously (soft or hard delete)

**Endpoint:** `POST /api/v1/batch/delete`

**Request Model:**
```python
class BatchDeleteRequest(BaseModel):
    document_ids: List[str] = Field(
        ...,
        description="List of document IDs to delete",
        min_items=1,
        max_items=1000
    )
    delete_mode: str = Field(
        default="soft",
        description="Delete mode: 'soft' (mark as deleted) or 'hard' (permanent)"
    )
    databases: Optional[List[str]] = Field(
        default=None,
        description="Target databases (default: all)"
    )
    cascade: bool = Field(
        default=True,
        description="Delete related data (chunks, relationships, etc.)"
    )
```

**Request Example:**
```json
{
  "document_ids": [
    "doc_0001",
    "doc_0002",
    "doc_0003"
  ],
  "delete_mode": "soft",
  "databases": ["postgresql", "chromadb", "neo4j"],
  "cascade": true
}
```

**Response Model:**
```python
class BatchDeleteResponse(BaseModel):
    success: bool
    deleted: int
    failed: int
    errors: List[DeleteError]
    execution_time_ms: float
    performance_note: str
    results: List[DeleteResult]

class DeleteResult(BaseModel):
    document_id: str
    status: str  # "success" or "failed"
    databases_deleted: List[str]
    cascade_deleted: Optional[Dict[str, int]] = None  # {"chunks": 5, "relationships": 3}
    error: Optional[str] = None

class DeleteError(BaseModel):
    document_id: str
    database: str
    error_message: str
```

**Response Example:**
```json
{
  "success": true,
  "deleted": 3,
  "failed": 0,
  "errors": [],
  "execution_time_ms": 20.45,
  "performance_note": "100x faster than sequential deletes",
  "results": [
    {
      "document_id": "doc_0001",
      "status": "success",
      "databases_deleted": ["postgresql", "chromadb", "neo4j"],
      "cascade_deleted": {
        "chunks": 5,
        "relationships": 3
      },
      "error": null
    },
    {
      "document_id": "doc_0002",
      "status": "success",
      "databases_deleted": ["postgresql", "chromadb", "neo4j"],
      "cascade_deleted": {
        "chunks": 8,
        "relationships": 5
      },
      "error": null
    }
  ]
}
```

**Performance Targets:**
- 100 deletes: Sequential ~2000ms → Batch ~20ms (**100x speedup**)
- 500 deletes: Sequential ~10s → Batch ~80ms (**125x speedup**)

**Implementation Strategy:**

1. **Soft Delete (Recommended for Production):**
   - PostgreSQL: `UPDATE documents SET deleted = true, deleted_at = NOW() WHERE document_id IN (...)`
   - Neo4j: `MATCH (n {id: id}) SET n.deleted = true, n.deleted_at = timestamp()`
   - ChromaDB: Update metadata `{"deleted": true, "deleted_at": "2025-10-21"}`
   - CouchDB: Update document `{"_deleted": false, "deleted": true}` (keep for audit)

2. **Hard Delete (Permanent):**
   - PostgreSQL: `DELETE FROM documents WHERE document_id IN (...)`
   - Neo4j: `MATCH (n {id: id}) DETACH DELETE n` (cascade deletes relationships)
   - ChromaDB: `collection.delete(ids=[...])`
   - CouchDB: `_bulk_docs` with `{"_deleted": true}`

3. **Cascade Delete:**
   - Delete all related chunks (ChromaDB)
   - Delete all relationships (Neo4j)
   - Delete job records (PostgreSQL)

**Batch Size Limits:**
- Recommended: 100-500 deletes per request
- Maximum: 1000 deletes

**Safety Features:**
- Transaction support (rollback on partial failure)
- Dry-run mode (preview what would be deleted)
- Audit logging (who deleted what, when)
- Recovery mechanism (restore soft-deleted documents)

---

### Endpoint 3: Batch UPSERT

**Purpose:** Insert or update documents (conditional operation)

**Endpoint:** `POST /api/v1/batch/upsert`

**Request Model:**
```python
class BatchUpsertRequest(BaseModel):
    documents: List[DocumentUpsert] = Field(
        ...,
        description="List of documents to insert or update"
    )
    conflict_resolution: str = Field(
        default="update",
        description="Conflict resolution: 'update', 'skip', or 'error'"
    )
    databases: Optional[List[str]] = Field(
        default=None,
        description="Target databases (default: all)"
    )

class DocumentUpsert(BaseModel):
    document_id: str = Field(..., description="Document ID")
    fields: Dict[str, Any] = Field(..., description="Document fields")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Document metadata"
    )
    vector: Optional[List[float]] = Field(
        default=None,
        description="Embedding vector (for ChromaDB)"
    )
```

**Request Example:**
```json
{
  "documents": [
    {
      "document_id": "doc_0001",
      "fields": {
        "file_path": "/path/to/doc1.pdf",
        "classification": "VERTRAG",
        "content_length": 1024,
        "quality_score": 0.92
      },
      "metadata": {
        "created_at": "2025-10-21",
        "source": "import"
      },
      "vector": [0.1, 0.2, ..., 0.384]
    },
    {
      "document_id": "doc_0002",
      "fields": {
        "file_path": "/path/to/doc2.pdf",
        "classification": "RECHNUNG",
        "content_length": 2048,
        "quality_score": 0.88
      }
    }
  ],
  "conflict_resolution": "update",
  "databases": ["postgresql", "chromadb"]
}
```

**Response Model:**
```python
class BatchUpsertResponse(BaseModel):
    success: bool
    inserted: int
    updated: int
    skipped: int
    failed: int
    errors: List[UpsertError]
    execution_time_ms: float
    performance_note: str
    results: List[UpsertResult]

class UpsertResult(BaseModel):
    document_id: str
    operation: str  # "inserted", "updated", "skipped", or "failed"
    status: str
    databases_affected: List[str]
    error: Optional[str] = None

class UpsertError(BaseModel):
    document_id: str
    database: str
    error_message: str
```

**Response Example:**
```json
{
  "success": true,
  "inserted": 1,
  "updated": 1,
  "skipped": 0,
  "failed": 0,
  "errors": [],
  "execution_time_ms": 30.12,
  "performance_note": "83x faster than sequential upserts",
  "results": [
    {
      "document_id": "doc_0001",
      "operation": "updated",
      "status": "success",
      "databases_affected": ["postgresql", "chromadb"],
      "error": null
    },
    {
      "document_id": "doc_0002",
      "operation": "inserted",
      "status": "success",
      "databases_affected": ["postgresql", "chromadb"],
      "error": null
    }
  ]
}
```

**Performance Targets:**
- 100 upserts: Sequential ~2500ms → Batch ~30ms (**83x speedup**)
- 500 upserts: Sequential ~12.5s → Batch ~120ms (**104x speedup**)

**Implementation Strategy:**

1. **PostgreSQL: INSERT ... ON CONFLICT DO UPDATE**
   ```sql
   INSERT INTO documents (document_id, file_path, classification, ...)
   VALUES 
     ('doc_0001', '/path/to/doc1.pdf', 'VERTRAG', ...),
     ('doc_0002', '/path/to/doc2.pdf', 'RECHNUNG', ...)
   ON CONFLICT (document_id) 
   DO UPDATE SET 
     file_path = EXCLUDED.file_path,
     classification = EXCLUDED.classification,
     updated_at = NOW()
   RETURNING document_id, xmax = 0 AS inserted
   ```
   - `xmax = 0`: true if inserted (new row), false if updated (existing row)

2. **Neo4j: MERGE with ON CREATE/ON MATCH**
   ```cypher
   UNWIND $documents AS doc
   MERGE (n:Document {id: doc.document_id})
   ON CREATE SET n += doc.fields, n.created_at = timestamp()
   ON MATCH SET n += doc.fields, n.updated_at = timestamp()
   RETURN n.id as document_id, n.created_at = n.updated_at as inserted
   ```

3. **ChromaDB: Add with upsert=True**
   ```python
   collection.add(
       ids=document_ids,
       embeddings=vectors,
       metadatas=metadata_list,
       upsert=True  # Update if exists, insert if not
   )
   ```

4. **CouchDB: _bulk_docs (auto-upserts)**
   ```python
   bulk_docs = [
       {"_id": doc_id, "fields": fields, "metadata": metadata}
       for doc_id, fields, metadata in documents
   ]
   # CouchDB auto-creates if missing, updates if _rev provided
   db.update(bulk_docs)
   ```

**Batch Size Limits:**
- Recommended: 50-200 upserts per request
- Maximum: 1000 upserts

**Conflict Resolution Modes:**
- `update`: Update existing documents (default)
- `skip`: Skip existing documents (insert only new)
- `error`: Raise error on conflict (strict mode)

---

## 📊 Implementation Roadmap

### Phase 4.1: Backend Implementation (3-5 days)

**Tasks:**
1. ✅ **Design API Specification** (This document)
2. ⏸️ **Implement Batch UPDATE**
   - Create Pydantic models
   - Implement PostgreSQL batch update
   - Implement Neo4j batch update
   - Implement ChromaDB batch update (delete + re-insert)
   - Implement CouchDB batch update
   - Error handling & transaction support
3. ⏸️ **Implement Batch DELETE**
   - Create Pydantic models
   - Implement soft delete logic
   - Implement hard delete logic
   - Implement cascade delete
   - Safety features (dry-run, audit logging)
4. ⏸️ **Implement Batch UPSERT**
   - Create Pydantic models
   - Implement PostgreSQL UPSERT
   - Implement Neo4j MERGE
   - Implement ChromaDB upsert
   - Implement CouchDB bulk docs
   - Conflict resolution logic

**Estimated Time:** 3-5 days (24-40 hours development)

---

### Phase 4.2: Testing & Validation (2-3 days)

**Tasks:**
1. ⏸️ **Unit Tests**
   - Test each endpoint with mock data
   - Test error handling
   - Test edge cases (empty arrays, invalid IDs, etc.)
2. ⏸️ **Integration Tests**
   - Test with real databases (PostgreSQL, ChromaDB, Neo4j, CouchDB)
   - Test cascade operations
   - Test transaction rollback
3. ⏸️ **Performance Tests**
   - Measure sequential vs batch performance
   - Validate speedup targets (67-100x)
   - Load testing (1000+ documents)
4. ⏸️ **Production Validation**
   - Test with production data (6,523 documents)
   - Verify data integrity
   - Rollback testing

**Estimated Time:** 2-3 days (16-24 hours testing)

---

### Phase 4.3: Documentation & Examples (1-2 days)

**Tasks:**
1. ⏸️ **API Documentation**
   - Update OpenAPI/Swagger docs
   - Add usage examples
   - Document error codes
2. ⏸️ **Code Examples**
   - Python examples (4 files × 300+ lines)
   - TypeScript examples (React hooks)
   - Vue.js examples (components)
   - JavaScript examples (vanilla)
3. ⏸️ **Integration Guides**
   - Update `docs/examples/README.md`
   - Add batch WRITE examples
   - Update performance metrics

**Estimated Time:** 1-2 days (8-16 hours documentation)

---

### Phase 4.4: Deployment & Monitoring (1 day)

**Tasks:**
1. ⏸️ **Backend Deployment**
   - Deploy to production
   - Verify endpoints
   - Monitor performance
2. ⏸️ **Monitoring Setup**
   - Add Prometheus metrics
   - Configure alerts
   - Dashboard updates

**Estimated Time:** 1 day (8 hours deployment)

---

## 🗓️ Timeline Estimation

**Total Estimated Time:** 7-11 days (56-88 hours)

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| 4.1 Backend Implementation | 3-5 days | Day 1 | Day 5 |
| 4.2 Testing & Validation | 2-3 days | Day 6 | Day 8 |
| 4.3 Documentation & Examples | 1-2 days | Day 9 | Day 10 |
| 4.4 Deployment & Monitoring | 1 day | Day 11 | Day 11 |

**Recommended Schedule:**
- **Week 1:** Backend implementation + Unit tests
- **Week 2:** Integration tests + Documentation + Deployment

---

## 🔧 Database Implementation Details

### PostgreSQL Batch Operations

#### Batch UPDATE Implementation

**Strategy 1: CASE/WHEN (Best for heterogeneous updates)**
```sql
UPDATE documents 
SET 
  classification = CASE 
    WHEN document_id = 'doc_0001' THEN 'VERTRAG_IMPORTANT'
    WHEN document_id = 'doc_0002' THEN 'RECHNUNG'
    ELSE classification
  END,
  quality_score = CASE 
    WHEN document_id = 'doc_0001' THEN 0.95
    WHEN document_id = 'doc_0002' THEN 0.88
    ELSE quality_score
  END,
  updated_at = NOW()
WHERE document_id IN ('doc_0001', 'doc_0002')
RETURNING document_id, classification, quality_score;
```

**Strategy 2: Temporary Table (Best for large batches)**
```sql
-- Create temporary table
CREATE TEMP TABLE updates_temp (
  document_id TEXT PRIMARY KEY,
  classification TEXT,
  quality_score FLOAT
);

-- Insert batch data
INSERT INTO updates_temp VALUES 
  ('doc_0001', 'VERTRAG_IMPORTANT', 0.95),
  ('doc_0002', 'RECHNUNG', 0.88),
  ...;

-- Batch update with JOIN
UPDATE documents d
SET 
  classification = u.classification,
  quality_score = u.quality_score,
  updated_at = NOW()
FROM updates_temp u
WHERE d.document_id = u.document_id
RETURNING d.document_id;

-- Cleanup
DROP TABLE updates_temp;
```

**Performance Comparison:**
- CASE/WHEN: Best for < 100 updates
- Temporary Table: Best for > 100 updates
- **Expected Performance:** 50 updates in ~15ms (vs ~1000ms sequential)

---

#### Batch DELETE Implementation

**Soft Delete (Recommended):**
```sql
UPDATE documents 
SET 
  deleted = true,
  deleted_at = NOW(),
  deleted_by = 'admin'
WHERE document_id IN ('doc_0001', 'doc_0002', ...)
RETURNING document_id, deleted_at;
```

**Hard Delete (Permanent):**
```sql
-- Start transaction
BEGIN;

-- Delete related records first (cascade)
DELETE FROM job_files WHERE document_id IN ('doc_0001', 'doc_0002', ...);

-- Delete main records
DELETE FROM documents WHERE document_id IN ('doc_0001', 'doc_0002', ...)
RETURNING document_id;

-- Commit
COMMIT;
```

**Performance:**
- 100 soft deletes: ~20ms (vs ~2000ms sequential)
- 100 hard deletes: ~50ms (with cascade)

---

#### Batch UPSERT Implementation

**PostgreSQL 9.5+ (INSERT ... ON CONFLICT):**
```sql
INSERT INTO documents (
  document_id, 
  file_path, 
  classification, 
  content_length, 
  quality_score,
  created_at
) VALUES 
  ('doc_0001', '/path/to/doc1.pdf', 'VERTRAG', 1024, 0.92, NOW()),
  ('doc_0002', '/path/to/doc2.pdf', 'RECHNUNG', 2048, 0.88, NOW()),
  ...
ON CONFLICT (document_id) 
DO UPDATE SET 
  file_path = EXCLUDED.file_path,
  classification = EXCLUDED.classification,
  content_length = EXCLUDED.content_length,
  quality_score = EXCLUDED.quality_score,
  updated_at = NOW()
RETURNING 
  document_id, 
  (xmax = 0) AS inserted,  -- true if inserted, false if updated
  created_at,
  updated_at;
```

**Detecting Insert vs Update:**
- `xmax = 0`: New row inserted (INSERT)
- `xmax != 0`: Existing row updated (UPDATE)

**Performance:**
- 100 upserts: ~30ms (vs ~2500ms sequential)
- Mixed insert/update: Same performance

---

### Neo4j Batch Operations

#### Batch UPDATE Implementation

**UNWIND-based Batch Update:**
```cypher
UNWIND $updates AS update
MATCH (n:Document {id: update.document_id})
SET n += update.fields
SET n.updated_at = timestamp()
RETURN n.id as document_id, n.classification, n.quality_score
```

**Python Code:**
```python
updates = [
    {
        "document_id": "doc_0001",
        "fields": {
            "classification": "VERTRAG_IMPORTANT",
            "quality_score": 0.95
        }
    },
    {
        "document_id": "doc_0002",
        "fields": {
            "classification": "RECHNUNG",
            "quality_score": 0.88
        }
    }
]

with driver.session(database="neo4j") as session:
    result = session.run(
        """
        UNWIND $updates AS update
        MATCH (n:Document {id: update.document_id})
        SET n += update.fields
        SET n.updated_at = timestamp()
        RETURN n.id as document_id
        """,
        {"updates": updates}
    )
    updated_ids = [record["document_id"] for record in result]
```

**Performance:**
- 50 updates: ~25ms (vs ~1000ms sequential)
- 200 updates: ~80ms (vs ~4000ms sequential)

---

#### Batch DELETE Implementation

**Soft Delete:**
```cypher
UNWIND $document_ids AS doc_id
MATCH (n:Document {id: doc_id})
SET n.deleted = true
SET n.deleted_at = timestamp()
RETURN n.id as document_id, n.deleted_at
```

**Hard Delete (with cascade):**
```cypher
UNWIND $document_ids AS doc_id
MATCH (n:Document {id: doc_id})
OPTIONAL MATCH (n)-[r]-()  // Find all relationships
DETACH DELETE n            // Delete node and relationships
RETURN doc_id
```

**Performance:**
- 100 soft deletes: ~30ms
- 100 hard deletes: ~100ms (with relationship cascade)

---

#### Batch UPSERT Implementation

**MERGE with ON CREATE/ON MATCH:**
```cypher
UNWIND $documents AS doc
MERGE (n:Document {id: doc.document_id})
ON CREATE SET 
  n += doc.fields,
  n.created_at = timestamp(),
  n.operation = 'inserted'
ON MATCH SET 
  n += doc.fields,
  n.updated_at = timestamp(),
  n.operation = 'updated'
RETURN 
  n.id as document_id,
  n.operation,
  n.created_at,
  n.updated_at
```

**Python Code:**
```python
documents = [
    {
        "document_id": "doc_0001",
        "fields": {
            "file_path": "/path/to/doc1.pdf",
            "classification": "VERTRAG",
            "quality_score": 0.92
        }
    },
    {
        "document_id": "doc_0002",
        "fields": {
            "file_path": "/path/to/doc2.pdf",
            "classification": "RECHNUNG",
            "quality_score": 0.88
        }
    }
]

with driver.session(database="neo4j") as session:
    result = session.run(
        """
        UNWIND $documents AS doc
        MERGE (n:Document {id: doc.document_id})
        ON CREATE SET n += doc.fields, n.created_at = timestamp()
        ON MATCH SET n += doc.fields, n.updated_at = timestamp()
        RETURN n.id, n.created_at = n.updated_at as inserted
        """,
        {"documents": documents}
    )
```

**Performance:**
- 100 upserts: ~50ms (vs ~2500ms sequential)

---

### ChromaDB Batch Operations

#### Batch UPDATE Implementation

**Challenge:** ChromaDB has **no native update operation**

**Solution: Delete + Re-insert Pattern:**
```python
# Step 1: Fetch existing vectors (to preserve embedding)
existing_data = collection.get(
    ids=document_ids,
    include=["embeddings", "metadatas"]
)

# Step 2: Delete old vectors
collection.delete(ids=document_ids)

# Step 3: Re-insert with updated metadata
collection.add(
    ids=document_ids,
    embeddings=existing_data["embeddings"],  # Preserve original
    metadatas=updated_metadatas  # New metadata
)
```

**Optimization:** Use upsert=True (ChromaDB 0.4.0+)
```python
collection.upsert(
    ids=document_ids,
    embeddings=embeddings,  # Optional: keep existing if None
    metadatas=updated_metadatas
)
```

**Performance:**
- 50 updates: ~100ms (vs ~1000ms sequential)
- 200 updates: ~300ms (vs ~4000ms sequential)

---

#### Batch DELETE Implementation

**Simple Batch Delete:**
```python
collection.delete(ids=document_ids)
```

**Soft Delete (Metadata-based):**
```python
# Fetch existing data
existing = collection.get(ids=document_ids, include=["embeddings", "metadatas"])

# Update metadata with "deleted" flag
updated_metadatas = [
    {**meta, "deleted": True, "deleted_at": "2025-10-21"}
    for meta in existing["metadatas"]
]

# Upsert with updated metadata
collection.upsert(
    ids=document_ids,
    embeddings=existing["embeddings"],
    metadatas=updated_metadatas
)
```

**Performance:**
- 100 deletes: ~20ms (hard delete)
- 100 soft deletes: ~80ms (upsert with metadata)

---

#### Batch UPSERT Implementation

**ChromaDB Native Upsert (v0.4.0+):**
```python
collection.upsert(
    ids=document_ids,
    embeddings=embeddings,
    metadatas=metadatas
)
# Automatically inserts if missing, updates if exists
```

**Fallback for Older Versions:**
```python
# Check existence
existing_ids = collection.get(ids=document_ids, include=[])["ids"]
existing_set = set(existing_ids)

# Separate into insert and update
to_insert = [doc for doc in documents if doc["id"] not in existing_set]
to_update = [doc for doc in documents if doc["id"] in existing_set]

# Insert new
if to_insert:
    collection.add(
        ids=[d["id"] for d in to_insert],
        embeddings=[d["embedding"] for d in to_insert],
        metadatas=[d["metadata"] for d in to_insert]
    )

# Update existing (delete + re-insert)
if to_update:
    update_ids = [d["id"] for d in to_update]
    collection.delete(ids=update_ids)
    collection.add(
        ids=update_ids,
        embeddings=[d["embedding"] for d in to_update],
        metadatas=[d["metadata"] for d in to_update]
    )
```

**Performance:**
- 100 upserts: ~50ms (native upsert)
- 100 upserts: ~120ms (fallback method)

---

### CouchDB Batch Operations

#### Batch UPDATE Implementation

**_bulk_docs API:**
```python
# Fetch existing documents (to get _rev)
existing_docs = db.view("_all_docs", keys=document_ids, include_docs=True)
doc_revs = {doc["id"]: doc["doc"]["_rev"] for doc in existing_docs.rows}

# Prepare bulk update
bulk_updates = [
    {
        "_id": doc_id,
        "_rev": doc_revs.get(doc_id),  # Required for update
        "fields": updated_fields,
        "updated_at": "2025-10-21"
    }
    for doc_id, updated_fields in updates.items()
]

# Bulk update
result = db.update(bulk_updates)

# Check results
success_count = sum(1 for r in result if "ok" in r)
failed_count = len(result) - success_count
```

**Performance:**
- 50 updates: ~30ms (vs ~1000ms sequential)
- 200 updates: ~100ms (vs ~4000ms sequential)

---

#### Batch DELETE Implementation

**Soft Delete (_deleted: false, custom field):**
```python
# Fetch documents
existing_docs = db.view("_all_docs", keys=document_ids, include_docs=True)

# Mark as deleted (but keep document)
bulk_deletes = [
    {
        "_id": doc["id"],
        "_rev": doc["doc"]["_rev"],
        "deleted": True,
        "deleted_at": "2025-10-21"
    }
    for doc in existing_docs.rows
]

result = db.update(bulk_deletes)
```

**Hard Delete (_deleted: true):**
```python
# Fetch documents
existing_docs = db.view("_all_docs", keys=document_ids, include_docs=True)

# Prepare hard delete
bulk_deletes = [
    {
        "_id": doc["id"],
        "_rev": doc["doc"]["_rev"],
        "_deleted": True  # CouchDB hard delete flag
    }
    for doc in existing_docs.rows
]

result = db.update(bulk_deletes)
```

**Performance:**
- 100 deletes: ~40ms (soft or hard)

---

#### Batch UPSERT Implementation

**CouchDB Auto-Upserts (no _rev = insert, with _rev = update):**
```python
bulk_upserts = [
    {
        "_id": doc_id,
        "fields": fields,
        "metadata": metadata,
        "upserted_at": "2025-10-21"
    }
    for doc_id, fields, metadata in documents
]

result = db.update(bulk_upserts)

# Check operation type
for r in result:
    if "rev" in r:
        if r["rev"].startswith("1-"):
            operation = "inserted"
        else:
            operation = "updated"
```

**Performance:**
- 100 upserts: ~50ms (auto-detection)

---

## 🛡️ Safety & Error Handling

### Transaction Support

**PostgreSQL:**
```python
async def batch_update_transactional(updates):
    async with postgres_backend.pool.acquire() as conn:
        async with conn.transaction():
            try:
                # Perform batch update
                result = await conn.executemany(update_query, updates)
                return {"success": True, "updated": len(result)}
            except Exception as e:
                # Automatic rollback on error
                logger.error(f"Transaction failed: {e}")
                raise
```

**Neo4j:**
```python
def batch_update_transactional(updates):
    with driver.session(database="neo4j") as session:
        with session.begin_transaction() as tx:
            try:
                result = tx.run(unwind_query, {"updates": updates})
                tx.commit()
                return {"success": True, "updated": result.consume().counters.properties_set}
            except Exception as e:
                tx.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
```

**ChromaDB/CouchDB:**
- No native transaction support
- Implement application-level compensation logic
- Store operation log for manual rollback

---

### Error Handling Strategy

**Levels of Error Handling:**

1. **Request Validation (400 Bad Request)**
   - Empty document_ids array
   - Invalid document_id format
   - Missing required fields
   - Batch size exceeds limit

2. **Database-Level Errors (503 Service Unavailable)**
   - Database connection failed
   - Query timeout
   - Insufficient permissions

3. **Partial Success (207 Multi-Status)**
   - Some documents updated, some failed
   - Return detailed results per document

**Example Response (Partial Success):**
```json
{
  "success": false,
  "updated": 48,
  "failed": 2,
  "errors": [
    {
      "document_id": "doc_0025",
      "database": "neo4j",
      "error_message": "Node not found"
    },
    {
      "document_id": "doc_0037",
      "database": "chromadb",
      "error_message": "Embedding dimension mismatch"
    }
  ],
  "execution_time_ms": 45.23,
  "results": [...]
}
```

---

### Dry-Run Mode

**Purpose:** Preview changes without committing

**Implementation:**
```python
class BatchUpdateRequest(BaseModel):
    updates: List[DocumentUpdate]
    dry_run: bool = Field(default=False, description="Preview only, no changes")

@app.post("/api/v1/batch/update")
async def batch_update(request: BatchUpdateRequest):
    if request.dry_run:
        # Validate updates, simulate changes
        preview = []
        for update in request.updates:
            # Check if document exists
            exists = await check_document_exists(update.document_id)
            preview.append({
                "document_id": update.document_id,
                "exists": exists,
                "would_update": exists,
                "fields": update.fields
            })
        return {
            "dry_run": True,
            "preview": preview,
            "total": len(preview),
            "would_update": sum(1 for p in preview if p["would_update"])
        }
    else:
        # Perform actual update
        return await perform_batch_update(request.updates)
```

---

### Audit Logging

**Purpose:** Track who changed what, when

**PostgreSQL Audit Table:**
```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    operation TEXT NOT NULL,  -- 'update', 'delete', 'upsert'
    document_id TEXT NOT NULL,
    user_id TEXT,
    changes JSONB,  -- {"field": {"old": value, "new": value}}
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Trigger for automatic audit logging
CREATE OR REPLACE FUNCTION audit_document_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (operation, document_id, changes)
    VALUES (
        TG_OP,
        NEW.document_id,
        jsonb_build_object(
            'classification', jsonb_build_object('old', OLD.classification, 'new', NEW.classification),
            'quality_score', jsonb_build_object('old', OLD.quality_score, 'new', NEW.quality_score)
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER document_audit
AFTER UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION audit_document_changes();
```

**Application-Level Logging:**
```python
async def log_batch_update(updates, user_id):
    for update in updates:
        await audit_log.insert({
            "operation": "batch_update",
            "document_id": update.document_id,
            "user_id": user_id,
            "changes": update.fields,
            "timestamp": datetime.now()
        })
```

---

## 📈 Monitoring & Metrics

### Prometheus Metrics

**Metrics to Track:**
```python
from prometheus_client import Counter, Histogram

# Request counters
batch_update_requests = Counter(
    'covina_batch_update_requests_total',
    'Total batch update requests',
    ['status']  # 'success', 'partial', 'failed'
)

batch_delete_requests = Counter(
    'covina_batch_delete_requests_total',
    'Total batch delete requests',
    ['status', 'mode']  # mode: 'soft', 'hard'
)

batch_upsert_requests = Counter(
    'covina_batch_upsert_requests_total',
    'Total batch upsert requests',
    ['status']
)

# Performance histograms
batch_update_duration = Histogram(
    'covina_batch_update_duration_seconds',
    'Batch update execution time',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

batch_update_size = Histogram(
    'covina_batch_update_size',
    'Number of documents per batch update',
    buckets=[10, 50, 100, 200, 500, 1000]
)

# Document counters
documents_updated = Counter(
    'covina_documents_updated_total',
    'Total documents updated',
    ['database']  # 'postgresql', 'neo4j', etc.
)

documents_deleted = Counter(
    'covina_documents_deleted_total',
    'Total documents deleted',
    ['database', 'mode']
)

documents_upserted = Counter(
    'covina_documents_upserted_total',
    'Total documents upserted',
    ['database', 'operation']  # 'inserted', 'updated'
)
```

**Usage in Endpoint:**
```python
@app.post("/api/v1/batch/update")
async def batch_update(request: BatchUpdateRequest):
    start_time = time.time()
    
    try:
        result = await perform_batch_update(request.updates)
        
        # Metrics
        status = 'success' if result['failed'] == 0 else 'partial'
        batch_update_requests.labels(status=status).inc()
        batch_update_size.observe(len(request.updates))
        documents_updated.labels(database='postgresql').inc(result['updated'])
        
        return result
        
    except Exception as e:
        batch_update_requests.labels(status='failed').inc()
        raise
        
    finally:
        duration = time.time() - start_time
        batch_update_duration.observe(duration)
```

---

### Grafana Dashboard

**Dashboard Panels:**

1. **Request Rate**
   - Batch UPDATE/DELETE/UPSERT requests per second
   - Success vs failure rate
   - Chart type: Time series

2. **Performance**
   - P50/P95/P99 latency
   - Average batch size
   - Chart type: Heatmap

3. **Throughput**
   - Documents updated/deleted/upserted per second
   - Per-database throughput
   - Chart type: Stacked area

4. **Error Rate**
   - Failed requests percentage
   - Error breakdown by type
   - Chart type: Gauge + Table

**Example Queries:**
```promql
# Request rate
rate(covina_batch_update_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(covina_batch_update_duration_seconds_bucket[5m]))

# Success rate
rate(covina_batch_update_requests_total{status="success"}[5m]) 
/ 
rate(covina_batch_update_requests_total[5m])

# Throughput per database
rate(covina_documents_updated_total{database="postgresql"}[5m])
```

---

## 🚨 Alerts

### Critical Alerts (PagerDuty)

**1. High Error Rate**
```yaml
alert: BatchUpdateHighErrorRate
expr: |
  rate(covina_batch_update_requests_total{status="failed"}[5m]) 
  / 
  rate(covina_batch_update_requests_total[5m]) 
  > 0.1
for: 5m
severity: critical
description: "Batch update error rate > 10% for 5 minutes"
```

**2. High Latency**
```yaml
alert: BatchUpdateHighLatency
expr: |
  histogram_quantile(0.95, 
    rate(covina_batch_update_duration_seconds_bucket[5m])
  ) > 1.0
for: 10m
severity: warning
description: "Batch update P95 latency > 1 second"
```

**3. Database Connection Failure**
```yaml
alert: BatchUpdateDatabaseDown
expr: |
  rate(covina_batch_update_requests_total{status="failed"}[1m]) > 10
for: 2m
severity: critical
description: "Database connection issues detected"
```

---

## 📚 Code Structure

### File Organization

```
covina/
├─ main_backend.py (+300 lines)
│  ├─ Batch UPDATE endpoint
│  ├─ Batch DELETE endpoint
│  ├─ Batch UPSERT endpoint
│  └─ Request/Response models
│
├─ database/
│  ├─ batch_operations.py (existing, +200 lines)
│  │  ├─ PostgreSQLBatchWriter (new)
│  │  ├─ Neo4jBatchWriter (new)
│  │  ├─ ChromaDBBatchWriter (new)
│  │  └─ CouchDBBatchWriter (new)
│  │
│  └─ batch_write_core.py (new, 500+ lines)
│     ├─ BatchUpdateExecutor
│     ├─ BatchDeleteExecutor
│     └─ BatchUpsertExecutor
│
├─ tests/
│  ├─ test_batch_update.py (new, 400+ lines)
│  ├─ test_batch_delete.py (new, 400+ lines)
│  └─ test_batch_upsert.py (new, 400+ lines)
│
└─ docs/
   ├─ examples/
   │  ├─ batch_update_examples.py (new, 400+ lines)
   │  ├─ batch_delete_examples.py (new, 400+ lines)
   │  ├─ batch_upsert_examples.py (new, 400+ lines)
   │  └─ README.md (update)
   │
   └─ PHASE4_BATCH_WRITE_PLAN.md (this file)
```

**Estimated Lines of Code:**
- Backend implementation: ~1,000 lines
- Tests: ~1,200 lines
- Examples: ~1,200 lines
- Documentation: ~2,500 lines (this plan)
- **Total: ~5,900 lines**

---

## 🎯 Success Criteria

### Functional Requirements

✅ **Batch UPDATE**
- [ ] Accept 1-1000 documents per request
- [ ] Support partial and full update modes
- [ ] Update PostgreSQL, Neo4j, ChromaDB, CouchDB
- [ ] Return detailed results per document
- [ ] Handle errors gracefully (partial success)

✅ **Batch DELETE**
- [ ] Accept 1-1000 documents per request
- [ ] Support soft and hard delete modes
- [ ] Cascade delete related data
- [ ] Audit logging
- [ ] Dry-run mode

✅ **Batch UPSERT**
- [ ] Accept 1-1000 documents per request
- [ ] Detect insert vs update operations
- [ ] Support conflict resolution modes
- [ ] Return operation type per document

---

### Performance Requirements

✅ **Speedup Targets**
- [ ] Batch UPDATE: 67-80x faster than sequential
- [ ] Batch DELETE: 100x faster than sequential
- [ ] Batch UPSERT: 83x faster than sequential

✅ **Latency Targets**
- [ ] 50 updates: < 20ms (P95)
- [ ] 200 updates: < 80ms (P95)
- [ ] 1000 updates: < 400ms (P95)

✅ **Throughput Targets**
- [ ] 2,500+ updates per second (sustained)
- [ ] 5,000+ deletes per second (sustained)
- [ ] 2,000+ upserts per second (sustained)

---

### Reliability Requirements

✅ **Error Handling**
- [ ] Validate all requests (400 Bad Request)
- [ ] Handle database errors (503 Service Unavailable)
- [ ] Support partial success (207 Multi-Status)
- [ ] Transaction rollback on critical failures

✅ **Safety Features**
- [ ] Dry-run mode (preview changes)
- [ ] Audit logging (track all changes)
- [ ] Soft delete default (recoverable)
- [ ] Batch size limits (prevent overload)

✅ **Monitoring**
- [ ] Prometheus metrics
- [ ] Grafana dashboard
- [ ] Critical alerts (PagerDuty)
- [ ] Performance tracking

---

## 📖 Related Documentation

**Phase 3 (Batch READ) - Completed:**
- `docs/PHASE3_PRODUCTION_TEST_RESULTS.md` - Production test results (8-97x speedup)
- `docs/BATCH_API_INTEGRATION.md` - Backend integration guide
- `docs/examples/README.md` - API integration examples

**UDS3 Framework:**
- `docs/UDS3_FULL_INTEGRATION_COMPLETE.md` - Multi-database architecture
- `database/batch_operations.py` - ChromaDB/Neo4j batch inserters

**Performance Optimization:**
- `docs/PERFORMANCE_OPTIMIZATION_ROADMAP.md` - 4-phase optimization plan
- `docs/LOAD_TEST_REPORT.md` - Load testing results

---

## ✅ Next Steps

**Immediate Actions:**

1. **Review & Approval**
   - [ ] Review this plan with team
   - [ ] Approve API specification
   - [ ] Approve timeline (7-11 days)

2. **Start Implementation (Phase 4.1)**
   - [ ] Create `database/batch_write_core.py`
   - [ ] Implement PostgreSQLBatchWriter
   - [ ] Implement Batch UPDATE endpoint
   - [ ] Write unit tests

3. **Milestone 1: Batch UPDATE Complete**
   - [ ] Backend implementation
   - [ ] Unit tests passing
   - [ ] Integration tests passing
   - [ ] Performance validated

4. **Milestone 2: Batch DELETE Complete**
   - [ ] Backend implementation
   - [ ] Safety features (dry-run, audit)
   - [ ] Tests passing
   - [ ] Performance validated

5. **Milestone 3: Batch UPSERT Complete**
   - [ ] Backend implementation
   - [ ] Conflict resolution logic
   - [ ] Tests passing
   - [ ] Performance validated

6. **Milestone 4: Phase 4 Complete**
   - [ ] All endpoints implemented
   - [ ] All tests passing
   - [ ] Documentation complete
   - [ ] Deployed to production

---

## 📞 Contact & Support

**Questions or Issues:**
- Check Phase 3 implementation: `main_backend.py` (Lines 1900-2100)
- Review batch operations: `database/batch_operations.py`
- Test with Phase 3 endpoints: `http://127.0.0.1:45678/api/v1/batch/get`

**Documentation Updates:**
- This plan will be updated as implementation progresses
- Performance metrics will be added after testing
- Examples will be added after implementation

---

**Status:** 🎯 **Ready to Start Implementation**  
**Next Action:** Begin Phase 4.1 - Backend Implementation  
**Estimated Completion:** 7-11 days from start  

**Last Updated:** 21. Oktober 2025  
**Version:** 1.0.0 - Initial Planning Complete
