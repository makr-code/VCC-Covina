# Frontend Progressbar Implementation - Bulk Copy Progress Feedback

**Feature:** Real-time progress feedback during robocopy bulk copy phase  
**Datum:** 14. Oktober 2025  
**Priority:** MEDIUM (User Experience)  
**Aufwand:** 4-6 Stunden  
**Status:** TODO (Design Complete)

---

## 🎯 Problem Statement

**Current Situation:**
```
User uploads 7.7 GB directory from Y:\
Backend: robocopy runs for 15+ minutes
Frontend: Shows "scanning..." with NO progress
User: Thinks system is frozen ❌
```

**User Experience Issue:**
- No visual feedback during bulk copy (10-20 minutes)
- User can't see if system is working or frozen
- No ETA or progress indication
- Leads to user canceling upload prematurely

**Expected User Experience:**
```
Upload Started
  ↓
[████████░░░░░░░░░░] 40% - Copying files...
7.2 GB / 7.7 GB @ 21.3 MB/s
ETA: ~2 minutes

User: ✅ Can see progress, knows it's working
```

---

## 📊 Solution Design

### Architecture Overview

```
┌─────────────────┐         WebSocket          ┌──────────────────┐
│                 │  ───────────────────────>   │                  │
│  Backend        │   Progress Updates          │  Frontend        │
│  (robocopy)     │   every 5-10 seconds        │  (Progressbar)   │
│                 │  <───────────────────────   │                  │
└─────────────────┘                             └──────────────────┘
        │
        ├─ Parse robocopy output
        ├─ Calculate % complete
        ├─ Estimate ETA
        └─ Broadcast via WebSocket
```

### Data Flow

```
1. robocopy stdout → Real-time parsing
2. Extract stats (bytes, files, %)
3. Calculate rate & ETA
4. WebSocket broadcast
5. Frontend updates Progressbar
```

---

## 🔧 Backend Implementation

### File: `ingestion_backend.py`

#### 1. Update `_bulk_copy_directory()` Method (Lines 348-438)

**Current (v3.5.1):**
```python
async def _bulk_copy_directory(self):
    # ...
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Output captured but NOT streamed ❌
```

