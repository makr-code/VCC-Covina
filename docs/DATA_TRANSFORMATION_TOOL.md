# Data Transformation Tool

**Transform existing data in databases without re-uploading files.**

## 🎯 Purpose

After making changes to the ingestion pipeline (polyglot optimization, CouchDB migration, new embedding models), this tool transforms existing data in the databases to match the new formats.

**Key Difference from Reprocessing:**
- **Reprocessing** (`/maintenance/reprocess`): Re-uploads files through ingestion pipeline
- **Transformation** (`/maintenance/transform`): Updates existing database records directly

## 🚀 Transformation Types

### 1. **Polyglot Optimization** (`polyglot`)
Transforms existing data to leverage polyglot database strengths:
- **PostgreSQL**: Keep structured relational data
- **Neo4j**: Add graph relationships (if missing)
- **ChromaDB**: Generate semantic embeddings (if missing)
- **CouchDB**: Add full document content (if missing)

**Use Case:** After implementing polyglot optimizations, update old records

### 2. **CouchDB Migration** (`couchdb_migration`)
Copies documents from PostgreSQL to CouchDB:
- Reads all documents from PostgreSQL
- Creates CouchDB documents with full content
- Preserves metadata and timestamps

**Use Case:** Initial CouchDB setup, backfilling data

### 3. **Embedding Regeneration** (`embedding_regeneration`)
Updates ChromaDB vectors with new embedding model:
- Re-generates embeddings using latest model
- Updates existing vectors in ChromaDB
- Improves semantic search quality

**Use Case:** After upgrading to better embedding model

### 4. **Graph Rebuild** (`graph_rebuild`)
Recreates Neo4j relationships from metadata:
- Extracts relationships from PostgreSQL metadata
- Rebuilds graph structure in Neo4j
- Fixes broken or missing relationships

**Use Case:** After schema changes or data corruption

## 📦 Components

### Backend API Endpoints

```python
# Start transformation job
POST /maintenance/transform
{
    "transformation_type": "polyglot",  # polyglot | couchdb_migration | embedding_regeneration | graph_rebuild
    "scope": "all",                     # all | by_ids | since | range
    "batch_size": 100,                  # Documents per batch
    "dry_run": false                    # Preview mode (don't modify data)
}

# Get job status
GET /maintenance/transform/{job_id}

# Cancel job
POST /maintenance/transform/{job_id}/cancel
```

### Admin GUI

**Location:** `admin_tools/data_transformation_tool.py`

**Features:**
- Configure transformation parameters
- Start/cancel jobs
- Monitor real-time progress
- View errors and warnings
- Batch size control
- Dry-run mode for preview

### Launcher Script

**Location:** `scripts/launch_data_transformation.ps1`

```powershell
.\scripts\launch_data_transformation.ps1
```

## 🔧 Usage

### 1. Start Backend (if not running)

```powershell
.\scripts\start_services.ps1
```

### 2. Launch Transformation Tool

```powershell
.\scripts\launch_data_transformation.ps1
```

### 3. Configure Transformation

**GUI:**
1. Select **Transformation Type** (e.g., `polyglot`)
2. Choose **Scope**:
   - `all`: All documents
   - `by_ids`: Specific document IDs
   - `since`: Documents created after date
   - `range`: Date range
3. Set **Batch Size** (default: 100)
4. Optional: Set **Limit** (max documents)
5. Enable **Dry Run** to preview (no changes)

**API Example:**
```bash
curl -X POST http://127.0.0.1:45678/maintenance/transform \
  -H "Content-Type: application/json" \
  -d '{
    "transformation_type": "polyglot",
    "scope": "all",
    "batch_size": 100,
    "dry_run": false
  }'
```

### 4. Monitor Progress

**GUI:** Real-time progress bar and stats

