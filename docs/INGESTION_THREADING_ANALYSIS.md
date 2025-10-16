# Ingestion Backend - Threading & Queue Architektur Analyse

**Datum:** 12. Oktober 2025, 17:45 Uhr  
**Status:** 🔴 POTENTIAL ISSUE IDENTIFIED

---

## 🔍 Aktuelle Architektur

### Aktuelles Design

```python
# Upload Endpoint
@app.post("/upload/files")
async def upload_files(background_tasks: BackgroundTasks, files: List[UploadFile]):
    # 1. Speichere Dateien (blocking I/O)
    # 2. Starte BackgroundTask
    background_tasks.add_task(process_documents_batch, job_id, file_paths, temp_dir)
    # 3. Return sofort (non-blocking)
    return UploadResponse(...)

# Background Processing
async def process_documents_batch(job_id, file_paths, temp_dir):
    # Läuft in separatem Thread (FastAPI BackgroundTasks)
    tasks = [process_single_document(fp, jm) for fp in file_paths]
    results = await asyncio.gather(*tasks)  # Parallel I/O
```

### Thread Pool Konfiguration

```python
CPU_COUNT = multiprocessing.cpu_count()  # 20 Cores
CPU_WORKERS = CPU_COUNT // 2            # 10 Workers
IO_WORKERS = CPU_COUNT * 2 - 2          # 38 Workers

io_executor = ThreadPoolExecutor(max_workers=IO_WORKERS)   # ✅ Verwendet
cpu_executor = ProcessPoolExecutor(max_workers=CPU_WORKERS) # ❌ NICHT verwendet!
```

---

## 🔴 Identifizierte Probleme

### Problem 1: BackgroundTasks ist Thread-basiert

**Was passiert:**
```python
background_tasks.add_task(process_documents_batch, ...)
# → Läuft in einem separaten Thread
# → Shared Memory mit Main Thread
# → GIL (Global Interpreter Lock) kann blockieren
```

**Impact:**
- Bei CPU-intensiver Arbeit: Main Thread wird blockiert (GIL)
- Bei vielen simultanen Uploads: Thread Pool Exhaustion
- Bei langen Tasks: Keine Task-Cancellation möglich

---

### Problem 2: UDS3 Processing ist MOCK

**Aktueller Code:**
```python
async def process_document_with_uds3(file_path, content, job_manager):
    # TODO: Implement actual UDS3 processing
    # For now, return mock metrics
    return {
        "content_extracted_chars": len(content),  # Nur String-Länge!
        "ai_entities_found": 0,                    # Mock!
        ...
    }
```

**Wenn echte UDS3-Verarbeitung implementiert wird:**
- AI Entity Extraction (CPU-intensiv)
- Embedding Generation (CPU/GPU-intensiv)
- Classification (CPU-intensiv)
- Multiple Database Writes (I/O-intensiv)

**→ Könnte FastAPI blockieren!**

---

### Problem 3: CPU Executor wird nicht genutzt

```python
cpu_executor = ProcessPoolExecutor(max_workers=CPU_WORKERS)  # Erstellt aber nicht verwendet!
```

**Process Pool wäre besser für:**
- AI Entity Extraction
- Embedding Generation
- Content Classification
- Keine GIL-Probleme!

---

## ✅ Empfohlene Lösung: Queue-basiertes Threading

### Architecture Overview

```
FastAPI Endpoint
      ↓
   [Job Queue]  ← Thread-safe Queue
      ↓
 Worker Threads (dedicated)
      ↓
   [I/O Pool]   ← File I/O, DB Writes
      ↓
  [CPU Pool]    ← AI Processing, Embeddings
      ↓
  [WebSocket]   ← Real-time Updates
```

### Implementation Plan

#### 1. Job Queue (thread-safe)
```python
import queue
import threading

# Global Job Queue
job_queue = queue.Queue(maxsize=1000)

class IngestionJob:
    def __init__(self, job_id, file_paths, temp_dir):
        self.job_id = job_id
        self.file_paths = file_paths
        self.temp_dir = temp_dir
        self.status = "queued"
        self.created_at = datetime.now()
```

#### 2. Worker Threads (dedicated)
```python
class IngestionWorker(threading.Thread):
    def __init__(self, worker_id, job_queue):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # Get job from queue (blocking, timeout 1s)
                job = self.job_queue.get(timeout=1.0)
                
                # Process job
                self.process_job(job)
                
                # Mark as done
                self.job_queue.task_done()
                
            except queue.Empty:
                continue  # No jobs, wait for next
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
    
    def process_job(self, job):
        # Non-blocking: läuft in separatem Thread
        # Kann asyncio.run() nutzen für async code
        asyncio.run(process_documents_batch_async(job))
```

#### 3. FastAPI Endpoint (non-blocking)
```python
@app.post("/upload/files")
async def upload_files(files: List[UploadFile]):
    # 1. Speichere Dateien (in Thread Pool)
    loop = asyncio.get_event_loop()
    file_paths = await loop.run_in_executor(io_executor, save_files, files)
    
    # 2. Create Job
    job = IngestionJob(job_id, file_paths, temp_dir)
    
    # 3. Add to Queue (non-blocking!)
    try:
        job_queue.put_nowait(job)
    except queue.Full:
        raise HTTPException(503, "Job queue full, try again later")
    
    # 4. Return immediately
    return UploadResponse(job_id=job.job_id, ...)
```

---

## 📊 Performance Vergleich

