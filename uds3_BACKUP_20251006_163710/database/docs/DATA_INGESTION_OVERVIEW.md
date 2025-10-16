# Veritas Data Ingestion Suite
## Übersicht der verfügbaren Scraper

Stand: 22. August 2025

### 1. GovData.de Scraper (`ingestion_govdata_scraper.py`)
**Status: ✅ Vollständig funktionsfähig**

**Beschreibung:**
Scraper für die deutsche Regierungsdatenplattform GovData.de, die über 132.000 Datasets von 72 Organisationen und 13 Kategorien enthält.

**Features:**
- CKAN API-basierter Zugriff
- Vollständiges Scraping aller Datasets
- Themen-basierte Suche
- Statistiken und Organisationsübersichten
- Export nach JSON und CSV
- Rate-Limiting und Fehlerbehandlung
- Checkpoint-System für große Scraping-Jobs

**Nutzung:**
```bash
# Statistiken anzeigen
python ingestion_govdata_scraper.py --list

# Nach Thema suchen
python ingestion_govdata_scraper.py --search "Verkehr"

# Alle Datasets scrapen (mit Maximum)
python ingestion_govdata_scraper.py --all --max 1000

# Organisationen anzeigen
python ingestion_govdata_scraper.py --organizations
```

**Datenvolumen:** 132.936 Datasets, 71.737 Tags, 72 Organisationen

### 2. Verwaltungsvorschriften Scraper (`ingestion_verwaltungsvorschriften_scraper.py`)
**Status: ✅ Vollständig funktionsfähig**

**Beschreibung:**
Scraper für verwaltungsvorschriften-im-internet.de mit HTML-zu-Markdown-Konvertierung und Ministeriumsfilterung.

**Features:**
- XML-Katalog-Parsing
- HTML-zu-Markdown-Konvertierung mit html2text
- Ministeriumsfilterung (93 verschiedene Ministerien)
- Volltext-Extraktion aus HTML-Seiten
- Rate-Limiting und Fehlerbehandlung
- Export nach JSON, CSV und Markdown

**Nutzung:**
```bash
# Alle Dokumente scrapen
python ingestion_verwaltungsvorschriften_scraper.py --all

# Nach Ministerium filtern
python ingestion_verwaltungsvorschriften_scraper.py --search --ministry "Bundesministerium der Finanzen"

# Verfügbare Ministerien auflisten
python ingestion_verwaltungsvorschriften_scraper.py --list
```

**Datenvolumen:** 817 Verwaltungsvorschriften von 93 Ministerien

### 3. Rechtsprechung-im-Internet Scraper (`ingestion_rechtsprechung_scraper.py`)
**Status: ✅ Vollständig funktionsfähig**

**Beschreibung:**
Scraper für die deutsche Rechtsprechungsdatenbank rechtsprechung-im-internet.de mit über 79.000 Gerichtsentscheidungen aller Bundesgerichte.

**Features:**
- XML-Katalog-Parsing (22 MB XML-Datei)
- Filterung nach Gericht, Jahr, Aktenzeichen
- Download von ZIP-Dateien mit Entscheidungstexten
- Export nach JSON und CSV
- Statistische Analysen nach Gericht und Zeitraum
- Rate-Limiting und robuste Fehlerbehandlung

**Nutzung:**
```bash
# Statistiken anzeigen
python ingestion_rechtsprechung_scraper.py --statistics

# Nach Gericht suchen
python ingestion_rechtsprechung_scraper.py --search --court "BGH"

# Entscheidungen eines Jahres
python ingestion_rechtsprechung_scraper.py --search --year 2024

# Mit Download der Entscheidungsdateien
python ingestion_rechtsprechung_scraper.py --search --court "BVerfG" --download --max-downloads 50
```

**Datenvolumen:** 79.284 Entscheidungen von 8 Bundesgerichten (2010-2025)

**Gerichtsverteilung:**
- BGH (Bundesgerichtshof): 32.373 Entscheidungen
- BFH (Bundesfinanzhof): 11.184 Entscheidungen  
- BVerwG (Bundesverwaltungsgericht): 9.823 Entscheidungen
- BPatG (Bundespatentgericht): 7.183 Entscheidungen
- BAG (Bundesarbeitsgericht): 7.055 Entscheidungen
- BSG (Bundessozialgericht): 6.141 Entscheidungen
- BVerfG (Bundesverfassungsgericht): 5.523 Entscheidungen

### 4. Weitere geplante Scraper

**EUR-Lex Scraper**
- Status: Geplant
- Ziel: Europäische Rechtsdatenbank

**Bundesgesetzblatt Scraper**
- Status: Geplant  
- Ziel: Aktuelle und historische Gesetze

**Landesparlamente**
- Status: Geplant
- Ziel: Landtagsdrucksachen und -protokolle

## Technische Architektur

