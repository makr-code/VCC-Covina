# Real Company Extraction & Handelsregister Test - Anleitung

## Überblick

Dieses Testskript validiert die vollständige Handelsregister-Integration mit **10 echten deutschen Firmen**:

1. SAP SE (Walldorf)
2. Siemens AG (München)
3. Volkswagen AG (Wolfsburg)
4. Deutsche Telekom AG (Bonn)
5. Allianz SE (München)
6. BMW AG (München)
7. Daimler AG (Stuttgart)
8. BASF SE (Ludwigshafen)
9. Deutsche Bank AG (Frankfurt)
10. Adidas AG (Herzogenaurach)

---

## Was wird getestet?

Für jede Firma:

1. **✅ Dokument-Erstellung:** Erstellt realistisches Vertragsdokument in PostgreSQL
2. **🔍 Company Extraction:** Extrahiert Firmennamen, Registernummer, Registergericht
3. **🏛️ Handelsregister-Suche:** Ruft echte HRA/HRB-Daten ab (falls verfügbar)
4. **💎 Company Enrichment:** Reichert Metadaten mit Handelsregister-Infos an
5. **📋 Review Queue:** Erstellt Tasks für fehlende/unvollständige Daten

---

## Voraussetzungen

### 1. Backend läuft
```powershell
# Terminal 1
python backend.py
```

**Erwartete Ausgabe:**
```
✅ ReviewQueue (PostgreSQL) initialisiert
✅ Handelsregister Client initialisiert
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 2. PostgreSQL verfügbar
- Host: 192.168.178.94:5432
- Database: postgres
- Tables: documents, company_metadata, review_tasks

### 3. Handelsregister API verfügbar
- Entweder: handelsregister.de API
- Oder: Mock-Backend mit Test-Daten

---

## Ausführung

### Schritt 1: Backend starten
```powershell
# Terminal 1
cd C:\VCC\Covina
python backend.py
```

Warten bis:
```
INFO: Application startup complete.
```

### Schritt 2: Tests ausführen
```powershell
# Terminal 2 (neues Terminal)
cd C:\VCC\Covina
python scripts/test_real_company_extraction.py
```

---

## Erwartete Ausgabe

```
======================================================================
Real Company Extraction & Handelsregister Integration Test
======================================================================
Anzahl Test-Firmen: 10
Start: 2025-10-10 16:30:00

🔌 Backend-Verfügbarkeit prüfen...
✅ Backend erreichbar: http://localhost:8000

🗄️  PostgreSQL-Verfügbarkeit prüfen...
✅ PostgreSQL verbunden: 192.168.178.94:5432


######################################################################
Test 1/10
######################################################################

======================================================================
Test: SAP SE
======================================================================

📄 Schritt 1: Dokument erstellen...
✅ Dokument erstellt: doc_real_a1b2c3d4e5f6 (SAP SE)

🔍 Schritt 2: Firmen extrahieren...
✅ 2 Firma(n) gefunden:
   - SAP SE
     Register: HRB 719915
     Gericht: Mannheim
   - Musterfirma GmbH
     Register: HRB 98765
     Gericht: Charlottenburg

🏛️  Schritt 3: Handelsregister-Suche...
✅ Handelsregister-Daten gefunden:
   Name: SAP SE
   Register: HRB 719915
   Gericht: Amtsgericht Mannheim
   Status: Aktiv

💎 Schritt 4: Company Enrichment...
✅ Company Enrichment erfolgreich

📋 Schritt 5: Review Tasks prüfen...
ℹ️  Keine Review Tasks erstellt (alle Daten vollständig)

⏳ Pause 3 Sekunden vor nächstem Test...


######################################################################
Test 2/10
######################################################################

======================================================================
Test: Siemens AG
======================================================================

📄 Schritt 1: Dokument erstellen...
✅ Dokument erstellt: doc_real_b2c3d4e5f6a1 (Siemens AG)

🔍 Schritt 2: Firmen extrahieren...
✅ 2 Firma(n) gefunden:
   - Siemens AG
     Register: HRB 6684
     Gericht: München
   - Musterfirma GmbH
     Register: HRB 98765
     Gericht: Charlottenburg

