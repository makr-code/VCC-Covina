"""
SAGA Monitor View - Phase 3: View Migration

View for SAGA orchestration monitoring.
Shows transaction status, compensation events, and workflow health.

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 3)
Date: 14.10.2025, 11:20 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List
from datetime import datetime

from frontend.views.base_view import BaseView
from frontend.core.event_bus import EventType


class SAGAView(BaseView):
    """
    SAGA Monitor View (Event-Driven).
    
    Monitor SAGA orchestration:
    - Transaction status tracking
    - Compensation event monitoring
    - Workflow health indicators
    - Real-time transaction updates
    """
    
    def __init__(self, parent, event_bus, backend_service, **kwargs):
        self.backend_service = backend_service
        self._transactions: List[Dict[str, Any]] = []
        super().__init__(parent, event_bus, **kwargs)
    
    def build_ui(self):
        """Build SAGA Monitor UI (Pure UI construction)."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        
        title_label = ttk.Label(
            header_frame,
            text="🔄 SAGA Orchestration Monitor",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(side="left")
        
        self.status_label = ttk.Label(
            header_frame,
            text="⚪ Ready",
            font=("Segoe UI", 10)
        )
        self.status_label.pack(side="right", padx=10)
        
        refresh_btn = ttk.Button(
            header_frame,
            text="🔄 Refresh",
            command=self._on_refresh_clicked
        )
        refresh_btn.pack(side="right")
        
        # Statistics Cards
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self._stat_labels = {}
        stat_names = [
            ("total", "Total Transactions"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("failed", "Failed/Compensated")
        ]
        
        for i, (key, label) in enumerate(stat_names):
            card = ttk.LabelFrame(stats_frame, text=label, padding=10)
            card.grid(row=0, column=i, sticky="ew", padx=5)
            
            value_label = ttk.Label(card, text="0", font=("Segoe UI", 14, "bold"))
            value_label.pack()
            
            self._stat_labels[key] = value_label
        
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)
        
        # Transaction List
        list_frame = ttk.LabelFrame(self, text="Recent Transactions", padding=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Treeview
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        
        self.transaction_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "type", "status", "steps", "started", "duration"),
            show="headings",
            yscrollcommand=scrollbar.set
        )
        
        scrollbar.config(command=self.transaction_tree.yview)
        
        # Column headings
        self.transaction_tree.heading("id", text="Transaction ID")
        self.transaction_tree.heading("type", text="Type")
        self.transaction_tree.heading("status", text="Status")
        self.transaction_tree.heading("steps", text="Steps")
        self.transaction_tree.heading("started", text="Started At")
        self.transaction_tree.heading("duration", text="Duration")
        
        # Column widths
        self.transaction_tree.column("id", width=150)
        self.transaction_tree.column("type", width=150)
        self.transaction_tree.column("status", width=120)
        self.transaction_tree.column("steps", width=100)
        self.transaction_tree.column("started", width=150)
        self.transaction_tree.column("duration", width=100)
        
        self.transaction_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Tags for status colors
        self.transaction_tree.tag_configure("active", foreground="orange")
        self.transaction_tree.tag_configure("completed", foreground="green")
        self.transaction_tree.tag_configure("failed", foreground="red")
        
        # Placeholder
        self._show_placeholder()
    
    def _show_placeholder(self):
        """Show placeholder message."""
        self.transaction_tree.insert("", "end", values=(
            "-", "No transactions", "-", "-", "-", "-"
        ))
    
    def update_data(self, data: Dict[str, Any]):
        """Update view with new data (Pure business logic)."""
        data_type = data.get("type")
        
        if data_type == "transactions":
            self._update_transactions(data.get("transactions", []))
        
        elif data_type == "transaction_update":
            self._update_single_transaction(data.get("transaction"))
        
        elif data_type == "statistics":
            self._update_statistics(data.get("stats", {}))
        
        elif data_type == "status":
            self._update_status(data.get("message"), data.get("color", "black"))
    
    def _update_transactions(self, transactions: List[Dict[str, Any]]):
        """Update transaction list."""
        self._transactions = transactions
        
        # Clear existing items
        for item in self.transaction_tree.get_children():
            self.transaction_tree.delete(item)
        
        if not transactions:
            self._show_placeholder()
            return
        
        # Add transactions
        for txn in transactions:
            status = txn.get("status", "unknown")
            tag = status if status in ["active", "completed", "failed"] else ""
            
            self.transaction_tree.insert("", "end", values=(
                txn.get("id", ""),
                txn.get("type", ""),
                status.upper(),
                f"{txn.get('completed_steps', 0)}/{txn.get('total_steps', 0)}",
                txn.get("started_at", ""),
                txn.get("duration", "")
            ), tags=(tag,))
        
        # Update statistics
        self._calculate_statistics()
    
    def _update_single_transaction(self, transaction: Dict[str, Any]):
        """Update a single transaction in the list."""
        if not transaction:
            return
        
        txn_id = transaction.get("id")
        
        # Find and update existing item
        for item in self.transaction_tree.get_children():
            values = self.transaction_tree.item(item)["values"]
            if values[0] == txn_id:
                status = transaction.get("status", "unknown")
                tag = status if status in ["active", "completed", "failed"] else ""
                
                self.transaction_tree.item(item, values=(
                    txn_id,
                    transaction.get("type", ""),
                    status.upper(),
                    f"{transaction.get('completed_steps', 0)}/{transaction.get('total_steps', 0)}",
                    transaction.get("started_at", ""),
                    transaction.get("duration", "")
                ), tags=(tag,))
                return
        
        # If not found, add new
        self._update_transactions(self._transactions + [transaction])
    
    def _calculate_statistics(self):
        """Calculate and update statistics."""
        if not self._transactions:
            stats = {"total": 0, "active": 0, "completed": 0, "failed": 0}
        else:
            stats = {
                "total": len(self._transactions),
                "active": sum(1 for t in self._transactions if t.get("status") == "active"),
                "completed": sum(1 for t in self._transactions if t.get("status") == "completed"),
                "failed": sum(1 for t in self._transactions if t.get("status") in ["failed", "compensated"])
            }
        
        self._update_statistics(stats)
    
    def _update_statistics(self, stats: Dict[str, int]):
        """Update statistics cards."""
        for key, label in self._stat_labels.items():
            value = stats.get(key, 0)
            label.config(text=str(value))
    
    def _update_status(self, message: str, color: str = "black"):
        """Update status indicator."""
        icons = {"black": "⚪", "green": "🟢", "orange": "🟠", "red": "🔴"}
        icon = icons.get(color, "⚪")
        self.status_label.config(text=f"{icon} {message}", foreground=color)
    
    def on_activate(self):
        """Lifecycle: Subscribe to events when view becomes visible."""
        # Subscribe to SAGA events
        self.event_bus.subscribe(EventType.SAGA_TRANSACTION_STARTED, self._on_saga_started)
        self.event_bus.subscribe(EventType.SAGA_TRANSACTION_COMPLETE, self._on_saga_complete)
        self.event_bus.subscribe(EventType.SAGA_TRANSACTION_FAILED, self._on_saga_failed)
        self.event_bus.subscribe(EventType.SAGA_COMPENSATION_STARTED, self._on_compensation)
        
        # Load initial data
        self._load_transactions()
    
    def on_deactivate(self):
        """Lifecycle: Unsubscribe from events when view becomes hidden."""
        self.event_bus.unsubscribe(EventType.SAGA_TRANSACTION_STARTED, self._on_saga_started)
        self.event_bus.unsubscribe(EventType.SAGA_TRANSACTION_COMPLETE, self._on_saga_complete)
        self.event_bus.unsubscribe(EventType.SAGA_TRANSACTION_FAILED, self._on_saga_failed)
        self.event_bus.unsubscribe(EventType.SAGA_COMPENSATION_STARTED, self._on_compensation)
    
    # Event Handlers
    
    def _on_saga_started(self, event):
        """Handle SAGA transaction started."""
        txn_id = event.data.get("transaction_id")
        self.safe_update_data({
            "type": "status",
            "message": f"Transaction {txn_id} started",
            "color": "orange"
        })
    
    def _on_saga_complete(self, event):
        """Handle SAGA transaction complete."""
        txn_id = event.data.get("transaction_id")
        self.safe_update_data({
            "type": "status",
            "message": f"Transaction {txn_id} completed",
            "color": "green"
        })
        # Refresh list
        self._load_transactions()
    
    def _on_saga_failed(self, event):
        """Handle SAGA transaction failed."""
        txn_id = event.data.get("transaction_id")
        self.safe_update_data({
            "type": "status",
            "message": f"Transaction {txn_id} failed",
            "color": "red"
        })
        # Refresh list
        self._load_transactions()
    
    def _on_compensation(self, event):
        """Handle SAGA compensation started."""
        txn_id = event.data.get("transaction_id")
        self.safe_update_data({
            "type": "status",
            "message": f"Compensation started for {txn_id}",
            "color": "orange"
        })
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self._load_transactions()
    
    def _load_transactions(self):
        """Load transactions from backend (placeholder)."""
        # TODO: Implement actual backend call
        # For now, show mock data
        mock_transactions = [
            {
                "id": "txn_001",
                "type": "document_ingestion",
                "status": "completed",
                "completed_steps": 4,
                "total_steps": 4,
                "started_at": "2025-10-14 10:30:15",
                "duration": "2.5s"
            },
            {
                "id": "txn_002",
                "type": "batch_processing",
                "status": "active",
                "completed_steps": 2,
                "total_steps": 5,
                "started_at": "2025-10-14 10:35:20",
                "duration": "15s"
            },
            {
                "id": "txn_003",
                "type": "data_migration",
                "status": "failed",
                "completed_steps": 3,
                "total_steps": 6,
                "started_at": "2025-10-14 10:20:05",
                "duration": "45s"
            }
        ]
        
        self.safe_update_data({"type": "transactions", "transactions": mock_transactions})


# Export
__all__ = ["SAGAView"]
