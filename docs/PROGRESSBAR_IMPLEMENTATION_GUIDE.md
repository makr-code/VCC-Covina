# Progressbar für Bulk Copy - Implementierungsanleitung

**Datum:** 14. Oktober 2025, 14:45 Uhr  
**Status:** 🔨 READY TO IMPLEMENT  
**Aufwand:** 4-6 Stunden  
**Priorität:** MEDIUM (UX-Verbesserung)

---

## 🎯 Ziel

**Problem:** User sieht 15+ Minuten lang einen leeren Screen während robocopy 7.7 GB kopiert.

**Lösung:** Real-Time Progressbar mit:
- Progress Percentage (0-100%)
- Files Copied Count
- Data Copied (GB)
- Copy Rate (MB/s)
- Estimated Time Remaining (ETA)

---

## ✅ Bereits Implementiert

### 1. Backend-Seite (teilweise fertig)

**✅ Pydantic Models erweitert:**
```python
# File: ingestion_backend.py Lines 124-148

class BulkCopyProgress(BaseModel):
    """Progress information for bulk copy operation"""
    percent_complete: float = 0.0
    files_copied: int = 0
    total_files: int = 0
    bytes_copied: int = 0
    total_bytes: int = 0
    copy_rate_mbps: float = 0.0
    eta_seconds: int = 0
    current_file: str = ""
    status: str = "preparing"  # preparing, copying, completed, error

class DirectoryScanStatusResponse(BaseModel):
    """Response for scan status query"""
    scan_job_id: str
    status: str  # scanning, creating_jobs, completed, error
    files_found: int
    bulk_copy_progress: Optional[BulkCopyProgress] = None  # 🆕 NEW!
```

**✅ WebSocket Broadcast Helper:**
```python
# File: ingestion_backend.py Lines 252-276

async def _broadcast_bulk_copy_progress(self):
    """🆕 Broadcast bulk copy progress to all WebSocket clients"""
    if not hasattr(self, 'bulk_copy_progress'):
        return
    
    message = {
        "type": "bulk_copy_progress",
        "scan_job_id": self.scan_job_id,
        "progress": {
            "percent_complete": self.bulk_copy_progress.percent_complete,
            "files_copied": self.bulk_copy_progress.files_copied,
            "bytes_copied": self.bulk_copy_progress.bytes_copied,
            "bytes_gb": round(self.bulk_copy_progress.bytes_copied / (1024**3), 2),
            "copy_rate_mbps": round(self.bulk_copy_progress.copy_rate_mbps, 1),
            "status": self.bulk_copy_progress.status
        }
    }
    
    await self.broadcast(message)
```

**✅ Streaming Bulk Copy Modul:**
```python
# File: ingestion/bulk_copy_streaming.py (komplett fertig!)

from ingestion.bulk_copy_streaming import BulkCopyStreaming, CopyProgress

# Usage:
async def on_progress(progress: CopyProgress):
    # Update UI here
    print(f"Progress: {progress.percent_complete:.1f}%")

copier = BulkCopyStreaming(
    source=Path("/source"),
    destination=Path("/dest"),
    progress_callback=on_progress
)

result = await copier.execute()
```

---

## 🔨 Noch zu Implementieren

### 2. Backend Integration (1-2 Stunden)

**Datei:** `ingestion_backend.py`  
**Location:** Lines 381-460 (Methode `_bulk_copy_directory`)

**Aufgabe:** Ersetze die aktuelle `_bulk_copy_directory` Methode mit der neuen Streaming-Version.

**Code-Änderung:**

```python
async def _bulk_copy_directory(self):
    """
    Copy entire directory to temp_dir using OS-level commands (fast!).
    🆕 WITH STREAMING PROGRESS UPDATES
    """
    from ingestion.bulk_copy_streaming import BulkCopyStreaming
    
    logger.info(f"📦 [SCAN {self.scan_job_id}] Bulk copy: {self.directory_path} → {self.temp_dir}")
    
    # 🆕 Initialize progress tracking
    self.bulk_copy_progress = BulkCopyProgress(status="preparing")
    
    async def on_progress(progress):
        """Callback for progress updates"""
        # Update our progress object
        self.bulk_copy_progress.percent_complete = progress.percent_complete
        self.bulk_copy_progress.files_copied = progress.files_copied
        self.bulk_copy_progress.bytes_copied = progress.bytes_copied
        self.bulk_copy_progress.copy_rate_mbps = progress.copy_rate_mbps
        self.bulk_copy_progress.status = progress.status
        
        # Broadcast to WebSocket clients
        await self._broadcast_bulk_copy_progress()
    
    # 🆕 Use streaming bulk copy
    copier = BulkCopyStreaming(
        source=self.directory_path,
        destination=self.temp_dir,
        progress_callback=on_progress,
        broadcast_interval=5.0  # Update every 5 seconds
    )
    
    timeout_seconds = 1800  # 30 minutes
    
    try:
        final_progress = await copier.execute(timeout=timeout_seconds)
        
        logger.info(
            f"✅ [SCAN {self.scan_job_id}] Bulk copy complete: "
            f"{final_progress.files_copied} files, "
            f"{final_progress.bytes_copied / (1024**3):.2f} GB"
        )
        
        # Re-initialize scanner to point to LOCAL copy
        logger.info(f"🔄 [SCAN {self.scan_job_id}] Re-initializing scanner for local copy...")
        self.scanner = DirectoryScanner(
            root=self.temp_dir,  # ✅ Now scans local copy!
            classifier=FileClassifier(),
            compute_hashes=False
        )
        
    except asyncio.TimeoutError:
        logger.error(f"❌ [SCAN {self.scan_job_id}] Bulk copy timeout after {timeout_seconds}s")
        raise HTTPException(status_code=504, detail=f"Bulk copy timeout after {timeout_seconds}s")
    except Exception as e:
        logger.error(f"❌ [SCAN {self.scan_job_id}] Bulk copy error: {e}")
        raise
```

