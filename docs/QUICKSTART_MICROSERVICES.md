# Covina Microservices - Quick Start Guide

**Architektur:** 2 FastAPI Backends (Main + Ingestion)  
**Datum:** 11. Oktober 2025

## 🚀 Schnellstart

### 1. Services starten

```powershell
# Starte beide Backends parallel
.\scripts\start_services.ps1
```

**Output:**
```
🚀 Starting Covina Microservices...
============================================================
📡 Starting Main Backend (Port 45678)...
⚙️  Starting Ingestion Backend (Port 45679)...

🔍 Running Health Checks...
  ✅ Main Backend: healthy
  ✅ Ingestion Backend: healthy
     Workers: 18 I/O, 18 CPU

🎯 Covina Microservices Running:
   Main Backend:      http://127.0.0.1:45678
   Ingestion Backend: http://127.0.0.1:45679
```

### 2. Services testen

```powershell
# Teste alle Endpoints
.\scripts\test_services.ps1
```

### 3. Services stoppen

```powershell
# Stoppe beide Backends
.\scripts\stop_services.ps1
```

---

## 📡 Service-URLs

| Service | URL | Port | Beschreibung |
|---------|-----|------|--------------|
| **Main Backend** | http://127.0.0.1:45678 | 45678 | API Gateway, Queries, DSGVO, Review Queue |
| **Ingestion Backend** | http://127.0.0.1:45679 | 45679 | Document Upload & Processing |

---

## 🔌 API Endpoints

### Main Backend (45678)

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/health` | Health Check |
| GET | `/database/stats` | Datenbankstatistiken |
| POST | `/search` | Dokumentensuche |
| POST | `/query` | Query API |
| GET | `/api/review-tasks` | Review Queue |
| POST | `/handelsregister/extract` | Company Extraction |
| POST | `/process-mining/analyze` | Process Mining |

### Ingestion Backend (45679)

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/health` | Health Check + Worker Status |
| POST | `/upload/files` | Upload Dateien (Multi-File) |
| POST | `/upload/directory` | Upload Verzeichnis (Batch) |
| GET | `/jobs` | Liste aller Jobs |
| GET | `/jobs/{job_id}/status` | Job Status |
| GET | `/jobs/{job_id}/metrics` | Job Metriken |

---

## 📤 Upload-Beispiele

### Single File Upload

```powershell
# PowerShell
$file = Get-Item "test.pdf"
Invoke-RestMethod -Uri "http://127.0.0.1:45679/upload/files" `
    -Method Post -Form @{ files = $file }
```

```bash
# Bash/curl
curl -X POST http://127.0.0.1:45679/upload/files \
    -F "files=@test.pdf"
```

**Response:**
```json
{
  "message": "Upload erfolgreich. 1 Dateien werden verarbeitet.",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_count": 1,
  "estimated_processing_time": "2s"
}
```

### Multi-File Upload

```powershell
# PowerShell
$files = Get-ChildItem "*.pdf"
Invoke-RestMethod -Uri "http://127.0.0.1:45679/upload/files" `
    -Method Post -Form @{ files = $files }
```

```bash
# Bash/curl
curl -X POST http://127.0.0.1:45679/upload/files \
    -F "files=@file1.pdf" \
    -F "files=@file2.pdf" \
    -F "files=@file3.pdf"
```

### Directory Upload (Batch)

```powershell
# PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:45679/upload/directory" `
    -Method Post -Form @{ 
        directory_path = "C:\Documents\ToProcess"
        chunk_size = 50
    }
```

```bash
# Bash/curl
curl -X POST http://127.0.0.1:45679/upload/directory \
    -F "directory_path=/path/to/documents" \
    -F "chunk_size=50"
```

---

## 📊 Job Status Tracking

### Get Job Status

```powershell
# PowerShell
$jobId = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
Invoke-RestMethod -Uri "http://127.0.0.1:45679/jobs/$jobId/status"
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "created_at": "2025-10-11T14:30:00",
  "updated_at": "2025-10-11T14:30:15",
  "file_count": 10,
  "processed_files": 7,
  "error_message": null
}
```

### Get Job Metrics (after completion)

```powershell
# PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:45679/jobs/$jobId/metrics"
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "total_files": 10,
  "successful_files": 9,
  "failed_files": 1,
  "processing_time": 18.5,
  "content_extracted_chars": 125430,
  "ai_entities_found": 42,
  "metadata_completeness": 0.85,
  "classification_stats": {
    "DOCUMENT": 7,
    "CONTRACT": 2,
    "ERROR": 1
  },
  "backend_metrics": {}
}
```

---

## 🔍 Health Monitoring

### Main Backend Health

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:45678/health"
```

