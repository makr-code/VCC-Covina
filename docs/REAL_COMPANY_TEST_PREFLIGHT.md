# Real Company Test - Pre-Flight Checklist

## ✅ Voraussetzungen

Bevor du den Real Company Test startest, stelle sicher:

### 1. Backend Status

**Prüfen:**
```powershell
curl http://127.0.0.1:45678/health | python -m json.tool
```

**Erwartete Ausgabe:**
```json
{
  "status": "healthy",
  "active_jobs": 0,
  "mail_configured": true
}
```

❌ Falls Backend nicht läuft:
```powershell
python backend.py
```

**WICHTIG:** Achte auf diese Zeile beim Start:
```
✅ PostgreSQL ReviewQueue initialisiert (dediziertes Backend)
```

Falls diese Zeile **fehlt**, wurde die Review Queue nicht initialisiert!

---

### 2. PostgreSQL Connection

**Prüfen:**
```powershell
python scripts/test_postgres_connection.py
```

**Erwartete Ausgabe:**
```
✅ Verbindung erfolgreich!
✅ PostgreSQL Version: PostgreSQL 18.0 ...
✅ Dokumente in Datenbank: 1897
```

---

### 3. Review Queue API

**Prüfen:**
```powershell
curl http://127.0.0.1:45678/api/review-tasks/statistics
```

**Erwartete Ausgabe:**
```json
{
  "total_tasks": 0,
  "by_status": {},
  "by_severity": {},
  "by_gap_type": {},
  "avg_resolution_time_hours": null
}
```

❌ Falls 503 Error:
```
{"detail":"Review Queue Service nicht verfügbar"}
```

**Lösung:** Backend neu starten (siehe Schritt 1)

---

## 🚀 Test ausführen

### Option 1: Vollautomatischer Test (EMPFOHLEN)

```powershell
.\scripts\run_real_company_test.ps1
```

Dieser PowerShell-Script:
- ✅ Prüft Backend Health
- ✅ Prüft PostgreSQL Connection
- ✅ Prüft Review Queue API
- ✅ Führt Real Company Test aus (10 Firmen)
- ✅ Zeigt finale Statistiken

**Dauer:** 2-5 Minuten

---

### Option 2: Manueller Test

```powershell
python scripts/test_real_company_extraction.py
```

**Was passiert:**

1. **Test-Dokumente erstellen** (10 Firmen)
   - SAP SE, Siemens AG, Volkswagen AG, etc.
   - Dokumente werden in PostgreSQL gespeichert

2. **Company Extraction**
   - spaCy NER erkennt Firmennamen
   - Companies werden in company_metadata gespeichert

3. **Handelsregister API Calls** (40 Requests)
   - 4 Requests pro Firma:
     - HRB search by name
     - HRA search by name
     - HRB search by number
     - HRA search by number

4. **Company Enrichment**
   - Gefundene Daten werden mit company_metadata verknüpft
   - Fehlende Daten werden markiert

5. **Review Queue Integration**
   - Review Tasks werden für fehlende Daten erstellt
   - Tasks in PostgreSQL `review_tasks` Tabelle

**Erwartete Ausgabe:**
```
================================================================================
REAL COMPANY EXTRACTION TEST
================================================================================

[TEST 1/10] SAP SE (Mannheim, HRB 719915)
   ✅ Dokument erstellt: doc_id_123
   ✅ Company extrahiert: SAP SE
   📞 Handelsregister API: 4 Requests
      ✅ HRB search (name): 1 Ergebnisse
      ❌ HRA search (name): 0 Ergebnisse
      ✅ HRB search (number): 1 Ergebnis
      ❌ HRA search (number): 0 Ergebnisse
   ✅ Company enriched: 2/4 Datenquellen erfolgreich
   ✅ Review Task erstellt: review_task_456

[TEST 2/10] Siemens AG ...
...

================================================================================
FINAL STATISTICS
================================================================================
Firmen getestet: 10
Dokumente erstellt: 10
Companies extrahiert: 10
Handelsregister Requests: 40
  - Erfolgreiche Anfragen: ~25-30
  - Fehlgeschlagene Anfragen: ~10-15
Companies enriched: 10
Review Tasks erstellt: ~15-20

Review Queue Statistics:
  Total Tasks: 18
  By Status: {"pending": 18}
  By Severity: {"medium": 10, "high": 8}
  By Gap Type: {"missing_hrb": 8, "missing_hra": 10}

✅ Test erfolgreich abgeschlossen!
```

---

## 📊 Ergebnisse prüfen

### PostgreSQL Queries

