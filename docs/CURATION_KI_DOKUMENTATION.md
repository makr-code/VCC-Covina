# 🤖 Curation GUI - KI/NLP-Unterstützung

## Stand: 5. Oktober 2025, 14:00 Uhr

## ✨ Implementierte Features

### 🎯 Kern-Funktionen

Das Kuratierungs-GUI wurde mit **lokaler KI/NLP-Unterstützung** erweitert:

1. **Automatische Dokumentanalyse**
   - Läuft komplett lokal ohne Internet-Verbindung
   - Verwendet spaCy mit deutschem Sprachmodell
   - Analysiert Dokumente in Sekunden

2. **KI-Vorschläge für Metadaten**
   - ✅ Dokumenttyp-Klassifikation (Gesetz, Urteil, Vertrag, etc.)
   - ✅ Rechtsgebiet-Erkennung (Zivil-, Straf-, Verwaltungsrecht, etc.)
   - ✅ Automatische Zusammenfassung (3 Sätze)
   - ✅ Keyword-Extraktion (Top 15 Schlagwörter)
   - ✅ Named Entity Recognition (Personen, Organisationen, Orte)
   - ✅ Juridische Entitäten (Gesetze, Paragraphen, Gerichte)
   - ✅ Text-Statistiken (Wörter, Sätze, Durchschnittslängen)

3. **Interaktive Kuratoren-Unterstützung**
   - Ein-Klick Analyse: "🧠 Dokument analysieren"
   - Vorschau der KI-Ergebnisse mit Konfidenz-Anzeige
   - Übernahme-Optionen:
     - "✅ Alle Vorschläge übernehmen" - Füllt alle Felder automatisch
     - "❌ Vorschläge verwerfen" - Löscht Vorschläge
   - Kurator kann Vorschläge einzeln annehmen/ablehnen/editieren

## 📦 Technologie-Stack

### Hauptbibliotheken

```python
# Kern-NLP
spacy==3.8.7              # NLP Framework
de_core_news_lg==3.8.0    # Deutsches Sprachmodell (567MB)

# Dokumenten-Verarbeitung
pypdf==6.1.1              # PDF Textextraktion
python-docx==1.2.0        # Word Dokumente

# GUI
tkinter                   # Bereits in Python enthalten
```

### Architektur

```
curation_gui.py
├── CurationGUI (Hauptklasse)
│   ├── setup_ai_suggestions_section()  # KI-UI
│   ├── analyze_document_with_ai()      # Async-Analyse
│   ├── _extract_text_from_file()       # Text-Extraktion
│   ├── _display_ai_suggestions()       # Ergebnis-Anzeige
│   ├── accept_all_suggestions()        # Vorschläge übernehmen
│   └── clear_suggestions()             # Vorschläge verwerfen

curation_nlp_service.py
├── CurationNLPService (Singleton)
│   ├── analyze_document()              # Vollanalyse
│   ├── generate_summary()              # Zusammenfassung
│   ├── extract_keywords()              # Keywords
│   ├── extract_entities()              # Named Entities
│   ├── extract_legal_entities()        # Juridische Entities
│   ├── classify_document_type()        # Typ-Klassifikation
│   ├── analyze_sentiment()             # Sentiment-Analyse
│   └── suggest_metadata()              # Metadaten-Vorschläge
```

## 🚀 Verwendung

### 1. Installation

```bash
# Installiere Abhängigkeiten
pip install -r requirements-curation-nlp.txt

# Lade deutsches Sprachmodell (einmalig, ~567MB)
python -m spacy download de_core_news_lg
```

### 2. GUI starten

```bash
python curation_gui.py
```

### 3. Workflow

1. **Dokument laden**: "📁 Dokument auswählen"
   - Unterstützt: PDF, DOCX, TXT, MD

2. **KI-Analyse starten**: "🧠 Dokument analysieren"
   - Läuft im Hintergrund (Threading)
   - Dauert 5-30 Sekunden je nach Dokumentgröße

3. **Ergebnisse prüfen**:
   ```
   ✨ Analyse abgeschlossen (Konfidenz: 85%)
   
   📋 DOKUMENTTYP: RECHTSPRECHUNG
   📚 RECHTSGEBIET: Verwaltungsrecht
   
   📝 ZUSAMMENFASSUNG:
   Das Bundesverfassungsgericht hat in seinem Urteil...
   
   🔑 KEYWORDS (15 gefunden):
   bundesverfassungsgericht, versammlungsfreiheit, grundgesetz...
   
   👤 PERSONEN:
   Dr. Maria Schmidt, Prof. Hans Müller
   
   ⚖️ JURIDISCHE REFERENZEN:
   Gesetze: GG, VersG
   Paragraphen: § 12 Abs. 3 GG
   Gerichte: Bundesverfassungsgericht, OLG München
   ```

4. **Vorschläge übernehmen**: "✅ Alle Vorschläge übernehmen"
   - Füllt automatisch alle Formularfelder
   - Kurator kann nachträglich editieren