### Ingestion Backend Health

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:45679/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-11T14:30:00",
  "components": {
    "uds3": "✅ ready",
    "vector_db": "✅",
    "graph_db": "✅",
    "relational_db": "✅",
    "document_db": "✅"
  },
  "worker_pool": {
    "io_workers": 18,
    "cpu_workers": 18,
    "total_cpus": 20
  }
}
```

---

## 🐛 Troubleshooting

### Service startet nicht

**Problem:** Port bereits in Verwendung

```powershell
# Prüfe welcher Prozess Port 45678/45679 verwendet
netstat -ano | findstr :45678
netstat -ano | findstr :45679

# Stoppe Prozess
Stop-Process -Id <PID> -Force
```

### Backend nicht erreichbar

**1. Prüfe ob Prozess läuft:**
```powershell
Get-Process -Name python | Where-Object { 
    $_.CommandLine -like "*backend.py*" -or 
    $_.CommandLine -like "*ingestion_backend.py*" 
}
```

**2. Prüfe Logs:**
```powershell
Get-Content logs\main_backend.log -Tail 50
Get-Content logs\ingestion_backend.log -Tail 50
```

**3. Health Check:**
```powershell
curl http://127.0.0.1:45678/health
curl http://127.0.0.1:45679/health
```

### Upload schlägt fehl

**Problem:** Datei zu groß

**Lösung:** Erhöhe Upload-Limit in `ingestion_backend.py`:

```python
app = FastAPI(
    title="Covina Ingestion Backend",
    # ...
)

# Erhöhe Upload-Limit
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_request_size=100 * 1024 * 1024  # 100 MB
)
```

### Performance-Probleme

**Problem:** Langsame Verarbeitung

**1. Prüfe Worker-Auslastung:**
```powershell
# CPU-Auslastung
Get-Counter '\Processor(_Total)\% Processor Time'

# Memory-Auslastung
Get-Process -Name python | Select-Object WorkingSet64
```

**2. Erhöhe Worker-Count:**

Editiere `ingestion_backend.py`:
```python
# Standardmäßig: CPU_COUNT - 2
OPTIMAL_WORKERS = max(1, CPU_COUNT - 2)

# Für mehr Performance:
OPTIMAL_WORKERS = CPU_COUNT  # Alle CPUs nutzen
```

**3. Reduziere Chunk-Size:**
```powershell
# Kleinere Chunks = schnellere Rückmeldung
curl -X POST http://127.0.0.1:45679/upload/directory \
    -F "directory_path=/path" \
    -F "chunk_size=25"  # Statt 50
```

---

## 📝 Logs

### Log-Dateien

| Datei | Beschreibung |
|-------|--------------|
| `logs/main_backend.log` | Main Backend Logs |
| `logs/main_backend_error.log` | Main Backend Fehler |
| `logs/ingestion_backend.log` | Ingestion Backend Logs |
| `logs/ingestion_backend_error.log` | Ingestion Backend Fehler |

### Log-Level anpassen

**Ingestion Backend:**
```python
# ingestion_backend.py
logging.basicConfig(
    level=logging.DEBUG,  # Ändere zu DEBUG für mehr Details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Echtzeit-Logs ansehen

```powershell
# PowerShell - Tail Logs
Get-Content logs\ingestion_backend.log -Wait -Tail 20
```

```bash
# Bash
tail -f logs/ingestion_backend.log
```

---

## 🔧 Konfiguration

### Ports anpassen

**Main Backend:**
```powershell
python backend.py --port 8000
```

**Ingestion Backend:**
```powershell
python ingestion_backend.py --port 8001
```

### Worker-Count anpassen

**Editiere `ingestion_backend.py`:**
```python
# Line ~100
OPTIMAL_WORKERS = 10  # Fixe Anzahl statt dynamisch
```

### Datenbank-URLs

**Editiere `ingestion_backend.py` (Lines 180-250):**
```python
# PostgreSQL
pg_config = {
    'host': '192.168.178.94',  # Ändere Host
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'postgres',
}

# ChromaDB
chromadb_config = {
    "remote": {
        "host": "192.168.178.94",  # Ändere Host
        "port": 8000,
    }
}

# Neo4j
relations_core = UDS3RelationsCore(
    neo4j_uri="neo4j://192.168.178.94:7687",  # Ändere URI
    neo4j_auth=("neo4j", "password")
)
```

---

## 🚀 Production Deployment

### Docker

**Build Image:**
```bash
docker build -f Dockerfile.ingestion -t covina/ingestion-backend .
```

**Run Container:**
```bash
docker run -p 45679:45679 \
    -e UDS3_WORKERS=18 \
    covina/ingestion-backend
```

### Kubernetes

**Deploy:**
```bash
kubectl apply -f k8s/ingestion-deployment.yaml
```

**Scale:**
```bash
kubectl scale deployment covina-ingestion --replicas=3
```

---

## 📚 Weitere Dokumentation

- **Architektur:** `docs/MICROSERVICES_ARCHITECTURE.md`
- **API Docs:** http://127.0.0.1:45679/docs (FastAPI Swagger UI)
- **Redoc:** http://127.0.0.1:45679/redoc

---

**Erstellt:** 11. Oktober 2025  
**Version:** 1.0.0  
**Support:** Covina Development Team
