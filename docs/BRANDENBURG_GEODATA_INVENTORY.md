# Brandenburg Geobroker - WFS-Dienste Bestandsaufnahme

**Datum:** 2025-10-08  
**Status:** Systematische Durchsuchung abgeschlossen

---

## ✅ Verfügbare WFS-Dienste (INTEGRIERT)

###  1. **Verwaltungsgrenzen** (LGB)
- **URL:** `https://isk.geobasis-bb.de/ows/vg_wfs`
- **Provider:** Landesvermessung und Geobasisinformation Brandenburg (LGB)
- **Status:** ✅ Integriert (12 Layer, 2,552 Features)
- **Metadata:** `wfs_metadata_verwaltungsgrenzen.json`

### 2. **Schutzgebiete & Natura 2000** (LfU - INSPIRE)
- **URL:** `https://inspire.brandenburg.de/services/schutzg_wfs`
- **Provider:** Landesamt für Umwelt Brandenburg (LfU)
- **Status:** ✅ Integriert (7 Layer, 1,486 Features)
- **Metadata:** `wfs_metadata_schutzgebiete.json`
- **INSPIRE-konform:** Ja
- **Abdeckung:**
  - Naturschutzgebiete (NSG)
  - Landschaftsschutzgebiete (LSG)
  - Nationalpark, Naturparke, Biosphärenreservate
  - FFH-Gebiete (Natura 2000)
  - Vogelschutzgebiete / SPA (Natura 2000)

### 3. **Gazetteer** (LGB)
- **URL:** `https://isk.geobasis-bb.de/ows/gazetteer_wfs`
- **Provider:** Landesvermessung und Geobasisinformation Brandenburg (LGB)
- **Status:** ✅ Integriert (30 Layer, ~5M Features)
- **Metadata:** `wfs_metadata_gazetteer.json`

### 4. **ATKIS Basis-DLM** (LGB)
- **URL:** `https://isk.geobasis-bb.de/ows/atkisbdlm_nas_wfs`
- **Provider:** Landesvermessung und Geobasisinformation Brandenburg (LGB)
- **Status:** ✅ Integriert (117 Layer, ~3M Features)
- **Metadata:** `wfs_metadata_atkis.json`

### 5. **ALKIS** (LGB)
- **URL:** `https://isk.geobasis-bb.de/ows/alkis_sf_wfs`
- **Provider:** Landesvermessung und Geobasisinformation Brandenburg (LGB)
- **Status:** ✅ Integriert (139 Layer, ~15M Features)
- **Metadata:** `wfs_metadata_alkis.json`

---

## ⚠️ Geodaten NUR als Shapefile/WMS verfügbar (KEIN WFS)

Die folgenden wichtigen Geodaten sind im Geobroker verfügbar, aber **NUR als:**
- **Shapefile-Downloads** (benutzerkonfiguriert oder komplett)
- **WMS (View-Service)** - nur zur Visualisierung, keine Feature-Daten

### Wasser-Geodaten (Landesamt für Umwelt - LfU)

1. **Gewässernetz** (gewnet25.shp)
   - **Produkt-ID:** B9D461F1-99A1-4C10-97B4-9C36C0BD40B9
   - **Download:** https://data.geobasis-bb.de/geofachdaten/Wasser/Hydrologie/gewnet25.zip
   - **Format:** Shapefile + WMS
   - **Beschreibung:** Hauptgewässerläufe Brandenburg/Berlin, Bundeswasserstraßen, Landesgewässer 1. Ordnung
   - **Maßstab:** 1:10.000
   - **Aktualisierung:** Kontinuierlich
   - **Stand:** 01.01.2025

2. **Wasserschutzgebiete** (wsg.shp)
   - **Produkt-ID:** 657B712B-9009-49C0-8C91-A373AA87291A
   - **Download:** https://data.geobasis-bb.de/geofachdaten/Wasser/Gewaesserbewirtschaftung/wsg.zip
   - **Format:** Shapefile + WMS
   - **Beschreibung:** Wasserschutzgebiete des Landes Brandenburg
   - **Maßstab:** 1:10.000
   - **Aktualisierung:** Bei Bedarf
   - **Stand:** 10.12.2024

