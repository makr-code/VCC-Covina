"""
Multi-Method Upload Dialog

Provides user choice between 4 upload methods:
1. Chunked HTTP (resume capability, slow networks)
2. WebSocket Streaming (fast, real-time progress)
3. SMB File Watcher (drag-and-drop, network share)
4. Hybrid Manager (automatic selection)

Author: Covina Development Team
Created: 15. Oktober 2025
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import subprocess
import sys
from typing import Optional, List

class UploadMethodDialog(tk.Toplevel):
    """Upload method selection dialog"""
    
    def __init__(self, parent, files: List[str] = None):
        super().__init__(parent)
        
        self.title("Upload Method Selection")
        self.geometry("700x600")
        self.resizable(False, False)
        
        self.selected_method = None
        self.selected_files = files or []
        self.upload_result = None
        
        self._create_widgets()
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
    
    def _create_widgets(self):
        """Create dialog widgets"""
        # Title
        title_frame = ttk.Frame(self, padding=20)
        title_frame.pack(fill=tk.X)
        
        title = ttk.Label(
            title_frame,
            text="📤 Select Upload Method",
            font=('Segoe UI', 16, 'bold')
        )
        title.pack()
        
        subtitle = ttk.Label(
            title_frame,
            text="Choose the best method for your network and file size",
            font=('Segoe UI', 10),
            foreground='gray'
        )
        subtitle.pack(pady=(5, 0))
        
        # File info
        if self.selected_files:
            info_frame = ttk.Frame(self, padding=(20, 0, 20, 10))
            info_frame.pack(fill=tk.X)
            
            file_count = len(self.selected_files)
            total_size = sum(Path(f).stat().st_size for f in self.selected_files if Path(f).exists())
            size_mb = total_size / 1024 / 1024
            
            info_text = f"{file_count} file(s) selected | Total size: {size_mb:.2f} MB"
            info_label = ttk.Label(info_frame, text=info_text, font=('Segoe UI', 9), foreground='blue')
            info_label.pack()
        
        # Method options
        methods_frame = ttk.Frame(self, padding=20)
        methods_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_method_option(
            methods_frame,
            "1️⃣ Chunked HTTP Upload",
            "✅ Resume capability\n"
            "✅ Best for slow/unstable networks\n"
            "✅ Large files (auto-resume on failure)\n"
            "⚡ Speed: ~98 MB/s (5MB chunks)",
            "chunked_http",
            row=0
        )
        
        self._create_method_option(
            methods_frame,
            "2️⃣ WebSocket Streaming",
            "✅ Real-time bidirectional\n"
            "✅ Best for fast stable networks\n"
            "✅ Small-medium files (<100 MB)\n"
            "⚡ Speed: ~13 MB/s (256KB chunks)",
            "websocket",
            row=1
        )
        
        self._create_method_option(
            methods_frame,
            "3️⃣ SMB File Watcher",
            "✅ Drag-and-drop to network share\n"
            "✅ Automatic processing\n"
            "✅ Best for LAN environments\n"
            "⚡ Speed: Instant (local copy)",
            "smb_watcher",
            row=2
        )
        
        self._create_method_option(
            methods_frame,
            "4️⃣ Hybrid Manager (Recommended)",
            "✅ Automatic method selection\n"
            "✅ Network speed detection\n"
            "✅ Optimal chunk size selection\n"
            "⚡ Speed: Auto-optimized",
            "hybrid",
            row=3,
            recommended=True
        )
        
        # Button frame
        button_frame = ttk.Frame(self, padding=20)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side=tk.LEFT)
        
        self.upload_btn = ttk.Button(
            button_frame,
            text="🚀 Upload",
            command=self._start_upload,
            state=tk.DISABLED
        )
        self.upload_btn.pack(side=tk.RIGHT)
    
    def _create_method_option(self, parent, title, description, method_id, row, recommended=False):
        """Create a method option card"""
        # Card frame
        card = ttk.LabelFrame(parent, text=title, padding=15)
        card.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=5)
        
        if recommended:
            card.configure(relief=tk.GROOVE, borderwidth=2)
        
        # Description
        desc_label = ttk.Label(
            card,
            text=description,
            font=('Segoe UI', 9),
            foreground='#333',
            justify=tk.LEFT
        )
        desc_label.pack(anchor=tk.W)
        
        # Select button
        select_btn = ttk.Button(
            card,
            text="✓ Select" if not recommended else "⭐ Select (Recommended)",
            command=lambda: self._select_method(method_id)
        )
        select_btn.pack(anchor=tk.E, pady=(10, 0))
    
    def _select_method(self, method_id):
        """Select upload method"""
        self.selected_method = method_id
        self.upload_btn.configure(state=tk.NORMAL)
        
        # Update title to show selection
        self.title(f"Upload Method: {method_id.replace('_', ' ').title()}")
    
    def _start_upload(self):
        """Start upload with selected method"""
        if not self.selected_method:
            messagebox.showwarning("No Method", "Please select an upload method")
            return
        
        if not self.selected_files:
            messagebox.showwarning("No Files", "No files selected for upload")
            return
        
        # Start upload in background thread
        self.upload_btn.configure(state=tk.DISABLED, text="Uploading...")
        
        thread = threading.Thread(target=self._upload_worker, daemon=True)
        thread.start()
    
    def _upload_worker(self):
        """Upload worker thread"""
        try:
            if self.selected_method == "chunked_http":
                self._upload_chunked()
            elif self.selected_method == "websocket":
                self._upload_websocket()
            elif self.selected_method == "smb_watcher":
                self._upload_smb()
            elif self.selected_method == "hybrid":
                self._upload_hybrid()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Upload Error", str(e)))
        finally:
            self.after(0, self.destroy)
    
    def _upload_chunked(self):
        """Upload via Chunked HTTP"""
        for file_path in self.selected_files:
            result = subprocess.run(
                [sys.executable, "scripts/client_chunked_upload.py", file_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                raise Exception(f"Chunked HTTP upload failed: {file_path}")
        
        self.after(0, lambda: messagebox.showinfo("Success", f"{len(self.selected_files)} file(s) uploaded via Chunked HTTP"))
    
    def _upload_websocket(self):
        """Upload via WebSocket"""
        for file_path in self.selected_files:
            result = subprocess.run(
                [sys.executable, "scripts/client_websocket_upload.py", file_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                raise Exception(f"WebSocket upload failed: {file_path}")
        
        self.after(0, lambda: messagebox.showinfo("Success", f"{len(self.selected_files)} file(s) uploaded via WebSocket"))
    
    def _upload_smb(self):
        """Upload via SMB Watcher"""
        # For SMB, we just show instructions
        instructions = (
            "SMB File Watcher Instructions:\n\n"
            "1. Copy files to network share: \\\\server\\share\\inbox\n"
            "2. Files will be automatically processed\n"
            "3. Check 'Active Jobs' panel for progress\n\n"
            "Note: SMB Watcher runs as a background service"
        )
        
        self.after(0, lambda: messagebox.showinfo("SMB Upload", instructions))
    
    def _upload_hybrid(self):
        """Upload via Hybrid Manager"""
        for file_path in self.selected_files:
            result = subprocess.run(
                [sys.executable, "-m", "ingestion.hybrid_upload_manager", file_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                raise Exception(f"Hybrid upload failed: {file_path}")
        
        self.after(0, lambda: messagebox.showinfo("Success", f"{len(self.selected_files)} file(s) uploaded via Hybrid Manager"))


def show_upload_dialog(parent, files: List[str] = None):
    """Show upload method selection dialog"""
    dialog = UploadMethodDialog(parent, files)
    parent.wait_window(dialog)
    return dialog.selected_method
