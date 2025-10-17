# Backend Testing Quick Reference 🚀

**Nach Microservices Migration - Test Checklist**  
**Datum:** 14. Januar 2025  
**Status:** Ready for Testing ✅

---

## ⚡ Quick Test Commands

### 1. Stop All Services
```powershell
.\scripts\stop_services.ps1
```

**Expected Output:**
```
Stopping Main Backend on Port 45678... ✅
Stopping Ingestion Backend on Port 45679... ✅
All services stopped
```

---

### 2. Start Services (Simple)
```powershell
.\scripts\start_services.ps1
```

**Expected Output:**
```
Starting Main Backend on Port 45678...
Starting Ingestion Backend on Port 45679...
  Waiting for backends to initialize (10s)...

Running Health Checks...
  OK  Main Backend: healthy
  OK  Ingestion Backend: healthy
      Workers: 36 I/O, 36 CPU

Covina Microservices Running
Main Backend:      http://127.0.0.1:45678
Ingestion Backend: http://127.0.0.1:45679
```

---

### 3. Health Check (Manual)
```powershell
# Main Backend
curl http://127.0.0.1:45678/health | ConvertFrom-Json | Format-List

# Ingestion Backend
curl http://127.0.0.1:45679/health | ConvertFrom-Json | Format-List
```

**Expected Output (Main Backend):**
```
status        : healthy
version       : 3.4.x
port          : 45678
features      : {gap_detection, postgresql_backend, review_queue, compliance_service, chromadb, ...}
database      : {PostgreSQL: connected, ChromaDB: connected}
```

**Expected Output (Ingestion Backend):**
```
status        : healthy
version       : 3.4.x
port          : 45679
worker_pool   : {io_workers: 36, cpu_workers: 36}
databases     : {PostgreSQL: available, ChromaDB: available, Neo4j: available, CouchDB: available}
```

---

### 4. Test Admin Tools
```powershell
# Launch Admin Tools GUI
python admin_tools\launcher.py
```

**Expected:**
- Launcher window opens (Dark theme)
- "Backend Status" shows green ✅
- 3 Tool buttons clickable:
  - Golden Dataset Manager
  - Graph Pattern Manager
  - Governance Policy Manager

---

### 5. Full Deployment Test
```powershell
.\scripts\deploy_backend_v3_4_9.ps1
```

**Expected Output:**
```
🚀 Deploying Covina Microservices v3.4.9 (Dual Backend)

1️⃣  Backing up database...
   ✅ Database backed up to: ingestion_jobs.db.backup_20250114_HHMMSS

2️⃣  Stopping existing services...
   Stopping Main Backend on Port 45678... ✅
   Stopping Ingestion Backend on Port 45679... ✅

3️⃣  Validating code...
   ✅ Main Backend validation passed
   ✅ Ingestion Backend validation passed

4️⃣  Checking pending jobs (before restart)...
   📊 Pending jobs (0 progress): X

5️⃣  Starting Backends...
   🔄 Starting Main Backend (Port 45678)... ✅
   🔄 Starting Ingestion Backend (Port 45679)... ✅

6️⃣  Waiting for backends to be ready...
   ✅ Main Backend ready after X seconds
   ✅ Ingestion Backend ready after X seconds

7️⃣  Checking auto-resume results...
   📊 Jobs Status (after auto-resume):
      • Pending (0 progress):  X
      • Processing:            X
      • Failed (ghost jobs):   X

8️⃣  Checking worker pool...
   📊 Python processes (last 1 min): 36+
   ✅ Worker pool active (expected: 36+)

✅ Covina Microservices v3.4.9 deployed successfully!
```

---

## 🔍 Troubleshooting

### Issue: Backend doesn't start

**Symptom:**
```
FAIL Main Backend: not responding after 5 retries
```

**Solution:**
```powershell
# 1. Check if port is blocked
Get-NetTCPConnection -LocalPort 45678

# 2. Check logs
Get-Content logs\main_backend_error.log -Tail 20

# 3. Try manual start
python main_backend.py
```

---

### Issue: Import Error

**Symptom:**
```
ERROR: Could not import module 'covina_backend'
```

**Solution:**
```powershell
# Verify file exists
Get-ChildItem -Filter "*backend*.py"

# Should show:
# main_backend.py (64.8 KB) ✅
# ingestion_backend.py (126.4 KB) ✅
# backend_monolith_backup.py (390.6 KB) ✅

# If "covina_backend" import error persists:
# Check main_backend.py Line 1730:
# Should be: uvicorn.run("main_backend:app", ...)
# NOT:       uvicorn.run("covina_backend:app", ...)
```

---

### Issue: Admin Tools can't connect

**Symptom:**
```
Backend Status: ❌ Not Connected
```

