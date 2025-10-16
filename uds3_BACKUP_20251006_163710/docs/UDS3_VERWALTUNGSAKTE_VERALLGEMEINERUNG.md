# UDS3 Verwaltungsakte - Verallgemeinerte Form aus Realfall

## Analyse des BImSchG-Falls für Verallgemeinerung

### Extrahierte Grundmuster aus G09123-Genehmigungsbescheid:

#### 1. **VERFAHRENSSTRUKTUR-MUSTER**
```
Antragstellung → Prüfung → Beteiligung → Entscheidung → Vollzug
```

**Verallgemeinerbare Komponenten:**
- **Verfahrensinitiierung**: Antrag vom 15.11.2023
- **Bearbeitungszeit**: 19 Monate Verfahrensdauer
- **Behördenbeteiligung**: 8+ beteiligte Stellen
- **Entscheidung**: Bescheid vom 01.07.2025
- **Vollzugsfristen**: 3 Jahre Umsetzungsfrist

#### 2. **NEBENBESTIMMUNGS-SYSTEMATIK**
```
Hauptentscheidung + Strukturierte Nebenbestimmungen
```

**Typen im Realfall:**
- **Inhalts- und Nebenbestimmungen (IV.)**: Hauptregelungswerk
- **Bauordnungsrechtliche Bestimmungen**: Zusatzregelungen
- **Immissionsschutz**: Fachspezifische Auflagen
- **Naturschutz**: Umweltschutzauflagen
- **Überwachung**: Kontroll- und Berichtspflichten

#### 3. **RECHTSMITTEL-STRUKTUR**
```
Hauptentscheidung → Rechtsbehelfsbelehrung → Besondere Regelungen
```

**Komponenten:**
- **Standardwiderspruch**: 1 Monat Frist
- **Sonderregelungen**: § 63 BImSchG (keine aufschiebende Wirkung)
- **Instanzenzug**: Widerspruch → OVG Berlin-Brandenburg

#### 4. **GEBÜHREN-/KOSTEN-SYSTEMATIK**
```
Verfahrenskosten + Nebenkosten + Drittkosten
```

**Komponenten:**
- **Hauptgebühr**: BImSchG-Verfahren
- **Bauordnungsgebühren**: Zusätzliche Gebühren
- **Luftfahrtkosten**: Weitere Nebenkosten

---

## Verallgemeinerte UDS3-Feldstruktur

### **A. VERFAHRENS-METADATEN (Prozessual)**
```json
{
  "verfahren_art": "",                    // BImSchG | Planfeststellung | Baugenehmigung | etc.
  "verfahren_rechtsgrundlage": [],        // ["§ 4 BImSchG", "§ 19 BImSchG"]
  "verfahren_initiierung_datum": "",      // ISO Date
  "verfahren_entscheidung_datum": "",     // ISO Date  
  "verfahren_dauer_monate": 0,            // Berechnete Dauer
  "verfahren_komplexität": "",            // EINFACH | STANDARD | KOMPLEX
  "verfahren_öffentlichkeit": false,      // Öffentliche Beteiligung erforderlich
  "verfahren_beteiligte_behörden": []     // Array von Behörden
}
```

### **B. ENTSCHEIDUNGS-METADATEN (Inhaltlich)**
```json
{
  "entscheidung_gegenstand": "",          // Freier Text: "8 Windkraftanlagen"
  "entscheidung_umfang": "",              // VOLLUMFÄNGLICH | TEILWEISE | BEDINGT
  "entscheidung_räumlicher_bezug": "",    // Standort/Gemeinde
  "entscheidung_wirtschaftlicher_wert": 0, // Geschätzter Projektwert
  "entscheidung_umweltrelevanz": "",      // HOCH | MITTEL | NIEDRIG
  "entscheidung_drittbetroffenheit": []   // Array betroffener Gruppen
}
```

### **C. NEBENBESTIMMUNGS-SYSTEMATIK (Erweitert)**
```json
{
  "nebenbestimmungen_struktur": {
    "allgemeine_bestimmungen": [],        // Grundlegende Auflagen
    "fachspezifische_auflagen": [],       // BImSchG, Baurecht, etc.
    "überwachungsanordnungen": [],        // Kontrollen, Messungen
    "berichtspflichten": [],              // Regelmäßige Berichte
    "fristen_termine": [],                // Alle zeitlichen Vorgaben
    "kostentragung": []                   // Wer trägt welche Kosten
  },
  "nebenbestimmungen_durchsetzbarkeit": "", // VOLLSTRECKBAR | ANORDNUNGSFÄHIG
  "nebenbestimmungen_änderbarkeit": ""      // ÄNDERBAR | ENDGÜLTIG
}
```

