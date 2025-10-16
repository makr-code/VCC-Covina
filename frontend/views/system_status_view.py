"""
System Status Dashboard View
=============================

Zeigt Backend Health, Uptime, Active Jobs und Database Connections

🎯 ENHANCED (12. Oktober 2025):
+ 2 Matplotlib Charts: BACKEND_MATRIX, SYSTEM_METRICS
  (moved from Home Dashboard for better performance)
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional, Dict, Any
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from frontend.config import COLORS, FONTS
from frontend.services.api_client import api_client
from frontend.core.chart_threading import ChartThreadPool, ChartType, ChartResult, ChartStatus
from frontend.core.chart_workers import CHART_WORKERS


class SystemStatusView(ttk.Frame):
    """System Status Dashboard View + Charts"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        # Data cache
        self.health_data: Optional[Dict[str, Any]] = None
        self.uds3_data: Optional[Dict[str, Any]] = None
        self.connection_status: Optional[Dict[str, Any]] = None
        
        # Chart Thread Pool (3 workers: 2 charts + 1 refresh)
        self.chart_pool = ChartThreadPool(num_workers=3)
        self.canvases: Dict[tuple, FigureCanvasTkAgg] = {}
        
        # Chart Layout (1×2 Grid)
        self.chart_layout = {
            (0, 0): ChartType.BACKEND_MATRIX,         # Heatmap
            (0, 1): ChartType.SYSTEM_METRICS,         # Bar Chart
        }
        
        self._create_widgets()
        self._start_chart_pool()
        
        # Initial refresh (delayed)
        self.after(3000, self.refresh)
    
    def _create_widgets(self):
        """Create all widgets"""
        # Title
        title = ttk.Label(self, text="System Status", style='Title.TLabel')
        title.pack(pady=10, anchor=tk.W, padx=20)
        
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left column: Backend Health
        left_frame = ttk.LabelFrame(main_container, text="Backend Health", padding=15)
        left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5, pady=5)
        
        self.health_status_label = tk.Label(left_frame, 
                                           text="❌ Disconnected",
                                           font=FONTS["title"],
                                           fg=COLORS["error"],
                                           bg=COLORS["panel"])
        self.health_status_label.pack(pady=10)
        
        self.uptime_label = ttk.Label(left_frame, text="Uptime: N/A", style='Body.TLabel')
        self.uptime_label.pack(pady=5)
        
        self.active_jobs_label = ttk.Label(left_frame, text="Active Jobs: N/A", style='Body.TLabel')
        self.active_jobs_label.pack(pady=5)
        
        self.latency_label = ttk.Label(left_frame, text="Latency: N/A", style='Body.TLabel')
        self.latency_label.pack(pady=5)
        
        # Right column: Database Connections
        right_frame = ttk.LabelFrame(main_container, text="Database Connections", padding=15)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5, pady=5)
        
        self.db_status_labels = {}
        db_names = ["PostgreSQL", "Neo4j", "ChromaDB", "CouchDB"]
        
        for idx, db_name in enumerate(db_names):
            frame = ttk.Frame(right_frame)
            frame.pack(fill=tk.X, pady=5)
            
            label = tk.Label(frame,
                           text=f"● {db_name}",
                           font=FONTS["body"],
                           fg=COLORS["warning"],
                           bg=COLORS["panel"],
                           anchor=tk.W)
            label.pack(side=tk.LEFT)
            
            status = ttk.Label(frame, text="Checking...", style='Body.TLabel')
            status.pack(side=tk.RIGHT)
            
            self.db_status_labels[db_name] = (label, status)
        
        # Bottom: UDS3 Status
        bottom_frame = ttk.LabelFrame(main_container, text="UDS3 Framework", padding=15)
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.E, tk.W), padx=5, pady=5)
        
        self.uds3_status_label = ttk.Label(bottom_frame, text="Status: Unknown", style='Body.TLabel')
        self.uds3_status_label.pack(pady=5)
        
        self.uds3_mode_label = ttk.Label(bottom_frame, text="Mode: N/A", style='Body.TLabel')
        self.uds3_mode_label.pack(pady=5)
        
        # Configure grid weights
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=0)
        
        # Refresh button
        refresh_btn = ttk.Button(self, text="Refresh Now", command=self.refresh)
        refresh_btn.pack(pady=10)
        
        # ========================================================================
        # CHARTS SECTION (Moved from Home Dashboard)
        # ========================================================================
        charts_separator = ttk.Separator(self, orient='horizontal')
        charts_separator.pack(fill=tk.X, padx=20, pady=10)
        
        charts_title = ttk.Label(self, text="📊 System Analytics Charts", style='Subtitle.TLabel')
        charts_title.pack(pady=10, anchor=tk.W, padx=20)
        
        # Chart grid container (1×2)
        chart_grid = ttk.Frame(self)
        chart_grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Configure grid weights (2 columns, 1 row)
        for col in range(2):
            chart_grid.grid_columnconfigure(col, weight=1, uniform="col")
        chart_grid.grid_rowconfigure(0, weight=1)
        
        # Create placeholder frames for charts
        for (row, col), chart_type in self.chart_layout.items():
            placeholder = ttk.Frame(chart_grid, relief=tk.SUNKEN, borderwidth=1)
            placeholder.grid(row=row, column=col, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5, pady=5)
            
            # Loading label
            loading_label = ttk.Label(placeholder, text=f"Loading {chart_type.name}...", style='Body.TLabel')
            loading_label.pack(expand=True)
    
    def refresh(self):
        """Refresh all data + charts"""
        # Get connection status
        self.connection_status = api_client.get_connection_status()
        self._update_health_display()
        
        # Get UDS3 status
        self.uds3_data = api_client.get_uds3_strategy_status()
        self._update_uds3_display()
        
        # Refresh charts
        self.refresh_charts()
    
    def _update_health_display(self):
        """Update health status display"""
        if not self.connection_status:
            return
        
        if self.connection_status.get("connected"):
            # Connected
            self.health_status_label.config(
                text="✅ Backend Online",
                fg=COLORS["success"]
            )
            
            # Latency
            latency = self.connection_status.get("latency_ms", 0)
            latency_color = COLORS["success"] if latency < 100 else COLORS["warning"] if latency < 500 else COLORS["error"]
            self.latency_label.config(text=f"Latency: {latency:.1f} ms")
            
            # Active Jobs
            active_jobs = self.connection_status.get("active_jobs", 0)
            self.active_jobs_label.config(text=f"Active Jobs: {active_jobs}")
            
            # Uptime (placeholder - would need backend endpoint)
            self.uptime_label.config(text="Uptime: Connected")
        else:
            # Disconnected
            self.health_status_label.config(
                text=f"❌ {self.connection_status.get('error', 'Disconnected')}",
                fg=COLORS["error"]
            )
            self.latency_label.config(text="Latency: N/A")
            self.active_jobs_label.config(text="Active Jobs: N/A")
            self.uptime_label.config(text="Uptime: N/A")
    
    def _update_uds3_display(self):
        """Update UDS3 and database status display"""
        if not self.uds3_data or "error" in self.uds3_data:
            self.uds3_status_label.config(text="Status: Unavailable")
            self.uds3_mode_label.config(text="Mode: N/A")
            
            # Set all DBs to unknown
            for db_name, (label, status) in self.db_status_labels.items():
                label.config(fg=COLORS["warning"])
                status.config(text="Unknown")
            return
        
        # UDS3 Status
        available = self.uds3_data.get("strategy_available", False)
        self.uds3_status_label.config(
            text=f"Status: {'Available' if available else 'Unavailable'}"
        )
        
        # Backends status
        backends = self.uds3_data.get("backends", {})
        
        db_mapping = {
            "PostgreSQL": "relational",
            "Neo4j": "graph",
            "ChromaDB": "vector",
            "CouchDB": "document"
        }
        
        for db_name, backend_key in db_mapping.items():
            if db_name in self.db_status_labels:
                label, status = self.db_status_labels[db_name]
                
                backend_info = backends.get(backend_key, {})
                is_available = backend_info.get("available", False)
                backend_type = backend_info.get("type", "Unknown")
                
                # Update color
                color = COLORS["success"] if is_available else COLORS["error"]
                label.config(fg=color)
                
                # Update status text
                status_text = f"✓ {backend_type}" if is_available else "✗ Offline"
                status.config(text=status_text)
    
    # ========================================================================
    # CHART POOL METHODS (Moved from Home Dashboard)
    # ========================================================================
    
    def _start_chart_pool(self):
        """Start chart thread pool"""
        self.chart_pool.start(CHART_WORKERS)
    
    def refresh_charts(self):
        """Refresh system charts"""
        # Fetch fresh data
        self.health_data = api_client.get_health()
        self.uds3_data = api_client.get_uds3_strategy_status()
        db_stats = api_client.get_database_stats()
        
        # Submit chart requests
        self._submit_chart_requests()
    
    def _submit_chart_requests(self):
        """Submit all chart rendering requests to thread pool"""
        for (row, col), chart_type in self.chart_layout.items():
            chart_id = f"sys_chart_{row}_{col}"
            
            # Prepare data for chart worker
            data = {
                "health": self.health_data or {},
                "uds3": self.uds3_data or {},
                "db_stats": {},
                "vector": {}
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
            
            # Find grid cell frame (search for chart grid)
            grid_cell = None
            for child in self.winfo_children():
                if isinstance(child, ttk.Frame):
                    # Check if this is the chart grid
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, ttk.Frame):
                            info = grandchild.grid_info()
                            if info.get('row') == row and info.get('column') == col:
                                grid_cell = grandchild
                                break
                    if grid_cell:
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
                    print(f"⚠️ SystemStatusView chart pool shutdown error: {e}")
            
            # Destroy canvases
            if hasattr(self, 'canvases'):
                for canvas in self.canvases.values():
                    try:
                        if hasattr(canvas, 'get_tk_widget'):
                            canvas.get_tk_widget().destroy()
                    except Exception:
                        pass
        except Exception as e:
            print(f"⚠️ SystemStatusView destroy error: {e}")
        finally:
            try:
                super().destroy()
            except Exception:
                pass
