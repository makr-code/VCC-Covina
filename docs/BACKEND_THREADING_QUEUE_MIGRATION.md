# Backend Threading & Queue Migration - TODO

**Status:** ✅ SUPERSEDED - Microservices Architecture implementiert  
**Datum:** 11. Oktober 2025  
**Priorität:** P0 (höchste Priorität)  
**Neue Lösung:** Siehe `MICROSERVICES_ARCHITECTURE.md`

> **⚠️ HINWEIS:** Diese Celery-basierte Lösung wurde durch eine **Microservices-Architektur** ersetzt.
> Statt Celery nutzen wir jetzt ein **separates Ingestion Backend** (eigener FastAPI Service).
> 
> **Siehe:** `docs/MICROSERVICES_ARCHITECTURE.md` für Details.

## Problem-Analyse

### Kritische Symptome
1. **Backend nicht erreichbar während Ingestion**
   - Frontend zeigt API-Timeouts auf `/health`, `/database/stats`, etc.
   - Backend-Prozess läuft (PID aktiv) aber HTTP-Server antwortet nicht
   - Ursache: Synchrone Ingestion blockiert Event Loop

2. **Blockierende Operationen identifiziert**
   ```python
   # backend.py, Line 7870: process_documents_background()
   # Läuft als FastAPI BackgroundTask aber blockiert trotzdem
   
   # backend.py, Line 7585: process_documents_parallel()
   # Nutzt asyncio.gather() aber I/O Operations blockieren
   
   # backend.py, Line 7209: process_single_document_async()
   # CPU-intensive: Content Reading, Parsing, AI Processing
   ```

3. **Aktuelle Architektur-Schwächen**
   - ❌ **FastAPI BackgroundTasks:** Laufen im gleichen Event Loop
   - ❌ **I/O Executor:** Nur für File Read, nicht für Processing
   - ❌ **Keine Job Queue:** Jobs laufen sofort statt wartend
   - ❌ **Kein Worker Pool:** Keine isolierten Worker-Prozesse
   - ❌ **Keine Priorisierung:** Alle Jobs gleich wichtig

### Performance-Metriken (Aktuell)
```python
# backend.py, Lines 330-336
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = max(1, CPU_COUNT - 1)  # 15 Workers auf 16 Cores
io_executor = ThreadPoolExecutor(max_workers=OPTIMAL_WORKERS)
cpu_executor = ProcessPoolExecutor(max_workers=OPTIMAL_WORKERS)
```

**Problem:** Executors existieren, werden aber NICHT für Ingestion genutzt!

---

## Migration-Plan: Von Synchron zu Asynchron

### Phase 1: Task Queue System (PRIORITÄT 1) ⏰ 2-3h

#### 1.1 Celery Integration
**Ziel:** Entkopplung von API und Ingestion-Processing

**Erforderliche Änderungen:**

**`requirements.txt` erweitern:**
```python
celery[redis]==5.3.4
redis==5.0.1
flower==2.0.1  # Monitoring UI
```

**Neue Datei: `covina/celery_app.py`**
```python
from celery import Celery
import os

# Redis als Broker & Result Backend (läuft schon auf 192.168.178.94)
REDIS_URL = os.getenv('REDIS_URL', 'redis://192.168.178.94:6379/0')

celery_app = Celery(
    'covina',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['covina.tasks']  # Task Module
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Berlin',
    enable_utc=True,
    
    # Worker Config
    worker_prefetch_multiplier=1,  # Nur 1 Task pro Worker
    worker_max_tasks_per_child=50,  # Worker Recycling
    task_acks_late=True,  # Ack nach Completion
    
    # Task Routing
    task_routes={
        'covina.tasks.process_single_document': {'queue': 'ingestion'},
        'covina.tasks.process_archive': {'queue': 'ingestion'},
        'covina.tasks.process_batch': {'queue': 'batch'},
        'covina.tasks.send_notification': {'queue': 'notifications'},
    },
    
    # Retry Policy
    task_default_retry_delay=30,  # 30s zwischen Retries
    task_max_retries=3,
)
```

