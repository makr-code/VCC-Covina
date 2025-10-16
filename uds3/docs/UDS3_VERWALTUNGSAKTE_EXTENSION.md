# UDS3 Extension für Verwaltungsakte nach VwVfG

## Rechtliche Grundlage: Verwaltungsverfahrensgesetz (VwVfG)

### 1. Verwaltungsakt-Klassifikation nach § 35 VwVfG

#### 1.1 Art der Wirkung
- **Begünstigender Verwaltungsakt** (§ 48 VwVfG)
  - Gewährt Rechte, Befugnisse oder rechtliche Vorteile
  - Beispiele: Genehmigungen, Erlaubnisse, Subventionsbescheide
- **Belastender Verwaltungsakt** (§ 49 VwVfG)
  - Begründet Pflichten oder entzieht Rechte
  - Beispiele: Bußgeldbescheide, Untersagungsverfügungen, Steuerbescheide

#### 1.2 Form der Entscheidung
- **Ausdrücklicher Verwaltungsakt**
  - Schriftlich, mündlich oder in anderer Weise
- **Konkludenter Verwaltungsakt**
  - Durch schlüssiges Verhalten der Behörde
- **Verwaltungsakt durch Schweigen**
  - Genehmigungsfiktion nach § 42a VwVfG
  - Negative Entscheidung durch Fristablauf

### 2. Nebenbestimmungen nach §§ 36-39 VwVfG

#### 2.1 Typen von Nebenbestimmungen
- **Bedingung (§ 36 VwVfG)**
  - Aufschiebende Bedingung: Wirksamkeit abhängig von Ereigniseintritt
  - Auflösende Bedingung: Wirksamkeit endet bei Ereigniseintritt
- **Auflage (§ 36 VwVfG)**
  - Verpflichtung zu einem Tun, Dulden oder Unterlassen
- **Befristung (§ 36 VwVfG)**
  - Zeitliche Begrenzung der Wirksamkeit
- **Widerrufsvorbehalt (§ 36 VwVfG)**
  - Behörde behält sich Widerruf vor
- **Kostenvorbehalt**
  - Vorbehalt der Kostentragung

#### 2.2 Rechtmäßigkeitsvoraussetzungen
- **Ermächtigungsgrundlage vorhanden**
- **Sachlicher Zusammenhang mit Hauptakt**
- **Verhältnismäßigkeit gewahrt**
- **Bestimmtheit ausreichend**

### 3. Verfahrensarten nach VwVfG

#### 3.1 Allgemeines Verwaltungsverfahren (§§ 9ff VwVfG)
- Antragstellung
- Behördliche Prüfung
- Anhörung der Beteiligten (§ 28 VwVfG)
- Entscheidung

#### 3.2 Besondere Verfahrensarten
- **Planfeststellungsverfahren (§§ 72ff VwVfG)**
- **Plangenehmigungsverfahren (§ 74 VwVfG)**
- **Massenverfahren**
- **Eilverfahren**

### 4. Wirksamkeit und Bestandskraft

#### 4.1 Wirksamkeit (§ 43 VwVfG)
- **Bekanntgabe erforderlich**
- **Sofortige Vollziehbarkeit (§ 80 VwGO)**
- **Vollstreckbarkeit**

#### 4.2 Bestandskraft
- **Formelle Bestandskraft**: Unanfechtbarkeit
- **Materielle Bestandskraft**: Bindungswirkung

### 5. Aufhebung von Verwaltungsakten

#### 5.1 Rücknahme (§ 48 VwVfG)
- Bei rechtswidrigen Verwaltungsakten
- Ermessen der Behörde
- Vertrauensschutz zu beachten

#### 5.2 Widerruf (§ 49 VwVfG)
- Bei rechtmäßigen Verwaltungsakten
- Nur bei Widerrufsvorbehalt oder besonderen Umständen
- Entschädigungspflicht möglich

---

## UDS3 Metadaten-Felder für Verwaltungsakte

### Grundklassifikation
```json
{
  "verwaltungsakt_art": "",           // AUSDRÜCKLICH | KONKLUDENT | SCHWEIGEN
  "verwaltungsakt_wirkung": "",       // BEGÜNSTIGEND | BELASTEND | NEUTRAL
  "verfahrenstyp": "",               // ALLGEMEIN | PLANFESTSTELLUNG | PLANGENEHMIGUNG | MASSENVERFAHREN | EILVERFAHREN
  "entscheidungsform": "",           // BESCHEID | VERFÜGUNG | GENEHMIGUNG | ERLAUBNIS | UNTERSAGUNG
  "bestandskraft_status": "",        // FORMELL_BESTANDSKRÄFTIG | MATERIELL_BESTANDSKRÄFTIG | ANFECHTBAR | VOLLSTRECKBAR
}
```

### Nebenbestimmungen
```json
{
  "nebenbestimmungen": {
    "vorhanden": false,              // Boolean
    "typen": [],                     // Array: BEDINGUNG | AUFLAGE | BEFRISTUNG | WIDERRUFSVORBEHALT | KOSTENVORBEHALT
    "bedingung_typ": "",            // AUFSCHIEBEND | AUFLÖSEND
    "auflage_inhalt": "",           // String: Beschreibung der Auflage
    "befristung_datum": "",         // ISO Date: Enddatum der Befristung
    "widerruf_grund": "",           // String: Grund für Widerrufsmöglichkeit
    "rechtmäßigkeit_geprüft": false // Boolean: Ob Nebenbestimmungen rechtmäßig
  }
}
```

