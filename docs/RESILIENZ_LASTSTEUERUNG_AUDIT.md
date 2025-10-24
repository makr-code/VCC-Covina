# Resilienz & Laststeuerung Audit Report
**Datum:** 21. Oktober 2025  
**System:** Covina Document Management (Main + Ingestion Backend)  
**Auditor:** GitHub Copilot  
**Status:** 🟡 TEILWEISE IMPLEMENTIERT

---

## Executive Summary

**Zweck:** Bewertung der Resilienz-Mechanismen (Backpressure, Rate Limiting, Circuit Breaker, Graceful Shutdown, Retry, Idempotenz, De-Duplication).

**Bewertung:**
- ✅ **Retry-Policies:** Implementiert (Recovery-System, max 3 retries)
- ✅ **Idempotenz:** Teilweise (PostgreSQL ON CONFLICT, SAGA Idempotency Keys)
- ✅ **Graceful Shutdown:** Vorhanden (Executor shutdown, Pool disconnect)
- ⚠️ **De-Duplication:** Teilweise (Hash-based in Recovery, kein Upload-Dedupe)
- ❌ **Backpressure/Rate Limiting:** Nicht implementiert
- ❌ **Circuit Breaker:** Nicht vorhanden (DB-Ausfälle nicht abgefangen)
- ❌ **Bulkheads:** Nicht implementiert (keine DB-spezifische Isolation)

**Risiko-Einschätzung:** 🟡 MEDIUM-HIGH  
**Empfohlene Maßnahmen:** 3 Quick Wins (Rate Limiting, Circuit Breaker, Bulkheads)

---

## 1. Backpressure & Rate Limiting

### 1.1 Status

❌ **Rate Limiting:** Nicht implementiert
- Kein Per-IP Limiting
- Kein Per-Job Limiting
- Kein HTTP 429 (Too Many Requests)
- **Risiko:** DoS-Angriffe, Ressourcen-Erschöpfung

❌ **Backpressure:** Nicht implementiert
- Worker Pools haben keine Queue-Limits
- Kein Rejection bei Überlast
- **Risiko:** Memory-Exhaustion bei Spike-Traffic

### 1.2 Bedrohungsszenarien

**Szenario 1: IP-Flooding**
- Angreifer sendet 1000 req/s von einer IP
- Backend überlastet Worker Pools
- Legitime User blockiert

**Szenario 2: Job-Spam**
- User erstellt 100 Jobs in 1 Sekunde
- Temp-Verzeichnisse füllen Platte
- System-Crash

**Szenario 3: Große Dateien**
- Mehrere 2GB-Uploads gleichzeitig
- RAM-Exhaustion (trotz Streaming)
- Worker-Starvation

### 1.3 Empfohlene Implementierung

**QW-1: slowapi Rate Limiting (ingestion_backend.py)**

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/upload/files")
@limiter.limit("10/minute")  # Max 10 Uploads pro Minute pro IP
async def upload_files(...):
    # ... existing code ...
```

**QW-2: Job-Level Rate Limiting (Custom)**

```python
from collections import defaultdict
import time

class JobRateLimiter:
    def __init__(self, max_jobs_per_minute=20):
        self.max_jobs = max_jobs_per_minute
        self.jobs_per_user = defaultdict(list)  # user_id -> [timestamp, ...]
    
    def check_limit(self, user_id: str) -> bool:
        now = time.time()
        # Remove timestamps older than 1 minute
        self.jobs_per_user[user_id] = [
            ts for ts in self.jobs_per_user[user_id] 
            if now - ts < 60
        ]
        
        if len(self.jobs_per_user[user_id]) >= self.max_jobs:
            return False
        
        self.jobs_per_user[user_id].append(now)
        return True

# Usage
job_limiter = JobRateLimiter(max_jobs_per_minute=20)