3. **Seen**
   - **Produkt-ID:** D9C4E283-00C3-42A2-9F1F-15BFD6A40B55
   - **Format:** Shapefile + WMS
   - **Beschreibung:** Seen in Brandenburg

4. **Einzugsgebiete**
   - **Produkt-ID:** 20636164-EFA9-40D9-BDDF-325E7BBD0F99
   - **Format:** Shapefile + WMS

5. **Grundwassermessstellen**
   - **Produkt-ID:** 2FE302D7-0ADA-4AFF-B6B3-15AA98C229D7
   - **Format:** Shapefile + WMS

6. **Grundwasserkörper**
   - **Produkt-ID:** 65C309EA-8B73-4711-8444-91D83B2EC51C
   - **Format:** Shapefile + WMS

7. **Hochwasserrisikogebiete**
   - **Produkt-ID:** 3836DB1B-9435-40DE-8FC4-BEAFFA472C8C
   - **Format:** Shapefile + WMS

8. **Überschwemmungsgebiete**
   - **Metaver:** https://metaver.de/search/dls/#?serviceId=05EC61E6-C81E-4616-ACE6-2DC3D5E67E24
   - **Format:** WMS

### Boden-Geodaten (LfU)

9. **Deponien Brandenburg**
   - **Produkt-ID:** 5DFE0DA4-0877-404A-85D1-E4B6333BA6B3
   - **Format:** Shapefile + WMS

10. **Archivböden**
    - **Produkt-ID:** BB07A209-E253-413D-B285-7B14671585DF
    - **Format:** Shapefile + WMS

11. **Moorböden mit besonderer Funktionsausprägung**
    - **Produkt-ID:** DAC1E56E-7465-45AA-A90B-32C2CA476FE5
    - **Format:** Shapefile + WMS

### Immissionsschutz (LfU)

12. **BImSchG Anlagen** (Immissionsschutzanlagen)
    - **Produkt-ID:** 65A6F973-BC30-418A-9A9F-F7FC5686E3DE
    - **Format:** Shapefile + WMS

13. **Windkraftanlagen (WKA)**
    - **Produkt-ID:** 45C506E5-3E9D-4DE2-9073-C3DB636CE7CF
    - **Format:** Shapefile + WMS

### Biotope & Naturschutz (LfU)

14. **Biotope und FFH-Lebensraumtypen**
    - **Produkt-ID:** A061BB02-70AC-4422-BB58-4A49F585D7F2
    - **Format:** Shapefile + WMS

15. **CIR-Biotoptypen 2009**
    - **Produkt-ID:** B57B9F35-AFFF-49F2-BA32-618D1A1CD412
    - **Format:** Shapefile + WMS

### Landwirtschaft (MLUK)

16. **Digitales Feldblock Kataster**
    - **Produkt-ID:** 9e95f21f-4ecf-4682-9a44-e5f7609f6fa0
    - **Format:** Shapefile + WMS

17. **Nitratbelastete Gebiete**
    - **Produkt-ID:** b1d65972-6945-4e63-8c4f-f6b216849896
    - **Format:** Shapefile + WMS

18. **Feuchtgebiete und Moore**
    - **Produkt-ID:** 5ABFFB77-26F0-4DD4-B077-A779147592C0
    - **Format:** Shapefile + WMS

---

## 📊 Zusammenfassung

### WFS-Dienste verfügbar: 5
- ✅ **Alle 5 integriert** in Covina WFS Ingestion System
- ✅ **2 erfolgreich getestet** (Verwaltungsgrenzen + Schutzgebiete)
- ✅ **305 Layer insgesamt** verfügbar
- ✅ **~23 Millionen Features** geschätzt

### Shapefile-Only Geodaten: 18+
- ⚠️ **Keine WFS-API** - nur Downloads
- ⚠️ **WMS nur zur Visualisierung** - keine Feature-Queries
- ⚠️ **Manuelle Integration erforderlich** - Shapefile-Import nötig

---

## 💡 Empfehlungen

### Option 1: Shapefile-Import-Pipeline entwickeln
**Vorteile:**
- Zugriff auf 18+ zusätzliche Geodatensätze
- Einmalige Ingestion, dann lokal verfügbar
- Keine API-Limits

**Nachteile:**
- Manuelle Downloads erforderlich
- Keine automatische Update-Erkennung
- Speicherintensiv

