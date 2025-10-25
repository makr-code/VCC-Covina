# Polyglot Admin Tool v3.1

**Universal Document Inspector & Database Viewer for Polyglot Persistence Systems**

## 🎯 Overview

The Polyglot Admin Tool provides a unified interface to inspect and manage data across multiple database systems:

- **Neo4j Graph Database** - Cypher queries, node inspection, relationship visualization
- **ChromaDB Vector Store** - Similarity search, embedding inspection, metadata viewer
- **PostgreSQL Relational DB** - Document management, metadata queries, full-text search
- **UDS3 SAGA Orchestrator** - Transaction monitoring, step tracking, failure analysis
- **🆕 Hybrid Search** - Semantic + Keyword + Regex unified search

## 🚀 Quick Start

### Launch the Tool

```powershell
python tools\polyglot_admin.py
```

### Prerequisites

- Python 3.8+
- UDS3 package installed
- Database credentials configured in `uds3/database/config.py`
- Backend services running:
  - PostgreSQL (port 5432)
  - ChromaDB (port 8000)
  - Neo4j (port 7687)

## 📊 Features

### 🔍 Universal Search (Sidebar) - **NEW v3.1!**

**Search Modes:**
- **🤖 Auto-Detect** - Automatically selects best mode based on query
- **🧠 Semantic** - ChromaDB embeddings + similarity search (questions, natural language)
- **🔤 Keyword** - Traditional text matching (PostgreSQL ILIKE)
- **🔍 Regex** - Pattern matching (PostgreSQL regex operator `~`)

**How It Works:**
```
Semantic:  "How do I process invoices?"  → ChromaDB embeddings
Keyword:   "contract document"           → PostgreSQL ILIKE
Regex:     "^[A-Z].*invoice"             → PostgreSQL ~ operator
Auto:      Detects mode from query       → Best match
```

**Hybrid Ranking:**
- Results from all 3 backends (PostgreSQL + ChromaDB + Neo4j)
- Weighted relevance scoring:
  - Vector (ChromaDB): 50% weight (highest)
  - Relational (PostgreSQL): 30% weight
  - Graph (Neo4j): 20% weight
- Merged + sorted by final score

**Example Queries:**
- Semantic: "What documents discuss payment workflows?"
- Keyword: "invoice contract"
- Regex: "^DOC-[0-9]{4}$" (matches DOC-1234)
- Auto: Automatically picks best mode

### 1. Graph View (Neo4j) - Top-Left
**Cypher Console** ✅
- Execute Cypher queries directly
- View results in treeview format
- Query history and templates
- Real-time Neo4j connection

**Node Inspector** ✅
- Browse nodes by ID
- View node properties
- Inspect relationships
- Filter by labels

### 2. Vector View (ChromaDB) - Top-Right
**Similarity Search** ✅
- Semantic search queries
- TOP-K result ranking
- Distance metrics (cosine, L2, IP)
- Content preview

**Chunks Browser** ✅
- Hierarchical document/chunk structure
- Metadata inspection
- Embedding visualization

### 3. SAGA View (UDS3) - Bottom-Left 🆕
**Timeline Tab** ✅
- Recent SAGA transactions (10-500 limit)
- Status tracking (completed/compensated/pending/failed)
- Timestamp sorting
- Quick overview

**States Tab** ✅
- Transaction statistics dashboard
- Status distribution (✅🔄⏳❌)
- Failed SAGAs list
- Total transaction count

**Events Tab** ✅
- Step-by-step SAGA execution details
- Backend operation tracking (PostgreSQL → CouchDB → ChromaDB → Neo4j)
- Error messages and timestamps
- **Document-to-SAGA linking** 🔗

**Retry Tab** ✅
- Failed SAGA management
- Error detail viewer
- Retry count tracking
- Admin controls

