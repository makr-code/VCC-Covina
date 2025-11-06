"""
Data Transformation Admin Tool
===============================

GUI Tool to manage data transformation jobs:
- Transform existing data to new formats
- Monitor transformation progress
- View job history and errors

Author: GitHub Copilot
Date: 31. Oktober 2025
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional


class DataTransformationGUI:
    """GUI for managing data transformation jobs"""
    
    def __init__(self, backend_url: str = "http://127.0.0.1:45678"):
        self.backend_url = backend_url.rstrip("/")
        self.current_job_id: Optional[str] = None
        self.monitoring_active = False
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Data Transformation Tool - Covina Admin")
        self.root.geometry("1200x800")
        
        # Create UI
        self._create_ui()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitor_job, daemon=True)
        self.monitoring_thread.start()
    
    def _create_ui(self):
        """Create main UI layout"""
        # Top frame: Configuration
        config_frame = ttk.LabelFrame(self.root, text="Transformation Configuration", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Transformation Type
        ttk.Label(config_frame, text="Transformation Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar(value="polyglot")
        type_combo = ttk.Combobox(config_frame, textvariable=self.type_var, width=30)
        type_combo['values'] = ("polyglot", "couchdb_migration", "embedding_regeneration", "graph_rebuild")
        type_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Scope
        ttk.Label(config_frame, text="Scope:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.scope_var = tk.StringVar(value="all")
        scope_combo = ttk.Combobox(config_frame, textvariable=self.scope_var, width=30)
        scope_combo['values'] = ("all", "by_ids", "since", "range")
        scope_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Batch Size
        ttk.Label(config_frame, text="Batch Size:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.batch_size_var = tk.StringVar(value="100")
        ttk.Entry(config_frame, textvariable=self.batch_size_var, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Limit
        ttk.Label(config_frame, text="Limit (optional):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.limit_var = tk.StringVar(value="")
        ttk.Entry(config_frame, textvariable=self.limit_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Dry Run
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(config_frame, text="Dry Run (Preview Mode)", variable=self.dry_run_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="▶ Start Transformation", command=self._start_transformation).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="⏹ Cancel Job", command=self._cancel_job).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Refresh Status", command=self._refresh_status).pack(side=tk.LEFT, padx=5)
        
        # Middle frame: Progress
        progress_frame = ttk.LabelFrame(self.root, text="Job Progress", padding=10)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Job ID
        ttk.Label(progress_frame, text="Job ID:").grid(row=0, column=0, sticky=tk.W)
        self.job_id_label = ttk.Label(progress_frame, text="No job running", foreground="gray")
        self.job_id_label.grid(row=0, column=1, sticky=tk.W)
        
        # Status
        ttk.Label(progress_frame, text="Status:").grid(row=1, column=0, sticky=tk.W)
        self.status_label = ttk.Label(progress_frame, text="idle", foreground="gray")
        self.status_label.grid(row=1, column=1, sticky=tk.W)
        
        # Progress Bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.grid(row=2, column=0, columnspan=2, pady=10, sticky=tk.EW)
        
        # Stats
        stats_subframe = ttk.Frame(progress_frame)
        stats_subframe.grid(row=3, column=0, columnspan=2, sticky=tk.EW)
        
        ttk.Label(stats_subframe, text="Total:").pack(side=tk.LEFT, padx=5)
        self.total_label = ttk.Label(stats_subframe, text="0")
        self.total_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_subframe, text="Processed:").pack(side=tk.LEFT, padx=5)
        self.processed_label = ttk.Label(stats_subframe, text="0")
        self.processed_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_subframe, text="Succeeded:").pack(side=tk.LEFT, padx=5)
        self.succeeded_label = ttk.Label(stats_subframe, text="0", foreground="green")
        self.succeeded_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_subframe, text="Failed:").pack(side=tk.LEFT, padx=5)
        self.failed_label = ttk.Label(stats_subframe, text="0", foreground="red")
        self.failed_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_subframe, text="Skipped:").pack(side=tk.LEFT, padx=5)
        self.skipped_label = ttk.Label(stats_subframe, text="0", foreground="orange")
        self.skipped_label.pack(side=tk.LEFT, padx=5)
        
        # Bottom frame: Logs
        log_frame = ttk.LabelFrame(self.root, text="Job Logs & Errors", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def _start_transformation(self):
        """Start a new transformation job"""
        try:
            # Build request
            request_data = {
                "transformation_type": self.type_var.get(),
                "scope": self.scope_var.get(),
                "batch_size": int(self.batch_size_var.get()),
                "dry_run": self.dry_run_var.get()
            }
            
            if self.limit_var.get():
                request_data["limit"] = int(self.limit_var.get())
            
            # Send request
            self._log(f"🚀 Starting transformation: {request_data['transformation_type']}")
            
            response = requests.post(
                f"{self.backend_url}/maintenance/transform",
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.current_job_id = result.get("job_id")
                self.monitoring_active = True
                
                self._log(f"✅ Job started: {self.current_job_id}")
                self.job_id_label.config(text=self.current_job_id, foreground="blue")
                
                messagebox.showinfo("Success", f"Transformation job started!\nJob ID: {self.current_job_id}")
            else:
                self._log(f"❌ Error: {response.status_code} - {response.text}")
                messagebox.showerror("Error", f"Failed to start job: {response.text}")
        
        except Exception as e:
            self._log(f"❌ Exception: {e}")
            messagebox.showerror("Error", str(e))
    
    def _cancel_job(self):
        """Cancel the current job"""
        if not self.current_job_id:
            messagebox.showwarning("No Job", "No job is currently running")
            return
        
        try:
            response = requests.post(
                f"{self.backend_url}/maintenance/transform/{self.current_job_id}/cancel",
                timeout=10
            )
            
            if response.status_code == 200:
                self._log(f"⚠️ Job cancelled: {self.current_job_id}")
                messagebox.showinfo("Cancelled", "Job cancellation requested")
            else:
                messagebox.showerror("Error", f"Failed to cancel job: {response.text}")
        
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _refresh_status(self):
        """Manually refresh job status"""
        if not self.current_job_id:
            messagebox.showwarning("No Job", "No job is currently running")
            return
        
        self._update_job_status()
    
    def _monitor_job(self):
        """Background thread to monitor job progress"""
        while True:
            if self.monitoring_active and self.current_job_id:
                try:
                    self._update_job_status()
                except Exception as e:
                    self._log(f"❌ Monitoring error: {e}")
            
            time.sleep(2)  # Poll every 2 seconds
    
    def _update_job_status(self):
        """Fetch and update job status"""
        try:
            response = requests.get(
                f"{self.backend_url}/maintenance/transform/{self.current_job_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                job_data = response.json()
                
                # Update status
                status = job_data.get("status", "unknown")
                self.status_label.config(text=status)
                
                if status == "running":
                    self.status_label.config(foreground="blue")
                elif status == "completed":
                    self.status_label.config(foreground="green")
                    self.monitoring_active = False
                elif status == "failed":
                    self.status_label.config(foreground="red")
                    self.monitoring_active = False
                elif status == "cancelled":
                    self.status_label.config(foreground="orange")
                    self.monitoring_active = False
                
                # Update progress
                progress = job_data.get("progress", {})
                total = progress.get("total", 0)
                processed = progress.get("processed", 0)
                succeeded = progress.get("succeeded", 0)
                failed = progress.get("failed", 0)
                skipped = progress.get("skipped", 0)
                percentage = progress.get("percentage", 0)
                
                self.progress_var.set(percentage)
                self.total_label.config(text=str(total))
                self.processed_label.config(text=str(processed))
                self.succeeded_label.config(text=str(succeeded))
                self.failed_label.config(text=str(failed))
                self.skipped_label.config(text=str(skipped))
                
                # Update errors
                errors = job_data.get("errors", [])
                if errors:
                    self._log(f"⚠️ Recent errors: {len(errors)}")
                    for error in errors[-5:]:  # Last 5 errors
                        self._log(f"  • {error.get('document_id', 'N/A')}: {error.get('error', 'Unknown')}")
        
        except Exception as e:
            # Silently ignore monitoring errors
            pass
    
    def _log(self, message: str):
        """Add log message to log text area"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def run(self):
        """Start the GUI main loop"""
        self._log("✅ Data Transformation Tool started")
        self._log(f"🔗 Backend URL: {self.backend_url}")
        self.root.mainloop()


if __name__ == "__main__":
    app = DataTransformationGUI()
    app.run()
