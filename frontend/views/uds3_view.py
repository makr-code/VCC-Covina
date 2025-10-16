"""
UDS3 Datasets View - Phase 3: View Migration

View for UDS3 Multi-Database dataset management.
Shows datasets across PostgreSQL, ChromaDB, Neo4j, and CouchDB.

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 3)
Date: 14.10.2025, 11:15 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List

from frontend.views.base_view import BaseView
from frontend.core.event_bus import EventType


class UDS3View(BaseView):
    """
    UDS3 Datasets View (Event-Driven).
    
    Manage datasets across all 4 UDS3 databases:
    - PostgreSQL (Relational Master Data)
    - ChromaDB (Vector Embeddings)
    - Neo4j (Knowledge Graph)
    - CouchDB (Full Content Storage)
    """
    
    def __init__(self, parent, event_bus, backend_service, **kwargs):
        self.backend_service = backend_service
        self._datasets: List[Dict[str, Any]] = []
        super().__init__(parent, event_bus, **kwargs)
    
    def build_ui(self):
        """Build UDS3 Datasets UI (Pure UI construction)."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        
        title_label = ttk.Label(
            header_frame,
            text="📚 UDS3 Datasets",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(side="left")
        
        refresh_btn = ttk.Button(
            header_frame,
            text="🔄 Refresh",
            command=self._on_refresh_clicked
        )
        refresh_btn.pack(side="right")
        
        # Database Status Cards
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self._db_status_labels = {}
        db_names = ["PostgreSQL", "ChromaDB", "Neo4j", "CouchDB"]
        for i, db_name in enumerate(db_names):
            card = ttk.LabelFrame(status_frame, text=db_name, padding=10)
            card.grid(row=0, column=i, sticky="ew", padx=5)
            
            status_label = ttk.Label(card, text="⚪ Unknown", font=("Segoe UI", 10))
            status_label.pack()
            
            self._db_status_labels[db_name.lower().replace(" ", "_")] = status_label
        
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(2, weight=1)
        status_frame.columnconfigure(3, weight=1)
        
        # Dataset List
        list_frame = ttk.LabelFrame(self, text="Datasets", padding=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Treeview
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        
        self.dataset_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "name", "postgres", "chroma", "neo4j", "couch", "docs"),
            show="headings",
            yscrollcommand=scrollbar.set
        )
        
        scrollbar.config(command=self.dataset_tree.yview)
        
        # Column headings
        self.dataset_tree.heading("id", text="ID")
        self.dataset_tree.heading("name", text="Dataset Name")
        self.dataset_tree.heading("postgres", text="PostgreSQL")
        self.dataset_tree.heading("chroma", text="ChromaDB")
        self.dataset_tree.heading("neo4j", text="Neo4j")
        self.dataset_tree.heading("couch", text="CouchDB")
        self.dataset_tree.heading("docs", text="Documents")
        
        # Column widths
        self.dataset_tree.column("id", width=80)
        self.dataset_tree.column("name", width=200)
        self.dataset_tree.column("postgres", width=100)
        self.dataset_tree.column("chroma", width=100)
        self.dataset_tree.column("neo4j", width=100)
        self.dataset_tree.column("couch", width=100)
        self.dataset_tree.column("docs", width=100)
        
        self.dataset_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Placeholder
        self._show_placeholder()
    
    def _show_placeholder(self):
        """Show placeholder message."""
        self.dataset_tree.insert("", "end", values=(
            "-", "No datasets loaded", "-", "-", "-", "-", "-"
        ))
    
    def update_data(self, data: Dict[str, Any]):
        """Update view with new data (Pure business logic)."""
        data_type = data.get("type")
        
        if data_type == "datasets":
            self._update_datasets(data.get("datasets", []))
        
        elif data_type == "db_status":
            self._update_db_status(data.get("status", {}))
    
    def _update_datasets(self, datasets: List[Dict[str, Any]]):
        """Update dataset list."""
        self._datasets = datasets
        
        # Clear existing items
        for item in self.dataset_tree.get_children():
            self.dataset_tree.delete(item)
        
        if not datasets:
            self._show_placeholder()
            return
        
        # Add datasets
        for ds in datasets:
            self.dataset_tree.insert("", "end", values=(
                ds.get("id", ""),
                ds.get("name", ""),
                "✅" if ds.get("postgres", False) else "❌",
                "✅" if ds.get("chromadb", False) else "❌",
                "✅" if ds.get("neo4j", False) else "❌",
                "✅" if ds.get("couchdb", False) else "❌",
                ds.get("document_count", 0)
            ))
    
    def _update_db_status(self, status: Dict[str, bool]):
        """Update database status indicators."""
        for db_name, label in self._db_status_labels.items():
            connected = status.get(db_name, False)
            if connected:
                label.config(text="🟢 Connected", foreground="green")
            else:
                label.config(text="🔴 Disconnected", foreground="red")
    
    def on_activate(self):
        """Lifecycle: Subscribe to events when view becomes visible."""
        # Subscribe to UDS3 events
        self.event_bus.subscribe(EventType.UDS3_QUERY_STARTED, self._on_uds3_event)
        self.event_bus.subscribe(EventType.UDS3_QUERY_COMPLETE, self._on_uds3_event)
        self.event_bus.subscribe(EventType.DB_HEALTH_CHECK, self._on_db_health)
        
        # Load initial data
        self._load_datasets()
    
    def on_deactivate(self):
        """Lifecycle: Unsubscribe from events when view becomes hidden."""
        self.event_bus.unsubscribe(EventType.UDS3_QUERY_STARTED, self._on_uds3_event)
        self.event_bus.unsubscribe(EventType.UDS3_QUERY_COMPLETE, self._on_uds3_event)
        self.event_bus.unsubscribe(EventType.DB_HEALTH_CHECK, self._on_db_health)
    
    # Event Handlers
    
    def _on_uds3_event(self, event):
        """Handle UDS3 events."""
        # Could update specific dataset
        pass
    
    def _on_db_health(self, event):
        """Handle database health check."""
        db_status = event.data.get("status", {})
        self.safe_update_data({"type": "db_status", "status": db_status})
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self._load_datasets()
    
    def _load_datasets(self):
        """Load datasets from backend (placeholder)."""
        # TODO: Implement actual backend call
        # For now, show mock data
        mock_datasets = [
            {
                "id": 1,
                "name": "Production Dataset",
                "postgres": True,
                "chromadb": True,
                "neo4j": True,
                "couchdb": True,
                "document_count": 6523
            },
            {
                "id": 2,
                "name": "Test Dataset",
                "postgres": True,
                "chromadb": True,
                "neo4j": False,
                "couchdb": True,
                "document_count": 150
            }
        ]
        
        self.safe_update_data({"type": "datasets", "datasets": mock_datasets})
        
        # Mock DB status
        mock_status = {
            "postgresql": True,
            "chromadb": True,
            "neo4j": True,
            "couchdb": True
        }
        self.safe_update_data({"type": "db_status", "status": mock_status})


# Export
__all__ = ["UDS3View"]
