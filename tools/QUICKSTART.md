# 🚀 Quick Start Guide - Covina Ingestion GUI

## 1️⃣ Start Backend (Required)

```powershell
# Terminal 1: Start Covina Services
cd C:\VCC\Covina
.\scripts\start_services.ps1

# Wait for backends to start (both should show "Online"):
# - Main Backend: http://127.0.0.1:45678
# - Ingestion Backend: http://127.0.0.1:45679
```

## 2️⃣ Start Ingestion GUI

**Option A: PowerShell Script (Recommended)**
```powershell
# Terminal 2: Start GUI
cd C:\VCC\Covina\tools
.\start_ingestion_gui.ps1
```

**Option B: Direct Python**
```powershell
# Terminal 2: Start GUI directly
cd C:\VCC\Covina
python tools\ingestion_gui.py
```

**Option C: Batch Script**
```cmd
# Double-click or run in CMD
C:\VCC\Covina\tools\start_ingestion_gui.bat
```

## 3️⃣ Upload Files

### Method 1: Select Files (Best for few files)
1. Click **"📁 Select Files"**
2. Choose one or more files
3. Click **"🚀 Start Upload"**

### Method 2: Select Folder (Best for many files)
1. Click **"📂 Select Folder"**
2. Choose a folder (automatically scans for supported files)
3. Click **"🚀 Start Upload"**

### Method 3: Drag & Drop (Fastest)
1. Drag files or folders from Windows Explorer
2. Drop them into the file list
3. Click **"🚀 Start Upload"**

## 4️⃣ Monitor Progress

- **Progress Bar:** Shows upload/processing progress (0-100%)
- **File Count:** Shows "X/Y files (Z%)"
- **Status:** Shows current operation
- **Backend Status:** Green ✅ = Online, Red ❌ = Offline

## 📁 Supported File Types

- **Documents:** PDF, DOCX, DOC, TXT, MD, RTF
- **Spreadsheets:** XLSX, XLS, CSV
- **Data:** JSON, XML
- **Web:** HTML

## ⚡ Quick Tips

### Tip 1: Backend Must Run First
```powershell
# Check backend status:
curl http://127.0.0.1:45679/health

# If offline, start services:
.\scripts\start_services.ps1
```

### Tip 2: Batch Upload Large Folders
```
Small folders (< 50 files):   Upload directly
Medium folders (50-200 files): Upload in one batch
Large folders (> 200 files):   Split into smaller batches
```

### Tip 3: Monitor Job Progress
- Progress bar updates automatically via WebSocket
- Check backend logs for details: `logs/ingestion_backend.log`
- Job ID shown after upload (e.g., `job_20251021_123456`)

## 🔧 Troubleshooting

### Problem: Backend Offline

**Symptom:** Red "❌ Backend: Offline" indicator

**Solution:**
```powershell
cd C:\VCC\Covina
.\scripts\start_services.ps1

# Wait 10-15 seconds, then check GUI
# Backend indicator should turn green ✅
```

### Problem: Upload Hangs

**Symptom:** Progress bar stuck at 0%

**Solutions:**
1. Check file sizes (reduce if > 100MB per file)
2. Check network: `curl http://127.0.0.1:45679/health`
3. Check backend logs: `logs/ingestion_backend.log`
4. Restart backend: `.\scripts\stop_services.ps1` then start again

### Problem: No Files Found in Folder

**Symptom:** Message "Found 0 supported files"

**Solutions:**
1. Check folder contains supported file types (PDF, DOCX, etc.)
2. Try subfolder (GUI scans recursively)
3. Check file extensions match supported list

### Problem: Drag & Drop Not Working

**Symptom:** Dragging files has no effect

**Solutions:**
1. Use "📁 Select Files" or "📂 Select Folder" instead
2. Check tkinterdnd2 installed: `pip list | grep tkinterdnd2`
3. Restart GUI

## 📊 Example Workflow

```
1. Start Backend
   → .\scripts\start_services.ps1
   → Wait for "Backend: Online" ✅

2. Start GUI
   → .\tools\start_ingestion_gui.ps1
   → GUI opens

3. Select Folder
   → Click "📂 Select Folder"
   → Choose C:\Documents\Contracts
   → GUI shows: "47 files selected (12.5 MB)"

4. Start Upload
   → Click "🚀 Start Upload"
   → Progress: "Uploading 47 files..."
   → Job ID: job_20251021_123456

5. Monitor Progress
   → Progress bar: 47/47 (100%)
   → Status: "✅ Job completed! All 47 files processed successfully."

6. Check Results
   → Files now in PostgreSQL, ChromaDB, Neo4j, CouchDB
   → Query via Main Backend (Port 45678)
```

## 🎯 Next Steps

After upload completes:

1. **Query Documents:**
   ```bash
   curl http://127.0.0.1:45678/api/documents/
   ```

2. **Semantic Search:**
   ```bash
   curl -X POST http://127.0.0.1:45678/api/search/semantic \
     -H "Content-Type: application/json" \
     -d '{"query": "contracts", "top_k": 10}'
   ```

3. **Check Job Status:**
   ```bash
   curl http://127.0.0.1:45679/jobs/job_20251021_123456/status
   ```

---

**Need Help?** Check full documentation: `tools/README.md`

**Version:** 1.0.0  
**Status:** ✅ READY TO USE
