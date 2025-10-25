# Polyglot Admin Tool - Changelog

All notable changes to the Polyglot Admin Tool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.1.0] - 2025-10-24

### 🚀 Major Feature: Hybrid Search with Semantic, Keyword, and Regex

**Status:** ✅ Production Ready

### Added

#### Hybrid Search System
- **Search Mode Selector** in sidebar
  - 🤖 Auto-Detect: Automatically selects best mode from query pattern
  - 🧠 Semantic: ChromaDB embeddings + similarity search
  - 🔤 Keyword: Traditional text matching (PostgreSQL ILIKE)
  - 🔍 Regex: Pattern matching (PostgreSQL regex operator)

- **SearchController Enhancements** (`search_controller.py`)
  - `detect_search_mode()`: Auto-detect search intent from query
  - `hybrid_search()`: Unified search across all backends
  - `_search_semantic()`: True semantic search via embeddings
  - `_search_relational_fuzzy()`: PostgreSQL full-text search (ts_rank)
  - `_search_relational_regex()`: Regex pattern matching
  - `merge_and_rank_results()`: Weighted relevance scoring

- **Weighted Ranking System**
  - Vector (ChromaDB): 50% weight (highest priority)
  - Relational (PostgreSQL): 30% weight
  - Graph (Neo4j): 20% weight
  - Final score = Σ(relevance × weight)

- **UI Improvements**
  - Search mode radio buttons in sidebar
  - Results tree shows relevance scores
  - Status bar displays backend distribution (PG: X, ChromaDB: Y, Neo4j: Z)
  - Top 30 results sorted by final score

- **Test Suite**
  - `tests/test_hybrid_search.py`: 5 comprehensive tests
  - Auto-detect mode validation
  - Keyword, semantic, regex search tests
  - Hybrid ranking validation
  - Performance benchmarks

### Technical Details

**Auto-Detect Logic:**
```python
Regex indicators: ^, $, [.*], (.*), *, +, ?, .
Semantic indicators: 3+ words, question words (what, how, why)
Default: keyword mode
```

**Semantic Search:**
- Uses sentence-transformers embeddings
- ChromaDB similarity search (cosine distance)
- Relevance = 1 - distance (0-1 scale)

**Regex Search:**
- PostgreSQL `~` operator (POSIX regex)
- Pattern validation before execution
- High relevance score (0.7)

**Hybrid Workflow:**
```
User Query → Mode Detection → Multi-Backend Search
  → PostgreSQL (keyword/fuzzy/regex)
  → ChromaDB (semantic similarity)
  → Neo4j (graph pattern)
  → Merge Results → Weight by Backend → Sort by Score
```

### Breaking Changes
- `SearchController.universal_search()` replaced by `hybrid_search()`
- Results structure changed: added `relevance`, `final_score`, `mode` fields
- Results tree columns: "Type" → "Source", added "Relevance" column

---

## [2.0.0] - 2025-10-24

### 🎉 Major Release: SAGA Integration Complete

**Status:** ✅ Production Ready

### Added

#### SAGA View (Bottom-Left Frame)
- **Timeline Tab** - Recent SAGA transactions list
  - Configurable limit (10-500)
  - Status icons (✅🔄⏳❌)
  - Auto-refresh on tab load
  - Sort by creation date (DESC)

- **States Tab** - Statistics dashboard
  - Transaction count by status
  - Failed SAGAs list with error details
  - Color-coded indicators
  - Real-time PostgreSQL queries

- **Events Tab** - Step-by-step transaction details
  - SAGA ID input with load button
  - Step timeline with status tracking
  - Backend operation display (PostgreSQL → CouchDB → ChromaDB → Neo4j)
  - Error messages and timestamps
  - SAGA information panel

- **Retry Tab** - Failed transaction management
  - Failed SAGAs list with filters
  - Error detail viewer
  - Retry count tracking
  - Click-to-view-details functionality

#### SAGA Controller
- PostgreSQL-based SAGA state queries
- Custom `_execute_query()` wrapper for cursor access
- 7 query methods:
  - `get_saga_status(saga_id)`
  - `list_recent_sagas(limit)`
  - `get_saga_steps(saga_id)`
  - `get_statistics()`
  - `get_failed_sagas(limit)`
  - `get_health()`
  - `is_connected()`

#### Document-to-SAGA Linking
- "🔗 Find SAGA" button in Document Content Tab
- Automatic SAGA ID construction (`ingest_{document_id}`)
- Auto-switch to SAGA Events Tab
- Auto-load Steps Timeline
- Status feedback for found/not found SAGAs

#### Keyboard Shortcuts
- `F5` - Refresh All (including SAGA data)
- `Ctrl+Shift+S` - Focus SAGA View
- `Ctrl+Shift+D` - Focus Document View
- `Ctrl+Shift+G` - Focus Graph View
- `Ctrl+Shift+V` - Focus Vector View

#### View Focus Helpers
- `_focus_saga_view()` - Lift SAGA frame
- `_focus_document_view()` - Lift Document frame
- `_focus_graph_view()` - Lift Graph frame
- `_focus_vector_view()` - Lift Vector frame
- Status bar feedback on focus

