# WFS Discovery Guide

## Übersicht

Der **WFS Discovery Modus** im WFS Ingestion GUI ermöglicht die automatische Analyse beliebiger WFS-Dienste und die Generierung von Ingestion-Konfigurationen.

## Features

### 🔍 Automatische WFS-Analyse
- GetCapabilities-Request an WFS-Dienst
- Extraktion von Service-Metadaten (Titel, Anbieter, Version)
- Erkennung aller verfügbaren Layer
- Automatische Feature-Count-Ermittlung pro Layer
- BoundingBox-Extraktion
- CRS-Erkennung

### 📊 Layer-Informationen
- **Layer-Name:** Technischer Identifier
- **Titel:** Menschenlesbarer Name
- **Feature-Count:** Anzahl verfügbarer Features
- **BoundingBox:** Räumliche Ausdehnung (WGS84)
- **CRS:** Koordinatenreferenzsystem

### ⚙️ Config-Generierung
- Auswahl einzelner oder mehrerer Layer
- Anpassbare Ingestion-Parameter:
  - Service-Name
  - Kategorie (FNP, B-Plan, Custom, etc.)
  - Max Features pro Request
- Automatische Attribute-Mapping-Vorschläge
- Koordinatentransformation (Source CRS → EPSG:25833)

### 💾 Export-Optionen
- **Speichern:** Config als JSON-Datei
- **Vorschau:** Config vor dem Speichern ansehen
- **Zwischenablage:** Config direkt kopieren

## Workflow

### 1️⃣ WFS-URL eingeben

```
Beispiel-URLs:

# Brandenburg PLIS (Bebauungspläne)
https://isk.geobasis-bb.de/ows/plis_bebauungsplaene_rechtswirksam_wfs?SERVICE=WFS&REQUEST=GetCapabilities

# Brandenburg PLIS (Flächennutzungsplan Potsdam)
https://isk.geobasis-bb.de/ows/plis_fnp_potsdam_wfs?SERVICE=WFS&REQUEST=GetCapabilities

# LBV Regionalplan
https://data.geobasis-bb.de/geobasis/daten/regional_plan/hf_wen_wfs?SERVICE=WFS&REQUEST=GetCapabilities

# Andere WFS-Dienste (beliebig)
https://example.com/wfs?SERVICE=WFS&REQUEST=GetCapabilities
```

**Hinweis:** Die URL muss ein GetCapabilities-Request sein. Falls nicht, wird automatisch `?SERVICE=WFS&REQUEST=GetCapabilities` angehängt.

### 2️⃣ WFS analysieren

Klicken Sie auf **"🔍 WFS analysieren"**

Das System führt folgende Schritte aus:
1. ✅ GetCapabilities-Request senden
2. ✅ XML-Response parsen
3. ✅ Service-Informationen extrahieren
4. ✅ Layer-Liste aufbauen
5. ✅ Feature-Counts ermitteln (pro Layer)
6. ✅ BoundingBoxes extrahieren

**Ergebnis:**
- WFS-Informationen werden angezeigt
- Layer-Liste wird gefüllt
- Service-Name wird vorgeschlagen

### 3️⃣ Layer auswählen

- **Einzelauswahl:** Klick auf Layer
- **Mehrfachauswahl:** Ctrl+Klick oder Shift+Klick
- **Alle auswählen:** Ctrl+A

**Layer-Informationen:**
| Spalte | Beschreibung |
|--------|--------------|
| **Layer Name** | Technischer Identifier (wird in Config verwendet) |
| **Titel** | Menschenlesbarer Name |
| **Features** | Anzahl verfügbarer Features (? = nicht ermittelbar) |
| **BoundingBox** | Räumliche Ausdehnung (minx, miny)-(maxx, maxy) |

### 4️⃣ Config-Parameter anpassen

**Service-Name:**
- Vorschlag basiert auf WFS-Titel
- Kann manuell angepasst werden
- Wird als `source_name` in Config übernommen

**Kategorie:**
- `custom` - Standard für unbekannte Dienste
- `xplanung_fnp` - Flächennutzungspläne
- `xplanung_bplan` - Bebauungspläne
- `raumordnung_verfahren` - Raumordnungsverfahren
- `regionalplanung` - Regionalpläne
- `sonderplanung` - Sonderdienste

**Max Features:**
- Standard: 1000
- Empfohlen: 1000-5000 (abhängig von Layer-Größe)
- Maximum: 100000 (Server-abhängig)

### 5️⃣ Config generieren & speichern

**Option A: Speichern**
1. Klick auf **"💾 Config generieren & speichern"**
2. Dateiname wird vorgeschlagen (basierend auf Service-Name)
3. Standard-Verzeichnis: `examples/brandenburg_planning_wfs/`
4. Config wird als JSON gespeichert
5. Falls im gleichen Verzeichnis: Automatisches Reload der Config-Liste

**Option B: Vorschau**
1. Klick auf **"👁 Config Vorschau"**
2. JSON-Config wird in neuem Fenster angezeigt
3. Manuelles Kopieren/Bearbeiten möglich

