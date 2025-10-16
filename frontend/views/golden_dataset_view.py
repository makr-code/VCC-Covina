"""
Golden Dataset & Gap Detection View
====================================

Golden Dataset Status und Coverage Analysis
"""

import tkinter as tk
from tkinter import ttk

from frontend.config import COLORS, FONTS


class GoldenDatasetView(ttk.Frame):
    """Golden Dataset & Gap Detection View"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create widgets"""
        title = ttk.Label(self, text="Golden Dataset & Gap Detection", style='Title.TLabel')
        title.pack(pady=10, anchor=tk.W, padx=20)
        
        # Stats
        stats_frame = ttk.LabelFrame(self, text="Dataset Statistics", padding=15)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack()
        
        ttk.Label(stats_grid, text="Total Documents: N/A", style='Body.TLabel').grid(row=0, column=0, padx=20, pady=5)
        ttk.Label(stats_grid, text="Verified: N/A", style='Body.TLabel').grid(row=0, column=1, padx=20, pady=5)
        ttk.Label(stats_grid, text="Pending: N/A", style='Body.TLabel').grid(row=0, column=2, padx=20, pady=5)
        
        # Gap Detection
        gap_frame = ttk.LabelFrame(self, text="Gap Detection", padding=15)
        gap_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(gap_frame, text="Missing Classifications: 0", style='Body.TLabel').pack(anchor=tk.W, pady=3)
        ttk.Label(gap_frame, text="Incomplete Metadata: 0", style='Body.TLabel').pack(anchor=tk.W, pady=3)
        ttk.Label(gap_frame, text="Coverage Score: 0%", style='Body.TLabel').pack(anchor=tk.W, pady=3)
        
        # Golden dataset table
        table_frame = ttk.LabelFrame(self, text="Golden Dataset Documents", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("UUID", "Document", "Confidence", "Status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar.set, height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column("UUID", width=200)
        self.tree.column("Document", width=400)
        self.tree.column("Confidence", width=100)
        self.tree.column("Status", width=120)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.insert("", tk.END, values=("N/A", "No golden dataset available", "-", "-"))
        
        refresh_btn = ttk.Button(self, text="Refresh Golden Dataset", command=self.refresh)
        refresh_btn.pack(pady=10)
    
    def refresh(self):
        """Refresh data"""
        pass  # TODO: Implement when endpoint is available
