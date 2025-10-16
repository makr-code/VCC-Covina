"""
Ingestion Monitoring & Upload View
===================================

Dokument-Upload, Job-Monitoring und Pipeline-Status

✨ NEW: Real-Time WebSocket Updates (fallback zu Polling bei Fehler)
🎯 ENHANCED (12. Oktober 2025):
+ 2 Matplotlib Charts: INGESTION_TIMELINE, PROCESSING_RATE
  (moved from Home Dashboard for better performance)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict, Any, List
from pathlib import Path
import threading
import time
import logging  # ✅ FIX: Add missing logging import
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from frontend.config import COLORS, FONTS
from frontend.services.api_client import api_client, ingestion_api_client
from frontend.services.websocket_client import create_job_monitor_client
from frontend.core.chart_threading import ChartThreadPool, ChartType, ChartResult, ChartStatus
from frontend.core.chart_workers import CHART_WORKERS
from frontend.widgets.bulk_copy_progress_modal import BulkCopyProgressModal  # 🆕 NEW!
from frontend.widgets.upload_method_dialog import show_upload_dialog  # 🆕 NEW: Multi-method upload

# ✅ FIX: Initialize logger
logger = logging.getLogger(__name__)


class IngestionView(ttk.Frame):
    """Ingestion Monitoring & Upload View"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        self.db_stats: Optional[Dict[str, Any]] = None
        self.selected_files: List[str] = []
        self.active_jobs: List[Dict[str, Any]] = []
        
        # WebSocket Client for Real-Time Updates
        self.ws_client = None
        self.ws_enabled = True  # Try WebSocket first
        self.job_polling_active = False  # Fallback polling
        
        # Chart Thread Pool (3 workers: 2 charts + 1 refresh)
        self.chart_pool = ChartThreadPool(num_workers=3)
        self.canvases: Dict[tuple, FigureCanvasTkAgg] = {}
        
        # Chart Layout (1×2 Grid)
        self.chart_layout = {
            (0, 0): ChartType.INGESTION_TIMELINE,     # Line Chart
            (0, 1): ChartType.PROCESSING_RATE,        # Gauge Chart
        }
        
        self._create_widgets()
        self._setup_websocket()
        self._start_chart_pool()
        
        # Initial chart refresh (delayed)
        self.after(3000, self.refresh_charts)
    
    def _create_widgets(self):
        """Create widgets"""
        # Title with connection status
        title_frame = ttk.Frame(self)
        title_frame.pack(pady=10, anchor=tk.W, padx=20, fill=tk.X)
        
        title = ttk.Label(title_frame, text="📤 Document Ingestion & Upload", style='Title.TLabel')
        title.pack(side=tk.LEFT)
        
        # Connection Status Indicator
        self.connection_status_label = ttk.Label(
            title_frame, 
            text="🔌 Connecting...", 
            style='Body.TLabel',
            foreground='gray'
        )
        self.connection_status_label.pack(side=tk.RIGHT, padx=10)
        
        # Main container with two columns
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # LEFT COLUMN: Upload Controls
        left_frame = ttk.LabelFrame(main_container, text="Upload Controls", padding=15)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self._create_upload_controls(left_frame)
        
        # RIGHT COLUMN: Active Jobs
        right_frame = ttk.LabelFrame(main_container, text="Active Jobs", padding=15)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self._create_jobs_panel(right_frame)
        
        # BOTTOM: Pipeline Statistics
        stats_frame = ttk.LabelFrame(self, text="Pipeline Statistics", padding=15)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self._create_stats_panel(stats_frame)
        
        # ========================================================================
        # CHARTS SECTION (Moved from Home Dashboard)
        # ========================================================================
        charts_separator = ttk.Separator(self, orient='horizontal')
        charts_separator.pack(fill=tk.X, padx=20, pady=10)
        
        charts_title = ttk.Label(self, text="📊 Ingestion Analytics Charts", style='Subtitle.TLabel')
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
    
    def _create_upload_controls(self, parent):
        """Create upload control buttons and file selection"""
        # File Upload Section
        file_section = ttk.LabelFrame(parent, text="File Upload", padding=10)
        file_section.pack(fill=tk.X, pady=(0, 10))
        
        # File selection
        self.selected_files_label = ttk.Label(file_section, text="No files selected", style='Body.TLabel')
        self.selected_files_label.pack(anchor=tk.W, pady=5)
        
        btn_frame = ttk.Frame(file_section)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="📁 Browse Files", command=self.select_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="🚀 Upload Files", command=self.upload_files).pack(side=tk.LEFT)
        
        # Directory Upload Section
        dir_section = ttk.LabelFrame(parent, text="Directory Upload", padding=10)
        dir_section.pack(fill=tk.X, pady=10)
        
        self.dir_path_var = tk.StringVar(value="No directory selected")
        ttk.Label(dir_section, textvariable=self.dir_path_var, style='Body.TLabel').pack(anchor=tk.W, pady=5)
        
        dir_btn_frame = ttk.Frame(dir_section)
        dir_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(dir_btn_frame, text="📂 Browse Directory", command=self.select_directory).pack(side=tk.LEFT, padx=(0, 5))
        
        # Chunk size setting
        chunk_frame = ttk.Frame(dir_section)
        chunk_frame.pack(fill=tk.X, pady=5)
        ttk.Label(chunk_frame, text="Chunk Size:", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        self.chunk_size_var = tk.StringVar(value="50")
        ttk.Entry(chunk_frame, textvariable=self.chunk_size_var, width=10).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(dir_btn_frame, text="🚀 Upload Directory", command=self.upload_directory).pack(side=tk.LEFT)
        
        # Backend Status
        status_frame = ttk.LabelFrame(parent, text="Backend Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.backend_status_label = ttk.Label(status_frame, text="Checking...", style='Body.TLabel')
        self.backend_status_label.pack(anchor=tk.W, pady=5)
        
        ttk.Button(status_frame, text="🔄 Refresh Status", command=self.check_backend_status).pack(anchor=tk.W)
        
        # Check backend status on init
        self.after(500, self.check_backend_status)
    
    def _create_jobs_panel(self, parent):
        """Create active jobs monitoring panel"""
        # Scrollbar
        scrollbar = ttk.Scrollbar(parent)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview for jobs
        columns = ("Job ID", "Status", "Files", "Progress")
        self.jobs_tree = ttk.Treeview(parent, columns=columns, show='headings',
                                     yscrollcommand=scrollbar.set, height=12)
        
        self.jobs_tree.heading("Job ID", text="Job ID")
        self.jobs_tree.heading("Status", text="Status")
        self.jobs_tree.heading("Files", text="Files")
        self.jobs_tree.heading("Progress", text="Progress")
        
        self.jobs_tree.column("Job ID", width=250)
        self.jobs_tree.column("Status", width=100)
        self.jobs_tree.column("Files", width=80)
        self.jobs_tree.column("Progress", width=100)
        
        self.jobs_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.jobs_tree.yview)
        
        # Context menu
        self.jobs_tree.bind("<Double-Button-1>", self.show_job_details)
        
        # Refresh button
        ttk.Button(parent, text="🔄 Refresh Jobs", command=self.refresh_jobs).pack(pady=(10, 0))
    
    def _create_stats_panel(self, parent):
        """Create pipeline statistics panel"""
        stats_grid = ttk.Frame(parent)
        stats_grid.pack()
        
        self.total_label = ttk.Label(stats_grid, text="Total Processed: N/A", style='Body.TLabel')
        self.total_label.grid(row=0, column=0, padx=20, pady=5)
        
        self.rate_label = ttk.Label(stats_grid, text="Processing Rate: N/A", style='Body.TLabel')
        self.rate_label.grid(row=0, column=1, padx=20, pady=5)
        
        self.status_label = ttk.Label(stats_grid, text="Status: Idle", style='Body.TLabel')
        self.status_label.grid(row=0, column=2, padx=20, pady=5)
    
    # ========================================================================
    # FILE/DIRECTORY SELECTION
    # ========================================================================
    
    def select_files(self):
        """Select files for upload"""
        files = filedialog.askopenfilenames(
            title="Select Documents to Upload",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx *.doc"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if files:
            self.selected_files = list(files)
            count = len(files)
            total_size = sum(Path(f).stat().st_size for f in files if Path(f).exists())
            size_mb = total_size / (1024 * 1024)
            
            self.selected_files_label.config(text=f"✅ {count} files selected ({size_mb:.1f} MB)")
        else:
            self.selected_files = []
            self.selected_files_label.config(text="No files selected")
    
    def select_directory(self):
        """Select directory for batch upload"""
        directory = filedialog.askdirectory(title="Select Directory for Batch Upload")
        
        if directory:
            self.dir_path_var.set(directory)
        else:
            self.dir_path_var.set("No directory selected")
    
    # ========================================================================
    # UPLOAD OPERATIONS
    # ========================================================================
    
    def upload_files(self):
        """Upload selected files with method selection dialog"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select files first")
            return
        
        # Show upload method selection dialog
        selected_method = show_upload_dialog(self, self.selected_files)
        
        if selected_method:
            # Refresh jobs list after upload
            self.after(2000, self.refresh_jobs)
    
    def upload_directory(self):
        """🆕 Upload directory with PROGRESS MODAL (async with real-time tracking)"""
        directory = self.dir_path_var.get()
        
        if directory == "No directory selected":
            messagebox.showwarning("No Directory", "Please select a directory first")
            return
        
        try:
            chunk_size = int(self.chunk_size_var.get())
        except ValueError:
            messagebox.showerror("Invalid Chunk Size", "Chunk size must be a number")
            return
        
        # Perform upload in background thread
        def upload_thread():
            try:
                # Phase 1: Start scan (instant response!)
                result = ingestion_api_client.upload_directory(directory, chunk_size)
                
                if result and "error" not in result:
                    scan_job_id = result.get("scan_job_id")
                    
                    logger.info(f"📦 Directory scan started: {scan_job_id}")
                    
                    # 🆕 Show Progress Modal (main thread)
                    def show_modal():
                        modal = BulkCopyProgressModal(
                            parent=self.winfo_toplevel(),
                            scan_job_id=scan_job_id,
                            backend_url="http://127.0.0.1:45679",
                            on_complete=lambda: self._on_bulk_copy_complete(scan_job_id),
                            on_cancel=lambda: logger.info(f"User cancelled scan: {scan_job_id}")
                        )
                        modal.start_monitoring()
                        
                        # Show info message
                        messagebox.showinfo(
                            "Directory Scan Started",
                            f"✅ Directory scan started!\n\n"
                            f"Scan Job ID: {scan_job_id}\n"
                            f"Directory: {directory}\n\n"
                            f"Progress modal is monitoring the bulk copy.\n"
                            f"You can hide it and continue working."
                        )
                    
                    self.after(0, show_modal)
                    
                    # Phase 2: Poll scan status (for job creation after bulk copy)
                    self._poll_scan_status(scan_job_id)
                
                else:
                    error_msg = result.get("message", "Unknown error") if result else "No response"
                    self.after(0, lambda: messagebox.showerror(
                        "Scan Failed",
                        f"❌ Directory scan failed:\n{error_msg}"
                    ))
            
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Upload Error",
                    f"❌ Error during directory upload:\n{str(e)}"
                ))
        
        threading.Thread(target=upload_thread, daemon=True).start()
    
    def _poll_scan_status(self, scan_job_id: str):
        """Poll scan status until complete"""
        import time
        
        def poll_thread():
            last_status = None
            last_files_found = 0
            
            while True:
                try:
                    status = ingestion_api_client.get_scan_status(scan_job_id)
                    
                    # ✅ FIX: Check if status is None or contains actual error
                    if not status:
                        logger.error(f"Scan status is None for {scan_job_id}")
                        break
                    
                    scan_status = status.get("status")
                    files_found = status.get("files_found", 0)
                    upload_jobs = status.get("upload_jobs_created", 0)
                    elapsed = status.get("elapsed_time", 0)
                    error = status.get("error")
                    
                    # ✅ FIX: Only log error if scan_status is "error" or error field has value
                    if scan_status == "error" and error:
                        logger.error(f"Scan failed: {error}")
                        break
                    
                    # Log progress changes
                    if scan_status != last_status or files_found != last_files_found:
                        logger.info(f"[SCAN {scan_job_id[:8]}] Status: {scan_status}, Files: {files_found}, Jobs: {upload_jobs}, Elapsed: {elapsed:.1f}s")
                        last_status = scan_status
                        last_files_found = files_found
                    
                    # Check if completed or error
                    if scan_status == "completed":
                        # Show final notification
                        self.after(0, lambda f=files_found, j=upload_jobs: messagebox.showinfo(
                            "Directory Scan Complete",
                            f"✅ Scan completed!\n\n"
                            f"Files found: {f}\n"
                            f"Upload jobs created: {j}\n"
                            f"Elapsed time: {elapsed:.1f}s\n\n"
                            f"Check Active Jobs panel for processing status."
                        ))
                        
                        # Refresh jobs list
                        self.after(0, self.refresh_jobs)
                        break
                    
                    elif scan_status == "error":
                        # Show error notification
                        self.after(0, lambda e=error: messagebox.showerror(
                            "Scan Error",
                            f"❌ Directory scan failed:\n\n{e}"
                        ))
                        break
                    
                    # Poll interval (2 seconds)
                    time.sleep(2)
                
                except Exception as e:
                    logger.error(f"Scan status poll error: {e}")
                    break
        
        threading.Thread(target=poll_thread, daemon=True).start()
    
    def _on_bulk_copy_complete(self, scan_job_id: str):
        """🆕 Callback when bulk copy completes"""
        logger.info(f"✅ Bulk copy completed for scan job: {scan_job_id}")
        
        # Show notification
        messagebox.showinfo(
            "Bulk Copy Complete",
            f"✅ Network directory copied to local storage!\n\n"
            f"Scan Job ID: {scan_job_id}\n\n"
            f"Now scanning local files...\n"
            f"You will be notified when upload jobs are created."
        )
        
        # Refresh jobs list (scan will continue and create upload jobs)
        self.refresh_jobs()
    
    # ========================================================================
    # JOB MONITORING
    # ========================================================================
    
    def refresh_jobs(self):
        """Refresh active jobs list"""
        def fetch_jobs():
            try:
                result = ingestion_api_client.list_jobs(limit=20)
                
                if result and "error" not in result:
                    # Result is a list of jobs
                    jobs = result if isinstance(result, list) else []
                    self.after(0, lambda: self._update_jobs_display(jobs))
                else:
                    self.after(0, lambda: self._update_jobs_display([]))
            
            except Exception as e:
                print(f"Error fetching jobs: {e}")
                self.after(0, lambda: self._update_jobs_display([]))
        
        threading.Thread(target=fetch_jobs, daemon=True).start()
    
    def _update_jobs_display(self, jobs: List[Dict]):
        """Update jobs treeview"""
        # Clear current items
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        # Add jobs
        for job in jobs:
            job_id = job.get("job_id", "unknown")[:20] + "..."  # Truncate long IDs
            status = job.get("status", "unknown")
            file_count = job.get("file_count", 0)
            progress = job.get("progress", 0.0)
            
            # Color code by status
            if status == "completed":
                tag = "completed"
            elif status == "failed":
                tag = "failed"
            elif status == "processing":
                tag = "processing"
            else:
                tag = "pending"
            
            self.jobs_tree.insert("", tk.END, values=(
                job_id,
                status.upper(),
                file_count,
                f"{progress:.1f}%"
            ), tags=(tag,))
        
        # Configure tags
        self.jobs_tree.tag_configure("completed", foreground="green")
        self.jobs_tree.tag_configure("failed", foreground="red")
        self.jobs_tree.tag_configure("processing", foreground="blue")
        self.jobs_tree.tag_configure("pending", foreground="gray")
    
    def show_job_details(self, event):
        """Show detailed job information"""
        selection = self.jobs_tree.selection()
        if not selection:
            return
        
        item = self.jobs_tree.item(selection[0])
        job_id_short = item['values'][0]
        
        messagebox.showinfo("Job Details", f"Job ID: {job_id_short}\n\nDouble-click to see full details.")
    
    def _start_job_polling(self):
        """Start background job polling"""
        self.job_polling_active = True
        self._poll_jobs()
    
    def _poll_jobs(self):
        """Poll jobs periodically"""
        if self.job_polling_active:
            self.refresh_jobs()
            # Poll every 5 seconds
            self.after(5000, self._poll_jobs)
    
    # ========================================================================
    # WEBSOCKET INTEGRATION (NEW - Real-Time Updates)
    # ========================================================================
    
    def _setup_websocket(self):
        """Setup WebSocket connection for real-time job updates"""
        if not self.ws_enabled:
            # WebSocket disabled, use polling fallback
            self._start_job_polling()
            return
        
        try:
            self.ws_client = create_job_monitor_client(
                on_job_update=self._handle_websocket_message,
                on_connected=self._on_websocket_connected,
                on_disconnected=self._on_websocket_disconnected
            )
            
            # Connect in background thread
            threading.Thread(
                target=self.ws_client.connect,
                daemon=True,
                name="websocket_connector"
            ).start()
            
        except Exception as e:
            print(f"⚠️ WebSocket setup failed: {e}")
            self._fallback_to_polling()
    
    def _handle_websocket_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        msg_type = data.get("type")
        
        if msg_type == "connection":
            # Connection confirmation
            print(f"✅ {data.get('message')}")
        
        elif msg_type == "job_update":
            # Job status update - refresh UI
            self.after(0, self.refresh_jobs)
        
        elif msg_type == "pong":
            # Ping response (connection health check)
            pass
    
    def _on_websocket_connected(self):
        """Called when WebSocket connects successfully (runs in WebSocket thread)"""
        print("✅ WebSocket connected - Real-Time updates active")
        
        # Schedule UI updates in Tkinter main thread
        try:
            self.after(0, self._update_connection_status_connected)
            # Initial jobs refresh (delayed to allow UI to update)
            self.after(100, self.refresh_jobs)
        except RuntimeError as e:
            # Handle case where widget is not yet fully initialized
            logger.warning(f"Could not schedule UI update: {e}")
    
    def _update_connection_status_connected(self):
        """Update UI to show connected status (runs in Tkinter thread)"""
        try:
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.config(
                    text="🟢 Live",
                    foreground='green'
                )
        except Exception as e:
            logger.warning(f"Failed to update connection status: {e}")
    
    def _on_websocket_disconnected(self):
        """Called when WebSocket disconnects (runs in WebSocket thread)"""
        print("❌ WebSocket disconnected - Falling back to polling")
        
        # Schedule UI updates in Tkinter main thread
        try:
            self.after(0, self._update_connection_status_disconnected)
        except RuntimeError as e:
            logger.warning(f"Could not schedule UI update: {e}")
    
    def _update_connection_status_disconnected(self):
        """Update UI to show disconnected status (runs in Tkinter thread)"""
        try:
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.config(
                    text="🟡 Polling Mode",
                    foreground='orange'
                )
        except Exception as e:
            logger.warning(f"Failed to update connection status: {e}")
        
        # Fallback to polling
        self._fallback_to_polling()
    
    def _fallback_to_polling(self):
        """Fallback to 5s polling when WebSocket fails"""
        if not self.job_polling_active:
            self.ws_enabled = False
            self._start_job_polling()
    
    # ========================================================================
    # BACKEND STATUS
    # ========================================================================
    
    def check_backend_status(self):
        """Check Ingestion Backend status"""
        def fetch_status():
            try:
                result = ingestion_api_client.get_health()
                
                if result and "error" not in result:
                    status = result.get("status", "unknown")
                    components = result.get("components", {})
                    workers = result.get("worker_pool", {})
                    
                    status_text = f"✅ Status: {status.upper()}\n"
                    status_text += f"Workers: {workers.get('io_workers', 0)} I/O, {workers.get('cpu_workers', 0)} CPU\n"
                    status_text += f"Databases: {len([k for k, v in components.items() if '✅' in str(v)])} connected"
                    
                    self.after(0, lambda: self.backend_status_label.config(text=status_text))
                else:
                    error_msg = result.get("message", "Unknown error") if result else "Not reachable"
                    self.after(0, lambda: self.backend_status_label.config(
                        text=f"❌ Backend Error: {error_msg}"
                    ))
            
            except Exception as e:
                self.after(0, lambda: self.backend_status_label.config(
                    text=f"❌ Error: {str(e)}"
                ))
        
        threading.Thread(target=fetch_status, daemon=True).start()
    
    
    # ========================================================================
    # LEGACY REFRESH (for pipeline stats from Main Backend)
    # ========================================================================
    
    def refresh(self):
        """Refresh pipeline statistics from Main Backend"""
        self.db_stats = api_client.get_database_stats()
        
        if self.db_stats and "error" not in self.db_stats:
            self._update_stats_display()
    
    def _update_stats_display(self):
        """Update pipeline statistics"""
        if not self.db_stats:
            return
        
        # Update stats
        total = self.db_stats.get("total_documents", 0)
        self.total_label.config(text=f"Total Processed: {total:,}")
        
        # Estimate rate (placeholder - would need time-series data)
        self.rate_label.config(text="Processing Rate: Active")
        self.status_label.config(text="Status: Online")
    
    # ========================================================================
    # CHART POOL METHODS (Moved from Home Dashboard)
    # ========================================================================
    
    def _start_chart_pool(self):
        """Start chart thread pool"""
        self.chart_pool.start(CHART_WORKERS)
    
    def refresh_charts(self):
        """Refresh ingestion charts"""
        # Fetch fresh data
        self.db_stats = api_client.get_database_stats()
        job_data = ingestion_api_client.list_jobs()  # ✅ FIXED: get_jobs() → list_jobs()
        
        # Submit chart requests
        self._submit_chart_requests()
    
    def _submit_chart_requests(self):
        """Submit all chart rendering requests to thread pool"""
        for (row, col), chart_type in self.chart_layout.items():
            chart_id = f"ing_chart_{row}_{col}"
            
            # Prepare data for chart worker
            data = {
                "health": {},
                "uds3": {},
                "db_stats": self.db_stats or {},
                "vector": {},
                "jobs": self.active_jobs
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
                    print(f"⚠️ IngestionView chart pool shutdown error: {e}")
            
            # Disconnect WebSocket
            if hasattr(self, 'ws_client') and self.ws_client:
                try:
                    self.ws_client.disconnect()
                except Exception as e:
                    print(f"⚠️ IngestionView WebSocket disconnect error: {e}")
            
            # Destroy canvases
            if hasattr(self, 'canvases'):
                for canvas in self.canvases.values():
                    try:
                        if hasattr(canvas, 'get_tk_widget'):
                            canvas.get_tk_widget().destroy()
                    except Exception:
                        pass
        except Exception as e:
            print(f"⚠️ IngestionView destroy error: {e}")
        finally:
            try:
                super().destroy()
            except Exception:
                pass

