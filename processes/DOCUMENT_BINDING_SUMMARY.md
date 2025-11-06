# Dokument-Bindung & Zeitbasierte Queries - Zusammenfassung

**Datum:** 31. Oktober 2025  
**Version:** 1.0  
**Status:** ✅ Implementation komplett

---

## 🎯 Problem gelöst

**Frage:** Wie werden Dokumente an Prozesse/Steps gebunden, damit zeitbasierte Abfragen möglich sind?  
**Lösung:** Neo4j-Modell mit Document-Knoten, Multi-Process/Step-Bindungen und Temporal Canon für Gültigkeit + Wiederholungen.

---

## 📊 Implementierte Features

### 1. Neo4j Graph-Modell

**Document Node:**
```cypher
(:Document {
  id, key, title, type, source_uri,
  created_at, updated_at, published_at,
  metadata
})
```

**Bindungen (Multi-Process/Step möglich):**
```cypher
(doc)-[:RELATES_TO_PROCESS {role, confidence}]->(p:Process)
(doc)-[:EVIDENCES_STEP]->(s:Step)
(doc)-[:INPUT_OF_STEP]->(s:Step)
(doc)-[:OUTPUT_OF_STEP]->(s:Step)
```

**Zeitliche Gültigkeit:**
```cypher
(doc)-[:EFFECTIVE_FROM]->(d1:Date)
(doc)-[:EFFECTIVE_UNTIL]->(d2:Date)
(doc)-[:OCCURS_ON]->(d:Date)  # published_at
```

**Wiederholungen (Recurrence):**
```cypher
(:Recurrence {
  id, freq, interval, byday, bymonthday,
  until, count, timezone, rrule
})

(Process|Step|Document)-[:HAS_RECURRENCE]->(r:Recurrence)

(:StepOccurrence {id, step_id, occurred_at})
  -[:OF_STEP]->(s:Step)
  -[:OCCURS_ON]->(d:Date)
```

---

### 2. Neo4j Constraints & Indices

**Neu hinzugefügt:**
```cypher
-- Constraints
CREATE CONSTRAINT document_id_unique FOR (d:Document) REQUIRE d.id IS UNIQUE
CREATE CONSTRAINT recurrence_id_unique FOR (r:Recurrence) REQUIRE r.id IS UNIQUE
CREATE CONSTRAINT step_occurrence_id_unique FOR (o:StepOccurrence) REQUIRE o.id IS UNIQUE

-- Indices
CREATE INDEX document_key FOR (d:Document) ON (d.key)
CREATE INDEX document_type FOR (d:Document) ON (d.type)
CREATE INDEX document_created_at FOR (d:Document) ON (d.created_at)
CREATE INDEX document_published_at FOR (d:Document) ON (d.published_at)

CREATE INDEX recurrence_freq FOR (r:Recurrence) ON (r.freq)
CREATE INDEX recurrence_until FOR (r:Recurrence) ON (r.until)

CREATE INDEX step_occurrence_step_id FOR (o:StepOccurrence) ON (o.step_id)
CREATE INDEX step_occurrence_occurred_at FOR (o:StepOccurrence) ON (o.occurred_at)
```

**Setup:**
```python
from processes.graph.setup_indices import setup_all_indices
from uds3.database.database_api_neo4j import Neo4jGraphBackend

graph = Neo4jGraphBackend(config)
graph.connect()
counts = setup_all_indices(graph)
# Returns: {"temporal": 9, "process": 43, "total": 52}
```

---

### 3. ProcessGraphWriter - Neue Methoden

**Dokument erstellen:**
```python
document = {
    "id": "doc_001",
    "key": "guideline-2025",
    "title": "Prozess-Leitlinie 2025",
    "type": "guideline",
    "source_uri": "https://example.com/doc.pdf",
    "published_at": "2025-10-31T10:00:00",
    "metadata": {"author": "System"}
}
doc_id = await writer.write_document(document)
```

**An Prozess binden:**
```python
await writer.link_document_to_process(
    document_id="doc_001",
    process_id="proc_123",
    role="guideline",  # source | evidence | output | input | guideline
    confidence=0.95
)
```

**An Step binden:**
```python
await writer.link_document_to_step(
    document_id="doc_001",
    step_id="step_456",
    relation="EVIDENCES_STEP"  # EVIDENCES_STEP | INPUT_OF_STEP | OUTPUT_OF_STEP
)
```

