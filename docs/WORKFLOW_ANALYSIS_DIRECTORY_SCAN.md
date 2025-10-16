# Workflow-Analyse: Directory Scan & Ingestion

**Datum:** 14. Oktober 2025, 14:15 Uhr  
**Analysiert von:** GitHub Copilot  
**Status:** 🔴 **WORKFLOW FEHLERHAFT - Redesign erforderlich**

---

## 🎯 **SOLL-Workflow (User-Erwartung)**

### Phase 1: Directory Scan
```
Frontend → POST /upload/directory → Ingestion Backend
  ↓
1. Async Directory Scan (recursive)
   - os.walk() durch übergebenes Verzeichnis
   - Findet alle unterstützten Dateien (inkl. Archive)
   - Erstellt Liste aller zu verarbeitenden Dateien

2. Dateien verschieben
   ✅ Alle gefundenen Dateien nach data/uploads/ verschieben
   ✅ Organisiert nach Job-ID oder Scan-ID
   ✅ Original-Verzeichnis bleibt unverändert

3. Archive erkennen & entpacken
   ✅ .zip, .rar, .7z, .tar.gz Dateien erkennen
   ✅ Entpacken nach data/uploads/job_xxx/extracted/
   ✅ Rekursiv nach weiteren ingestierbaren Dateien suchen
   ✅ Neue Jobs für entpackte Dateien erstellen

4. Ingestion starten
   ✅ Text-Dokumente: Sofortige Verarbeitung
   ✅ Archive: Nach Extraktion verarbeiten
   ✅ Alles async/parallel
```

---

## ❌ **IST-Workflow (Aktueller Code)**

### Was FUNKTIONIERT:
```python
# 1. Directory Scan (Lines 395-475)
✅ os.walk() findet Dateien rekursiv
✅ Extension-Filter funktioniert
✅ Hardening-Limits aktiv (MAX_FILES, MAX_SIZE)
✅ Timeout-Protection für Network Drives

# 2. Job Creation (Lines 300-340)
✅ Smart Chunking (size-aware)
✅ Jobs werden erstellt (job_id generiert)
✅ Chunk-Statistiken geloggt

# 3. Processing (Lines 1650-1750)
✅ process_documents_batch() verarbeitet Dateien
✅ UDS3 SAGA Orchestrator schreibt in 4 DBs
✅ Embeddings werden generiert (GPU)
✅ Neo4j Graphen werden erstellt
```

### Was FEHLT:
```python
# ❌ 1. DATEIEN WERDEN NICHT VERSCHOBEN!
#    - Dateien bleiben im Original-Verzeichnis
#    - Keine Kopie nach data/uploads/
#    - process_documents_batch() liest direkt aus Original-Pfad

# ❌ 2. KEINE ARCHIVE-UNTERSTÜTZUNG!
#    - .zip, .rar, .7z NICHT in supported_extensions
#    - Kein Entpack-Code vorhanden
#    - Keine rekursive Extraktion

# ❌ 3. KEINE ARCHIVE-VERARBEITUNG!
#    - Kein zipfile.ZipFile() Import
#    - Keine extract() Logik
#    - Keine Job-Erstellung für entpackte Dateien
```

---

## 📊 **Code-Analyse: Aktueller Ablauf**

### DirectoryScanJob.scan_and_create_jobs() (Lines 265-375)
```python
async def scan_and_create_jobs(self):
    # Phase 1: Scan (✅ FUNKTIONIERT)
    file_paths = await self._scan_directory_async()
    # → Gibt Liste von ABSOLUTEN Pfaden zurück (im Original-Verzeichnis!)
    
    # Phase 2: Smart Chunking (✅ FUNKTIONIERT)
    file_chunks = self._create_smart_chunks(file_paths)
    
    # Phase 3: Job Creation (✅ FUNKTIONIERT)
    for chunk in file_chunks:
        upload_job_id = jm.create_job(len(chunk), temp_directory=None, ...)
        # ❌ temp_directory=None → KEINE Datei-Verschiebung!
        
        # Background Processing starten
        def process_chunk_sync(job_id, file_paths, ...):
            loop.run_until_complete(process_documents_batch(job_id, file_paths, None))
            # ❌ file_paths zeigen auf ORIGINAL-Verzeichnis!
            # ❌ Keine Verschiebung nach data/uploads/
```

### process_documents_batch() (Lines 1650-1750)
```python
async def process_documents_batch(job_id, file_paths, temp_dir):
    # ❌ temp_dir ist None (von DirectoryScanJob)
    # ❌ Dateien werden NICHT verschoben
    # ❌ Liest direkt aus Original-Pfaden
    
    tasks = []
    for file_path in file_paths:
        # Verarbeitet Datei am Original-Ort
        task = process_single_document(file_path, jm, job_id)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # ❌ Keine Verschiebung nach data/uploads/
    # ❌ Keine Archive-Extraktion
```

---

