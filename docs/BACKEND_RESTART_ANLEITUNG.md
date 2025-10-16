# Backend Neustart-Anleitung

## Problem gelöst! ✅

Die ReviewQueue wurde nicht initialisiert, weil die Bedingung zu restriktiv war.

**Änderung in backend.py (Zeile 383-395):**
- ❌ Alt: ReviewQueue nur initialisieren wenn `job_manager.relational_backend.update_company_metadata` existiert
- ✅ Neu: ReviewQueue **immer** initialisieren mit dediziertem PostgreSQL-Backend

## Nächste Schritte

### 1. Backend neu starten

**Im Terminal wo Backend läuft:**
```powershell
# Stoppe Backend mit Ctrl+C
# Dann neu starten:
python backend.py
```

**Erwartete Ausgabe:**
```
✅ PostgreSQL Backend initialisiert: 192.168.178.94:5432
✅ PostgreSQL ReviewQueue verfügbar
✅ PostgreSQL ReviewQueue initialisiert (dediziertes Backend)
✅ Handelsregister Service initialisiert
```

### 2. Connection-Test nochmal ausführen

```powershell
python scripts/test_backend_connection.py
```

**Erwartetes Ergebnis:**
- ✅ Health Endpoint (200 OK)
- ✅ Database Stats (200 OK) - sollte jetzt funktionieren
- ✅ Review Queue Statistics (200 OK) - **NEU VERFÜGBAR!**
- ✅ CORS Headers (405 Method Not Allowed - OK)

**Erwartung:** 4/4 Tests bestanden ✅

### 3. Review Queue testen

```powershell
curl http://127.0.0.1:45678/api/review-tasks/statistics | python -m json.tool
```

**Erwartete Antwort:**
```json
{
  "total_tasks": 0,
  "by_status": {},
  "by_severity": {},
  "by_gap_type": {},
  "avg_resolution_time_hours": null
}
```

### 4. Real Company Test ausführen

Nach erfolgreichem Backend-Neustart:

```powershell
python scripts/test_real_company_extraction.py
```

Dies wird:
- 10 deutsche DAX-Firmen testen
- Handelsregister-Daten abrufen (HRA/HRB)
- Review Tasks erstellen für fehlende Daten
- Statistiken ausgeben

## Technische Details

**Was wurde geändert:**

```python
# NEU: Direkte PostgreSQL-Backend-Erstellung
from database.database_api_postgresql import PostgreSQLRelationalBackend

pg_backend = PostgreSQLRelationalBackend(POSTGRES_CONFIG)
job_manager.review_queue_postgres = ReviewQueue(pg_backend)
```

**Warum das funktioniert:**
- PostgreSQL-Backend wird dediziert für ReviewQueue erstellt
- Keine Abhängigkeit von `job_manager.relational_backend`
- ReviewQueue nutzt POSTGRES_CONFIG (192.168.178.94:5432)
- Tabelle `review_tasks` existiert bereits in PostgreSQL

## Troubleshooting

Falls Backend nicht startet:

**Fehler:** `ImportError: cannot import name 'PostgreSQLRelationalBackend'`
**Lösung:** Datei `database/database_api_postgresql.py` fehlt oder fehlerhaft

**Fehler:** `Connection refused to PostgreSQL`
**Lösung:** PostgreSQL-Server prüfen (läuft auf 192.168.178.94:5432)

**Fehler:** `Table 'review_tasks' does not exist`
**Lösung:** Migrations-Script ausführen (erstellt Tabellen automatisch)

## Status nach Neustart

✅ Backend erreichbar (http://127.0.0.1:45678)
✅ PostgreSQL verbunden (1.897 Dokumente)
✅ Review Queue initialisiert (**NEU!**)
✅ Handelsregister Service verfügbar
✅ Mail Service konfiguriert

---

**Bereit für Real Company Test!** 🚀
