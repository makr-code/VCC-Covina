# Polyglot Admin Tool - Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Polyglot Admin Tool v2.0                             │
│                    Universal Database Inspector & Viewer                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ Tkinter GUI
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          UDS3 PolyglotManager                                │
│                         (Database Orchestration)                             │
└─────────────────────────────────────────────────────────────────────────────┘
        │              │              │              │              │
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PostgreSQL   │ │  ChromaDB    │ │    Neo4j     │ │   CouchDB    │ │  SAGA State  │
│  Backend     │ │   Backend    │ │   Backend    │ │   Backend    │ │   (PG)       │
│              │ │              │ │              │ │              │ │              │
│ Port: 5432   │ │ Port: 8000   │ │ Port: 7687   │ │ Port: 32931  │ │ saga_state   │
│ Type: SQL    │ │ Type: HTTP   │ │ Type: Bolt   │ │ Type: HTTP   │ │ saga_steps   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

## Controller Layer

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Controller Layer                                   │
└─────────────────────────────────────────────────────────────────────────────┘
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Document    │ │   Vector     │ │    Graph     │ │   Search     │ │    SAGA      │
│ Controller   │ │ Controller   │ │ Controller   │ │ Controller   │ │ Controller   │
│              │ │              │ │              │ │              │ │              │
│ PostgreSQL   │ │  ChromaDB    │ │    Neo4j     │ │  Multi-DB    │ │ PostgreSQL   │
│ Queries      │ │  Similarity  │ │   Cypher     │ │   Search     │ │ SAGA Queries │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

## UI Layout (4-Frame Grid)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  Header: Polyglot Admin Tool v2 - Universal Document Inspector               │
│  Toolbar: [🔍 Search] [📄 Open] [🔄 Refresh] [⚙️ Settings] [ℹ️ Help]       │
├──────────────────────────────────────┬────────────────────────────────────────┤
│                                      │                                        │
│  ┌────────────────────────────────┐  │  ┌──────────────────────────────────┐ │
│  │   Graph View (Neo4j)           │  │  │   Vector View (ChromaDB)         │ │
│  │   ─────────────────────────    │  │  │   ──────────────────────────     │ │
│  │   📊 Tabs:                     │  │  │   📊 Tabs:                       │ │
│  │   • Visualizer                 │  │  │   • Chunks                       │ │
│  │   • Cypher Console    ✅       │  │  │   • Embeddings                   │ │
│  │   • Node Inspector    ✅       │  │  │   • Similarity Search   ✅       │ │
│  │   • Relationships              │  │  │   • Metadata            ✅       │ │
│  │                                │  │  │                                  │ │
│  │   [Execute Cypher Query]       │  │  │   [Search Similar Chunks]        │ │
│  │   [Load Node by ID]            │  │  │   [Browse Collection]            │ │
│  └────────────────────────────────┘  │  └──────────────────────────────────┘ │
│                                      │                                        │
├──────────────────────────────────────┼────────────────────────────────────────┤
│                                      │                                        │
│  ┌────────────────────────────────┐  │  ┌──────────────────────────────────┐ │
│  │   SAGA View (UDS3) 🆕          │  │  │   Document View (PostgreSQL)     │ │
│  │   ─────────────────────────    │  │  │   ───────────────────────────    │ │
│  │   ⚙️ Tabs:                     │  │  │   📄 Tabs:                       │ │
│  │   • Timeline          ✅       │  │  │   • Content Display     ✅       │ │
│  │   • States (Stats)    ✅       │  │  │   • Metadata            ✅       │ │
│  │   • Events (Steps)    ✅       │  │  │   • SAGA Finder 🔗      ✅       │ │
│  │   • Retry (Failed)    ✅       │  │  │   • Processing History           │ │
│  │                                │  │  │   • Export Options               │ │
│  │   Recent SAGAs: 147            │  │  │                                  │ │
│  │   ✅ 140  🔄 5  ⏳ 1  ❌ 1     │  │  │   [Load Document]                │ │
│  │                                │  │  │   [🔗 Find SAGA] 🆕              │ │
│  └────────────────────────────────┘  │  └──────────────────────────────────┘ │
│                                      │                                        │
├──────────────────────────────────────┴────────────────────────────────────────┤
│  Status Bar: ✅ PostgreSQL | ✅ ChromaDB | ⚠️ Neo4j | 📊 SAGA: 147 total    │
└───────────────────────────────────────────────────────────────────────────────┘
```

## SAGA Transaction Flow

```
Document Ingestion with SAGA Pattern
═════════════════════════════════════