## 🔍 **Vergleich: /upload/files vs /upload/directory**

### POST /upload/files (Lines 1795-1870) ✅ FUNKTIONIERT KORREKT
```python
async def upload_files(files: List[UploadFile]):
    # 1. Erstellt temp_dir
    temp_dir = Path("data/uploads") / f"job_{temp_job_id}_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Verschiebt Dateien (streaming)
    for file in files:
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as f:
            while chunk := await file.read(65536):
                f.write(chunk)  # ✅ DATEIEN WERDEN VERSCHOBEN!
        file_paths.append(str(file_path))
    
    # 3. Background Processing
    job_id = jm.create_job(len(files), temp_directory=str(temp_dir))
    # ✅ temp_directory wird übergeben!
    
    # 4. Cleanup nach Erfolg
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
        # ✅ CLEANUP FUNKTIONIERT!
```

### POST /upload/directory (Lines 1950-2015) ❌ FEHLERHAFT
```python
async def upload_directory(directory_path: str):
    # 1. Erstellt Scan Job
    scan_job = DirectoryScanJob(scan_job_id, directory_path, ...)
    
    # 2. Submitted to ThreadPool
    io_executor.submit(run_scan_in_new_loop)
    
    # ❌ KEINE Datei-Verschiebung!
    # ❌ KEINE temp_dir Erstellung!
    # ❌ process_documents_batch() bekommt temp_dir=None!
    
    # ❌ Dateien bleiben im Original-Verzeichnis
    # ❌ Kein Cleanup möglich (Original-Dateien dürfen nicht gelöscht werden!)
```

---

## 🎯 **Benötigtes Redesign**

### 1. Datei-Verschiebung implementieren
```python
async def scan_and_create_jobs(self):
    # Phase 1: Scan (✅ bleibt)
    file_paths = await self._scan_directory_async()
    
    # 🆕 Phase 2: Dateien verschieben
    temp_dir = Path("data/uploads") / f"scan_{self.scan_job_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    moved_paths = []
    for file_path in file_paths:
        dest_path = temp_dir / Path(file_path).name
        shutil.copy2(file_path, dest_path)  # ✅ Kopieren (nicht verschieben!)
        moved_paths.append(str(dest_path))
    
    # Phase 3: Archive erkennen & entpacken
    final_paths = []
    for path in moved_paths:
        if Path(path).suffix.lower() in ['.zip', '.rar', '.7z']:
            extracted = await self._extract_archive(path, temp_dir)
            final_paths.extend(extracted)  # ✅ Entpackte Dateien hinzufügen
        else:
            final_paths.append(path)  # ✅ Normale Dateien
    
    # Phase 4: Smart Chunking mit VERSCHOBENEN Pfaden
    file_chunks = self._create_smart_chunks(final_paths)
    
    # Phase 5: Job Creation mit temp_directory
    for chunk in file_chunks:
        upload_job_id = jm.create_job(
            len(chunk), 
            temp_directory=str(temp_dir),  # ✅ WICHTIG!
            scan_job_id=self.scan_job_id
        )
        # ✅ Jetzt funktioniert Cleanup nach Erfolg!
```

### 2. Archive-Extraktion implementieren
```python
async def _extract_archive(self, archive_path: str, temp_dir: Path) -> List[str]:
    """
    Entpackt Archive und findet ingestierbare Dateien
    
    Returns:
        Liste von absoluten Pfaden zu extrahierten Dateien
    """
    import zipfile
    import tarfile
    import rarfile  # pip install rarfile
    
    extracted_files = []
    extract_dir = temp_dir / "extracted" / Path(archive_path).stem
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    suffix = Path(archive_path).suffix.lower()
    
    try:
        # ZIP Archive
        if suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        
        # RAR Archive
        elif suffix == '.rar':
            with rarfile.RarFile(archive_path, 'r') as rar_ref:
                rar_ref.extractall(extract_dir)
        
        # TAR Archive
        elif suffix in ['.tar', '.tar.gz', '.tgz']:
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_dir)
        
        # 7z Archive
        elif suffix == '.7z':
            import py7zr  # pip install py7zr
            with py7zr.SevenZipFile(archive_path, 'r') as z:
                z.extractall(extract_dir)
        
        logger.info(f"📦 Extracted archive: {archive_path} → {extract_dir}")
        
        # Rekursiv nach ingestierbaren Dateien suchen
        for root, _, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if Path(file).suffix.lower() in self.supported_extensions:
                    extracted_files.append(file_path)
        
        logger.info(f"✅ Found {len(extracted_files)} files in archive")
        return extracted_files
        
    except Exception as e:
        logger.error(f"❌ Failed to extract archive {archive_path}: {e}")
        return []
```

