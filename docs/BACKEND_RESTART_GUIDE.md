# Backend Restart & Re-Ingestion Guide

**Datum:** 09.10.2025  
**Kontext:** Nach CouchDB + ChromaDB API-Fixes  
**Status:** UDS3 Package neu installiert, Backend-Neustart erforderlich

---

## ✅ Abgeschlossene Schritte

1. **CouchDB API-Fix** (backend.py Line 2777)
   - `create_document(doc_id=..., data=...)` → `create_document(doc=..., doc_id=...)`
   - ✅ Implementiert

2. **ChromaDB API-Fix** (database_api_chromadb_remote.py Line 798)
   - `add_document()` Methode hinzugefügt (Wrapper um `add_vectors()`)
   - ✅ Implementiert

3. **UDS3 Package Neuinstallation**
   - `pip install -e C:\VCC\uds3 --force-reinstall --no-deps`
   - ✅ Erfolgreich (uds3-1.0.0)

---

## 🚀 Nächste Schritte (JETZT DURCHFÜHREN)

### Schritt 1: Backend neu starten

**Terminal:** Python Terminal (wo Backend aktuell läuft)

```bash
# 1. Stoppe aktuelles Backend
CTRL + C

# 2. Starte Backend neu
python backend.py
```

**Expected Output:**
```
✅ UDS3 Framework mit Quality & Security Module verfügbar
✅ UDS3 DSGVO Framework verfügbar
✅ UDS3 SAGA Framework verfügbar
✅ UDS3 Relations Framework verfügbar
✅ UDS3 Vector Database (ChromaDB Remote HTTP Client 192.168.178.94:8000) verfügbar
✅ UDS3 Polyglot Integration verfügbar

# CouchDB Backend Initialisierung
✅ CouchDB Backend initialisiert: 192.168.178.94:32931

# ChromaDB Backend Initialisierung
ChromaDB Remote Client initialized: http://192.168.178.94:8000

🚀 Covina Backend bereit!
INFO:     Uvicorn running on http://0.0.0.0:45678
```

**Validation:**
- ✅ KEINE Fehler beim Import von UDS3-Modulen
- ✅ CouchDB Backend erfolgreich verbunden
- ✅ ChromaDB Remote Client initialisiert
- ✅ Backend läuft auf Port 45678

---

### Schritt 2: Backend Health Check

**Terminal:** Neues PowerShell Terminal

```powershell
curl http://127.0.0.1:45678/health
```

**Expected Output:**
```json
{
  "status": "healthy",
  "active_jobs": 0,
  "mail_configured": true,
  "timestamp": "09.10.2025 HH:MM:SS"
}
```

---

### Schritt 3: Database Stats (vor Re-Ingestion)

```powershell
curl http://127.0.0.1:45678/database/stats
```

**Expected Output (nach Cleanup):**
```json
{
  "total_documents": 0,
  "polyglot_status": {
    "relational_db": {"documents": 0},
    "couchdb": {"documents": 0},
    "chromadb": {"documents": 0},
    "neo4j": {"nodes": 0, "relationships": 0}
  }
}
```

**Validation:**
- ✅ API antwortet (Status 200)
- ✅ Alle Datenbanken leer (nach cleanup)
- ✅ CouchDB-Stats verfügbar (API funktioniert!)

---

### Schritt 4: Re-Ingestion (34 Dokumente)

**WICHTIG:** OHNE cleanup_remote_databases.py danach ausführen!

```powershell
# Batch-Upload Script
.\scripts\batch_upload.ps1 -SourceDir 'Y:\data\00_bund_gesetze_auswahl' -ParallelUploads 5
```

**Expected Output (für JEDES Dokument):**
```
INFO:covina_backend:🔄 Using SAGA-based polyglot operations for document abc123 (5 Steps)
DEBUG:covina_backend:SAGA Step 1/5 - PostgreSQL: Document abc123 inserted
DEBUG:covina_backend:✅ CouchDB: Document abc123 gespeichert (12345 Zeichen)
DEBUG:covina_backend:SAGA Step 3/5 - ChromaDB: 2 Chunks in ChromaDB gespeichert
DEBUG:covina_backend:SAGA Step 4/5 - Neo4j: Document Node created
DEBUG:covina_backend:SAGA Step 5/5 - File System: Document stored locally
INFO:covina_backend:✅ SAGA erfolgreich abgeschlossen für abc123 (5/5 Steps)
```

