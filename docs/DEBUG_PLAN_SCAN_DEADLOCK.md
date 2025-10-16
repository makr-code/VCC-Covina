# Systematic Debug Plan - Scan Job Deadlock

**Date:** 14. Oktober 2025, 13:55 Uhr  
**Objective:** Find and fix why scan_and_create_jobs() never executes  
**Method:** Step-by-step isolation and testing

---

## Debug Strategy

### Phase 1: Verify Event Loop Execution (5 min)
**Test:** Does `run_until_complete()` actually run the coroutine?

**Changes:**
1. Add print() IMMEDIATELY at start of `scan_and_create_jobs()`
2. Add print() BEFORE `run_until_complete()` call
3. Add print() AFTER `run_until_complete()` call

**Expected:** If prints 1+2 appear but not 3 → coroutine blocks

---

### Phase 2: Simplify Async Chain (10 min)
**Test:** Replace `_scan_directory_async()` with sync version

**Changes:**
1. Create `_scan_directory_sync()` method
2. Call directly without `await`
3. See if scan completes

**Expected:** If works → async/await chain is broken

---

### Phase 3: Test Minimal Coroutine (5 min)
**Test:** Replace entire `scan_and_create_jobs()` with dummy

**Changes:**
```python
async def scan_and_create_jobs(self):
    print("HELLO FROM COROUTINE")
    await asyncio.sleep(0.1)
    print("COROUTINE COMPLETED")
    return
```

**Expected:** If prints appear → problem is in scan logic

---

### Phase 4: Check Coroutine Creation (5 min)
**Test:** Verify coroutine object is created

**Changes:**
```python
coro = scan_job.scan_and_create_jobs()
print(f"Coroutine: {coro}")
print(f"Type: {type(coro)}")
new_loop.run_until_complete(coro)
```

**Expected:** Should see `<coroutine object ...>`

---

## Implementation Order

1. ✅ Phase 1 (quickest)
2. → Phase 3 (if Phase 1 fails)
3. → Phase 2 (if Phase 3 works)
4. → Phase 4 (if all else fails)

---

**Status:** Starting Phase 1
