# Polyglot Admin Tool - Development Guide

**Version:** 2.0.0  
**Last Updated:** 2025-10-24  
**Status:** Production Ready

---

## 🎯 Architecture Overview

### Component Structure

```
PolyglotAdminApp
├── UDS3 PolyglotManager (Database Orchestration)
├── Controllers (Backend Access Layer)
│   ├── DocumentController → PostgreSQL
│   ├── VectorController → ChromaDB
│   ├── GraphController → Neo4j
│   ├── SearchController → Multi-DB Search
│   └── SAGAController → PostgreSQL (saga_state/saga_steps)
├── Views (4 Main Frames)
│   ├── Graph Frame (Top-Left)
│   ├── Vector Frame (Top-Right)
│   ├── SAGA Frame (Bottom-Left) 🆕
│   └── Document Frame (Bottom-Right)
└── UI Components
    ├── Menubar (File, Edit, View, Tools, Help)
    ├── Toolbar (Quick Actions)
    ├── Header (Covina Branding)
    └── Status Bar (Connection Status)
```

### Key Design Patterns

**1. MVC Architecture**
- **Model:** UDS3 Backends (PostgreSQL, ChromaDB, Neo4j)
- **View:** Tkinter UI Components (Frames, Notebooks, Treeviews)
- **Controller:** Controller classes (document_controller.py, saga_controller.py, etc.)

**2. Tab-Based Navigation**
- Each main frame has a Notebook widget
- Multiple tabs per frame (4+ tabs per view)
- Independent data loading per tab

**3. Backend Abstraction**
- Controllers receive UDS3 PolyglotManager instance
- Access backends via `getattr(uds3_manager, 'backend_name')`
- No direct HTTP calls (except ChromaDB remote)

---

## 🔧 Adding a New Controller

### Step 1: Create Controller Class

```python
# polyglot_admin/controllers/new_controller.py

class NewController:
    """Controller for New Backend."""
    
    def __init__(self, uds3_manager):
        """Initialize with UDS3 manager."""
        self.uds3 = uds3_manager
        self.backend = getattr(uds3_manager, 'new_backend', None)
        
        if self.backend:
            print(f"[OK] NewController: Backend from UDS3")
        else:
            print(f"[WARNING] NewController: No Backend")
    
    def is_connected(self) -> bool:
        """Check backend connection."""
        if not self.backend:
            return False
        return hasattr(self.backend, 'conn') and self.backend.conn is not None
    
    def get_data(self, query_params):
        """Fetch data from backend."""
        if not self.is_connected():
            return []
        
        try:
            # Access backend methods
            results = self.backend.query(query_params)
            return results
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            return []
```

### Step 2: Integrate in Main App

```python
# polyglot_admin/main.py

from polyglot_admin.controllers.new_controller import NewController

class PolyglotAdminApp:
    def __init__(self):
        # ... existing code ...
        
        # Initialize New Controller
        self.new_controller = NewController(self.uds3)
```

### Step 3: Create UI Tab

```python
def _init_new_tab(self, parent):
    """Initialize New Tab."""
    # Input frame
    input_frame = ttk.LabelFrame(parent, text="Query Input", padding=5)
    input_frame.pack(fill=tk.X, padx=5, pady=5)
    
    # Query entry
    query_var = tk.StringVar()
    query_entry = ttk.Entry(input_frame, textvariable=query_var, width=50)
    query_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    # Load button
    def load_data():
        query = query_var.get().strip()
        if not query:
            return
        
        try:
            results = self.new_controller.get_data(query)
            # Display results in treeview
            for result in results:
                tree.insert("", tk.END, values=(result['id'], result['name']))
        except Exception as e:
            print(f"[ERROR] Load failed: {e}")
    
    ttk.Button(input_frame, text="🔍 Load", command=load_data).pack(side=tk.LEFT, padx=5)
    
    # Results treeview
    tree_frame = ttk.Frame(parent)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    columns = ("id", "name")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
    tree.heading("id", text="ID")
    tree.heading("name", text="Name")
    tree.pack(fill=tk.BOTH, expand=True)
```

---

## 📊 Adding a New SAGA Tab

### Example: Adding "Metrics" Tab