**New (with Progress Streaming):**
```python
async def _bulk_copy_directory(self):
    """
    Copy entire directory with REAL-TIME progress updates via WebSocket.
    """
    import platform
    import subprocess
    import re
    from datetime import datetime
    
    source = str(self.directory_path)
    dest = str(self.temp_dir)
    
    logger.info(f"📦 [SCAN {self.scan_job_id}] Bulk copy: {source} → {dest}")
    
    # Initialize progress state
    self.bulk_copy_progress = {
        "bytes_copied": 0,
        "bytes_total": 0,
        "percent": 0,
        "files_copied": 0,
        "files_total": 0,
        "rate_mbps": 0.0,
        "eta_seconds": 0,
        "phase": "initializing"
    }
    
    def parse_robocopy_output(line: str):
        """Parse robocopy output for progress stats"""
        # Example robocopy output:
        # "  New File         123456789    file.txt"
        # "       Files :         3    0    3    0    0    0"
        # "       Bytes : 7.23 GB  0  7.23 GB  0  0  0"
        
        # Parse file count
        if "Files :" in line:
            # Format: "Files :  Copied  Skipped  Mismatch  FAILED  Extras"
            match = re.search(r'Files\s*:\s*(\d+)\s+(\d+)\s+(\d+)', line)
            if match:
                copied = int(match.group(1))
                self.bulk_copy_progress["files_copied"] = copied
        
        # Parse bytes
        if "Bytes :" in line:
            # Format: "Bytes : 7.23 GB  0  7.23 GB  0  0  0"
            match = re.search(r'Bytes\s*:\s*([\d.]+\s*[KMGT]?B)', line)
            if match:
                size_str = match.group(1)
                bytes_copied = parse_size_string(size_str)
                self.bulk_copy_progress["bytes_copied"] = bytes_copied
        
        # Parse percentage (if available)
        if "%" in line:
            match = re.search(r'(\d+)%', line)
            if match:
                self.bulk_copy_progress["percent"] = int(match.group(1))
    
    def parse_size_string(size_str: str) -> int:
        """Convert '7.23 GB' to bytes"""
        match = re.match(r'([\d.]+)\s*([KMGT]?B)', size_str.strip())
        if not match:
            return 0
        
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4
        }
        
        return int(value * multipliers.get(unit, 1))
    
    async def copy_with_progress():
        """Run robocopy with real-time progress streaming"""
        nonlocal cmd
        
        if platform.system() == "Windows":
            # Windows: robocopy with VERBOSE output
            cmd = [
                "robocopy",
                source,
                dest,
                "/E",          # Copy subdirectories
                "/MT:16",      # Multi-threaded
                "/R:2",        # Retry 2 times
                "/W:5",        # Wait 5 seconds
                "/BYTES",      # Show sizes in bytes
                "/V",          # Verbose (show files being copied)
                "/TS",         # Include timestamps
                "/FP",         # Include full paths
                "/NP"          # No percentage (we parse manually)
            ]
        else:
            # Linux: rsync with progress
            cmd = [
                "rsync",
                "-av",
                "--progress",
                "--stats",
                f"{source}/",
                dest
            ]
        
        logger.info(f"🔧 [SCAN {self.scan_job_id}] Starting: {' '.join(cmd)}")
        
        # Start subprocess with PIPE for stdout
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line-buffered
        )
        
        start_time = datetime.now()
        last_broadcast = start_time
        broadcast_interval = 5.0  # Broadcast every 5 seconds
        
        try:
            # Stream output line by line
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                
                # Parse for progress stats
                parse_robocopy_output(line)
                
                # Calculate rate & ETA
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 0 and self.bulk_copy_progress["bytes_copied"] > 0:
                    rate_bps = self.bulk_copy_progress["bytes_copied"] / elapsed
                    self.bulk_copy_progress["rate_mbps"] = round(rate_bps / 1024**2, 1)
                    
                    # Estimate total size (if not yet known)
                    if self.bulk_copy_progress["bytes_total"] == 0:
                        # Use current bytes as rough estimate
                        self.bulk_copy_progress["bytes_total"] = self.bulk_copy_progress["bytes_copied"]
                    
                    # Calculate ETA
                    remaining_bytes = self.bulk_copy_progress["bytes_total"] - self.bulk_copy_progress["bytes_copied"]
                    if rate_bps > 0:
                        eta_seconds = int(remaining_bytes / rate_bps)
                        self.bulk_copy_progress["eta_seconds"] = eta_seconds
                    
                    # Calculate percentage
                    if self.bulk_copy_progress["bytes_total"] > 0:
                        percent = int((self.bulk_copy_progress["bytes_copied"] / self.bulk_copy_progress["bytes_total"]) * 100)
                        self.bulk_copy_progress["percent"] = min(100, percent)
                
                # Broadcast progress via WebSocket (throttled)
                now = datetime.now()
                if (now - last_broadcast).total_seconds() >= broadcast_interval:
                    await self._broadcast_bulk_copy_progress()
                    last_broadcast = now
                    
                    # Also log progress
                    logger.info(
                        f"📊 [SCAN {self.scan_job_id}] "
                        f"{self.bulk_copy_progress['percent']}% - "
                        f"{self.bulk_copy_progress['bytes_copied'] / 1024**3:.2f} GB @ "
                        f"{self.bulk_copy_progress['rate_mbps']} MB/s - "
                        f"ETA: {self.bulk_copy_progress['eta_seconds']}s"
                    )
            
            # Wait for completion
            return_code = process.wait()
            
            # Check exit code
            if platform.system() == "Windows" and return_code >= 8:
                stderr = process.stderr.read()
                raise RuntimeError(f"robocopy failed (code {return_code}): {stderr}")
            elif platform.system() != "Windows" and return_code != 0:
                stderr = process.stderr.read()
                raise RuntimeError(f"rsync failed (code {return_code}): {stderr}")
            
            # Final progress broadcast (100%)
            self.bulk_copy_progress["percent"] = 100
            self.bulk_copy_progress["phase"] = "complete"
            await self._broadcast_bulk_copy_progress()
            
            logger.info(f"✅ [SCAN {self.scan_job_id}] Bulk copy complete")
            
        except Exception as e:
            logger.error(f"❌ [SCAN {self.scan_job_id}] Copy error: {e}")
            process.kill()
            raise
    
    # Execute with timeout
    loop = asyncio.get_running_loop()
    timeout_seconds = 1800  # 30 minutes
    
    try:
        await asyncio.wait_for(
            copy_with_progress(),
            timeout=timeout_seconds
        )
        
        # Re-initialize scanner to local copy
        logger.info(f"🔄 [SCAN {self.scan_job_id}] Re-initializing scanner...")
        self.scanner = DirectoryScanner(
            root=self.temp_dir,
            classifier=FileClassifier(),
            compute_hashes=False
        )
        logger.info(f"✅ [SCAN {self.scan_job_id}] Scanner ready")
        
    except asyncio.TimeoutError:
        raise TimeoutError(f"Bulk copy timeout after {timeout_seconds}s")
```

