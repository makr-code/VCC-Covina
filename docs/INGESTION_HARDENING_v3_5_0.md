# Ingestion Hardening - v3.5.0

**Date:** 14. Oktober 2025, 12:50 Uhr  
**Priority:** 🔥 CRITICAL - Production Readiness  
**Goal:** Robuste Ingestion für große Datenmengen (Dateien & Größe)  
**Status:** 🎯 DESIGN PHASE

---

## 🎯 Zielsetzung

**Aktuelle Probleme:**
- ❌ Memory Exhaustion bei großen Uploads (>4500 Dateien → 12.9 GB RAM → Crash)
- ❌ Scan-Job Deadlock bei vielen Dateien (10+ Minuten, 0 Fortschritt)
- ❌ Keine Limits für Dateianzahl/Größe
- ❌ Keine Progress-Anzeige während Scan (nur am Ende)
- ❌ OOM bei großen einzelnen Dateien (>1 GB)
- ❌ Worker Pool Überlastung bei zu vielen Jobs
- ❌ Keine Priorisierung (alle Jobs gleichbehandelt)

**Ziele:**
- ✅ Stabile Verarbeitung von 10,000+ Dateien
- ✅ Einzeldateien bis 2 GB (streaming)
- ✅ Totale Upload-Größe: 50 GB+ (batch processing)
- ✅ Echtzeit Progress (alle 100 Dateien während Scan)
- ✅ Graceful Degradation bei Limits
- ✅ Memory-effiziente Verarbeitung
- ✅ Worker Pool Throttling
- ✅ Job Priorisierung

---

## 📊 Aktuelle Schwachstellen

### 1. Scanner - Memory & Performance

**Location:** `ingestion_backend.py` Lines 365-390 (`_scan_directory_async()`)

**Problems:**
```python
def scan_sync():
    paths = []
    
    for root, _, files in os.walk(self.directory_path):
        for file in files:
            if Path(file).suffix.lower() in self.supported_extensions:
                paths.append(os.path.join(root, file))  # ❌ Alle Paths im RAM!
    
    return paths  # ❌ Liste kann 100,000+ Elemente haben!
```

**Issues:**
- **Memory:** Liste mit 100,000 Pfaden = ~20 MB+ RAM
- **Progress:** Keine Updates während Scan (nur am Ende)
- **Limits:** Keine Begrenzung der Dateianzahl
- **Size Check:** Keine Prüfung der Dateigröße
- **Robustness:** Kein Error Handling (Permission Denied, etc.)

---

### 2. Chunking - Fixed Size

**Location:** `ingestion_backend.py` Lines 293-296

**Problems:**
```python
file_chunks = [
    file_paths[i:i+self.chunk_size]  # ❌ Fixed 50 files/chunk
    for i in range(0, len(file_paths), self.chunk_size)
]
```

**Issues:**
- **Fixed Size:** 50 Dateien/Chunk unabhängig von Dateigröße
- **Example:** 50x 1 GB = 50 GB pro Chunk! ❌
- **Worker Overload:** Alle Chunks parallel → 200+ Jobs gleichzeitig
- **Memory:** Große Chunks laden zu viel in RAM

---

### 3. File Upload - Streaming (FIXED v3.4.5)

**Location:** `ingestion_backend.py` Lines 1575-1600

**Status:** ✅ Bereits gefixt (64KB chunks)

**Previous Problem:**
```python
# OLD (Memory Exhaustion):
content = await file.read()  # ❌ Loads entire file!
f.write(content)

# NEW (Streaming):
while chunk := await file.read(65536):  # ✅ 64KB chunks
    f.write(chunk)
```

**Result:** -83% memory usage ✅

---

### 4. Worker Pool - No Throttling

**Location:** `ingestion_backend.py` Lines 558-595 (IngestionJobManager)

**Problems:**
```python
# No checks on active jobs!
io_executor.submit(process_chunk_sync, job_id, chunk, ...)  # ❌ Unbegrenzt!
```

**Issues:**
- **No Limit:** Kann 1000+ Jobs parallel starten
- **Memory:** Jeder Job verbraucht RAM
- **CPU:** Worker Pool überlastet
- **Disk I/O:** Bottleneck bei zu vielen Writes

---

### 5. Progress - End-Only Updates

**Location:** `ingestion_backend.py` Lines 365-390

**Problems:**
- Progress nur **nach** Scan-Abschluss
- Keine Updates während Scan (kann 10+ Minuten dauern)
- User denkt, System ist abgestürzt

---

## 🔧 Härtungskonzept

### Phase 1: Limits & Validation (CRITICAL)

#### 1.1: Configuration Limits

