#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Covina Ingestion GUI Tool
==========================

Simple GUI tool for uploading files/folders to Covina Ingestion Backend.

Features:
- File/Folder selection (recursive folder scan)
- Drag & Drop support
- Real-time progress bar
- Job status monitoring via WebSocket
- Automatic file filtering (supported formats)

Author: Covina System
Date: 21. Oktober 2025
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import requests
import json
import threading
import time
from pathlib import Path
from typing import List, Dict, Any
import websocket
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
INGESTION_BACKEND_URL = "http://127.0.0.1:45679"
WEBSOCKET_URL = "ws://127.0.0.1:45679/ws/jobs"

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.pdf', '.txt', '.docx', '.doc', '.xlsx', '.xls', 
    '.csv', '.json', '.xml', '.html', '.md', '.rtf'
}


class IngestionGUI:
    """Main GUI Application for Covina Ingestion"""
    
    def __init__(self, root):
        """Initialize GUI"""
        self.root = root
        self.root.title("Covina Ingestion Tool v1.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # State
        self.selected_files: List[str] = []
        self.current_job_id: str = None
        self.ws: websocket.WebSocket = None
        self.upload_thread: threading.Thread = None
        self.ws_thread: threading.Thread = None
        
        # Create GUI
        self._create_widgets()
        self._setup_drag_drop()
        
        # Check backend availability
        self.root.after(100, self._check_backend)
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="📄 Covina Document Ingestion", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)
        
        # File Selection Section
        selection_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        selection_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        selection_frame.columnconfigure(1, weight=1)
        
        # Buttons
        ttk.Button(
            selection_frame, 
            text="📁 Select Files", 
            command=self._select_files
        ).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        
        ttk.Button(
            selection_frame, 
            text="📂 Select Folder", 
            command=self._select_folder
        ).grid(row=0, column=1, padx=5, sticky=tk.W)
        
        ttk.Button(
            selection_frame, 
            text="🗑️ Clear", 
            command=self._clear_selection
        ).grid(row=0, column=2, padx=5, sticky=tk.W)
        
        # File count label
        self.file_count_label = ttk.Label(selection_frame, text="No files selected")
        self.file_count_label.grid(row=1, column=0, columnspan=3, pady=(10, 0), sticky=tk.W)
        
        # File List Section
        list_frame = ttk.LabelFrame(main_frame, text="Selected Files", padding="10")
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # File listbox with scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.file_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED,
            height=10
        )
        scrollbar.config(command=self.file_listbox.yview)
        
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Upload Progress", padding="10")
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            mode='determinate',
            length=300
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Progress label
        self.progress_label = ttk.Label(progress_frame, text="Ready to upload")
        self.progress_label.grid(row=1, column=0, sticky=tk.W)
        
        # Status label
        self.status_label = ttk.Label(progress_frame, text="", foreground="blue")
        self.status_label.grid(row=2, column=0, sticky=tk.W)
        
        # Action Buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=4, column=0, sticky=(tk.W, tk.E))
        action_frame.columnconfigure(0, weight=1)
        
        self.upload_button = ttk.Button(
            action_frame, 
            text="🚀 Start Upload", 
            command=self._start_upload,
            state=tk.DISABLED
        )
        self.upload_button.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.cancel_button = ttk.Button(
            action_frame, 
            text="❌ Cancel", 
            command=self._cancel_upload,
            state=tk.DISABLED
        )
        self.cancel_button.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Backend status indicator
        self.backend_status = ttk.Label(
            main_frame, 
            text="⚪ Backend: Checking...", 
            foreground="gray"
        )
        self.backend_status.grid(row=5, column=0, pady=(10, 0), sticky=tk.W)
    
    def _setup_drag_drop(self):
        """Setup drag & drop functionality"""
        try:
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self._on_drop)
        except Exception as e:
            logger.warning(f"Drag & Drop not available: {e}")
    
    def _on_drop(self, event):
        """Handle drag & drop"""
        files = self.root.tk.splitlist(event.data)
        for file_path in files:
            file_path = file_path.strip('{}')
            if os.path.isfile(file_path):
                self._add_file(file_path)
            elif os.path.isdir(file_path):
                self._add_folder(file_path)
        
        self._update_file_list()
    
    def _check_backend(self):
        """Check if backend is available"""
        try:
            response = requests.get(f"{INGESTION_BACKEND_URL}/health", timeout=2)
            if response.status_code == 200:
                self.backend_status.config(
                    text="✅ Backend: Online", 
                    foreground="green"
                )
            else:
                self.backend_status.config(
                    text="⚠️ Backend: Unhealthy", 
                    foreground="orange"
                )
        except Exception as e:
            self.backend_status.config(
                text="❌ Backend: Offline", 
                foreground="red"
            )
            logger.error(f"Backend check failed: {e}")
    
    def _select_files(self):
        """Open file dialog to select files"""
        filetypes = [
            ("All supported files", " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)),
            ("PDF files", "*.pdf"),
            ("Text files", "*.txt"),
            ("Word documents", "*.docx *.doc"),
            ("Excel files", "*.xlsx *.xls"),
            ("All files", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="Select files to upload",
            filetypes=filetypes
        )
        
        for file_path in files:
            self._add_file(file_path)
        
        self._update_file_list()
    
    def _select_folder(self):
        """Open folder dialog to select folder (recursive scan)"""
        folder_path = filedialog.askdirectory(title="Select folder to upload")
        
        if folder_path:
            self._add_folder(folder_path)
            self._update_file_list()
    
    def _add_file(self, file_path: str):
        """Add file to selection if supported"""
        ext = Path(file_path).suffix.lower()
        
        if ext in SUPPORTED_EXTENSIONS:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_path}")
    
    def _add_folder(self, folder_path: str):
        """Add all supported files from folder (recursive)"""
        count = 0
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                ext = Path(file_path).suffix.lower()
                
                if ext in SUPPORTED_EXTENSIONS:
                    if file_path not in self.selected_files:
                        self.selected_files.append(file_path)
                        count += 1
        
        if count > 0:
            messagebox.showinfo(
                "Folder Scan Complete", 
                f"Found {count} supported files in folder:\n{folder_path}"
            )
    
    def _update_file_list(self):
        """Update file listbox and labels"""
        # Update listbox
        self.file_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            self.file_listbox.insert(tk.END, file_path)
        
        # Update count label
        count = len(self.selected_files)
        if count == 0:
            self.file_count_label.config(text="No files selected")
            self.upload_button.config(state=tk.DISABLED)
        else:
            total_size = sum(os.path.getsize(f) for f in self.selected_files) / (1024 * 1024)
            self.file_count_label.config(
                text=f"{count} file{'s' if count != 1 else ''} selected ({total_size:.2f} MB)"
            )
            self.upload_button.config(state=tk.NORMAL)
    
    def _clear_selection(self):
        """Clear file selection"""
        self.selected_files.clear()
        self._update_file_list()
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Ready to upload")
        self.status_label.config(text="")
    
    def _start_upload(self):
        """Start upload in background thread"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select files to upload.")
            return
        
        # Disable UI during upload
        self.upload_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Preparing upload...")
        
        # Start upload thread
        self.upload_thread = threading.Thread(target=self._upload_files, daemon=True)
        self.upload_thread.start()
    
    def _upload_files(self):
        """Upload files to ingestion backend"""
        try:
            # Prepare files for upload
            files = []
            for file_path in self.selected_files:
                files.append(
                    ('files', (os.path.basename(file_path), open(file_path, 'rb')))
                )
            
            # Update progress
            self.root.after(0, lambda: self.progress_label.config(
                text=f"Uploading {len(files)} files..."
            ))
            
            # Upload files
            response = requests.post(
                f"{INGESTION_BACKEND_URL}/upload/",
                files=files,
                timeout=300  # 5 minutes timeout
            )
            
            # Close file handles
            for _, (_, file_handle) in files:
                file_handle.close()
            
            if response.status_code == 200:
                result = response.json()
                self.current_job_id = result.get('job_id')
                
                self.root.after(0, lambda: self._update_ui_after_upload(
                    success=True,
                    message=f"Upload successful! Job ID: {self.current_job_id}"
                ))
                
                # Start WebSocket monitoring
                self._start_websocket_monitoring()
                
            else:
                error_msg = f"Upload failed: {response.status_code} - {response.text}"
                self.root.after(0, lambda: self._update_ui_after_upload(
                    success=False,
                    message=error_msg
                ))
                
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            logger.error(error_msg)
            self.root.after(0, lambda: self._update_ui_after_upload(
                success=False,
                message=error_msg
            ))
    
    def _update_ui_after_upload(self, success: bool, message: str):
        """Update UI after upload completes"""
        if success:
            self.progress_label.config(text="Upload complete! Processing files...")
            self.status_label.config(text=message, foreground="green")
        else:
            self.progress_label.config(text="Upload failed")
            self.status_label.config(text=message, foreground="red")
            self.upload_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
    
    def _start_websocket_monitoring(self):
        """Start WebSocket monitoring in background thread"""
        if not self.current_job_id:
            return
        
        self.ws_thread = threading.Thread(
            target=self._monitor_job_progress, 
            daemon=True
        )
        self.ws_thread.start()
    
    def _monitor_job_progress(self):
        """Monitor job progress via WebSocket"""
        try:
            self.ws = websocket.WebSocket()
            self.ws.connect(WEBSOCKET_URL)
            logger.info(f"WebSocket connected for job {self.current_job_id}")
            
            while True:
                try:
                    message = self.ws.recv()
                    if not message:
                        break
                    
                    data = json.loads(message)
                    
                    # Check if message is for current job
                    if data.get('job_id') == self.current_job_id:
                        self._update_progress(data)
                    
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as e:
                    logger.error(f"WebSocket receive error: {e}")
                    break
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            if self.ws:
                self.ws.close()
    
    def _update_progress(self, data: Dict[str, Any]):
        """Update progress bar based on WebSocket data"""
        status = data.get('status', '')
        processed = data.get('files_processed', 0)
        total = data.get('total_files', len(self.selected_files))
        
        # Calculate progress
        progress = (processed / total * 100) if total > 0 else 0
        
        # Update UI in main thread
        self.root.after(0, lambda: self._update_progress_ui(
            progress=progress,
            processed=processed,
            total=total,
            status=status
        ))
    
    def _update_progress_ui(self, progress: float, processed: int, total: int, status: str):
        """Update progress UI elements"""
        self.progress_bar['value'] = progress
        self.progress_label.config(
            text=f"Processing: {processed}/{total} files ({progress:.1f}%)"
        )
        
        # Update status
        if status == 'completed':
            self.status_label.config(
                text=f"✅ Job completed! All {total} files processed successfully.",
                foreground="green"
            )
            self.upload_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            
            # Show completion message
            messagebox.showinfo(
                "Upload Complete",
                f"Successfully processed {total} files!\n\nJob ID: {self.current_job_id}"
            )
            
        elif status == 'failed':
            self.status_label.config(
                text=f"❌ Job failed. Check logs for details.",
                foreground="red"
            )
            self.upload_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
    
    def _cancel_upload(self):
        """Cancel ongoing upload"""
        if messagebox.askyesno("Cancel Upload", "Are you sure you want to cancel?"):
            # TODO: Implement job cancellation API call
            self.status_label.config(text="Upload cancelled", foreground="orange")
            self.upload_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            
            if self.ws:
                self.ws.close()
    
    def on_closing(self):
        """Handle window close event"""
        if self.ws:
            self.ws.close()
        self.root.destroy()


def main():
    """Main entry point"""
    # Use TkinterDnD for drag & drop support
    try:
        root = TkinterDnD.Tk()
    except Exception:
        # Fallback to regular Tk if TkinterDnD not available
        logger.warning("TkinterDnD not available - Drag & Drop disabled")
        root = tk.Tk()
    
    app = IngestionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
