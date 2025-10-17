# Discovery Service Initialization Guide

**Datum:** 16. Oktober 2025, 11:00 Uhr  
**Status:** ⏸️ PENDING (Ready to implement)  
**Priorität:** MEDIUM (non-critical, but enables directory scanning)

---

## 🎯 Problem Summary

### Current Status

**Discovery Service:**
```bash
curl -X POST http://127.0.0.1:45678/discovery/trigger-scan -H "Content-Type: application/json" -d '{}'
# Response: {"detail":"Manual scan failed: 501: Discovery Service nicht verfügbar"}
```

**Root Cause:**
- Discovery Service exists in code (`discovery/discovery_service.py`)
- NOT initialized in backend startup (lifespan event)
- Endpoint registered but service instance is `None`
- DirectoryScanner available but not running

---

## 🔧 Solution Design

### Implementation Plan

**Phase 1: Initialize Discovery Service in Backend**

1. **Import Discovery Service** (backend.py Line ~370)
   ```python
   from discovery.discovery_service import DiscoveryService
   ```

2. **Initialize in Lifespan** (backend.py Line ~380-390)
   ```python
   # Initialize Discovery Service
   discovery_service = DiscoveryService(
       watch_directories=[
           "data/inbox",          # Watch inbox for new files
           "data/upload_temp"     # Watch upload temp directory
       ],
       scan_interval_seconds=60,  # Scan every 60 seconds
       file_event_callback=handle_file_event  # Callback for new files
   )
   discovery_service.start()
   logger.info("[OK] Discovery Service initialized and started")
   ```

3. **Create File Event Handler** (backend.py)
   ```python
   def handle_file_event(file_path: str, event_type: str):
       """Handle file discovery events"""
       logger.info(f"[DISCOVERY] {event_type}: {file_path}")
       
       # Option 1: Auto-create ingestion job
       # create_job_from_file(file_path)
       
       # Option 2: Add to queue for manual review
       # add_to_review_queue(file_path)
   ```

4. **Shutdown Hook** (backend.py lifespan)
   ```python
   # Shutdown Discovery Service
   if discovery_service:
       discovery_service.stop()
       logger.info("[OK] Discovery Service stopped")
   ```

---

## 📊 Discovery Service Architecture

### Core Components

**DiscoveryService Class:**
```python
class DiscoveryService:
    def __init__(
        self,
        watch_directories: List[str],
        scan_interval_seconds: int = 60,
        file_event_callback: Optional[Callable] = None
    ):
        self.watch_directories = watch_directories
        self.scan_interval = scan_interval_seconds
        self.file_event_callback = file_event_callback
        self.scanner = DirectoryScanner()
        self._running = False
        self._scan_thread = None
    
    def start(self):
        """Start background scanning"""
        self._running = True
        self._scan_thread = threading.Thread(target=self._scan_loop)
        self._scan_thread.start()
    
    def stop(self):
        """Stop background scanning"""
        self._running = False
        if self._scan_thread:
            self._scan_thread.join()
    
    def _scan_loop(self):
        """Background scan loop"""
        while self._running:
            for directory in self.watch_directories:
                self._scan_directory(directory)
            time.sleep(self.scan_interval)
    
    def _scan_directory(self, directory: str):
        """Scan a single directory"""
        files = self.scanner.scan_directory(directory)
        for file_path in files:
            if self.file_event_callback:
                self.file_event_callback(file_path, "discovered")
```

### DirectoryScanner Integration

**Already Available:**
- `ingestion/directory_scanner.py` - Full implementation exists
- `DirectoryScanner` class - scan_directory(), classify_file() methods
- File pattern matching - supports all major file types
- Recursive scanning - traverses subdirectories

---

## 🧪 Testing Plan

### Manual Tests

**Test 1: Start Discovery Service**
```bash
# Start backends
.\scripts\start_services.ps1

# Check logs for Discovery Service initialization
# Expected: "[OK] Discovery Service initialized and started"
```

**Test 2: Trigger Manual Scan**
```bash
# Trigger scan via API
curl -X POST http://127.0.0.1:45678/discovery/trigger-scan -H "Content-Type: application/json" -d '{}'

# Expected: {"message": "Scan triggered successfully", "files_discovered": 0}
```

**Test 3: File Discovery**
```bash
# Create test file in watch directory
Write-Output "Test content" | Out-File -FilePath "data/inbox/test.txt"

# Wait 60 seconds (scan interval)
# OR trigger manual scan

# Check logs for discovery event
# Expected: "[DISCOVERY] discovered: data/inbox/test.txt"
```

**Test 4: Auto-Ingestion (if enabled)**
```bash
# Create test file
Write-Output "Auto-ingest test" | Out-File -FilePath "data/inbox/auto_test.pdf"

# Wait for discovery + auto-ingestion

# Check job creation
curl http://127.0.0.1:45679/jobs
# Expected: New job with file "auto_test.pdf"
```

---

## ⚙️ Configuration Options

### Environment Variables