**Option C: Zwischenablage**
1. Klick auf **"📋 Config in Zwischenablage"**
2. JSON wird direkt kopiert
3. Kann in Editor eingefügt werden

## Generierte Config-Struktur

```json
{
  "wfs_service": {
    "url": "https://example.com/wfs",
    "version": "2.0.0",
    "layers": [
      {
        "name": "layer_name",
        "title": "Layer Title",
        "geometry_field": "geom",
        "properties": []
      }
    ],
    "output_format": "application/json",
    "max_features": 1000,
    "srs": "EPSG:25833"
  },
  "ingestion_config": {
    "source_name": "Custom WFS Service",
    "source_type": "wfs",
    "category": "custom",
    "batch_size": 100,
    "enable_preprocessing": true,
    "metadata": {
      "provider": "Service Provider Name",
      "title": "Service Title",
      "abstract": "Service description...",
      "keywords": ["keyword1", "keyword2"],
      "created_date": "2025-10-08T12:00:00",
      "created_by": "WFS Ingestion GUI"
    }
  },
  "attribute_mapping": {
    "id_field": "id",
    "title_field": "name",
    "description_field": "description"
  },
  "filters": {
    "spatial_filter": null,
    "attribute_filter": null
  },
  "transformation": {
    "coordinate_transform": {
      "source_crs": "EPSG:4326",
      "target_crs": "EPSG:25833"
    }
  }
}
```

## Erweiterte Verwendung

### Multi-Layer Configs

**Szenario:** Ein WFS-Dienst mit mehreren thematisch zusammengehörigen Layern

**Vorgehen:**
1. WFS analysieren
2. Alle relevanten Layer auswählen (Ctrl+Klick)
3. Config generieren
4. **Eine einzige Config-Datei** enthält alle Layer

**Beispiel:**
```json
"layers": [
  {"name": "fnp_flaechen", "title": "FNP Flächengeometrien"},
  {"name": "fnp_linien", "title": "FNP Linienelemente"},
  {"name": "fnp_punkte", "title": "FNP Punktelemente"}
]
```

### Custom Attribute Mapping

Nach dem Generieren können Sie die Config manuell anpassen:

```json
"attribute_mapping": {
  "id_field": "gml_id",           // WFS-spezifisch
  "title_field": "planname",      // Statt "name"
  "description_field": "rechtscharakter"  // Statt "description"
}
```

### Spatial Filters

Räumliche Einschränkung (manuell hinzufügen):

```json
"filters": {
  "spatial_filter": {
    "type": "bbox",
    "coordinates": [12.0, 51.0, 14.0, 53.0]  // minx, miny, maxx, maxy
  }
}
```

### Attribute Filters

Attribut-basierte Filter (manuell hinzufügen):

```json
"filters": {
  "attribute_filter": {
    "field": "rechtsstand",
    "operator": "equals",
    "value": "rechtswirksam"
  }
}
```

## Fehlerbehebung

### ❌ "HTTP-Fehler 404"
**Ursache:** WFS-URL ist falsch oder Dienst existiert nicht  
**Lösung:** URL überprüfen, Browser-Test durchführen

### ❌ "XML-Parse-Fehler"
**Ursache:** Response ist kein gültiges XML (z.B. HTML-Fehlerseite)  
**Lösung:** URL im Browser öffnen, prüfen ob XML zurückgegeben wird

### ❌ "Keine Layer gefunden"
**Ursache:** WFS-Version nicht unterstützt oder leerer FeatureTypeList  
**Lösung:** WFS-Version prüfen (1.1.0, 2.0.0 unterstützt)

### ❌ "Timeout"
**Ursache:** Server antwortet zu langsam  
**Lösung:** Timeout-Einstellung erhöhen (aktuell 30s), Server-Status prüfen

### ⚠️ "Feature-Count = ?"
**Ursache:** GetFeature mit resultType=hits nicht unterstützt  
**Lösung:** Normal, Config kann trotzdem erstellt werden

## Best Practices

### ✅ URL-Validierung vor Analyse
```bash
# Browser-Test
https://example.com/wfs?SERVICE=WFS&REQUEST=GetCapabilities

# Erwartetes Ergebnis: XML-Response mit <WFS_Capabilities>
```

### ✅ Service-Name Konventionen
```
Format: <region>_<thema>_<spezifikation>

Beispiele:
- brandenburg_fnp_potsdam
- nrw_bplan_koeln
- sachsen_regionalplan_leipzig
```

### ✅ Kategorie-Zuordnung
| WFS-Typ | Kategorie |
|---------|-----------|
| Flächennutzungsplan | `xplanung_fnp` |
| Bebauungsplan | `xplanung_bplan` |
| Regionalplan | `regionalplanung` |
| Raumordnungsverfahren | `raumordnung_verfahren` |
| Sonstige | `custom` |

### ✅ Max Features Tuning
| Layer-Größe | Empfohlener Wert |
|-------------|------------------|
| < 1.000 Features | 1000 |
| 1.000 - 10.000 | 2000 |
| 10.000 - 50.000 | 5000 |
| > 50.000 | 10000 |

