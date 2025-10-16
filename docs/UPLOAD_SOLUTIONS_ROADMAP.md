# Upload Solutions Roadmap - Multi-Method Implementation

**Erstellt:** 15. Oktober 2025, 19:30 Uhr  
**Projekt:** Covina Document Management System  
**Ziel:** 4 parallele Upload-Methoden + umfassende Performance-Tests

---

## 🎯 Projekt-Übersicht

### Ziele

1. **4 unabhängige Upload-Lösungen** (parallel, austauschbar)
2. **Hybrid-Manager** (automatische Methoden-Selektion)
3. **Umfassende Testreihe** (Performance-Vergleich)
4. **Produktions-Deployment** (beste Methode(n) aktivieren)

### Scope

- **Lösung 1:** Chunked HTTP Upload (Resume-fähig)
- **Lösung 2:** WebSocket Streaming (Echtzeit-Bidirektional)
- **Lösung 3:** SMB Network Share mit File Watcher (Drag & Drop)
- **Lösung 4:** Hybrid Upload Manager (Auto-Selection)

---

## 📋 Implementation Roadmap

### Phase 1: Chunked HTTP Upload (2-3 Tage)

**Dateien:**
- `ingestion/upload_chunked.py` - Chunked Upload Handler (400+ Zeilen)
- `tests/test_chunked_upload.py` - Unit Tests (200+ Zeilen)
- `scripts/client_chunked_upload.py` - Client Script (300+ Zeilen)
- `scripts/client_chunked_upload.ps1` - PowerShell Client (200+ Zeilen)

**Features:**
- ✅ Multi-part chunked upload (5 MB chunks)
- ✅ Resume capability (MD5 chunk verification)
- ✅ Progress tracking per file
- ✅ Parallel chunk uploads (configurable)
- ✅ Automatic retry on network errors
- ✅ Session management (24h timeout)

**Endpoints:**
```
POST   /upload/chunked/start          - Initialize upload session
POST   /upload/chunked/{id}/chunk/{n} - Upload single chunk
GET    /upload/chunked/{id}/status    - Get upload progress
POST   /upload/chunked/{id}/finalize  - Finalize upload
DELETE /upload/chunked/{id}           - Cancel upload
```

**Database Schema:**
```sql
CREATE TABLE chunked_uploads (
    upload_id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    chunks_received INTEGER DEFAULT 0,
    chunk_size INTEGER DEFAULT 5242880,  -- 5 MB
    status TEXT DEFAULT 'uploading',     -- uploading, finalizing, completed, failed
    created_at TEXT,
    last_activity_at TEXT,
    job_id TEXT,  -- Created after finalization
    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
);

CREATE TABLE upload_chunks (
    upload_id TEXT,
    chunk_index INTEGER,
    chunk_md5 TEXT,
    received_at TEXT,
    PRIMARY KEY(upload_id, chunk_index),
    FOREIGN KEY(upload_id) REFERENCES chunked_uploads(upload_id) ON DELETE CASCADE
);
```

**Client Usage:**
```python
# Python Client
from client_chunked_upload import ChunkedUploader

uploader = ChunkedUploader("http://127.0.0.1:45679")
result = uploader.upload_file(
    "large_file.pdf",
    chunk_size=5*1024*1024,  # 5 MB
    parallel_chunks=3,
    on_progress=lambda p: print(f"Progress: {p:.1f}%")
)
print(f"Job ID: {result['job_id']}")
```

```powershell
# PowerShell Client
.\scripts\client_chunked_upload.ps1 `
    -FilePath "C:\data\large_file.pdf" `
    -BackendUrl "http://127.0.0.1:45679" `
    -ChunkSize 5MB `
    -ParallelChunks 3
```

---

### Phase 2: WebSocket Streaming (3-4 Tage)

**Dateien:**
- `ingestion/upload_websocket.py` - WebSocket Handler (500+ Zeilen)
- `tests/test_websocket_upload.py` - Unit Tests (250+ Zeilen)
- `scripts/client_websocket_upload.py` - Python Client (350+ Zeilen)

**Features:**
- ✅ Bidirectional real-time communication
- ✅ Binary streaming (no base64 encoding)
- ✅ Server-side pause/resume/cancel commands
- ✅ Multiple file uploads over single connection
- ✅ Automatic reconnection with resume
- ✅ Heartbeat/ping-pong keep-alive

