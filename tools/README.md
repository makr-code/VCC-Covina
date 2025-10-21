# Covina Ingestion GUI Tool

Simple GUI tool for uploading files and folders to the Covina Ingestion Backend.

## Features

- ✅ **File Selection:** Select individual files via file dialog
- ✅ **Folder Selection:** Select entire folders (recursive scan)
- ✅ **Drag & Drop:** Drag files/folders directly into the window
- ✅ **Progress Tracking:** Real-time progress bar with file counts
- ✅ **WebSocket Monitoring:** Live job status updates
- ✅ **Supported Formats:** PDF, DOCX, TXT, XLSX, CSV, JSON, XML, HTML, MD, RTF
- ✅ **Backend Status:** Visual indicator for backend availability

## Installation

### 1. Install Dependencies

```bash
# Navigate to tools directory
cd C:\VCC\Covina\tools

# Install requirements
pip install -r requirements.txt
```

### 2. Verify Backend Running

Ensure Covina Ingestion Backend is running on `http://127.0.0.1:45679`:

```powershell
# Start Covina services
cd C:\VCC\Covina
.\scripts\start_services.ps1
```

## Usage

### Start GUI

```bash
# From tools directory
python ingestion_gui.py

# Or from Covina root
python tools\ingestion_gui.py
```

### Upload Files

**Method 1: File Dialog**
1. Click "📁 Select Files" button
2. Choose one or more files
3. Click "🚀 Start Upload"

**Method 2: Folder Dialog**
1. Click "📂 Select Folder" button
2. Choose a folder (recursively scans for supported files)
3. Click "🚀 Start Upload"

**Method 3: Drag & Drop** (if tkinterdnd2 installed)
1. Drag files or folders into the file list
2. Click "🚀 Start Upload"

### Monitor Progress

- **Progress Bar:** Shows upload/processing progress (0-100%)
- **Status Label:** Shows current operation and file counts
- **Backend Indicator:** Shows backend connection status
  - ✅ Green: Backend online
  - ❌ Red: Backend offline
  - ⚪ Gray: Checking...

## Configuration

Edit the following constants in `ingestion_gui.py`:

```python
# Backend URL
INGESTION_BACKEND_URL = "http://127.0.0.1:45679"

# WebSocket URL for job monitoring
WEBSOCKET_URL = "ws://127.0.0.1:45679/ws/jobs"

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.pdf', '.txt', '.docx', '.doc', '.xlsx', '.xls', 
    '.csv', '.json', '.xml', '.html', '.md', '.rtf'
}
```

## Troubleshooting

### Backend Offline

**Symptom:** Red "❌ Backend: Offline" indicator

**Solution:**
```powershell
# Start Covina backends
cd C:\VCC\Covina
.\scripts\start_services.ps1

# Verify backends running
curl http://127.0.0.1:45678/health  # Main Backend
curl http://127.0.0.1:45679/health  # Ingestion Backend
```

### Drag & Drop Not Working

**Symptom:** Drag & drop has no effect

**Solution:**
```bash
# Install tkinterdnd2
pip install tkinterdnd2

# If still not working, use file/folder dialogs instead
```

### Upload Timeout

**Symptom:** Upload fails with timeout error

**Solution:**
- Reduce number of files (< 100 files at once)
- Check backend logs: `logs/ingestion_backend.log`
- Increase timeout in code (default: 300 seconds)

### WebSocket Connection Failed

**Symptom:** Progress bar doesn't update during processing

**Solution:**
- Check WebSocket endpoint: `ws://127.0.0.1:45679/ws/jobs`
- Verify firewall allows WebSocket connections
- Check backend logs for WebSocket errors

## Architecture

```
┌─────────────────────────┐
│  Ingestion GUI Tool     │
│  (ingestion_gui.py)     │
└──────────┬──────────────┘
           │
           │ HTTP POST /upload/
           ├──────────────────────────┐
           │                          │
           │                          v
           │              ┌─────────────────────────┐
           │              │  Ingestion Backend      │
           │              │  (Port 45679)           │
           │              └──────────┬──────────────┘
           │                         │
           │ WebSocket /ws/jobs      │ UDS3 Processing
           │ (Job Progress)          │
           │                         v
           │              ┌─────────────────────────┐
           └──────────────│  PostgreSQL + ChromaDB  │
                          │  + Neo4j + CouchDB      │
                          └─────────────────────────┘
```

## API Endpoints

### Upload Files
```
POST http://127.0.0.1:45679/upload/
Content-Type: multipart/form-data

Body: files[] (multiple files)

Response:
{
  "job_id": "job_20251021_123456",
  "status": "pending",
  "total_files": 5
}
```

### WebSocket Job Monitoring
```
WS ws://127.0.0.1:45679/ws/jobs

Messages:
{
  "job_id": "job_20251021_123456",
  "status": "processing",
  "files_processed": 3,
  "total_files": 5
}
```

## Future Enhancements

- [ ] **Job History:** View past uploads and their status
- [ ] **Resume Failed Jobs:** Retry failed file processing
- [ ] **Batch Operations:** Create multiple jobs with different folders
- [ ] **Filters:** Show only specific file types
- [ ] **Preview:** Show file content before upload
- [ ] **Settings:** Save backend URL and preferences
- [ ] **Dark Mode:** Toggle between light/dark themes

## Version History

**v1.0.0** (21. Oktober 2025)
- Initial release
- File/folder selection
- Drag & drop support
- Progress tracking
- WebSocket monitoring
- Backend status indicator

---

**Status:** ✅ PRODUCTION READY  
**Author:** Covina System Team  
**License:** Internal Use Only