### Verfahrensstatus
```json
{
  "verfahrensstatus": {
    "aktueller_stand": "",          // EINGELEITET | ANHÖRUNG_LÄUFT | ENTSCHIEDEN | BESTANDSKRÄFTIG | AUFGEHOBEN
    "anhörung_erforderlich": false, // Boolean nach § 28 VwVfG
    "anhörung_durchgeführt": false, // Boolean
    "anhörung_datum": "",          // ISO Date
    "frist_entscheidung": "",      // ISO Date: Entscheidungsfrist
    "bekanntgabe_datum": "",       // ISO Date: Datum der Bekanntgabe
    "rechtsmittel_frist": "",      // ISO Date: Ende der Widerspruchsfrist
    "sofort_vollziehbar": false    // Boolean nach § 80 VwGO
  }
}
```

### Rechtliche Bewertung
```json
{
  "rechtsbewertung": {
    "ermächtigungsgrundlage": "",   // String: Rechtsnorm
    "ermessen_art": "",            // GEBUNDEN | INTENDIERTES_ERMESSEN | AUSWAHLERMESSEN
    "ermessen_ausgeübt": false,     // Boolean
    "verhältnismäßigkeit": {
      "geeignet": null,             // Boolean | null
      "erforderlich": null,         // Boolean | null  
      "angemessen": null           // Boolean | null
    },
    "vertrauensschutz": {
      "schutzwürdig": null,        // Boolean | null
      "abwägung_erforderlich": false // Boolean
    }
  }
}
```

### Aufhebung/Änderung
```json
{
  "aufhebung": {
    "möglich": null,               // Boolean | null
    "art": "",                    // RÜCKNAHME | WIDERRUF | ÄNDERUNG
    "grund": "",                  // String: Grund für Aufhebung
    "frist": "",                  // ISO Date: Aufhebungsfrist
    "entschädigungspflicht": null, // Boolean | null
    "verfahren_eingeleitet": false // Boolean
  }
}
```

---

## LLM-Prompts für Verwaltungsakte

### Verwaltungsakt-Klassifikation
```
"Analyse den vorliegenden Verwaltungsakt. 
1. Handelt es sich um einen begünstigenden oder belastenden Verwaltungsakt? 
2. Wird dem Adressaten ein Recht gewährt (begünstigend) oder eine Pflicht auferlegt (belastend)?
3. Ist die Entscheidung ausdrücklich formuliert oder ergibt sie sich aus dem Verhalten der Behörde?
Verwende nur Begriffe aus dem Text. Text: {text}"
```

### Nebenbestimmungen-Extraktion
```
"Identifiziere alle Nebenbestimmungen in diesem Verwaltungsakt:
1. Bedingungen: Gibt es Voraussetzungen für die Wirksamkeit? (wenn... dann...)
2. Auflagen: Welche Verpflichtungen werden dem Adressaten auferlegt? (Der Antragsteller hat zu...)
3. Befristungen: Gibt es zeitliche Begrenzungen? (bis zum..., für die Dauer von...)
4. Widerrufsvorbehalte: Behält sich die Behörde den Widerruf vor?
Liste alle gefundenen Nebenbestimmungen mit exakter Textstelle auf. Text: {text}"
```

### Verfahrensstatus-Analyse
```
"Analysiere den Verfahrensstand dieses Verwaltungsakts:
1. In welchem Stadium befindet sich das Verfahren?
2. Wurde eine Anhörung durchgeführt? (Suche nach 'Anhörung', 'Stellungnahme', 'Gelegenheit zur Äußerung')
3. Wann wurde der Bescheid bekannt gegeben?
4. Gibt es Hinweise auf Rechtsmittelfristen oder sofortige Vollziehbarkeit?
Extrahiere alle relevanten Daten und Fristen. Text: {text}"
```

### Rechtmäßigkeitsprüfung
```
"Prüfe die rechtlichen Grundlagen dieses Verwaltungsakts:
1. Welche Ermächtigungsgrundlage wird genannt? (Rechtsgrundlage, Paragraf)
2. Handelt es sich um gebundene Entscheidung oder Ermessen?
3. Werden Verhältnismäßigkeitsaspekte erwähnt?
4. Gibt es Hinweise auf Vertrauensschutz oder erworbene Rechte?
Extrahiere nur explizit genannte rechtliche Bewertungen. Text: {text}"
```

---

## Implementierungsplan

### Phase 1: Grundstruktur
1. Neue Metadaten-Felder zu `default_metadata.json` hinzufügen
2. Validation Rules im Postprocessor erweitern  
3. Grundlegende LLM-Prompts implementieren

### Phase 2: Extractor-Erweiterung
1. `_extract_uds3_verwaltungsakte()` Methode im Preprocessor
2. Automatische Erkennung von Verwaltungsakt-Typen
3. Nebenbestimmungen-Parser entwickeln

### Phase 3: Verfahrensanalyse
1. Verfahrensstatus-Tracking implementieren
2. Fristenberechnung automatisieren
3. Rechtsmittel-Hinweise extrahieren

### Phase 4: Rechtsbewertung
1. Ermächtigungsgrundlagen-Mapping
2. Verhältnismäßigkeits-Indikatoren
3. Aufhebungsvoraussetzungen-Check

### Phase 5: UI Integration
1. Covina-Interface für Verwaltungsakte
2. Verfahrensstatus-Dashboard
3. Fristenüberwachung-System