**WebSocket Protocol:**
```json
// Client → Server: Start Upload
{
    "type": "start_upload",
    "file_name": "document.pdf",
    "file_size": 104857600,
    "chunk_size": 65536
}

// Server → Client: Upload Started
{
    "type": "upload_started",
    "upload_id": "abc123",
    "resume_from_chunk": 0
}

// Client → Server: Binary Chunk
<binary data: 65536 bytes>

// Server → Client: Progress Update
{
    "type": "progress",
    "upload_id": "abc123",
    "chunks_received": 150,
    "total_chunks": 1600,
    "percent": 9.375
}

// Server → Client: Pause Request
{
    "type": "pause",
    "reason": "Server maintenance in 5 minutes"
}

// Client → Server: Resume Upload
{
    "type": "resume",
    "upload_id": "abc123"
}

// Server → Client: Upload Complete
{
    "type": "completed",
    "upload_id": "abc123",
    "job_id": "xyz789"
}
```

**Endpoint:**
```
WS /ws/upload - WebSocket upload endpoint
```

**Client Usage:**
```python
# Python Client
import asyncio
from client_websocket_upload import WebSocketUploader

async def main():
    uploader = WebSocketUploader("ws://127.0.0.1:45679/ws/upload")
    
    await uploader.connect()
    
    result = await uploader.upload_file(
        "large_file.pdf",
        chunk_size=64*1024,  # 64 KB
        on_progress=lambda p: print(f"Progress: {p:.1f}%"),
        on_pause=lambda: print("Server requested pause"),
        on_resume=lambda: print("Upload resumed")
    )
    
    print(f"Job ID: {result['job_id']}")
    
    await uploader.disconnect()

asyncio.run(main())
```

---

### Phase 3: SMB Network Share + File Watcher (1-2 Tage)

**Dateien:**
- `ingestion/upload_smb_watcher.py` - File Watcher (300+ Zeilen)
- `tests/test_smb_watcher.py` - Unit Tests (150+ Zeilen)
- `scripts/setup_smb_share.ps1` - Server Setup Script (100+ Zeilen)

**Features:**
- ✅ Automatic file detection on network share
- ✅ File lock detection (wait for complete write)
- ✅ Subdirectory support (recursive watching)
- ✅ Move-on-success (archive processed files)
- ✅ Metadata from filename/path (optional)
- ✅ Duplicate detection (MD5 hash)

**Setup:**
```powershell
# Server: Create SMB Share
.\scripts\setup_smb_share.ps1 -ShareName "covina_upload" `
    -Path "C:\covina_data\uploads" `
    -FullAccess "DOMAIN\CovinaAdmins" `
    -ChangeAccess "DOMAIN\CovinaUsers"

# Client: Map Drive (Windows)
net use Y: \\SERVER\covina_upload /persistent:yes

# Client: Mount Share (Linux)
mount -t cifs //SERVER/covina_upload /mnt/covina -o user=USERNAME
```

**Directory Structure:**
```
\\SERVER\covina_upload\
├── inbox\           # User drops files here
│   ├── file1.pdf
│   ├── file2.docx
│   └── subdir\
│       └── file3.txt
├── processing\      # Auto-moved during processing
└── archive\         # Auto-moved after success
    └── 2025-10-15\
        ├── file1.pdf
        └── file2.docx
```

**Watcher Logic:**
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CovinaUploadHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Wait for file to be fully written
        if not self._wait_for_file_complete(file_path):
            logger.warning(f"File locked or incomplete: {file_path}")
            return
        
        # Move to processing directory
        processing_path = self._move_to_processing(file_path)
        
        # Create job and process
        job_id = self._create_job_from_file(processing_path)
        
        # On success: move to archive
        # On failure: move back to inbox with .error suffix
```

**User Experience:**
```
1. User opens Windows Explorer
2. Navigate to Y:\ (mapped SMB share)
3. Drag & Drop files into inbox\
4. Files automatically processed
5. Success: Files moved to archive\YYYY-MM-DD\
6. Failure: Files moved to inbox\ with .error suffix
```

---

### Phase 4: Hybrid Upload Manager (1 Tag)

**Dateien:**
- `ingestion/upload_hybrid_manager.py` - Hybrid Manager (400+ Zeilen)
- `tests/test_hybrid_manager.py` - Unit Tests (200+ Zeilen)

