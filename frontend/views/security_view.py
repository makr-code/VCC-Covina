"""
Security & Audit Dashboard
===========================

Security Events und Audit Logs
"""

import tkinter as tk
from tkinter import ttk

from frontend.config import COLORS, FONTS


class SecurityView(ttk.Frame):
    """Security & Audit Dashboard"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create widgets"""
        title = ttk.Label(self, text="Security & Audit", style='Title.TLabel')
        title.pack(pady=10, anchor=tk.W, padx=20)
        
        # Alert counters
        alerts_frame = ttk.LabelFrame(self, text="Security Alerts", padding=15)
        alerts_frame.pack(fill=tk.X, padx=20, pady=10)
        
        counters = ttk.Frame(alerts_frame)
        counters.pack()
        
        ttk.Label(counters, text="CRITICAL: 0", style='Body.TLabel').pack(side=tk.LEFT, padx=20)
        ttk.Label(counters, text="WARNING: 0", style='Body.TLabel').pack(side=tk.LEFT, padx=20)
        ttk.Label(counters, text="INFO: 0", style='Body.TLabel').pack(side=tk.LEFT, padx=20)
        
        # Audit logs table
        table_frame = ttk.LabelFrame(self, text="Recent Audit Logs", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("Timestamp", "Action", "User", "Severity")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar.set, height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.insert("", tk.END, values=("N/A", "No audit logs available", "-", "-"))
        
        refresh_btn = ttk.Button(self, text="Refresh Audit Logs", command=self.refresh)
        refresh_btn.pack(pady=10)
    
    def refresh(self):
        """Refresh data"""
        pass  # TODO: Implement when endpoint is available