```bash
# Discovery Service
DISCOVERY_ENABLED=true
DISCOVERY_WATCH_DIRS=data/inbox,data/upload_temp
DISCOVERY_SCAN_INTERVAL=60
DISCOVERY_AUTO_INGEST=false

# File Patterns
DISCOVERY_FILE_PATTERNS=*.pdf,*.docx,*.xlsx,*.txt
DISCOVERY_IGNORE_PATTERNS=*.tmp,*.lock,*.part
```

### Backend Configuration

**Option 1: Auto-Ingestion (Automatic)**
```python
# Auto-create jobs for discovered files
def handle_file_event(file_path: str, event_type: str):
    if event_type == "discovered":
        job_id = create_ingestion_job([file_path])
        logger.info(f"[AUTO-INGEST] Created job {job_id} for {file_path}")
```

**Option 2: Manual Review (Conservative)**
```python
# Add to review queue for manual approval
def handle_file_event(file_path: str, event_type: str):
    if event_type == "discovered":
        add_to_review_queue(file_path, reason="Discovered by scanner")
        logger.info(f"[REVIEW] Added {file_path} to review queue")
```

**Option 3: Hybrid (Smart)**
```python
# Auto-ingest safe file types, review others
def handle_file_event(file_path: str, event_type: str):
    if event_type == "discovered":
        file_type = classify_file(file_path)
        
        if file_type in ["TEXT", "OFFICE"]:
            # Safe types - auto-ingest
            create_ingestion_job([file_path])
        else:
            # Unknown types - manual review
            add_to_review_queue(file_path)
```

---

## 📋 Implementation Steps

### Step 1: Backend Changes

**File:** `backend.py`

**Location:** Lifespan startup (around Line 370-390)

**Add:**
```python
# Discovery Service initialization
discovery_service = None
try:
    from discovery.discovery_service import DiscoveryService
    
    discovery_service = DiscoveryService(
        watch_directories=["data/inbox"],
        scan_interval_seconds=60,
        file_event_callback=None  # No auto-action for now
    )
    discovery_service.start()
    logger.info("[OK] Discovery Service started (watch: data/inbox)")
except Exception as e:
    logger.warning(f"[WARNING] Discovery Service failed to start: {e}")
    discovery_service = None
```

**Location:** Lifespan shutdown (around Line 425-435)

**Add:**
```python
# Shutdown Discovery Service
if discovery_service:
    discovery_service.stop()
    logger.info("[OK] Discovery Service stopped")
```

### Step 2: Endpoint Fix

**File:** `backend.py`

**Find:** `/discovery/trigger-scan` endpoint

**Update:**
```python
@app.post("/discovery/trigger-scan", tags=["discovery"])
async def trigger_manual_scan():
    """Trigger a manual directory scan"""
    if not discovery_service:
        raise HTTPException(
            status_code=501,
            detail="Discovery Service not available"
        )
    
    # Trigger immediate scan (non-blocking)
    files_discovered = discovery_service.scan_now()
    
    return {
        "message": "Scan triggered successfully",
        "files_discovered": files_discovered,
        "watch_directories": discovery_service.watch_directories
    }
```

### Step 3: Create scan_now() Method

**File:** `discovery/discovery_service.py`

**Add:**
```python
def scan_now(self) -> int:
    """
    Trigger immediate scan (non-blocking).
    
    Returns:
        Number of files discovered
    """
    files_discovered = 0
    
    for directory in self.watch_directories:
        files = self._scan_directory(directory)
        files_discovered += len(files)
    
    return files_discovered
```

---

## ✅ Completion Checklist

- [ ] Import DiscoveryService in backend.py
- [ ] Initialize Discovery Service in lifespan startup
- [ ] Add shutdown hook in lifespan
- [ ] Update /discovery/trigger-scan endpoint
- [ ] Add scan_now() method to DiscoveryService
- [ ] Test manual scan trigger
- [ ] Test file discovery (create file in data/inbox)
- [ ] Test backend restart (Discovery Service auto-starts)
- [ ] Document configuration options
- [ ] Add environment variables for configuration

---

## 🎯 Success Criteria

**Before Implementation:**
```bash
curl -X POST http://127.0.0.1:45678/discovery/trigger-scan
# Response: 501 - Discovery Service nicht verfügbar
```

**After Implementation:**
```bash
curl -X POST http://127.0.0.1:45678/discovery/trigger-scan
# Response: 200 - {"message": "Scan triggered successfully", "files_discovered": 0}
```

**File Discovery Test:**
```bash
# Create test file
Write-Output "Test" | Out-File "data/inbox/test.txt"

# Trigger scan
curl -X POST http://127.0.0.1:45678/discovery/trigger-scan

# Check logs
# Expected: [DISCOVERY] discovered: data/inbox/test.txt
```

---

## 📚 References

- `discovery/discovery_service.py` - Full implementation (if exists)
- `ingestion/directory_scanner.py` - DirectoryScanner class
- `backend.py` - Lifespan events (Lines 350-440)
- `docs/DISCOVERY_SERVICE_ARCHITECTURE.md` - Architecture docs (if exists)

---

**Last Updated:** 16. Oktober 2025, 11:05 Uhr  
**Status:** ⏸️ READY TO IMPLEMENT  
**Priority:** MEDIUM (non-critical functionality)  
**Estimated Time:** 20-30 minutes