**Features:**
- ✅ Automatic method selection based on file size/count
- ✅ Unified API for all upload methods
- ✅ Method preference configuration
- ✅ Fallback chain (WebSocket → Chunked → SMB)
- ✅ Load balancing across methods
- ✅ Unified progress tracking

**Selection Logic:**
```python
class HybridUploadManager:
    def select_upload_method(self, file_size: int, file_count: int, 
                            client_capabilities: dict) -> str:
        """
        Auto-select best upload method
        
        Rules:
        1. Single file < 10 MB → Chunked HTTP (simple)
        2. Single file > 100 MB → WebSocket (streaming)
        3. Multiple files (>50) → SMB Watch (batch)
        4. Real-time feedback needed → WebSocket
        5. Resume capability required → Chunked HTTP
        6. Client doesn't support WS → Chunked HTTP
        """
        
        # Large single file → WebSocket
        if file_count == 1 and file_size > 100*1024*1024:
            if client_capabilities.get("websocket"):
                return "websocket"
            return "chunked"
        
        # Many small files → SMB
        if file_count > 50:
            return "smb_watch"
        
        # Default: Chunked HTTP
        return "chunked"
    
    async def upload(self, files: list[Path], method: str = "auto"):
        """Unified upload interface"""
        if method == "auto":
            method = self.select_upload_method(...)
        
        handler = self.get_handler(method)
        return await handler.upload(files)
```

**Unified API:**
```python
# Client doesn't care which method is used
from ingestion.upload_hybrid_manager import HybridUploadManager

manager = HybridUploadManager("http://127.0.0.1:45679")

# Auto-select best method
result = await manager.upload(
    files=["file1.pdf", "file2.pdf"],
    method="auto",  # or "chunked", "websocket", "smb"
    on_progress=lambda p: print(f"Progress: {p:.1f}%")
)

print(f"Method used: {result['method']}")
print(f"Job ID: {result['job_id']}")
```

---

## 🧪 Test-Suite (Phase 5: 2-3 Tage)

### Test-Szenarien

**1. Viele kleine Dateien (Stress Test)**
```
Files:     10,000 files
Size:      1-10 KB each
Total:     ~50 MB
Goal:      Test overhead, connection pooling
Expected:  SMB > WebSocket > Chunked
```

**2. Wenige riesige Dateien (Throughput Test)**
```
Files:     5 files
Size:      1-2 GB each
Total:     ~7.5 GB
Goal:      Test streaming, resume, memory
Expected:  WebSocket > Chunked > SMB
```

**3. Gemischte Dateigrößen (Real-World)**
```
Files:     100 files
Sizes:     10 KB - 500 MB (mixed)
Total:     ~10 GB
Goal:      Test adaptive selection
Expected:  Hybrid > Single-Method
```

**4. Netzwerk-Unterbrechung (Resilience)**
```
Scenario:  Upload 1 GB file, disconnect at 50%
Goal:      Test resume capability
Expected:  Chunked + WebSocket succeed, SMB fails
```

**5. Parallele Uploads (Concurrency)**
```
Clients:   10 simultaneous clients
Files:     100 files each
Goal:      Test scalability, resource limits
Expected:  All methods handle gracefully
```

**6. Bandbreiten-Limit (Throttling)**
```
Bandwidth: 10 Mbps limit
Files:     1 GB file
Goal:      Test throttling, timeouts
Expected:  WebSocket most efficient
```

### Test-Dateien

**Datei-Struktur:**
```python
# tests/test_data_generator.py
def generate_test_files():
    """Generate test files for all scenarios"""
    
    # Scenario 1: 10,000 small files (1-10 KB)
    for i in range(10000):
        size = random.randint(1024, 10240)
        create_random_file(f"small_{i:05d}.txt", size)
    
    # Scenario 2: 5 huge files (1-2 GB)
    for i in range(5):
        size = random.randint(1024**3, 2*1024**3)
        create_random_file(f"huge_{i}.bin", size)
    
    # Scenario 3: 100 mixed files (10 KB - 500 MB)
    for i in range(100):
        size = random.randint(10240, 500*1024**2)
        create_random_file(f"mixed_{i:03d}.dat", size)
```

### Test-Implementierung

**Dateien:**
- `tests/load_test_upload_methods.py` - Haupttest-Suite (800+ Zeilen)
- `tests/test_data_generator.py` - Test-Daten Generator (200+ Zeilen)
- `tests/network_simulator.py` - Netzwerk-Simulation (300+ Zeilen)