**KEINE Fehler mehr:**
```
# Diese Fehler sollten NICHT mehr auftreten:
ERROR:covina_backend:❌ SAGA Fehler: CouchDB document insert failed: ...
ERROR:polyglot_integration:❌ Vector DB Error: 'ChromaRemoteVectorBackend' object has no attribute 'add_document'
```

**Erwartete Dauer:**
- 34 Dokumente @ ~2.5 docs/sec = ca. 14 Sekunden
- Mit parallelen Uploads (5 parallel) = ca. 8-10 Sekunden

---

### Schritt 5: Database Stats (nach Re-Ingestion)

```powershell
curl http://127.0.0.1:45678/database/stats
```

**Expected Output:**
```json
{
  "total_documents": 34,
  "polyglot_status": {
    "relational_db": {
      "documents": 34,
      "tables": ["documents"],
      "backend_type": "PostgreSQL"
    },
    "couchdb": {
      "documents": 34,
      "database": "covina_documents",
      "backend_type": "CouchDB"
    },
    "chromadb": {
      "documents": 68,
      "collection": "covina_documents",
      "backend_type": "ChromaDB-Remote"
    },
    "neo4j": {
      "nodes": 34,
      "relationships": 0,
      "backend_type": "Neo4j"
    }
  }
}
```

**Validation:**
- ✅ **PostgreSQL:** 34 Dokumente (SAGA Step 1 funktioniert)
- ✅ **CouchDB:** 34 Dokumente (SAGA Step 2 funktioniert!) → **NEU!**
- ✅ **ChromaDB:** 68 Chunks (SAGA Step 3 funktioniert, Legal-Chunking 2.0!) → **NEU!**
- ✅ **Neo4j:** 34 Nodes (SAGA Step 4 funktioniert)
- ✅ **File System:** 34 Files (SAGA Step 5 funktioniert)

**KRITISCH:**
- **CouchDB MUSS 34 sein** (vorher 0 wegen API-Fehler)
- **ChromaDB MUSS 68 sein** (vorher 0 wegen API-Fehler)

---

### Schritt 6: SAGA Logs validieren

**Terminal:** Suche im Backend-Output nach SAGA-Logs

```powershell
# Suche nach SAGA-Success-Meldungen
# Im Backend-Terminal-Output nach "✅ SAGA erfolgreich abgeschlossen" suchen
```

**Expected für JEDES der 34 Dokumente:**
```
INFO:covina_backend:✅ SAGA erfolgreich abgeschlossen für <document_id> (5/5 Steps)
```

**Count:**
```
# Sollte 34x auftreten (für jedes Dokument)
```

---

### Schritt 7: Job-Historie prüfen

```powershell
curl http://127.0.0.1:45678/jobs
```

**Expected Output:**
```json
[
  {
    "job_id": "<uuid>",
    "status": "completed",
    "file_count": 34,
    "processed_files": 34,
    "error_message": null,
    "created_at": "2025-10-09T...",
    "updated_at": "2025-10-09T..."
  }
]
```

**Validation:**
- ✅ Status: `completed`
- ✅ processed_files: 34 (100% Success-Rate)
- ✅ error_message: `null` (keine Fehler!)

---

### Schritt 8: CouchDB direkt validieren (Optional)

**Futon Web UI:**
```
http://192.168.178.94:5984/_utils/
```

**Oder CLI:**
```powershell
curl http://192.168.178.94:5984/covina_documents/_all_docs
```

**Expected Output:**
```json
{
  "total_rows": 34,
  "offset": 0,
  "rows": [
    {"id": "doc_...", "key": "doc_...", "value": {"rev": "1-..."}},
    ...
  ]
}
```

**Validation:**
- ✅ 34 Dokumente in CouchDB vorhanden
- ✅ Jedes Dokument hat vollständigen Content in Metadaten

---

### Schritt 9: ChromaDB direkt validieren (Optional)

**Python:**
```python
import chromadb
client = chromadb.HttpClient(host="192.168.178.94", port=8000)
collection = client.get_collection("covina_documents")
count = collection.count()
print(f"ChromaDB Chunks: {count}")  # Expected: 68
```

**Expected Output:**
```
ChromaDB Chunks: 68
```

**Validation:**
- ✅ 68 Chunks in ChromaDB vorhanden
- ✅ Legal-Chunking funktioniert (2.0 Chunks/Dokument)

---

## 🎯 Success Criteria (Alle müssen erfüllt sein)