### Aktuell (BackgroundTasks)
```
Upload Request → BackgroundTask Thread → AsyncIO Gather → I/O Pool
                     ↓ (GIL locked bei CPU work)
                FastAPI Main Thread kann blockieren
```

**Problems:**
- GIL Contention bei CPU-intensiver Arbeit
- Thread Pool kann erschöpft sein
- Keine Job-Priorisierung

### Verbessert (Queue + Workers)
```
Upload Request → Job Queue (instant return)
                     ↓ (completely decoupled)
              Worker Threads → Process Pool (AI) + I/O Pool (DB)
                     ↓ (no GIL issues)
               FastAPI bleibt responsive
```

**Benefits:**
- ✅ FastAPI NIE blockiert (sofortiger Return)
- ✅ Job Queue mit Priorisierung
- ✅ Worker Pool kontrollierbar (start/stop)
- ✅ Process Pool für CPU-Arbeit (keine GIL)
- ✅ Graceful Shutdown möglich
- ✅ Job Cancellation implementierbar

---

## 🎯 Implementation Recommendation

### Phase 1: Minimal Changes (Quick Fix)
**Keep BackgroundTasks, aber nutze Process Pool:**

```python
async def process_documents_batch(job_id, file_paths, temp_dir):
    jm = get_job_manager()
    
    # Nutze Process Pool für CPU-intensive Arbeit
    loop = asyncio.get_event_loop()
    
    def process_in_worker(file_path):
        # Läuft in separatem Process (kein GIL!)
        content = Path(file_path).read_text()
        return process_document_uds3_sync(file_path, content)
    
    # Process Pool statt asyncio.gather
    results = await loop.run_in_executor(
        cpu_executor,
        lambda: [process_in_worker(fp) for fp in file_paths]
    )
```

**Effort:** 2-3 Stunden  
**Impact:** GIL-Probleme gelöst

---

### Phase 2: Queue-based Architecture (Recommended)
**Implement Job Queue + Worker Threads:**

```python
# 1. Start Worker Threads
NUM_WORKERS = 4
workers = [IngestionWorker(i, job_queue) for i in range(NUM_WORKERS)]
for worker in workers:
    worker.start()

# 2. Endpoint queues job
@app.post("/upload/files")
async def upload_files(...):
    job = IngestionJob(...)
    job_queue.put_nowait(job)
    return UploadResponse(...)

# 3. Worker processes job
class IngestionWorker:
    def process_job(self, job):
        asyncio.run(process_documents_batch_async(job))
```

**Effort:** 1-2 Tage  
**Impact:** 
- FastAPI 100% non-blocking
- Job Queue mit Backpressure
- Graceful Shutdown
- Job Cancellation
- Worker Pool Management

---

### Phase 3: Full Async Rewrite (Future)
**Pure async/await mit asyncio:**

```python
# Async Worker Pool
async def worker_loop(worker_id):
    while True:
        job = await async_job_queue.get()
        await process_job_async(job)

# Start Workers
asyncio.create_task(worker_loop(1))
asyncio.create_task(worker_loop(2))
```

**Effort:** 3-5 Tage  
**Impact:** 
- Native async/await
- Höhere Concurrency
- Bessere Performance
- Komplexerer Code

---

## 🔧 Immediate Action Required?

### Current Status: 🟡 MEDIUM PRIORITY

**Why not urgent:**
- ✅ BackgroundTasks funktioniert aktuell
- ✅ UDS3 Processing ist noch Mock (keine CPU-Last)
- ✅ Load Tests zeigen gute Performance (187 f/s upload)

**When to implement:**
- 🔴 **Phase 1 (Process Pool):** Wenn echte UDS3-Verarbeitung implementiert wird
- 🟡 **Phase 2 (Queue):** Wenn >500 QPS Upload Traffic erwartet
- 🟢 **Phase 3 (Async):** Wenn horizontal scaling auf Kubernetes geplant

---

## 📋 Decision Matrix

| Scenario | Current (BackgroundTasks) | Phase 1 (Process Pool) | Phase 2 (Queue) | Phase 3 (Async) |
|----------|--------------------------|------------------------|-----------------|-----------------|
| **Mock UDS3** | ✅ OK | ⚪ Overkill | ⚪ Overkill | ⚪ Overkill |
| **Real UDS3** | 🔴 GIL Issues | ✅ OK | ✅ Better | ✅ Best |
| **High Load** | 🟡 Thread Exhaustion | 🟡 OK | ✅ OK | ✅ Best |
| **Complexity** | ✅ Simple | ✅ Simple | 🟡 Medium | 🔴 Complex |
| **Effort** | ✅ 0h | ✅ 2-3h | 🟡 1-2d | 🔴 3-5d |

---

## 🎯 Recommendation

**For NOW (Mock UDS3):**
- ✅ Keep current BackgroundTasks architecture
- ✅ Works well for current load (187 f/s)
- ✅ No blocking issues (Mock ist lightweight)

**For LATER (Real UDS3):**
1. **Implement Phase 1** (Process Pool) - Quick fix für GIL
2. **Monitor Performance** - Check for blocking
3. **Consider Phase 2** (Queue) - If high load expected
4. **Phase 3** (Async) - Only for cloud-scale deployment

**Priority:** 🟡 Plan Phase 1 when implementing real UDS3 processing

---

**Erstellt:** 12. Oktober 2025, 17:45 Uhr  
**Status:** Analysis Complete  
**Nächster Schritt:** Monitor + Phase 1 when UDS3 real processing starts