@app.post("/upload/files")
async def upload_files(...):
    user_id = _principal.username if _principal else "anonymous"
    
    if not job_limiter.check_limit(user_id):
        raise HTTPException(
            status_code=429,
            detail="Too many jobs. Try again later.",
            headers={"Retry-After": "60"}
        )
    # ... existing code ...
```

**QW-3: Worker Pool Backpressure**

```python
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

class BoundedExecutor:
    def __init__(self, max_workers, queue_size):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.queue = Queue(maxsize=queue_size)
    
    def submit(self, fn, *args, **kwargs):
        if self.queue.full():
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable (queue full)",
                headers={"Retry-After": "30"}
            )
        
        future = self.executor.submit(fn, *args, **kwargs)
        self.queue.put(future)
        future.add_done_callback(lambda f: self.queue.get())
        return future

# Replace
io_executor = BoundedExecutor(max_workers=36, queue_size=200)
```

**Location:** `ingestion_backend.py`

---

## 2. Circuit Breaker / Bulkheads

### 2.1 Status

❌ **Circuit Breaker:** Nicht vorhanden
- DB-Ausfälle führen zu Exception-Flooding
- Keine automatische Fehlerisolation
- **Risiko:** Cascade Failures

❌ **Bulkheads:** Nicht implementiert
- Keine DB-spezifische Connection/Request-Isolation
- Ein DB-Ausfall kann gesamtes System blockieren
- **Risiko:** Single Point of Failure

### 2.2 Bedrohungsszenarien

**Szenario 1: ChromaDB Down**
- ChromaDB Server offline
- Jede Dokument-Verarbeitung versucht Connect
- Timeouts häufen sich → Worker Pool exhausted
- **Impact:** Kompletter Ingestion-Ausfall

**Szenario 2: Neo4j Slow**
- Neo4j antwortet mit 10s Latenz
- Graph-Operationen blockieren Worker
- Backlog wächst exponentiell
- **Impact:** Throughput-Kollaps

### 2.3 Empfohlene Implementierung

**QW-4: pybreaker Circuit Breaker**

```bash
pip install pybreaker
```

```python
from pybreaker import CircuitBreaker, CircuitBreakerError

# Separate Circuit Breakers pro DB
postgres_breaker = CircuitBreaker(
    fail_max=5,           # 5 Fehler
    timeout_duration=30,  # 30s Open
    name="PostgreSQL"
)

chromadb_breaker = CircuitBreaker(
    fail_max=3,
    timeout_duration=60,
    name="ChromaDB"
)

neo4j_breaker = CircuitBreaker(
    fail_max=5,
    timeout_duration=45,
    name="Neo4j"
)

couchdb_breaker = CircuitBreaker(
    fail_max=5,
    timeout_duration=30,
    name="CouchDB"
)

# Wrapper für DB-Operationen
@postgres_breaker
def insert_to_postgres(doc):
    return postgres_backend.insert_document(**doc)

@chromadb_breaker
def insert_to_chromadb(vectors):
    return chromadb_backend.add_vectors(vectors)

# Error Handling
try:
    insert_to_chromadb(vectors)
except CircuitBreakerError:
    logger.warning("[CIRCUIT] ChromaDB breaker OPEN - skipping vector insert")
    # Optional: Fallback oder Dead Letter Queue
```

**QW-5: Bulkhead Pattern (Connection Pools)**

```python
# Separate Connection Pools pro DB
postgres_pool = PostgreSQLConnectionPool(
    min_connections=5,
    max_connections=20,  # Limitiert auf 20
)

chromadb_pool = ChromaDBConnectionPool(
    max_connections=10  # Separate Limit
)