**Neue Datei: `covina/tasks.py`**
```python
from celery import Task, group, chord
from covina.celery_app import celery_app
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DatabaseTask(Task):
    """Base Task mit Auto-Retry bei DB-Fehlern"""
    autoretry_for = (
        ConnectionError,
        TimeoutError,
    )
    retry_kwargs = {'max_retries': 3, 'countdown': 5}
    retry_backoff = True
    retry_backoff_max = 600  # Max 10min
    retry_jitter = True

@celery_app.task(base=DatabaseTask, bind=True)
def process_single_document(self, file_path: str, job_id: str) -> Dict[str, Any]:
    """
    Verarbeite einzelnes Dokument (Celery Task)
    
    Args:
        file_path: Pfad zur Datei
        job_id: Job ID für Progress Tracking
    
    Returns:
        Verarbeitungs-Metriken
    """
    try:
        # Import hier um Circular Dependencies zu vermeiden
        from backend import get_job_manager
        import asyncio
        
        jm = get_job_manager()
        
        # Validierung
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
        
        # Lese Dateiinhalt
        try:
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
        except UnicodeDecodeError:
            content = Path(file_path).read_text(encoding='latin-1', errors='ignore')
        
        # UDS3 Processing
        if jm.uds3_ready:
            # Nutze asyncio für UDS3 Processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                from backend import process_document_with_uds3
                metrics = loop.run_until_complete(
                    process_document_with_uds3(file_path, content, jm)
                )
            finally:
                loop.close()
            
            # Update Job Progress
            job = jm.get_job(job_id)
            if job:
                processed = job.get('processed_files', 0) + 1
                jm.update_job_progress(job_id, processed)
            
            logger.info(f"✅ Celery: {Path(file_path).name} verarbeitet")
            return metrics
        else:
            raise RuntimeError("UDS3 nicht verfügbar")
            
    except Exception as e:
        logger.error(f"❌ Celery Task Fehler: {file_path}: {e}")
        # Auto-Retry durch DatabaseTask Base Class
        raise self.retry(exc=e)

@celery_app.task(bind=True)
def process_batch_completion(self, results: List[Dict], job_id: str):
    """
    Callback nach Batch-Completion (Celery Chord)
    
    Args:
        results: Liste von Task-Ergebnissen
        job_id: Job ID
    """
    from backend import get_job_manager
    
    jm = get_job_manager()
    
    # Aggregiere Metriken
    total_metrics = {
        "total_files": len(results),
        "successful_files": sum(1 for r in results if r.get('error_info') is None),
        "failed_files": sum(1 for r in results if r.get('error_info') is not None),
        "content_extracted_chars": sum(r.get('content_extracted_chars', 0) for r in results),
        "ai_entities_found": sum(r.get('ai_entities_found', 0) for r in results),
    }
    
    # Job abschließen
    jm.set_job_metrics(job_id, total_metrics)
    jm.update_job_status(job_id, "completed")
    
    logger.info(f"✅ Batch Job {job_id} abgeschlossen: {total_metrics['successful_files']}/{total_metrics['total_files']}")

@celery_app.task
def send_job_completion_notification(job_id: str, metrics: Dict):
    """E-Mail Benachrichtigung (Celery Task)"""
    from backend import mail_service
    from mail_service import MailRecipient
    import asyncio
    
    if mail_service:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recipients = [MailRecipient(email="admin@fritz.box", name="Covina Admin")]
            loop.run_until_complete(
                mail_service.send_job_completion_email(recipients, job_id, metrics)
            )
        finally:
            loop.close()
```

#### 1.2 Backend API Migration

**`backend.py` Änderungen:**