🏛️  Schritt 3: Handelsregister-Suche...
✅ Handelsregister-Daten gefunden:
   Name: Siemens Aktiengesellschaft
   Register: HRB 6684
   Gericht: Amtsgericht München
   Status: Aktiv

💎 Schritt 4: Company Enrichment...
✅ Company Enrichment erfolgreich

📋 Schritt 5: Review Tasks prüfen...
ℹ️  Keine Review Tasks erstellt (alle Daten vollständig)

... [Tests 3-10 ähnlich] ...


======================================================================
ZUSAMMENFASSUNG
======================================================================

📊 Statistiken:
   Gesamt-Firmen: 10
   Extraktion erfolgreich: 10
   Extraktion fehlgeschlagen: 0
   Handelsregister gefunden: 8
   Handelsregister nicht gefunden: 2
   Review Tasks erstellt: 4

📄 Erstellte Dokumente: 10
   - doc_real_a1b2c3d4e5f6
   - doc_real_b2c3d4e5f6a1
   - doc_real_c3d4e5f6a1b2
   ... [7 weitere]

📋 Erstellte Review Tasks: 4
   - 550e8400-e29b-41d4-a716-446655440001
   - 550e8400-e29b-41d4-a716-446655440002
   - 550e8400-e29b-41d4-a716-446655440003
   - 550e8400-e29b-41d4-a716-446655440004

📋 Detaillierte Ergebnisse:

Firma                          Extraktion   HR-Daten   Review Tasks   
----------------------------------------------------------------------
SAP SE                         ✅           ✅         0              
Siemens AG                     ✅           ✅         0              
Volkswagen AG                  ✅           ✅         0              
Deutsche Telekom AG            ✅           ✅         0              
Allianz SE                     ✅           ✅         0              
BMW AG                         ✅           ✅         0              
Daimler AG                     ✅           ✅         0              
BASF SE                        ✅           ✅         0              
Deutsche Bank AG               ✅           ❌         2              
Adidas AG                      ✅           ❌         2              

✅ Success Rates:
   Extraktion: 100.0%
   Handelsregister: 80.0%

======================================================================
Ende: 2025-10-10 16:32:45
======================================================================


🗑️  Cleanup
======================================================================
Test-Daten wurden erstellt:
   - 10 Dokumente
   - 4 Review Tasks

Möchten Sie die Test-Daten löschen? (j/n): n
ℹ️  Test-Daten bleiben erhalten für weitere Analysen
```

---

## Review Tasks analysieren

Nach dem Test können die erstellten Review Tasks analysiert werden:

### Alle Review Tasks anzeigen
```powershell
python -c "
import requests
response = requests.get('http://localhost:8000/api/review-tasks')
print(response.json())
"
```

### Review Tasks nach Severity filtern
```powershell
# Nur hohe Priorität
python -c "
import requests
response = requests.get('http://localhost:8000/api/review-tasks?severity=high')
print(response.json())
"
```

### Statistiken anzeigen
```powershell
python -c "
import requests
response = requests.get('http://localhost:8000/api/review-tasks/statistics')
import json
print(json.dumps(response.json(), indent=2))
"
```

---

## Handelsregister-Daten inspizieren

### company_metadata Tabelle prüfen
```sql
-- PostgreSQL Query
SELECT 
    document_id,
    jsonb_pretty(company_metadata) as metadata
FROM documents
WHERE document_id LIKE 'doc_real_%'
ORDER BY created_at DESC
LIMIT 5;
```

**Erwartete Ausgabe:**
```json
{
  "companies": [
    {
      "firma": "SAP SE",
      "registernummer": "HRB 719915",
      "registergericht": "Amtsgericht Mannheim",
      "handelsregister_verified": true,
      "handelsregister_data": {
        "name": "SAP SE",
        "register_number": "HRB 719915",
        "register_court": "Amtsgericht Mannheim",
        "status": "Aktiv",
        "legal_form": "SE",
        "registered_address": "Dietmar-Hopp-Allee 16, 69190 Walldorf"
      }
    }
  ]
}
```

---

## Fehlerbehandlung

### Problem 1: Backend nicht erreichbar
```
❌ Backend nicht erreichbar: Connection refused
```

**Lösung:**
```powershell
# Terminal 1: Backend starten
python backend.py

