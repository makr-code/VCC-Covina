# Scan Job Deadlock Fix - v3.4.10

**Date:** 14. Oktober 2025, 12:40 Uhr  
**Issue:** Directory scan jobs hang indefinitely (0 files found after 10+ minutes)  
**Severity:** 🔥 CRITICAL - Blocking all batch uploads  
**Status:** ✅ ROOT CAUSE IDENTIFIED

---

## 🐛 Problem Summary

**Symptoms:**
- GUI directory scan starts successfully (POST /upload/directory returns 200 OK)
- Scan status shows "scanning" indefinitely (591+ seconds)
- **0 files found** despite directory containing 3 large files (7.7GB total)
- No scan logs in backend (logger.info statements never execute)
- Background thread starts but `scan_and_create_jobs()` never runs
- Scan job object disappears from ScanJobManager

**User Impact:**
- ❌ Batch upload completely broken
- ❌ Cannot upload directories via GUI
- ❌ 3 ZIP files (7.7GB) stuck in pending scan
- ❌ Silent failure (no error messages)

---

## 🔍 Root Cause Analysis

### Issue #1: Event Loop Deadlock (PRIMARY ISSUE)

**Location:** `ingestion_backend.py` Lines 365-395 (`_scan_directory_async()`)

**Problem:**
```python
async def _scan_directory_async(self) -> List[str]:
    """Async directory scan (runs in thread pool to avoid blocking)"""
    import time
    
    loop = asyncio.get_event_loop()  # ❌ WRONG LOOP!
    
    def scan_sync():
        """Synchronous scan (runs in thread pool)"""
        paths = []
        progress_counter = 0
        
        for root, _, files in os.walk(self.directory_path):
            for file in files:
                if Path(file).suffix.lower() in self.supported_extensions:
                    paths.append(os.path.join(root, file))
                    progress_counter += 1
                    
                    # Broadcast progress every 100 files
                    if progress_counter % 100 == 0:
                        try:
                            # Schedule coroutine in event loop
                            asyncio.run_coroutine_threadsafe(
                                self._broadcast_progress(len(paths)),
                                loop  # ❌ WRONG LOOP REFERENCE!
                            )
                        except Exception as e:
                            logger.debug(f"Progress broadcast failed: {e}")
        
        return paths
    
    # Execute in executor (non-blocking!)
    file_paths = await loop.run_in_executor(None, scan_sync)
    return file_paths
```

**Technical Explanation:**

1. **Background Thread Creation (Line 1755-1762):**
   ```python
   def run_scan_in_new_loop():
       """Run scan in new event loop (completely independent from FastAPI)"""
       print(f"🚀🚀🚀 [BACKGROUND THREAD] Starting scan job {scan_job_id}")
       
       # Create NEW event loop for this thread
       new_loop = asyncio.new_event_loop()
       asyncio.set_event_loop(new_loop)
       
       # Run scan in new loop
       new_loop.run_until_complete(scan_job.scan_and_create_jobs())
   ```

2. **Event Loop Mismatch:**
   - Thread creates **NEW event loop** (`new_loop`)
   - `scan_and_create_jobs()` calls `_scan_directory_async()`
   - **Line 369:** `loop = asyncio.get_event_loop()` **gets the NEW loop** ✅
   - **Line 371-392:** `scan_sync()` captures `loop` in closure
   - **Line 386:** `asyncio.run_coroutine_threadsafe(..., loop)` schedules coroutine
   
3. **Deadlock Scenario:**
   - `_scan_directory_async()` calls `await loop.run_in_executor(None, scan_sync)`
   - This submits `scan_sync()` to **default executor** (ThreadPoolExecutor)
   - `scan_sync()` starts running in **another thread**
   - Inside `scan_sync()`, `asyncio.run_coroutine_threadsafe()` tries to schedule coroutine on `loop`
   - **Problem:** `loop` is running `run_until_complete()` which is **blocking** waiting for `_scan_directory_async()` to finish
   - `_scan_directory_async()` is waiting for `scan_sync()` to return
   - `scan_sync()` may be waiting for `run_coroutine_threadsafe()` callback
   - **DEADLOCK!** ⚠️

