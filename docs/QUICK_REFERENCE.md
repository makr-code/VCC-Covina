# Covina System - Quick Reference Card

**Version:** 3.4 | **Status:** ✅ PRODUCTION READY | **Rating:** ⭐⭐⭐⭐⭐ 5.0/5

**Latest Update:** SAGA Production Mode + Microservices Startup Fix (13.10.2025)

---

## 🚀 Quick Start

```powershell
# Start Services (with improved health checks)
.\scripts\start_services.ps1

# Stop Services (port-based detection)
.\scripts\stop_services.ps1

# Start Services (Production, Optimized)
.\scripts\deploy_production.ps1

# Health Check
curl http://127.0.0.1:45678/health
curl http://127.0.0.1:45679/health
```

---

## 🔧 SAGA Orchestrator Status

**Mode:** ✅ **Production Mode** (PostgreSQL Backend)  
**Mock Mode:** ❌ **DISABLED**

**Features:**
- ✅ Persistence (PostgreSQL)
- ✅ Compensation (Rollback)
- ✅ ACID Transactions
- ✅ Idempotency

**Generic Executors:**
- `RelationalSAGAExecutor` (PostgreSQL, MySQL, SQLite)
- `DocumentSAGAExecutor` (CouchDB, MongoDB)
- `VectorSAGAExecutor` (ChromaDB, Pinecone, Weaviate)
- `GraphSAGAExecutor` (Neo4j, ArangoDB, JanusGraph)

---

## 📊 Current Performance

```
Upload:    187 files/s   (100% success rate)
Query:     280 queries/s (<300ms P95 latency)
Document:  ~1,100ms     (Real embeddings, all 4 DBs)
WebSocket: <50ms        (Real-time updates)
```

---

## 🎯 System Architecture

```
Main Backend (45678)          Ingestion Backend (45679)
├─ Queries                    ├─ Upload
├─ DSGVO                      ├─ Job Management
├─ Review Queue               ├─ I/O Workers: 36
└─ Handelsregister            └─ CPU Workers: 36
         │                             │
         └──────────┬──────────────────┘
                    ▼
         ┌─────────────────────┐
         │   UDS3 Framework    │
         └─────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
PostgreSQL      ChromaDB         Neo4j
(Relational)    (Vectors)       (Graph)
1,976 docs      87,910+ vecs    1,930 nodes
    │               │               │
    └───────────────┼───────────────┘
                    ▼
                CouchDB
              (Documents)
               1,927 docs
```

---

## 🔧 Key Features

### ✅ Production Ready
- [x] Microservices (Main + Ingestion)
- [x] UDS3 Full Polyglot (4 Databases)
- [x] Real Embeddings (384-dim)
- [x] Batch Embeddings (+46%)
- [x] WebSocket Real-Time (<50ms)
- [x] Load Tested (187 f/s, 280 q/s)

### ⏸️ Ready (Not Activated)
- [ ] Batch Insert (-67% latency)
  - Code: ✅ Complete
  - ENV: ✅ Set (true)
  - Status: ⏸️ Needs restart

---

## 📁 Important Files

```
Backend:
├─ backend.py (Main, Port 45678)
├─ ingestion_backend.py (Upload, Port 45679)
└─ .env.production (Configuration)

Database:
├─ database/database_api_postgresql.py
├─ database/database_api_couchdb.py
├─ database/batch_operations.py (Batch Insert)
└─ uds3/database/database_api_chromadb_remote.py

Optimization:
├─ ingestion/batch_embeddings.py (Real Embeddings)
└─ database/batch_operations.py (Batch Insert)

Tests:
├─ tests/test_batch_embeddings.py (8/8 ✅)
├─ tests/test_chromadb_batch_insert.py (8/8 ✅)
└─ tests/test_full_uds3_integration.py (5.0/5 ✅)
```

---

## 🔑 Environment Variables

```bash
# Worker Pool
WORKERS_IO=36
WORKERS_CPU=36

# Databases
POSTGRES_HOST=192.168.178.94
CHROMADB_HOST=192.168.178.94
NEO4J_HOST=192.168.178.94
COUCHDB_HOST=192.168.178.94

# Batch Embeddings (✅ ACTIVE)
ENABLE_BATCH_EMBEDDINGS=true
BATCH_EMBEDDINGS_SIZE=32
BATCH_EMBEDDINGS_USE_GPU=true

# Batch Insert (⏸️ READY)
ENABLE_CHROMA_BATCH_INSERT=true
CHROMA_BATCH_INSERT_SIZE=100
```