**Add to config.py:**
```python
# Ingestion Limits
MAX_FILES_PER_SCAN = 50000           # Maximale Dateien pro Directory Scan
MAX_FILE_SIZE_MB = 2048              # Maximale Einzeldateigröße (2 GB)
MAX_TOTAL_SIZE_GB = 100              # Maximale Gesamtgröße pro Scan (100 GB)
MAX_CHUNK_SIZE_FILES = 50            # Max Dateien pro Chunk
MAX_CHUNK_SIZE_MB = 1024             # Max MB pro Chunk (1 GB)
MAX_ACTIVE_JOBS = 100                # Maximale gleichzeitige Jobs
SCAN_PROGRESS_INTERVAL = 100         # Progress Update alle N Dateien
```

#### 1.2: Scanner Validation

**Enhance `_scan_directory_async()` with:**
- ✅ File count limit check
- ✅ Total size tracking
- ✅ Progress updates every 100 files
- ✅ Individual file size check
- ✅ Early termination if limits exceeded

**Pseudocode:**
```python
def scan_sync():
    paths = []
    total_size = 0
    file_count = 0
    
    for root, _, files in os.walk(self.directory_path):
        for file in files:
            # Check limits BEFORE adding
            if file_count >= MAX_FILES_PER_SCAN:
                logger.warning(f"⚠️ File limit reached: {MAX_FILES_PER_SCAN}")
                return paths  # Early termination
            
            file_path = os.path.join(root, file)
            
            # Check extension
            if Path(file).suffix.lower() not in self.supported_extensions:
                continue
            
            # Check individual file size
            try:
                file_size = os.path.getsize(file_path)
                if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    logger.warning(f"⚠️ File too large: {file} ({file_size / 1024 / 1024:.1f} MB)")
                    continue  # Skip large files
                
                # Check total size
                if total_size + file_size > MAX_TOTAL_SIZE_GB * 1024 * 1024 * 1024:
                    logger.warning(f"⚠️ Total size limit reached: {MAX_TOTAL_SIZE_GB} GB")
                    return paths  # Early termination
                
                total_size += file_size
                file_count += 1
                paths.append(file_path)
                
                # Progress update every 100 files
                if file_count % SCAN_PROGRESS_INTERVAL == 0:
                    # Broadcast progress (non-blocking)
                    try:
                        self.files_found = file_count
                        asyncio.run_coroutine_threadsafe(
                            self._broadcast_progress(file_count),
                            loop
                        )
                    except:
                        pass  # Best effort
                        
            except OSError as e:
                logger.debug(f"Cannot access file {file_path}: {e}")
                continue  # Skip inaccessible files
    
    return paths
```

---

### Phase 2: Smart Chunking (HIGH PRIORITY)

#### 2.1: Size-Aware Chunking

**Replace fixed-size chunking with size-aware:**

**Current (Fixed):**
```python
# ❌ Fixed 50 files/chunk
file_chunks = [
    file_paths[i:i+50]
    for i in range(0, len(file_paths), 50)
]
```

**New (Size-Aware):**
```python
def create_smart_chunks(file_paths: List[str]) -> List[List[str]]:
    """Create chunks based on file count AND total size"""
    chunks = []
    current_chunk = []
    current_size = 0
    
    for file_path in file_paths:
        try:
            file_size = os.path.getsize(file_path)
            
            # Check if adding this file would exceed limits
            if (len(current_chunk) >= MAX_CHUNK_SIZE_FILES or 
                current_size + file_size > MAX_CHUNK_SIZE_MB * 1024 * 1024):
                
                # Start new chunk
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(file_path)
            current_size += file_size
            
        except OSError:
            # File no longer accessible, skip
            continue
    
    # Add last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
```

**Benefits:**
- ✅ Keine Chunks >1 GB
- ✅ Keine Chunks >50 Dateien
- ✅ Memory-effizient
- ✅ Worker Pool freundlich

---

### Phase 3: Worker Pool Throttling (MEDIUM PRIORITY)

#### 3.1: Active Job Tracking

**Add to IngestionJobManager:**
```python
class IngestionJobManager:
    def __init__(self):
        self.jobs: Dict[str, IngestionJob] = {}
        self.active_jobs: Set[str] = set()  # ✅ NEW: Track active jobs
        self.job_queue: Queue = Queue()      # ✅ NEW: Job queue for throttling
        self._max_active_jobs = MAX_ACTIVE_JOBS
        
    def submit_job(self, job_id: str, file_paths: List[str]):
        """Submit job with throttling"""
        
        # Check if we can start immediately
        if len(self.active_jobs) < self._max_active_jobs:
            self._start_job(job_id, file_paths)
            self.active_jobs.add(job_id)
        else:
            # Queue for later
            self.job_queue.put((job_id, file_paths))
            logger.info(f"⏸️ Job {job_id} queued (active: {len(self.active_jobs)})")
    
    def _on_job_complete(self, job_id: str):
        """Called when job completes"""
        self.active_jobs.remove(job_id)
        
        # Start next job from queue
        if not self.job_queue.empty():
            next_job_id, next_file_paths = self.job_queue.get()
            self._start_job(next_job_id, next_file_paths)
            self.active_jobs.add(next_job_id)
            logger.info(f"▶️ Starting queued job {next_job_id}")
```