# Benefit: Neo4j-Ausfall blockiert nicht PostgreSQL-Pool
```

**Location:** `ingestion_backend.py`, `uds3/database/`

---

## 3. Graceful Shutdown

### 3.1 Status

✅ **Executor Shutdown:** Implementiert
- `io_executor.shutdown(wait=True)`
- `cpu_executor.shutdown(wait=True)`
- Location: `ingestion_backend.py` Line ~2533 (lifespan context)

✅ **PostgreSQL Pool Disconnect:** Implementiert
- `postgres_backend.disconnect()`
- Location: `main_backend.py` Line ~527 (shutdown_event)

⚠️ **In-Flight Job Draining:** Teilweise
- Jobs werden nicht aktiv gedrained
- Nur Executor-Tasks werden gewartet
- **Risiko:** Unvollständige Jobs bei Shutdown

❌ **Health Probe Readiness:** Nicht für Shutdown
- `/ready` ändert Status nicht vor Shutdown
- K8s könnte Traffic während Shutdown routen
- **Risiko:** 502 Bad Gateway für User

### 3.2 Empfohlene Verbesserung

**QW-6: Graceful Drain + Readiness Probe**

```python
# Global shutdown flag
shutdown_in_progress = False

@app.on_event("shutdown")
async def shutdown_event():
    global shutdown_in_progress
    shutdown_in_progress = True
    
    logger.info("[SHUTDOWN] Initiating graceful shutdown...")
    logger.info("[SHUTDOWN] Rejecting new uploads...")
    
    # Wait for in-flight jobs (max 2 minutes)
    max_wait = 120
    elapsed = 0
    
    while elapsed < max_wait:
        in_flight = io_executor._work_queue.qsize()
        if in_flight == 0:
            break
        
        logger.info(f"[SHUTDOWN] Waiting for {in_flight} jobs... ({elapsed}s)")
        await asyncio.sleep(5)
        elapsed += 5
    
    logger.info("[SHUTDOWN] Shutting down executors...")
    io_executor.shutdown(wait=True)
    cpu_executor.shutdown(wait=True)
    
    logger.info("[SHUTDOWN] Complete")

@app.get("/ready")
async def readiness_probe():
    if shutdown_in_progress:
        raise HTTPException(status_code=503, detail="Shutting down")
    return {"ready": True}

@app.post("/upload/files")
async def upload_files(...):
    if shutdown_in_progress:
        raise HTTPException(status_code=503, detail="Service shutting down")
    # ... existing code ...
