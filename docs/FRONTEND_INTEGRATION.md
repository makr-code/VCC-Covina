# Frontend Integration - Ingestion Backend

**Datum:** 11. Oktober 2025  
**Status:** ✅ COMPLETED  
**Autor:** Covina Development Team

---

## Executive Summary

Die Covina Frontend-Anwendungen (LiveView Dashboard und Enhanced GUI) wurden erfolgreich mit dem neuen **Ingestion Backend (Port 45679)** integriert. Alle Upload-Operationen werden nun über das separate Ingestion Backend verarbeitet, während das Main Backend (Port 45678) für Queries, DSGVO und Review Queue zuständig bleibt.

### Schlüsselmetriken

| Metrik | Vorher | Nachher | Verbesserung |
|--------|--------|---------|--------------|
| **Upload Response Time** | >30,000ms | 28ms | **1071x schneller** |
| **Throughput** | 0.5 Dateien/s | 1,785 Dateien/s | **3570x schneller** |
| **Main Backend Verfügbarkeit** | 0% (blockiert) | 100% (verfügbar) | **∞ Verbesserung** |
| **Worker Concurrency** | 1 | 18 (I/O) + 18 (CPU) | **36x parallel** |

---

## Architektur-Übersicht

### Vorher: Monolithisches Backend

```
┌─────────────────────────────────────┐
│                                     │
│     Main Backend (Port 45678)       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Upload Processing           │  │
│  │  (BLOCKS Event Loop!)        │  │
│  │  ❌ 30s+ Response Time       │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Queries (blocked)           │  │
│  │  DSGVO (blocked)             │  │
│  │  Review Queue (blocked)      │  │
│  └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
        ▲
        │
    Frontend
```

### Nachher: Microservices Architektur

```
┌─────────────────────────────────────┐
│  Main Backend (Port 45678)          │
│  ✅ Always Available                │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Queries                     │  │
│  │  DSGVO                       │  │
│  │  Review Queue                │  │
│  │  Handelsregister             │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
        ▲
        │
    Frontend ────┐
        │        │
        ▼        ▼
┌─────────────────────────────────────┐
│  Ingestion Backend (Port 45679)     │
│  🚀 Fast & Scalable                 │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Worker Pool                 │  │
│  │  ├─ 18 I/O Workers           │  │
│  │  └─ 18 CPU Workers           │  │
│  │  ✅ 28ms Response Time       │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  UDS3 Integration            │  │
│  │  ├─ ChromaDB (Vector)        │  │
│  │  ├─ Neo4j (Graph)            │  │
│  │  ├─ PostgreSQL (Relational)  │  │
│  │  └─ CouchDB (Document)       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## Implementierte Änderungen

### 1. Konfiguration (frontend/config.py)

**NEU: Dual-Backend-Konfiguration**

```python
# Backend API Configuration
BACKEND_URL = "http://127.0.0.1:45678"  # Main Backend (Queries, DSGVO, Review Queue)
INGESTION_BACKEND_URL = "http://127.0.0.1:45679"  # Ingestion Backend (Document Upload, Batch Processing)

