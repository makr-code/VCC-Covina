# Task 6: NLP → Neo4j Full Persistence - Quick Start Guide

**Erstellt:** 30. Oktober 2025  
**Status:** Ready to Execute (wartet auf Task 5 Completion)

---

## 📋 Prerequisites

**Task 5 muss abgeschlossen sein:**
- ✅ NLP Batch Extraction complete
- ✅ Output file exists: `data/nlp/entities_full.jsonl`
- ✅ Expected: ~3,618 documents, ~760k entities

**Neo4j Datenbank:**
- ✅ Neo4j läuft auf: `bolt://192.168.178.94:7687`
- ✅ Credentials: User `neo4j` (Password aus config_local.py)
- ✅ Existing data: 162k Document nodes (Phase L1-L3 ✅)

---

## 🚀 Execution

### Dry-Run Mode (Test ohne DB-Writes)
```powershell
# Test-Lauf ohne echte Neo4j-Writes
python scripts\run_nlp_neo4j_persistence.py --dry-run
```

**Output:**
- Simuliert alle Operations
- Zeigt Progress & Statistiken
- **Kein Neo4j-Write!**
- ETA: ~5-10 Sekunden

---

### Production Mode (Echte Persistierung)
```powershell
# PRODUCTION: Echte Neo4j-Writes!
python scripts\run_nlp_neo4j_persistence.py
```

**Output:**
- Erstellt LegalConcept, LegalNorm, Authority Nodes
- Verlinkt mit Document Nodes (MENTIONS, CITES, REFERENCES_AUTHORITY)
- Checkpoint-Logging alle 500 Dokumente
- ETA: **~30 Minuten** (210 docs/min)

---

## 📊 Expected Results

**Input:**
- `data/nlp/entities_full.jsonl`
- ~3,618 documents
- ~760k entities (PER, ORG, LOC, MISC)
- ~8.2k relations (CITES_NORM, HAS_JURISDICTION)

**Output (Neo4j Nodes):**
- **LegalConcept Nodes:** ~600k (from entities)
  - Labels: ORG, LOC, MISC, PER
  - Properties: name, label, source, extraction_count
  
- **LegalNorm Nodes:** ~6k (from CITES_NORM relations)
  - Properties: name, citation_count
  
- **Authority Nodes:** ~2k (from HAS_JURISDICTION relations)
  - Properties: name, mention_count

**Output (Neo4j Relationships):**
- **Document→LegalConcept (MENTIONS):** ~600k
- **Document→LegalNorm (CITES):** ~6k
- **Document→Authority (REFERENCES_AUTHORITY):** ~2k
- **Total Relations:** ~608k new + 1.6k existing = **~610k total**

---

## 📈 Performance Benchmarks

**From Phase L4 Testing (435 docs):**
- Processing Speed: **~210 docs/min**
- Entities per Doc: **~140 entities**
- Relations per Doc: **~2.3 relations**
- Neo4j Write Latency: ~50ms per entity

**Expected for Full Batch (3,618 docs):**
- Duration: **~17 minutes** (3,618 / 210)
- Peak Memory: ~500 MB (streaming JSONL)
- Neo4j Operations: ~610k MERGE + CREATE operations

---

## 🔍 Progress Monitoring

**Checkpoint Output (every 500 docs):**
```
[NLP-PERSIST] Checkpoint: 500 docs | 70,000 entities | 1,150 relations | 0 errors
[NLP-PERSIST] Checkpoint: 1000 docs | 140,000 entities | 2,300 relations | 0 errors
[NLP-PERSIST] Checkpoint: 1500 docs | 210,000 entities | 3,450 relations | 0 errors
...
```

**Final Summary:**
```
Task 6: COMPLETE!
================================================================================
End Time:        2025-10-30 15:45:23
Duration:        1024.3 seconds (17.1 minutes)

Statistics:
  Docs processed:     3,618
  Entities created:   607,320
  Relations created:  8,201
  Errors:             0

Performance:
  Processing speed:   211.5 docs/min
  Entities per doc:   167.8
  Relations per doc:  2.3
```

---

## 🗄️ Neo4j Data Model

### Node Types Created

**1. LegalConcept (from Entities)**
```cypher
(:LegalConcept {
    id: "nlp_org_Bundesgerichtshof",
    name: "Bundesgerichtshof",
    label: "ORG",
    source: "nlp_extraction",
    created_at: datetime(),
    extraction_count: 127  // Wie oft extrahiert
})
```

**2. LegalNorm (from CITES_NORM Relations)**
```cypher
(:LegalNorm {
    id: "nlp_norm_BGB § 433",
    name: "BGB § 433",
    source: "nlp_extraction",
    created_at: datetime(),
    citation_count: 45  // Wie oft zitiert
})
```

**3. Authority (from HAS_JURISDICTION Relations)**
```cypher
(:Authority {
    id: "nlp_authority_Landgericht München",
    name: "Landgericht München",
    source: "nlp_extraction",
    created_at: datetime(),
    mention_count: 23  // Wie oft erwähnt
})
```

### Relationship Types Created

