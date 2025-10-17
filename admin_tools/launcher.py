"""
Covina Admin Tools Launcher
============================

Zentrale Launcher-Applikation für alle Admin-Tools

Admin Tools:
1. Golden Dataset Manager (Relational)
2. Graph Pattern Manager (Neo4j)
3. Governance Policy Manager

Author: Covina Backend Team
Date: 17. Oktober 2025
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
from pathlib import Path


class AdminToolsLauncher:
    """Zentrale Launcher GUI für alle Admin-Tools"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.admin_tools_dir = Path(__file__).parent
        
        # Window Configuration
        self.root.title("Covina Admin Tools - Launcher")
        self.root.geometry("800x600")
        self.root.configure(bg="#2b2b2b")
        
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Initialize UI
        self._create_header()
        self._create_tools_section()
        self._create_footer()
    
    def _create_header(self):
        """Create header with logo and title"""
        header = tk.Frame(self.root, bg="#1e1e1e", height=100)
        header.pack(side=tk.TOP, fill=tk.X)
        
        # Title
        title_label = tk.Label(header, text="Covina Admin Tools", 
                              font=("Arial", 24, "bold"), bg="#1e1e1e", fg="#4a90e2")
        title_label.pack(pady=20)
        
        # Subtitle
        subtitle_label = tk.Label(header, text="Verwaltung von Golden Datasets, Graph Patterns & Governance Policies", 
                                 font=("Arial", 10), bg="#1e1e1e", fg="#aaaaaa")
        subtitle_label.pack()
    
    def _create_tools_section(self):
        """Create tools selection section"""
        tools_frame = tk.Frame(self.root, bg="#2b2b2b")
        tools_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        # Tools Grid
        tools_grid = tk.Frame(tools_frame, bg="#2b2b2b")
        tools_grid.pack(expand=True)
        
        # Tool 1: Golden Dataset Manager
        self._create_tool_card(
            tools_grid, 
            row=0, col=0,
            title="Golden Dataset Manager",
            description="Verwaltung von Golden Datasets\n(Relational, PostgreSQL)",
            icon="📋",
            script="golden_dataset_manager.py",
            features=[
                "✅ CRUD Operations",
                "✅ Filter & Search",
                "✅ Quality Score Tracking",
                "✅ CSV Export"
            ]
        )
        
        # Tool 2: Graph Pattern Manager
        self._create_tool_card(
            tools_grid,
            row=0, col=1,
            title="Graph Pattern Manager",
            description="Verwaltung von Graph Patterns\n(Neo4j, PostgreSQL Hybrid)",
            icon="🔗",
            script="graph_pattern_manager.py",
            features=[
                "✅ Pattern Definition",
                "✅ Node & Relation Config",
                "✅ Validation Rules",
                "✅ JSON Export"
            ]
        )
        
        # Tool 3: Governance Policy Manager
        self._create_tool_card(
            tools_grid,
            row=1, col=0,
            title="Governance Policy Manager",
            description="Verwaltung von Governance Policies\n(Retention, Compliance, Access Control)",
            icon="⚖️",
            script="governance_policy_manager.py",
            features=[
                "✅ Policy Management",
                "✅ Approval Workflow",
                "✅ Temporal Validity",
                "✅ Priority Handling"
            ]
        )
        
        # Tool 4: All-in-One (Future)
        self._create_tool_card(
            tools_grid,
            row=1, col=1,
            title="All-in-One Dashboard",
            description="Kombinierte Ansicht aller Tools\n(Coming Soon)",
            icon="🎛️",
            script=None,
            features=[
                "⏳ Multi-Tab Interface",
                "⏳ Cross-Tool Analytics",
                "⏳ Unified Search",
                "⏳ Batch Operations"
            ],
            disabled=True
        )
    
    def _create_tool_card(self, parent, row, col, title, description, icon, script, features, disabled=False):
        """Create a tool card"""
        # Card Frame
        card = tk.Frame(parent, bg="#3c3f41", relief=tk.RAISED, borderwidth=2)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Icon
        icon_label = tk.Label(card, text=icon, font=("Arial", 48), bg="#3c3f41", fg="white")
        icon_label.pack(pady=(20, 10))
        
        # Title
        title_label = tk.Label(card, text=title, font=("Arial", 14, "bold"), 
                              bg="#3c3f41", fg="white", wraplength=300)
        title_label.pack(pady=(0, 5))
        
        # Description
        desc_label = tk.Label(card, text=description, font=("Arial", 9), 
                             bg="#3c3f41", fg="#aaaaaa", wraplength=300, justify=tk.CENTER)
        desc_label.pack(pady=(0, 10))
        
        # Features
        features_frame = tk.Frame(card, bg="#3c3f41")
        features_frame.pack(pady=(10, 15))
        
        for feature in features:
            feature_label = tk.Label(features_frame, text=feature, font=("Arial", 8), 
                                    bg="#3c3f41", fg="#dddddd", anchor=tk.W)
            feature_label.pack(anchor=tk.W, padx=20)
        
        # Launch Button
        if not disabled:
            btn = tk.Button(card, text="🚀 Starten", command=lambda: self.launch_tool(script),
                          bg="#4a90e2", fg="white", font=("Arial", 11, "bold"), 
                          padx=30, pady=10, cursor="hand2")
        else:
            btn = tk.Button(card, text="⏳ Bald verfügbar", state=tk.DISABLED,
                          bg="#555555", fg="#999999", font=("Arial", 11), 
                          padx=30, pady=10)
        btn.pack(pady=(0, 20))
        
        # Make card slightly interactive
        if not disabled:
            card.bind("<Enter>", lambda e: card.configure(bg="#4a4f51"))
            card.bind("<Leave>", lambda e: card.configure(bg="#3c3f41"))
    
    def _create_footer(self):
        """Create footer with info and settings"""
        footer = tk.Frame(self.root, bg="#1e1e1e", height=60)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Backend URL Configuration
        config_frame = tk.Frame(footer, bg="#1e1e1e")
        config_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        tk.Label(config_frame, text="Backend URL:", bg="#1e1e1e", fg="white").pack(side=tk.LEFT)
        self.backend_url_var = tk.StringVar(value="http://127.0.0.1:45678")
        tk.Entry(config_frame, textvariable=self.backend_url_var, width=30, bg="#3c3f41", fg="white").pack(side=tk.LEFT, padx=10)
        
        # Status
        status_frame = tk.Frame(footer, bg="#1e1e1e")
        status_frame.pack(side=tk.RIGHT, padx=20, pady=10)
        
        tk.Label(status_frame, text="Version 1.0.0", bg="#1e1e1e", fg="#aaaaaa").pack(side=tk.LEFT, padx=10)
        tk.Label(status_frame, text="•", bg="#1e1e1e", fg="#666666").pack(side=tk.LEFT)
        tk.Label(status_frame, text="Covina Backend Team", bg="#1e1e1e", fg="#aaaaaa").pack(side=tk.LEFT, padx=10)
    
    def launch_tool(self, script_name):
        """Launch selected admin tool"""
        if not script_name:
            messagebox.showwarning("Nicht verfügbar", "Dieses Tool ist noch nicht verfügbar.")
            return
        
        script_path = self.admin_tools_dir / script_name
        
        if not script_path.exists():
            messagebox.showerror("Fehler", f"Tool nicht gefunden:\n{script_path}")
            return
        
        try:
            # Get backend URL
            backend_url = self.backend_url_var.get()
            
            # Launch tool in new process
            subprocess.Popen([sys.executable, str(script_path)], 
                           env={**os.environ, "COVINA_BACKEND_URL": backend_url})
            
            messagebox.showinfo("Tool gestartet", f"{script_name} wurde in einem neuen Fenster geöffnet.")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Starten des Tools:\n{str(e)}")


def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Set style
    style = ttk.Style()
    style.theme_use('clam')
    
    app = AdminToolsLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