---

## 🧪 Testing

```powershell
# Load Tests
python tests\load_test_upload_simple.py
python tests\load_test_queries_simple.py

# Integration Test
python tests\test_full_uds3_integration.py

# Batch Operations
python tests\test_batch_embeddings.py
python tests\test_chromadb_batch_insert.py
```

---

## 📈 Performance Targets

### Current (Validated)
```
Upload:  187 f/s
Query:   280 q/s
Doc:     ~1,100ms
```

### Phase 1 (Batch Insert Active)
```
Upload:  250-320 f/s (+34-71%)
Query:   1,000-2,000 q/s (Linux)
Doc:     ~370ms (-67%)
```

### Phase 2 (I/O Optimized)
```
Upload:  500-1,200 f/s (+167-541%)
Query:   1,000-2,000 q/s
Latency: <300ms P95
```

---

## 🚨 Troubleshooting

### Service Health
```powershell
# Check Backend Status
curl http://127.0.0.1:45678/health
curl http://127.0.0.1:45679/health

# Check Database Connections
# → See logs for "✅ Connected" messages
```

### Common Issues

**ChromaDB Not Available:**
```
Solution: Check CHROMADB_HOST in .env.production
Verify: curl http://192.168.178.94:8000/api/v1
```

**Neo4j Auth Error:**
```
Solution: Update NEO4J_USER/NEO4J_PASSWORD in .env.production
Default: neo4j / neo4j
```

**Batch Insert Not Working:**
```
Solution: Restart backend after ENV change
Command: .\scripts\stop_services.ps1 && .\scripts\deploy_production.ps1
```

---

## 📚 Documentation

```
Complete System:
docs/COMPLETE_SYSTEM_DOCUMENTATION.md (5,000+ lines)

UDS3 Integration:
docs/UDS3_FULL_INTEGRATION_COMPLETE.md (1,200+ lines)

Batch Operations:
docs/BATCH_EMBEDDINGS_IMPLEMENTATION.md (1,200+ lines)
docs/CHROMADB_BATCH_INSERT_COMPLETE.md (400+ lines)

Performance:
docs/LOAD_TEST_REPORT.md (700+ lines)
docs/PERFORMANCE_OPTIMIZATION_ROADMAP.md (1,100+ lines)

Quick Reference:
docs/UDS3_QUICK_REFERENCE.md (500+ lines)
docs/EXECUTIVE_SUMMARY.md
docs/PERFORMANCE_SUMMARY.md
```

---

## 🎯 Next Steps

### To Activate Batch Insert (-67% Latency)

```powershell
# 1. Verify ENV
cat .env.production | grep CHROMA_BATCH
# → Should show: ENABLE_CHROMA_BATCH_INSERT=true

# 2. Restart Backend
.\scripts\stop_services.ps1
.\scripts\deploy_production.ps1

# 3. Verify Logs
# → Look for: "🚀 ChromaDB Batch Insert aktiviert"
# → Look for: "✅ Batch Insert SUCCESS"
```

### For GPU Acceleration (+300-500%)

```bash
# Install CUDA Toolkit + PyTorch GPU
# Expected: 43ms → 9ms encoding (-79%)
# See: docs/GPU_SETUP_GUIDE.md (TODO)
```

---

## 📞 Support

**Endpoints:**
- Main API: http://127.0.0.1:45678
- Ingestion API: http://127.0.0.1:45679
- WebSocket: ws://127.0.0.1:45679/ws/jobs
- API Docs: http://127.0.0.1:45678/docs

**Databases:**
- PostgreSQL: 192.168.178.94:5432
- ChromaDB: 192.168.178.94:8000
- Neo4j: 192.168.178.94:7687
- CouchDB: 192.168.178.94:32931

---

**Last Update:** 12. Oktober 2025, 21:30 Uhr  
**Version:** 3.3 (Real Embeddings + Batch Operations)  
**Maintainer:** Covina AI Team