**Upload Endpoint (Line 4770):**
```python
# VORHER:
@app.post("/upload/files", response_model=UploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,  # ❌ Blockiert Event Loop
    files: List[UploadFile] = File(...)
):
    # ... File Speicherung ...
    
    background_tasks.add_task(
        process_documents_background,  # ❌ Synchron im gleichen Event Loop
        job_id, file_paths, temp_dir
    )

# NACHHER:
@app.post("/upload/files", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...)
):
    """Upload und verarbeite mehrere Dateien (Celery Queue)"""
    from covina.tasks import process_single_document, process_batch_completion
    from celery import group, chord
    
    if not files:
        raise HTTPException(status_code=400, detail="Keine Dateien hochgeladen")
    
    jm = get_job_manager()
    job_id = jm.create_job(len(files))
    
    # Dateien temporär speichern
    temp_dir = Path(tempfile.mkdtemp(prefix="covina_"))
    file_paths = []
    
    try:
        for file in files:
            file_path = temp_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            file_paths.append(str(file_path))
        
        # ✅ Celery Chord: Parallele Tasks + Completion Callback
        job = chord(
            group(
                process_single_document.s(fp, job_id) 
                for fp in file_paths
            )
        )(process_batch_completion.s(job_id))
        
        logger.info(f"📤 Upload erfolgreich - Celery Job {job_id} mit {len(files)} Dateien")
        
        return UploadResponse(
            message=f"Upload erfolgreich. {len(files)} Dateien werden verarbeitet.",
            job_id=job_id,
            file_count=len(files),
            estimated_processing_time=f"{len(files) * 2}s"
        )
        
    except Exception as e:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        jm.update_job_status(job_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"Upload fehlgeschlagen: {e}")
```

**Directory Upload (Line 4818):**
```python
# VORHER:
@app.post("/upload/directory", response_model=UploadResponse)
async def upload_directory(
    background_tasks: BackgroundTasks,  # ❌
    directory_path: str = Form(...),
    chunk_size: int = Form(50)
):
    # ... Directory Scan ...
    
    for chunk in file_chunks:
        background_tasks.add_task(  # ❌ Blockiert
            process_documents_background,
            chunk_job_id, chunk, None
        )

# NACHHER:
@app.post("/upload/directory", response_model=UploadResponse)
async def upload_directory(
    directory_path: str = Form(...),
    chunk_size: int = Form(50)
):
    """Verarbeite Verzeichnis mit Celery Queue"""
    from covina.tasks import process_single_document, process_batch_completion
    from celery import group, chord
    
    # ... Directory Scan (gleich) ...
    
    # ✅ Celery Chord für jeden Chunk
    for i, chunk in enumerate(file_chunks):
        chunk_job_id = jm.create_job(len(chunk))
        
        job = chord(
            group(
                process_single_document.s(fp, chunk_job_id) 
                for fp in chunk
            )
        )(process_batch_completion.s(chunk_job_id))
    
    return UploadResponse(...)
```

#### 1.3 Worker Deployment

**Neue Datei: `scripts/start_celery_workers.sh`**
```bash
#!/bin/bash
# Starte Celery Workers für Covina Backend

# Ingestion Queue (CPU-intensive)
celery -A covina.celery_app worker \
    --queue=ingestion \
    --concurrency=14 \
    --loglevel=info \
    --logfile=logs/celery_ingestion_%I.log \
    --pidfile=tmp/celery_ingestion_%I.pid \
    --hostname=ingestion@%h &

# Batch Queue (Memory-intensive)
celery -A covina.celery_app worker \
    --queue=batch \
    --concurrency=4 \
    --max-memory-per-child=2000000 \
    --loglevel=info \
    --logfile=logs/celery_batch_%I.log \
    --pidfile=tmp/celery_batch_%I.pid \
    --hostname=batch@%h &

# Notification Queue (I/O)
celery -A covina.celery_app worker \
    --queue=notifications \
    --concurrency=2 \
    --loglevel=info \
    --logfile=logs/celery_notifications_%I.log \
    --pidfile=tmp/celery_notifications_%I.pid \
    --hostname=notifications@%h &

# Flower Monitoring UI
celery -A covina.celery_app flower \
    --port=5555 \
    --basic_auth=admin:covina123 &

echo "✅ Celery Workers gestartet"
echo "📊 Monitoring UI: http://localhost:5555"
```

**PowerShell Version: `scripts/start_celery_workers.ps1`**
```powershell
# Starte Celery Workers für Covina Backend

# Ingestion Queue
Start-Process -NoNewWindow -FilePath "celery" -ArgumentList `
    "-A", "covina.celery_app", "worker", `
    "--queue=ingestion", `
    "--concurrency=14", `
    "--loglevel=info", `
    "--logfile=logs/celery_ingestion.log", `
    "--hostname=ingestion@%COMPUTERNAME%"

# Batch Queue
Start-Process -NoNewWindow -FilePath "celery" -ArgumentList `
    "-A", "covina.celery_app", "worker", `
    "--queue=batch", `
    "--concurrency=4", `
    "--max-memory-per-child=2000000", `
    "--loglevel=info", `
    "--logfile=logs/celery_batch.log", `
    "--hostname=batch@%COMPUTERNAME%"