### 4. Document View (PostgreSQL) - Bottom-Right
**Content Display** ✅
- Load documents by ID
- Full-text search
- Metadata viewer
- **SAGA Finder** 🆕 🔗

**SAGA Integration** 🆕
- "🔗 Find SAGA" button
- Automatic SAGA ID construction (`ingest_{document_id}`)
- Auto-switch to SAGA Events Tab
- Direct step timeline display

## ⌨️ Keyboard Shortcuts

### General
| Shortcut | Action |
|----------|--------|
| `F5` | Refresh All (including SAGA data) |
| `Ctrl+O` | Open Document by ID |
| `Ctrl+F` | Focus Search Bar |
| `Ctrl+E` | Export Current Document |
| `Ctrl+Q` | Exit Application |

### View Navigation
| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+S` | Focus SAGA View |
| `Ctrl+Shift+D` | Focus Document View |
| `Ctrl+Shift+G` | Focus Graph View |
| `Ctrl+Shift+V` | Focus Vector View |

## 🔗 Document-to-SAGA Workflow

### Use Case: Track Document Ingestion

1. **Load Document**
   - Enter Document ID (e.g., `doc_20241024_123456`)
   - Click "📄 Load by ID"

2. **Find Associated SAGA**
   - Click "🔗 Find SAGA" button
   - System constructs SAGA ID: `ingest_doc_20241024_123456`

3. **View Transaction Steps**
   - Auto-switch to SAGA View → Events Tab
   - See all 4 database operations:
     - Step 1: PostgreSQL (metadata insert)
     - Step 2: CouchDB (full content storage)
     - Step 3: ChromaDB (vector embedding)
     - Step 4: Neo4j (knowledge graph)

4. **Analyze Failures**
   - Check step status (✅ completed, ❌ failed)
   - View error messages
   - Track retry attempts

## 🛠️ SAGA Pattern Details

### SAGA ID Construction
```python
# Pattern from ingestion_backend.py
saga_id = f"ingest_{document_id}"

# Example
document_id = "doc_20241024_123456"
saga_id = "ingest_doc_20241024_123456"
```

### Database Tables
```sql
-- Main SAGA state
saga_state (
    saga_id VARCHAR PRIMARY KEY,
    status VARCHAR,  -- completed, compensated, pending, failed
    context JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER
)

-- Individual steps
saga_steps (
    saga_id VARCHAR,
    step_id VARCHAR PRIMARY KEY,
    backend_name VARCHAR,  -- relational, document, vector, graph
    operation VARCHAR,     -- insert, delete
    status VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER,
    step_order INTEGER
)
```

### SAGA Execution Flow
```
1. PostgreSQL (Relational)
   └─ Metadata: document_id, classification, timestamps
   
2. CouchDB (Document)
   └─ Full Content: original text, entities, keywords
   
3. ChromaDB (Vector)
   └─ Embeddings: semantic chunks, similarity search
   
4. Neo4j (Graph)
   └─ Knowledge Graph: entities, relationships

ROLLBACK: If ANY step fails → ALL previous steps are compensated
```

## 📈 Status Indicators

| Icon | Status | Meaning |
|------|--------|---------|
| ✅ | Completed | Step executed successfully |
| 🔄 | Compensated | Step rolled back (SAGA failed) |
| ⏳ | Pending | Step waiting to execute |
| ❌ | Failed | Step execution error |

## 🔍 Troubleshooting

### SAGA Query Errors
**Error:** `[ERROR] SAGA Query failed: Not connected`

**Solutions:**
1. Check PostgreSQL connection (port 5432)
2. Verify `saga_state` table exists
3. Enable SAGA in ingestion backend (`ENABLE_SAGA=true`)
4. Restart backends: `.\scripts\start_services.ps1`

### Neo4j Authentication
**Error:** `Neo.ClientError.Security.Unauthorized`

**Solutions:**
1. Update credentials in `main.py` (Line ~135)
2. Check Neo4j password in `uds3/database/config.py`
3. Verify Neo4j service is running

### ChromaDB Connection
**Error:** `ChromaDB Server nicht verbunden`

**Solutions:**
1. Start ChromaDB server (port 8000)
2. Check `CHROMA_HOST` in environment
3. Verify HTTP endpoint accessible

## 📦 Architecture

```
polyglot_admin/
├── main.py                      # Main application (2,340+ lines)
├── controllers/
│   ├── document_controller.py   # PostgreSQL queries
│   ├── vector_controller.py     # ChromaDB operations
│   ├── graph_controller.py      # Neo4j Cypher execution
│   ├── search_controller.py     # Universal search
│   └── saga_controller.py       # UDS3 SAGA monitoring 🆕
├── utils/
│   └── branding.py              # Covina branding components
└── README.md                    # This file