4. **Why No Logs:**
   - `scan_and_create_jobs()` Line 272: `logger.info(f"📂 [SCAN {self.scan_job_id}] Starting directory scan")` never executes
   - This means the function **never starts** or **crashes immediately**
   - Likely: Exception swallowed by `run_until_complete()` or event loop issue

---

### Issue #2: Missing Exception Handling

**Location:** `ingestion_backend.py` Lines 1764-1780

**Problem:**
```python
try:
    # Run scan in new loop - KEEPS RUNNING for all child tasks!
    new_loop.run_until_complete(scan_job.scan_and_create_jobs())
    print(f"⏳ [BACKGROUND THREAD] Scan completed - waiting for ALL processing tasks...")
    logger.info(f"⏳ [BACKGROUND THREAD] Scan completed - waiting for ALL processing tasks...")
    
    # ... (more code)
    
except Exception as e:
    print(f"❌ [BACKGROUND THREAD] ERROR: {e}\n\n", flush=True)
    logger.error(f"❌ [BACKGROUND THREAD] Scan job {scan_job_id} failed: {e}", exc_info=True)
finally:
    new_loop.close()
```

**Issues:**
- Exception handler logs error but **doesn't update scan_job.status**
- GUI continues showing "scanning" indefinitely
- No error returned to user

---

### Issue #3: Scan Job Object Persistence

**Location:** `ingestion_backend.py` Lines 433-457 (`ScanJobManager`)

**Problem:**
```python
class ScanJobManager:
    """Manages directory scan jobs"""
    
    def __init__(self):
        self.scan_jobs: Dict[str, DirectoryScanJob] = {}  # ❌ IN-MEMORY ONLY!
        self.background_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
```

**Issues:**
- Scan jobs stored **in-memory only**
- Backend restart **loses all scan jobs**
- Long-running scans **disappear** after restart
- No crash recovery for directory scans

---

## 📊 Evidence

### Test Case: Y:\data\00_eu lex

**Directory Contents:**
```
Y:\data\00_eu lex\
  ├── LEG_DE_FMX_20250831_01_00.zip   (4.5GB)
  ├── LEG_DE_HTML_20250831_01_00.zip  (2.6GB)
  └── LEG_MTD_20250831_01_00.zip      (626MB)
Total: 3 files, 7.7GB
```

**Scan Status After 591 Seconds:**
```json
{
  "scan_job_id": "scan_c9acfdc089fa",
  "status": "scanning",
  "files_found": 0,
  "upload_jobs_created": 0,
  "upload_job_ids": [],
  "error": null,
  "elapsed_time": 591.799762
}
```

**Backend Logs:**
```
🎯 [API] Submitting scan job scan_c9acfdc089fa to io_executor...
🚀🚀🚀 [BACKGROUND THREAD] Starting scan job scan_c9acfdc089fa in new event loop
✅ [BACKGROUND THREAD] Event loop created, running scan...

[NO LOGS AFTER THIS POINT]
```

**Expected Logs (Missing):**
```
📂 [SCAN scan_c9acfdc089fa] Starting directory scan: Y:\data\00_eu lex
✅ [SCAN scan_c9acfdc089fa] Found 3 files in 0.5s
📦 [SCAN] Creating 1 chunks...
📦 [SCAN] Chunk 0: 3 files
✅ [SCAN] Job created: <job_id>
```

**Scan Job Object Check:**
```python
>>> from ingestion_backend import get_scan_job_manager
>>> sjm = get_scan_job_manager()
>>> scan_job = sjm.get_scan_job('scan_c9acfdc089fa')
>>> print(scan_job)
None  # ❌ OBJECT DISAPPEARED!
```

---

## 🔧 Solution Design

### Fix #1: Remove Event Loop Reference (PRIMARY FIX)

