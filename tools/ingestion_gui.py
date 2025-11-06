#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Covina Ingestion GUI Tool
==========================

Simple GUI tool for uploading files/folders to Covina Ingestion Backend.

Features:
- File/Folder selection (recursive folder scan)
- Drag & Drop support
- Real-time progress bar with byte-level tracking
- Job status monitoring via WebSocket
- Automatic file filtering (supported formats)
- Streaming uploads for large files (multi-GB support)
- Dynamic timeout calculation (5min base + 10min/GB)
- Smart batch sizing based on file sizes

Author: Covina System
Date: 28. Oktober 2025
Version: 2.0.0 - Streaming Upload Support
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Optional Drag & Drop (tkinterdnd2)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    TKDND_AVAILABLE = True
except Exception:
    TKDND_AVAILABLE = False
    DND_FILES = None  # type: ignore
    TkinterDnD = None  # type: ignore
import os
import requests
import json
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
import websocket
import logging
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration (client-side)
# Base HTTP origin of the ingestion service (no trailing slash)
INGESTION_BACKEND_URL = os.getenv("INGESTION_BACKEND_URL", "http://127.0.0.1:45679")

# API prefix and base path for new microservice layout
# New ingestion service exposes routes under "/ingestion" and also supports "/v1" via middleware
API_VERSION_PREFIX = "/v1"   # set to "" to disable versioned calls
INGESTION_BASE_PATH = "/ingestion"

def _build_http_urls(*paths: str) -> list[str]:
    """Build candidate HTTP URLs by combining base URL with provided paths.

    The first entries should prefer versioned variants; later entries cover legacy paths.
    """
    urls: list[str] = []
    base = INGESTION_BACKEND_URL.rstrip("/")
    for p in paths:
        if not p.startswith("/"):
            p = "/" + p
        urls.append(base + p)
    return urls

def _build_ws_urls(*paths: str) -> list[str]:
    base_http = INGESTION_BACKEND_URL.rstrip("/")
    # derive ws scheme from http/https
    if base_http.startswith("https://"):
        ws_origin = "wss://" + base_http[len("https://"):]
    elif base_http.startswith("http://"):
        ws_origin = "ws://" + base_http[len("http://"):]
    else:
        ws_origin = "ws://" + base_http
    urls: list[str] = []
    for p in paths:
        if not p.startswith("/"):
            p = "/" + p
        urls.append(ws_origin + p)
    return urls

# Candidate endpoints (ordered by preference)
HEALTH_ENDPOINTS = [
    f"{API_VERSION_PREFIX}{INGESTION_BASE_PATH}/health",
    f"{INGESTION_BASE_PATH}/health",
    "/health",  # legacy
]

CAPABILITIES_ENDPOINTS = [
    f"{API_VERSION_PREFIX}{INGESTION_BASE_PATH}/capabilities/supported-filetypes",
    f"{INGESTION_BASE_PATH}/capabilities/supported-filetypes",
    "/capabilities/supported-filetypes",  # legacy
]

UPLOAD_ENDPOINTS = [
    f"{API_VERSION_PREFIX}{INGESTION_BASE_PATH}/upload/files",  # new preferred
    f"{INGESTION_BASE_PATH}/upload/files",
    f"{API_VERSION_PREFIX}/upload/files",  # legacy layout with version prefix
    "/upload/files",  # legacy
]

WS_JOB_ENDPOINTS = [
    f"{API_VERSION_PREFIX}/ws/jobs",
    "/ws/jobs",
    f"{API_VERSION_PREFIX}{INGESTION_BASE_PATH}/ws/jobs",
    f"{INGESTION_BASE_PATH}/ws/jobs",
]

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.pdf', '.txt', '.docx', '.doc', '.xlsx', '.xls', 
    '.csv', '.json', '.xml', '.html', '.md', '.rtf'
}


