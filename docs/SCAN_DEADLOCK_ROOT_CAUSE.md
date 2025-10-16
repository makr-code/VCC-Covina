# Scan Job Deadlock - Root Cause Analysis

**Date:** 14. Oktober 2025, 13:50 Uhr  
**Issue:** Directory scan jobs hang indefinitely (scan_and_create_jobs never executes)  
**Severity:** 🔥 CRITICAL  
**Status:** 🔍 INVESTIGATING

---

## Problem Summary

**Symptoms:**
- Background thread starts successfully
- `run_scan_in_new_loop()` executes
- **But:** `scan_and_create_jobs()` is NEVER called
- No scan logs appear (no "Starting file system scan")
- Scan status stays "scanning" forever
- 0 files found after 10+ minutes

**Evidence:**
```
Logs show:
🎯 [API] Submitting scan job scan_xxx to io_executor...
🚀🚀🚀 [BACKGROUND THREAD] Starting scan job scan_xxx in new event loop
✅ [API] Scan job scan_xxx submitted successfully

But NO logs from scan_and_create_jobs():
❌ Missing: "📂 [SCAN] Starting directory scan"
❌ Missing: "🔵 [SCAN] scan_and_create_jobs() entry point"  
❌ Missing: ANY scan activity
```

---

## Root Cause Hypothesis

**Line 1888:** `new_loop.run_until_complete(scan_job.scan_and_create_jobs())`

**Possible Issues:**

### 1. Event Loop Deadlock (MOST LIKELY)
- `run_until_complete()` blocks waiting for coroutine
- But coroutine never starts executing
- **Why?** Possible circular wait or missing executor

### 2. Silent Exception
- Exception thrown before first log statement
- Exception handler catches but doesn't log properly
- **Evidence:** Exception handler logs appear (tried Lines 1905-1913)

### 3. Threading Issue
- `io_executor.submit()` doesn't actually start thread
- Or thread dies immediately
- **Evidence:** "BACKGROUND THREAD" logs appear, so thread DOES start

---

## Next Steps

**Immediate Actions:**
1. ✅ Add debug logging at entry of `scan_and_create_jobs()`
2. ⏸️ Check if coroutine is created correctly
3. ⏸️ Verify event loop state
4. ⏸️ Test with simple sync function instead of async

**Workaround:**
- Use file upload API instead of directory scan
- Manually select files in GUI

---

**Status:** Problem NOT resolved - requires deeper investigation

**Recommendation:** Consider simplifying async architecture or using sync scan with threading