User Upload
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Ingestion Backend (Port 45679)                                 │
│  ───────────────────────────────────                            │
│                                                                  │
│  SAGA Orchestrator Start                                        │
│  saga_id = f"ingest_{document_id}"                              │
│                                                                  │
│  Step 1: PostgreSQL (Relational)                                │
│  ├─ Operation: INSERT                                           │
│  ├─ Payload: document_id, classification, metadata              │
│  └─ Status: ✅ completed                                        │
│                                                                  │
│  Step 2: CouchDB (Document)                                     │
│  ├─ Operation: INSERT                                           │
│  ├─ Payload: full_content, entities, keywords                   │
│  └─ Status: ✅ completed                                        │
│                                                                  │
│  Step 3: ChromaDB (Vector)                                      │
│  ├─ Operation: INSERT                                           │
│  ├─ Payload: embeddings, chunks, metadata                       │
│  └─ Status: ✅ completed                                        │
│                                                                  │
│  Step 4: Neo4j (Graph)                                          │
│  ├─ Operation: INSERT                                           │
│  ├─ Payload: entities, relationships                            │
│  └─ Status: ✅ completed                                        │
│                                                                  │
│  SAGA Result: SUCCESS (all steps completed)                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
     │
     │ PostgreSQL Write (saga_state table)
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  SAGA State Persistence                                         │
│  ─────────────────────                                          │
│                                                                  │
│  Table: saga_state                                              │
│  ├─ saga_id: "ingest_doc_20241024_123456"                       │
│  ├─ status: "completed"                                         │
│  ├─ created_at: "2025-10-24 10:15:32"                           │
│  ├─ completed_at: "2025-10-24 10:15:34"                         │
│  └─ error_message: NULL                                         │
│                                                                  │
│  Table: saga_steps (4 rows)                                     │
│  ├─ step_order: 1, backend: relational, status: completed       │
│  ├─ step_order: 2, backend: document, status: completed         │
│  ├─ step_order: 3, backend: vector, status: completed           │
│  └─ step_order: 4, backend: graph, status: completed            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
     │
     │ Query via SAGA Controller
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Polyglot Admin Tool - SAGA View                                │
│  ───────────────────────────────────                            │
│                                                                  │
│  Timeline Tab: Shows recent SAGA "ingest_doc_20241024_123456"  │
│  States Tab: Statistics (1 completed)                           │
│  Events Tab: 4 steps displayed with status icons               │
│  Retry Tab: N/A (no failures)                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Document-to-SAGA Linking Flow

```
User Workflow: Find SAGA for Document
══════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Load Document                                          │
│  ───────────────────                                            │
│                                                                  │
│  Document View → Content Tab                                    │
│  User enters: "doc_20241024_123456"                             │
│  Clicks: "📄 Load by ID"                                        │
│                                                                  │
│  Result: Document loaded with metadata                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Find SAGA                                              │
│  ──────────────────                                             │
│                                                                  │
│  User clicks: "🔗 Find SAGA"                                    │
│                                                                  │
│  System constructs:                                             │
│  saga_id = f"ingest_{doc_id}"                                   │
│  saga_id = "ingest_doc_20241024_123456"                         │
│                                                                  │
│  Query PostgreSQL:                                              │
│  SELECT * FROM saga_state WHERE saga_id = %s                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Auto-Switch View                                       │
│  ─────────────────────                                          │
│                                                                  │
│  If SAGA found:                                                 │
│  ├─ Switch to: SAGA View                                        │
│  ├─ Select tab: Events (Tab 3)                                  │
│  └─ Auto-populate saga_id_entry                                 │
│                                                                  │
│  If SAGA not found:                                             │
│  └─ Display: "⚠️ No SAGA found for document"                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Load Steps                                             │
│  ───────────────────                                            │
│                                                                  │
│  Query PostgreSQL:                                              │
│  SELECT * FROM saga_steps                                       │
│  WHERE saga_id = 'ingest_doc_20241024_123456'                   │
│  ORDER BY step_order                                            │
│                                                                  │
│  Display in Treeview:                                           │
│  ├─ Step 1: PostgreSQL → insert → ✅ completed                 │
│  ├─ Step 2: CouchDB → insert → ✅ completed                    │
│  ├─ Step 3: ChromaDB → insert → ✅ completed                   │
│  └─ Step 4: Neo4j → insert → ✅ completed                      │
│                                                                  │
│  SAGA Info Panel:                                               │
│  ├─ SAGA ID: ingest_doc_20241024_123456                         │
│  ├─ Status: completed                                           │
│  ├─ Created: 2025-10-24 10:15:32                                │
│  └─ Completed: 2025-10-24 10:15:34                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

```
                          ┌──────────────────┐
                          │  User Interface  │
                          │    (Tkinter)     │
                          └────────┬─────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
         ┌──────────▼────────┐       ┌───────────▼──────────┐
         │   UI Components   │       │   Event Handlers    │
         │  - Frames         │       │  - Button Clicks    │
         │  - Notebooks      │       │  - Keyboard Events  │
         │  - Treeviews      │       │  - Auto-Refresh     │
         └──────────┬────────┘       └───────────┬──────────┘
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   Controller Layer          │
                    │  - DocumentController       │
                    │  - VectorController         │
                    │  - GraphController          │
                    │  - SAGAController 🆕        │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  UDS3 PolyglotManager       │
                    │  - Backend Orchestration    │
                    │  - Connection Management    │
                    └──────────────┬──────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
    ┌───────▼────────┐    ┌───────▼────────┐    ┌───────▼────────┐
    │  PostgreSQL    │    │   ChromaDB     │    │     Neo4j      │
    │   Backend      │    │    Backend     │    │    Backend     │
    │                │    │                │    │                │
    │  - Documents   │    │  - Vectors     │    │  - Graph       │
    │  - SAGA State  │    │  - Embeddings  │    │  - Entities    │
    └────────────────┘    └────────────────┘    └────────────────┘
```

---

**Polyglot Admin Tool v2.0** | Architecture Diagram  
**Last Updated:** 2025-10-24  
**Status:** ✅ Production Ready