### Gemeinsame Features aller Scraper:
- **Rate-Limiting:** Respektvoller Umgang mit Servern (1-2s Delays)
- **Fehlerbehandlung:** Robuste Fehlerbehandlung mit Logging
- **Export-Formate:** JSON, CSV, teilweise Markdown
- **Checkpoint-System:** Große Jobs können unterbrochen und fortgesetzt werden
- **CLI-Interface:** Benutzerfreundliche Kommandozeilen-Schnittstelle
- **Filterfunktionen:** Flexible Such- und Filteroptionen

### Technologie-Stack:
- **Python 3.7+**
- **requests:** HTTP-Anfragen und Session-Management
- **BeautifulSoup4:** HTML-Parsing
- **xml.etree.ElementTree:** XML-Parsing
- **html2text:** HTML-zu-Markdown-Konvertierung
- **pandas:** Datenverarbeitung (optional)
- **json/csv:** Standardisierte Datenexporte

## Installation und Setup

### Voraussetzungen:
```bash
pip install requests beautifulsoup4 html2text pandas lxml
```

### Verzeichnisstruktur:
```
veritas/
├── ingestion_govdata_scraper.py
├── ingestion_verwaltungsvorschriften_scraper.py
├── ingestion_rechtsprechung_scraper.py
├── govdata_output/
│   ├── govdata_statistics_*.json
│   └── govdata_search_*.json
├── verwaltungsvorschriften_output/
│   ├── catalog_*.json
│   └── documents_*.json
├── rechtsprechung_output/
│   ├── rii_statistics_*.json
│   ├── rii_search_*.json
│   └── decisions/*.zip
└── logs/
    ├── govdata_scraper.log
    ├── verwaltungsvorschriften_scraper.log
    └── rechtsprechung_scraper.log
```

## Datenqualität und -struktur

### GovData.de:
- **132.936 Datasets** aus verschiedenen Behörden
- **Metadaten:** Titel, Beschreibung, Organisation, Tags, Ressourcen
- **Formate:** CSV, JSON, PDF, XML, WMS, TIFF, etc.
- **Lizenzierung:** Meist CC-BY oder ähnlich

### Verwaltungsvorschriften:
- **817 Dokumente** von 93 Ministerien
- **Volltext:** HTML zu strukturiertem Markdown konvertiert
- **Metadaten:** Titel, Ministerium, Datum, Fundstelle
- **Formatierung:** Behält HTML-Strukturen als Markdown bei

### Rechtsprechung:
- **79.284 Entscheidungen** von 8 Bundesgerichten
- **Zeitraum:** 2010-2025 (kontinuierlich aktualisiert)
- **Volltext:** ZIP-Archive mit Original-Entscheidungstexten
- **Metadaten:** Gericht, Senat, Aktenzeichen, Entscheidungsdatum
- **Kategorisierung:** Nach Gericht und Jahr filterbar

## Verwendungsmöglichkeiten

### Forschung:
- Analyse von Regierungsdatenveröffentlichungen
- Rechtsprechungsanalyse und juristische Forschung
- Transparenz- und Open-Data-Studien
- Verwaltungsrechts- und Verfassungsforschung

### Entwicklung:
- Basis für Suchmaschinen und Datenkataloge
- Training für NLP-Modelle auf Behördentexten und Rechtsprechung
- Compliance- und Monitoring-Systeme
- Legal-Tech-Anwendungen

### Journalismus:
- Investigative Recherche in Regierungsdaten
- Faktenchecking mit offiziellen Quellen
- Datengetriebene Berichterstattung über Rechtsprechung
- Analyse von Verwaltungsentscheidungen

## Performance-Metriken

### Scraping-Geschwindigkeiten (mit Rate-Limiting):
- **GovData:** ~1.000 Datasets/Stunde
- **Verwaltungsvorschriften:** ~500 Dokumente/Stunde  
- **Rechtsprechung:** ~2.000 Metadaten/Stunde, ~100 Downloads/Stunde

### Datenvolumen:
- **Gesamte Metadaten:** >212.000 Einträge
- **Volltext-Dokumente:** >1.000 (und wachsend)
- **Speicherbedarf:** ~500 MB für alle Metadaten, ~10 GB für Volltext-Archive

## Support und Weiterentwicklung

**Aktuelle Version:** 2.0
**Letztes Update:** 22. August 2025
**Wartung:** Aktiv

### Neue Features in v2.0:
- Rechtsprechung-im-Internet Scraper hinzugefügt
- Verbesserte Datumsverarbeitung und File-ID-Extraktion
- Erweiterte Statistikfunktionen
- Optimierte Download-Performance

Bei Fragen oder Feature-Requests: Siehe Dokumentation in den jeweiligen Scraper-Dateien.

---

*Diese Suite wurde entwickelt für Bildungs- und Forschungszwecke. Alle Scraper respektieren robots.txt und implementieren angemessenes Rate-Limiting gemäß den Nutzungsrichtlinien der jeweiligen Websites.*