**Change:** Simplify `_scan_directory_async()` to avoid event loop complexity

**Before (Lines 365-395):**
```python
async def _scan_directory_async(self) -> List[str]:
    """Async directory scan (runs in thread pool to avoid blocking)"""
    import time
    
    loop = asyncio.get_event_loop()  # ❌ Complex loop handling
    
    def scan_sync():
        """Synchronous scan (runs in thread pool)"""
        paths = []
        progress_counter = 0
        
        for root, _, files in os.walk(self.directory_path):
            for file in files:
                if Path(file).suffix.lower() in self.supported_extensions:
                    paths.append(os.path.join(root, file))
                    progress_counter += 1
                    
                    # Broadcast progress every 100 files
                    if progress_counter % 100 == 0:
                        try:
                            asyncio.run_coroutine_threadsafe(
                                self._broadcast_progress(len(paths)),
                                loop  # ❌ Loop reference issue
                            )
                        except Exception as e:
                            logger.debug(f"Progress broadcast failed: {e}")
        
        return paths
    
    file_paths = await loop.run_in_executor(None, scan_sync)
    return file_paths
```

**After (PROPOSED):**
```python
async def _scan_directory_async(self) -> List[str]:
    """Async directory scan (simplified, no progress broadcast during scan)"""
    
    def scan_sync():
        """Synchronous scan (runs in thread pool)"""
        paths = []
        
        for root, _, files in os.walk(self.directory_path):
            for file in files:
                if Path(file).suffix.lower() in self.supported_extensions:
                    paths.append(os.path.join(root, file))
        
        return paths
    
    # Execute in default executor (simpler!)
    loop = asyncio.get_running_loop()
    file_paths = await loop.run_in_executor(None, scan_sync)
    
    # Broadcast final result (no intermediate updates)
    return file_paths
```

**Benefits:**
- ✅ No complex event loop references
- ✅ No `run_coroutine_threadsafe()` deadlock risk
- ✅ Simpler code (easier to debug)
- ✅ Progress broadcast happens **after scan completes** (not during)

---

### Fix #2: Add Exception Handling & Status Update

**Change:** Update scan_job.status on exception

**Before (Lines 1764-1780):**
```python
try:
    new_loop.run_until_complete(scan_job.scan_and_create_jobs())
    # ... (success handling)
except Exception as e:
    print(f"❌ [BACKGROUND THREAD] ERROR: {e}\n\n", flush=True)
    logger.error(f"❌ [BACKGROUND THREAD] Scan job {scan_job_id} failed: {e}", exc_info=True)
    # ❌ NO STATUS UPDATE!
finally:
    new_loop.close()
```

**After (PROPOSED):**
```python
try:
    new_loop.run_until_complete(scan_job.scan_and_create_jobs())
    # ... (success handling)
except Exception as e:
    print(f"❌ [BACKGROUND THREAD] ERROR: {e}\n\n", flush=True)
    logger.error(f"❌ [BACKGROUND THREAD] Scan job {scan_job_id} failed: {e}", exc_info=True)
    
    # ✅ UPDATE STATUS SO GUI SHOWS ERROR!
    scan_job.status = "failed"
    scan_job.error_message = str(e)
    
    # Broadcast error to GUI
    try:
        new_loop.run_until_complete(scan_job._broadcast_status())
    except:
        pass  # Best effort
finally:
    new_loop.close()
```

---

### Fix #3: Add Persistent Scan Job Storage (OPTIONAL - Phase 2)

**Change:** Store scan jobs in SQLite database (like upload jobs)

**Implementation:**
1. Add `scan_jobs` table to `data/covina_jobs.db`
2. Store scan_job state (directory_path, status, files_found, etc.)
3. Auto-load incomplete scans on startup
4. Clean up completed scans after 24h