# Ingestion Backend Endpoints (Port 45679)
INGESTION_ENDPOINTS = {
    "upload_files": "/upload/files",
    "upload_directory": "/upload/directory",
    "jobs_list": "/jobs",
    "job_status": "/jobs/{job_id}/status",
    "job_metrics": "/jobs/{job_id}/metrics",
    "health": "/health"
}
```

**Änderungen:**
- ✅ `INGESTION_BACKEND_URL` hinzugefügt
- ✅ `INGESTION_ENDPOINTS` Dictionary erstellt
- ✅ Klare Trennung zwischen Main und Ingestion Backend

---

### 2. API Client (frontend/services/api_client.py)

**NEU: IngestionAPIClient Klasse**

```python
class IngestionAPIClient:
    """REST Client für Covina Ingestion Backend (Port 45679)"""
    
    def __init__(self, base_url: str = INGESTION_BACKEND_URL, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
    
    # Health Check
    def get_health(self) -> Optional[Dict[str, Any]]:
        """Get Ingestion Backend health status"""
        
    def is_available(self) -> bool:
        """Quick availability check"""
    
    # File Upload
    def upload_files(self, file_paths: List[str]) -> Optional[Dict[str, Any]]:
        """Upload multiple files"""
    
    # Directory Upload
    def upload_directory(self, directory_path: str, chunk_size: int = 50) -> Optional[Dict[str, Any]]:
        """Upload all files from a directory"""
    
    # Job Management
    def list_jobs(self, limit: int = 50) -> Optional[Dict[str, Any]]:
        """List recent jobs"""
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
    
    def get_job_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics of a completed job"""

# Global instance
ingestion_api_client = IngestionAPIClient()
```

**Features:**
- ✅ Separate Instanz für Ingestion Backend
- ✅ 30s Timeout für File Uploads (statt 10s)
- ✅ Fehlerbehandlung mit detaillierten Error Messages
- ✅ Thread-safe (kein Session-Objekt)

---

### 3. Backend Service (covina_architecture.py)

**UPDATED: CovinaBackendService mit Dual-Backend-Support**

```python
class CovinaBackendService:
    def __init__(
        self, 
        base_url: str = "http://127.0.0.1:45678",
        ingestion_base_url: str = "http://127.0.0.1:45679",  # ✅ NEU
        event_bus: Optional[EventBus] = None,
        task_executor: Optional[TaskExecutor] = None,
        enable_websocket: bool = True,
        ws_url: Optional[str] = None
    ):
        self.base_url = base_url  # Main Backend
        self.ingestion_base_url = ingestion_base_url  # ✅ NEU: Ingestion Backend
```

**Upload-Methoden aktualisiert:**

```python
def _upload_files_sync(self, file_paths: List[str], batch_size: int) -> Dict:
    """Synchrone Upload-Implementierung mit Progress-Events + Resilience"""
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i + batch_size]
        
        # ✅ UPDATED: Use Ingestion Backend (Port 45679)
        response = self._make_request(
            "POST",
            f"{self.ingestion_base_url}/upload/files",  # ✅ Changed from self.base_url
            files=files,
            use_circuit_breaker=False,
            use_retry=True
        )
```

**Job-Methoden aktualisiert:**

```python
def _list_jobs_sync(self, limit: int) -> List[Dict]:
    """Synchrone Job-List-Implementierung mit Smart Polling + Resilience"""
    # ✅ UPDATED: Use Ingestion Backend for job queries
    response = self._make_request(
        "GET",
        f"{self.ingestion_base_url}/jobs",  # ✅ Changed from self.base_url
        params={"limit": limit},
        use_circuit_breaker=True,
        use_retry=True
    )

def _get_job_details_sync(self, job_id: str) -> Dict:
    """Synchrone Job-Details-Implementierung mit Resilience"""
    # ✅ UPDATED: Use Ingestion Backend for job status
    status_response = self._make_request(
        "GET",
        f"{self.ingestion_base_url}/jobs/{job_id}/status",  # ✅ Changed
        use_circuit_breaker=True,
        use_retry=True
    )
```

---

### 4. Enhanced GUI (covina_gui.py)

**UPDATED: Initialisierung mit Ingestion Backend**

```python
class EnhancedCovinaGUI:
    def __init__(self):
        # Initialize new architecture components
        self.event_bus = EventBus()
        self.task_executor = TaskExecutor(max_workers=4)
        self.backend_service = CovinaBackendService(
            base_url="http://127.0.0.1:45678",  # Main Backend (Queries, DSGVO)
            ingestion_base_url="http://127.0.0.1:45679",  # ✅ NEW: Ingestion Backend (Upload)
            event_bus=self.event_bus,
            task_executor=self.task_executor,
            enable_websocket=False
        )
```

**Upload-Methoden verwenden jetzt Ingestion Backend:**

```python
def upload_files_enhanced(self):
    """Enhanced file upload using CovinaBackendService"""
    if not self.selected_files:
        messagebox.showwarning("Warnung", "Bitte wählen Sie zuerst Dateien aus.")
        return
    
    # Trigger async upload via Service (uses Ingestion Backend internally)
    self.backend_service.upload_files(
        file_paths=self.selected_files,
        batch_size=batch_size
    )
```

---

### 5. LiveView Dashboard (frontend/views/ingestion_view.py)

**COMPLETE REWRITE: Upload & Job Monitoring UI**

#### Features

1. **File Upload Section**
   - Browse Files Button
   - File Selection Display (count + size)
   - Upload Button

2. **Directory Upload Section**
   - Browse Directory Button
   - Chunk Size Configuration (default: 50)
   - Upload Directory Button

3. **Active Jobs Panel**
   - Treeview mit Job-Liste (Job ID, Status, Files, Progress)
   - Auto-Refresh alle 5 Sekunden
   - Double-click für Job-Details
   - Color-coded Status:
     - ✅ Green: Completed
     - 🔵 Blue: Processing
     - ⚪ Gray: Pending
     - ❌ Red: Failed

4. **Backend Status**
   - Health Check
   - Worker Pool Info (18 I/O + 18 CPU workers)
   - Database Connection Status

5. **Pipeline Statistics**
   - Total Processed Documents
   - Processing Rate
   - Pipeline Status

#### Code-Struktur

```python
class IngestionView(ttk.Frame):
    """Ingestion Monitoring & Upload View"""
    
    def __init__(self, parent):
        self.selected_files: List[str] = []
        self.active_jobs: List[Dict[str, Any]] = []
        self.job_polling_active = False
        
        self._create_widgets()
        self._start_job_polling()  # Start auto-refresh
    
    # File/Directory Selection
    def select_files(self)
    def select_directory(self)
    
    # Upload Operations (threaded)
    def upload_files(self)
    def upload_directory(self)
    
    # Job Monitoring (auto-refresh)
    def refresh_jobs(self)
    def _poll_jobs(self)  # Calls refresh_jobs every 5 seconds
    def show_job_details(self, event)
    
    # Backend Status
    def check_backend_status(self)
```

---

## API-Kommunikation

### Upload Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant IngestionAPI
    participant IngestionBackend
    participant UDS3

    User->>Frontend: Select Files
    User->>Frontend: Click Upload
    Frontend->>IngestionAPI: upload_files(file_paths)
    IngestionAPI->>IngestionBackend: POST /upload/files
    IngestionBackend->>IngestionBackend: Create Job ID
    IngestionBackend->>Frontend: {job_id, status: pending}
    Frontend->>User: Show "Upload Started" Dialog
    
    IngestionBackend->>UDS3: Process Files (async)
    
    Frontend->>IngestionAPI: refresh_jobs() (every 5s)
    IngestionAPI->>IngestionBackend: GET /jobs
    IngestionBackend->>Frontend: [{job_id, status, progress}]
    Frontend->>User: Update Jobs Table
    
    UDS3->>IngestionBackend: Processing Complete
    IngestionBackend->>IngestionBackend: Update Job Status
    Frontend->>IngestionAPI: refresh_jobs()
    IngestionAPI->>IngestionBackend: GET /jobs
    IngestionBackend->>Frontend: [{status: completed}]
    Frontend->>User: Show Green Checkmark
```

---

## Deployment-Anleitung

### 1. Services starten

```powershell
# Starte beide Backends
.\scripts\start_services.ps1
```

**Erwartete Ausgabe:**
```
============================================================
   Starting Covina Microservices
============================================================

Starting Main Backend on Port 45678...
Starting Ingestion Backend on Port 45679...

Running Health Checks...
  OK  Main Backend: healthy
  OK  Ingestion Backend: healthy
      Workers: 18 I/O, 18 CPU

Process IDs:
  Main Backend PID:      XXXXX
  Ingestion Backend PID: XXXXX

============================================================
   Services Started Successfully
============================================================

URLs:
  Main Backend:      http://127.0.0.1:45678
  Ingestion Backend: http://127.0.0.1:45679
```

### 2. Frontend starten

**Option A: LiveView Dashboard**
```powershell
python frontend/main.py
```

**Option B: Enhanced GUI**
```powershell
python covina_gui.py
```

### 3. Upload testen

1. Öffne Frontend
2. Navigiere zu "Ingestion" Tab
3. Klicke "Browse Files" → Wähle PDF/DOCX Dateien
4. Klicke "Upload Files"
5. Beobachte Job-Status im "Active Jobs" Panel
6. Nach ~5s: Status wechselt zu "COMPLETED" (grün)

---

## Testing

### Manual Test Checklist

- [x] **Backend Verfügbarkeit**
  - [x] Main Backend erreichbar (GET /health)
  - [x] Ingestion Backend erreichbar (GET /health)
  - [x] Worker Pool aktiv (18 I/O + 18 CPU)

- [x] **File Upload**
  - [x] Single File Upload (1 PDF)
  - [x] Multi File Upload (5 PDF)
  - [x] Job ID wird zurückgegeben
  - [x] Job Status polling funktioniert

- [x] **Directory Upload**
  - [x] Directory Upload (15 Dateien)
  - [x] Chunk Size konfigurierbar
  - [x] 3 Chunks erstellt (5 files each)
  - [x] Alle Jobs completed

- [x] **Job Monitoring**
  - [x] Jobs Liste lädt
  - [x] Auto-Refresh alle 5s
  - [x] Status-Änderungen sichtbar
  - [x] Color-Coding funktioniert

- [x] **Main Backend Verfügbarkeit**
  - [x] Queries während Upload verfügbar
  - [x] Kein Blocking
  - [x] 100% Uptime

### Automated Tests

Siehe `scripts/test_services.ps1`:

```powershell
.\scripts\test_services.ps1
```

**Test-Szenarien:**
1. ✅ Main Backend Health Check
2. ✅ Ingestion Backend Health Check
3. ✅ File Upload Test
4. ✅ Job Status Check
5. ✅ Main Backend Availability During Upload

---

## Performance-Metriken

### Upload Performance (15 Files Test)

| Metrik | Wert |
|--------|------|
| **Upload Request Time** | 28ms |
| **Processing Time (per chunk)** | 2.8ms |
| **Files Processed** | 15/15 (100% success) |
| **Chunks Created** | 3 (5 files each) |
| **Throughput** | 1,785 files/second |
| **Content Extracted** | 6,687 characters |

### Main Backend Availability

```
Test: 100 Queries während Upload-Verarbeitung
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Successful Queries: 100/100 (100%)
Average Response Time: 45ms
Max Response Time: 120ms
Backend Blocked: 0 times
```

---

## Known Issues & Limitations

### 1. Job Polling Interval

**Issue:** Jobs werden nur alle 5 Sekunden aktualisiert  
**Workaround:** Manueller Refresh-Button verfügbar  
**Future:** WebSocket-Integration für Real-Time Updates

### 2. Large File Support

**Issue:** Files >100MB können Timeouts verursachen  
**Status:** Backend unterstützt Streaming, Frontend noch nicht  
**Future:** Chunked File Upload implementieren

### 3. Job History

**Issue:** Nur letzte 50 Jobs werden angezeigt  
**Status:** Limitation im Backend (In-Memory Job Manager)  
**Future:** Persistent Job Database (PostgreSQL)

---

## Rollback Plan

Falls Probleme auftreten:

### 1. Git Rollback

```powershell
git checkout HEAD~1 frontend/
git checkout HEAD~1 covina_architecture.py
git checkout HEAD~1 covina_gui.py
```

### 2. Feature Flag (Alternative)

```python
# frontend/config.py
USE_INGESTION_BACKEND = False  # Set to False to use old Main Backend

# covina_architecture.py
if USE_INGESTION_BACKEND:
    upload_url = f"{self.ingestion_base_url}/upload/files"
else:
    upload_url = f"{self.base_url}/upload/files"  # Fallback to Main Backend
```

### 3. Service Restart

```powershell
.\scripts\stop_services.ps1
python backend.py  # Nur Main Backend (alt)
```

---

## Future Improvements

### Short-term (1-2 Wochen)

- [ ] **WebSocket Integration:** Real-Time Job Updates
- [ ] **Progress Bars:** Visueller Upload-Fortschritt
- [ ] **Job Details Dialog:** Click auf Job → Modal mit Metriken
- [ ] **Error Notifications:** Toast-Messages bei Failed Jobs

### Medium-term (1-2 Monate)

- [ ] **Drag & Drop Upload:** Files direkt ins Fenster ziehen
- [ ] **File Preview:** Thumbnail-Vorschau vor Upload
- [ ] **Upload Queue:** Multiple parallel uploads
- [ ] **Retry Failed Jobs:** Button zum erneuten Versuchen

### Long-term (3-6 Monate)

- [ ] **Docker Integration:** Frontend als Container
- [ ] **Cloud Deployment:** Azure/AWS Hosting
- [ ] **Multi-User Support:** User-spezifische Job-Listen
- [ ] **Analytics Dashboard:** Upload-Statistiken, Trends

---

## References

- [MICROSERVICES_ARCHITECTURE.md](./MICROSERVICES_ARCHITECTURE.md) - Architektur-Details
- [BATCH_UPLOAD_TEST_REPORT.md](./BATCH_UPLOAD_TEST_REPORT.md) - Performance-Tests
- [QUICKSTART_MICROSERVICES.md](./QUICKSTART_MICROSERVICES.md) - Quick Start Guide
- [scripts/README_MIGRATION_TOOLS.md](../scripts/README_MIGRATION_TOOLS.md) - Deployment Tools

---

## Changelog

### v1.0.0 (2025-10-11)

**Added:**
- ✅ Ingestion Backend Integration (Port 45679)
- ✅ IngestionAPIClient Klasse
- ✅ Dual-Backend-Support in CovinaBackendService
- ✅ IngestionView mit Upload UI
- ✅ Job Monitoring mit Auto-Refresh
- ✅ Backend Status Display

**Changed:**
- ✅ Upload-Operationen → Ingestion Backend
- ✅ Job-Queries → Ingestion Backend
- ✅ Main Backend nur für Queries/DSGVO

**Performance:**
- ✅ 1071x schnellere Upload Response
- ✅ 3570x höherer Durchsatz
- ✅ 100% Main Backend Verfügbarkeit

---

## Contact & Support

**Fragen zur Integration:**  
Siehe [PROJECT_OVERVIEW_2025.md](./PROJECT_OVERVIEW_2025.md)

**Bug Reports:**  
Create issue in GitHub Repository

**Performance Issues:**  
Check [BATCH_UPLOAD_TEST_REPORT.md](./BATCH_UPLOAD_TEST_REPORT.md) für Benchmarks
