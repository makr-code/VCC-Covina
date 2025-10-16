# Progressbar Backend Integration - Manuelle Anleitung

**Datum:** 14. Oktober 2025, 15:00 Uhr  
**Datei:** `ingestion_backend.py`  
**Lines:** 381-482 (Methode `_bulk_copy_directory`)

---

## ⚠️ Problem

Die automatische String-Ersetzung schlägt fehl wegen:
- Datei zu groß (2798 Zeilen)
- Komplexe Multi-Line Replacement (100+ Zeilen)
- Formatierungs-Unterschiede

---

## ✅ Lösung: Manuelle Integration

### Schritt 1: Alte Methode löschen

**Datei:** `ingestion_backend.py`  
**Lines:** 381-482

Lösche KOMPLETT die alte `_bulk_copy_directory` Methode (101 Zeilen).

**Visual Studio Code:**
1. Öffne `ingestion_backend.py`
2. Gehe zu Line 381
3. Markiere Lines 381-482
4. Drücke `Delete`

---

### Schritt 2: Neue Methode einfügen

**Position:** Line 381 (wo die alte Methode war)

**Code zum Einfügen:**

```python
    async def _bulk_copy_directory(self):
        """
        🆕 Copy entire directory to temp_dir with STREAMING PROGRESS UPDATES.
        
        Benefits:
        - Much faster than Python file-by-file copy
        - Handles Network Drives efficiently
        - Real-time progress updates via WebSocket
        - Robust error handling
        - Uses robocopy (Windows) or rsync (Linux)
        """
        from ingestion.bulk_copy_streaming import BulkCopyStreaming, CopyProgress
        
        logger.info(f"📦 [SCAN {self.scan_job_id}] Bulk copy: {self.directory_path} → {self.temp_dir}")
        
        # 🆕 Initialize progress tracking
        self.bulk_copy_progress = BulkCopyProgress(status="preparing")
        await self._broadcast_bulk_copy_progress()
        
        async def on_progress(progress: CopyProgress):
            """Callback for progress updates from streaming module"""
            # Update our progress object
            self.bulk_copy_progress.percent_complete = progress.percent_complete
            self.bulk_copy_progress.files_copied = progress.files_copied
            self.bulk_copy_progress.total_files = progress.total_files
            self.bulk_copy_progress.bytes_copied = progress.bytes_copied
            self.bulk_copy_progress.total_bytes = progress.total_bytes
            self.bulk_copy_progress.copy_rate_mbps = progress.copy_rate_mbps
            self.bulk_copy_progress.eta_seconds = progress.eta_seconds
            self.bulk_copy_progress.current_file = progress.current_file
            self.bulk_copy_progress.status = progress.status
            
            # Broadcast to WebSocket clients
            await self._broadcast_bulk_copy_progress()
        
        # 🆕 Use streaming bulk copy with progress callbacks
        copier = BulkCopyStreaming(
            source=self.directory_path,
            destination=self.temp_dir,
            progress_callback=on_progress,
            broadcast_interval=5.0  # Update UI every 5 seconds
        )
        
        timeout_seconds = 1800  # 30 minutes for large network transfers (7+ GB)
        
        try:
            final_progress = await copier.execute(timeout=timeout_seconds)
            
            logger.info(
                f"✅ [SCAN {self.scan_job_id}] Bulk copy complete: "
                f"{final_progress.files_copied} files, "
                f"{final_progress.bytes_copied / (1024**3):.2f} GB, "
                f"avg rate: {final_progress.copy_rate_mbps:.1f} MB/s"
            )
            
            # Mark progress as completed
            self.bulk_copy_progress.status = "completed"
            await self._broadcast_bulk_copy_progress()
            
            # Re-initialize scanner to point to LOCAL copy
            logger.info(f"🔄 [SCAN {self.scan_job_id}] Re-initializing scanner for local copy...")
            self.scanner = DirectoryScanner(
                root=self.temp_dir,  # ✅ Now scans local copy!
                classifier=FileClassifier(),
                compute_hashes=False
            )
            logger.info(f"✅ [SCAN {self.scan_job_id}] Scanner ready for local directory")
            
        except asyncio.TimeoutError:
            self.bulk_copy_progress.status = "error"
            await self._broadcast_bulk_copy_progress()
            raise TimeoutError(
                f"Directory copy timeout after {timeout_seconds}s "
                f"(source: {self.directory_path})"
            )
        except Exception as e:
            self.bulk_copy_progress.status = "error"
            await self._broadcast_bulk_copy_progress()
            logger.error(f"❌ [SCAN {self.scan_job_id}] Bulk copy error: {e}")
            raise
```