**Solution:**
```powershell
# 1. Verify Main Backend is running
curl http://127.0.0.1:45678/health

# 2. Check admin_tools config
# File: admin_tools/golden_dataset_manager.py
# Line ~100: BACKEND_URL = "http://127.0.0.1:45678"

# 3. Test API manually
curl http://127.0.0.1:45678/api/golden-datasets
```

---

### Issue: Worker Pool not starting

**Symptom:**
```
⚠️  Worker pool not fully active yet
Python processes (last 1 min): 5
```

**Solution:**
```powershell
# Normal - Worker pool needs 30-60 seconds to fully spin up
# Wait and re-check:
Start-Sleep -Seconds 30
(Get-Process python -ErrorAction SilentlyContinue).Count

# Expected: 36+ processes (2 backends + 36 workers)
```

---

## 📊 Expected Process Count

```powershell
# Check Python processes
Get-Process python -ErrorAction SilentlyContinue | Measure-Object

# Expected Count:
# 1x Main Backend (uvicorn)
# 1x Ingestion Backend (uvicorn)
# 36x I/O Workers (ThreadPool - shared process)
# 36x CPU Workers (ProcessPool - separate processes)
# Total: ~38-40 Python processes
```

---

## 🎯 API Endpoint Tests

### Main Backend (Port 45678)

```powershell
# Health
curl http://127.0.0.1:45678/health

# Gap Detection
curl http://127.0.0.1:45678/api/gaps

# Review Queue
curl http://127.0.0.1:45678/api/review-queue

# Golden Datasets
curl http://127.0.0.1:45678/api/golden-datasets

# Graph Patterns
curl http://127.0.0.1:45678/api/graph-patterns

# Governance Policies
curl http://127.0.0.1:45678/api/governance-policies

# DSGVO
curl http://127.0.0.1:45678/api/dsgvo-check
```

### Ingestion Backend (Port 45679)

```powershell
# Health
curl http://127.0.0.1:45679/health

# Jobs List
curl http://127.0.0.1:45679/jobs

# Upload (requires file)
curl -Method POST -Form @{files=Get-Item "test.pdf"} http://127.0.0.1:45679/upload

# WebSocket (Browser)
# ws://127.0.0.1:45679/ws/jobs
```

---

## ✅ Success Criteria

### ✅ Startup Successful
- [ ] Main Backend responds on Port 45678
- [ ] Ingestion Backend responds on Port 45679
- [ ] Health checks return "healthy"
- [ ] Worker pool shows 36+ processes
- [ ] No errors in logs

### ✅ Admin Tools Working
- [ ] Launcher opens without errors
- [ ] Backend Status shows green ✅
- [ ] All 3 tools launch successfully
- [ ] CRUD operations work (Create, Read, Update, Delete)

### ✅ API Endpoints Working
- [ ] Main Backend: 22/23 endpoints respond
- [ ] Ingestion Backend: Upload works
- [ ] WebSocket connection successful
- [ ] Database connections verified

---

## 🚀 Next Steps After Testing

### If All Tests Pass ✅

1. **Update CHANGELOG.md:**
   ```markdown
   ## v3.4.10 - Backend Scripts Update
   - Microservices Migration complete
   - All PowerShell scripts updated
   - Dual backend startup validated
   ```

2. **Commit Changes:**
   ```powershell
   git add scripts/
   git add docs/BACKEND_SCRIPTS_UPDATE_COMPLETE.md
   git add .github/copilot-instructions.md
   git commit -m "feat: Update all scripts for Microservices architecture"
   ```

3. **Test in Production:**
   - Deploy to Linux server
   - Test Multi-Worker FastAPI (gunicorn)
   - Monitor performance

### If Tests Fail ❌

1. **Rollback Available:**
   ```powershell
   # Revert to monolith (if needed)
   git mv main_backend.py covina_backend.py
   git mv backend_monolith_backup.py backend.py
   git checkout scripts/
   ```

2. **Check Documentation:**
   - `docs/BACKEND_REFACTORING_COMPLETE.md`
   - `docs/BACKEND_SCRIPTS_UPDATE_COMPLETE.md`

3. **Report Issue:**
   - Check error logs
   - Note which test failed
   - Review copilot-instructions.md

---

## 📚 Related Documentation

- **Architecture:** `docs/BACKEND_REFACTORING_COMPLETE.md`
- **Scripts Update:** `docs/BACKEND_SCRIPTS_UPDATE_COMPLETE.md`
- **Microservices:** `docs/MICROSERVICES_ARCHITECTURE.md`
- **Admin Tools:** `admin_tools/README.md`

---

**Quick Reference - Ready to Use!**  
**Last Updated:** 14. Januar 2025  
**Status:** ✅ TESTING READY