#### Documentation
- `polyglot_admin/README.md` - Complete user guide (300+ lines)
- `docs/POLYGLOT_ADMIN_DEVELOPMENT.md` - Developer guide (500+ lines)
- `docs/POLYGLOT_ADMIN_QUICK_REFERENCE.md` - Cheat sheet
- `docs/POLYGLOT_ADMIN_ARCHITECTURE.md` - Architecture diagrams

### Changed
- Updated Help menu with new shortcuts
- Enhanced status bar with SAGA connection info
- Improved error handling with console output
- Refactored backend access pattern (UDS3 PolyglotManager)

### Fixed
- PostgreSQL cursor access (dict-based row access)
- `COLOR_INFO` → `COLOR_PRIMARY` (branding fix)
- Missing `step_order` in SAGA steps query
- Event loop issues with `self.update_status_label()` → `print()`

### Technical Details
- **Lines of Code:** 2,340+ (main.py)
- **Controllers:** 5 (Document, Vector, Graph, Search, SAGA)
- **SAGA Controller:** 355 lines
- **UI Tabs:** 16 total (4 per view × 4 views)
- **Keyboard Shortcuts:** 9
- **Database Integration:** 4 backends (PostgreSQL, ChromaDB, Neo4j, CouchDB)

---

## [1.0.0] - 2025-10-20

### 🚀 Initial Release

**Status:** ✅ Production Ready (without SAGA)

### Added

#### Core Features
- UDS3 PolyglotManager integration
- 4-frame grid layout (Graph, Vector, Document, Search)
- Real-time database connections
- Covina branding components

#### Graph View (Neo4j)
- Cypher Console with query execution
- Node Inspector with property viewer
- Relationship browser (placeholder)
- Graph visualizer canvas (placeholder)

#### Vector View (ChromaDB)
- Similarity search with TOP-K
- Chunks browser (hierarchical treeview)
- Metadata viewer
- Embedding heatmap (placeholder)

#### Document View (PostgreSQL)
- Content display with load by ID
- Full-text search
- Metadata viewer (structured treeview)
- Processing history (placeholder)
- Export options (placeholder)

#### Search View
- Universal search bar
- Multi-database search controller
- Results treeview
- Filter options

#### UI Components
- Menubar (File, Edit, View, Tools, Help)
- Toolbar with quick actions
- Status bar with backend connection status
- Covina branded header
- Auto-refresh every 30 seconds

#### Controllers
- DocumentController (PostgreSQL)
- VectorController (ChromaDB)
- GraphController (Neo4j)
- SearchController (Multi-DB)

#### Keyboard Shortcuts
- `Ctrl+O` - Open Document
- `Ctrl+F` - Focus Search
- `Ctrl+E` - Export Document
- `F5` - Refresh All
- `Ctrl+Q` - Exit

### Technical Details
- **Lines of Code:** 1,800+ (main.py)
- **Controllers:** 4
- **UI Tabs:** 12 (3 per view × 4 views)
- **Database Integration:** 3 backends (PostgreSQL, ChromaDB, Neo4j)

---

## [Unreleased]

### Planned Features

#### Short Term (Next Release)
- [ ] SAGA Retry functionality (admin override)
- [ ] Export current document (JSON/Markdown/PDF)
- [ ] Graph visualizer canvas implementation
- [ ] Embedding heatmap visualization
- [ ] Processing history tab

#### Medium Term
- [ ] Batch operations (select multiple documents)
- [ ] Advanced filters (date range, classification)
- [ ] Custom Cypher query templates
- [ ] Vector search saved queries
- [ ] User preferences persistence

#### Long Term
- [ ] Plugin system for custom views
- [ ] REST API for remote access
- [ ] Multi-user support with permissions
- [ ] Real-time WebSocket updates
- [ ] Docker deployment

---

## Version Numbering

- **Major (X.0.0):** Breaking changes, major new features
- **Minor (0.X.0):** New features, backward compatible
- **Patch (0.0.X):** Bug fixes, minor improvements

---

## Release Notes

### v2.0.0 Highlights

**SAGA Integration** 🎉
The main feature of v2.0.0 is the complete SAGA (Saga Pattern) integration, providing full visibility into UDS3 transaction orchestration across all 4 databases.

**Key Benefits:**
1. **Transaction Monitoring:** Track every document ingestion step
2. **Failure Analysis:** Identify which database step failed and why
3. **Document Linking:** Jump directly from document to its SAGA transaction
4. **Audit Trail:** Complete history of all SAGA operations

**Production Readiness:**
- ✅ Zero runtime errors in testing
- ✅ All 4 SAGA tabs operational
- ✅ PostgreSQL integration verified
- ✅ Document-to-SAGA workflow tested
- ✅ Keyboard shortcuts functional

**Breaking Changes:**
- None (backward compatible with v1.0.0)

**Migration Notes:**
- Requires `saga_state` and `saga_steps` tables in PostgreSQL
- Requires SAGA enabled in ingestion backend (`ENABLE_SAGA=true`)
- Recommended: Update UDS3 to latest version for full compatibility

---

## Contributors

**Development Team:**
- Covina Development Team

**Special Thanks:**
- UDS3 Package maintainers
- Tkinter community
- PostgreSQL/ChromaDB/Neo4j teams

---

**Last Updated:** 2025-10-24  
**Current Version:** 2.0.0  
**Status:** ✅ Production Ready