**⚠️ Wichtig:** Die Methode ist lang (80+ Zeilen). Am besten:
1. Alte Methode komplett löschen (Lines 381-460)
2. Neue Methode einfügen
3. Testen mit kleinem Directory

---

### 3. Status Endpoint erweitern (30 Min)

**Datei:** `ingestion_backend.py`  
**Location:** Finde die Route `/scan-status/{scan_job_id}`

**Aufgabe:** Füge `bulk_copy_progress` zum Response hinzu.

**Code-Änderung:**

```python
@app.get("/scan-status/{scan_job_id}", response_model=DirectoryScanStatusResponse)
async def get_scan_status(scan_job_id: str):
    """Get status of directory scan/upload job"""
    if scan_job_id not in scan_jobs:
        raise HTTPException(status_code=404, detail="Scan job not found")
    
    job = scan_jobs[scan_job_id]
    
    return DirectoryScanStatusResponse(
        scan_job_id=scan_job_id,
        status=job.status,
        files_found=job.files_found,
        bulk_copy_progress=getattr(job, 'bulk_copy_progress', None)  # 🆕 NEW!
    )
```

---

### 4. Frontend Progress Modal (2-3 Stunden)

**Datei:** `covina_app_phase4.py` oder separate Datei `views/directory_upload_view.py`

**Location:** DirectoryUploadView class

**Aufgabe:** Erstelle einen Progress Modal Dialog.

**UI-Design:**

```
┌─────────────────────────────────────────────┐
│  📦 Bulk Copy in Progress...                │
│                                             │
│  ████████████░░░░░░░░░░░░░ 65%             │
│                                             │
│  Files Copied:     1,234 / ~2,000          │
│  Data Copied:      4.8 GB / ~7.7 GB        │
│  Copy Rate:        145.3 MB/s              │
│  Time Remaining:   ~3 minutes              │
│                                             │
│  Status: Copying files...                  │
│                                             │
│         [ Cancel ]         [ Hide ]         │
└─────────────────────────────────────────────┘
```

**Code-Implementierung:**