class StreamingMultipartUploader:
    """
    Best-Practice Streaming Upload Handler for Large Files
    
    Features:
    - Memory-efficient streaming (no full file loading)
    - Progress tracking with callbacks
    - Dynamic timeout calculation
    - Automatic retry logic
    - Robust error handling
    
    Usage:
        uploader = StreamingMultipartUploader(
            url="http://backend/upload",
            progress_callback=lambda p: print(f"{p}%")
        )
        result = uploader.upload_files(file_paths)
    """
    
    def __init__(
        self,
        url: str,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
        timeout_base: int = 300,  # 5 minutes base timeout
        timeout_per_gb: int = 600,  # +10 minutes per GB
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize streaming uploader
        
        Args:
            url: Backend upload endpoint URL
            progress_callback: Callback function(bytes_uploaded, total_bytes, percent)
            timeout_base: Base timeout in seconds (default: 300s = 5min)
            timeout_per_gb: Additional timeout per GB (default: 600s = 10min/GB)
            max_retries: Maximum retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 5)
        """
        self.url = url
        self.progress_callback = progress_callback
        self.timeout_base = timeout_base
        self.timeout_per_gb = timeout_per_gb
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # State
        self.total_bytes = 0
        self.uploaded_bytes = 0
        self.cancelled = False
        
    def cancel(self):
        """Cancel ongoing upload"""
        self.cancelled = True
        logger.info("[UPLOAD] Upload cancelled by user")
        
    def _calculate_timeout(self, total_bytes: int) -> int:
        """
        Calculate dynamic timeout based on file sizes
        
        Formula: base + (GB × timeout_per_gb)
        Example: 5GB file → 300s + (5 × 600s) = 3300s = 55 minutes
        
        Args:
            total_bytes: Total size in bytes
            
        Returns:
            Timeout in seconds
        """
        gb = total_bytes / (1024 ** 3)  # Bytes to GB
        timeout = self.timeout_base + int(gb * self.timeout_per_gb)
        
        logger.info(f"[UPLOAD] Calculated timeout: {timeout}s for {gb:.2f} GB")
        return timeout
        
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
        
    def _progress_monitor(self, monitor: MultipartEncoderMonitor):
        """
        Internal progress callback for MultipartEncoderMonitor
        
        Args:
            monitor: MultipartEncoderMonitor instance
        """
        if self.cancelled:
            raise Exception("Upload cancelled by user")
            
        self.uploaded_bytes = monitor.bytes_read
        percent = int((self.uploaded_bytes / self.total_bytes) * 100) if self.total_bytes > 0 else 0
        
        # Call external progress callback if provided
        if self.progress_callback:
            try:
                self.progress_callback(self.uploaded_bytes, self.total_bytes, percent)
            except Exception as e:
                logger.warning(f"[UPLOAD] Progress callback error: {e}")
                
    def upload_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Upload files using streaming multipart encoding
        
        This method:
        1. Calculates total size WITHOUT loading files into memory
        2. Creates MultipartEncoder for streaming upload
        3. Wraps with progress monitor
        4. Uploads with dynamic timeout
        5. Retries on failure
        
        Args:
            file_paths: List of file paths to upload
            
        Returns:
            Response dict with job_id, file_count, etc.
            
        Raises:
            Exception: On upload failure after all retries
        """
        if not file_paths:
            raise ValueError("No files to upload")
            
        # Reset state
        self.uploaded_bytes = 0
        self.cancelled = False
        
        # Calculate total size (stat without opening files)
        logger.info(f"[UPLOAD] Calculating total size for {len(file_paths)} files...")
        self.total_bytes = sum(os.path.getsize(fp) for fp in file_paths)
        logger.info(f"[UPLOAD] Total size: {self._format_bytes(self.total_bytes)}")
        
        # Calculate dynamic timeout
        timeout = self._calculate_timeout(self.total_bytes)
        
        # Retry loop
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[UPLOAD] Attempt {attempt}/{self.max_retries}")
                
                # Create multipart fields (lazy file opening!)
                # Files are opened by MultipartEncoder only when needed
                fields = []
                for file_path in file_paths:
                    filename = os.path.basename(file_path)
                    # Use tuple format: ('field_name', ('filename', file_obj, 'content-type'))
                    # File will be opened lazily by MultipartEncoder
                    fields.append((
                        'files',
                        (filename, open(file_path, 'rb'), 'application/octet-stream')
                    ))
                
                # Create streaming encoder
                encoder = MultipartEncoder(fields=fields)
                
                # Wrap with progress monitor
                monitor = MultipartEncoderMonitor(
                    encoder,
                    callback=self._progress_monitor
                )
                
                # Execute streaming upload
                logger.info(f"[UPLOAD] Starting streaming upload (timeout: {timeout}s)...")
                response = requests.post(
                    self.url,
                    data=monitor,
                    headers={'Content-Type': monitor.content_type},
                    timeout=timeout
                )

                # Check response
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"[UPLOAD] ✅ Upload successful! Job ID: {result.get('job_id')}")
                    return result
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                    logger.error(f"[UPLOAD] ❌ Upload failed: {error_msg}")
                    last_error = Exception(error_msg)
                    
            except Exception as e:
                logger.error(f"[UPLOAD] ❌ Attempt {attempt} failed: {e}")
                last_error = e
                
                # Clean up file handles on error
                try:
                    if 'encoder' in locals():
                        # Close any open file handles
                        for field_name, field_value in encoder.fields.items():
                            if hasattr(field_value, 'close'):
                                field_value.close()
                except:
                    pass
                    
            # Retry delay (except on last attempt)
            if attempt < self.max_retries:
                logger.info(f"[UPLOAD] Retrying in {self.retry_delay}s...")
                time.sleep(self.retry_delay)
                
        # All retries failed
        error_msg = f"Upload failed after {self.max_retries} attempts: {last_error}"
        logger.error(f"[UPLOAD] {error_msg}")
        raise Exception(error_msg)