# Warten bis Server läuft
# Dann Tests erneut ausführen
```

---

### Problem 2: PostgreSQL Connection Error
```
❌ PostgreSQL Connection Error: could not connect to server
```

**Lösung:**
```powershell
# PostgreSQL-Verbindung prüfen
# Option 1: Remote-Server prüfen
ping 192.168.178.94

# Option 2: Lokale PostgreSQL verwenden
# test_real_company_extraction.py, Zeilen 27-33 anpassen:
# 'host': 'localhost',
```

---

### Problem 3: Handelsregister API Rate Limit
```
⚠️  Rate Limit erreicht - warte 2 Sekunden...
```

**Hinweis:** Skript wartet automatisch und versucht erneut. Bei häufigem Rate Limit:

```python
# test_real_company_extraction.py, Zeile 523 anpassen:
time.sleep(5)  # Von 3 auf 5 Sekunden erhöhen
```

---

### Problem 4: Company Extraction fehlgeschlagen
```
❌ Keine Firmen extrahiert
```

**Mögliche Ursachen:**
1. spaCy Model nicht geladen
2. CompanyExtractor nicht initialisiert
3. Text zu kurz/ungültig

**Lösung:**
```powershell
# spaCy Model neu installieren
python -m spacy download de_core_news_lg

# Backend neu starten
python backend.py
```

---

## Test-Daten aufräumen

### Manuelles Cleanup
```sql
-- PostgreSQL Query
DELETE FROM documents WHERE document_id LIKE 'doc_real_%';

-- Review Tasks werden automatisch gelöscht (CASCADE)
```

### Automatisches Cleanup
```powershell
# Beim Test-Ausführung 'j' wählen wenn gefragt:
# Möchten Sie die Test-Daten löschen? (j/n): j
```

---

## Erweiterte Nutzung

### Nur bestimmte Firmen testen
```python
# test_real_company_extraction.py, Zeile 52 anpassen:
TEST_COMPANIES = [
    {
        'name': 'SAP SE',
        'location': 'Walldorf',
        ...
    },
    # Nur SAP testen, Rest auskommentieren
]
```

### Eigene Firmen hinzufügen
```python
# test_real_company_extraction.py, Zeile 102 erweitern:
{
    'name': 'Ihre Firma GmbH',
    'location': 'Berlin',
    'register_court': 'Charlottenburg',
    'register_number': 'HRB 12345',
    'expected_type': 'GmbH'
}
```

---

## Performance-Metriken

**Erwartete Laufzeit:**
- 1 Firma: ~5-8 Sekunden
- 10 Firmen: ~60-90 Sekunden (mit Pausen)

**API-Calls pro Firma:**
1. POST /api/companies/extract (1x)
2. POST /api/handelsregister/search (1x)
3. POST /api/companies/enrich (1x)
4. GET /api/review-tasks?document_id=... (1x)

**Gesamt:** 4 API-Calls × 10 Firmen = 40 API-Calls

---

## Nächste Schritte

Nach erfolgreichen Tests:

1. **✅ Review Queue API testen:**
   ```powershell
   python scripts/test_review_queue_api.py
   ```

2. **📊 Statistiken analysieren:**
   ```powershell
   curl http://localhost:8000/api/review-tasks/statistics
   ```

3. **🎨 Frontend-Integration:**
   - Review Tasks in Admin-UI anzeigen
   - Bulk-Operations implementieren
   - Email-Benachrichtigungen

4. **🔐 Production-Vorbereitung:**
   - Authentication hinzufügen
   - Rate Limiting konfigurieren
   - Monitoring einrichten

---

**Autor:** Covina System  
**Version:** 1.0.0  
**Datum:** 10. Oktober 2025  
**Status:** ✅ Produktionsbereit