**1. Document MENTIONS LegalConcept**
```cypher
(:Document {file_path: "Y:\\data\\doc_123.md"})
-[:MENTIONS {created_at: datetime()}]->
(:LegalConcept {name: "Bundesgerichtshof"})
```

**2. Document CITES LegalNorm**
```cypher
(:Document {file_path: "Y:\\data\\doc_456.md"})
-[:CITES {created_at: datetime()}]->
(:LegalNorm {name: "BGB § 433"})
```

**3. Document REFERENCES_AUTHORITY Authority**
```cypher
(:Document {file_path: "Y:\\data\\doc_789.md"})
-[:REFERENCES_AUTHORITY {created_at: datetime()}]->
(:Authority {name: "Landgericht München"})
```

---

## 🔧 Configuration Options

### Environment Variables

```powershell
# Input/Output
$env:NLP_INPUT_JSONL = "data/nlp/entities_full.jsonl"

# Performance
$env:NLP_CHECKPOINT_INTERVAL = "500"  # Progress logging interval

# Neo4j Connection
$env:NEO4J_URI = "bolt://192.168.178.94:7687"
$env:NEO4J_USER = "neo4j"
$env:NEO4J_PASSWORD = "..."  # Falls nicht in config_local.py
```

### Command-Line Arguments

```powershell
# Dry-Run Mode
python scripts\run_nlp_neo4j_persistence.py --dry-run

# Custom input file
python scripts\run_nlp_neo4j_persistence.py --input "data/nlp/custom.jsonl"

# Custom checkpoint interval (every 1000 docs)
python scripts\run_nlp_neo4j_persistence.py --checkpoint 1000
```

---

## 📝 Output Files

**1. Summary File**
- Location: `data/nlp/persistence_summary.txt`
- Content: Final statistics, performance metrics
- Created: Automatically after completion

**2. Console Output**
- Real-time progress updates
- Checkpoint statistics
- Error messages (if any)

---

## 🐛 Troubleshooting

### Problem: "Input file not found"
**Ursache:** Task 5 (NLP Extraction) noch nicht abgeschlossen  
**Lösung:** Warte bis `data/nlp/entities_full.jsonl` existiert

### Problem: "UDS3RelationsCore nicht verfügbar"
**Ursache:** UDS3 Modul nicht im Python Path  
**Lösung:** Script erkennt automatisch und fällt zu Dry-Run

### Problem: "Neo4j connection failed"
**Ursache:** Neo4j nicht erreichbar oder falsche Credentials  
**Lösung:** 
1. Check Neo4j läuft: `http://192.168.178.94:7474`
2. Verify credentials in `uds3/config_local.py`
3. Test connection: `python tests\test_neo4j_connection.py`

### Problem: "Errors > 0 in final statistics"
**Ursache:** JSONL-Parsing-Fehler oder Neo4j-Timeouts  
**Lösung:**
1. Check `data/nlp/entities_full.jsonl` für malformed JSON
2. Increase Neo4j connection timeout in UDS3 config
3. Re-run nur für failed documents (filter JSONL)

---

## ✅ Verification After Completion

### 1. Node Counts
```cypher
// Neo4j Browser: http://192.168.178.94:7474
MATCH (c:LegalConcept) RETURN count(c) as legal_concepts;
MATCH (n:LegalNorm) RETURN count(n) as legal_norms;
MATCH (a:Authority) RETURN count(a) as authorities;
```

**Expected:**
- LegalConcept: ~600k
- LegalNorm: ~6k
- Authority: ~2k

### 2. Relationship Counts
```cypher
MATCH ()-[r:MENTIONS]->() RETURN count(r) as mentions;
MATCH ()-[r:CITES]->() RETURN count(r) as citations;
MATCH ()-[r:REFERENCES_AUTHORITY]->() RETURN count(r) as references;
```

**Expected:**
- MENTIONS: ~600k
- CITES: ~6k
- REFERENCES_AUTHORITY: ~2k

### 3. Sample Queries
```cypher
// Most frequently mentioned concepts
MATCH (c:LegalConcept)
RETURN c.name, c.label, c.extraction_count
ORDER BY c.extraction_count DESC
LIMIT 10;

// Most cited norms
MATCH (n:LegalNorm)
RETURN n.name, n.citation_count
ORDER BY n.citation_count DESC
LIMIT 10;

// Documents with most relations
MATCH (d:Document)-[r]->()
RETURN d.file_path, count(r) as relation_count
ORDER BY relation_count DESC
LIMIT 10;
```

---

## 🎯 Next Steps After Completion

**Task 6 Complete → Phase L5 Optional:**
- L5: Citation Network Analytics
- L5: Authority Ranking
- L5: Jurisdiction Mapping
- L5: Semantic Clustering

**Documentation Updates:**
- Update `copilot-todo.md` (mark Task 6 complete)
- Update Wiki: `Project-Status.md` (add L4 results)
- Update Wiki: `Database-Architecture.md` (add new node types)

---

**Letzte Aktualisierung:** 30. Oktober 2025  
**Status:** Ready to Execute (wartet auf Task 5)  
**ETA:** ~17 Minuten (Production Mode)