Integration:
├── UDS3 PolyglotManager         # Database orchestration
├── PostgreSQL Backend           # Relational + SAGA state
├── ChromaDB Backend             # Vector embeddings
├── Neo4j Backend                # Knowledge graph
└── CouchDB Backend              # Document storage (optional)
```

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  Header: Polyglot Admin Tool v2                         │
│  Toolbar: [Search] [Open] [Refresh] [Settings]          │
├────────────────────┬────────────────────────────────────┤
│                    │                                    │
│  Graph (Neo4j)     │  Vector (ChromaDB)                │
│  - Visualizer      │  - Chunks                         │
│  - Cypher ✅       │  - Embeddings                     │
│  - Node Details ✅ │  - Search ✅                      │
│  - Relationships   │  - Metadata ✅                    │
│                    │                                    │
├────────────────────┼────────────────────────────────────┤
│                    │                                    │
│  SAGA (UDS3) 🆕    │  Document (PostgreSQL)            │
│  - Timeline ✅     │  - Content ✅                     │
│  - States ✅       │  - Metadata ✅                    │
│  - Events ✅       │  - SAGA Finder 🆕 🔗             │
│  - Retry ✅        │  - Export                         │
│                    │                                    │
├────────────────────┴────────────────────────────────────┤
│  Status Bar: [Backend Status] [Operations] [Messages]   │
└─────────────────────────────────────────────────────────┘
```

## 📝 Version History

### v2.0.0 (2025-10-24) - SAGA Integration
- ✅ Complete SAGA monitoring system (4 tabs)
- ✅ Document-to-SAGA linking
- ✅ PostgreSQL-based SAGA controller
- ✅ Keyboard shortcuts (Ctrl+Shift+S, F5)
- ✅ View focus helpers
- ✅ Auto-refresh functionality

### v1.0.0 (2025-10-20) - Initial Release
- ✅ UDS3 PolyglotManager integration
- ✅ Real data views (Graph, Vector, Document)
- ✅ Cypher Console
- ✅ Similarity Search
- ✅ Node Inspector

## 🚦 Production Readiness

**Status:** ✅ **PRODUCTION READY**

**Tested:**
- ✅ PostgreSQL queries (document_controller)
- ✅ ChromaDB searches (vector_controller)
- ✅ Neo4j Cypher execution (graph_controller)
- ✅ SAGA state queries (saga_controller)
- ✅ All 4 SAGA tabs (Timeline, States, Events, Retry)
- ✅ Document-to-SAGA linking
- ✅ Keyboard shortcuts
- ✅ No runtime errors

**Known Limitations:**
- ⚠️ SAGA requires `saga_state` table (create via ingestion backend)
- ⚠️ Neo4j auth may need configuration
- ⚠️ ChromaDB requires server running on port 8000

## 📞 Support

**Documentation:** `docs/POLYGLOT_ADMIN_TOOL.md`  
**Issues:** GitHub Issues @ VCC-Covina  
**Contact:** Covina Development Team

---

**Covina System © 2025** | Build with ❤️ for Polyglot Persistence
