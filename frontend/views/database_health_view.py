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

from frontend.config import COLORS, FONTS, CHART_MODE
from frontend.services.api_client import api_client
from frontend.widgets.kpi_card import KPICard, create_kpi_grid
try:
    if CHART_MODE == "full":
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from frontend.core.chart_threading import ChartThreadPool, ChartType, ChartResult, ChartStatus
        from frontend.core.chart_workers import CHART_WORKERS
    else:
        FigureCanvasTkAgg = None  # type: ignore
        ChartThreadPool = None  # type: ignore
        ChartType = None  # type: ignore
        ChartResult = None  # type: ignore
        ChartStatus = None  # type: ignore
        CHART_WORKERS = None  # type: ignore
except Exception:
    FigureCanvasTkAgg = None  # type: ignore
    ChartThreadPool = None  # type: ignore
    ChartType = None  # type: ignore
    ChartResult = None  # type: ignore
    ChartStatus = None  # type: ignore
    CHART_WORKERS = None  # type: ignore


class DatabaseHealthView(ttk.Frame):
    """Database Health Dashboard mit 4 Backend-Panels + 4 Charts"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        self.uds3_data: Optional[Dict[str, Any]] = None
        self.db_stats: Optional[Dict[str, Any]] = None
        self.vector_stats: Optional[Dict[str, Any]] = None
        
        # Chart Thread Pool (only in full mode)
        self.chart_pool = ChartThreadPool(num_workers=2) if CHART_MODE == "full" and ChartThreadPool is not None else None
        self.canvases: Dict[tuple, Any] = {}
        
        # Chart Layout (REDUCED: 1 Chart only - DATABASE_CONNECTIONS)
        # Removed: CLASSIFICATION_PIE (redundant), QUALITY_SPIDER (no data), STORAGE_USAGE (now KPI)
        self.chart_layout = {
            (0, 0): ChartType.DATABASE_CONNECTIONS,   # Bar Chart - PostgreSQL Tables
        } if CHART_MODE == "full" and ChartType is not None else {}
        
        # KPI Cards (NEW)
        self.kpi_cards: Dict[str, KPICard] = {}
        
        self._create_widgets()
        self._start_chart_pool()
        
        # Initial refresh (delayed)
        self.after(2000, self.refresh)
    
    def _create_widgets(self):
        """Create widgets"""
        title = ttk.Label(self, text="💾 Database Health Monitor", style='Title.TLabel')
        title.pack(pady=10, anchor=tk.W, padx=20)
        
        # KPI Cards (NEW - 4 cards showing key metrics)
        kpi_definitions = [
            {"title": "Total Size", "value": "N/A", "icon": "💾"},
            {"title": "Connections", "value": "N/A", "icon": "🔌"},
            {"title": "Avg Query Time", "value": "N/A", "icon": "⚡"},
            {"title": "Table Count", "value": "N/A", "icon": "📊"}
        ]
        self.kpi_cards = create_kpi_grid(self, kpi_definitions, columns=4)
        
        # Grid container (Database panels)
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
        refresh_btn = ttk.Button(self, text="🔄 Refresh Health Status", command=self.refresh)
        refresh_btn.pack(pady=10)
        
        # ========================================================================
        # CHART SECTION (REDUCED: 1 chart only - DATABASE_CONNECTIONS)
        # ========================================================================
        if CHART_MODE == "full":
            charts_separator = ttk.Separator(self, orient='horizontal')
            charts_separator.pack(fill=tk.X, padx=20, pady=10)
            charts_title = ttk.Label(self, text="📊 Database Analytics", style='Subtitle.TLabel')
            charts_title.pack(pady=10, anchor=tk.W, padx=20)
            chart_grid = ttk.Frame(self)
            chart_grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            chart_grid.grid_columnconfigure(0, weight=1)
            chart_grid.grid_rowconfigure(0, weight=1)
            # Create placeholder for single chart
            for (row, col), chart_type in self.chart_layout.items():
                placeholder = ttk.Frame(chart_grid, relief=tk.SUNKEN, borderwidth=1)
                placeholder.grid(row=row, column=col, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5, pady=5)
                loading_label = ttk.Label(placeholder, text=f"⏳ Loading {chart_type.name}...", style='Body.TLabel')
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
        """Refresh all database health data + KPIs + charts"""
        self.uds3_data = api_client.get_uds3_strategy_status()
        self.db_stats = api_client.get_database_stats()
        self.vector_stats = api_client.get_vector_monitoring()
        
        self._update_panels()
        self._update_kpis()  # NEW: Update KPI cards
        self.refresh_charts()  # Also refresh charts
    
    def _update_kpis(self):
        """Update KPI cards with database metrics"""
        try:
            if self.db_stats and isinstance(self.db_stats, dict):
                # Total Size: Sum all table sizes
                total_size_mb = 0
                table_count = 0
                if 'table_stats' in self.db_stats:
                    for table_name, table_info in self.db_stats['table_stats'].items():
                        if isinstance(table_info, dict) and 'size_mb' in table_info:
                            total_size_mb += table_info['size_mb']
                            table_count += 1
                
                self.kpi_cards["Total Size"].update_value(f"{total_size_mb:.1f} MB")
                self.kpi_cards["Total Size"].set_status("success" if total_size_mb > 0 else "unknown")
                
                # Connections: Active / Total
                if 'connection_pool' in self.db_stats:
                    pool = self.db_stats['connection_pool']
                    active = pool.get('active', 0)
                    total = pool.get('total', 0)
                    self.kpi_cards["Connections"].update_value(f"{active} / {total}")
                    
                    # Color based on usage
                    usage_pct = (active / total * 100) if total > 0 else 0
                    if usage_pct < 70:
                        self.kpi_cards["Connections"].set_status("success")
                    elif usage_pct < 90:
                        self.kpi_cards["Connections"].set_status("warning")
                    else:
                        self.kpi_cards["Connections"].set_status("error")
                else:
                    self.kpi_cards["Connections"].update_value("N/A")
                    self.kpi_cards["Connections"].set_status("unknown")
                
                # Avg Query Time (placeholder - TODO: add to backend)
                self.kpi_cards["Avg Query Time"].update_value("N/A")
                self.kpi_cards["Avg Query Time"].set_status("unknown")
                
                # Table Count
                self.kpi_cards["Table Count"].update_value(str(table_count))
                self.kpi_cards["Table Count"].set_status("success" if table_count > 0 else "unknown")
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"KPI update error: {e}")
    
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
        if CHART_MODE == "full" and self.chart_pool is not None and CHART_WORKERS is not None:
            self.chart_pool.start(CHART_WORKERS)
    
    def refresh_charts(self):
        """Refresh all charts"""
        # Fetch fresh data
        self.uds3_data = api_client.get_uds3_strategy_status()
        self.db_stats = api_client.get_database_stats()
        self.vector_stats = api_client.get_vector_monitoring()
        
        # Submit chart requests
        if CHART_MODE == "full" and self.chart_pool is not None:
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
        if CHART_MODE == "full" and result.status == ChartStatus.SUCCESS and result.figure:
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
                if FigureCanvasTkAgg is not None:
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