### 3. supported_extensions erweitern
```python
self.supported_extensions = supported_extensions or {
    # Text-Dokumente
    '.pdf', '.doc', '.docx', '.odt', '.rtf',
    '.txt', '.md', '.markdown',
    
    # Strukturierte Daten
    '.json', '.xml', '.yaml', '.yml',
    '.csv', '.xlsx', '.xls',
    
    # Web-Formate
    '.html', '.htm',
    
    # 🆕 Archive (werden entpackt!)
    '.zip', '.rar', '.7z',
    '.tar', '.tar.gz', '.tgz',
}
```

---

## 📋 **Test-Ergebnisse (14.10.2025)**

### Test 1: Lokales Verzeichnis (C:\temp\test_scan)
```
Dateien: file1.txt, file2.pdf, file3.docx
Scan: ✅ Erfolgreich (3 files found)
Processing: ✅ Erfolgreich (SAGA completed)
Datei-Verschiebung: ❌ FEHLT (Dateien noch in C:\temp\test_scan)
Cleanup: ❌ NICHT MÖGLICH (Original-Dateien)

Status: ✅ FUNKTIONIERT (aber keine Datei-Verschiebung)
```

### Test 2: Network Drive (Y:\data\00_eu lex)
```
Dateien: 3 ZIP files (7.7 GB)
Scan: ⏸️ HÄNGT bei os.walk() (Network Drive Issue)
Timeout: ✅ FUNKTIONIERT (300s Protection)
Archive-Extraktion: ❌ NICHT IMPLEMENTIERT

Status: ❌ FUNKTIONIERT NICHT (Network Drive + Keine Archive-Unterstützung)
```

---

## 🚀 **Implementierungs-Prioritäten**

### Priority 1: KRITISCH (Blocker) 🔥
1. ✅ **Datei-Verschiebung** nach data/uploads/
   - Kopieren (nicht verschieben!) der gescannten Dateien
   - temp_directory an process_documents_batch() übergeben
   - Cleanup nach Erfolg ermöglichen

2. ✅ **Archive-Extraktion**
   - .zip, .rar, .7z, .tar.gz Support
   - Rekursive Suche in entpackten Inhalten
   - Neue Jobs für entpackte Dateien

### Priority 2: WICHTIG (Performance) ⚡
3. ✅ **Network Drive Optimization**
   - Timeout-Protection (✅ IMPLEMENTIERT)
   - Alternative Scan-Methode (glob.glob()?)
   - SMB/CIFS Tuning Empfehlungen

4. ✅ **Error Handling**
   - Teilweise fehlgeschlagene Scans
   - Korrupte Archive
   - Permission Errors

### Priority 3: NICE-TO-HAVE (Features) 💡
5. ⏸️ **Intelligente Archive-Erkennung**
   - MIME-Type Detection (statt nur Extension)
   - Verschachtelte Archive (Archive in Archives)
   - Passwort-geschützte Archive

6. ⏸️ **Fortschritts-Tracking**
   - Real-Time WebSocket Updates
   - Extracted Files Counter
   - Processing Progress per Archive

---

## 🎯 **Zusammenfassung**

### Problem:
- ❌ **Dateien werden NICHT verschoben** (bleiben im Original-Verzeichnis)
- ❌ **Archive werden NICHT entpackt** (keine .zip/.rar/.7z Support)
- ❌ **Network Drives hängen** bei os.walk() (aber Timeout-Protection aktiv)

### Lösung:
1. **Datei-Verschiebung** implementieren (shutil.copy2 nach data/uploads/)
2. **Archive-Extraktion** implementieren (zipfile, rarfile, py7zr)
3. **Rekursive Job-Erstellung** für entpackte Dateien

### Aufwand:
- **Phase 1 (Datei-Verschiebung):** ~50 Lines, 30 Min
- **Phase 2 (Archive-Extraktion):** ~150 Lines, 2 Std
- **Phase 3 (Testing):** ~1 Std

**Total:** ~3-4 Stunden Implementierung

---

## 📝 **Nächste Schritte**

**Option A: Minimales Redesign (SCHNELL)**
```python
# 1. Datei-Verschiebung hinzufügen (30 Min)
# 2. temp_directory übergeben (5 Min)
# 3. Test mit lokalem Verzeichnis (10 Min)
# → Network Drive & Archive Support SPÄTER
```

**Option B: Komplettes Redesign (SAUBER)**
```python
# 1. Datei-Verschiebung + Archive-Extraktion (2 Std)
# 2. Rekursive Job-Erstellung (30 Min)
# 3. Network Drive Optimierung (30 Min)
# 4. Comprehensive Testing (1 Std)
# → VOLLSTÄNDIGE Implementierung der SOLL-Architektur
```

**Empfehlung:** **Option B** (Komplettes Redesign)
- Einmalig korrekt implementieren
- Vermeidet technische Schulden
- Erfüllt alle User-Anforderungen
- Zeitaufwand akzeptabel (~4 Std)

---

**Autor:** GitHub Copilot  
**Datum:** 14. Oktober 2025, 14:20 Uhr  
**Status:** 🔴 **WORKFLOW FEHLERHAFT - Redesign erforderlich**