# Notification Queue
Start-Process -NoNewWindow -FilePath "celery" -ArgumentList `
    "-A", "covina.celery_app", "worker", `
    "--queue=notifications", `
    "--concurrency=2", `
    "--loglevel=info", `
    "--logfile=logs/celery_notifications.log", `
    "--hostname=notifications@%COMPUTERNAME%"

# Flower Monitoring
Start-Process -NoNewWindow -FilePath "celery" -ArgumentList `
    "-A", "covina.celery_app", "flower", `
    "--port=5555", `
    "--basic_auth=admin:covina123"

Write-Host "✅ Celery Workers gestartet" -ForegroundColor Green
Write-Host "📊 Monitoring UI: http://localhost:5555" -ForegroundColor Cyan
```

---

### Phase 2: ProcessPoolExecutor für CPU-Intensive Tasks ⏰ 1-2h

**Problem:** `process_document_with_uds3()` ist CPU-intensiv (AI, Parsing)

#### 2.1 CPU-Bound Processing Migration

**Neue Datei: `covina/workers.py`**
```python
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any
from pathlib import Path
import multiprocessing

# CPU-Bound Worker Pool
CPU_COUNT = multiprocessing.cpu_count()
WORKER_COUNT = max(1, CPU_COUNT - 2)  # Reserve 2 Cores für FastAPI

cpu_pool = ProcessPoolExecutor(max_workers=WORKER_COUNT)

def process_document_cpu_worker(file_path: str, content: str) -> Dict[str, Any]:
    """
    CPU-intensives Processing in separatem Prozess
    
    WICHTIG: Läuft in separatem Prozess - keine shared memory
    """
    import asyncio
    from backend import get_job_manager, process_document_with_uds3
    
    # Neuer Event Loop für diesen Prozess
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        jm = get_job_manager()
        
        # UDS3 Processing
        metrics = loop.run_until_complete(
            process_document_with_uds3(file_path, content, jm)
        )
        
        return metrics
    finally:
        loop.close()

async def process_document_async_worker(file_path: str) -> Dict[str, Any]:
    """
    Async Wrapper für CPU-Worker (non-blocking)
    """
    # Lese File Content in ThreadPool (I/O)
    loop = asyncio.get_event_loop()
    content = await loop.run_in_executor(
        None,  # Default ThreadPool
        lambda: Path(file_path).read_text(encoding='utf-8', errors='ignore')
    )
    
    # CPU-Processing in separatem Prozess
    metrics = await loop.run_in_executor(
        cpu_pool,  # ProcessPoolExecutor
        process_document_cpu_worker,
        file_path,
        content
    )
    
    return metrics
```

**Backend Integration:**
```python
# backend.py - Update process_single_document_async()

async def process_single_document_async(
    file_path: str,
    job_manager: 'JobManager',
    retry_count: int = 2
) -> Dict[str, Any]:
    """Verarbeite Dokument mit ProcessPoolExecutor (CPU-optimiert)"""
    from covina.workers import process_document_async_worker
    
    try:
        # ✅ Non-blocking CPU-Processing
        metrics = await process_document_async_worker(file_path)
        return metrics
    except Exception as e:
        logger.error(f"❌ Worker Fehler: {e}")
        return _create_error_metrics(file_path, "WORKER_ERROR", str(e))
```

---

### Phase 3: Job Priority & Rate Limiting ⏰ 1h

#### 3.1 Priority Queues

**`covina/celery_app.py` erweitern:**
```python
celery_app.conf.update(
    # Priority Queues
    task_routes={
        'covina.tasks.process_single_document': {
            'queue': 'ingestion',
            'priority': 5  # 0 = lowest, 10 = highest
        },
        'covina.tasks.process_urgent_document': {
            'queue': 'ingestion',
            'priority': 10  # Hohe Priorität
        },
        'covina.tasks.send_notification': {
            'queue': 'notifications',
            'priority': 8
        },
    },
    
    # Rate Limiting
    task_annotations={
        'covina.tasks.process_single_document': {
            'rate_limit': '100/m',  # Max 100 Tasks pro Minute
        },
        'covina.tasks.send_notification': {
            'rate_limit': '10/m',  # Max 10 E-Mails pro Minute
        },
    },
)
```

