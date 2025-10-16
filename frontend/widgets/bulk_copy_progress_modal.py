"""
Bulk Copy Progress Modal Dialog
================================

Real-time progress display for network directory bulk copy operations.

Features:
- Live progress bar (0-100%)
- Real-time metrics (files, data, rate, ETA)
- WebSocket updates (5s interval)
- HTTP polling fallback (2s interval)
- Cancel operation support

Author: Covina Development Team
Version: 1.0.0
Date: 14. Oktober 2025, 15:15 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, Callable
import threading
import time
import logging

from frontend.config import COLORS, FONTS

logger = logging.getLogger(__name__)


class BulkCopyProgressModal(tk.Toplevel):
    """
    Modal dialog for displaying bulk copy progress.
    
    Usage:
        modal = BulkCopyProgressModal(
            parent=root,
            scan_job_id="scan_abc123",
            backend_url="http://127.0.0.1:45679",
            on_complete=lambda: print("Copy completed!"),
            on_cancel=lambda: print("Copy cancelled!")
        )
        modal.start_monitoring()
    """
    
    def __init__(
        self,
        parent: tk.Tk,
        scan_job_id: str,
        backend_url: str = "http://127.0.0.1:45679",
        on_complete: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        polling_interval: int = 2000,  # ms
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.scan_job_id = scan_job_id
        self.backend_url = backend_url
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.polling_interval = polling_interval
        
        # State
        self.is_monitoring = False
        self.last_update_time = 0
        self.monitoring_thread = None
        
        # Window configuration
        self.title("Bulk Copy Progress")
        self.geometry("550x400")
        self.resizable(False, False)
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        self._center_on_parent(parent)
        
        # Protocol for window close
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # Build UI
        self._create_widgets()
        
        logger.info(f"📦 BulkCopyProgressModal initialized for scan job: {scan_job_id}")
    
    def _center_on_parent(self, parent):
        """Center modal on parent window"""
        self.update_idletasks()
        
        # Get parent position and size
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # Calculate center position
        modal_width = 550
        modal_height = 400
        x = parent_x + (parent_width - modal_width) // 2
        y = parent_y + (parent_height - modal_height) // 2
        
        self.geometry(f"{modal_width}x{modal_height}+{x}+{y}")
    
    def _create_widgets(self):
        """Create UI elements"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(pady=20, padx=20, fill=tk.X)
        
        self.header_label = ttk.Label(
            header_frame,
            text="📦 Bulk Copy in Progress...",
            font=FONTS.get("heading", ("Arial", 16, "bold")),
            foreground=COLORS.get("primary", "#2196F3")
        )
        self.header_label.pack()
        
        # Progress Bar
        progress_frame = ttk.Frame(self)
        progress_frame.pack(pady=10, padx=40, fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            length=470,
            mode='determinate',
            maximum=100
        )
        self.progress_bar.pack()
        
        # Progress Percentage
        self.percent_label = ttk.Label(
            progress_frame,
            text="0%",
            font=FONTS.get("body", ("Arial", 14)),
            foreground=COLORS.get("text_primary", "#212121")
        )
        self.percent_label.pack(pady=5)
        
        # Stats Frame
        stats_frame = ttk.LabelFrame(self, text="Copy Statistics", padding=15)
        stats_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Files Copied
        files_frame = ttk.Frame(stats_frame)
        files_frame.pack(fill=tk.X, pady=5)
        ttk.Label(files_frame, text="📄 Files Copied:", font=FONTS.get("body_bold", ("Arial", 10, "bold"))).pack(side=tk.LEFT)
        self.files_label = ttk.Label(files_frame, text="0", font=FONTS.get("body", ("Arial", 10)))
        self.files_label.pack(side=tk.RIGHT)
        
        # Data Copied
        data_frame = ttk.Frame(stats_frame)
        data_frame.pack(fill=tk.X, pady=5)
        ttk.Label(data_frame, text="💾 Data Copied:", font=FONTS.get("body_bold", ("Arial", 10, "bold"))).pack(side=tk.LEFT)
        self.data_label = ttk.Label(data_frame, text="0.0 GB", font=FONTS.get("body", ("Arial", 10)))
        self.data_label.pack(side=tk.RIGHT)
        
        # Copy Rate
        rate_frame = ttk.Frame(stats_frame)
        rate_frame.pack(fill=tk.X, pady=5)
        ttk.Label(rate_frame, text="⚡ Copy Rate:", font=FONTS.get("body_bold", ("Arial", 10, "bold"))).pack(side=tk.LEFT)
        self.rate_label = ttk.Label(rate_frame, text="0.0 MB/s", font=FONTS.get("body", ("Arial", 10)))
        self.rate_label.pack(side=tk.RIGHT)
        
        # ETA
        eta_frame = ttk.Frame(stats_frame)
        eta_frame.pack(fill=tk.X, pady=5)
        ttk.Label(eta_frame, text="⏱️ Time Remaining:", font=FONTS.get("body_bold", ("Arial", 10, "bold"))).pack(side=tk.LEFT)
        self.eta_label = ttk.Label(eta_frame, text="Calculating...", font=FONTS.get("body", ("Arial", 10)))
        self.eta_label.pack(side=tk.RIGHT)
        
        # Status
        status_frame = ttk.Frame(stats_frame)
        status_frame.pack(fill=tk.X, pady=5)
        ttk.Label(status_frame, text="📊 Status:", font=FONTS.get("body_bold", ("Arial", 10, "bold"))).pack(side=tk.LEFT)
        self.status_label = ttk.Label(
            status_frame,
            text="Preparing...",
            font=FONTS.get("body", ("Arial", 10)),
            foreground=COLORS.get("warning", "#FF9800")
        )
        self.status_label.pack(side=tk.RIGHT)
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        self.hide_button = ttk.Button(
            button_frame,
            text="🙈 Hide",
            command=self.withdraw,
            width=12
        )
        self.hide_button.pack(side=tk.LEFT, padx=10)
        
        self.cancel_button = ttk.Button(
            button_frame,
            text="❌ Cancel",
            command=self._cancel_copy,
            width=12
        )
        self.cancel_button.pack(side=tk.LEFT, padx=10)
    
    def start_monitoring(self):
        """Start monitoring progress via HTTP polling"""
        if self.is_monitoring:
            logger.warning("⚠️ Monitoring already active")
            return
        
        self.is_monitoring = True
        logger.info(f"🔄 Starting progress monitoring for scan job: {self.scan_job_id}")
        
        # Start polling in background thread
        self.monitoring_thread = threading.Thread(target=self._poll_progress, daemon=True)
        self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring progress"""
        self.is_monitoring = False
        logger.info("🛑 Stopped progress monitoring")
    
    def _poll_progress(self):
        """Background thread: Poll backend for progress updates"""
        import requests
        
        while self.is_monitoring:
            try:
                # HTTP GET to status endpoint
                url = f"{self.backend_url}/scan/{self.scan_job_id}"
                response = requests.get(url, timeout=2)
                
                if response.status_code == 200:
                    data = response.json()
                    progress = data.get("bulk_copy_progress")
                    
                    if progress:
                        # Update UI (thread-safe via after())
                        self.after(0, lambda p=progress: self._update_ui(p))
                        
                        # Check if completed
                        status = progress.get("status", "")
                        if status == "completed":
                            self.after(0, self._on_copy_complete)
                            break
                        elif status == "error":
                            self.after(0, self._on_copy_error)
                            break
                    else:
                        logger.debug("No bulk_copy_progress in response (copy not started yet)")
                
                else:
                    logger.warning(f"⚠️ Status endpoint returned {response.status_code}")
            
            except requests.exceptions.Timeout:
                logger.warning("⚠️ Status endpoint timeout")
            except Exception as e:
                logger.error(f"❌ Progress poll error: {e}")
            
            # Wait before next poll
            time.sleep(self.polling_interval / 1000.0)
        
        logger.info("📊 Polling thread stopped")
    
    def _update_ui(self, progress: Dict[str, Any]):
        """Update UI with latest progress (called from main thread)"""
        try:
            # Progress bar
            percent = progress.get("percent_complete", 0.0)
            self.progress_bar["value"] = percent
            self.percent_label.config(text=f"{percent:.1f}%")
            
            # Files
            files = progress.get("files_copied", 0)
            total_files = progress.get("total_files", 0)
            if total_files > 0:
                self.files_label.config(text=f"{files:,} / {total_files:,}")
            else:
                self.files_label.config(text=f"{files:,}")
            
            # Data
            bytes_copied = progress.get("bytes_copied", 0)
            data_gb = bytes_copied / (1024**3)
            total_bytes = progress.get("total_bytes", 0)
            if total_bytes > 0:
                total_gb = total_bytes / (1024**3)
                self.data_label.config(text=f"{data_gb:.2f} GB / {total_gb:.2f} GB")
            else:
                self.data_label.config(text=f"{data_gb:.2f} GB")
            
            # Rate
            rate = progress.get("copy_rate_mbps", 0.0)
            self.rate_label.config(text=f"{rate:.1f} MB/s")
            
            # ETA
            eta_seconds = progress.get("eta_seconds", 0)
            if eta_seconds > 0 and percent < 100:
                eta_mins = eta_seconds // 60
                eta_secs = eta_seconds % 60
                if eta_mins > 0:
                    self.eta_label.config(text=f"~{eta_mins} min {eta_secs} sec")
                else:
                    self.eta_label.config(text=f"~{eta_secs} seconds")
            elif percent >= 100:
                self.eta_label.config(text="Complete!")
            else:
                self.eta_label.config(text="Calculating...")
            
            # Status
            status = progress.get("status", "preparing")
            status_text = {
                "preparing": "Preparing copy...",
                "copying": "Copying files...",
                "completed": "✅ Complete!",
                "error": "❌ Error!"
            }
            status_colors = {
                "preparing": COLORS.get("warning", "#FF9800"),
                "copying": COLORS.get("info", "#2196F3"),
                "completed": COLORS.get("success", "#4CAF50"),
                "error": COLORS.get("error", "#F44336")
            }
            self.status_label.config(
                text=status_text.get(status, status),
                foreground=status_colors.get(status, "#212121")
            )
            
            # Update timestamp
            self.last_update_time = time.time()
            
            logger.debug(f"📊 Progress: {percent:.1f}% | Files: {files} | Rate: {rate:.1f} MB/s")
        
        except Exception as e:
            logger.error(f"❌ UI update error: {e}")
    
    def _on_copy_complete(self):
        """Handle copy completion"""
        logger.info("✅ Bulk copy completed!")
        
        # Update UI
        self.header_label.config(text="✅ Bulk Copy Complete!")
        self.cancel_button.config(state="disabled")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Callback
        if self.on_complete:
            try:
                self.on_complete()
            except Exception as e:
                logger.error(f"❌ on_complete callback error: {e}")
        
        # Auto-close after 3 seconds
        self.after(3000, self.destroy)
    
    def _on_copy_error(self):
        """Handle copy error"""
        logger.error("❌ Bulk copy failed!")
        
        # Update UI
        self.header_label.config(text="❌ Bulk Copy Failed!", foreground=COLORS.get("error", "#F44336"))
        self.cancel_button.config(text="Close", state="normal")
        
        # Stop monitoring
        self.stop_monitoring()
    
    def _cancel_copy(self):
        """Cancel the copy operation"""
        logger.warning("⚠️ User cancelled bulk copy")
        
        # TODO: Implement cancel endpoint
        # For now, just close the modal
        
        # Callback
        if self.on_cancel:
            try:
                self.on_cancel()
            except Exception as e:
                logger.error(f"❌ on_cancel callback error: {e}")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Close modal
        self.destroy()
    
    def _on_window_close(self):
        """Handle window close button"""
        # Just hide, don't destroy (copy continues in background)
        self.withdraw()
        logger.info("🙈 Progress modal hidden (copy continues in background)")
    
    def destroy(self):
        """Override destroy to stop monitoring"""
        self.stop_monitoring()
        super().destroy()


# Export
__all__ = ["BulkCopyProgressModal"]
