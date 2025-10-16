"""
Recovery View - Phase 3: View Migration

View for failed file recovery management.
Integrates with Recovery System v3.4.8.

Features:
- List failed files with retry counts
- Recover failed files (with safety checks)
- View blocked files (max retries exceeded)
- Admin override for unblocking files
- System-wide recovery audit

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 3)
Date: 14.10.2025, 10:35 Uhr
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
from datetime import datetime

from frontend.views.base_view import BaseView
from frontend.core.event_bus import EventType
from frontend.core.task_executor import Task


class RecoveryView(BaseView):
    """
    Recovery View für Failed File Recovery Management.
    
    Features:
    - Failed Files List (mit Retry Counts)
    - Recover Button (mit Safety Checks)
    - Blocked Files Audit
    - Admin Override Option
    
    Integration mit Recovery System v3.4.8:
    - GET /jobs/{job_id}/failed-files
    - POST /jobs/{job_id}/recover-failed-files
    - POST /jobs/{job_id}/files/{file_path}/unblock?admin_override=true
    - GET /recovery/blocked-files
    """
    
    def __init__(self, parent, event_bus, backend_service, **kwargs):
        self.backend_service = backend_service
        self._failed_files: List[Dict[str, Any]] = []
        self._blocked_files: List[Dict[str, Any]] = []
        self._selected_job_id: Optional[str] = None
        super().__init__(parent, event_bus, **kwargs)
    
    def build_ui(self):
        """Build Recovery View UI (Pure UI construction)."""
        # Main container with padding
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        self._build_header(main_frame)
        
        # Job Selection Section
        self._build_job_selection(main_frame)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(10, 0))
        
        # Tab 1: Failed Files
        self.failed_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.failed_tab, text="❌ Failed Files")
        self._build_failed_files_tab(self.failed_tab)
        
        # Tab 2: Blocked Files Audit
        self.blocked_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.blocked_tab, text="🚫 Blocked Files")
        self._build_blocked_files_tab(self.blocked_tab)
    
    def _build_header(self, parent):
        """Build header section."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text="🔧 Recovery Management",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(side="left")
        
        # Status indicator
        self.status_label = ttk.Label(
            header_frame,
            text="⚪ Ready",
            font=("Segoe UI", 10)
        )
        self.status_label.pack(side="right", padx=10)
        
        # Refresh button
        refresh_btn = ttk.Button(
            header_frame,
            text="🔄 Refresh",
            command=self._on_refresh_clicked
        )
        refresh_btn.pack(side="right")
    
    def _build_job_selection(self, parent):
        """Build job selection section."""
        job_frame = ttk.LabelFrame(parent, text="Job Selection", padding=10)
        job_frame.pack(fill="x", pady=(0, 10))
        
        # Job ID Entry
        ttk.Label(job_frame, text="Job ID:").pack(side="left", padx=(0, 5))
        
        self.job_id_entry = ttk.Entry(job_frame, width=30)
        self.job_id_entry.pack(side="left", padx=(0, 10))
        
        # Load button
        load_btn = ttk.Button(
            job_frame,
            text="Load Failed Files",
            command=self._on_load_failed_files
        )
        load_btn.pack(side="left", padx=(0, 10))
        
        # Load all blocked button
        load_blocked_btn = ttk.Button(
            job_frame,
            text="Load All Blocked Files",
            command=self._on_load_blocked_files
        )
        load_blocked_btn.pack(side="left")
    
    def _build_failed_files_tab(self, parent):
        """Build failed files tab."""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", padx=10, pady=10)
        
        # Recover button
        self.recover_btn = ttk.Button(
            toolbar,
            text="🔄 Recover Selected Files",
            command=self._on_recover_clicked,
            state="disabled"
        )
        self.recover_btn.pack(side="left", padx=(0, 10))
        
        # Force retry checkbox
        self.force_retry_var = tk.BooleanVar(value=False)
        force_retry_cb = ttk.Checkbutton(
            toolbar,
            text="Force Retry (Admin Override)",
            variable=self.force_retry_var
        )
        force_retry_cb.pack(side="left")
        
        # Info label
        info_label = ttk.Label(
            toolbar,
            text="ℹ Files with 3+ retries are automatically blocked",
            font=("Segoe UI", 9, "italic"),
            foreground="gray"
        )
        info_label.pack(side="right")
        
        # Treeview for failed files
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.failed_tree = ttk.Treeview(
            tree_frame,
            columns=("file", "status", "retries", "last_retry", "blocked", "reason"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="extended"
        )
        
        # Configure scrollbars
        vsb.config(command=self.failed_tree.yview)
        hsb.config(command=self.failed_tree.xview)
        
        # Column headings
        self.failed_tree.heading("file", text="File Path")
        self.failed_tree.heading("status", text="Status")
        self.failed_tree.heading("retries", text="Retry Count")
        self.failed_tree.heading("last_retry", text="Last Retry")
        self.failed_tree.heading("blocked", text="Blocked")
        self.failed_tree.heading("reason", text="Block Reason")
        
        # Column widths
        self.failed_tree.column("file", width=300)
        self.failed_tree.column("status", width=100)
        self.failed_tree.column("retries", width=100)
        self.failed_tree.column("last_retry", width=150)
        self.failed_tree.column("blocked", width=80)
        self.failed_tree.column("reason", width=200)
        
        # Pack
        self.failed_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind selection event
        self.failed_tree.bind("<<TreeviewSelect>>", self._on_failed_file_selected)
    
    def _build_blocked_files_tab(self, parent):
        """Build blocked files audit tab."""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", padx=10, pady=10)
        
        # Unblock button
        self.unblock_btn = ttk.Button(
            toolbar,
            text="🔓 Unblock Selected Files",
            command=self._on_unblock_clicked,
            state="disabled"
        )
        self.unblock_btn.pack(side="left", padx=(0, 10))
        
        # Warning label
        warning_label = ttk.Label(
            toolbar,
            text="⚠️ Unblocking requires admin confirmation",
            font=("Segoe UI", 9, "italic"),
            foreground="orange"
        )
        warning_label.pack(side="right")
        
        # Treeview for blocked files
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.blocked_tree = ttk.Treeview(
            tree_frame,
            columns=("job_id", "file", "retries", "blocked_at", "reason"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="extended"
        )
        
        # Configure scrollbars
        vsb.config(command=self.blocked_tree.yview)
        hsb.config(command=self.blocked_tree.xview)
        
        # Column headings
        self.blocked_tree.heading("job_id", text="Job ID")
        self.blocked_tree.heading("file", text="File Path")
        self.blocked_tree.heading("retries", text="Retry Count")
        self.blocked_tree.heading("blocked_at", text="Blocked At")
        self.blocked_tree.heading("reason", text="Block Reason")
        
        # Column widths
        self.blocked_tree.column("job_id", width=100)
        self.blocked_tree.column("file", width=300)
        self.blocked_tree.column("retries", width=100)
        self.blocked_tree.column("blocked_at", width=150)
        self.blocked_tree.column("reason", width=250)
        
        # Pack
        self.blocked_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind selection event
        self.blocked_tree.bind("<<TreeviewSelect>>", self._on_blocked_file_selected)
    
    def update_data(self, data: Dict[str, Any]):
        """Update view with new data (Pure business logic)."""
        data_type = data.get("type")
        
        if data_type == "failed_files":
            self._update_failed_files(data.get("files", []))
        elif data_type == "blocked_files":
            self._update_blocked_files(data.get("files", []))
        elif data_type == "recovery_result":
            self._handle_recovery_result(data)
        elif data_type == "unblock_result":
            self._handle_unblock_result(data)
        elif data_type == "status":
            self._update_status(data.get("message"), data.get("color", "black"))
    
    def _update_failed_files(self, files: List[Dict[str, Any]]):
        """Update failed files treeview."""
        self._failed_files = files
        
        # Clear existing items
        for item in self.failed_tree.get_children():
            self.failed_tree.delete(item)
        
        # Add new items
        for file_info in files:
            blocked = "Yes" if file_info.get("recovery_blocked", False) else "No"
            self.failed_tree.insert("", "end", values=(
                file_info.get("file_path", ""),
                file_info.get("status", ""),
                file_info.get("retry_count", 0),
                file_info.get("last_retry_at", "Never"),
                blocked,
                file_info.get("block_reason", "")
            ))
        
        # Update status
        count = len(files)
        blocked_count = sum(1 for f in files if f.get("recovery_blocked", False))
        self._update_status(
            f"📊 {count} failed files ({blocked_count} blocked)",
            "black"
        )
    
    def _update_blocked_files(self, files: List[Dict[str, Any]]):
        """Update blocked files treeview."""
        self._blocked_files = files
        
        # Clear existing items
        for item in self.blocked_tree.get_children():
            self.blocked_tree.delete(item)
        
        # Add new items
        for file_info in files:
            self.blocked_tree.insert("", "end", values=(
                file_info.get("job_id", ""),
                file_info.get("file_path", ""),
                file_info.get("retry_count", 0),
                file_info.get("blocked_at", "Unknown"),
                file_info.get("block_reason", "")
            ))
        
        # Update status
        self._update_status(f"🚫 {len(files)} blocked files system-wide", "orange")
    
    def _update_status(self, message: str, color: str = "black"):
        """Update status indicator."""
        icons = {"black": "⚪", "green": "🟢", "orange": "🟠", "red": "🔴"}
        icon = icons.get(color, "⚪")
        self.status_label.config(text=f"{icon} {message}", foreground=color)
    
    def _handle_recovery_result(self, data: Dict[str, Any]):
        """Handle recovery operation result."""
        success = data.get("success", False)
        message = data.get("message", "Unknown result")
        
        if success:
            messagebox.showinfo("Recovery Success", message)
            self._update_status("✅ Recovery completed", "green")
            # Refresh failed files list
            if self._selected_job_id:
                self._load_failed_files(self._selected_job_id)
        else:
            messagebox.showerror("Recovery Failed", message)
            self._update_status("❌ Recovery failed", "red")
    
    def _handle_unblock_result(self, data: Dict[str, Any]):
        """Handle unblock operation result."""
        success = data.get("success", False)
        message = data.get("message", "Unknown result")
        
        if success:
            messagebox.showinfo("Unblock Success", message)
            self._update_status("✅ Files unblocked", "green")
            # Refresh blocked files list
            self._load_blocked_files()
        else:
            messagebox.showerror("Unblock Failed", message)
            self._update_status("❌ Unblock failed", "red")
    
    def on_activate(self):
        """Lifecycle: Subscribe to events when view becomes visible."""
        # Subscribe to recovery events
        self.event_bus.subscribe(EventType.RECOVERY_STARTED, self._on_recovery_started)
        self.event_bus.subscribe(EventType.RECOVERY_COMPLETE, self._on_recovery_complete)
        self.event_bus.subscribe(EventType.RECOVERY_FAILED, self._on_recovery_failed)
        self.event_bus.subscribe(EventType.RECOVERY_FILE_BLOCKED, self._on_file_blocked)
        self.event_bus.subscribe(EventType.RECOVERY_FILE_UNBLOCKED, self._on_file_unblocked)
    
    def on_deactivate(self):
        """Lifecycle: Unsubscribe from events when view becomes hidden."""
        # Unsubscribe from recovery events
        self.event_bus.unsubscribe(EventType.RECOVERY_STARTED, self._on_recovery_started)
        self.event_bus.unsubscribe(EventType.RECOVERY_COMPLETE, self._on_recovery_complete)
        self.event_bus.unsubscribe(EventType.RECOVERY_FAILED, self._on_recovery_failed)
        self.event_bus.unsubscribe(EventType.RECOVERY_FILE_BLOCKED, self._on_file_blocked)
        self.event_bus.unsubscribe(EventType.RECOVERY_FILE_UNBLOCKED, self._on_file_unblocked)
    
    # Event Handlers
    
    def _on_recovery_started(self, event):
        """Handle recovery started event."""
        job_id = event.data.get("job_id")
        self.safe_update_data({
            "type": "status",
            "message": f"Recovery started for job {job_id}...",
            "color": "orange"
        })
    
    def _on_recovery_complete(self, event):
        """Handle recovery complete event."""
        recovered = event.data.get("recovered", 0)
        total = event.data.get("total", 0)
        self.safe_update_data({
            "type": "status",
            "message": f"✅ Recovery complete: {recovered}/{total} files",
            "color": "green"
        })
    
    def _on_recovery_failed(self, event):
        """Handle recovery failed event."""
        error = event.data.get("error", "Unknown error")
        self.safe_update_data({
            "type": "status",
            "message": f"❌ Recovery failed: {error}",
            "color": "red"
        })
    
    def _on_file_blocked(self, event):
        """Handle file blocked event."""
        file_path = event.data.get("file_path")
        reason = event.data.get("reason", "Unknown")
        self.safe_update_data({
            "type": "status",
            "message": f"🚫 File blocked: {file_path} ({reason})",
            "color": "orange"
        })
    
    def _on_file_unblocked(self, event):
        """Handle file unblocked event."""
        file_path = event.data.get("file_path")
        self.safe_update_data({
            "type": "status",
            "message": f"🔓 File unblocked: {file_path}",
            "color": "green"
        })
    
    # UI Event Handlers
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        if self._selected_job_id:
            self._load_failed_files(self._selected_job_id)
        self._load_blocked_files()
    
    def _on_load_failed_files(self):
        """Handle load failed files button click."""
        job_id = self.job_id_entry.get().strip()
        if not job_id:
            messagebox.showwarning("Input Required", "Please enter a Job ID")
            return
        
        self._selected_job_id = job_id
        self._load_failed_files(job_id)
    
    def _on_load_blocked_files(self):
        """Handle load blocked files button click."""
        self._load_blocked_files()
    
    def _load_failed_files(self, job_id: str):
        """Load failed files from backend."""
        self._update_status(f"Loading failed files for job {job_id}...", "orange")
        
        # Call backend service (sync methods for direct return)
        def fetch():
            try:
                result = self.backend_service._get_failed_files_sync(job_id, max_retries=3)
                return {"success": True, "files": result.get("failed_files", [])}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        def on_success(result):
            if result["success"]:
                self.safe_update_data({
                    "type": "failed_files",
                    "files": result["files"]
                })
            else:
                messagebox.showerror("Error", f"Failed to load: {result['error']}")
                self._update_status("❌ Load failed", "red")
        
        task = Task(
            task_id=f"load_failed_files_{datetime.now().timestamp()}",
            func=fetch,
            callback=on_success,
            priority=7
        )
        self.backend_service.task_executor.submit(task)
    
    def _load_blocked_files(self):
        """Load all blocked files from backend."""
        self._update_status("Loading all blocked files...", "orange")
        
        # Call backend service (sync methods for direct return)
        def fetch():
            try:
                result = self.backend_service._get_all_blocked_files_sync()
                return {"success": True, "files": result.get("blocked_files", [])}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        def on_success(result):
            if result["success"]:
                self.safe_update_data({
                    "type": "blocked_files",
                    "files": result["files"]
                })
            else:
                messagebox.showerror("Error", f"Failed to load: {result['error']}")
                self._update_status("❌ Load failed", "red")
        
        task = Task(
            task_id=f"load_blocked_files_{datetime.now().timestamp()}",
            func=fetch,
            callback=on_success,
            priority=7
        )
        self.backend_service.task_executor.submit(task)
    
    def _on_recover_clicked(self):
        """Handle recover button click."""
        if not self._selected_job_id:
            messagebox.showwarning("No Job Selected", "Please load failed files first")
            return
        
        # Get selected files
        selection = self.failed_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select files to recover")
            return
        
        # Check for blocked files
        selected_files = [self.failed_tree.item(item)["values"][0] for item in selection]
        force_retry = self.force_retry_var.get()
        
        # Confirm
        msg = f"Recover {len(selected_files)} file(s)?"
        if force_retry:
            msg += "\n\n⚠️ Force retry enabled (admin override)"
        
        if not messagebox.askyesno("Confirm Recovery", msg):
            return
        
        # Perform recovery
        self._recover_files(self._selected_job_id, selected_files, force_retry)
    
    def _recover_files(self, job_id: str, file_paths: List[str], force_retry: bool):
        """Recover files via backend."""
        self._update_status(f"Recovering {len(file_paths)} files...", "orange")
        
        # Call backend service (sync methods for direct return)
        def recover():
            try:
                result = self.backend_service._recover_failed_files_sync(
                    job_id,
                    max_retries=3,
                    force_retry=force_retry
                )
                return {
                    "success": True,
                    "message": f"Recovery completed: {result.get('recovered', 0)}/{result.get('total', 0)} files"
                }
            except Exception as e:
                return {"success": False, "message": str(e)}
        
        def on_success(result):
            self.safe_update_data({
                "type": "recovery_result",
                **result
            })
        
        task = Task(
            task_id=f"recover_files_{datetime.now().timestamp()}",
            func=recover,
            callback=on_success,
            priority=8
        )
        self.backend_service.task_executor.submit(task)
    
    def _on_unblock_clicked(self):
        """Handle unblock button click."""
        # Get selected files
        selection = self.blocked_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select files to unblock")
            return
        
        # Confirm admin override
        msg = f"⚠️ ADMIN ACTION REQUIRED\n\nUnblock {len(selection)} file(s)?\n\n"
        msg += "This will:\n"
        msg += "- Reset retry count to 0\n"
        msg += "- Clear block reason\n"
        msg += "- Allow recovery attempts\n\n"
        msg += "Are you sure?"
        
        if not messagebox.askyesno("Confirm Unblock (Admin)", msg):
            return
        
        # Perform unblock
        for item in selection:
            values = self.blocked_tree.item(item)["values"]
            job_id = values[0]
            file_path = values[1]
            self._unblock_file(job_id, file_path)
    
    def _unblock_file(self, job_id: str, file_path: str):
        """Unblock file via backend."""
        self._update_status(f"Unblocking {file_path}...", "orange")
        
        # Call backend service (sync methods for direct return)
        def unblock():
            try:
                result = self.backend_service._unblock_file_sync(
                    job_id,
                    file_path,
                    admin_override=True
                )
                return {
                    "success": True,
                    "message": f"File unblocked: {file_path}"
                }
            except Exception as e:
                return {"success": False, "message": str(e)}
        
        def on_success(result):
            self.safe_update_data({
                "type": "unblock_result",
                **result
            })
        
        task = Task(
            task_id=f"unblock_files_{datetime.now().timestamp()}",
            func=unblock,
            callback=on_success,
            priority=8
        )
        self.backend_service.task_executor.submit(task)
    
    def _on_failed_file_selected(self, event):
        """Handle failed file selection."""
        selection = self.failed_tree.selection()
        self.recover_btn.config(state="normal" if selection else "disabled")
    
    def _on_blocked_file_selected(self, event):
        """Handle blocked file selection."""
        selection = self.blocked_tree.selection()
        self.unblock_btn.config(state="normal" if selection else "disabled")


# Export
__all__ = ["RecoveryView"]