### **D. RECHTSMITTEL-SYSTEMATIK (Speziell)**
```json
{
  "rechtsmittel_standardfrist": "",       // "1 Monat"
  "rechtsmittel_sonderregelungen": [],    // ["§ 63 BImSchG"]  
  "rechtsmittel_aufschiebende_wirkung": "", // JA | NEIN | BEDINGT
  "rechtsmittel_instanzenzug": [],        // ["Widerspruch", "VG", "OVG"]
  "rechtsmittel_kostenrisiko": "",        // STANDARD | ERHÖHT | BESONDERS
  "rechtsmittel_drittberechtigung": true  // Können Dritte Rechtsmittel einlegen
}
```

### **E. VOLLZUGS-METADATEN (Praktisch)**
```json
{
  "vollzug_frist_beginn": "",            // ISO Date oder Bedingung
  "vollzug_frist_ende": "",              // ISO Date  
  "vollzug_meldepflichten": [],          // Anzeigen, Berichte
  "vollzug_überwachung": [],             // Zuständige Behörden
  "vollzug_sanktionen": [],              // Bei Nichteinhaltung
  "vollzug_änderungsmöglichkeiten": ""   // Nachträgliche Anpassungen
}
```

---

## Spezialisierungen aufbauend auf der Grundstruktur

### **SPEZIALISIERUNG 1: BImSchG-GENEHMIGUNGEN**
```json
{
  "bimschg_anlagenart": "",              // WINDKRAFT | INDUSTRIE | GEWERBE
  "bimschg_genehmigungstyp": "",         // § 4 | § 19 | Änderungsgenehmigung
  "bimschg_emissionsarten": [],          // ["Lärm", "Luftschadstoffe", "Erschütterungen"]
  "bimschg_schutzgüter": [],             // ["Menschen", "Tiere", "Boden", "Wasser"]  
  "bimschg_überwachungsintensität": "",  // STANDARD | VERSCHÄRFT | REDUZIERT
  "bimschg_nachbarschutz": true,         // Besondere Nachbarrechte
  "bimschg_uvp_pflicht": true,           // UVP-Verfahren erforderlich
  "bimschg_störfall_relevant": false     // Störfallverordnung anwendbar
}
```

### **SPEZIALISIERUNG 2: BAUORDNUNGSRECHT**
```json
{
  "baurecht_genehmigungsart": "",        // VOLLGENEHMIGUNG | TEILGENEHMIGUNG | FREIGABE
  "baurecht_verfahrensart": "",          // VEREINFACHT | STANDARD | ERWEITERT
  "baurecht_planungsrecht": [],          // Anwendbare Pläne
  "baurecht_nachbarrechte": [],          // Betroffene Nachbarrechte
  "baurecht_erschließung": "",           // Erschließungssituation
  "baurecht_denkmalschutz": false,       // Denkmalschutz relevant
  "baurecht_naturschutz": [],            // Naturschutzauflagen
  "baurecht_brandschutz": []             // Brandschutzauflagen
}
```

### **SPEZIALISIERUNG 3: PLANUNGSRECHT**
```json
{
  "planung_planart": "",                 // BPLAN | FPLAN | PLANFESTSTELLUNG
  "planung_verfahrensstand": "",         // AUFSTELLUNG | AUSLEGUNG | BESCHLUSS
  "planung_beteiligungsart": [],         // ["Öffentlich", "TöB", "Nachbargemeinden"]
  "planung_umweltprüfung": "",           // SUP | UVP | NICHT_ERFORDERLICH
  "planung_ausgleichsmassnahmen": [],    // Erforderliche Ausgleichsmaßnahmen
  "planung_fachgutachten": [],           // Beauftragte Gutachten
  "planung_monitoring": []               // Überwachungsmaßnahmen
}
```

---

## Implementierungsstrategie

### **PHASE 1: Verallgemeinerte Basis implementieren**
1. Erweitere `default_metadata.json` um die 5 Hauptkategorien (A-E)
2. Implementiere generische Extraktoren im Preprocessor
3. Erweitere Postprocessor-Validierung um die neuen Strukturen

### **PHASE 2: Spezialisierungen aufbauen**
1. Implementiere BImSchG-Spezialisierung (basierend auf Realfall)
2. Entwickle Bauordnungsrecht-Spezialisierung  
3. Implementiere Planungsrecht-Spezialisierung

### **PHASE 3: Intelligente Typenerkennung**
1. Automatische Erkennung des Verwaltungsakt-Typs
2. Dynamische Aktivierung der passenden Spezialisierung
3. Intelligente Feldvalidierung je nach Typ

### **PHASE 4: Integration und Optimierung**
1. Covina-UI-Integration für spezialisierte Ansichten
2. Intelligente Such- und Filterfunktionen
3. Automatische Qualitätsbewertung je Spezialisierung
