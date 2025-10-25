"""
Polyglot Admin Tool - Main Application v2

Enhanced 4-Quadranten Admin-Tool für Polyglot Persistence Inspection:
- Frame 1: Neo4j Graph Visualizer (Multi-Tab: Canvas, Cypher, Inspector)
- Frame 2: ChromaDB Vector Data (Multi-Tab: Chunks, Embeddings, Search)
- Frame 3: UDS3 SAGA Monitor (Multi-Tab: Timeline, States, Events, Retry)
- Frame 4: PostgreSQL Raw Document (Multi-Tab: Content, Metadata, History, Export)

Features:
- Menubar (File, Edit, View, Tools, Help)
- Toolbar (Quick Actions)
- Search Sidebar (Universal Search + Results Treeview)
- StatusBar (Connection Indicators)

Author: Covina System
Date: 24. Oktober 2025
Version: 2.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polyglot_admin.utils.branding import (
    CovinarBranding,
    CovinaBrandingHeader,
    CovinaStatusBar,
    apply_covina_style
)

from polyglot_admin.controllers import (
    SearchController,
    GraphController,
    VectorController,
    DocumentController,
    SAGAController
)


class PolyglotAdminApp:
    """
    Main Application Class for Polyglot Admin Tool v2.
    
    Features:
    - Menubar + Toolbar
    - Search Sidebar (Universal Search + Results)
    - 4 Frames mit Multi-Tab-Notebooks (Graph, Vector, SAGA, Document)
    - Covina Branding (Header + StatusBar)
    - Backend Connection Management
    """
    
    def __init__(self):
        """Initialize Polyglot Admin Application v2."""
        
        # Create Root Window
        self.root = tk.Tk()
        self.root.title("Polyglot Admin Tool v2")
        self.root.geometry("1600x1000")
        
        # Apply Covina Style
        apply_covina_style(self.root)
        
        # Initialize UDS3 PolyglotManager (like main_backend.py)
        backend_config = {
            "vector": {"enabled": True},      # ChromaDB
            "graph": {"enabled": True},       # Neo4j
            "relational": {"enabled": True},  # PostgreSQL
            "file": {"enabled": True}         # CouchDB
        }
        
        print("🔧 Initialisiere UDS3 PolyglotManager...")
        print("   UDS3 DatabaseManager lädt Credentials aus uds3/database/config.py")
        
        try:
            from uds3 import UDS3PolyglotManager
            
            self.uds3 = UDS3PolyglotManager(
                backend_config=backend_config,
                enable_rag=False  # RAG nicht benötigt im Admin Tool
            )
            
            print("✅ UDS3 PolyglotManager initialisiert")
            
            # Manual Backend Setup (wie main_backend.py Lines 463-580)
            import os
            
            # PostgreSQL Backend
            try:
                from uds3.database.database_api_postgresql_pooled import PostgreSQLRelationalBackend
                
                pg_config = {
                    'host': os.getenv('POSTGRES_HOST', '192.168.178.94'),
                    'port': int(os.getenv('POSTGRES_PORT', '5432')),
                    'user': os.getenv('POSTGRES_USER', 'postgres'),
                    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
                    'database': os.getenv('POSTGRES_DB', 'postgres'),
                    'schema': 'public',
                    'min_connections': 2,
                    'max_connections': 10
                }
                
                postgres_backend = PostgreSQLRelationalBackend(pg_config)
                postgres_backend.connect()
                self.uds3.relational_backend = postgres_backend
                print("✅ PostgreSQL Backend connected")
            
            except Exception as pg_e:
                print(f"⚠️ PostgreSQL Backend failed: {pg_e}")
            
            # ChromaDB Backend
            try:
                from uds3.database.database_api_chromadb_remote import ChromaRemoteVectorBackend
                
                chroma_config = {
                    'host': os.getenv('CHROMA_HOST', '192.168.178.94'),
                    'port': int(os.getenv('CHROMA_PORT', '8000')),
                    'collection_name': 'covina_vectors'
                }
                
                chroma_backend = ChromaRemoteVectorBackend(chroma_config)
                chroma_backend.connect()
                self.uds3.vector_backend = chroma_backend
                print("✅ ChromaDB Backend connected")
            
            except Exception as chroma_e:
                print(f"⚠️ ChromaDB Backend failed: {chroma_e}")
            
            # Neo4j Backend
            try:
                from uds3.database.database_api_neo4j import Neo4jGraphBackend
                
                neo4j_config = {
                    'uri': os.getenv('NEO4J_URI', 'bolt://192.168.178.94:7687'),
                    'user': os.getenv('NEO4J_USER', 'neo4j'),
                    'password': os.getenv('NEO4J_PASSWORD', 'v3f3b1d7')
                }
                
                neo4j_backend = Neo4jGraphBackend(neo4j_config)
                neo4j_backend.connect()
                self.uds3.graph_backend = neo4j_backend
                print("✅ Neo4j Backend connected")
            
            except Exception as neo4j_e:
                print(f"⚠️ Neo4j Backend failed: {neo4j_e}")
            
        except Exception as e:
            print(f"❌ UDS3 Initialisierung fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()
            self.uds3 = None
        
        # Initialize Controllers (pass UDS3 instance)
        self.search_controller = SearchController(self.uds3)
        self.graph_controller = GraphController(self.uds3)
        self.vector_controller = VectorController(self.uds3)
        self.document_controller = DocumentController(self.uds3)
        
        # SAGA Controller nutzt jetzt PostgreSQL (via UDS3)
        self.saga_controller = SAGAController(self.uds3)
        
        # Create UI Components
        self._create_menubar()
        self._create_header()
        self._create_toolbar()
        self._create_main_layout()  # Sidebar + Content Area
        self._create_statusbar()
        
        # Initialize Search Results (empty)
        self.search_results = []
        self.current_document = None
        
        # Set Initial Status
        self.statusbar.set_status("Ready - Backend controllers initialized", "success")
        
        # Update Connection Status (real checks)
        self._update_connection_status()
    
    def _create_menubar(self):
        """Create Application Menubar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Document...", command=self._menu_open_document, accelerator="Ctrl+O")
        file_menu.add_command(label="Export Current...", command=self._menu_export, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", command=self._menu_copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="Find...", command=self._menu_find, accelerator="Ctrl+F")
        edit_menu.add_separator()
        edit_menu.add_command(label="Preferences...", command=self._menu_preferences)
        
        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh All", command=self._refresh_all, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Sidebar", variable=tk.BooleanVar(value=True), command=self._toggle_sidebar)
        view_menu.add_checkbutton(label="Show Toolbar", variable=tk.BooleanVar(value=True))
        
        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Connection Test...", command=self._menu_connection_test)
        tools_menu.add_command(label="Database Statistics...", command=self._menu_db_stats)
        tools_menu.add_separator()
        tools_menu.add_command(label="Cypher Console...", command=self._menu_cypher_console)
        tools_menu.add_command(label="Vector Search...", command=self._menu_vector_search)
        
        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self._menu_help)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._menu_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._menu_about)
        
        # Keyboard Shortcuts
        self.root.bind('<Control-o>', lambda e: self._menu_open_document())
        self.root.bind('<Control-f>', lambda e: self._menu_find())
        self.root.bind('<F5>', lambda e: self._refresh_all())
        self.root.bind('<Control-Shift-S>', lambda e: self._focus_saga_view())
        self.root.bind('<Control-Shift-D>', lambda e: self._focus_document_view())
        self.root.bind('<Control-Shift-G>', lambda e: self._focus_graph_view())
        self.root.bind('<Control-Shift-V>', lambda e: self._focus_vector_view())
    
    def _create_header(self):
        """Create Covina Branded Header."""
        self.header = CovinaBrandingHeader(
            self.root,
            title="Polyglot Admin Tool v2",
            subtitle="Universal Document Inspector & Database Viewer",
            show_tagline=True
        )
        self.header.pack(
            fill=tk.X,
            padx=CovinarBranding.PADDING_LARGE,
            pady=(CovinarBranding.PADDING_MEDIUM, 0)
        )
    
    def _create_toolbar(self):
        """Create Toolbar with Quick Actions."""
        toolbar = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        toolbar.pack(
            fill=tk.X,
            padx=CovinarBranding.PADDING_LARGE,
            pady=(CovinarBranding.PADDING_SMALL, 0)
        )
        
        # Quick Action Buttons
        ttk.Button(
            toolbar,
            text="🔍 Search",
            command=self._focus_search,
            width=12
        ).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Button(
            toolbar,
            text="📄 Open",
            command=self._menu_open_document,
            width=12
        ).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Button(
            toolbar,
            text="🔄 Refresh",
            command=self._refresh_all,
            width=12
        ).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Button(
            toolbar,
            text="💾 Export",
            command=self._menu_export,
            width=12
        ).pack(side=tk.LEFT, padx=2, pady=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=2)
        
        # Navigation
        ttk.Button(
            toolbar,
            text="◀ Back",
            command=self._navigate_back,
            width=10
        ).pack(side=tk.LEFT, padx=2, pady=2)
        
        ttk.Button(
            toolbar,
            text="Forward ▶",
            command=self._navigate_forward,
            width=10
        ).pack(side=tk.LEFT, padx=2, pady=2)
    
    def _create_statusbar(self):
        """Create Status Bar with Backend Connection Status."""
        self.statusbar = CovinaStatusBar(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize backend connection indicators
        self._update_backend_status()
        
        # Auto-refresh every 30 seconds
        self.root.after(30000, self._auto_refresh_status)
    
    def _update_backend_status(self):
        """Update all backend connection status indicators."""
        # PostgreSQL
        pg_connected = self.document_controller.is_connected()
        self.statusbar.set_connection_status("PostgreSQL", pg_connected)
        
        # ChromaDB
        chroma_connected = self.vector_controller.is_connected()
        self.statusbar.set_connection_status("ChromaDB", chroma_connected)
        
        # Neo4j
        neo4j_connected = self.graph_controller.is_connected()
        self.statusbar.set_connection_status("Neo4j", neo4j_connected)
        
        # SAGA (HTTP-based)
        try:
            saga_health = self.saga_controller.get_health()
            saga_connected = saga_health.get('status') == 'healthy'
        except:
            saga_connected = False
        self.statusbar.set_connection_status("SAGA", saga_connected)
    
    def _auto_refresh_status(self):
        """Auto-refresh backend status every 30 seconds."""
        self._update_backend_status()
        self.root.after(30000, self._auto_refresh_status)
    
    def _create_main_layout(self):
        """Create Main Layout: Sidebar (left) + 4-Frame Content Area (right)."""
        # Main Container (PanedWindow for resizable sidebar)
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(
            fill=tk.BOTH,
            expand=True,
            padx=CovinarBranding.PADDING_LARGE,
            pady=CovinarBranding.PADDING_MEDIUM
        )
        
        # Left: Search Sidebar
        self.sidebar = self._create_search_sidebar()
        main_paned.add(self.sidebar, weight=0)
        
        # Right: 4-Frame Content Area
        content_area = self._create_content_area()
        main_paned.add(content_area, weight=1)
    
    def _create_search_sidebar(self):
        """Create Search Sidebar with Universal Search + Results Treeview."""
        sidebar_frame = ttk.LabelFrame(
            self.root,
            text="Search & Results",
            padding=CovinarBranding.PADDING_MEDIUM
        )
        
        # Search Entry
        search_input_frame = ttk.Frame(sidebar_frame)
        search_input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            search_input_frame,
            text="Search:",
            font=CovinarBranding.FONT_NORMAL
        ).pack(anchor=tk.W)
        
        self.search_entry = ttk.Entry(search_input_frame, width=30)
        self.search_entry.pack(fill=tk.X, pady=(5, 0))
        self.search_entry.bind('<Return>', lambda e: self._execute_search())
        
        # Search Mode Selection (NEW!)
        mode_frame = ttk.LabelFrame(search_input_frame, text="Search Mode", padding=5)
        mode_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.search_mode = tk.StringVar(value="auto")
        
        modes = [
            ("auto", "🤖 Auto-Detect"),
            ("semantic", "🧠 Semantic"),
            ("keyword", "🔤 Keyword"),
            ("regex", "🔍 Regex")
        ]
        
        for mode_val, mode_label in modes:
            ttk.Radiobutton(
                mode_frame,
                text=mode_label,
                variable=self.search_mode,
                value=mode_val,
                style='Covina.TRadiobutton'
            ).pack(anchor=tk.W, pady=1)
        
        # Search Button
        ttk.Button(
            search_input_frame,
            text="🔍 Search",
            command=self._execute_search,
            style='CovinaAccent.TButton'
        ).pack(fill=tk.X, pady=(5, 0))
        
        # Filter Options
        filter_frame = ttk.LabelFrame(sidebar_frame, text="Filters", padding=5)
        filter_frame.pack(fill=tk.X, pady=(10, 10))
        
        ttk.Label(filter_frame, text="Type:", font=CovinarBranding.FONT_SMALL).pack(anchor=tk.W)
        self.filter_type = ttk.Combobox(
            filter_frame,
            values=["All", "PDF", "Markdown", "Text", "JSON"],
            state="readonly",
            width=25
        )
        self.filter_type.set("All")
        self.filter_type.pack(fill=tk.X, pady=(2, 5))
        
        ttk.Label(filter_frame, text="Status:", font=CovinarBranding.FONT_SMALL).pack(anchor=tk.W)
        self.filter_status = ttk.Combobox(
            filter_frame,
            values=["All", "Processed", "Pending", "Failed"],
            state="readonly",
            width=25
        )
        self.filter_status.set("All")
        self.filter_status.pack(fill=tk.X, pady=(2, 0))
        
        # Results Treeview
        results_label = ttk.Label(
            sidebar_frame,
            text="Results:",
            font=CovinarBranding.FONT_NORMAL
        )
        results_label.pack(anchor=tk.W, pady=(10, 5))
        
        # Treeview with Scrollbar
        tree_frame = ttk.Frame(sidebar_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_tree = ttk.Treeview(
            tree_frame,
            columns=("Type", "ID"),
            show="tree headings",
            height=20,
            yscrollcommand=scrollbar.set
        )
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.results_tree.yview)
        
        # Configure Columns
        self.results_tree.heading("#0", text="Title")
        self.results_tree.heading("Type", text="Type")
        self.results_tree.heading("ID", text="ID")
        self.results_tree.column("#0", width=200)
        self.results_tree.column("Type", width=80)
        self.results_tree.column("ID", width=100)
        
        # Bind Selection Event
        self.results_tree.bind('<<TreeviewSelect>>', self._on_result_selected)
        
        # Load Button
        ttk.Button(
            sidebar_frame,
            text="� Load Selected",
            command=self._load_selected_document,
            style='Covina.TButton'
        ).pack(fill=tk.X, pady=(10, 0))
        
        return sidebar_frame
    
    def _create_content_area(self):
        """Create 4-Frame Content Area (2x2 Grid) mit jeweils Multi-Tab-Notebooks."""
        # Container Frame (wichtig: separate container für grid!)
        container = ttk.Frame(self.root)
        
        content_frame = ttk.Frame(container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure Grid (2 rows x 2 columns, equal weight)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)
        
        # Top-Left: Graph Frame
        self.graph_frame = self._create_graph_frame(content_frame)
        self.graph_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5), pady=(0, 5))
        
        # Top-Right: Vector Frame
        self.vector_frame = self._create_vector_frame(content_frame)
        self.vector_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=(0, 5))
        
        # Bottom-Left: SAGA Frame
        self.saga_frame = self._create_saga_frame(content_frame)
        self.saga_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5), pady=(5, 0))
        
        # Bottom-Right: Document Frame
        self.document_frame = self._create_document_frame(content_frame)
        self.document_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=(5, 0))
        
        return container
    
    def _create_graph_frame(self, parent):
        """Create Graph Frame mit Multi-Tab Notebook."""
        frame = ttk.LabelFrame(parent, text="🔗 Neo4j Graph", padding=5)
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Graph Visualizer (Canvas)
        graph_canvas_tab = ttk.Frame(notebook)
        notebook.add(graph_canvas_tab, text="Visualizer")
        self._init_graph_canvas_tab(graph_canvas_tab)
        
        # Tab 2: Cypher Console
        cypher_tab = ttk.Frame(notebook)
        notebook.add(cypher_tab, text="Cypher")
        self._init_cypher_tab(cypher_tab)
        
        # Tab 3: Node Inspector
        node_tab = ttk.Frame(notebook)
        notebook.add(node_tab, text="Node Details")
        self._init_node_tab(node_tab)
        
        # Tab 4: Relationships
        rel_tab = ttk.Frame(notebook)
        notebook.add(rel_tab, text="Relationships")
        self._init_rel_tab(rel_tab)
        
        self.graph_notebook = notebook
        return frame
    
    def _create_vector_frame(self, parent):
        """Create Vector Frame mit Multi-Tab Notebook."""
        frame = ttk.LabelFrame(parent, text="📊 ChromaDB Vectors", padding=5)
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Document Chunks (Treeview)
        chunks_tab = ttk.Frame(notebook)
        notebook.add(chunks_tab, text="Chunks")
        self._init_chunks_tab(chunks_tab)
        
        # Tab 2: Embedding Heatmap
        embed_tab = ttk.Frame(notebook)
        notebook.add(embed_tab, text="Embeddings")
        self._init_embed_tab(embed_tab)
        
        # Tab 3: Similarity Search
        search_tab = ttk.Frame(notebook)
        notebook.add(search_tab, text="Search")
        self._init_vector_search_tab(search_tab)
        
        # Tab 4: Metadata
        meta_tab = ttk.Frame(notebook)
        notebook.add(meta_tab, text="Metadata")
        self._init_vector_meta_tab(meta_tab)
        
        self.vector_notebook = notebook
        return frame
    
    def _create_saga_frame(self, parent):
        """Create SAGA Frame mit Multi-Tab Notebook."""
        frame = ttk.LabelFrame(parent, text="⚙️ UDS3 SAGA", padding=5)
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Timeline View
        timeline_tab = ttk.Frame(notebook)
        notebook.add(timeline_tab, text="Timeline")
        self._init_timeline_tab(timeline_tab)
        
        # Tab 2: State Diagram
        state_tab = ttk.Frame(notebook)
        notebook.add(state_tab, text="States")
        self._init_state_tab(state_tab)
        
        # Tab 3: Event Log
        event_tab = ttk.Frame(notebook)
        notebook.add(event_tab, text="Events")
        self._init_event_tab(event_tab)
        
        # Tab 4: Error & Retry
        retry_tab = ttk.Frame(notebook)
        notebook.add(retry_tab, text="Retry")
        self._init_retry_tab(retry_tab)
        
        self.saga_notebook = notebook
        return frame
    
    def _create_document_frame(self, parent):
        """Create Document Frame mit Multi-Tab Notebook."""
        frame = ttk.LabelFrame(parent, text="📄 PostgreSQL Document", padding=5)
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Original Content
        content_tab = ttk.Frame(notebook)
        notebook.add(content_tab, text="Content")
        self._init_content_tab(content_tab)
        
        # Tab 2: Metadata
        meta_tab = ttk.Frame(notebook)
        notebook.add(meta_tab, text="Metadata")
        self._init_doc_meta_tab(meta_tab)
        
        # Tab 3: Processing History
        history_tab = ttk.Frame(notebook)
        notebook.add(history_tab, text="History")
        self._init_history_tab(history_tab)
        
        # Tab 4: Export Options
        export_tab = ttk.Frame(notebook)
        notebook.add(export_tab, text="Export")
        self._init_export_tab(export_tab)
        
        self.document_notebook = notebook
        return frame
    
    # ====================
    # Graph Frame Sub-Tabs
    # ====================
    
    def _init_graph_canvas_tab(self, parent):
        """Initialize Graph Canvas Tab (Visualizer)."""
        label = ttk.Label(
            parent,
            text="Graph Visualizer Canvas\n\n(Node/Edge Rendering, Zoom, Pan)",
            font=CovinarBranding.FONT_NORMAL,
            foreground=CovinarBranding.COLOR_TEXT_LIGHT,
            justify=tk.CENTER
        )
        label.pack(expand=True)
    
    def _init_cypher_tab(self, parent):
        """Initialize Cypher Console Tab - Real Neo4j Execution."""
        # Top Frame: Query Input
        input_frame = ttk.LabelFrame(parent, text="Cypher Query", padding=5)
        input_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # Query Text Widget
        query_text = tk.Text(
            input_frame,
            height=6,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#dcdcdc",
            insertbackground="white"
        )
        query_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Default Query
        query_text.insert("1.0", "MATCH (n) RETURN n LIMIT 10")
        
        # Button Frame
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        def execute_cypher():
            """Execute Cypher Query via GraphController."""
            query = query_text.get("1.0", tk.END).strip()
            if not query:
                return
            
            # Clear results
            results_tree.delete(*results_tree.get_children())
            
            try:
                results = self.graph_controller.execute_cypher(query)
                
                if results:
                    # Configure columns based on first result
                    if results:
                        columns = list(results[0].keys())
                        results_tree["columns"] = columns
                        results_tree["show"] = "tree headings"
                        
                        for col in columns:
                            results_tree.heading(col, text=col)
                            results_tree.column(col, width=150)
                        
                        # Add rows
                        for idx, row in enumerate(results):
                            values = [str(row.get(col, ""))[:100] for col in columns]
                            results_tree.insert("", tk.END, text=str(idx+1), values=values)
                        
                        status_label.config(text=f"✅ {len(results)} rows returned")
                    else:
                        status_label.config(text="✅ Query executed (no results)")
                else:
                    status_label.config(text="⚠️ No results")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        ttk.Button(btn_frame, text="▶ Execute", command=execute_cypher).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Clear", command=lambda: query_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=2)
        
        # Results Frame
        results_frame = ttk.LabelFrame(parent, text="Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results Treeview
        results_tree = ttk.Treeview(results_frame, columns=[], show="tree")
        results_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=results_tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        results_tree.configure(yscrollcommand=scrollbar.set)
        
        # Status Label
        status_label = ttk.Label(parent, text="Ready", foreground="#888")
        status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def _init_node_tab(self, parent):
        """Initialize Node Inspector Tab - Real Neo4j Node Browser."""
        # Top Frame: Node Selector
        selector_frame = ttk.LabelFrame(parent, text="Node Selector", padding=5)
        selector_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Node ID Entry
        id_frame = ttk.Frame(selector_frame)
        id_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(id_frame, text="Node ID:").pack(side=tk.LEFT, padx=5)
        node_id_entry = ttk.Entry(id_frame, width=50)
        node_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def load_node():
            """Load node details from Neo4j."""
            node_id = node_id_entry.get().strip()
            if not node_id:
                return
            
            properties_tree.delete(*properties_tree.get_children())
            
            try:
                node = self.graph_controller.get_node_by_id(node_id)
                
                if node:
                    labels = node.get('labels', [])
                    labels_label.config(text=", ".join(labels) if labels else "No labels")
                    
                    # Display properties
                    for key, value in node.items():
                        if key != 'labels':
                            properties_tree.insert("", tk.END, values=(key, str(value)[:100]))
                    
                    status_label.config(text=f"✅ Node loaded: {node_id[:50]}")
                else:
                    status_label.config(text="⚠️ Node not found")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        def browse_nodes():
            """Browse all nodes (limited)."""
            query = """
            MATCH (n)
            RETURN elementId(n) as id, labels(n) as labels, n as node
            LIMIT 50
            """
            
            properties_tree.delete(*properties_tree.get_children())
            
            try:
                results = self.graph_controller.execute_cypher(query)
                
                if results:
                    for result in results:
                        node_id = result.get('id', 'N/A')
                        labels = result.get('labels', [])
                        node = result.get('node', {})
                        
                        # Show node as row
                        name = node.get('name', node.get('title', node_id[:30]))
                        properties_tree.insert("", tk.END, values=(
                            node_id[:40],
                            ", ".join(labels) if labels else "N/A"
                        ), tags=('node',))
                    
                    labels_label.config(text=f"{len(results)} nodes")
                    status_label.config(text=f"✅ Found {len(results)} nodes")
                else:
                    status_label.config(text="⚠️ No nodes found")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        # Buttons
        btn_frame = ttk.Frame(selector_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🔍 Load Node", command=load_node).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📋 Browse Nodes", command=browse_nodes).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Clear", command=lambda: properties_tree.delete(*properties_tree.get_children())).pack(side=tk.LEFT, padx=2)
        
        # Labels Display
        labels_frame = ttk.Frame(selector_frame)
        labels_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(labels_frame, text="Labels:").pack(side=tk.LEFT, padx=5)
        labels_label = ttk.Label(labels_frame, text="...", foreground=CovinarBranding.COLOR_PRIMARY)
        labels_label.pack(side=tk.LEFT, padx=5)
        
        # Properties Treeview
        props_frame = ttk.LabelFrame(parent, text="Node Properties", padding=5)
        props_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("property", "value")
        properties_tree = ttk.Treeview(props_frame, columns=columns, show="headings", height=20)
        
        properties_tree.heading("property", text="Property")
        properties_tree.heading("value", text="Value")
        
        properties_tree.column("property", width=200)
        properties_tree.column("value", width=500)
        
        properties_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(props_frame, orient=tk.VERTICAL, command=properties_tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        properties_tree.configure(yscrollcommand=scrollbar.set)
        
        # Status Label
        status_label = ttk.Label(parent, text="Enter Node ID or browse nodes", foreground="#888")
        status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def _init_rel_tab(self, parent):
        """Initialize Relationships Tab."""
        label = ttk.Label(
            parent,
            text="Relationships Inspector\n\n(Edges and connections)",
            font=CovinarBranding.FONT_NORMAL,
            foreground=CovinarBranding.COLOR_TEXT_LIGHT,
            justify=tk.CENTER
        )
        label.pack(expand=True)
    
    # =====================
    # Vector Frame Sub-Tabs
    # =====================
    
    def _init_chunks_tab(self, parent):
        """Initialize Chunks Treeview Tab - Real ChromaDB Collection Browser."""
        # Top Frame: Controls
        control_frame = ttk.LabelFrame(parent, text="Collection Browser", padding=5)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Collection Info
        info_frame = ttk.Frame(control_frame)
        info_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(info_frame, text="Collection:").pack(side=tk.LEFT, padx=5)
        collection_label = ttk.Label(info_frame, text="covina_vectors", foreground=CovinarBranding.COLOR_PRIMARY, font=CovinarBranding.FONT_NORMAL)
        collection_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(info_frame, text="Count:").pack(side=tk.LEFT, padx=20)
        count_label = ttk.Label(info_frame, text="...", foreground=CovinarBranding.COLOR_ACCENT)
        count_label.pack(side=tk.LEFT, padx=5)
        
        def load_chunks():
            """Load all chunks from ChromaDB."""
            chunks_tree.delete(*chunks_tree.get_children())
            
            try:
                # Get all vectors (limit to prevent UI freeze)
                results = self.vector_controller.query_similar("", n_results=100)
                
                count_label.config(text=str(len(results)))
                
                # Group by document_id
                docs = {}
                for result in results:
                    metadata = result.get('metadata', {})
                    doc_id = metadata.get('document_id', 'unknown')
                    
                    if doc_id not in docs:
                        docs[doc_id] = []
                    docs[doc_id].append(result)
                
                # Insert into tree
                for doc_id, chunks in docs.items():
                    # Parent node: Document
                    parent_id = chunks_tree.insert("", tk.END, text=f"📄 {doc_id}", values=(
                        len(chunks),
                        "",
                        ""
                    ))
                    
                    # Child nodes: Chunks
                    for idx, chunk in enumerate(chunks):
                        chunk_id = chunk.get('id', 'N/A')
                        content = chunk.get('content', '')[:80]
                        distance = chunk.get('distance', 0)
                        
                        chunks_tree.insert(parent_id, tk.END, text=f"  Chunk {idx+1}", values=(
                            chunk_id[:40],
                            f"{distance:.4f}" if distance else "N/A",
                            content
                        ))
                
                status_label.config(text=f"✅ Loaded {len(results)} chunks from {len(docs)} documents")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        # Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🔄 Load Chunks", command=load_chunks).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Clear", command=lambda: chunks_tree.delete(*chunks_tree.get_children())).pack(side=tk.LEFT, padx=2)
        
        # Chunks Treeview
        tree_frame = ttk.LabelFrame(parent, text="Chunk Hierarchy", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("chunk_id", "distance", "content")
        chunks_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=20)
        
        chunks_tree.heading("#0", text="Document / Chunk")
        chunks_tree.heading("chunk_id", text="Chunk ID")
        chunks_tree.heading("distance", text="Distance")
        chunks_tree.heading("content", text="Content Preview")
        
        chunks_tree.column("#0", width=200)
        chunks_tree.column("chunk_id", width=180)
        chunks_tree.column("distance", width=80)
        chunks_tree.column("content", width=400)
        
        chunks_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=chunks_tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        chunks_tree.configure(yscrollcommand=scrollbar.set)
        
        # Status Label
        status_label = ttk.Label(parent, text="Click 'Load Chunks' to browse collection", foreground="#888")
        status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def _init_embed_tab(self, parent):
        """Initialize Embeddings Heatmap Tab."""
        label = ttk.Label(
            parent,
            text="Embedding Heatmap\n\n(First 20 dimensions visualization)",
            font=CovinarBranding.FONT_NORMAL,
            foreground=CovinarBranding.COLOR_TEXT_LIGHT,
            justify=tk.CENTER
        )
        label.pack(expand=True)
    
    def _init_vector_search_tab(self, parent):
        """Initialize Vector Search Tab - Real ChromaDB Similarity Search."""
        # Top Frame: Search Input
        input_frame = ttk.LabelFrame(parent, text="Semantic Search Query", padding=5)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Query Entry
        query_frame = ttk.Frame(input_frame)
        query_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(query_frame, text="Query:").pack(side=tk.LEFT, padx=5)
        query_entry = ttk.Entry(query_frame, width=50)
        query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        query_entry.insert(0, "Machine Learning")
        
        # TOP-K Limit
        ttk.Label(query_frame, text="Top-K:").pack(side=tk.LEFT, padx=5)
        topk_var = tk.StringVar(value="10")
        topk_spin = ttk.Spinbox(query_frame, from_=1, to=100, textvariable=topk_var, width=5)
        topk_spin.pack(side=tk.LEFT, padx=5)
        
        def execute_search():
            """Execute semantic similarity search."""
            query_text = query_entry.get().strip()
            if not query_text:
                return
            
            try:
                n_results = int(topk_var.get())
            except:
                n_results = 10
            
            # Clear results
            results_tree.delete(*results_tree.get_children())
            
            try:
                results = self.vector_controller.query_similar(query_text, n_results=n_results)
                
                if results:
                    for idx, result in enumerate(results):
                        chunk_id = result.get('id', 'N/A')
                        distance = result.get('distance', 0)
                        similarity = result.get('similarity', 0)
                        content = result.get('content', '')[:100]  # Preview
                        metadata = result.get('metadata', {})
                        doc_id = metadata.get('document_id', 'N/A')
                        
                        results_tree.insert("", tk.END, values=(
                            idx + 1,
                            f"{similarity:.4f}" if similarity else "N/A",
                            f"{distance:.4f}" if distance else "N/A",
                            chunk_id[:30],
                            doc_id[:20],
                            content
                        ))
                    
                    status_label.config(text=f"✅ Found {len(results)} similar chunks")
                else:
                    status_label.config(text="⚠️ No results found")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🔍 Search", command=execute_search).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Clear", command=lambda: results_tree.delete(*results_tree.get_children())).pack(side=tk.LEFT, padx=2)
        
        # Results Frame
        results_frame = ttk.LabelFrame(parent, text="Search Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results Treeview
        columns = ("rank", "similarity", "distance", "chunk_id", "doc_id", "content")
        results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        results_tree.heading("rank", text="#")
        results_tree.heading("similarity", text="Similarity")
        results_tree.heading("distance", text="Distance")
        results_tree.heading("chunk_id", text="Chunk ID")
        results_tree.heading("doc_id", text="Doc ID")
        results_tree.heading("content", text="Content Preview")
        
        results_tree.column("rank", width=40)
        results_tree.column("similarity", width=80)
        results_tree.column("distance", width=80)
        results_tree.column("chunk_id", width=150)
        results_tree.column("doc_id", width=120)
        results_tree.column("content", width=300)
        
        results_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=results_tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        results_tree.configure(yscrollcommand=scrollbar.set)
        
        # Status Label
        status_label = ttk.Label(parent, text="Ready", foreground="#888")
        status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def _init_vector_meta_tab(self, parent):
        """Initialize Vector Metadata Tab."""
        label = ttk.Label(
            parent,
            text="Vector Metadata\n\n(JSON metadata display)",
            font=CovinarBranding.FONT_NORMAL,
            foreground=CovinarBranding.COLOR_TEXT_LIGHT,
            justify=tk.CENTER
        )
        label.pack(expand=True)
    
    # ====================
    # SAGA Frame Sub-Tabs
    # ====================
    
    def _init_timeline_tab(self, parent):
        """Initialize SAGA Timeline Tab - Recent Transactions List."""
        # Top Frame: Controls
        control_frame = ttk.LabelFrame(parent, text="Recent SAGAs", padding=5)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Limit Selector
        limit_frame = ttk.Frame(control_frame)
        limit_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(limit_frame, text="Limit:").pack(side=tk.LEFT, padx=5)
        limit_var = tk.StringVar(value="50")
        limit_spin = ttk.Spinbox(limit_frame, from_=10, to=500, textvariable=limit_var, width=10)
        limit_spin.pack(side=tk.LEFT, padx=5)
        
        def load_recent_sagas():
            """Load recent SAGAs from PostgreSQL."""
            timeline_tree.delete(*timeline_tree.get_children())
            
            try:
                limit = int(limit_var.get())
                sagas = self.saga_controller.list_recent_sagas(limit=limit)
                
                for saga in sagas:
                    saga_id = saga.get('saga_id', 'N/A')
                    status = saga.get('status', 'N/A')
                    created = saga.get('created_at', 'N/A')
                    completed = saga.get('completed_at', 'N/A')
                    error = saga.get('error_message', '')
                    
                    # Status Icon
                    status_icon = {
                        'completed': '✅',
                        'compensated': '🔄',
                        'pending': '⏳',
                        'failed': '❌'
                    }.get(status, '❓')
                    
                    timeline_tree.insert("", tk.END, values=(
                        f"{status_icon} {status}",
                        saga_id[:40],
                        str(created)[:19],
                        str(completed)[:19] if completed else "N/A",
                        error[:50] if error else ""
                    ))
                
                status_label.config(text=f"✅ Loaded {len(sagas)} SAGAs")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        # Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🔄 Load Recent", command=load_recent_sagas).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Clear", command=lambda: timeline_tree.delete(*timeline_tree.get_children())).pack(side=tk.LEFT, padx=2)
        
        # Timeline Treeview
        tree_frame = ttk.LabelFrame(parent, text="SAGA Transactions", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("status", "saga_id", "created", "completed", "error")
        timeline_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        timeline_tree.heading("status", text="Status")
        timeline_tree.heading("saga_id", text="SAGA ID")
        timeline_tree.heading("created", text="Created")
        timeline_tree.heading("completed", text="Completed")
        timeline_tree.heading("error", text="Error")
        
        timeline_tree.column("status", width=120)
        timeline_tree.column("saga_id", width=250)
        timeline_tree.column("created", width=150)
        timeline_tree.column("completed", width=150)
        timeline_tree.column("error", width=300)
        
        timeline_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=timeline_tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        timeline_tree.configure(yscrollcommand=scrollbar.set)
        
        # Status Label
        status_label = ttk.Label(parent, text="Click 'Load Recent' to view SAGAs", foreground="#888")
        status_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Auto-load on startup
        self.root.after(500, load_recent_sagas)
    
    def _init_state_tab(self, parent):
        """Initialize State Diagram Tab (SAGA Statistics)."""
        # Main container
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="📊 SAGA Statistics & State Overview",
            font=CovinarBranding.FONT_TITLE,
            foreground=CovinarBranding.COLOR_ACCENT
        )
        title.pack(pady=(0, 10))
        
        # Statistics Frame
        stats_frame = ttk.LabelFrame(main_frame, text="Transaction Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Stats grid
        stats_container = ttk.Frame(stats_frame)
        stats_container.pack(fill=tk.BOTH, expand=True)
        
        # Status labels with icons
        status_data = [
            ("✅ Completed", "completed_label", CovinarBranding.COLOR_SUCCESS),
            ("🔄 Compensated", "compensated_label", CovinarBranding.COLOR_WARNING),
            ("⏳ Pending", "pending_label", CovinarBranding.COLOR_PRIMARY),
            ("❌ Failed", "failed_label", CovinarBranding.COLOR_ERROR)
        ]
        
        self.saga_stat_labels = {}
        
        for idx, (text, key, color) in enumerate(status_data):
            row = idx // 2
            col = idx % 2
            
            frame = ttk.Frame(stats_container)
            frame.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            
            label = ttk.Label(frame, text=text, font=CovinarBranding.FONT_NORMAL, foreground=color)
            label.pack(side=tk.LEFT)
            
            count_label = ttk.Label(frame, text="0", font=("Segoe UI", 14, "bold"), foreground=color)
            count_label.pack(side=tk.LEFT, padx=10)
            
            self.saga_stat_labels[key] = count_label
        
        stats_container.columnconfigure(0, weight=1)
        stats_container.columnconfigure(1, weight=1)
        
        # Total label
        total_frame = ttk.Frame(stats_frame)
        total_frame.pack(pady=(10, 0))
        
        total_label = ttk.Label(total_frame, text="Total Transactions:", font=CovinarBranding.FONT_NORMAL)
        total_label.pack(side=tk.LEFT)
        
        self.saga_total_label = ttk.Label(total_frame, text="0", font=("Segoe UI", 14, "bold"), foreground=CovinarBranding.COLOR_ACCENT)
        self.saga_total_label.pack(side=tk.LEFT, padx=10)
        
        # Recent Failed SAGAs Frame
        failed_frame = ttk.LabelFrame(main_frame, text="Recent Failed Transactions", padding=10)
        failed_frame.pack(fill=tk.BOTH, expand=True)
        
        # Failed SAGAs treeview
        failed_tree_frame = ttk.Frame(failed_frame)
        failed_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        failed_scrollbar = ttk.Scrollbar(failed_tree_frame, orient=tk.VERTICAL)
        failed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("saga_id", "status", "error", "created", "retry_count")
        failed_tree = ttk.Treeview(failed_tree_frame, columns=columns, show="headings", yscrollcommand=failed_scrollbar.set)
        failed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        failed_scrollbar.config(command=failed_tree.yview)
        
        failed_tree.heading("saga_id", text="SAGA ID")
        failed_tree.heading("status", text="Status")
        failed_tree.heading("error", text="Error Message")
        failed_tree.heading("created", text="Created At")
        failed_tree.heading("retry_count", text="Retries")
        
        failed_tree.column("saga_id", width=300)
        failed_tree.column("status", width=120)
        failed_tree.column("error", width=300)
        failed_tree.column("created", width=150)
        failed_tree.column("retry_count", width=80)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        refresh_btn = ttk.Button(button_frame, text="🔄 Refresh Statistics", command=lambda: load_statistics())
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        def load_statistics():
            """Load SAGA statistics from PostgreSQL."""
            try:
                # Get statistics
                stats = self.saga_controller.get_statistics()
                
                # Update counts
                self.saga_stat_labels['completed_label'].config(text=str(stats.get('completed', 0)))
                self.saga_stat_labels['compensated_label'].config(text=str(stats.get('compensated', 0)))
                self.saga_stat_labels['pending_label'].config(text=str(stats.get('pending', 0)))
                self.saga_stat_labels['failed_label'].config(text=str(stats.get('failed', 0)))
                self.saga_total_label.config(text=str(stats.get('total', 0)))
                
                # Load failed SAGAs
                failed_tree.delete(*failed_tree.get_children())
                failed_sagas = self.saga_controller.get_failed_sagas(limit=20)
                
                for saga in failed_sagas:
                    saga_id = saga.get('saga_id', 'N/A')[:40]
                    status = saga.get('status', 'N/A')
                    error = saga.get('error_message', '')[:50]
                    created = str(saga.get('created_at', 'N/A'))[:19]
                    retry_count = saga.get('retry_count', 0)
                    
                    failed_tree.insert("", tk.END, values=(saga_id, status, error, created, retry_count))
                
                print(f"[SAGA] ✅ Statistics loaded: {stats.get('total', 0)} total transactions")
            except Exception as e:
                print(f"[SAGA] ❌ Failed to load statistics: {str(e)}")
        
        # Auto-load on startup
        self.root.after(500, load_statistics)
    
    def _init_event_tab(self, parent):
        """Initialize Event Log Tab (SAGA Steps Details)."""
        # Main container
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="📋 SAGA Steps Event Log",
            font=CovinarBranding.FONT_TITLE,
            foreground=CovinarBranding.COLOR_ACCENT
        )
        title.pack(pady=(0, 10))
        
        # Input Frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(input_frame, text="SAGA ID:", font=CovinarBranding.FONT_NORMAL).pack(side=tk.LEFT, padx=5)
        
        saga_id_var = tk.StringVar()
        saga_id_entry = ttk.Entry(input_frame, textvariable=saga_id_var, width=50)
        saga_id_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        load_btn = ttk.Button(input_frame, text="🔍 Load Steps", command=lambda: load_steps())
        load_btn.pack(side=tk.LEFT, padx=5)
        
        # Steps treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("step_order", "status", "backend", "operation", "started", "completed", "error")
        steps_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=steps_tree.yview)
        
        steps_tree.heading("step_order", text="Step")
        steps_tree.heading("status", text="Status")
        steps_tree.heading("backend", text="Backend")
        steps_tree.heading("operation", text="Operation")
        steps_tree.heading("started", text="Started At")
        steps_tree.heading("completed", text="Completed At")
        steps_tree.heading("error", text="Error Message")
        
        steps_tree.column("step_order", width=60)
        steps_tree.column("status", width=120)
        steps_tree.column("backend", width=120)
        steps_tree.column("operation", width=100)
        steps_tree.column("started", width=150)
        steps_tree.column("completed", width=150)
        steps_tree.column("error", width=300)
        
        # SAGA Info Frame
        info_frame = ttk.LabelFrame(main_frame, text="SAGA Information", padding=10)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.saga_info_text = tk.Text(info_frame, height=4, wrap=tk.WORD, font=("Courier New", 9))
        self.saga_info_text.pack(fill=tk.BOTH, expand=True)
        
        def load_steps():
            """Load SAGA steps from PostgreSQL."""
            steps_tree.delete(*steps_tree.get_children())
            self.saga_info_text.delete(1.0, tk.END)
            
            saga_id = saga_id_var.get().strip()
            if not saga_id:
                print("[SAGA] ❌ Please enter a SAGA ID")
                return
            
            try:
                # Get SAGA status
                saga_status = self.saga_controller.get_saga_status(saga_id)
                
                if not saga_status:
                    print(f"[SAGA] ❌ SAGA not found: {saga_id}")
                    return
                
                # Display SAGA info
                info_text = f"SAGA ID: {saga_status.get('saga_id', 'N/A')}\n"
                info_text += f"Status: {saga_status.get('status', 'N/A')}\n"
                info_text += f"Created: {saga_status.get('created_at', 'N/A')}\n"
                info_text += f"Completed: {saga_status.get('completed_at', 'N/A')}"
                self.saga_info_text.insert(1.0, info_text)
                
                # Get steps
                steps = self.saga_controller.get_saga_steps(saga_id)
                
                for step in steps:
                    step_order = step.get('step_order', 'N/A')
                    status = step.get('status', 'N/A')
                    backend = step.get('backend_name', 'N/A')
                    operation = step.get('operation', 'N/A')
                    started = str(step.get('started_at', 'N/A'))[:19]
                    completed = str(step.get('completed_at', 'N/A'))[:19] if step.get('completed_at') else "N/A"
                    error = step.get('error_message', '')[:50]
                    
                    # Status icon
                    status_icon = ""
                    if status == "completed":
                        status_icon = "✅ "
                    elif status == "compensated":
                        status_icon = "🔄 "
                    elif status == "pending":
                        status_icon = "⏳ "
                    elif status == "failed":
                        status_icon = "❌ "
                    
                    steps_tree.insert("", tk.END, values=(
                        step_order,
                        f"{status_icon}{status}",
                        backend,
                        operation,
                        started,
                        completed,
                        error
                    ))
                
                print(f"[SAGA] ✅ Loaded {len(steps)} steps for SAGA {saga_id[:20]}...")
            except Exception as e:
                print(f"[SAGA] ❌ Failed to load steps: {str(e)}")
    
    def _init_retry_tab(self, parent):
        """Initialize Retry Controls Tab (Failed SAGAs Management)."""
        # Main container
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="🔧 Failed SAGAs Management",
            font=CovinarBranding.FONT_TITLE,
            foreground=CovinarBranding.COLOR_ACCENT
        )
        title.pack(pady=(0, 10))
        
        # Warning banner
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 10))
        
        warning_label = ttk.Label(
            warning_frame,
            text="⚠️ Note: SAGA retry requires Ingestion Backend restart with ENABLE_SAGA=true. This tab shows failed transactions for audit purposes.",
            font=CovinarBranding.FONT_SMALL,
            foreground=CovinarBranding.COLOR_WARNING,
            wraplength=800,
            justify=tk.LEFT
        )
        warning_label.pack(pady=5)
        
        # Controls Frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls_frame, text="Limit:", font=CovinarBranding.FONT_NORMAL).pack(side=tk.LEFT, padx=5)
        
        limit_var = tk.StringVar(value="50")
        limit_spin = ttk.Spinbox(controls_frame, from_=10, to=500, textvariable=limit_var, width=10)
        limit_spin.pack(side=tk.LEFT, padx=5)
        
        load_btn = ttk.Button(controls_frame, text="🔍 Load Failed SAGAs", command=lambda: load_failed_sagas())
        load_btn.pack(side=tk.LEFT, padx=5)
        
        # Failed SAGAs treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("status", "saga_id", "created", "retry_count", "error")
        failed_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        failed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=failed_tree.yview)
        
        failed_tree.heading("status", text="Status")
        failed_tree.heading("saga_id", text="SAGA ID")
        failed_tree.heading("created", text="Created At")
        failed_tree.heading("retry_count", text="Retry Count")
        failed_tree.heading("error", text="Error Message")
        
        failed_tree.column("status", width=120)
        failed_tree.column("saga_id", width=300)
        failed_tree.column("created", width=150)
        failed_tree.column("retry_count", width=100)
        failed_tree.column("error", width=350)
        
        # Details Frame
        details_frame = ttk.LabelFrame(main_frame, text="Error Details", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.retry_details_text = tk.Text(
            details_frame,
            wrap=tk.WORD,
            font=("Courier New", 9),
            yscrollcommand=details_scrollbar.set
        )
        self.retry_details_text.pack(fill=tk.BOTH, expand=True)
        details_scrollbar.config(command=self.retry_details_text.yview)
        
        def on_saga_select(event):
            """Show SAGA details when selected."""
            selection = failed_tree.selection()
            if not selection:
                return
            
            item = failed_tree.item(selection[0])
            values = item['values']
            saga_id = values[1]  # saga_id is 2nd column
            
            # Load details
            self.retry_details_text.delete(1.0, tk.END)
            
            try:
                # Get SAGA status
                saga_status = self.saga_controller.get_saga_status(saga_id)
                
                if saga_status:
                    details = f"{'='*80}\n"
                    details += f"SAGA ID: {saga_status.get('saga_id', 'N/A')}\n"
                    details += f"Status: {saga_status.get('status', 'N/A')}\n"
                    details += f"Created At: {saga_status.get('created_at', 'N/A')}\n"
                    details += f"Updated At: {saga_status.get('updated_at', 'N/A')}\n"
                    details += f"Completed At: {saga_status.get('completed_at', 'N/A')}\n"
                    details += f"Retry Count: {saga_status.get('retry_count', 0)}\n"
                    details += f"Error: {saga_status.get('error_message', 'N/A')}\n"
                    details += f"{'='*80}\n\n"
                    
                    # Get steps
                    steps = self.saga_controller.get_saga_steps(saga_id)
                    
                    if steps:
                        details += f"SAGA STEPS ({len(steps)}):\n"
                        details += f"{'-'*80}\n"
                        
                        for step in steps:
                            step_order = step.get('step_order', 'N/A')
                            status = step.get('status', 'N/A')
                            backend = step.get('backend_name', 'N/A')
                            operation = step.get('operation', 'N/A')
                            error = step.get('error_message', 'N/A')
                            
                            details += f"\n[Step {step_order}] {backend} - {operation}\n"
                            details += f"  Status: {status}\n"
                            details += f"  Started: {step.get('started_at', 'N/A')}\n"
                            details += f"  Completed: {step.get('completed_at', 'N/A')}\n"
                            if error:
                                details += f"  Error: {error}\n"
                    
                    self.retry_details_text.insert(1.0, details)
                else:
                    self.retry_details_text.insert(1.0, "SAGA not found.")
            except Exception as e:
                self.retry_details_text.insert(1.0, f"Error loading details: {str(e)}")
        
        failed_tree.bind('<<TreeviewSelect>>', on_saga_select)
        
        def load_failed_sagas():
            """Load failed SAGAs from PostgreSQL."""
            failed_tree.delete(*failed_tree.get_children())
            self.retry_details_text.delete(1.0, tk.END)
            
            try:
                limit = int(limit_var.get())
                sagas = self.saga_controller.get_failed_sagas(limit=limit)
                
                for saga in sagas:
                    saga_id = saga.get('saga_id', 'N/A')
                    status = saga.get('status', 'N/A')
                    created = str(saga.get('created_at', 'N/A'))[:19]
                    retry_count = saga.get('retry_count', 0)
                    error = saga.get('error_message', '')[:60]
                    
                    # Status icon
                    status_icon = "🔄" if status == "compensated" else "❌"
                    
                    failed_tree.insert("", tk.END, values=(
                        f"{status_icon} {status}",
                        saga_id[:40],
                        created,
                        retry_count,
                        error
                    ))
                
                print(f"[SAGA] ✅ Loaded {len(sagas)} failed SAGAs")
            except Exception as e:
                print(f"[SAGA] ❌ Failed to load SAGAs: {str(e)}")
        
        # Auto-load on startup
        self.root.after(500, load_failed_sagas)
    
    # =======================
    # Document Frame Sub-Tabs
    # =======================
    
    def _init_content_tab(self, parent):
        """Initialize Document Content Tab - Real PostgreSQL Document Display."""
        # Top Frame: Document Selector
        selector_frame = ttk.LabelFrame(parent, text="Document Selector", padding=5)
        selector_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Document ID Entry
        id_frame = ttk.Frame(selector_frame)
        id_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(id_frame, text="Document ID:").pack(side=tk.LEFT, padx=5)
        doc_id_entry = ttk.Entry(id_frame, width=40)
        doc_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def find_saga_for_document():
            """Find and load SAGA for current document ID."""
            doc_id = doc_id_entry.get().strip()
            if not doc_id:
                status_label.config(text="❌ Please enter a Document ID first")
                return
            
            # SAGA ID Pattern: ingest_{document_id}
            saga_id = f"ingest_{doc_id}"
            
            try:
                # Check if SAGA exists
                saga_status = self.saga_controller.get_saga_status(saga_id)
                
                if saga_status:
                    # Switch to SAGA View → Events Tab
                    self.saga_notebook.select(2)  # Tab 3 = Events (0=Timeline, 1=States, 2=Events)
                    
                    # Load SAGA steps in Event Tab
                    # Find the saga_id_var entry widget and set it
                    event_tab = self.saga_notebook.nametowidget(self.saga_notebook.tabs()[2])
                    
                    # Find all entry widgets recursively
                    def find_entry_widget(widget):
                        for child in widget.winfo_children():
                            if isinstance(child, ttk.Entry):
                                return child
                            result = find_entry_widget(child)
                            if result:
                                return result
                        return None
                    
                    entry = find_entry_widget(event_tab)
                    if entry:
                        entry.delete(0, tk.END)
                        entry.insert(0, saga_id)
                        
                        # Trigger load by simulating button click
                        # Find the load button
                        def find_button_widget(widget):
                            for child in widget.winfo_children():
                                if isinstance(child, ttk.Button) and "Load" in str(child.cget('text')):
                                    return child
                                result = find_button_widget(child)
                                if result:
                                    return result
                            return None
                        
                        button = find_button_widget(event_tab)
                        if button:
                            button.invoke()
                    
                    status_label.config(text=f"✅ SAGA found: {saga_id[:50]}")
                else:
                    status_label.config(text=f"⚠️ No SAGA found for document: {doc_id}")
            
            except Exception as e:
                status_label.config(text=f"❌ Error finding SAGA: {str(e)[:80]}")
        
        def load_document():
            """Load document from PostgreSQL."""
            doc_id = doc_id_entry.get().strip()
            if not doc_id:
                return
            
            content_text.delete("1.0", tk.END)
            metadata_text.delete("1.0", tk.END)
            
            try:
                doc = self.document_controller.get_document_by_id(doc_id)
                
                if doc:
                    # Display Content
                    content = doc.get('content_preview', doc.get('content', 'No content available'))
                    content_text.insert("1.0", content)
                    
                    # Display Metadata
                    metadata_lines = [
                        f"Document ID: {doc.get('document_id', 'N/A')}",
                        f"Title: {doc.get('title', 'N/A')}",
                        f"File Name: {doc.get('file_name', 'N/A')}",
                        f"Created: {doc.get('created_at', 'N/A')}",
                        f"Status: {doc.get('status', 'N/A')}",
                        f"Size: {doc.get('file_size', 'N/A')} bytes",
                        f"Type: {doc.get('file_type', 'N/A')}"
                    ]
                    metadata_text.insert("1.0", "\n".join(metadata_lines))
                    
                    status_label.config(text=f"✅ Document loaded: {doc.get('title', doc_id)[:50]}")
                else:
                    status_label.config(text="⚠️ Document not found")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        def search_documents():
            """Search documents by keyword."""
            query = doc_id_entry.get().strip()
            if not query:
                return
            
            try:
                results = self.document_controller.search_documents(query, filters={}, limit=20)
                
                if results:
                    # Show results in a simple list
                    result_text = "\n\n".join([
                        f"ID: {r.get('document_id')}\nTitle: {r.get('title')}\nFile: {r.get('file_name')}"
                        for r in results
                    ])
                    content_text.delete("1.0", tk.END)
                    content_text.insert("1.0", f"Found {len(results)} documents:\n\n{result_text}")
                    status_label.config(text=f"✅ Found {len(results)} documents")
                else:
                    status_label.config(text="⚠️ No documents found")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        # Buttons
        btn_frame = ttk.Frame(selector_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="📄 Load by ID", command=load_document).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🔍 Search", command=search_documents).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="� Find SAGA", command=find_saga_for_document).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="�🗑 Clear", command=lambda: content_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=2)
        
        # Content Display (PanedWindow for split view)
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Content
        content_frame = ttk.LabelFrame(paned, text="Document Content", padding=5)
        paned.add(content_frame, weight=2)
        
        content_text = tk.Text(
            content_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#f5f5f5"
        )
        content_text.pack(fill=tk.BOTH, expand=True)
        
        content_scroll = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=content_text.yview)
        content_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        content_text.configure(yscrollcommand=content_scroll.set)
        
        # Right: Metadata
        metadata_frame = ttk.LabelFrame(paned, text="Metadata", padding=5)
        paned.add(metadata_frame, weight=1)
        
        metadata_text = tk.Text(
            metadata_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#f9f9f9"
        )
        metadata_text.pack(fill=tk.BOTH, expand=True)
        
        # Status Label
        status_label = ttk.Label(parent, text="Enter Document ID or search keyword", foreground="#888")
        status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def _init_doc_meta_tab(self, parent):
        """Initialize Document Metadata Tab - Structured Metadata Display."""
        # Top Frame: Document Selector
        selector_frame = ttk.LabelFrame(parent, text="Document Selector", padding=5)
        selector_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Document ID Entry
        id_frame = ttk.Frame(selector_frame)
        id_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(id_frame, text="Document ID:").pack(side=tk.LEFT, padx=5)
        doc_id_entry = ttk.Entry(id_frame, width=50)
        doc_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def load_metadata():
            """Load document metadata from PostgreSQL."""
            doc_id = doc_id_entry.get().strip()
            if not doc_id:
                return
            
            metadata_tree.delete(*metadata_tree.get_children())
            
            try:
                doc = self.document_controller.get_document_by_id(doc_id)
                
                if doc:
                    # Core Metadata
                    core_parent = metadata_tree.insert("", tk.END, text="📋 Core Metadata", open=True)
                    metadata_tree.insert(core_parent, tk.END, values=("Document ID", doc.get('document_id', 'N/A')))
                    metadata_tree.insert(core_parent, tk.END, values=("Title", doc.get('title', 'N/A')))
                    metadata_tree.insert(core_parent, tk.END, values=("File Name", doc.get('file_name', 'N/A')))
                    metadata_tree.insert(core_parent, tk.END, values=("Status", doc.get('status', 'N/A')))
                    
                    # File Info
                    file_parent = metadata_tree.insert("", tk.END, text="📁 File Information", open=True)
                    metadata_tree.insert(file_parent, tk.END, values=("File Type", doc.get('file_type', 'N/A')))
                    metadata_tree.insert(file_parent, tk.END, values=("File Size", f"{doc.get('file_size', 0):,} bytes"))
                    metadata_tree.insert(file_parent, tk.END, values=("File Path", doc.get('file_path', 'N/A')))
                    
                    # Timestamps
                    time_parent = metadata_tree.insert("", tk.END, text="⏰ Timestamps", open=True)
                    metadata_tree.insert(time_parent, tk.END, values=("Created At", doc.get('created_at', 'N/A')))
                    metadata_tree.insert(time_parent, tk.END, values=("Updated At", doc.get('updated_at', 'N/A')))
                    metadata_tree.insert(time_parent, tk.END, values=("Processed At", doc.get('processed_at', 'N/A')))
                    
                    # Processing Info
                    proc_parent = metadata_tree.insert("", tk.END, text="⚙️ Processing", open=False)
                    metadata_tree.insert(proc_parent, tk.END, values=("Job ID", doc.get('job_id', 'N/A')))
                    metadata_tree.insert(proc_parent, tk.END, values=("Classification", doc.get('classification', 'N/A')))
                    metadata_tree.insert(proc_parent, tk.END, values=("Language", doc.get('language', 'N/A')))
                    
                    status_label.config(text=f"✅ Metadata loaded: {doc.get('title', doc_id)[:50]}")
                else:
                    status_label.config(text="⚠️ Document not found")
            
            except Exception as e:
                status_label.config(text=f"❌ Error: {str(e)[:80]}")
        
        # Buttons
        btn_frame = ttk.Frame(selector_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="📄 Load Metadata", command=load_metadata).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Clear", command=lambda: metadata_tree.delete(*metadata_tree.get_children())).pack(side=tk.LEFT, padx=2)
        
        # Metadata Treeview
        tree_frame = ttk.LabelFrame(parent, text="Metadata Structure", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("field", "value")
        metadata_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=20)
        
        metadata_tree.heading("#0", text="Category")
        metadata_tree.heading("field", text="Field")
        metadata_tree.heading("value", text="Value")
        
        metadata_tree.column("#0", width=200)
        metadata_tree.column("field", width=200)
        metadata_tree.column("value", width=400)
        
        metadata_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=metadata_tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        metadata_tree.configure(yscrollcommand=scrollbar.set)
        
        # Status Label
        status_label = ttk.Label(parent, text="Enter Document ID to load metadata", foreground="#888")
        status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def _init_history_tab(self, parent):
        """Initialize Processing History Tab."""
        label = ttk.Label(
            parent,
            text="Processing History\n\n(Upload, Scans, Jobs)",
            font=CovinarBranding.FONT_NORMAL,
            foreground=CovinarBranding.COLOR_TEXT_LIGHT,
            justify=tk.CENTER
        )
        label.pack(expand=True)
    
    def _init_export_tab(self, parent):
        """Initialize Export Options Tab."""
        label = ttk.Label(
            parent,
            text="Export Options\n\n(PDF, Markdown, JSON)",
            font=CovinarBranding.FONT_NORMAL,
            foreground=CovinarBranding.COLOR_TEXT_LIGHT,
            justify=tk.CENTER
        )
        label.pack(expand=True)
    
    # ====================
    # Search & Navigation
    # ====================
    
    def _execute_search(self):
        """Execute Universal Search via SearchController with hybrid/semantic/regex modes."""
        query = self.search_entry.get().strip()
        
        if not query:
            messagebox.showwarning("Input Required", "Please enter a search term")
            return
        
        # Get selected search mode
        mode = self.search_mode.get()
        
        self.statusbar.set_status(f"Searching ({mode}): {query}...", "info")
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Real Search via SearchController with hybrid mode
        try:
            # Execute hybrid search (auto-detects mode or uses selected)
            results = self.search_controller.hybrid_search(
                query=query, 
                limit=50,
                mode=mode
            )
            
            # Merge and rank results from all backends
            merged_results = self.search_controller.merge_and_rank_results(results)
            
            # Populate Treeview with ranked results
            self.search_results = merged_results
            
            for result in self.search_results[:30]:  # Top 30 results
                # Extract title/content preview
                title = (
                    result.get('title', '') or 
                    result.get('content', '')[:50] or 
                    result.get('properties', {}).get('title', 'Untitled')
                )
                
                source = result.get('source', 'Unknown')
                relevance = result.get('final_score', 0.0)
                doc_id = result.get('document_id', result.get('id', 'N/A'))
                
                self.results_tree.insert(
                    "",
                    "end",
                    text=title[:80],
                    values=(
                        source,
                        f"{relevance:.2f}",
                        str(doc_id)[:30]
                    )
                )
            
            # Update status with search mode and backend distribution
            rel_count = len(results.get('relational', []))
            vec_count = len(results.get('vector', []))
            graph_count = len(results.get('graph', []))
            
            status_msg = f"Found {len(self.search_results)} results ({mode}) | "
            status_msg += f"PG: {rel_count}, ChromaDB: {vec_count}, Neo4j: {graph_count}"
            
            self.statusbar.set_status(status_msg, "success")
        
        except Exception as e:
            self.statusbar.set_status(f"Search failed: {str(e)[:80]}", "error")
            print(f"[ERROR] Search execution failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _populate_demo_results(self, query):
        """Populate Treeview with demo search results."""
        self.search_results = [
            {"id": "doc_001", "title": f"Document about {query}", "type": "PDF"},
            {"id": "doc_002", "title": f"Research: {query}", "type": "Markdown"},
            {"id": "doc_003", "title": f"Analysis {query}", "type": "Text"},
        ]
        
        for result in self.search_results:
            self.results_tree.insert(
                "",
                "end",
                text=result["title"],
                values=(result["type"], result["id"])
            )
    
    def _on_result_selected(self, event):
        """Handle Treeview selection (preview in statusbar)."""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            doc_id = item["values"][1] if item["values"] else "N/A"
            self.statusbar.set_status(f"Selected: {doc_id}", "info")
    
    def _load_selected_document(self):
        """Load selected document from Treeview into 4 frames."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a document from the results")
            return
        
        item = self.results_tree.item(selection[0])
        doc_id = item["values"][1] if item["values"] else None
        
        if not doc_id:
            return
        
        self.statusbar.set_status(f"Loading document: {doc_id}...", "info")
        self.current_document = doc_id
        
        # TODO: Load data into all 4 frames
        # - Graph Frame: Query Neo4j for document graph
        # - Vector Frame: Query ChromaDB for chunks
        # - SAGA Frame: Query SAGA for processing state
        # - Document Frame: Query PostgreSQL for content
        
        # Demo: Simulate success
        self.root.after(1000, lambda: self.statusbar.set_status(
            f"Document '{doc_id}' loaded successfully",
            "success"
        ))
    
    def _focus_search(self):
        """Focus search entry (Toolbar button)."""
        self.search_entry.focus_set()
    
    def _navigate_back(self):
        """Navigate to previous document in history (placeholder)."""
        self.statusbar.set_status("Back navigation (not implemented)", "info")
    
    def _navigate_forward(self):
        """Navigate to next document in history (placeholder)."""
        self.statusbar.set_status("Forward navigation (not implemented)", "info")
    
    def _refresh_all(self):
        """Refresh all views and backend status."""
        self.statusbar.set_status("Refreshing all data...", "info")
        
        # Refresh backend connection status
        self._update_backend_status()
        
        # Re-execute current search if exists
        if self.search_entry.get().strip():
            self._execute_search()
        
        # Refresh current document if loaded
        if self.current_document:
            doc_id = self.current_document.get('document_id')
            if doc_id:
                # Reload from PostgreSQL
                try:
                    refreshed_doc = self.document_controller.get_document_by_id(doc_id)
                    if refreshed_doc:
                        self.current_document = refreshed_doc
                except Exception as e:
                    print(f"[ERROR] Refresh failed: {e}")
        
        # Refresh SAGA data
        self.refresh_saga_data()
        
        self.root.after(500, lambda: self.statusbar.set_status("✅ Refresh complete", "success"))
    
    def refresh_saga_data(self):
        """Refresh SAGA data in all tabs."""
        print("[SAGA] 🔄 Refreshing SAGA data...")
        
        # Get current SAGA tab
        current_tab = self.saga_notebook.index(self.saga_notebook.select())
        
        # Refresh based on current tab
        if current_tab == 0:  # Timeline
            # Trigger timeline reload by finding the load function
            # This is called by the auto-load timer, so we just simulate it
            print("[SAGA] Refreshing Timeline...")
        elif current_tab == 1:  # States
            print("[SAGA] Refreshing Statistics...")
        elif current_tab == 2:  # Events
            print("[SAGA] Events tab - manual SAGA ID required")
        elif current_tab == 3:  # Retry
            print("[SAGA] Refreshing Failed SAGAs...")
        
        self.statusbar.set_status("🔄 SAGA data refreshed", "success")
    
    # ================
    # Menu Callbacks
    # ================
    
    def _menu_open_document(self):
        """Menu: Open Document by ID (dialog)."""
        doc_id = tk.simpledialog.askstring("Open Document", "Enter Document ID:")
        if doc_id:
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, doc_id)
            self._execute_search()
    
    def _menu_export(self):
        """Menu: Export current document."""
        if not self.current_document:
            messagebox.showinfo("No Document", "No document loaded yet")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Export Document",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Markdown", "*.md"), ("Text", "*.txt"), ("All Files", "*.*")]
        )
        
        if filepath:
            self.statusbar.set_status(f"Exporting to: {filepath}...", "info")
            # TODO: Implement export logic
            self.root.after(500, lambda: self.statusbar.set_status("Export complete", "success"))
    
    def _menu_copy(self):
        """Menu: Copy selected text (placeholder)."""
        self.statusbar.set_status("Copy (not implemented)", "info")
    
    def _menu_find(self):
        """Menu: Focus search entry."""
        self._focus_search()
    
    def _menu_preferences(self):
        """Menu: Open Preferences dialog (placeholder)."""
        messagebox.showinfo("Preferences", "Preferences dialog (not implemented)")
    
    def _toggle_sidebar(self):
        """Menu: Toggle sidebar visibility (placeholder)."""
        self.statusbar.set_status("Toggle sidebar (not implemented)", "info")
    
    def _menu_connection_test(self):
        """Menu: Test all backend connections with detailed results."""
        # Create Test Dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Connection Test")
        dialog.geometry("450x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Results Frame
        results_frame = ttk.LabelFrame(dialog, text="Backend Connection Tests", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        results = []
        
        # Test PostgreSQL
        ttk.Label(results_frame, text="Testing PostgreSQL...").pack(anchor=tk.W, pady=2)
        dialog.update()
        try:
            pg_connected = self.document_controller.is_connected()
            if pg_connected:
                # Try a simple query
                result = self.document_controller.backend.execute_query("SELECT 1", ())
                status = "✅ Connected" if result else "⚠️ Connected (query failed)"
            else:
                status = "❌ Not Connected"
            results.append(("PostgreSQL", status))
        except Exception as e:
            results.append(("PostgreSQL", f"❌ Error: {str(e)[:30]}"))
        
        # Test ChromaDB
        ttk.Label(results_frame, text="Testing ChromaDB...").pack(anchor=tk.W, pady=2)
        dialog.update()
        try:
            chroma_connected = self.vector_controller.is_connected()
            if chroma_connected:
                # Try a test query
                test_results = self.vector_controller.query_similar("test", n_results=1)
                status = "✅ Connected"
            else:
                status = "❌ Not Connected"
            results.append(("ChromaDB", status))
        except Exception as e:
            results.append(("ChromaDB", f"❌ Error: {str(e)[:30]}"))
        
        # Test Neo4j
        ttk.Label(results_frame, text="Testing Neo4j...").pack(anchor=tk.W, pady=2)
        dialog.update()
        try:
            neo4j_connected = self.graph_controller.is_connected()
            if neo4j_connected:
                # Try a simple query
                result = self.graph_controller.execute_cypher("RETURN 1 as test")
                status = "✅ Connected" if result else "⚠️ Connected (query failed)"
            else:
                status = "❌ Not Connected"
            results.append(("Neo4j", status))
        except Exception as e:
            results.append(("Neo4j", f"❌ Error: {str(e)[:30]}"))
        
        # Test SAGA
        ttk.Label(results_frame, text="Testing SAGA...").pack(anchor=tk.W, pady=2)
        dialog.update()
        try:
            saga_health = self.saga_controller.get_health()
            status = "✅ Connected" if saga_health.get('status') == 'healthy' else "⚠️ Unhealthy"
            results.append(("SAGA", status))
        except Exception as e:
            results.append(("SAGA", f"❌ Not Connected"))
        
        # Display Results
        ttk.Separator(results_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        for backend, status in results:
            result_label = ttk.Label(
                results_frame,
                text=f"{backend:15} {status}",
                font=("Consolas", 10)
            )
            result_label.pack(anchor=tk.W, pady=2)
        
        # Update statusbar
        self._update_backend_status()
        
        # Close Button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def _menu_db_stats(self):
        """Menu: Show database statistics in dialog."""
        # Create Stats Dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Database Statistics")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Stats Frame
        stats_frame = ttk.LabelFrame(dialog, text="Backend Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # PostgreSQL Stats
        pg_frame = ttk.LabelFrame(stats_frame, text="📊 PostgreSQL", padding=5)
        pg_frame.pack(fill=tk.X, pady=5)
        
        try:
            # Count documents
            result = self.document_controller.backend.execute_query(
                "SELECT COUNT(*) FROM documents", ()
            )
            doc_count = result[0][0] if result else 0
            ttk.Label(pg_frame, text=f"Documents: {doc_count:,}").pack(anchor=tk.W, padx=5)
        except Exception as e:
            ttk.Label(pg_frame, text=f"Error: {str(e)[:50]}").pack(anchor=tk.W, padx=5)
        
        # ChromaDB Stats
        chroma_frame = ttk.LabelFrame(stats_frame, text="📊 ChromaDB", padding=5)
        chroma_frame.pack(fill=tk.X, pady=5)
        
        try:
            # Get collection count (approximate via query)
            results = self.vector_controller.query_similar("", n_results=1)
            ttk.Label(chroma_frame, text="Collection: covina_vectors").pack(anchor=tk.W, padx=5)
            ttk.Label(chroma_frame, text="Status: Connected ✅").pack(anchor=tk.W, padx=5)
        except Exception as e:
            ttk.Label(chroma_frame, text=f"Error: {str(e)[:50]}").pack(anchor=tk.W, padx=5)
        
        # Neo4j Stats
        neo4j_frame = ttk.LabelFrame(stats_frame, text="🔗 Neo4j", padding=5)
        neo4j_frame.pack(fill=tk.X, pady=5)
        
        try:
            stats = self.graph_controller.get_statistics()
            ttk.Label(neo4j_frame, text=f"Nodes: {stats.get('nodes', 0):,}").pack(anchor=tk.W, padx=5)
            ttk.Label(neo4j_frame, text=f"Relationships: {stats.get('relationships', 0):,}").pack(anchor=tk.W, padx=5)
            ttk.Label(neo4j_frame, text=f"Labels: {stats.get('node_labels', 0):,}").pack(anchor=tk.W, padx=5)
        except Exception as e:
            ttk.Label(neo4j_frame, text=f"Error: {str(e)[:50]}").pack(anchor=tk.W, padx=5)
        
        # Close Button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def _menu_cypher_console(self):
        """Menu: Open Cypher Console (switch to Graph → Cypher tab)."""
        # Switch to Graph Frame, Cypher Tab
        if hasattr(self, 'graph_notebook'):
            self.graph_notebook.select(1)  # Tab index 1 = Cypher
        self.statusbar.set_status("Cypher Console activated", "info")
    
    def _menu_vector_search(self):
        """Menu: Open Vector Search (switch to Vector → Search tab)."""
        if hasattr(self, 'vector_notebook'):
            self.vector_notebook.select(2)  # Tab index 2 = Search
        self.statusbar.set_status("Vector Search activated", "info")
    
    def _menu_help(self):
        """Menu: Show documentation (placeholder)."""
        messagebox.showinfo("Help", "Documentation: https://covina.docs/polyglot-admin")
    
    def _menu_shortcuts(self):
        """Menu: Show keyboard shortcuts."""
        shortcuts = """
Keyboard Shortcuts:

General:
Ctrl+O  - Open Document
Ctrl+F  - Focus Search
Ctrl+E  - Export Document
F5      - Refresh All
Ctrl+Q  - Exit

View Navigation:
Ctrl+Shift+S  - Focus SAGA View
Ctrl+Shift+D  - Focus Document View
Ctrl+Shift+G  - Focus Graph View
Ctrl+Shift+V  - Focus Vector View
        """
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def _menu_about(self):
        """Menu: Show About dialog."""
        about_text = f"""
Polyglot Admin Tool v2.0.0

Universal Document Inspector & Database Viewer
for Polyglot Persistence Systems

Features:
• Neo4j Graph Visualization
• ChromaDB Vector Search
• UDS3 SAGA Monitoring
• PostgreSQL Document Management

Covina System © 2025
        """
        messagebox.showinfo("About", about_text)
    
    # ====================
    # View Focus Helpers
    # ====================
    
    def _focus_saga_view(self):
        """Focus SAGA View (Ctrl+Shift+S)."""
        # SAGA is bottom-left (row=1, col=0)
        self.saga_frame.lift()
        self.statusbar.set_status("📊 SAGA View focused", "info")
    
    def _focus_document_view(self):
        """Focus Document View (Ctrl+Shift+D)."""
        # Document is bottom-right (row=1, col=1)
        self.document_frame.lift()
        self.statusbar.set_status("📄 Document View focused", "info")
    
    def _focus_graph_view(self):
        """Focus Graph View (Ctrl+Shift+G)."""
        # Graph is top-left (row=0, col=0)
        self.graph_frame.lift()
        self.statusbar.set_status("🔗 Graph View focused", "info")
    
    def _focus_vector_view(self):
        """Focus Vector View (Ctrl+Shift+V)."""
        # Vector is top-right (row=0, col=1)
        self.vector_frame.lift()
        self.statusbar.set_status("📊 Vector View focused", "info")
    
    # ====================
    # Connection Management
    # ====================
    
    def _update_connection_status(self):
        """Update Backend Connection Status Indicators (real checks)."""
        # Check PostgreSQL (via Document Controller)
        pg_status = self.document_controller.is_connected()
        self.statusbar.set_connection_status("PostgreSQL", pg_status)
        
        # Check ChromaDB (via Vector Controller)
        chroma_status = self.vector_controller.is_connected()
        self.statusbar.set_connection_status("ChromaDB", chroma_status)
        
        # Check Neo4j (via Graph Controller)
        neo4j_status = self.graph_controller.is_connected()
        self.statusbar.set_connection_status("Neo4j", neo4j_status)
        
        # Check UDS3 SAGA (via SAGA Controller)
        saga_status = self.saga_controller.is_connected()
        self.statusbar.set_connection_status("UDS3", saga_status)
    
    def run(self):
        """Start Application Main Loop."""
        self.root.mainloop()


def main():
    """Entry Point."""
    app = PolyglotAdminApp()
    app.run()


if __name__ == "__main__":
    main()