```python
def _init_metrics_tab(self, parent):
    """Initialize SAGA Metrics Tab."""
    # Main container
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Title
    title = ttk.Label(
        main_frame,
        text="📊 SAGA Performance Metrics",
        font=CovinarBranding.FONT_TITLE,
        foreground=CovinarBranding.COLOR_ACCENT
    )
    title.pack(pady=(0, 10))
    
    # Metrics display
    metrics_frame = ttk.LabelFrame(main_frame, text="Metrics", padding=10)
    metrics_frame.pack(fill=tk.BOTH, expand=True)
    
    def load_metrics():
        """Load SAGA metrics from PostgreSQL."""
        try:
            # Query average execution time
            query = """
            SELECT 
                AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration,
                COUNT(*) as total_count
            FROM saga_state
            WHERE status = 'completed'
            """
            results = self.saga_controller._execute_query(query, ())
            
            if results:
                row = results[0]
                avg_duration = row.get('avg_duration', 0)
                total_count = row.get('total_count', 0)
                
                # Display metrics
                ttk.Label(
                    metrics_frame,
                    text=f"Average Duration: {avg_duration:.2f}s",
                    font=CovinarBranding.FONT_NORMAL
                ).pack(pady=5)
                
                ttk.Label(
                    metrics_frame,
                    text=f"Total Completed: {total_count}",
                    font=CovinarBranding.FONT_NORMAL
                ).pack(pady=5)
        
        except Exception as e:
            print(f"[ERROR] Load metrics failed: {e}")
    
    # Load button
    ttk.Button(main_frame, text="🔄 Refresh", command=load_metrics).pack(pady=10)
    
    # Auto-load on startup
    self.root.after(500, load_metrics)
```

### Register Tab in SAGA Notebook

```python
# In _create_saga_frame() method
metrics_tab = ttk.Frame(notebook)
notebook.add(metrics_tab, text="Metrics")
self._init_metrics_tab(metrics_tab)
```

---

## 🎨 Branding Guidelines

### Using Covina Colors

```python
from polyglot_admin.utils.branding import CovinarBranding

# Primary colors
CovinarBranding.COLOR_PRIMARY    # Covina Blue: #0078D7
CovinarBranding.COLOR_ACCENT     # Dark Blue: #005A9E
CovinarBranding.COLOR_SUCCESS    # Green: #107C10
CovinarBranding.COLOR_WARNING    # Orange: #FF8C00
CovinarBranding.COLOR_ERROR      # Red: #E81123

# Text colors
CovinarBranding.COLOR_TEXT       # Dark Gray: #333333
CovinarBranding.COLOR_TEXT_LIGHT # Medium Gray: #666666

# Fonts
CovinarBranding.FONT_TITLE       # ("Segoe UI", 16, "bold")
CovinarBranding.FONT_NORMAL      # ("Segoe UI", 10)
CovinarBranding.FONT_SMALL       # ("Segoe UI", 9)
```

### Creating Status Indicators

```python
# Success indicator
ttk.Label(frame, text="✅ Connected", foreground=CovinarBranding.COLOR_SUCCESS)

# Error indicator
ttk.Label(frame, text="❌ Failed", foreground=CovinarBranding.COLOR_ERROR)

# Warning indicator
ttk.Label(frame, text="⚠️ Warning", foreground=CovinarBranding.COLOR_WARNING)
```

---

## 🔌 Backend Integration Patterns

### PostgreSQL Direct Query

```python
def query_postgresql(self, sql_query, params):
    """Execute raw SQL on PostgreSQL."""
    try:
        # Ensure connection
        if not self.backend.conn or self.backend.conn.closed:
            self.backend.connect()
        
        # Execute query
        self.backend.cursor.execute(sql_query, params)
        
        # Fetch results
        results = self.backend.cursor.fetchall()
        
        # Convert RealDictRow to regular dicts
        return [dict(row) for row in results]
    
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        return []
```

### ChromaDB HTTP Query

```python
def query_chromadb(self, collection_name, query_texts, n_results=10):
    """Query ChromaDB via HTTP."""
    try:
        results = self.backend.query(
            collection_name=collection_name,
            query_texts=query_texts,
            n_results=n_results
        )
        return results
    except Exception as e:
        print(f"[ERROR] ChromaDB query failed: {e}")
        return None
```

### Neo4j Cypher Query

```python
def query_neo4j(self, cypher_query, params=None):
    """Execute Cypher on Neo4j."""
    try:
        with self.backend.driver.session() as session:
            result = session.run(cypher_query, params or {})
            records = [dict(record) for record in result]
            return records
    except Exception as e:
        print(f"[ERROR] Cypher query failed: {e}")
        return []
```

---

## ⚙️ Configuration Management

### Environment Variables

```python
# .env.production
POSTGRES_HOST=192.168.178.94
POSTGRES_PORT=5432
CHROMA_HOST=192.168.178.94
CHROMA_PORT=8000
NEO4J_URI=bolt://192.168.178.94:7687
ENABLE_SAGA=true
```

### Loading Configuration

```python
import os
from dotenv import load_dotenv

load_dotenv('.env.production')

config = {
    'postgres_host': os.getenv('POSTGRES_HOST'),
    'chroma_host': os.getenv('CHROMA_HOST'),
    'enable_saga': os.getenv('ENABLE_SAGA', 'false').lower() == 'true'
}
```

---

## 🧪 Testing Guidelines

### Unit Test Example

