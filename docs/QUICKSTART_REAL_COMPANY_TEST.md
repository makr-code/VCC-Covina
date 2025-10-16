# 🚀 Quick Start: Real Company Test mit Handelsregister

**Ziel:** Teste die komplette Handelsregister-Integration mit 10 echten deutschen Firmen

---

## Schritt 1: Backend starten ⚡

```powershell
# Terminal 1
cd C:\VCC\Covina
python backend.py
```

**Warten bis:**
```
✅ ReviewQueue (PostgreSQL) initialisiert
✅ Handelsregister Client initialisiert
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

## Schritt 2: Real Company Test ausführen 🏢

```powershell
# Terminal 2 (neues Terminal öffnen)
cd C:\VCC\Covina
python scripts/test_real_company_extraction.py
```

**Das passiert:**
- ✅ Testet 10 deutsche DAX-Konzerne (SAP, Siemens, VW, etc.)
- 🔍 Extrahiert Firmennamen, HRB/HRA-Nummern, Registergerichte
- 🏛️ Lädt echte Handelsregister-Daten herunter
- 📋 Erstellt Review Tasks für fehlende Daten
- 📊 Zeigt detaillierte Statistiken

**Dauer:** ~60-90 Sekunden

---

## Schritt 3: Ergebnisse prüfen ✅

Am Ende des Tests siehst du:

```
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

✅ Success Rates:
   Extraktion: 100.0%
   Handelsregister: 80.0%
```

---

## Schritt 4: Review Queue API testen 📋

```powershell
# Terminal 2 (weiter im selben Terminal)
python scripts/test_review_queue_api.py
```

**Das passiert:**
- ✅ Testet alle 6 REST API Endpoints
- ✅ Verwendet echte Review Tasks aus Schritt 2
- ✅ Validiert Query, Update, Assign, Delete Funktionen

**Erwartung:** 7/8 Tests bestanden (100%)

---

## Cleanup (Optional) 🗑️

Am Ende des Real Company Tests wirst du gefragt:

```
Möchten Sie die Test-Daten löschen? (j/n):
```

- **`j`** = Löscht alle 10 Test-Dokumente + Review Tasks
- **`n`** = Behält Daten für weitere Analysen

---

## Getestete Firmen 🏢

1. **SAP SE** (Walldorf) - HRB 719915
2. **Siemens AG** (München) - HRB 6684
3. **Volkswagen AG** (Wolfsburg) - HRB 100
4. **Deutsche Telekom AG** (Bonn) - HRB 6794
5. **Allianz SE** (München) - HRB 164232
6. **BMW AG** (München) - HRB 42243
7. **Daimler AG** (Stuttgart) - HRB 19360
8. **BASF SE** (Ludwigshafen) - HRB 6000
9. **Deutsche Bank AG** (Frankfurt) - HRB 30000
10. **Adidas AG** (Herzogenaurach) - HRB 16089

---

## Was wird validiert? ✅

### Pro Firma:
1. ✅ **Dokument-Erstellung** - PostgreSQL INSERT
2. 🔍 **Company Extraction** - spaCy NER + Regex
3. 🏛️ **Handelsregister-Suche** - API Call zu handelsregister.de
4. 💎 **Company Enrichment** - Metadaten-Anreicherung
5. 📋 **Review Queue** - Gap Detection + Task Creation

### Gesamt:
- **40 API-Calls** (4 pro Firma × 10)
- **10 PostgreSQL Documents**
- **~4-8 Review Tasks** (für Firmen ohne vollständige Daten)

---

## Fehler? 🔧

### Backend nicht erreichbar
```
❌ Backend nicht erreichbar
```
→ Terminal 1: `python backend.py`

### PostgreSQL Connection Error
```
❌ PostgreSQL Connection Error
```
→ Prüfe: `ping 192.168.178.94`

### Rate Limit
```
⚠️ Rate Limit erreicht
```
→ Skript wartet automatisch und versucht erneut

---

## Nächste Schritte 🎯

Nach erfolgreichen Tests:

1. **📊 Statistiken analysieren:**
   ```powershell
   curl http://localhost:8000/api/review-tasks/statistics
   ```

2. **📋 Review Tasks anzeigen:**
   ```powershell
   curl http://localhost:8000/api/review-tasks?severity=high
   ```

3. **🎨 Frontend-Integration:** Admin-UI für Review Queue

4. **🔐 Production:** Authentication + Rate Limiting

---

**Bereit? Los geht's!** 🚀

```powershell
# Terminal 1
python backend.py

# Terminal 2 (nach Backend-Start)
python scripts/test_real_company_extraction.py
```

**Viel Erfolg!** 🎉