### ✅ Config-Verzeichnisstruktur
```
examples/
├── brandenburg_planning_wfs/
│   ├── fnp_*.json              # Flächennutzungspläne
│   ├── bplan_*.json            # Bebauungspläne
│   ├── rov_*.json              # Raumordnung
│   └── regplan_*.json          # Regionalpläne
├── nrw_planning_wfs/           # Andere Bundesländer
└── custom_wfs/                 # Custom WFS-Dienste
```

## Beispiel-Workflow: Neuer WFS-Dienst

### Szenario: Flächennutzungsplan Stadt XY

**1. URL beschaffen**
```
https://gis.stadt-xy.de/wfs/fnp?SERVICE=WFS&REQUEST=GetCapabilities
```

**2. Im GUI analysieren**
- URL eingeben
- "WFS analysieren" klicken
- Warten auf Ergebnis (2-5 Sekunden)

**3. Ergebnis prüfen**
```
Version:      2.0.0
Titel:        Flächennutzungsplan Stadt XY
Anbieter:     Stadt XY - Planungsamt

Gefundene Layer: 4
- fnp_hauptnutzungen (23.456 Features)
- fnp_ueberlagernde_nutzungen (5.678 Features)
- fnp_kennzeichnungen (890 Features)
- fnp_nachrichtliche_uebernahmen (234 Features)
```

**4. Layer auswählen**
- Alle 4 Layer auswählen (Ctrl+A)

**5. Parameter setzen**
- Service-Name: `Stadt XY - Flächennutzungsplan`
- Kategorie: `xplanung_fnp`
- Max Features: `2000` (wegen großer Layer)

**6. Config speichern**
- Dateiname: `fnp_stadt_xy.json`
- Verzeichnis: `examples/brandenburg_planning_wfs/`

**7. Ingestion testen**
- Zum Tab "Ingestion" wechseln
- Config `fnp_stadt_xy.json` auswählen
- "Ingestion starten"

**Erwartetes Ergebnis:**
```
✅ Stadt XY - Flächennutzungsplan: 30.258 Features
   - fnp_hauptnutzungen: 23.456
   - fnp_ueberlagernde_nutzungen: 5.678
   - fnp_kennzeichnungen: 890
   - fnp_nachrichtliche_uebernahmen: 234
```

## API-Kompatibilität

### Unterstützte WFS-Versionen
- ✅ **WFS 2.0.0** (empfohlen)
- ✅ **WFS 1.1.0** (getestet)
- ⚠️ **WFS 1.0.0** (eingeschränkt)

### Unterstützte Output-Formate
- ✅ `application/json` (GeoJSON)
- ✅ `application/gml+xml` (GML 3.2)
- ⚠️ `text/xml; subtype=gml/3.1.1` (GML 3.1)

### Unterstützte CRS
- ✅ EPSG:4326 (WGS84)
- ✅ EPSG:25833 (ETRS89 UTM 33N - Brandenburg)
- ✅ EPSG:3857 (Web Mercator)
- ✅ EPSG:31467 (Gauss-Krüger Zone 3)

## Integration mit Ingestion

Nach der Config-Generierung:

**Einzelner Dienst:**
```bash
python -m ingestion.wfs_ingestion_worker examples/brandenburg_planning_wfs/fnp_stadt_xy.json
```

**Im GUI:**
1. Tab "Ingestion" öffnen
2. Generierte Config wird automatisch in Liste angezeigt
3. Config auswählen
4. "Ingestion starten"

**Batch-Ingestion:**
```bash
# Alle FNP-Dienste
foreach($file in Get-ChildItem examples/brandenburg_planning_wfs/fnp_*.json) {
  python -m ingestion.wfs_ingestion_worker $file
}
```

## Changelog

### Version 1.0 (2025-10-08)
- ✅ Initiale Implementierung
- ✅ WFS 2.0.0 / 1.1.0 Support
- ✅ GetCapabilities-Parsing
- ✅ Layer-Extraktion mit Feature-Counts
- ✅ BoundingBox-Erkennung
- ✅ Config-Generierung
- ✅ Multi-Layer-Support
- ✅ Export-Optionen (Speichern, Vorschau, Zwischenablage)

## Support

Bei Problemen oder Fragen:
1. Dokumentation prüfen (dieses Dokument)
2. Logs im GUI-Tab "Logs" überprüfen
3. Config manuell validieren
4. Issue erstellen mit:
   - WFS-URL
   - GetCapabilities-Response (falls möglich)
   - Fehlermeldung aus Logs

## Siehe auch

- [BRANDENBURG_PLANNING_WFS_COMPLETE.md](BRANDENBURG_PLANNING_WFS_COMPLETE.md) - Übersicht Brandenburg WFS-Dienste
- [WFS_INGESTION_WORKER.md](WFS_INGESTION_WORKER.md) - Ingestion-Worker Dokumentation
- [CONFIG_FORMAT.md](CONFIG_FORMAT.md) - Detaillierte Config-Format-Spezifikation