```python
# tests/test_saga_controller.py

import unittest
from polyglot_admin.controllers.saga_controller import SAGAController

class TestSAGAController(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock UDS3 manager
        self.mock_uds3 = MockUDS3Manager()
        self.controller = SAGAController(self.mock_uds3)
    
    def test_get_saga_status(self):
        """Test get_saga_status method."""
        saga_id = "ingest_doc_test123"
        
        result = self.controller.get_saga_status(saga_id)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['saga_id'], saga_id)
        self.assertIn('status', result)
    
    def test_list_recent_sagas(self):
        """Test list_recent_sagas method."""
        limit = 10
        
        results = self.controller.list_recent_sagas(limit=limit)
        
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), limit)
```

### Integration Test Example

```python
# tests/integration/test_saga_integration.py

import unittest
from polyglot_admin.main import PolyglotAdminApp

class TestSAGAIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test app."""
        cls.app = PolyglotAdminApp()
    
    def test_saga_controller_initialized(self):
        """Test SAGA controller is initialized."""
        self.assertIsNotNone(self.app.saga_controller)
        self.assertTrue(self.app.saga_controller.is_connected())
    
    def test_saga_tabs_exist(self):
        """Test all SAGA tabs are created."""
        notebook = self.app.saga_notebook
        tab_count = len(notebook.tabs())
        
        self.assertEqual(tab_count, 4)  # Timeline, States, Events, Retry
```

---

## 📝 Code Style Guidelines

### Naming Conventions

```python
# Classes: PascalCase
class SAGAController:
    pass

# Methods: snake_case with leading underscore for private
def _execute_query(self, sql, params):
    pass

def get_saga_status(self, saga_id):
    pass

# Constants: UPPERCASE
COLOR_PRIMARY = "#0078D7"
FONT_TITLE = ("Segoe UI", 16, "bold")

# Variables: snake_case
saga_id = "ingest_doc_123"
query_results = []
```

### Documentation Standards

```python
def get_saga_status(self, saga_id: str) -> Optional[Dict[str, Any]]:
    """
    Get SAGA status by ID from PostgreSQL.
    
    Args:
        saga_id: SAGA instance ID (format: ingest_{document_id})
    
    Returns:
        SAGA status dict with keys:
            - saga_id: str
            - status: str (completed/compensated/pending/failed)
            - created_at: timestamp
            - error_message: str (optional)
        
        Returns None if SAGA not found.
    
    Example:
        >>> status = controller.get_saga_status("ingest_doc_123")
        >>> print(status['status'])
        'completed'
    """
    # Implementation...
```

---

## 🚀 Deployment Checklist

### Pre-Deployment

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] No console errors on startup
- [ ] All 4 SAGA tabs load without errors
- [ ] Document-to-SAGA linking works
- [ ] Keyboard shortcuts functional
- [ ] Backend connections verified

### Production Environment

- [ ] PostgreSQL running (port 5432)
- [ ] ChromaDB running (port 8000)
- [ ] Neo4j running (port 7687)
- [ ] SAGA tables exist (`saga_state`, `saga_steps`)
- [ ] UDS3 credentials configured
- [ ] Environment variables set (`.env.production`)

### Post-Deployment

- [ ] Monitor console for errors
- [ ] Verify SAGA queries return data
- [ ] Test Document-to-SAGA workflow
- [ ] Check connection status in UI
- [ ] Validate F5 refresh works

---

## 🐛 Common Issues & Solutions

### Issue: SAGA Query Errors

**Symptom:** `[ERROR] SAGA Query failed: Not connected`

**Solutions:**
1. Check PostgreSQL connection pool
2. Verify `saga_state` table exists
3. Enable SAGA in backend (`ENABLE_SAGA=true`)
4. Restart PostgreSQL backend

### Issue: Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'polyglot_admin'`

**Solutions:**
1. Add parent directory to PYTHONPATH
2. Install package in development mode: `pip install -e .`
3. Check directory structure

### Issue: Tkinter Errors

**Symptom:** `_tkinter.TclError: invalid command name`

**Solutions:**
1. Check widget lifecycle (not destroyed prematurely)
2. Verify `self.root.after()` timing
3. Use try-except for widget access

---

## 📚 Resources

**Documentation:**
- `polyglot_admin/README.md` - User guide
- `docs/SAGA_ARCHITECTURE.md` - SAGA pattern details
- `docs/UDS3_INTEGRATION.md` - UDS3 PolyglotManager guide

**Code References:**
- `main.py` - Main application (2,340+ lines)
- `controllers/saga_controller.py` - SAGA implementation (355 lines)
- `utils/branding.py` - Covina branding components

**External:**
- UDS3 Package: `uds3/` directory
- Tkinter Docs: https://docs.python.org/3/library/tkinter.html
- Neo4j Python Driver: https://neo4j.com/docs/api/python-driver/

---

**Last Updated:** 2025-10-24  
**Maintainer:** Covina Development Team  
**Status:** ✅ Production Ready