**Test-Suite:**
```python
# tests/load_test_upload_methods.py
import pytest
from ingestion.upload_chunked import ChunkedUploadHandler
from ingestion.upload_websocket import WebSocketUploadHandler
from ingestion.upload_smb_watcher import SMBWatcherHandler
from ingestion.upload_hybrid_manager import HybridUploadManager

class TestUploadMethods:
    @pytest.mark.parametrize("method", ["chunked", "websocket", "smb", "hybrid"])
    def test_many_small_files(self, method):
        """Test 10,000 small files (1-10 KB)"""
        files = generate_small_files(10000)
        
        start = time.time()
        result = upload_files(files, method=method)
        duration = time.time() - start
        
        assert result["status"] == "completed"
        assert result["files_processed"] == 10000
        
        print(f"{method}: {duration:.2f}s, {10000/duration:.2f} files/s")
    
    @pytest.mark.parametrize("method", ["chunked", "websocket", "smb", "hybrid"])
    def test_few_huge_files(self, method):
        """Test 5 huge files (1-2 GB each)"""
        files = generate_huge_files(5)
        
        start = time.time()
        result = upload_files(files, method=method)
        duration = time.time() - start
        
        total_size_gb = sum(f.stat().st_size for f in files) / 1024**3
        throughput_mbps = (total_size_gb * 1024 * 8) / duration
        
        assert result["status"] == "completed"
        assert result["files_processed"] == 5
        
        print(f"{method}: {duration:.2f}s, {throughput_mbps:.2f} Mbps")
    
    def test_resume_capability(self):
        """Test resume after disconnect (Chunked + WebSocket only)"""
        file = create_random_file("resume_test.bin", 1024**3)  # 1 GB
        
        for method in ["chunked", "websocket"]:
            uploader = get_uploader(method)
            
            # Start upload
            upload_id = uploader.start_upload(file)
            
            # Wait for 50% progress
            while uploader.get_progress(upload_id) < 0.5:
                time.sleep(1)
            
            # Simulate disconnect
            uploader.disconnect()
            
            # Resume
            uploader.connect()
            result = uploader.resume_upload(upload_id)
            
            assert result["status"] == "completed"
            assert result["resumed_from"] >= 0.4  # Within 10% of disconnect
```

**Expected Results:**
```
========================== Test Results ==========================

Test: Many Small Files (10,000 × 5 KB)
----------------------------------------------------------------------
Method          Duration    Files/s    Throughput    Rating
----------------------------------------------------------------------
SMB Watch       12.5s       800 f/s    32 MB/s       ⭐⭐⭐⭐⭐
WebSocket       18.3s       546 f/s    22 MB/s       ⭐⭐⭐⭐
Chunked HTTP    45.2s       221 f/s    8.8 MB/s      ⭐⭐⭐
Hybrid (Auto)   13.1s       763 f/s    31 MB/s       ⭐⭐⭐⭐⭐

Test: Few Huge Files (5 × 1.5 GB)
----------------------------------------------------------------------
Method          Duration    Throughput    Memory     Rating
----------------------------------------------------------------------
WebSocket       620s        97 Mbps       250 MB     ⭐⭐⭐⭐⭐
Chunked HTTP    680s        88 Mbps       180 MB     ⭐⭐⭐⭐
SMB Watch       890s        67 Mbps       520 MB     ⭐⭐⭐
Hybrid (Auto)   625s        96 Mbps       260 MB     ⭐⭐⭐⭐⭐

Test: Mixed Files (100 files, 10 KB - 500 MB)
----------------------------------------------------------------------
Method          Duration    Throughput    Rating
----------------------------------------------------------------------
Hybrid (Auto)   285s        285 MB/s      ⭐⭐⭐⭐⭐
WebSocket       310s        258 MB/s      ⭐⭐⭐⭐
Chunked HTTP    420s        190 MB/s      ⭐⭐⭐
SMB Watch       380s        210 MB/s      ⭐⭐⭐⭐

Test: Resume Capability (1 GB file, 50% disconnect)
----------------------------------------------------------------------
Method          Resumed     Data Re-sent    Rating
----------------------------------------------------------------------
Chunked HTTP    ✅ Yes      0% (perfect)    ⭐⭐⭐⭐⭐
WebSocket       ✅ Yes      2% (acceptable) ⭐⭐⭐⭐
SMB Watch       ❌ No       100% (restart)  ⭐

Test: Parallel Uploads (10 clients × 100 files)
----------------------------------------------------------------------
Method          Duration    Success Rate    Rating
----------------------------------------------------------------------
Hybrid (Auto)   95s         100%            ⭐⭐⭐⭐⭐
WebSocket       110s        100%            ⭐⭐⭐⭐
SMB Watch       125s        100%            ⭐⭐⭐⭐
Chunked HTTP    180s        100%            ⭐⭐⭐

==================================================================
OVERALL RANKING:
1. Hybrid Manager     - ⭐⭐⭐⭐⭐ (Best overall)
2. WebSocket          - ⭐⭐⭐⭐  (Best for large files)
3. SMB Watch          - ⭐⭐⭐⭐  (Best for small files)
4. Chunked HTTP       - ⭐⭐⭐   (Most reliable)
==================================================================
```

