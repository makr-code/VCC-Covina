"""
Database Health Dashboard
=========================

4 Panels für PostgreSQL, Neo4j, ChromaDB, CouchDB mit Health Metrics

🎯 ENHANCED (12. Oktober 2025):
+ 4 Matplotlib Charts: DATABASE_CONNECTIONS, CLASSIFICATION_PIE, QUALITY_SPIDER, STORAGE_USAGE
  (moved from Home Dashboard for better performance)
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from frontend.config import COLORS, FONTS
from frontend.services.api_client import api_client
from frontend.core.chart_threading import ChartThreadPool, ChartType, ChartResult, ChartStatus
from frontend.core.chart_workers import CHART_WORKERS


class DatabaseHealthView(ttk.Frame):
    """Database Health Dashboard mit 4 Backend-Panels + 4 Charts"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        self.uds3_data: Optional[Dict[str, Any]] = None
        self.db_stats: Optional[Dict[str, Any]] = None
        self.vector_stats: Optional[Dict[str, Any]] = None
        
        # Chart Thread Pool (5 workers: 4 charts + 1 refresh)
        self.chart_pool = ChartThreadPool(num_workers=5)
        self.canvases: Dict[tuple, FigureCanvasTkAgg] = {}
        
        # Chart Layout (2×2 Grid)
        self.chart_layout = {
            (0, 0): ChartType.DATABASE_CONNECTIONS,   # Bar Chart
            (0, 1): ChartType.CLASSIFICATION_PIE,     # Pie Chart
            (1, 0): ChartType.QUALITY_SPIDER,         # Radar Chart
            (1, 1): ChartType.STORAGE_USAGE,          # Pie Chart
        }
        
        self._create_widgets()
        self._start_chart_pool()
        
        # Initial refresh (delayed)
        self.after(2000, self.refresh)
    
    def _create_widgets(self):
        """Create widgets"""
        title = ttk.Label(self, text="Database Health", style='Title.TLabel')
        title.pack(pady=10, anchor=tk.W, padx=20)
        
        # Grid container
        grid = ttk.Frame(self)
        grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 2x2 Grid for 4 databases
        self.panels = {}
        db_configs = [
            ("PostgreSQL", 0, 0, "relational"),
            ("Neo4j", 0, 1, "graph"),
            ("ChromaDB", 1, 0, "vector"),
            ("CouchDB", 1, 1, "document")
        ]
        
        for db_name, row, col, backend_key in db_configs:
            panel = self._create_db_panel(grid, db_name, backend_key)
            panel.grid(row=row, column=col, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5, pady=5)
            self.panels[db_name] = panel
        
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)
        
        # Refresh button
        refresh_btn = ttk.Button(self, text="Refresh Health Status", command=self.refresh)
        refresh_btn.pack(pady=10)
        
        # ========================================================================
        # CHARTS SECTION (Moved from Home Dashboard)
        # ========================================================================
        charts_separator = ttk.Separator(self, orient='horizontal')
        charts_separator.pack(fill=tk.X, padx=20, pady=10)
        
        charts_title = ttk.Label(self, text="📊 Database Analytics Charts", style='Subtitle.TLabel')
        charts_title.pack(pady=10, anchor=tk.W, padx=20)
        
        # Chart grid container (2×2)
        chart_grid = ttk.Frame(self)
        chart_grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Configure grid weights (2 columns, 2 rows)
        for col in range(2):
            chart_grid.grid_columnconfigure(col, weight=1, uniform="col")
        for row in range(2):
            chart_grid.grid_rowconfigure(row, weight=1, uniform="row")
        
        # Create placeholder frames for charts
        for (row, col), chart_type in self.chart_layout.items():
            placeholder = ttk.Frame(chart_grid, relief=tk.SUNKEN, borderwidth=1)
            placeholder.grid(row=row, column=col, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5, pady=5)
            
            # Loading label
            loading_label = ttk.Label(placeholder, text=f"Loading {chart_type.name}...", style='Body.TLabel')
            loading_label.pack(expand=True)
    
    def _create_db_panel(self, parent, db_name, backend_key):
        """Create individual database panel"""
        frame = ttk.LabelFrame(parent, text=db_name, padding=15)
        
        # Status
        status_label = tk.Label(frame, text="● Unknown", font=FONTS["subtitle"],
                               fg=COLORS["warning"], bg=COLORS["panel"])
        status_label.pack(pady=5)
        
        # Details frame
        details = ttk.Frame(frame)
        details.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Connection
        conn_label = ttk.Label(details, text="Connection: N/A", style='Body.TLabel')
        conn_label.pack(anchor=tk.W, pady=2)
        
        # Documents
        docs_label = ttk.Label(details, text="Documents: N/A", style='Body.TLabel')
        docs_label.pack(anchor=tk.W, pady=2)
        
        # Response Time
        response_label = ttk.Label(details, text="Response: N/A", style='Body.TLabel')
        response_label.pack(anchor=tk.W, pady=2)
        
        # Type
        type_label = ttk.Label(details, text="Type: N/A", style='Body.TLabel')
        type_label.pack(anchor=tk.W, pady=2)
        
        # Store references
        frame.status_label = status_label
        frame.conn_label = conn_label
        frame.docs_label = docs_label
        frame.response_label = response_label
        frame.type_label = type_label
        frame.backend_key = backend_key
        
        return frame
    
    def refresh(self):
        """Refresh all database health data + charts"""
        self.uds3_data = api_client.get_uds3_strategy_status()
        self.db_stats = api_client.get_database_stats()
        self.vector_stats = api_client.get_vector_monitoring()
        
        self._update_panels()
        self.refresh_charts()  # Also refresh charts
    
    def _update_panels(self):
        """Update all panels"""
        if not self.uds3_data or "error" in self.uds3_data:
            return
        
        backends = self.uds3_data.get("backends", {})
        
        for db_name, panel in self.panels.items():
            backend_key = panel.backend_key
            backend_info = backends.get(backend_key, {})
            
            available = backend_info.get("available", False)
            backend_type = backend_info.get("type", "Unknown")
            
            # Update status
            if available:
                panel.status_label.config(text="● Online", fg=COLORS["success"])
                panel.conn_label.config(text="Connection: ✓ Connected")
                panel.type_label.config(text=f"Type: {backend_type}")
            else:
                panel.status_label.config(text="● Offline", fg=COLORS["error"])
                panel.conn_label.config(text="Connection: ✗ Disconnected")
                panel.type_label.config(text="Type: N/A")
            
            # Update document count
            if db_name == "PostgreSQL" and self.db_stats:
                total = self.db_stats.get("total_documents", 0)
                panel.docs_label.config(text=f"Documents: {total:,}")
            elif db_name == "ChromaDB" and self.vector_stats:
                stats = self.vector_stats.get("collection_stats", {})
                total = stats.get("total_documents", 0)
                panel.docs_label.config(text=f"Documents: {total:,}")
            else:
                panel.docs_label.config(text="Documents: N/A")
            
            # Response time (placeholder)
            if available:
                panel.response_label.config(text="Response: < 100ms")
            else:
                panel.response_label.config(text="Response: N/A")
    
    # ========================================================================
    # CHART POOL METHODS (Moved from Home Dashboard)
    # ========================================================================
    
    def _start_chart_pool(self):
        """Start chart thread pool"""
        self.chart_pool.start(CHART_WORKERS)
    
    def refresh_charts(self):
        """Refresh all charts"""
        # Fetch fresh data
        self.uds3_data = api_client.get_uds3_strategy_status()
        self.db_stats = api_client.get_database_stats()
        self.vector_stats = api_client.get_vector_monitoring()
        
        # Submit chart requests
        self._submit_chart_requests()
    
    def _submit_chart_requests(self):
        """Submit all chart rendering requests to thread pool"""
        for (row, col), chart_type in self.chart_layout.items():
            chart_id = f"db_chart_{row}_{col}"
            
            # Prepare data for chart worker
            data = {
                "health": {},
                "uds3": self.uds3_data or {},
                "db_stats": self.db_stats or {},
                "vector": self.vector_stats or {}
            }
            
            # Submit request
            success = self.chart_pool.submit_request(
                chart_id=chart_id,
                chart_type=chart_type,
                data=data,
                callback=lambda result, r=row, c=col: self._handle_chart_result(result, r, c)
            )
            
            if not success:
                print(f"Failed to submit chart request for {chart_type.name}")
    
    def _handle_chart_result(self, result: ChartResult, row: int, col: int):
        """Handle chart rendering result"""
        if result.status == ChartStatus.SUCCESS and result.figure:
            # Remove old canvas if exists
            if (row, col) in self.canvases:
                old_canvas = self.canvases[(row, col)]
                old_canvas.get_tk_widget().destroy()
            
            # Find grid cell frame
            grid_cell = None
            for child in self.children.values():
                if isinstance(child, ttk.Frame):
                    # Find chart grid
                    for grandchild in child.children.values():
                        if isinstance(grandchild, ttk.Frame):
                            # Check grid position
                            info = grandchild.grid_info()
                            if info.get('row') == row and info.get('column') == col:
                                grid_cell = grandchild
                                break
            
            if grid_cell:
                # Clear loading label
                for widget in grid_cell.winfo_children():
                    widget.destroy()
                
                # Create canvas
                canvas = FigureCanvasTkAgg(result.figure, master=grid_cell)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                
                # Store canvas
                self.canvases[(row, col)] = canvas
        elif result.status == ChartStatus.ERROR:
            print(f"Chart error at ({row}, {col}): {result.error}")
    
    def destroy(self):
        """Cleanup when view is destroyed with graceful shutdown"""
        try:
            # Shutdown chart pool
            if hasattr(self, 'chart_pool'):
                try:
                    self.chart_pool.shutdown(timeout=5.0)
                except Exception as e:
                    print(f"⚠️ DatabaseHealthView chart pool shutdown error: {e}")
            
            # Destroy canvases
            if hasattr(self, 'canvases'):
                for canvas in self.canvases.values():
                    try:
                        if hasattr(canvas, 'get_tk_widget'):
                            canvas.get_tk_widget().destroy()
                    except Exception:
                        pass
        except Exception as e:
            print(f"⚠️ DatabaseHealthView destroy error: {e}")
        finally:
            try:
                super().destroy()
            except Exception:
                pass