#### 2. Add WebSocket Broadcast Method

```python
async def _broadcast_bulk_copy_progress(self):
    """Broadcast bulk copy progress via WebSocket"""
    if not hasattr(self, 'bulk_copy_progress'):
        return
    
    message = {
        "type": "bulk_copy_progress",
        "scan_job_id": self.scan_job_id,
        "progress": self.bulk_copy_progress
    }
    
    # Broadcast to all connected clients
    await websocket_manager.broadcast(message)
```

#### 3. Update Status Endpoint

```python
# In DirectoryScanResponse model
class DirectoryScanResponse(BaseModel):
    scan_job_id: str
    status: str
    files_found: int
    upload_jobs_created: int
    upload_job_ids: List[str]
    error: Optional[str] = None
    elapsed_time: float = 0.0
    bulk_copy_progress: Optional[dict] = None  # ← NEW!

# In /scan/{scan_job_id} endpoint
@app.get("/scan/{scan_job_id}", response_model=DirectoryScanResponse)
async def get_scan_status(scan_job_id: str):
    job = active_scan_jobs.get(scan_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    
    # Include bulk copy progress if available
    bulk_copy_progress = None
    if hasattr(job, 'bulk_copy_progress'):
        bulk_copy_progress = job.bulk_copy_progress
    
    return DirectoryScanResponse(
        scan_job_id=job.scan_job_id,
        status=job.status,
        files_found=job.files_found,
        upload_jobs_created=len(job.upload_job_ids),
        upload_job_ids=job.upload_job_ids,
        error=job.error_message,
        elapsed_time=(datetime.now() - job.start_time).total_seconds(),
        bulk_copy_progress=bulk_copy_progress  # ← NEW!
    )
```

---

## 🖥️ Frontend Implementation

### File: `covina_app_phase4.py`

#### 1. Update DirectoryUploadView