---

### Schritt 3: Syntax-Check

**Visual Studio Code:**
1. Speichere die Datei (`Ctrl+S`)
2. Prüfe auf Syntax-Fehler (rote Wellenlinien)
3. Achte auf korrekte Indentation (4 Spaces)

**Python Syntax Check:**
```powershell
python -m py_compile ingestion_backend.py
```

Erwarte: Keine Ausgabe = Syntax OK ✅

---

### Schritt 4: Import-Check

Prüfe, ob `BulkCopyStreaming` importierbar ist:

```powershell
python -c "from ingestion.bulk_copy_streaming import BulkCopyStreaming; print('✅ Import OK')"
```

Erwarte: `✅ Import OK`

---

### Schritt 5: Backend neu starten

**PowerShell:**
```powershell
# Stop old backend
Get-Process | Where-Object { $_.ProcessName -eq 'python' -and $_.CommandLine -like '*ingestion_backend*' } | Stop-Process -Force

# Start new backend
python ingestion_backend.py
```

**Erwartete Logs:**
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:45679 (Press CTRL+C to quit)
```

---

### Schritt 6: Health Check

```powershell
curl http://127.0.0.1:45679/health
```

**Erwartete Response:**
```json
{
  "status": "healthy",
  "version": "3.4.9.2",
  "ingestion_backend": true
}
```

---

## 🧪 Testing

### Test 1: Kleines Directory (100 MB)

**PowerShell:**
```powershell
# Erstelle Test-Directory
New-Item -Path "C:\Temp\test_small" -ItemType Directory -Force
1..10 | ForEach-Object { 
    $file = New-Item -Path "C:\Temp\test_small\file_$_.txt" -ItemType File -Force
    1..1048576 | ForEach-Object { "Test data line $_" } | Out-File -FilePath $file -Encoding UTF8
}

# Upload via API
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:45679/upload-directory" `
    -Body (@{ directory_path = "C:\Temp\test_small" } | ConvertTo-Json) `
    -ContentType "application/json"
```

**Erwartetes Verhalten:**
- ✅ Sofortige Response mit `scan_job_id`
- ✅ WebSocket updates alle 5s
- ✅ Progress: 0% → 100%
- ✅ Final log: "Bulk copy complete: 10 files, X GB"

---

### Test 2: WebSocket Monitoring

**wscat (installiere mit `npm install -g wscat`):**
```bash
wscat -c ws://127.0.0.1:45679/ws/jobs
```

**Oder Python:**
```python
import asyncio
import websockets
import json

async def monitor():
    uri = "ws://127.0.0.1:45679/ws/jobs"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            if data.get("type") == "bulk_copy_progress":
                progress = data["progress"]
                print(f"Progress: {progress['percent_complete']:.1f}% | "
                      f"Files: {progress['files_copied']} | "
                      f"Data: {progress['bytes_gb']} GB | "
                      f"Rate: {progress['copy_rate_mbps']} MB/s")

asyncio.run(monitor())
```

**Erwartete Ausgabe:**
```
Progress: 0.0% | Files: 0 | Data: 0.0 GB | Rate: 0.0 MB/s
Progress: 15.3% | Files: 2 | Data: 0.02 GB | Rate: 45.2 MB/s
Progress: 47.8% | Files: 5 | Data: 0.05 GB | Rate: 98.1 MB/s
Progress: 89.4% | Files: 9 | Data: 0.09 GB | Rate: 112.5 MB/s
Progress: 100.0% | Files: 10 | Data: 0.10 GB | Rate: 105.3 MB/s
```

---

### Test 3: Status Endpoint