#### 3.2 Job Prioritization API

**`backend.py` neuer Endpoint:**
```python
@app.post("/upload/files/priority", response_model=UploadResponse)
async def upload_files_priority(
    files: List[UploadFile] = File(...),
    priority: int = Form(5, ge=0, le=10)
):
    """Upload mit Priorität (0=niedrig, 10=hoch)"""
    from covina.tasks import process_single_document
    from celery import group, chord
    
    # ... File Speicherung ...
    
    # ✅ Celery mit Priorität
    job = chord(
        group(
            process_single_document.apply_async(
                args=(fp, job_id),
                priority=priority  # ✅ Priorität setzen
            )
            for fp in file_paths
        )
    )(process_batch_completion.s(job_id))
    
    return UploadResponse(...)
```

---

### Phase 4: Job Monitoring & Health Checks ⏰ 1h

#### 4.1 Celery Status Endpoint

**`backend.py` neue Endpoints:**
```python
@app.get("/system/celery/status")
async def get_celery_status():
    """Celery Worker Status"""
    from covina.celery_app import celery_app
    
    # Active Workers
    inspect = celery_app.control.inspect()
    
    active = inspect.active()
    registered = inspect.registered()
    stats = inspect.stats()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "workers": {
            "active": len(active or {}),
            "registered": len(registered or {}),
            "details": stats or {}
        },
        "queues": {
            "ingestion": {
                "workers": sum(1 for w in (active or {}) if 'ingestion' in w),
                "concurrency": 14
            },
            "batch": {
                "workers": sum(1 for w in (active or {}) if 'batch' in w),
                "concurrency": 4
            },
            "notifications": {
                "workers": sum(1 for w in (active or {}) if 'notifications' in w),
                "concurrency": 2
            }
        }
    }

@app.get("/system/celery/tasks")
async def get_celery_tasks():
    """Aktive Celery Tasks"""
    from covina.celery_app import celery_app
    
    inspect = celery_app.control.inspect()
    
    active_tasks = inspect.active()
    reserved_tasks = inspect.reserved()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "active_tasks": sum(len(tasks) for tasks in (active_tasks or {}).values()),
        "reserved_tasks": sum(len(tasks) for tasks in (reserved_tasks or {}).values()),
        "details": {
            "active": active_tasks or {},
            "reserved": reserved_tasks or {}
        }
    }
```

#### 4.2 Health Check Integration

**`backend.py` /health Endpoint erweitern:**
```python
@app.get("/health")
async def health_check():
    """Health Check mit Celery Status"""
    from covina.celery_app import celery_app
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "fastapi": "✅ running",
            "uds3": "✅" if get_job_manager().uds3_ready else "❌",
        }
    }
    
    # Celery Worker Check
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats and len(stats) > 0:
            health["components"]["celery"] = f"✅ {len(stats)} workers"
        else:
            health["components"]["celery"] = "⚠️ no workers"
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["celery"] = f"❌ {str(e)}"
        health["status"] = "degraded"
    
    return health
```

---

## Implementierungs-Checkliste