**1. Review Tasks anzeigen:**
```sql
SELECT 
    review_id,
    document_id,
    company_id,
    gap_type,
    severity,
    status,
    created_at
FROM review_tasks
ORDER BY created_at DESC
LIMIT 20;
```

**2. Company Metadata:**
```sql
SELECT 
    company_id,
    company_name,
    register_court,
    register_number,
    register_type,
    handelsregister_verified
FROM company_metadata
WHERE company_name IN ('SAP SE', 'Siemens AG', 'Volkswagen AG')
ORDER BY company_name;
```

**3. Dokumente mit Companies:**
```sql
SELECT 
    d.document_id,
    d.file_path,
    d.classification,
    cm.company_name,
    cm.register_number
FROM documents d
LEFT JOIN company_metadata cm ON d.document_id = cm.document_id
WHERE cm.company_name IS NOT NULL
ORDER BY d.created_at DESC
LIMIT 10;
```

---

### REST API Queries

**1. Alle Review Tasks:**
```powershell
curl "http://127.0.0.1:45678/api/review-tasks?limit=10" | python -m json.tool
```

**2. Review Tasks nach Status:**
```powershell
curl "http://127.0.0.1:45678/api/review-tasks?status=pending" | python -m json.tool
```

**3. Review Tasks nach Severity:**
```powershell
curl "http://127.0.0.1:45678/api/review-tasks?severity=high" | python -m json.tool
```

**4. Einzelne Review Task:**
```powershell
curl "http://127.0.0.1:45678/api/review-tasks/{review_id}" | python -m json.tool
```

---

## 🐛 Troubleshooting

### Problem: Backend startet nicht

**Fehler:**
```
ImportError: cannot import name 'PostgreSQLRelationalBackend'
```

**Lösung:**
Datei `database/database_api_postgresql.py` fehlt oder ist fehlerhaft.

---

### Problem: Review Queue nicht verfügbar (503)

**Fehler:**
```
{"detail":"Review Queue Service nicht verfügbar"}
```

**Ursache:**
`job_manager.review_queue_postgres` ist None.

**Lösung:**
Backend neu starten. Achte auf Log-Ausgabe:
```
✅ PostgreSQL ReviewQueue initialisiert (dediziertes Backend)
```

Falls diese Zeile fehlt, wurde die Review Queue nicht initialisiert.

**Debug:**
Prüfe backend.py Zeile 383-395. Die Bedingung sollte sein:
```python
if REVIEW_QUEUE_AVAILABLE:
    try:
        from database.database_api_postgresql import PostgreSQLRelationalBackend
        pg_backend = PostgreSQLRelationalBackend(POSTGRES_CONFIG)
        job_manager = get_job_manager()
        job_manager.review_queue_postgres = ReviewQueue(pg_backend)
```

---

### Problem: Handelsregister API Timeout

**Fehler:**
```
ReadTimeout: HTTPConnectionPool(...): Read timed out. (read timeout=30)
```

**Ursache:**
Handelsregister API antwortet nicht innerhalb von 30 Sekunden.

**Lösung:**
1. Rate Limit einhalten (60 Requests/Stunde)
2. Zwischen Requests warten (min. 2 Sekunden)
3. Retry-Logic nutzen

---

### Problem: PostgreSQL Connection Timeout

**Fehler:**
```
psycopg2.OperationalError: could not connect to server
```

**Ursache:**
PostgreSQL-Server (192.168.178.94:5432) nicht erreichbar.

**Lösung:**
1. Prüfe ob PostgreSQL läuft: `sudo systemctl status postgresql`
2. Prüfe Firewall: `sudo ufw allow 5432/tcp`
3. Prüfe pg_hba.conf für Remote-Access

---

## 📚 Weitere Ressourcen

- **Handelsregister API Docs:** `docs/HANDELSREGISTER_CLIENT.md`
- **Review Queue API Docs:** `docs/REVIEW_QUEUE_API.md`
- **Migration Docs:** `docs/SQLITE_TO_POSTGRES_MIGRATION.md`
- **Backend Restart Guide:** `docs/BACKEND_RESTART_ANLEITUNG.md`

---

## ✅ Erfolgs-Kriterien

Der Test gilt als **erfolgreich**, wenn:

- ✅ Alle 10 Firmen wurden verarbeitet
- ✅ Mindestens 8/10 Dokumente erstellt
- ✅ Mindestens 8/10 Companies extrahiert
- ✅ Mindestens 30/40 Handelsregister-Requests erfolgreich
- ✅ Mindestens 5 Review Tasks erstellt
- ✅ Review Queue API funktioniert

---

**Viel Erfolg! 🚀**