---

## 📊 Implementation Timeline

### Woche 1: Core Upload Methods

| **Tag** | **Task** | **Deliverable** | **Status** |
|---------|----------|-----------------|------------|
| **1** | Chunked HTTP Backend | `upload_chunked.py` (400 lines) | ⏸️ |
| **2** | Chunked HTTP Client | Python + PowerShell clients (500 lines) | ⏸️ |
| **3** | Chunked HTTP Tests | Unit + Integration tests (200 lines) | ⏸️ |
| **4** | WebSocket Backend | `upload_websocket.py` (500 lines) | ⏸️ |
| **5** | WebSocket Client | Python async client (350 lines) | ⏸️ |
| **6** | WebSocket Tests | Unit + Integration tests (250 lines) | ⏸️ |
| **7** | SMB Watcher | `upload_smb_watcher.py` (300 lines) | ⏸️ |

### Woche 2: Hybrid Manager + Testing

| **Tag** | **Task** | **Deliverable** | **Status** |
|---------|----------|-----------------|------------|
| **8** | SMB Setup Scripts | PowerShell server setup (100 lines) | ⏸️ |
| **9** | Hybrid Manager | `upload_hybrid_manager.py` (400 lines) | ⏸️ |
| **10** | Test Data Generator | Generate test files (200 lines) | ⏸️ |
| **11** | Load Test Suite | All 6 scenarios (800 lines) | ⏸️ |
| **12** | Performance Testing | Run full test suite | ⏸️ |
| **13** | Documentation | Complete docs + results | ⏸️ |
| **14** | Production Deploy | Deploy best method(s) | ⏸️ |

---

## 📁 File Structure

```
Covina/
├── ingestion/
│   ├── upload_chunked.py           # Lösung 1: Chunked HTTP (400 lines)
│   ├── upload_websocket.py         # Lösung 2: WebSocket (500 lines)
│   ├── upload_smb_watcher.py       # Lösung 3: SMB Watch (300 lines)
│   └── upload_hybrid_manager.py    # Lösung 4: Hybrid (400 lines)
│
├── scripts/
│   ├── client_chunked_upload.py    # Python Chunked Client (300 lines)
│   ├── client_chunked_upload.ps1   # PowerShell Chunked Client (200 lines)
│   ├── client_websocket_upload.py  # Python WebSocket Client (350 lines)
│   └── setup_smb_share.ps1         # SMB Server Setup (100 lines)
│
├── tests/
│   ├── test_chunked_upload.py      # Chunked Unit Tests (200 lines)
│   ├── test_websocket_upload.py    # WebSocket Unit Tests (250 lines)
│   ├── test_smb_watcher.py         # SMB Watcher Tests (150 lines)
│   ├── test_hybrid_manager.py      # Hybrid Tests (200 lines)
│   ├── test_data_generator.py      # Test File Generator (200 lines)
│   ├── network_simulator.py        # Network Sim (300 lines)
│   └── load_test_upload_methods.py # Full Test Suite (800 lines)
│
├── docs/
│   ├── UPLOAD_SOLUTIONS_ROADMAP.md         # This file
│   ├── CHUNKED_UPLOAD_IMPLEMENTATION.md    # Chunked HTTP docs
│   ├── WEBSOCKET_UPLOAD_IMPLEMENTATION.md  # WebSocket docs
│   ├── SMB_WATCHER_IMPLEMENTATION.md       # SMB Watch docs
│   ├── HYBRID_MANAGER_IMPLEMENTATION.md    # Hybrid docs
│   └── UPLOAD_PERFORMANCE_TEST_RESULTS.md  # Test results
│
└── data/
    └── uploads/
        ├── chunked/           # Temp chunks
        ├── websocket/         # Temp streams
        ├── smb_inbox/         # SMB inbox
        ├── smb_processing/    # SMB processing
        └── smb_archive/       # SMB archive
```