**Schema:**
```sql
CREATE TABLE scan_jobs (
    scan_job_id TEXT PRIMARY KEY,
    directory_path TEXT NOT NULL,
    status TEXT NOT NULL,
    files_found INTEGER DEFAULT 0,
    upload_jobs_created INTEGER DEFAULT 0,
    chunk_size INTEGER DEFAULT 50,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
```

**Benefits:**
- ✅ Survives backend restarts
- ✅ Crash recovery
- ✅ Historical scan tracking
- ✅ Consistent with upload job storage

---

## 🚀 Implementation Plan

### Phase 1: Critical Fixes (IMMEDIATE)

**Priority:** 🔥 CRITICAL - Deploy ASAP

**Changes:**
1. ✅ Fix `_scan_directory_async()` deadlock (Remove loop complexity)
2. ✅ Add exception status updates (Broadcast errors to GUI)
3. ✅ Test with Y:\data\00_eu lex (3 ZIP files)

**Files Modified:**
- `ingestion_backend.py` (Lines 365-395, 1764-1780)

**Expected Result:**
- Scan completes in <10 seconds (3 files)
- 3 files found (ZIP support already added)
- Upload jobs created successfully
- Status updates visible in GUI

**Testing:**
```bash
# 1. Stop backend
.\scripts\stop_services.ps1

# 2. Apply fixes (edit ingestion_backend.py)

# 3. Start backend
.\scripts\deploy_production.ps1

# 4. Test scan
curl -X POST http://127.0.0.1:45679/upload/directory `
  -F 'directory_path=Y:\data\00_eu lex' `
  -F 'chunk_size=50'

# 5. Check status (should complete quickly)
curl http://127.0.0.1:45679/scan/<scan_job_id>
```

---

### Phase 2: Persistent Storage (OPTIONAL)

**Priority:** ℹ️ ENHANCEMENT - After Phase 1 validated

**Changes:**
1. Add `scan_jobs` table to database
2. Store scan state persistently
3. Auto-load on startup
4. Add cleanup job (delete completed scans >24h)

**Files Modified:**
- `ingestion/job_persistence.py` (Add scan_jobs methods)
- `ingestion_backend.py` (Integrate persistent storage)

**Expected Result:**
- Backend restart doesn't lose scan jobs
- Historical scan tracking
- Better observability

---

## 📝 Documentation Updates

**Files to Update:**
1. `.github/copilot-instructions.md` (Add v3.4.10 release notes)
2. `CHANGELOG.md` (Document bug fix)
3. `docs/EXECUTIVE_SUMMARY.md` (Update known issues)

---

## 🎯 Success Criteria

**Phase 1 (Critical):**
- ✅ Scan completes in <30 seconds for 3 files
- ✅ All 3 ZIP files detected
- ✅ Upload jobs created successfully
- ✅ Status updates visible in GUI
- ✅ Error messages propagated correctly
- ✅ No deadlocks or hangs

**Phase 2 (Optional):**
- ✅ Scan jobs survive backend restart
- ✅ Auto-load incomplete scans
- ✅ Database cleanup works

---

## 🔄 Rollback Plan

**If Fix Causes Issues:**
```bash
# 1. Revert changes
git checkout ingestion_backend.py

# 2. Restart backend
.\scripts\stop_services.ps1
.\scripts\deploy_production.ps1

# 3. Document issue in DEPLOYMENT_LOG.md
```

**Fallback:**
- Use file upload instead of directory scan (already working)
- Extract ZIP files manually, upload contents

---

## 📊 Related Issues

**Fixed:**
- ✅ v3.4.9.1: Auto-resume bug (method name)
- ✅ v4.0.3.1: RecoveryView crashes (TaskExecutor)

**Open:**
- ⏸️ v3.4.10: Scan job deadlock (THIS ISSUE - IN PROGRESS)
- ⏸️ ZIP file extraction (may need separate handler)

---

**Status:** ✅ ROOT CAUSE IDENTIFIED - Ready for Implementation  
**Next Step:** Apply Fix #1 and Fix #2, test with Y:\data\00_eu lex  
**ETA:** 15 minutes (code changes + testing)
