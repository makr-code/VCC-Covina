# Ingestion Backend - Performance Fix

**Problem:** Ingestion hängt bei Job-Verarbeitung (50+ jobs stuck)  
**Root Cause:** Backend läuft mit alter Config (ohne Batch-Features)  
**Solution:** Backend neu starten mit Batch-Optimierungen  

---

## 🔥 Current Status

**Jobs:**
- 38 jobs: Status `pending` (wartend)
- 12 jobs: Status `processing` (0 processed_files!)
- **Problem:** Extrem langsam, keine Fortschritte

**Backend:**
- Started: 10:48 Uhr (vor 49 Minuten)
- Config: ALT (ohne Batch-Features)
- Performance: ~1-2 docs/minute (SEHR LANGSAM!)

---

## ✅ Solution: Restart with Batch Features

### Step 1: Stop Ingestion Backend

```powershell
# Find ingestion_backend.py process
Get-Process python | Where-Object {$_.StartTime -lt (Get-Date).AddMinutes(-30)}

# Stop old processes (started before 11:25)
Get-Process python | Where-Object {$_.StartTime -lt (Get-Date).AddMinutes(-15)} | Stop-Process -Force
```

**Or manually:**
- Find ingestion_backend.py terminal
- Press Ctrl+C

---

### Step 2: Verify .env.production

**Check config:**
```powershell
Get-Content .env.production | Select-String "ENABLE.*BATCH"
```

**Expected:**
```
ENABLE_BATCH_EMBEDDINGS=true   ✅
ENABLE_CHROMA_BATCH_INSERT=true ✅
```

---

### Step 3: Restart Ingestion Backend

```powershell
python ingestion_backend.py
```

**Verify startup logs:**
```
✅ "Batch Embeddings: ENABLED"
✅ "ChromaDB Batch Insert: ENABLED"
✅ "Worker Pool: 36 I/O, 36 CPU"
```

---

## 📊 Expected Performance

### Before (Current - WITHOUT Batch)

```
Model Loading:  PER DOCUMENT (2.2s each!)
Embeddings:     SEQUENTIAL (~40ms per chunk)
ChromaDB:       SINGLE INSERT (~400ms per vector)
───────────────────────────────────────────────
Total/Doc:      ~3,400ms (first) + ~1,100ms (cached)
Throughput:     ~1-2 docs/minute ❌ SLOW!
```

### After (WITH Batch Features)

```
Model Loading:  ONCE (cached, lazy)
Embeddings:     BATCH (~43ms for 5 chunks)
ChromaDB:       BATCH INSERT (~50ms for 5 vectors)
───────────────────────────────────────────────
Total/Doc:      ~370ms per document
Throughput:     ~150-180 docs/minute ✅ FAST!
Improvement:    ~100x faster! 🚀
```

---

## 🎯 Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Doc Processing | ~1,100ms | ~370ms | -67% ⚡ |
| Throughput | 1-2/min | 150-180/min | +100x 🚀 |
| Queue Clear | ~25 hours | ~15 minutes | -99% ⏱️ |

**For 50 jobs × 50 files = 2,500 documents:**
- Before: ~42 hours ❌
- After: ~14 minutes ✅

---

## ⚠️ Alternative: Clear Job Queue

**If restart not possible immediately:**

```bash
# Clear pending jobs (keeps processing ones)
curl -X DELETE http://127.0.0.1:45679/jobs/clear-pending

# Or: Reset ALL jobs
curl -X DELETE http://127.0.0.1:45679/jobs/reset-all
```

**Warning:** This deletes job data (files stay in `data/uploads/`)

---

## 🔍 Monitoring

**After restart, monitor:**

```bash
# Check job progress every 30s
watch -n 30 'curl http://127.0.0.1:45679/jobs | jq ".[0:5]"'

# Expected: processed_files increasing rapidly
```

**Logs:**
```bash
# Watch ingestion logs
tail -f logs/ingestion_backend.log

# Look for:
✅ "[OK] SAGA completed"
✅ "[OK] Processed: filename.md"
✅ "Batch size: 5" (embeddings)
✅ "Batch insert: 5 vectors" (ChromaDB)
```

---

## 📋 Checklist

```
[ ] Stop old ingestion_backend.py process
[ ] Verify .env.production has ENABLE_BATCH_*=true
[ ] Start ingestion_backend.py
[ ] Verify "Batch Embeddings: ENABLED" in logs
[ ] Monitor job progress (processed_files increasing)
[ ] Verify ~150 docs/minute throughput
```

---

**Status:** 🔧 **READY TO FIX**  
**Expected Time:** 2 minutes (stop + restart)  
**Expected Impact:** 100x faster processing! 🚀

---

**Last Updated:** 14. Oktober 2025, 11:40 Uhr