**Total Lines of Code (Estimated):** ~5,800 Zeilen

---

## 🔧 Configuration

**ENV Variables:**
```bash
# .env.production

# Chunked Upload
ENABLE_CHUNKED_UPLOAD=true
CHUNKED_CHUNK_SIZE=5242880          # 5 MB
CHUNKED_MAX_PARALLEL_CHUNKS=3
CHUNKED_SESSION_TIMEOUT=86400       # 24 hours

# WebSocket Upload
ENABLE_WEBSOCKET_UPLOAD=true
WEBSOCKET_CHUNK_SIZE=65536          # 64 KB
WEBSOCKET_MAX_CONNECTIONS=100
WEBSOCKET_HEARTBEAT_INTERVAL=30     # seconds

# SMB Watcher
ENABLE_SMB_WATCHER=true
SMB_WATCH_PATH=\\\\SERVER\\covina_upload\\inbox
SMB_ARCHIVE_PATH=\\\\SERVER\\covina_upload\\archive
SMB_MOVE_ON_SUCCESS=true
SMB_CHECK_INTERVAL=5                # seconds

# Hybrid Manager
ENABLE_HYBRID_MANAGER=true
HYBRID_AUTO_SELECT=true
HYBRID_PREFER_METHOD=auto           # auto, chunked, websocket, smb
HYBRID_SMALL_FILE_THRESHOLD=10485760    # 10 MB
HYBRID_LARGE_FILE_THRESHOLD=104857600   # 100 MB
HYBRID_BATCH_THRESHOLD=50               # files
```

---

## 🎯 Success Criteria

### Functional Requirements

- ✅ All 4 methods upload files successfully
- ✅ Progress tracking works for all methods
- ✅ Resume works for Chunked + WebSocket
- ✅ SMB Watcher detects files within 5 seconds
- ✅ Hybrid Manager selects optimal method

### Performance Requirements

- ✅ **Many small files:** >500 files/s
- ✅ **Few huge files:** >80 Mbps throughput
- ✅ **Mixed files:** <300s for 10 GB
- ✅ **Resume:** <5% data re-transmission
- ✅ **Parallel:** 10 clients without degradation

### Quality Requirements

- ✅ **Unit Test Coverage:** >80%
- ✅ **Integration Tests:** All scenarios pass
- ✅ **Documentation:** Complete for all methods
- ✅ **Error Handling:** Graceful failures
- ✅ **Logging:** Comprehensive audit trail

---

## 📚 Documentation Deliverables

1. **CHUNKED_UPLOAD_IMPLEMENTATION.md** (~1,500 Zeilen)
   - Architecture, API, Client usage, Resume logic

2. **WEBSOCKET_UPLOAD_IMPLEMENTATION.md** (~1,800 Zeilen)
   - Protocol spec, Reconnection, Bidirectional control

3. **SMB_WATCHER_IMPLEMENTATION.md** (~1,200 Zeilen)
   - Setup guide, Watcher logic, Directory structure

4. **HYBRID_MANAGER_IMPLEMENTATION.md** (~1,500 Zeilen)
   - Selection algorithm, Unified API, Fallback chain

5. **UPLOAD_PERFORMANCE_TEST_RESULTS.md** (~2,000 Zeilen)
   - Test scenarios, Results, Recommendations

**Total Documentation:** ~8,000 Zeilen

---

## 🚀 Next Steps

1. **Review Roadmap** - User approval
2. **Start Phase 1** - Chunked HTTP implementation
3. **Parallel Development** - Can split work across methods
4. **Testing** - Continuous testing during development
5. **Documentation** - Write as we implement

**Ready to start?** Welche Lösung sollen wir zuerst implementieren? 🎯

**Empfehlung:** Beginnen mit **Lösung 1 (Chunked HTTP)** - bietet beste Basis für Hybrid Manager!
