# Covina Backend Analyse
**Datum:** 17. Oktober 2025  
**Status:** Analyse der Backend-Dateien

---

## 📊 Übersicht der Backend-Dateien

### 1. `backend.py` → **INGESTION BACKEND** (Port 45679)

**Rolle:** Upload & Processing Backend  
**Port:** 45679 (Standard)  
**Größe:** 9,181 Zeilen  
**Haupt-Features:**
- ✅ **Datei-Upload** (multipart/form-data)
- ✅ **UDS3 Integration** (4 Datenbanken: PostgreSQL, CouchDB, ChromaDB, Neo4j)
- ✅ **Worker Pools** (36 I/O Threads, 36 CPU Processes)
- ✅ **Job Management** (Persistent Jobs mit SQLite)
- ✅ **WebSocket** (Real-Time Job Updates auf /ws/jobs)
- ✅ **Auto-Processing** (Callback System für Auto-Ingestion)
- ✅ **SAGA Orchestrator** (Polyglot Persistence)
- ✅ **Process Mining** (Petri Nets, Conformance Checking)

**Wichtige Endpoints:**
```
POST   /upload/files          # File Upload (Multipart)
GET    /jobs/{job_id}         # Job Status
GET    /jobs/{job_id}/files   # Job Files
WS     /ws/jobs               # WebSocket Real-Time Updates
POST   /admin/process-mining  # Process Mining Features
```

**Bezeichnung in Doku:**
- "Ingestion Backend"
- "Upload Backend"
- "Processing Backend"

---

### 2. `covina_backend.py` → **MAIN BACKEND** (Port 45678)

**Rolle:** Query & Management Backend  
**Port:** 45678 (Standard)  
**Größe:** 1,735 Zeilen  
**Haupt-Features:**
- ✅ **Query APIs** (PostgreSQL Full-Text, ChromaDB Semantic Search)
- ✅ **DSGVO Compliance** (Right to Access, Right to Erasure)
- ✅ **Review Queue** (Task Management)
- ✅ **Gap Detection** (Knowledge Gap Analysis)
- ✅ **Compliance Service** (DSGVO, HGB, GoBD Checks)
- ✅ **Golden Datasets** (Relational + Graph Patterns)
- ✅ **Governance Policies** (Retention, Access Control, etc.)
- ✅ **Handelsregister API** (Geplant)

**Wichtige Endpoints:**
```
GET    /query/documents           # Full-Text Search
GET    /query/semantic            # Semantic Search (ChromaDB)
GET    /gaps/detect               # Gap Detection
GET    /review-queue              # Review Tasks
POST   /compliance/check          # Compliance Check
GET    /golden-dataset            # Golden Datasets
GET    /graph-golden-dataset      # Graph Patterns
GET    /governance/policies       # Governance Policies
```

**Bezeichnung in Doku:**
- "Main Backend"
- "Query Backend"
- "Management Backend"

---

## 🔄 Empfohlene Umbenennung

### Problem:
- `backend.py` ist NICHT das Main Backend (trotz Namen!)
- `covina_backend.py` ist das EIGENTLICHE Main Backend
- Verwirrende Namensgebung!

### Lösung:

| Alte Datei | Neue Datei | Port | Rolle |
|------------|------------|------|-------|
| `backend.py` | `ingestion_backend.py` | 45679 | Upload & Processing |
| `covina_backend.py` | `main_backend.py` | 45678 | Query & Management |

---

## 📝 Notwendige Änderungen

### 1. Datei-Umbenennung

```bash
# Option 1: Git mv (preserves history)
git mv backend.py ingestion_backend.py
git mv covina_backend.py main_backend.py

# Option 2: Manuell (Windows)
Rename-Item backend.py ingestion_backend.py
Rename-Item covina_backend.py main_backend.py
```

### 2. Import-Anpassungen

**Dateien die `backend.py` importieren:**
- `scripts/start_services.ps1`
- `scripts/deploy_production.ps1`
- `scripts/stop_services.ps1`
- Eventuell Frontend-Code

**Suche nach Referenzen:**
```powershell
Get-ChildItem -Recurse -Include *.py,*.ps1,*.md | Select-String "backend.py"
```

### 3. Dokumentations-Updates

**Dateien zum Aktualisieren:**
- `.github/copilot-instructions.md`
- `README.md`
- `docs/*.md`
- `admin_tools/README.md`

---

## 🎯 Empfehlung

**JETZT umbenennen:**
- ✅ Klare Trennung der Rollen
- ✅ Konsistente Namensgebung
- ✅ Bessere Wartbarkeit
- ✅ Vermeidung von Verwirrung

**ODER später umbenennen:**
- ⚠️ Weiter mit aktuellen Namen arbeiten
- ⚠️ In Doku klar dokumentieren
- ⚠️ Später in v4.x umbenennen

---

## 📌 Aktuelle Situation (Ohne Umbenennung)

**Wenn wir NICHT umbenennen:**

1. **Dokumentation schärfen:**
   - Überall explizit "backend.py (Ingestion)" schreiben
   - Überall explizit "covina_backend.py (Main)" schreiben

2. **Kommentare in Code:**
   ```python
   # backend.py - INGESTION BACKEND (Port 45679)
   # covina_backend.py - MAIN BACKEND (Port 45678)
   ```

3. **Admin Tools anpassen:**
   - Launcher zeigt beide Backends an
   - Klare Bezeichnung in UI

---

## ✅ Meine Empfehlung

**UMBENENNEN ist besser!**

**Grund:**
- Einmalige Arbeit (30 Minuten)
- Langfristig weniger Verwirrung
- Code wird selbst-dokumentierend
- Neue Entwickler verstehen sofort die Struktur

**Vorgehen:**
1. Git mv für History Preservation
2. Import-Updates (10-15 Dateien)
3. Doku-Updates (5-10 Dateien)
4. Commit: "refactor: Rename backends for clarity (backend.py → ingestion_backend.py, covina_backend.py → main_backend.py)"

**Möchten Sie die Umbenennung durchführen?**