**Während Upload läuft:**
```powershell
$response = Invoke-RestMethod -Uri "http://127.0.0.1:45679/scan-status/{scan_job_id}"
$response | ConvertTo-Json -Depth 5
```

**Erwartete Response:**
```json
{
  "scan_job_id": "scan_abc123",
  "status": "scanning",
  "files_found": 0,
  "bulk_copy_progress": {
    "percent_complete": 47.8,
    "files_copied": 5,
    "total_files": 10,
    "bytes_copied": 52428800,
    "total_bytes": 104857600,
    "copy_rate_mbps": 98.1,
    "eta_seconds": 120,
    "current_file": "file_5.txt",
    "status": "copying"
  }
}
```

---

## ✅ Erfolgs-Kriterien

- [ ] Backend startet ohne Fehler
- [ ] Health endpoint: `status: "healthy"`
- [ ] WebSocket connection: Erfolgreich
- [ ] Bulk copy progress: Updates alle 5s
- [ ] Progress: 0% → 100%
- [ ] Final status: "completed"
- [ ] Logs: Keine Errors
- [ ] Scanner: Re-initialisiert auf local copy

---

## 🐛 Troubleshooting

### Problem: Import Error `No module named 'ingestion.bulk_copy_streaming'`

**Ursache:** Modul nicht gefunden

**Lösung:**
```powershell
# Prüfe, ob Datei existiert
Test-Path "C:\VCC\Covina\ingestion\bulk_copy_streaming.py"
# Sollte: True

# Prüfe Python Path
python -c "import sys; print('\n'.join(sys.path))"
# Sollte: C:\VCC\Covina enthalten
```

---

### Problem: `BulkCopyProgress` not defined

**Ursache:** Pydantic Model nicht definiert (sollte bereits in Lines 124-148 sein)

**Lösung:**
```powershell
# Prüfe Lines 124-148
Select-String -Path "ingestion_backend.py" -Pattern "class BulkCopyProgress"
# Sollte: Line 124 gefunden
```

Wenn nicht gefunden:
```python
# Füge nach Line 123 ein:
class BulkCopyProgress(BaseModel):
    """Progress information for bulk copy operation"""
    percent_complete: float = 0.0
    files_copied: int = 0
    total_files: int = 0
    bytes_copied: int = 0
    total_bytes: int = 0
    copy_rate_mbps: float = 0.0
    eta_seconds: int = 0
    current_file: str = ""
    status: str = "preparing"
```

---

### Problem: WebSocket keine Updates

**Ursache:** `_broadcast_bulk_copy_progress()` nicht aufgerufen

**Lösung:**
```powershell
# Prüfe Lines 252-276
Select-String -Path "ingestion_backend.py" -Pattern "_broadcast_bulk_copy_progress"
# Sollte: 2+ matches (Definition + Aufrufe)
```

---

### Problem: robocopy findet keine Dateien

**Ursache:** `source` oder `dest` Pfad falsch

**Lösung:**
```python
# Prüfe Logs:
logger.info(f"Source: {self.directory_path}")
logger.info(f"Dest: {self.temp_dir}")

# Beide sollten absolute Pfade sein:
# Source: C:\Data\MyDirectory
# Dest: C:\VCC\Covina\data\uploads\job_xyz_1234567890
```

---

## 📊 Performance Erwartungen

**7.7 GB Directory (~ 2000 Files):**

| Metrik | Erwartung |
|--------|-----------|
| Copy Rate | 50-200 MB/s (abhängig von HDD/SSD) |
| Total Time | 6-25 Minuten |
| WebSocket Updates | ~72-300 messages (5s Intervall) |
| Progress Accuracy | ±5% |
| ETA Accuracy | ±20% nach 10% |

---

## 🎉 Fertig!

Nach erfolgreicher Integration:

1. ✅ Backend hat streaming progress
2. ✅ WebSocket broadcasts alle 5s
3. ✅ Status endpoint mit progress data
4. ⏳ Frontend implementation (nächster Schritt)

---

**Erstellt:** 14. Oktober 2025, 15:00 Uhr  
**Status:** READY FOR MANUAL INTEGRATION  
**Next Step:** Frontend Progress Modal (2-3h)