### Phase 1: Celery Setup (Kritisch)
- [ ] **1.1** Redis Connection testen (192.168.178.94:6379)
- [ ] **1.2** `requirements.txt` aktualisieren (celery, redis, flower)
- [ ] **1.3** `covina/celery_app.py` erstellen
- [ ] **1.4** `covina/tasks.py` erstellen
- [ ] **1.5** `backend.py` Upload Endpoints migrieren
- [ ] **1.6** Worker Start-Scripts erstellen
- [ ] **1.7** Celery Workers starten
- [ ] **1.8** Flower Monitoring UI testen (http://localhost:5555)
- [ ] **1.9** Ersten Test-Upload durchführen
- [ ] **1.10** Backend HTTP Responsiveness während Upload testen

### Phase 2: CPU Workers
- [ ] **2.1** `covina/workers.py` erstellen
- [ ] **2.2** ProcessPoolExecutor integrieren
- [ ] **2.3** `process_single_document_async()` migrieren
- [ ] **2.4** Performance-Tests (Throughput messen)

### Phase 3: Prioritization
- [ ] **3.1** Priority Queues konfigurieren
- [ ] **3.2** Rate Limiting aktivieren
- [ ] **3.3** Priority Upload Endpoint erstellen
- [ ] **3.4** Priority-Tests durchführen

### Phase 4: Monitoring
- [ ] **4.1** Celery Status Endpoints implementieren
- [ ] **4.2** Health Check erweitern
- [ ] **4.3** Flower Dashboard konfigurieren
- [ ] **4.4** Logging & Metrics erweitern

---

## Testing Plan

### Test 1: Backend Responsiveness
```bash
# Terminal 1: Start Backend
python backend.py

# Terminal 2: Start Celery Workers
./scripts/start_celery_workers.sh

# Terminal 3: Upload 1000 Dateien
curl -X POST http://127.0.0.1:45678/upload/directory \
  -F "directory_path=C:\VCC\test_documents" \
  -F "chunk_size=50"

# Terminal 4: Health Check während Upload
while true; do
  curl http://127.0.0.1:45678/health
  sleep 1
done
```

**Erwartung:** `/health` antwortet IMMER innerhalb 500ms

### Test 2: Throughput Messung
```python
# Vorher (synchron):
# - 100 Dateien in ~200s = 0.5 Dateien/s
# - Backend blockiert während Processing

# Nachher (Celery):
# - 100 Dateien in ~20s = 5 Dateien/s (10x schneller)
# - Backend antwortet sofort
```

### Test 3: Worker Failure Handling
```bash
# Stoppe 1 Worker während Processing
kill <worker_pid>

# Erwartung: Tasks werden automatisch auf andere Worker verteilt
```

---

## Rollback Plan

### Wenn Celery-Migration fehlschlägt:

1. **Code Rollback:**
   ```bash
   git checkout backend.py
   ```

2. **Alte BackgroundTasks wiederherstellen:**
   ```python
   # backend.py - Fallback Code
   if CELERY_AVAILABLE:
       # Neue Celery Implementation
   else:
       # Alte BackgroundTasks (Fallback)
       background_tasks.add_task(process_documents_background, ...)
   ```

3. **Dependencies entfernen:**
   ```bash
   pip uninstall celery redis flower
   ```

---

## Performance-Ziele

### Vor Migration (Ist-Zustand):
- **API Response Time:** ❌ Timeout während Ingestion (>30s)
- **Throughput:** 0.5 Dateien/s (single-threaded)
- **Concurrency:** 1 Job gleichzeitig
- **Backend Availability:** ❌ Blockiert während Processing

### Nach Migration (Soll-Zustand):
- **API Response Time:** ✅ <100ms (immer)
- **Throughput:** 5-10 Dateien/s (multi-worker)
- **Concurrency:** 14+ parallel Jobs
- **Backend Availability:** ✅ 100% (auch während Ingestion)

---

## Redis Setup (Falls noch nicht vorhanden)

**Docker Compose:**
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  redis_data:
```

**Start:**
```bash
docker-compose up -d redis
```

**Test:**
```bash
redis-cli -h 192.168.178.94 ping
# Erwartung: PONG
```

---

## Nächste Schritte (Priorisiert)

1. ✅ **JETZT:** Dokumentation erstellen (dieser TODO)
2. ⏰ **Heute:** Redis Setup testen
3. ⏰ **Heute:** Phase 1 Celery Setup (Items 1.1-1.5)
4. ⏰ **Morgen:** Phase 1 Testing & Deployment (Items 1.6-1.10)
5. 📅 **Später:** Phase 2-4 (Performance-Optimierung)

---

## Lessons Learned

### Was haben wir gelernt?

1. **FastAPI BackgroundTasks sind NICHT für lange Tasks geeignet**
   - Laufen im gleichen Event Loop
   - Blockieren andere Requests
   - Keine Skalierung auf mehrere Worker

2. **asyncio.gather() alleine reicht nicht**
   - Nur für I/O-bound Tasks effektiv
   - CPU-bound Tasks brauchen ProcessPoolExecutor
   - Database Operations brauchen Connection Pooling

3. **Job Queues sind essentiell für Production**
   - Entkopplung von API und Processing
   - Retry-Logic und Fehlerbehandlung
   - Monitoring und Observability

---

**Erstellt:** 11. Oktober 2025  
**Autor:** Covina Development Team  
**Status:** 🔴 Ready for Implementation