1. ✅ **Backend startet ohne Fehler**
   - Alle UDS3-Module geladen
   - CouchDB Backend verbunden
   - ChromaDB Remote Client initialisiert

2. ✅ **Re-Ingestion erfolgreich**
   - 34/34 Dokumente verarbeitet
   - KEINE API-Fehler (CouchDB/ChromaDB)
   - Alle SAGA-Steps (5/5) erfolgreich

3. ✅ **Database Stats korrekt**
   - PostgreSQL: 34 Dokumente
   - **CouchDB: 34 Dokumente** (war 0!)
   - **ChromaDB: 68 Chunks** (war 0!)
   - Neo4j: 34 Nodes

4. ✅ **SAGA Logs vollständig**
   - 34x "✅ SAGA erfolgreich abgeschlossen (5/5 Steps)"
   - Alle 5 Steps für jedes Dokument erfolgreich

5. ✅ **Job-Status: Completed**
   - processed_files: 34
   - error_message: null

---

## ⚠️ Troubleshooting

### Problem: Backend startet nicht

**Symptom:**
```
ModuleNotFoundError: No module named 'uds3.database.database_api_chromadb_remote'
```

**Lösung:**
```powershell
# UDS3 Package erneut installieren
pip install -e C:\VCC\uds3 --force-reinstall
```

---

### Problem: CouchDB API-Fehler trotz Fix

**Symptom:**
```
ERROR: CouchDBAdapter.create_document() got an unexpected keyword argument 'data'
```

**Lösung:**
```powershell
# 1. Backend stoppen (CTRL+C)
# 2. UDS3 Cache löschen
Remove-Item -Recurse -Force C:\VCC\uds3\__pycache__
Remove-Item -Recurse -Force C:\VCC\uds3\database\__pycache__

# 3. UDS3 neu installieren
pip install -e C:\VCC\uds3 --force-reinstall

# 4. Backend neu starten
python backend.py
```

---

### Problem: ChromaDB API-Fehler trotz Fix

**Symptom:**
```
ERROR: 'ChromaRemoteVectorBackend' object has no attribute 'add_document'
```

**Lösung:**
```powershell
# 1. Prüfe ob add_document() Methode vorhanden ist
python -c "from uds3.database.database_api_chromadb_remote import ChromaRemoteVectorBackend; print(hasattr(ChromaRemoteVectorBackend, 'add_document'))"

# Expected: True

# Falls False:
# 2. UDS3 Cache löschen und neu installieren
Remove-Item -Recurse -Force C:\VCC\uds3\database\__pycache__
pip install -e C:\VCC\uds3 --force-reinstall
```

---

### Problem: Database Stats zeigen noch 0

**Symptom:**
```json
{
  "total_documents": 0,
  "polyglot_status": {
    "couchdb": {"documents": 0},
    "chromadb": {"documents": 0}
  }
}
```

**Prüfung:**
1. War Re-Ingestion erfolgreich? (Job-Status prüfen)
2. Wurden ALLE 34 Dokumente verarbeitet?
3. Gab es SAGA-Fehler im Backend-Log?

**Lösung:**
- Falls Ingestion fehlgeschlagen: Backend-Logs prüfen
- Falls cleanup gelaufen: Re-Ingestion wiederholen (OHNE cleanup!)

---

## 📊 Performance-Metriken

**Expected Performance (nach Re-Ingestion):**

| Metrik | Wert | Status |
|--------|------|--------|
| Total Documents | 34 | ✅ |
| Processing Time | 8-14 Sekunden | ✅ |
| Throughput | 2.4-4.25 docs/sec | ✅ |
| Success Rate | 100% (34/34) | ✅ |
| SAGA Success Rate | 100% (5/5 Steps) | ✅ |
| PostgreSQL Docs | 34 | ✅ |
| CouchDB Docs | 34 | ✅ NEU! |
| ChromaDB Chunks | 68 | ✅ NEU! |
| Neo4j Nodes | 34 | ✅ |

---

## 🔗 Related Documentation

- **API-Fixes:** `docs/API_FIXES_COUCHDB_CHROMADB.md`
- **SAGA Pattern:** `docs/SAGA_5_STEP_COMPLETE.md`
- **Ingestion-Analyse:** `docs/INGESTION_RESULT_34_DOCS.md`

---

**Ready to proceed!** 🚀

Nächster Schritt: **Backend neu starten** (CTRL+C + python backend.py)