```python
import customtkinter as ctk
from typing import Optional
import time

class BulkCopyProgressModal(ctk.CTkToplevel):
    """Modal Dialog für Bulk Copy Progress"""
    
    def __init__(self, parent, scan_job_id: str):
        super().__init__(parent)
        
        self.scan_job_id = scan_job_id
        self.parent_window = parent
        
        # Window setup
        self.title("Bulk Copy Progress")
        self.geometry("500x350")
        self.resizable(False, False)
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        # Layout
        self._create_widgets()
        
        # Start polling
        self.poll_interval = 2000  # 2 seconds
        self._poll_progress()
    
    def _create_widgets(self):
        """Create UI elements"""
        # Header
        self.header = ctk.CTkLabel(
            self,
            text="📦 Bulk Copy in Progress...",
            font=("Arial", 16, "bold")
        )
        self.header.pack(pady=20)
        
        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self,
            width=400,
            height=20
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)
        
        # Progress Percentage
        self.percent_label = ctk.CTkLabel(
            self,
            text="0%",
            font=("Arial", 14)
        )
        self.percent_label.pack()
        
        # Stats Frame
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(pady=20, padx=20, fill="both")
        
        # Files Copied
        self.files_label = ctk.CTkLabel(
            stats_frame,
            text="Files Copied: 0",
            anchor="w"
        )
        self.files_label.pack(anchor="w", padx=10, pady=5)
        
        # Data Copied
        self.data_label = ctk.CTkLabel(
            stats_frame,
            text="Data Copied: 0.0 GB",
            anchor="w"
        )
        self.data_label.pack(anchor="w", padx=10, pady=5)
        
        # Copy Rate
        self.rate_label = ctk.CTkLabel(
            stats_frame,
            text="Copy Rate: 0.0 MB/s",
            anchor="w"
        )
        self.rate_label.pack(anchor="w", padx=10, pady=5)
        
        # ETA
        self.eta_label = ctk.CTkLabel(
            stats_frame,
            text="Time Remaining: Calculating...",
            anchor="w"
        )
        self.eta_label.pack(anchor="w", padx=10, pady=5)
        
        # Status
        self.status_label = ctk.CTkLabel(
            stats_frame,
            text="Status: Preparing...",
            anchor="w"
        )
        self.status_label.pack(anchor="w", padx=10, pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=20)
        
        self.hide_button = ctk.CTkButton(
            button_frame,
            text="Hide",
            command=self.withdraw
        )
        self.hide_button.pack(side="left", padx=10)
        
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            fg_color="red",
            hover_color="darkred",
            command=self._cancel_copy
        )
        self.cancel_button.pack(side="left", padx=10)
    
    def _poll_progress(self):
        """Poll backend for progress updates"""
        try:
            # Call backend API
            response = requests.get(
                f"http://127.0.0.1:45679/scan-status/{self.scan_job_id}",
                timeout=2
            )
            
            if response.status_code == 200:
                data = response.json()
                progress = data.get("bulk_copy_progress")
                
                if progress:
                    self._update_ui(progress)
                    
                    # Check if completed
                    if progress["status"] == "completed":
                        self._on_complete()
                        return
                    elif progress["status"] == "error":
                        self._on_error()
                        return
        
        except Exception as e:
            print(f"⚠️ Progress poll error: {e}")
        
        # Continue polling
        self.after(self.poll_interval, self._poll_progress)
    
    def _update_ui(self, progress: dict):
        """Update UI with latest progress"""
        # Progress bar
        percent = progress["percent_complete"]
        self.progress_bar.set(percent / 100.0)
        self.percent_label.configure(text=f"{percent:.1f}%")
        
        # Files
        files = progress["files_copied"]
        self.files_label.configure(text=f"Files Copied: {files:,}")
        
        # Data
        data_gb = progress["bytes_gb"]
        self.data_label.configure(text=f"Data Copied: {data_gb:.2f} GB")
        
        # Rate
        rate = progress["copy_rate_mbps"]
        self.rate_label.configure(text=f"Copy Rate: {rate:.1f} MB/s")
        
        # ETA
        if rate > 0 and percent < 100:
            remaining_percent = 100 - percent
            eta_seconds = int((remaining_percent / percent) * (data_gb * 1024 / rate))
            eta_mins = eta_seconds // 60
            self.eta_label.configure(text=f"Time Remaining: ~{eta_mins} minutes")
        else:
            self.eta_label.configure(text="Time Remaining: Calculating...")
        
        # Status
        status = progress["status"]
        status_text = {
            "preparing": "Status: Preparing copy...",
            "copying": "Status: Copying files...",
            "completed": "Status: ✅ Complete!",
            "error": "Status: ❌ Error!"
        }
        self.status_label.configure(text=status_text.get(status, f"Status: {status}"))
    
    def _on_complete(self):
        """Handle completion"""
        self.header.configure(text="✅ Bulk Copy Complete!")
        self.cancel_button.configure(state="disabled")
        
        # Auto-close after 3 seconds
        self.after(3000, self.destroy)
    
    def _on_error(self):
        """Handle error"""
        self.header.configure(text="❌ Bulk Copy Failed!")
        self.cancel_button.configure(text="Close", fg_color="gray")
    
    def _cancel_copy(self):
        """Cancel the copy operation"""
        # TODO: Implement cancel endpoint
        self.destroy()


# Integration in DirectoryUploadView:

class DirectoryUploadView:
    def _on_upload_directory(self):
        """Handle directory upload button click"""
        directory = filedialog.askdirectory(title="Select Directory to Upload")
        
        if directory:
            # Validate directory
            # ...
            
            # Start scan/upload
            response = requests.post(
                "http://127.0.0.1:45679/upload-directory",
                json={"directory_path": directory}
            )
            
            if response.status_code == 200:
                data = response.json()
                scan_job_id = data["scan_job_id"]
                
                # 🆕 Show progress modal
                progress_modal = BulkCopyProgressModal(
                    parent=self.root,
                    scan_job_id=scan_job_id
                )
                progress_modal.focus()
```

---

### 5. WebSocket Alternative (Optional - 1 Stunde)

**Vorteile:** Echtzeit-Updates ohne Polling

**Datei:** `covina_app_phase4.py`

**Code:**