**Gültigkeit setzen:**
```python
await writer.link_document_validity(
    document_id="doc_001",
    valid_from="2025-11-01",  # ISO date YYYY-MM-DD
    valid_until="2026-10-31"
)
```

**Wiederholung erstellen:**
```python
recurrence = {
    "id": "rec_001",
    "freq": "MONTHLY",  # DAILY | WEEKLY | MONTHLY | YEARLY
    "interval": 1,
    "bymonthday": [15],  # Am 15. des Monats
    "until": "2026-12-31",
    "timezone": "Europe/Berlin"
}
await writer.write_recurrence(recurrence)
await writer.link_entity_recurrence("Step", "step_456", "rec_001")
```

**Termine materialisieren:**
```python
# Für wiederkehrenden Step die nächsten 6 Monate erzeugen
dates = ["2025-11-15", "2025-12-15", "2026-01-15", "2026-02-15", "2026-03-15", "2026-04-15"]
count = await writer.materialize_occurrences("Step", "step_456", dates)
# → Erzeugt 6x (:StepOccurrence)-[:OCCURS_ON]->(:Date)
```

---

### 4. REST API Endpoints (Main Backend)

**GET /processes/{process_id}/documents**
```powershell
# Alle Dokumente eines Prozesses
Invoke-RestMethod "http://127.0.0.1:45678/processes/PROC_123/documents"

# Mit Filtern (Gültigkeit & Rolle)
Invoke-RestMethod "http://127.0.0.1:45678/processes/PROC_123/documents?from_date=2025-11-01&until_date=2025-12-31&role=guideline"
```

**Response:**
```json
{
  "count": 2,
  "results": [
    {
      "document_id": "doc_001",
      "key": "guideline-2025",
      "title": "Prozess-Leitlinie 2025",
      "type": "guideline",
      "source_uri": "https://example.com/doc.pdf",
      "published_at": "2025-10-31T10:00:00",
      "valid_from": "2025-11-01",
      "valid_until": "2026-10-31",
      "role": "guideline",
      "confidence": 0.95
    }
  ]
}
```

**GET /processes/steps/{step_id}/documents**
```powershell
# Alle Dokumente eines Steps
Invoke-RestMethod "http://127.0.0.1:45678/processes/steps/STEP_456/documents"

# Nur gültig an einem Datum
Invoke-RestMethod "http://127.0.0.1:45678/processes/steps/STEP_456/documents?on_date=2025-11-15"
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "document_id": "doc_001",
      "key": "guideline-2025",
      "title": "Prozess-Leitlinie 2025",
      "type": "guideline",
      "relation": "EVIDENCES_STEP",
      "valid_from": "2025-11-01",
      "valid_until": "2026-10-31"
    }
  ]
}
```

**GET /processes/{process_id}/calendar**
```powershell
# Kalenderansicht: Steps, Occurrences, Dokumente im Zeitraum
Invoke-RestMethod "http://127.0.0.1:45678/processes/PROC_123/calendar?from_date=2025-11-01&until_date=2025-11-30"
```

**Response:**
```json
{
  "count": 8,
  "results": [
    {
      "type": "step",
      "id": "step_001",
      "name": "Antragsprüfung",
      "date": "2025-11-05"
    },
    {
      "type": "occurrence",
      "id": "step_456:2025-11-15",
      "name": "Review Step",
      "date": "2025-11-15"
    },
    {
      "type": "document",
      "id": "doc_001",
      "name": "Prozess-Leitlinie 2025",
      "date": "2025-11-01"
    }
  ]
}
```

---

## 🔍 Beispiel-Queries (Cypher)

### Dokumente zu Prozess im Zeitraum

```cypher
MATCH (p:Process {id: $pid})<-[:RELATES_TO_PROCESS]-(doc:Document)
OPTIONAL MATCH (doc)-[:EFFECTIVE_FROM]->(df:Date)
OPTIONAL MATCH (doc)-[:EFFECTIVE_UNTIL]->(dt:Date)
WHERE (df.iso IS NULL OR df.iso <= $until)
  AND (dt.iso IS NULL OR dt.iso >= $from)
RETURN doc.id, doc.title, doc.type, df.iso AS valid_from, dt.iso AS valid_until
ORDER BY coalesce(doc.published_at, doc.created_at) DESC
```

