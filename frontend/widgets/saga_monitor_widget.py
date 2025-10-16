"""
SAGA Transaction Monitor Widget
================================

SAGA Transactions Table und Status Monitor
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any

from frontend.config import COLORS, FONTS


class SAGAMonitorWidget(ttk.Frame):
    """SAGA Transaction Monitor"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create widgets"""
        title = ttk.Label(self, text="SAGA Transaction Monitor", style='Title.TLabel')
        title.pack(pady=10, anchor=tk.W, padx=20)
        
        # Stats
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.total_label = ttk.Label(stats_frame, text="Total Transactions: N/A", style='Body.TLabel')
        self.total_label.pack(side=tk.LEFT, padx=10)
        
        self.success_label = ttk.Label(stats_frame, text="Success: N/A", style='Body.TLabel')
        self.success_label.pack(side=tk.LEFT, padx=10)
        
        self.rollback_label = ttk.Label(stats_frame, text="Rollbacks: N/A", style='Body.TLabel')
        self.rollback_label.pack(side=tk.LEFT, padx=10)
        
        # Transactions table
        table_frame = ttk.LabelFrame(self, text="Recent Transactions", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("ID", "Status", "Steps", "Timestamp")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar.set, height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column("ID", width=200)
        self.tree.column("Status", width=150)
        self.tree.column("Steps", width=100)
        self.tree.column("Timestamp", width=180)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Placeholder message
        self.tree.insert("", tk.END, values=("N/A", "No data available", "-", "-"))
        
        # Refresh button
        refresh_btn = ttk.Button(self, text="Refresh SAGA Status", command=self.refresh)
        refresh_btn.pack(pady=10)
    
    def refresh(self):
        """Refresh data"""
        # TODO: Implement when /admin/saga/status endpoint is available
        self.total_label.config(text="Total Transactions: N/A (Endpoint pending)")
        self.success_label.config(text="Success: N/A")
        self.rollback_label.config(text="Rollbacks: N/A")
