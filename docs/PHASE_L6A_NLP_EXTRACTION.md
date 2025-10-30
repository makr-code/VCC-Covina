# Phase L6A: NLP-Extraktion & Semantische Analyse

**Ziel:** Automatische Extraktion von Entitäten, Relationen und Domänen aus den Markdown-Inhalten (`data/uploads/scan_*/markdown/*.md`).

## Vorgehen
1. Named Entity Recognition (NER) mit spaCy (chunked)
2. Domain Classification (optional: Transformers, Zero-Shot per Env-Flag)
3. Relation Extraction (Stub)
4. Batch- und Parallelverarbeitung für große Datenmengen
5. YAML/JSON-Export der Ergebnisse (optional JSONL-Streaming)

## Umsetzung
- Neues Modul: `ingestion/nlp_extraction.py`
- Funktionen: `extract_entities`, `classify_domain`, `extract_relations`
- Chunking: `SPACY_CHUNK_SIZE` (Default: 100k), weiche Grenzen via `\n\n`
- spaCy Max Length: `SPACY_MAX_LENGTH` (Default: 1.000.000)
- Zero-Shot: `NLP_ENABLE_ZERO_SHOT` (Default: false), nur Sample (2k Zeichen)
- Optionaler JSONL-Writer: `NLP_WRITE_JSONL=true`, Pfad via `NLP_OUTPUT_JSONL`

## Environment-Variablen
- SPACY_MODEL: Name des spaCy-Modells (default: de_core_news_md)
- SPACY_MAX_LENGTH: Maximale Textlänge pro spaCy-Durchlauf (default: 1000000)
- SPACY_CHUNK_SIZE: Chunk-Größe in Zeichen (default: min(100000, SPACY_MAX_LENGTH-1))
- NLP_ENABLE_ZERO_SHOT: true|false, Zero-Shot Domain-Classification via Transformers (default: false)
- NLP_INPUT_DIR: Eingabeverzeichnis für Markdown (default: data/uploads)
- NLP_WRITE_JSONL: true|false, Ergebnisse als JSONL streamen (default: false)
- NLP_OUTPUT_JSONL: Pfad zur JSONL-Datei (default: data/nlp/entities.jsonl)

## Status
- [x] Modul-Design
- [x] Implementierung
- [x] Smoke-Test (1 Datei, E088 vermieden)
- [x] Testlauf auf 37 Markdown-Dateien (3.892 Entities, 66 Relations, 0 Fehler)
- [x] Ergebnis-Export (JSONL)
- [x] Analyse-Tool (`tests/analyze_nlp_jsonl.py`)
- [ ] Vollständiger Lauf auf allen 3.618 Dateien (optional)
- [ ] Integration in Ingestion-Pipeline

## Test-Ergebnisse (37 Dateien)
- **Total Documents:** 37
- **Total Entities:** 3.892 (Durchschnitt: 105 pro Dokument)
- **Total Relations:** 66 (60× HAS_JURISDICTION, 6× CITES_NORM)
- **Errors:** 0
- **Top Entity Labels:** MISC (1.694), ORG (1.131), LOC (814), PER (253)
- **Domain Distribution:** Unbekannt (37) – Zero-Shot deaktiviert für Performance

## Hinweise zur Performance
- Lange Dokumente werden in Chunks verarbeitet, um spaCy E088 zu vermeiden.
- Zero-Shot-Classification ist standardmäßig deaktiviert, da das Modell groß (~1.6GB) ist.
- Für schnelle Tests einzelne Dateien verarbeiten oder JSONL aktivieren.
- **Performance:** ~1-2 Dateien/Sekunde (abhängig von Dateigröße und CPU)
- **Empfehlung:** Für Production-Läufe auf allen Dateien: Batch-Processing mit Progress-Checkpoints

## Lessons Learned
- spaCy Chunking (SPACY_CHUNK_SIZE=100k) vermeidet E088-Fehler bei großen Dokumenten erfolgreich
- JSONL-Streaming mit Flush nach jeder Zeile bietet gute Crash-Recovery
- Regelbasierte Relation-Extraction findet ~1.8 Relations pro Dokument (hauptsächlich Zuständigkeiten)
- Entity-Extraction robust mit 0% Error-Rate auf 37 Test-Dokumenten
- Zero-Shot Domain-Classification zu langsam für Batch-Processing (deaktiviert empfohlen)