```python
import websocket
import json
import threading

class BulkCopyProgressModal(ctk.CTkToplevel):
    def __init__(self, parent, scan_job_id: str):
        super().__init__(parent)
        # ... existing code ...
        
        # 🆕 WebSocket connection
        self._connect_websocket()
    
    def _connect_websocket(self):
        """Connect to WebSocket for real-time updates"""
        def on_message(ws, message):
            data = json.loads(message)
            
            if data.get("type") == "bulk_copy_progress":
                if data.get("scan_job_id") == self.scan_job_id:
                    progress = data["progress"]
                    
                    # Update UI (must use self.after for thread-safety)
                    self.after(0, lambda: self._update_ui(progress))
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket closed")
        
        def on_open(ws):
            print("WebSocket connected")
        
        # Create WebSocket connection
        ws_url = "ws://127.0.0.1:45679/ws/jobs"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Run in separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        ws_thread.start()
    
    def destroy(self):
        """Override destroy to close WebSocket"""
        if hasattr(self, 'ws'):
            self.ws.close()
        super().destroy()
```

---

## 🧪 Testing Plan

### Test 1: Small Directory (<100 MB)
```
Expected: Progress updates every 5s
         Complete within 30s
         Accurate file count
```

### Test 2: Medium Directory (1-2 GB)
```
Expected: Smooth progress bar
         Copy rate 50-200 MB/s
         ETA within 20% accuracy
```

### Test 3: Large Directory (7.7 GB)
```
Expected: No timeout (1800s limit)
         Progress updates consistent
         Final stats match actual
         Clean cleanup after completion
```

### Test 4: Network Timeout
```
Expected: Graceful error handling
         Progress shows "error" status
         User can retry
```

### Test 5: User Cancel
```
Expected: Cancel button works
         Temp files cleaned up
         Job marked as cancelled
```

---

## 📊 Expected Performance

**Before:**
```
User Experience:
  - Click "Upload Directory"
  - Screen freezes
  - No feedback for 15+ minutes
  - User thinks app crashed
  
Rating: 1/5 ⭐ (terrible UX)
```

**After:**
```
User Experience:
  - Click "Upload Directory"
  - Progress modal appears
  - Real-time updates every 5s
  - Can hide modal and continue working
  - Clear ETA and stats
  
Rating: 5/5 ⭐⭐⭐⭐⭐ (excellent UX)
```

---

## 🚀 Implementierungs-Reihenfolge

1. **Backend Integration** (1-2h)
   - Ersetze `_bulk_copy_directory` Methode
   - Teste mit kleinem Directory
   - Validiere WebSocket Broadcasts

2. **Status Endpoint** (30min)
   - Erweitere `/scan-status/` Response
   - Teste API Response

3. **Frontend Modal** (2-3h)
   - Erstelle `BulkCopyProgressModal` class
   - Integriere in DirectoryUploadView
   - Style mit customtkinter

4. **Testing** (1h)
   - Test mit verschiedenen Directory-Größen
   - Verify ETA Accuracy
   - Test Cancel-Funktion

5. **Polish** (30min)
   - Error Handling verbessern
   - Loading-Animationen
   - Cleanup Code

**Total:** 4-6 Stunden

---

## 📝 Checkliste

- [ ] Backend: `_bulk_copy_directory` Methode ersetzen
- [ ] Backend: Status Endpoint erweitern
- [ ] Backend: WebSocket Broadcast testen
- [ ] Frontend: Progress Modal erstellen
- [ ] Frontend: Polling implementieren (oder WebSocket)
- [ ] Frontend: UI stylen
- [ ] Testing: Small directory (<100 MB)
- [ ] Testing: Medium directory (1-2 GB)
- [ ] Testing: Large directory (7.7 GB)
- [ ] Testing: Error handling
- [ ] Testing: Cancel functionality
- [ ] Documentation: Update README
- [ ] Documentation: Add screenshots

---

## 📚 Referenzen

**Bereits erstellt:**
- ✅ `ingestion/bulk_copy_streaming.py` (komplett)
- ✅ `ingestion_backend.py` (Pydantic Models + Broadcast Helper)
- ✅ `docs/PROGRESSBAR_IMPLEMENTATION.md` (diese Datei)

**Zu ändern:**
- `ingestion_backend.py` Lines 381-460 (`_bulk_copy_directory`)
- `ingestion_backend.py` Status Endpoint (`/scan-status/`)
- `covina_app_phase4.py` (DirectoryUploadView + BulkCopyProgressModal)

**Zu erstellen:**
- Optional: `views/bulk_copy_progress_modal.py` (separates UI-Modul)

---

**Erstellt:** 14. Oktober 2025, 14:45 Uhr  
**Autor:** GitHub Copilot  
**Version:** 1.0  
**Status:** READY TO IMPLEMENT 🚀