**Benefits:**
- ✅ Nie mehr als 100 aktive Jobs
- ✅ Worker Pool nicht überlastet
- ✅ Memory-effizient
- ✅ Graceful Degradation

---

### Phase 4: Enhanced Progress (LOW PRIORITY)

#### 4.1: Real-Time Scan Progress

**Add WebSocket updates during scan:**
```python
# In scan_sync() (every 100 files):
if file_count % SCAN_PROGRESS_INTERVAL == 0:
    # Broadcast to GUI
    asyncio.run_coroutine_threadsafe(
        self._broadcast_scan_progress(file_count, total_size),
        loop
    )

async def _broadcast_scan_progress(self, files_found: int, total_size: int):
    """Broadcast scan progress to GUI"""
    await ws_manager.broadcast_job_update({
        "type": "scan_progress_update",
        "scan_job_id": self.scan_job_id,
        "files_found": files_found,
        "total_size_mb": total_size / 1024 / 1024,
        "timestamp": datetime.now().isoformat()
    })
```

**Benefits:**
- ✅ User sieht Fortschritt in Echtzeit
- ✅ Keine "System hängt" Panik
- ✅ Bessere UX

---

## 📊 Expected Performance Impact

### Before Hardening:
```
Max Files:        ~4500 (dann Crash)
Max File Size:    Unlimited (Memory Exhaustion)
Max Total Size:   ~7 GB (dann Crash)
Scan Progress:    End-only (keine Updates)
Active Jobs:      Unlimited (Worker Pool Overload)
Memory:           12.9 GB @ 4500 files
Robustness:       ❌ Crash-prone
```

### After Hardening (Phase 1+2):
```
Max Files:        50,000 (konfigurierbar)
Max File Size:    2 GB (konfigurierbar)
Max Total Size:   100 GB (konfigurierbar)
Scan Progress:    Every 100 files (real-time)
Active Jobs:      100 (throttled)
Memory:           ~3-5 GB @ 50,000 files
Robustness:       ✅ Graceful Degradation
```

### Performance Targets:
```
Scan Speed:       1,000-5,000 files/second (filesystem dependent)
Memory Usage:     <5 GB @ 10,000 files
Throughput:       187 files/s (unchanged, disk I/O limited)
Latency:          <200ms P95 (worker pool throttling)
Success Rate:     99%+ (robust error handling)
```

---

## 🚀 Implementation Plan

### Phase 1: Limits & Validation (IMMEDIATE - 1 hour)

**Changes:**
1. ✅ Add configuration limits to `config.py`
2. ✅ Enhance `_scan_directory_async()` with validation
3. ✅ Add file size checks
4. ✅ Add total size tracking
5. ✅ Add early termination logic
6. ✅ Improve error handling (Permission Denied, etc.)

**Files:**
- `config.py` (+20 lines)
- `ingestion_backend.py` Lines 365-390 (+50 lines)

**Testing:**
```bash
# Test 1: Large directory (10,000+ files)
curl -X POST http://127.0.0.1:45679/upload/directory \
  -F 'directory_path=/large_test_dir' \
  -F 'chunk_size=50'

# Expected: Completes successfully, limits enforced

# Test 2: File size limit
# Place 3 GB file in directory
# Expected: File skipped with warning

# Test 3: Total size limit
# Directory with 150 GB
# Expected: Stops at 100 GB with warning
```

---

### Phase 2: Smart Chunking (HIGH - 45 minutes)

**Changes:**
1. ✅ Implement `create_smart_chunks()`
2. ✅ Replace fixed chunking in `scan_and_create_jobs()`
3. ✅ Add size calculation before chunking
4. ✅ Log chunk statistics (count, avg size, etc.)

**Files:**
- `ingestion_backend.py` Lines 280-310 (+60 lines)

**Testing:**
```bash
# Test 1: Mixed file sizes
# Directory: 20x 1 MB, 5x 500 MB, 2x 1 GB
# Expected: Smart chunks (no chunk >1 GB)

# Test 2: Many small files
# Directory: 10,000x 10 KB
# Expected: Chunks of 50 files each

# Test 3: Few large files
# Directory: 10x 800 MB
# Expected: 1 file per chunk (size limit)
```

---