**API:**
```bash
curl http://127.0.0.1:45678/maintenance/transform/{job_id}
```

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "running",
  "progress": {
    "total": 1000,
    "processed": 250,
    "succeeded": 240,
    "failed": 5,
    "skipped": 5,
    "percentage": 25.0
  },
  "errors": [
    {
      "document_id": "doc_456",
      "error": "Embedding generation failed",
      "timestamp": "2025-10-31T10:30:00Z"
    }
  ]
}
```

### 5. Cancel Job (if needed)

**GUI:** Click **⏹ Cancel Job** button

**API:**
```bash
curl -X POST http://127.0.0.1:45678/maintenance/transform/{job_id}/cancel
```

## 📊 Performance

**Batch Processing:**
- Default batch size: 100 documents
- Recommended: 50-200 for polyglot (embeddings are expensive)
- Max: 1000 for simple migrations

**Speed Estimates:**
- **Polyglot:** ~1-2 docs/sec (with embedding generation)
- **CouchDB Migration:** ~10-20 docs/sec
- **Embedding Regeneration:** ~1-2 docs/sec
- **Graph Rebuild:** ~5-10 docs/sec

**Memory Usage:**
- Batch size 100: ~500 MB RAM
- Batch size 1000: ~2 GB RAM

## ⚠️ Safety Features

### Dry Run Mode
Preview what will be transformed without modifying data:
```json
{
  "transformation_type": "polyglot",
  "scope": "all",
  "dry_run": true  // ← Preview only!
}
```

### Job Cancellation
Cancel long-running jobs:
- GUI: **⏹ Cancel Job** button
- API: `POST /maintenance/transform/{job_id}/cancel`
- Job stops at next batch boundary (graceful)

### Error Handling
- Failed documents are logged but don't stop job
- Last 10 errors visible in job status
- Full error log in backend logs

### Skipping Existing Data
- **Polyglot:** Skips documents that already have embeddings/relationships
- **CouchDB:** Skips documents that already exist in CouchDB
- **Efficient:** Only processes what's needed

## 🔍 Troubleshooting

### Problem: Job stuck in "queued" status
**Solution:** Check backend logs, job may have failed to start

### Problem: High failure rate
**Causes:**
- Database connection issues (ChromaDB, Neo4j down)
- Embedding model not loaded
- Insufficient memory

**Solution:** 
- Check database connectivity
- Reduce batch size
- Check backend logs for details

### Problem: Slow performance
**Causes:**
- Large batch size (memory pressure)
- Embedding generation bottleneck
- Database write latency

**Solution:**
- Reduce batch size to 50
- Check database performance
- Consider running during off-hours

## 📝 Example Scenarios

### Scenario 1: Polyglot Optimization After Migration

**Situation:** You've implemented polyglot transformations, but existing data still has old format

**Solution:**
```json
{
  "transformation_type": "polyglot",
  "scope": "all",
  "batch_size": 100,
  "dry_run": false
}
```

**Result:** All documents get embeddings in ChromaDB and relationships in Neo4j

### Scenario 2: CouchDB Backfill

**Situation:** CouchDB was added later, PostgreSQL has 10,000 documents

**Solution:**
```json
{
  "transformation_type": "couchdb_migration",
  "scope": "all",
  "batch_size": 200,
  "limit": 10000
}
```

**Result:** All 10,000 documents copied to CouchDB

### Scenario 3: Upgrade Embedding Model

**Situation:** New embedding model released (better quality)

**Solution:**
```json
{
  "transformation_type": "embedding_regeneration",
  "scope": "all",
  "batch_size": 50
}
```

**Result:** All ChromaDB vectors regenerated with new model

## 🔐 Security

**Access Control:**
- **Admin-only** endpoints (RBAC required)
- All transformation operations require admin role
- Audit log of all transformations

**Data Safety:**
- Dry-run mode for testing
- Batch processing (graceful failure)
- Job cancellation support
- Error logging (no data loss)

## 📚 Related Documentation

- **Polyglot Optimization:** `docs/POLYGLOT_DATA_GAP_ANALYSIS.md`
- **UDS3 Architecture:** `docs/UDS3_FULL_INTEGRATION_COMPLETE.md`
- **Reprocessing Tool:** Backend endpoint `/maintenance/reprocess`
- **Admin Tools:** `admin_tools/` directory

## 🎉 Summary

**Data Transformation Tool** enables efficient migration of existing data to new formats without re-uploading files:

✅ **4 Transformation Types** (polyglot, CouchDB, embeddings, graph)  
✅ **Admin GUI** with real-time progress monitoring  
✅ **Batch Processing** for efficiency  
✅ **Safety Features** (dry-run, cancellation, error handling)  
✅ **Production-Ready** with comprehensive error logging  

**Use this tool whenever you update the data model or add new database features!**