```python
class DirectoryUploadView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        # ... existing code ...
        
        # Add progress modal (hidden by default)
        self.progress_modal = None
    
    def _upload_directory(self):
        """Start directory upload"""
        directory_path = self.directory_entry.get().strip()
        if not directory_path:
            messagebox.showerror("Error", "Bitte Verzeichnis auswählen")
            return
        
        # Show progress modal
        self._show_progress_modal()
        
        # Start upload in thread
        threading.Thread(
            target=self._upload_directory_thread,
            args=(directory_path,),
            daemon=True
        ).start()
    
    def _show_progress_modal(self):
        """Show progress modal dialog"""
        self.progress_modal = ctk.CTkToplevel(self)
        self.progress_modal.title("Directory Upload")
        self.progress_modal.geometry("500x300")
        self.progress_modal.transient(self)
        self.progress_modal.grab_set()
        
        # Title
        title = ctk.CTkLabel(
            self.progress_modal,
            text="Uploading Directory...",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=20)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_modal,
            width=400,
            height=20
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            self.progress_modal,
            text="Initializing...",
            font=("Arial", 12)
        )
        self.progress_label.pack(pady=5)
        
        # Stats label
        self.stats_label = ctk.CTkLabel(
            self.progress_modal,
            text="",
            font=("Arial", 10)
        )
        self.stats_label.pack(pady=5)
        
        # ETA label
        self.eta_label = ctk.CTkLabel(
            self.progress_modal,
            text="",
            font=("Arial", 10)
        )
        self.eta_label.pack(pady=5)
        
        # Cancel button
        cancel_btn = ctk.CTkButton(
            self.progress_modal,
            text="Cancel",
            command=self._cancel_upload,
            fg_color="red"
        )
        cancel_btn.pack(pady=20)
    
    def _upload_directory_thread(self, directory_path):
        """Upload directory in background thread"""
        try:
            # Start upload
            response = requests.post(
                f"{INGESTION_URL}/upload/directory",
                data={
                    "directory_path": directory_path,
                    "chunk_size": 50
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                scan_job_id = result["scan_job_id"]
                
                # Monitor progress
                self._monitor_upload_progress(scan_job_id)
            else:
                self._close_progress_modal()
                messagebox.showerror("Error", f"Upload failed: {response.text}")
        
        except Exception as e:
            self._close_progress_modal()
            messagebox.showerror("Error", f"Upload error: {str(e)}")
    
    def _monitor_upload_progress(self, scan_job_id):
        """Monitor upload progress via status endpoint + WebSocket"""
        # Poll status endpoint every 2 seconds
        while True:
            try:
                response = requests.get(
                    f"{INGESTION_URL}/scan/{scan_job_id}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    status = response.json()
                    
                    # Update progress from bulk_copy_progress
                    if status.get("bulk_copy_progress"):
                        self._update_progress_ui(status["bulk_copy_progress"])
                    
                    # Check if completed
                    if status["status"] in ["completed", "error"]:
                        self._close_progress_modal()
                        
                        if status["status"] == "completed":
                            messagebox.showinfo(
                                "Success",
                                f"Upload completed!\n"
                                f"Files: {status['files_found']}\n"
                                f"Jobs: {status['upload_jobs_created']}"
                            )
                        else:
                            messagebox.showerror(
                                "Error",
                                f"Upload failed: {status.get('error', 'Unknown error')}"
                            )
                        break
                
                time.sleep(2)
            
            except Exception as e:
                logger.error(f"Progress monitor error: {e}")
                time.sleep(2)
    
    def _update_progress_ui(self, progress):
        """Update progress UI from progress dict"""
        try:
            # Update progress bar
            percent = progress.get("percent", 0) / 100.0
            self.after(0, lambda: self.progress_bar.set(percent))
            
            # Update progress label
            bytes_copied = progress.get("bytes_copied", 0)
            bytes_total = progress.get("bytes_total", 0)
            
            if bytes_total > 0:
                copied_gb = bytes_copied / 1024**3
                total_gb = bytes_total / 1024**3
                progress_text = f"{progress.get('percent', 0)}% - Copying files..."
                self.after(0, lambda: self.progress_label.configure(text=progress_text))
                
                # Update stats label
                rate = progress.get("rate_mbps", 0)
                stats_text = f"{copied_gb:.2f} GB / {total_gb:.2f} GB @ {rate} MB/s"
                self.after(0, lambda: self.stats_label.configure(text=stats_text))
                
                # Update ETA label
                eta_seconds = progress.get("eta_seconds", 0)
                if eta_seconds > 0:
                    eta_minutes = eta_seconds / 60
                    eta_text = f"ETA: ~{eta_minutes:.1f} minutes"
                    self.after(0, lambda: self.eta_label.configure(text=eta_text))
        
        except Exception as e:
            logger.error(f"Progress UI update error: {e}")
    
    def _close_progress_modal(self):
        """Close progress modal"""
        if self.progress_modal:
            self.after(0, lambda: self.progress_modal.destroy())
            self.progress_modal = None
    
    def _cancel_upload(self):
        """Cancel upload"""
        # TODO: Implement cancel endpoint
        self._close_progress_modal()
        messagebox.showinfo("Cancelled", "Upload cancelled")
```