**Implementierung:**
```bash
# Beispiel: Gewässernetz
wget https://data.geobasis-bb.de/geofachdaten/Wasser/Hydrologie/gewnet25.zip
unzip gewnet25.zip
python -m ingestion.shapefile_ingestion_worker gewnet25.shp --metadata shapefile_metadata_gewnet.json
```

### Option 2: Fokus auf bestehende WFS-Dienste
**Vorteile:**
- 5 WFS-Dienste bereits integriert
- Automatische Updates möglich
- API-basiert, skalierbar

**Nachteile:**
- Nur 5 Dienste verfügbar
- Wasserdaten fehlen (wichtig!)

**Empfehlung:** ✅ **Vorerst bei WFS bleiben, später Shapefile-Import**

### Option 3: LfU nach WFS-Diensten anfragen
**Idee:** Das Landesamt für Umwelt (LfU) betreibt bereits einen INSPIRE WFS (Schutzgebiete). 
Möglicherweise sind weitere WFS-Dienste für Wasserdaten verfügbar oder können bereitgestellt werden.

**Kontakt:**
- **Email:** BdP@lfu.brandenburg.de
- **Telefon:** +49 33201 442-102
- **Anfrage:** "Sind WFS-Dienste für Gewässernetz, Wasserschutzgebiete, Grundwasserdaten verfügbar?"

---

## 🚀 Priorisierung für Shapefile-Import (falls implementiert)

### Priorität 1: Wasserdaten
1. **Gewässernetz** - Hydrologie-Basis
2. **Wasserschutzgebiete** - Rechtlich relevant
3. **Seen** - Gewässer-Kataster

### Priorität 2: Umweltdaten
4. **Biotope und FFH-Lebensraumtypen** - Ergänzt Schutzgebiete-WFS
5. **Windkraftanlagen** - Energiewende-Monitoring
6. **Deponien** - Altlasten

### Priorität 3: Landwirtschaft
7. **Digitales Feldblock Kataster** - Landwirtschaftliche Nutzung
8. **Nitratbelastete Gebiete** - Wasserqualität
9. **Feuchtgebiete und Moore** - Klimaschutz

---

## 📝 Nächste Schritte

### Kurzfristig (jetzt)
1. ✅ **Alle 5 WFS-Dienste nutzen**
   - Verwaltungsgrenzen ✅ (getestet)
   - Schutzgebiete ✅ (getestet)
   - Gazetteer ⏳ (bereit)
   - ATKIS ⏳ (bereit)
   - ALKIS ⏳ (bereit)

### Mittelfristig (1-2 Wochen)
2. ⏳ **Shapefile-Import-Pipeline entwickeln**
   - Shapefile → GeoJSON Konverter
   - Metadata-Template für Shapefiles
   - Update-Tracking für manuelle Downloads

3. ⏳ **Gewässernetz & Wasserschutzgebiete integrieren**
   - Shapefile-Download automatisieren
   - Erste Ingestion durchführen
   - Mit WFS-Daten kombinieren

### Langfristig (1-3 Monate)
4. ⏳ **LfU nach zusätzlichen WFS kontaktieren**
5. ⏳ **Biotope & Landwirtschaftsdaten integrieren**
6. ⏳ **Monitoring-Dashboard für alle Geodaten**

---

## 📧 Kontakte

### Landesvermessung und Geobasisinformation (LGB)
- **WFS-Dienste:** Verwaltungsgrenzen, Gazetteer, ATKIS, ALKIS
- **Email:** kundenservice@geobasis-bb.de
- **Tel:** +49-331-8844-123

### Landesamt für Umwelt (LfU)
- **WFS-Dienste:** Schutzgebiete (INSPIRE)
- **Shapefile:** Gewässernetz, Wasserschutzgebiete, Biotope, etc.
- **Email:** BdP@lfu.brandenburg.de
- **Tel:** +49-33201-442-102

---

**Fazit:** Brandenburg bietet **5 hochwertige WFS-Dienste** (alle integriert) und **18+ Shapefile-Geodatensätze** (noch nicht integriert). Für vollständige Geodatenabdeckung wird mittelfristig eine **Shapefile-Import-Pipeline** empfohlen.