### Phase 3: Worker Pool Throttling (MEDIUM - 1 hour)

**Changes:**
1. ✅ Add `active_jobs` tracking to IngestionJobManager
2. ✅ Add `job_queue` for throttling
3. ✅ Implement `submit_job()` with queue logic
4. ✅ Add `_on_job_complete()` callback
5. ✅ Integrate with existing job submission

**Files:**
- `ingestion_backend.py` Lines 558-695 (+80 lines)

**Testing:**
```bash
# Test 1: 200 jobs submitted
# Expected: Max 100 active, 100 queued

# Test 2: Job completion
# Expected: Queued jobs start automatically

# Test 3: Memory usage
# Expected: Stable (no linear growth)
```

---

### Phase 4: Enhanced Progress (LOW - 30 minutes)

**Changes:**
1. ✅ Add `_broadcast_scan_progress()` method
2. ✅ Integrate into `scan_sync()` every 100 files
3. ✅ Update WebSocket event schema
4. ✅ Update GUI to display scan progress

**Files:**
- `ingestion_backend.py` (+30 lines)
- `frontend/views/upload_view.py` (+20 lines)

**Testing:**
```bash
# Test: Scan 5,000 files
# Expected: Progress updates every 100 files
# GUI: Shows "Scanning... 1,200 / 5,000 files"
```

---

## 🎯 Success Criteria

### Phase 1 (Critical):
- ✅ Scan 50,000 files without crash
- ✅ Skip files >2 GB with warning
- ✅ Stop at 100 GB total size
- ✅ Graceful error handling (Permission Denied)
- ✅ Memory usage <5 GB

### Phase 2 (High):
- ✅ No chunks >1 GB
- ✅ No chunks >50 files
- ✅ Smart chunking works for mixed sizes
- ✅ Log chunk statistics

### Phase 3 (Medium):
- ✅ Max 100 active jobs enforced
- ✅ Job queue works correctly
- ✅ Memory usage stable
- ✅ No worker pool overload

### Phase 4 (Low):
- ✅ Progress updates every 100 files
- ✅ GUI displays progress
- ✅ User sees real-time updates

---

## 🔄 Rollback Plan

**If Issues Occur:**
```bash
# 1. Revert changes
git checkout ingestion_backend.py config.py

# 2. Restart backend
.\scripts\stop_services.ps1
.\scripts\deploy_production.ps1

# 3. Document issue
echo "Rollback: [reason]" >> DEPLOYMENT_LOG.md
```

---

## 📝 Configuration Example

**After Phase 1+2, add to `.env.production`:**
```bash
# Ingestion Hardening (v3.5.0)
MAX_FILES_PER_SCAN=50000
MAX_FILE_SIZE_MB=2048
MAX_TOTAL_SIZE_GB=100
MAX_CHUNK_SIZE_FILES=50
MAX_CHUNK_SIZE_MB=1024
MAX_ACTIVE_JOBS=100
SCAN_PROGRESS_INTERVAL=100
```

---

## 📊 Related Issues

**Fixed:**
- ✅ v3.4.5: Memory Streaming Fix (-83% RAM)
- ✅ v3.4.9.1: Auto-Resume Bug Fix
- ✅ v4.0.3.1: RecoveryView Bug Fix

**In Progress:**
- 🔄 v3.5.0: Ingestion Hardening (THIS DOCUMENT)

**Planned:**
- ⏸️ v3.6.0: ZIP File Extraction Support
- ⏸️ v3.7.0: Parallel Database Writes

---

**Status:** 🎯 DESIGN COMPLETE - Ready for Phase 1 Implementation  
**Next Step:** Implement Phase 1 (Limits & Validation)  
**ETA:** 1 hour (code changes + testing)  
**Priority:** 🔥 CRITICAL - Deploy ASAP

---

## 💡 Additional Considerations

### Future Enhancements (v3.6+):

**1. ZIP File Extraction:**
- Auto-extract ZIP files during scan
- Process contents instead of ZIP
- Temporary extraction directory
- Cleanup after processing

**2. Parallel Database Writes:**
- PostgreSQL + CouchDB parallel
- ChromaDB batch insert (already implemented)
- Neo4j batch UNWIND (already ready)
- Expected: +30-50% throughput

**3. Resume Incomplete Scans:**
- Persistent scan state (SQLite)
- Auto-load on backend restart
- Continue from last position
- Crash recovery

**4. Job Prioritization:**
- User-submitted jobs: Priority 1
- Scan jobs: Priority 2
- Recovery jobs: Priority 3
- Queue ordering by priority

**5. Distributed Scanning:**
- Split large directories across multiple workers
- Parallel scans for faster completion
- Expected: 5,000-10,000 files/s scan speed