```

---

## 4. Retry-Policies & Idempotenz

### 4.1 Status (Retry)

✅ **Recovery System:** Implementiert
- Max 3 Retries pro Failed File
- Exponential Backoff (PostgreSQL Insert)
- Deadlock Detection
- Location: `ingestion/job_persistence.py`, `uds3/database/database_api_postgresql_pooled.py`

✅ **SAGA Compensation:** Implementiert
- Auto-Retry bei Step-Failure
- Compensation on Rollback
- Location: `uds3/saga/`

⚠️ **Dead-Letter Queue:** Nicht implementiert
- Files nach 3 Retries → Blocked (recovery_blocked=1)
- Keine separate DLQ für manuelle Inspektion
- **Impact:** Hartnäckige Fehler schwer zu debuggen

### 4.2 Status (Idempotenz)

✅ **PostgreSQL ON CONFLICT:** Implementiert
```sql
INSERT INTO documents (...) 
ON CONFLICT (document_id) 
DO UPDATE SET ...
```
Location: `uds3/database/database_api_postgresql_pooled.py` Line ~250

✅ **SAGA Idempotency Keys:** Implementiert
- Unique SAGA IDs verhindern Duplikate
- Location: `uds3/saga/saga_orchestrator.py`

⚠️ **ChromaDB/Neo4j Idempotenz:** Teilweise
- ChromaDB: Keine explizite Idempotency (überschreibt)
- Neo4j: MERGE verwendet (idempotent)
- **Risiko:** ChromaDB Duplicate Vectors bei Retry

### 4.3 Empfohlene Verbesserung

**QW-7: Dead-Letter Queue**

```python
class DeadLetterQueue:
    def __init__(self, db_path="data/dlq.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dead_letters (
                id INTEGER PRIMARY KEY,
                job_id TEXT,
                file_path TEXT,
                error TEXT,
                retry_count INTEGER,
                created_at TEXT,
                payload TEXT
            )
        """)
    
    def add(self, job_id, file_path, error, retry_count, payload):
        self.conn.execute(
            "INSERT INTO dead_letters (job_id, file_path, error, retry_count, created_at, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, file_path, error, retry_count, datetime.now().isoformat(), json.dumps(payload))
        )
        self.conn.commit()

# Usage nach 3 failed retries
if retry_count >= 3:
    dlq.add(job_id, file_path, str(error), retry_count, {
        "classification": doc_class,
        "content_length": len(content)
    })
    logger.warning(f"[DLQ] Added {file_path} to Dead Letter Queue")
```

**QW-8: ChromaDB Idempotenz (Check-Before-Insert)**

```python
def add_vector_idempotent(collection, id, vector, metadata):
    # Check if exists
    try:
        existing = collection.get(ids=[id])
        if existing and existing['ids']:
            logger.debug(f"[IDEMPOTENT] Vector {id} already exists - skipping")
            return {"status": "exists"}
    except:
        pass
    
    # Insert
    collection.add(ids=[id], embeddings=[vector], metadatas=[metadata])
    return {"status": "inserted"}
```

---

## 5. De-Duplication

### 5.1 Status

⚠️ **File-Hash De-Duplication:** Teilweise
- Hash-based Erkennung in Recovery-System
- Nur für bereits verarbeitete Files
- Location: `ingestion/job_persistence.py`

❌ **Upload De-Duplication:** Nicht implementiert
- Gleiche Datei mehrfach hochladbar
- Kein Content-Hash-Check vor Processing
- **Risiko:** Redundante Speicherung, Verschwendung

❌ **Chunk De-Duplication:** Nicht vorhanden
- Große Files werden in Chunks aufgeteilt
- Keine Chunk-Hash-Deduplication
- **Risiko:** Speicher-Overhead bei ähnlichen Dokumenten

### 5.2 Bedrohungsszenarien

**Szenario 1: Duplicate Upload**
- User lädt "Vertrag.pdf" 5x hoch (Versehen)
- System verarbeitet 5x identischen Content
- ChromaDB/Neo4j haben 5x identische Einträge
- **Impact:** Storage-Waste, Query-Pollution

**Szenario 2: Large File Deduplication**
- 100 PDF-Rechnungen mit identischem Template
- Jede Rechnung hat 90% gleichen Content
- Alle Chunks werden redundant gespeichert
- **Impact:** 10x Storage-Overhead

### 5.3 Empfohlene Implementierung

**QW-9: Content-Hash Upload Deduplication**

```python
import hashlib

def compute_file_hash(file_path: str) -> str:
    """SHA256 Hash des Dateiinhalts"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

# Deduplication Table
CREATE TABLE file_hashes (
    hash TEXT PRIMARY KEY,
    document_id TEXT,
    file_path TEXT,
    uploaded_at TEXT
);

# Check vor Processing
@app.post("/upload/files")
async def upload_files(...):
    for file in files:
        file_hash = compute_file_hash(file_path)
        
        # Check if hash exists
        existing = postgres_backend.execute(
            "SELECT document_id FROM file_hashes WHERE hash = %s",
            (file_hash,)
        )
        
        if existing:
            logger.info(f"[DEDUPE] File {file.filename} already processed (hash: {file_hash[:8]})")
            # Return existing document_id statt neu zu verarbeiten
            continue
        
        # Process + Store hash
        document_id = process_document(file_path)
        postgres_backend.execute(
            "INSERT INTO file_hashes (hash, document_id, file_path, uploaded_at) VALUES (%s, %s, %s, %s)",
            (file_hash, document_id, file_path, datetime.now().isoformat())
        )