### Dokumente, die einen Step am Tag X belegen

```cypher
MATCH (s:Step {id: $sid})-[:OCCURS_ON]->(ds:Date {iso: $on_date})
MATCH (doc:Document)-[:EVIDENCES_STEP]->(s)
OPTIONAL MATCH (doc)-[:EFFECTIVE_FROM]->(df:Date)
OPTIONAL MATCH (doc)-[:EFFECTIVE_UNTIL]->(dt:Date)
WHERE (df.iso IS NULL OR df.iso <= ds.iso)
  AND (dt.iso IS NULL OR dt.iso >= ds.iso)
RETURN doc.id, doc.title, doc.type
```

### Nächste Termine für wiederkehrenden Step

```cypher
MATCH (s:Step {id: $sid})-[:HAS_RECURRENCE]->(r:Recurrence)
MATCH (occ:StepOccurrence)-[:OF_STEP]->(s)-[:OCCURS_ON]->(d:Date)
WHERE d.iso >= $today AND d.iso <= $horizon
RETURN d.iso AS date, s.title AS step_name
ORDER BY d.iso ASC
```

---

## 📊 Use Cases

### 1. Multi-Process-Verwendung
Ein Dokument kann mehrere Prozesse evidenzieren:
```python
await writer.link_document_to_process("doc_001", "proc_A", role="guideline")
await writer.link_document_to_process("doc_001", "proc_B", role="evidence", confidence=0.75)
```

### 2. Zeitliche Gültigkeit prüfen
"Welche Dokumente waren am 15.11.2025 gültig?"
```cypher
WHERE (df.iso <= '2025-11-15') AND (dt.iso IS NULL OR dt.iso >= '2025-11-15')
```

### 3. Wiederkehrende Prozesse
Monatliches Reporting:
1. Recurrence erstellen (freq="MONTHLY", bymonthday=[1])
2. Occurrences für nächste 12 Monate materialisieren
3. Kalender-Endpoint liefert alle Termine

### 4. Mining/Inference-Integration
Automatische Dokument-Prozess-Bindung via NLP:
- ChromaDB Step-Similarity → confidence score
- RELATES_TO_PROCESS mit role="inferred" + confidence

---

## 📁 Dateien

```
processes/
├─ graph/
│  ├─ setup_indices.py              # +3 Constraints, +9 Indices (Document/Recurrence/StepOccurrence)
│  └─ process_graph_writer.py       # +8 Methoden (write_document, link_*, write_recurrence, materialize_occurrences)
├─ gap/
│  └─ engine.py                      # detect_temporal_inconsistencies (robuster: coalesce(d.date, d.iso))
└─ IMPLEMENTATION_STATUS.md          # Abschnitt "Dokumentbindung & Recurrence" aktualisiert

backend/queries/
└─ process_queries.py                # +3 Endpoints (GET /documents, GET /steps/{id}/documents, GET /calendar)
```

---

## ✅ Status

- [x] Neo4j Constraints/Indices (Document, Recurrence, StepOccurrence)
- [x] ProcessGraphWriter erweitert (Document-Bindung + Recurrence)
- [x] Temporal Canon Integration (EFFECTIVE_FROM/UNTIL, OCCURS_ON)
- [x] REST API Endpoints (3x GET für Dokumente/Kalender)
- [x] Cypher-Queries für zeitbasierte Abfragen
- [x] Multi-Process/Step-Bindung möglich
- [x] Wiederholungen (Recurrence) scaffold
- [x] Materialisierte Occurrences (StepOccurrence)

---

## 🚀 Nächste Schritte (optional)

- [ ] **Recurrence-Utility:** Python-Funktion mit `dateutil.rrule` für on-the-fly oder Batch-Materialisierung
- [ ] **Ingestion-Endpoint:** `POST /ingestion/documents` für Upload + Binding in einem Call
- [ ] **NLP/LLM-Mining:** Automatische Dokument-Prozess-Bindung via ChromaDB Step-Similarity
- [ ] **Review-Queue-Integration:** Dokumente als Evidenz für Gap-Findings nutzen

---

**Ende der Zusammenfassung**