5. **Metadaten speichern**: Wie gewohnt als JSON expor{
    "logs": [
        {
            "outputFile": "com.example.argus.app-mergeArchiveOffDebugResources-90:/values-en-rCA/values-en-rCA.xml",
            "map": [
                {
                    "source": "C:\\Users\\mkrueger\\.gradle\\caches\\8.13\\transforms\\7867f3f62ab9e73d08cf8b2c81149022\\transformed\\preference-1.2.1\\res\\values-en-rCA\\values-en-rCA.xml",
                    "from": {
                        "startLines": "2,3,4,5,6,7,8",
                        "startColumns": "4,4,4,4,4,4,4",
                        "startOffsets": "105,173,260,334,468,637,717",
                        "endColumns": "67,86,73,133,168,79,75",
                        "endOffsets": "168,255,329,463,632,712,788"
                    },
                    "to": {
                        "startLines": "39,43,108,109,119,125,126",
                        "startColumns": "4,4,4,4,4,4,4",
                        "startOffsets": "3729,4076,11024,11098,11951,12554,12634",
                        "endColumns": "67,86,73,133,168,79,75",
                        "endOffsets": "3792,4158,11093,11227,12115,12629,12705"
                    }
                },
                {
                    "source": "C:\\Users\\mkrueger\\.gradle\\caches\\8.13\\transforms\\04229b02784ce9e8133a19254c4c6879\\transformed\\glance-appwidget-1.1.1\\res\\values-en-rCA\\values-en-rCA.xml",
                    "from": {
                        "startLines": "2,3,4",
                        "startColumns": "4,4,4",
                        "startOffsets": "55,246,352",
                        "endColumns": "190,105,114",
                        "endOffsets": "241,347,462"
                    },
                    "to": {
                        "startLines": "44,45,46",
                        "startColumns": "4,4,4",
                        "startOffsets": "4163,4354,4460",
                        "endColumns": "190,105,114",
                        "endOffsets": "4349,4455,4570"
                    }
                },
                {
                    "source": "C:\\Users\\mkrueger\\.gradle\\caches\\8.13\\transforms\\fb5183f94d9a086c2d3f5960db221c85\\transformed\\material3-release\\res\\values-en-rCA\\values-en-rCA.xml",
                    "from": {
                        "startLines": "2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "55,173,289,400,514,613,708,820,956,1072,1208,1292,1391,1482,1579,1698,1823,1927,2054,2177,2305,2467,2588,2704,2827,2952,3044,3142,3259,3383,3480,3582,3684,3814,3953,4059,4158,4234,4330,4424,4528,4615,4702,4804,4884,4968,5069,5170,5270,5369,5457,5563,5664,5768,5884,5964,6064",
                        "endColumns": "117,115,110,113,98,94,111,135,115,135,83,98,90,96,118,124,103,126,122,127,161,120,115,122,124,91,97,116,123,96,101,101,129,138,105,98,75,95,93,103,86,86,101,79,83,100,100,99,98,87,105,100,103,115,79,99,94",
                        "endOffsets": "168,284,395,509,608,703,815,951,1067,1203,1287,1386,1477,1574,1693,1818,1922,2049,2172,2300,2462,2583,2699,2822,2947,3039,3137,3254,3378,3475,3577,3679,3809,3948,4054,4153,4229,4325,4419,4523,4610,4697,4799,4879,4963,5064,5165,5265,5364,5452,5558,5659,5763,5879,5959,6059,6154"
                    },
                    "to": {
                        "startLines": "49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "4747,4865,4981,5092,5206,5305,5400,5512,5648,5764,5900,5984,6083,6174,6271,6390,6515,6619,6746,6869,6997,7159,7280,7396,7519,7644,7736,7834,7951,8075,8172,8274,8376,8506,8645,8751,8850,8926,9022,9116,9220,9307,9394,9496,9576,9660,9761,9862,9962,10061,10149,10255,10356,10460,10576,10656,10756",
                        "endColumns": "117,115,110,113,98,94,111,135,115,135,83,98,90,96,118,124,103,126,122,127,161,120,115,122,124,91,97,116,123,96,101,101,129,138,105,98,75,95,93,103,86,86,101,79,83,100,100,99,98,87,105,100,103,115,79,99,94",
                        "endOffsets": "4860,4976,5087,5201,5300,5395,5507,5643,5759,5895,5979,6078,6169,6266,6385,6510,6614,6741,6864,6992,7154,7275,7391,7514,7639,7731,7829,7946,8070,8167,8269,8371,8501,8640,8746,8845,8921,9017,9111,9215,9302,9389,9491,9571,9655,9756,9857,9957,10056,10144,10250,10351,10455,10571,10651,10751,10846"
                    }
                },
                {
                    "source": "C:\\Users\\mkrueger\\.gradle\\caches\\8.13\\transforms\\fbec8997159b718443be441e57ff2ef4\\transformed\\ui-release\\res\\values-en-rCA\\values-en-rCA.xml",
                    "from": {
                        "startLines": "3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "181,273,355,449,548,634,716,806,895,979,1057,1139,1212,1296,1372,1444,1514,1591,1657",
                        "endColumns": "91,81,93,98,85,81,89,88,83,77,81,72,83,75,71,69,76,65,119",
                        "endOffsets": "268,350,444,543,629,711,801,890,974,1052,1134,1207,1291,1367,1439,1509,1586,1652,1772"
                    },
   