```

**QW-10: Chunk Deduplication (Advanced)**

```python
def deduplicate_chunks(chunks: List[str]) -> List[str]:
    """Remove duplicate chunks basierend auf Hash"""
    seen = set()
    unique_chunks = []
    
    for chunk in chunks:
        chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
        if chunk_hash not in seen:
            seen.add(chunk_hash)
            unique_chunks.append(chunk)
    
    dedup_rate = (len(chunks) - len(unique_chunks)) / len(chunks) * 100
    logger.info(f"[DEDUPE] Removed {dedup_rate:.1f}% duplicate chunks")
    
    return unique_chunks
```

---

## 6. Compliance-Checkliste

| Anforderung | Status | Priorität | Aufwand |
|-------------|--------|-----------|---------|
| Rate Limiting (Per-IP) | ❌ | P0 | 4h |
| Rate Limiting (Per-Job) | ❌ | P1 | 2h |
| Circuit Breaker (4 DBs) | ❌ | P1 | 1d |
| Bulkheads (Connection Pools) | ⚠️ | P2 | 1d |
| Graceful Shutdown (Drain) | ⚠️ | P1 | 4h |
| Readiness Probe (Shutdown) | ❌ | P2 | 1h |
| Dead-Letter Queue | ❌ | P2 | 4h |
| ChromaDB Idempotenz | ⚠️ | P2 | 2h |
| Upload De-Duplication | ❌ | P1 | 1d |
| Chunk De-Duplication | ❌ | P3 | 2d |

---

## 7. Quick Wins (Priorisiert)

### Top 5 Quick Wins (1-2 Tage):

1. **Rate Limiting (IP)** (4h, P0, DoS-Schutz)
2. **Circuit Breaker (4 DBs)** (1d, P1, Cascade Failure Prevention)
3. **Upload De-Duplication** (1d, P1, Storage Efficiency)
4. **Graceful Shutdown Drain** (4h, P1, Zero-Downtime Deploys)
5. **Dead-Letter Queue** (4h, P2, Debugging)

### Mittelfristig (1 Woche):

6. **Bulkheads (Connection Pools)** (1d, P2)
7. **ChromaDB Idempotenz** (2h, P2)
8. **Rate Limiting (Job)** (2h, P1)

### Langfristig (1 Monat):

9. **Chunk De-Duplication** (2d, P3, Advanced)
10. **Backpressure (Worker Queue Limits)** (1d, P2)

---

## 8. Risiko-Bewertung

| Risiko | Wahrscheinlichkeit | Impact | Gesamt | Maßnahme |
|--------|-------------------|--------|--------|----------|
| DoS via Flooding | HOCH | HOCH | 🔴 KRITISCH | QW-1 (4h) |
| Cascade Failure (DB Down) | MITTEL | HOCH | 🟡 HIGH | QW-4 (1d) |
| Duplicate Storage Waste | MITTEL | MITTEL | 🟡 MEDIUM | QW-9 (1d) |
| Unclean Shutdown (Data Loss) | NIEDRIG | HOCH | 🟡 MEDIUM | QW-6 (4h) |
| Hartnäckige Fehler unsichtbar | NIEDRIG | MITTEL | 🟢 LOW | QW-7 (4h) |

---

## 9. Zusammenfassung

**Status:** 🟡 TEILWEISE IMPLEMENTIERT (40% Coverage)

**Stärken:**
- ✅ Retry-Policies (Recovery + SAGA)
- ✅ Idempotenz (PostgreSQL ON CONFLICT)
- ✅ Graceful Shutdown (Executor)

**Schwächen:**
- ❌ Kein Rate Limiting (DoS-Risiko)
- ❌ Kein Circuit Breaker (Cascade Failures)
- ❌ Keine Upload-Deduplication (Storage-Waste)

**Empfehlung:** 5 Quick Wins (2 Tage) umsetzen für Production-Readiness.

**Nächster Audit:** Nach Circuit Breaker + Rate Limiting (in 1 Woche)

---

**Audit abgeschlossen:** 21. Oktober 2025  
**Nächste Review:** 28. Oktober 2025  
**Verantwortlich:** Backend Team