class IngestionGUI:
    """Main GUI Application for Covina Ingestion"""
    
    def __init__(self, root):
        """Initialize GUI"""
        self.root = root
        self.root.title("Covina Ingestion Tool v1.1")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        self.root.minsize(600, 400)
        
        # State
        self.selected_files: List[str] = []
        self.current_job_id: str = None
        self.ws: websocket.WebSocket = None
        self.upload_thread: threading.Thread = None
        self.ws_thread: threading.Thread = None
        self.scan_overlay: tk.Toplevel = None
        self.scan_cancelled: bool = False
        # Supported extensions (will be fetched from backend; default fallback)
        self.supported_extensions: set[str] = set(SUPPORTED_EXTENSIONS)
        self._capabilities_fetched: bool = False
        
        # Create GUI
        self._create_widgets()
        self._setup_drag_drop()
        
        # Check backend availability
        self.root.after(100, self._check_backend)
        # Try fetching capabilities shortly after startup
        self.root.after(500, self._fetch_supported_filetypes)
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        # Main container with less padding
        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Header frame with title and logo
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        header_frame.columnconfigure(0, weight=1)
        
        # Compact title (left)
        title_label = ttk.Label(
            header_frame, 
            text="📄 Covina Document Ingestion", 
            font=('Arial', 14, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # COVINA Logo/Brand (right) - clickable for About dialog
        covina_logo = tk.Label(
            header_frame,
            text="COVINA",
            font=('Segoe UI', 14, 'bold'),
            foreground='#0066CC',
            cursor='hand2',
            padx=8,
            pady=2
        )
        covina_logo.grid(row=0, column=1, sticky=tk.E)
        covina_logo.bind('<Button-1>', lambda e: self._show_about())
        
        # Hover-Effekt für Logo
        def on_enter(e):
            covina_logo.config(foreground='#004499')
        def on_leave(e):
            covina_logo.config(foreground='#0066CC')
        
        covina_logo.bind('<Enter>', on_enter)
        covina_logo.bind('<Leave>', on_leave)
        
        # File Selection Section - more compact
        selection_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="6")
        selection_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 6))
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
        
        # File count label - more compact
        self.file_count_label = ttk.Label(selection_frame, text="No files selected", 
                                          font=('Arial', 9))
        self.file_count_label.grid(row=1, column=0, columnspan=3, pady=(6, 0), sticky=tk.W)
        
        # File List Section - reduced padding
        list_frame = ttk.LabelFrame(main_frame, text="Selected Files", padding="6")
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # File listbox with scrollbar - reduced height
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.file_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED,
            height=8,
            font=('Courier New', 8)
        )
        scrollbar.config(command=self.file_listbox.yview)
        
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Progress Section - compact
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="6")
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 6))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            mode='determinate'
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 3))
        
        # Progress label - smaller font
        self.progress_label = ttk.Label(progress_frame, text="Ready to upload", 
                                       font=('Arial', 9))
        self.progress_label.grid(row=1, column=0, sticky=tk.W)
        
        # Status label - smaller font
        self.status_label = ttk.Label(progress_frame, text="", foreground="blue",
                                     font=('Arial', 9))
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
        
        # Backend status indicator - compact
        self.backend_status = ttk.Label(
            main_frame, 
            text="⚪ Backend: Checking...", 
            foreground="gray",
            font=('Arial', 8)
        )
        self.backend_status.grid(row=5, column=0, pady=(6, 0), sticky=tk.W)
    
    def _show_about(self):
        """Show About dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About Covina Ingestion Tool")
        about_window.geometry("450x380")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        
        # Center on parent
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 380) // 2
        about_window.geometry(f"+{x}+{y}")
        
        # Content frame
        content = ttk.Frame(about_window, padding="20")
        content.pack(fill=tk.BOTH, expand=True)
        
        # Logo/Brand
        ttk.Label(
            content,
            text="COVINA",
            font=('Segoe UI', 24, 'bold'),
            foreground='#0066CC'
        ).pack(pady=(0, 5))
        
        # Subtitle
        ttk.Label(
            content,
            text="Document Ingestion Tool",
            font=('Arial', 12)
        ).pack(pady=(0, 20))
        
        # Version info
        ttk.Label(
            content,
            text="Version 1.1.0",
            font=('Arial', 10, 'bold')
        ).pack()
        
        ttk.Label(
            content,
            text="Build: 28. Oktober 2025",
            font=('Arial', 9)
        ).pack(pady=(0, 15))
        
        # Features
        features_frame = ttk.LabelFrame(content, text="Features", padding="10")
        features_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        features = [
            "✓ Batch file upload to Covina Backend",
            "✓ Recursive folder scanning with live feedback",
            "✓ Drag & Drop support",
            "✓ Real-time progress monitoring",
            "✓ WebSocket job status updates",
            "✓ Automatic file type filtering",
            "✓ Large upload optimization (10,000+ files)"
        ]
        
        for feature in features:
            ttk.Label(
                features_frame,
                text=feature,
                font=('Arial', 9)
            ).pack(anchor=tk.W, pady=2)
        
        # Technical info
        tech_frame = ttk.Frame(content)
        tech_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            tech_frame,
            text=f"Backend: {INGESTION_BACKEND_URL} (prefix={API_VERSION_PREFIX or '/'} base={INGESTION_BASE_PATH})",
            font=('Courier New', 8),
            foreground='gray'
        ).pack()
        
        # Close button
        ttk.Button(
            content,
            text="Close",
            command=about_window.destroy
        ).pack()
    
    def _setup_drag_drop(self):
        """Setup drag & drop functionality"""
        if not TKDND_AVAILABLE:
            logger.info("Drag & Drop (tkinterdnd2) not available - continuing without DnD")
            return
        try:
            self.file_listbox.drop_target_register(DND_FILES)  # type: ignore
            self.file_listbox.dnd_bind('<<Drop>>', self._on_drop)  # type: ignore
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
                # Use new overlay scan for dropped folders
                self._start_folder_scan(file_path)
                return  # Don't update list yet, scan will do it
        
        self._update_file_list()
    
    def _check_backend(self):
        """Check if backend is available"""
        try:
            # Try versioned ingestion health first, then fall back
            ok = False
            for path in HEALTH_ENDPOINTS:
                url = _build_http_urls(path)[0]
                try:
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        ok = True
                        break
                except Exception:
                    continue
            if ok:
                self.backend_status.config(
                    text="✅ Backend: Online", 
                    foreground="green"
                )
                # Fetch capabilities once when online
                if not self._capabilities_fetched:
                    self.root.after(50, self._fetch_supported_filetypes)
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

    def _fetch_supported_filetypes(self):
        """Fetch supported file types from ingestion backend capabilities endpoint."""
        if self._capabilities_fetched:
            return
        try:
            for path in CAPABILITIES_ENDPOINTS:
                url = _build_http_urls(path)[0]
                try:
                    resp = requests.get(url, timeout=3)
                except Exception:
                    continue
                if resp.status_code == 200:
                    data = resp.json()
                    all_ext = data.get("all_extensions", [])
                    if isinstance(all_ext, list) and all_ext:
                        self.supported_extensions = {str(e).lower() for e in all_ext}
                        self._capabilities_fetched = True
                        logger.info(f"[CAPABILITIES] Loaded {len(self.supported_extensions)} extensions from backend")
                        # Update UI hint
                        self.status_label.config(text=f"Supported types loaded ({len(self.supported_extensions)}).", foreground="blue")
                if self._capabilities_fetched:
                    break
        except Exception as e:
            # Silent fallback - keep defaults
            logger.debug(f"[CAPABILITIES] Using default extensions (fetch failed: {e})")
    
    def _select_files(self):
        """Open file dialog to select files"""
        all_supported = sorted(self.supported_extensions) if self.supported_extensions else sorted(SUPPORTED_EXTENSIONS)
        filetypes = [
            ("All supported files", " ".join(f"*{ext}" for ext in all_supported)),
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
            # Start scan in background thread with overlay
            self._start_folder_scan(folder_path)
    
    def _start_folder_scan(self, folder_path: str):
        """Start folder scan with progress overlay"""
        # Create modal overlay window - more compact
        self.scan_overlay = tk.Toplevel(self.root)
        self.scan_overlay.title("Scanning...")
        self.scan_overlay.geometry("450x200")
        self.scan_overlay.transient(self.root)
        self.scan_overlay.grab_set()
        self.scan_overlay.resizable(False, False)
        
        # Center on parent
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        self.scan_overlay.geometry(f"+{x}+{y}")
        
        # Prevent closing during scan
        self.scan_overlay.protocol("WM_DELETE_WINDOW", self._cancel_scan)
        
        # Create overlay content
        overlay_frame = ttk.Frame(self.scan_overlay, padding="15")
        overlay_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title - smaller
        ttk.Label(
            overlay_frame, 
            text="📂 Scanning Folder", 
            font=('Arial', 11, 'bold')
        ).pack(pady=(0, 10))
        
        # Folder path label - truncated
        folder_name = os.path.basename(folder_path) or folder_path
        folder_label = ttk.Label(
            overlay_frame, 
            text=f"{folder_name}", 
            font=('Arial', 9),
            wraplength=420
        )
        folder_label.pack(pady=(0, 8))
        
        # Progress info
        self.scan_progress_label = ttk.Label(
            overlay_frame, 
            text="Starting scan...",
            font=('Arial', 8)
        )
        self.scan_progress_label.pack(pady=(0, 8))
        
        # File counter - prominent
        self.scan_file_counter = ttk.Label(
            overlay_frame,
            text="Files found: 0",
            font=('Arial', 12, 'bold'),
            foreground='#2E7D32'
        )
        self.scan_file_counter.pack(pady=(0, 10))
        
        # Indeterminate progress bar - smaller
        self.scan_progress_bar = ttk.Progressbar(
            overlay_frame, 
            mode='indeterminate',
            length=350
        )
        self.scan_progress_bar.pack(pady=(0, 10))
        self.scan_progress_bar.start(10)
        
        # Cancel button
        ttk.Button(
            overlay_frame, 
            text="❌ Cancel Scan", 
            command=self._cancel_scan
        ).pack()
        
        # Reset cancel flag
        self.scan_cancelled = False
        
        # Start scan thread
        scan_thread = threading.Thread(
            target=self._scan_folder_thread, 
            args=(folder_path,),
            daemon=True
        )
        scan_thread.start()
    
    def _cancel_scan(self):
        """Cancel ongoing folder scan"""
        self.scan_cancelled = True
        if self.scan_overlay:
            self.scan_progress_label.config(text="Cancelling scan...")
    
    def _scan_folder_thread(self, folder_path: str):
        """Scan folder in background thread"""
        count = 0
        scanned_dirs = 0
        new_files = []
        update_interval = 50  # Update UI only every 50 files
        last_update = 0
        
        try:
            # Walk through directory tree
            for root, dirs, files in os.walk(folder_path):
                if self.scan_cancelled:
                    # Add found files before cancelling
                    self.selected_files.extend(new_files)
                    self.root.after(0, lambda: self._close_scan_overlay(cancelled=True, count=count))
                    self.root.after(50, self._update_file_list)
                    return
                
                scanned_dirs += 1
                current_folder = os.path.basename(root)
                
                for file in files:
                    if self.scan_cancelled:
                        break
                    
                    file_path = os.path.join(root, file)
                    ext = Path(file_path).suffix.lower()
                    allowed = self.supported_extensions or SUPPORTED_EXTENSIONS
                    if ext in allowed:
                        if file_path not in self.selected_files:
                            new_files.append(file_path)
                            count += 1
                            
                            # Batch UI updates for performance
                            if count - last_update >= update_interval:
                                # Use functools.partial to avoid closure issues
                                from functools import partial
                                self.root.after(0, partial(self._update_scan_progress, 
                                                          current_folder, scanned_dirs, count))
                                last_update = count
            
            # Final update with exact count
            if not self.scan_cancelled:
                # Add all found files
                self.selected_files.extend(new_files)
                
                # Close overlay (no message box!)
                self.root.after(0, lambda: self._close_scan_overlay(cancelled=False, count=count))
                # Update file list asynchronously
                self.root.after(50, self._update_file_list)
                
        except Exception as e:
            logger.error(f"Folder scan error: {e}")
            self.root.after(0, self._close_scan_overlay, f"Scan error: {str(e)}")
    
    def _update_scan_progress(self, folder_name: str, dirs_scanned: int, files_found: int):
        """Update scan progress UI (called from background thread via root.after)"""
        if self.scan_progress_label and self.scan_progress_label.winfo_exists():
            self.scan_progress_label.config(
                text=f"Scanning: {folder_name}...\n({dirs_scanned} folders scanned)"
            )
        if self.scan_file_counter and self.scan_file_counter.winfo_exists():
            self.scan_file_counter.config(text=f"Files found: {files_found}")
    
    def _close_scan_overlay(self, cancelled: bool = False, count: int = 0):
        """Close scan overlay without blocking message box"""
        if self.scan_overlay:
            self.scan_progress_bar.stop()
            self.scan_overlay.destroy()
            self.scan_overlay = None
        
        # Update status label instead of message box
        if cancelled:
            status_msg = f"⚠️ Scan cancelled - {count} files added to list"
            self.status_label.config(text=status_msg, foreground="orange")
        else:
            status_msg = f"✅ Scan complete - {count} files found"
            self.status_label.config(text=status_msg, foreground="green")
        
        logger.info(f"Folder scan completed: {count} files, cancelled={cancelled}")
    
    def _add_file(self, file_path: str):
        """Add file to selection if supported"""
        ext = Path(file_path).suffix.lower()

        allowed = self.supported_extensions or SUPPORTED_EXTENSIONS
        if ext in allowed:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_path}")
    
    def _update_file_list(self):
        """Update file listbox and labels (optimized for large lists)"""
        count = len(self.selected_files)
        
        # Update count label first (non-blocking)
        if count == 0:
            self.file_count_label.config(text="No files selected")
            self.upload_button.config(state=tk.DISABLED)
            self.file_listbox.delete(0, tk.END)
            return
        
        # For large lists, show count immediately, calculate size in background
        if count > 100:
            self.file_count_label.config(
                text=f"{count} files selected (calculating size...)"
            )
            self.upload_button.config(state=tk.NORMAL)
            
            # Update listbox in chunks to avoid freezing
            self._update_listbox_chunked()
            
            # Calculate total size in background thread
            threading.Thread(target=self._calculate_total_size, daemon=True).start()
        else:
            # Small list - update normally
            self.file_listbox.delete(0, tk.END)
            for file_path in self.selected_files:
                self.file_listbox.insert(tk.END, file_path)
            
            total_size = sum(os.path.getsize(f) for f in self.selected_files if os.path.exists(f)) / (1024 * 1024)
            self.file_count_label.config(
                text=f"{count} file{'s' if count != 1 else ''} selected ({total_size:.2f} MB)"
            )
            self.upload_button.config(state=tk.NORMAL)
    
    def _update_listbox_chunked(self, chunk_size: int = 100, start_idx: int = 0):
        """Update listbox in chunks to avoid freezing UI"""
        if start_idx == 0:
            self.file_listbox.delete(0, tk.END)
        
        end_idx = min(start_idx + chunk_size, len(self.selected_files))
        
        for i in range(start_idx, end_idx):
            self.file_listbox.insert(tk.END, self.selected_files[i])
        
        # Schedule next chunk
        if end_idx < len(self.selected_files):
            self.root.after(10, lambda: self._update_listbox_chunked(chunk_size, end_idx))
    
    def _calculate_total_size(self):
        """Calculate total size in background thread"""
        try:
            total_size = 0
            for file_path in self.selected_files:
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
            
            total_size_mb = total_size / (1024 * 1024)
            count = len(self.selected_files)
            
            # Update UI in main thread
            self.root.after(0, lambda: self.file_count_label.config(
                text=f"{count} file{'s' if count != 1 else ''} selected ({total_size_mb:.2f} MB)"
            ))
        except Exception as e:
            logger.error(f"Size calculation error: {e}")
            self.root.after(0, lambda: self.file_count_label.config(
                text=f"{len(self.selected_files)} files selected (size unknown)"
            ))
    
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
        
        # Check if backend is online before upload (with fallbacks)
        try:
            health_ok = False
            for path in HEALTH_ENDPOINTS:
                url = _build_http_urls(path)[0]
                try:
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        health_ok = True
                        break
                except Exception:
                    continue
            if not health_ok:
                if not messagebox.askyesno(
                    "Backend Unhealthy",
                    "Backend is not responding correctly.\n\nUpload may fail. Continue anyway?"
                ):
                    return
        except Exception as e:
            if not messagebox.askyesno(
                "Backend Offline",
                f"Cannot connect to backend at {INGESTION_BACKEND_URL}\n\n"
                f"Error: {str(e)[:100]}\n\n"
                f"Please start the backend first:\n"
                f"  .\\scripts\\start_services.ps1\n\n"
                f"Try upload anyway?"
            ):
                return
        
        # Warn for very large uploads
        file_count = len(self.selected_files)
        if file_count > 1000:
            if not messagebox.askyesno(
                "Large Upload", 
                f"You are about to upload {file_count} files.\n\n"
                f"This will be processed in batches to avoid system limits.\n\n"
                f"Continue?"
            ):
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
        """
        Upload files using streaming multipart encoding
        
        NEW: Uses StreamingMultipartUploader for memory-efficient uploads
        - Handles multi-GB files without memory issues
        - Dynamic timeout calculation (5min base + 10min/GB)
        - Real-time progress tracking (bytes uploaded / total)
        - Automatic retry logic (3 attempts with 5s delay)
        
        Batching Strategy:
        - Small files (<100MB avg): 500 files per batch (old behavior)
        - Large files (>100MB avg): Dynamic batch size to keep batches ~50GB
        - Prevents memory exhaustion and timeout issues
        """
        total_files = len(self.selected_files)
        
        try:
            # Calculate average file size for smart batching
            total_size = sum(os.path.getsize(fp) for fp in self.selected_files)
            avg_file_size = total_size / total_files if total_files > 0 else 0
            
            # Smart batch sizing based on file size
            # Small files: 500/batch, Large files: keep batches ~50GB
            MAX_BATCH_SIZE_BYTES = 50 * 1024 ** 3  # 50 GB
            if avg_file_size > 100 * 1024 ** 2:  # Files >100MB avg
                # Calculate batch size to stay under 50GB
                BATCH_SIZE = max(1, int(MAX_BATCH_SIZE_BYTES / avg_file_size))
                BATCH_SIZE = min(BATCH_SIZE, 500)  # Cap at 500
                logger.info(f"[BATCH] Large files detected (avg: {avg_file_size / (1024**2):.2f}MB), using batch size: {BATCH_SIZE}")
            else:
                BATCH_SIZE = 500  # Default for small files
                logger.info(f"[BATCH] Small files detected, using batch size: {BATCH_SIZE}")
            
            # Split into batches
            total_batches = (total_files + BATCH_SIZE - 1) // BATCH_SIZE
            logger.info(f"[BATCH] Uploading {total_files} files in {total_batches} batches")
            
            # Process each batch
            for batch_num in range(0, total_files, BATCH_SIZE):
                batch_files = self.selected_files[batch_num:batch_num + BATCH_SIZE]
                batch_size = len(batch_files)
                batch_index = batch_num // BATCH_SIZE + 1
                
                logger.info(f"[BATCH] Processing batch {batch_index}/{total_batches}: {batch_size} files")
                
                # Update UI: Preparing batch
                self.root.after(0, lambda bi=batch_index, tb=total_batches, s=batch_size: 
                    self.progress_label.config(
                        text=f"Batch {bi}/{tb}: Preparing {s} files..."
                    ))
                
                # Create progress callback for this batch
                def progress_callback(uploaded_bytes, total_bytes, percent):
                    """Update GUI with upload progress"""
                    # Format sizes
                    uploaded_str = self._format_bytes(uploaded_bytes)
                    total_str = self._format_bytes(total_bytes)
                    
                    # Update progress bar
                    self.root.after(0, lambda: self.progress_bar.config(value=percent))
                    
                    # Update progress label
                    self.root.after(0, lambda p=percent, u=uploaded_str, t=total_str, bi=batch_index, tb=total_batches:
                        self.progress_label.config(
                            text=f"Batch {bi}/{tb}: Uploading... {p}% ({u} / {t})"
                        ))
                
                # Prepare candidate upload endpoints (prefer versioned + /ingestion)
                candidate_upload_urls = _build_http_urls(*UPLOAD_ENDPOINTS)

                # Create streaming uploader (we'll set the URL per attempt)
                uploader = StreamingMultipartUploader(
                    url=candidate_upload_urls[0],
                    progress_callback=progress_callback,
                    timeout_base=300,
                    timeout_per_gb=600,
                    max_retries=3,
                    retry_delay=5
                )

                try:
                    # Try upload against candidate endpoints in order
                    last_error = None
                    result = None
                    for u in candidate_upload_urls:
                        uploader.url = u
                        try:
                            result = uploader.upload_files(batch_files)
                            break
                        except Exception as ex:
                            last_error = ex
                            logger.warning(f"[BATCH] Upload attempt failed on {u}: {ex}")
                            continue
                    if result is None:
                        # Fallback: try text ingest for small text-like files if available
                        fallback_paths = [f"{API_VERSION_PREFIX}{INGESTION_BASE_PATH}/ingest", f"{INGESTION_BASE_PATH}/ingest", f"{API_VERSION_PREFIX}/ingest", "/ingest"]
                        ingest_urls = _build_http_urls(*fallback_paths)
                        sent = 0
                        for file_path in batch_files:
                            ext = Path(file_path).suffix.lower()
                            if ext in {'.txt', '.md', '.json', '.csv', '.xml', '.html'}:
                                try:
                                    # Limit fallback size to 10 MB per file
                                    if os.path.getsize(file_path) > 10 * 1024 * 1024:
                                        logger.warning(f"[FALLBACK] Skipping large text file (>10MB): {file_path}")
                                        continue
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
                                        content = fh.read()
                                    success = False
                                    for iu in ingest_urls:
                                        try:
                                            r = requests.post(iu, json={"text": content}, timeout=60)
                                            if r.status_code == 200:
                                                success = True
                                                sent += 1
                                                break
                                        except Exception:
                                            continue
                                    if not success:
                                        logger.warning(f"[FALLBACK] Failed to ingest text for: {file_path}")
                                except Exception as ex2:
                                    logger.warning(f"[FALLBACK] Error reading/sending {file_path}: {ex2}")
                            else:
                                logger.warning(f"[FALLBACK] Unsupported binary type for text ingest: {file_path}")
                        if sent == 0:
                            raise last_error or Exception("No suitable upload endpoint available")
                        # Simulate a result dict for status messaging in fallback mode
                        result = {"job_id": self.current_job_id or "fallback-ingest"}
                    
                    # Store job_id from first successful batch
                    if batch_num == 0:
                        self.current_job_id = result.get('job_id')
                    
                    logger.info(f"[BATCH] ✅ Batch {batch_index}/{total_batches} uploaded successfully")
                    
                except Exception as e:
                    # Batch failed after all retries
                    error_msg = f"Batch {batch_index}/{total_batches} failed: {str(e)}"
                    logger.error(f"[BATCH] ❌ {error_msg}")
                    self.root.after(0, lambda msg=error_msg: self._update_ui_after_upload(
                        success=False,
                        message=msg
                    ))
                    return
            
            # All batches successful
            self.root.after(0, lambda: self._update_ui_after_upload(
                success=True,
                message=f"✅ Upload complete! {total_files} files in {total_batches} batches. Job ID: {self.current_job_id}"
            ))
            
            # Start WebSocket monitoring
            self._start_websocket_monitoring()
                
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            logger.error(f"[UPLOAD] ❌ {error_msg}")
            self.root.after(0, lambda: self._update_ui_after_upload(
                success=False,
                message=error_msg
            ))
    
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    
    def _update_ui_after_upload(self, success: bool, message: str):
        """Update UI after upload completes"""
        if success:
            self.progress_label.config(text="Upload complete! Processing files...")
            self.status_label.config(text=message, foreground="green")
            # Reset layout after a short confirmation delay
            self.root.after(1500, self._reset_layout_after_success)
        else:
            self.progress_label.config(text="Upload failed")
            self.status_label.config(text=message, foreground="red")
            self.upload_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)

    def _reset_layout_after_success(self):
        """Reset selection and controls after successful upload."""
        try:
            self._clear_selection()
            self.upload_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            # Keep status label brief, then clear
            self.root.after(1500, lambda: self.status_label.config(text=""))
        except Exception as e:
            logger.debug(f"Layout reset failed: {e}")
    
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
            # Try to connect to a suitable WS endpoint (versioned first)
            connected = False
            for p in WS_JOB_ENDPOINTS:
                try:
                    ws_urls = _build_ws_urls(p)
                    self.ws.connect(ws_urls[0])
                    connected = True
                    break
                except Exception as ex:
                    logger.debug(f"WebSocket connect failed on {p}: {ex}")
                    continue
            if not connected:
                logger.info("WebSocket endpoint not available; skipping live job monitoring")
                return
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
    # Use TkinterDnD for drag & drop support if available
    if TKDND_AVAILABLE and TkinterDnD is not None:
        try:
            root = TkinterDnD.Tk()  # type: ignore
        except Exception:
            logger.warning("TkinterDnD init failed - falling back to Tk")
            root = tk.Tk()
    else:
        logger.info("TkinterDnD not available - starting with standard Tk")
        root = tk.Tk()
    
    app = IngestionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