---

## 📋 Implementation Checklist

### Phase 1: Backend (2-3 hours)

- [ ] Update `_bulk_copy_directory()` to use `subprocess.Popen()`
- [ ] Implement `parse_robocopy_output()` function
- [ ] Implement `parse_size_string()` helper
- [ ] Add `self.bulk_copy_progress` state tracking
- [ ] Implement `copy_with_progress()` async function
- [ ] Add `_broadcast_bulk_copy_progress()` method
- [ ] Update `DirectoryScanResponse` model (add `bulk_copy_progress`)
- [ ] Update `/scan/{scan_job_id}` endpoint
- [ ] Test robocopy output parsing
- [ ] Validate WebSocket broadcasts

### Phase 2: Frontend (2-3 hours)

- [ ] Create progress modal dialog
- [ ] Add progress bar widget
- [ ] Add labels (progress, stats, ETA)
- [ ] Implement `_monitor_upload_progress()` polling
- [ ] Implement `_update_progress_ui()` method
- [ ] Add cancel functionality
- [ ] Test UI responsiveness
- [ ] Validate progress updates

### Phase 3: Testing (1 hour)

- [ ] Test with small directory (<100 MB)
- [ ] Test with medium directory (1-5 GB)
- [ ] Test with large directory (7.7 GB - Y:\data\00_eu lex)
- [ ] Validate progress accuracy
- [ ] Validate ETA calculation
- [ ] Test cancel functionality
- [ ] Test error scenarios

---

## 🎯 Expected Result

**Before:**
```
User uploads 7.7 GB
Frontend shows: "scanning..." (15 min, no feedback)
User: Confused, might cancel ❌
```

**After:**
```
User uploads 7.7 GB
Frontend shows:
┌────────────────────────────────────┐
│  Uploading Directory...            │
│                                    │
│  [████████████░░░░░░] 60%         │
│  Copying files...                  │
│                                    │
│  4.6 GB / 7.7 GB @ 21.3 MB/s      │
│  ETA: ~2.5 minutes                 │
│                                    │
│          [Cancel]                  │
└────────────────────────────────────┘

User: ✅ Knows it's working, can see progress!
```

---

## 📊 Performance Impact

**Backend:**
- Additional CPU: ~5% (parsing robocopy output)
- Additional Memory: ~10 MB (progress state)
- Network: +~100 bytes every 5 seconds (WebSocket)

**Frontend:**
- Additional CPU: ~2% (UI updates every 2s)
- Additional Memory: ~5 MB (modal dialog)

**Overall:** NEGLIGIBLE impact, HUGE UX improvement

---

## 🔄 Alternative Approaches

### Option 1: Progress via Status Endpoint Only (No WebSocket)

**Pros:**
- Simpler implementation
- No WebSocket dependency

**Cons:**
- Polling overhead (request every 2s)
- Less real-time

### Option 2: File-by-File Progress

**Pros:**
- More granular progress

**Cons:**
- Complex parsing
- More overhead

### Option 3: Time-Based Estimate

**Pros:**
- Very simple (no parsing)

**Cons:**
- Inaccurate
- No real progress info

**Chosen:** Option 1 + WebSocket (most accurate + real-time)

---

## 📖 Related Documentation

1. **BULK_COPY_OPTIMIZATION_COMPLETE.md** - Bulk copy implementation
2. **WEBSOCKET_INTEGRATION.md** - WebSocket architecture
3. **FRONTEND_INTEGRATION.md** - Frontend event system

---

**Letzte Aktualisierung:** 14. Oktober 2025  
**Status:** TODO (Design Complete)  
**Priorität:** MEDIUM (User Experience)  
**Aufwand:** 4-6 Stunden
