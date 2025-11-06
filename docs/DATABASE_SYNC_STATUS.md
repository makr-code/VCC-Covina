# Database Inventory Status - 30. Oktober 2025, 15:12 Uhr

## ✅ Alle 4 Datenbanken ONLINE und bereit!

### 1. PostgreSQL (Relational Master) ✅
- **Host:** 192.168.178.94:5432
- **Database:** postgres
- **Dokumente:** 168,454
- **Sample:** Y:\data\12_ovg_ag_brandenburg_gerichtsentscheidungen\markdown\OVG_4_E_4_21_1.md
- **Status:** ✅ Connected und produktiv

### 2. CouchDB (Document Store) ✅
- **Host:** 192.168.178.94:32770 (korrekt aus config_local.py)
- **Version:** 3.5.0
- **Auth:** couchdb/couchdb
- **Database 'covina':** Wird bei erstem Upload erstellt
- **Test:** 10/10 Dokumente erfolgreich hochgeladen
- **Status:** ✅ Connected und bereit für Full Sync

### 3. Neo4j (Knowledge Graph) ✅
- **Host:** bolt://192.168.178.94:7687
- **Auth:** neo4j/v3f3b1d7
- **Total Nodes:** 162,520
  - Document: 144,577
  - Entity: 16,514
  - LegalConcept: 1,369
  - Authority: 24
  - LegalDomain: 23
- **Total Relations:** 184,867
  - BELONGS_TO: 163,816
  - MENTIONS: 1,666 (aus NLP Phase L4)
  - REFERENCES_AUTHORITY: 25
  - CITES: 5
- **Status:** ✅ Connected mit NLP-Daten

### 4. ChromaDB (Vector Store) ✅
- **Host:** 192.168.178.94:8000
- **API Version:** v2 (nicht v1!)
- **Heartbeat:** ✅ Running
- **Status:** ✅ Connected
- **Note:** Für Collection-Details ChromaDB Python Client verwenden

---

## 📋 Pipeline Ready - Next Steps

### Option A: Full Database Sync (Empfohlen)
```powershell
python -m ingestion.database_sync_pipeline
```
**Umfang:**
- PostgreSQL → CouchDB (168k docs, ~30-60 Min)
- NLP Extraction (3,618 files, ~70 Min)
- NLP → Neo4j (760k entities, ~30 Min)
- ChromaDB Verification

**Total ETA:** ~2-3 Stunden

### Option B: Nur CouchDB Sync
```powershell
python -m ingestion.database_sync_pipeline --skip-nlp --skip-neo4j
```
**Umfang:**
- PostgreSQL → CouchDB (168k docs)
- ChromaDB Verification only

**ETA:** ~30-60 Min

### Option C: Nur NLP Pipeline
```powershell
python -m ingestion.database_sync_pipeline --skip-couchdb
```
**Umfang:**
- NLP Extraction (3,618 files)
- NLP → Neo4j (760k entities)
- ChromaDB Verification

**ETA:** ~100 Min

---

## 🔍 Port-Konfiguration aus UDS3 config_local.py

**Korrekte Ports (verifiziert):**
- PostgreSQL: 5432 ✅
- CouchDB: **32770** (nicht 32931!) ✅
- Neo4j: 7687 ✅
- ChromaDB: 8000 (v2 API) ✅

**Credentials:**
- PostgreSQL: postgres/postgres
- CouchDB: couchdb/couchdb
- Neo4j: neo4j/v3f3b1d7
- ChromaDB: keine Auth

---

## 📊 Erwartete Ergebnisse nach Full Sync

### CouchDB
- **Dokumente:** 168,454 (full content von Y:\data\)
- **Größe:** ~500 MB - 1 GB (geschätzt)
- **Features:** Full-Text Search, Revisions, Attachments

### Neo4j (nach NLP)
- **LegalConcept Nodes:** ~1,400 (aktuell) → ~50,000 (nach Full NLP)
- **MENTIONS Relations:** 1,666 → ~600,000
- **CITES Relations:** 5 → ~5,000
- **REFERENCES_AUTHORITY:** 25 → ~3,000

### ChromaDB
- **Aktuelle Vektoren:** Unknown (v2 API Client nötig)
- **Nach Sync:** Verification only (kein neuer Upload in Pipeline)

---

## 🎯 Empfehlung

**START:** Option A (Full Database Sync)

**Grund:**
- Einmalige Ausführung synchronisiert alle Datenbanken
- Progress-Tracking in Pipeline integriert
- Error Recovery vorhanden
- Alle Daten auf einheitlichen Stand

**Command:**
```powershell
python -m ingestion.database_sync_pipeline
```

**Monitoring:**
- PostgreSQL → CouchDB: Progress alle 100 docs
- NLP Extraction: Progress alle 100 files
- Neo4j Persistence: Checkpoint alle 1000 docs

**Bei Fragen oder Problemen:** Pipeline kann jederzeit gestoppt und mit `--skip-*` Flags fortgesetzt werden.
