# 🚀 Graph-RAG Quick Start Guide

**Ziel:** Graph-RAG Hybrid Retrieval in 10 Minuten zum Laufen bringen!

---

## 1. Installation (2 Minuten)

```powershell
# PowerShell im Covina-Verzeichnis
cd C:\VCC\Covina

# Automatische Installation
.\scripts\install_graph_rag.ps1

# ODER: Manuell
pip install rank-bm25>=0.2.2 neo4j>=5.14.0 sentence-transformers>=2.2.0 spacy>=3.6.0
python -m spacy download de_core_news_lg
```

**Überprüfen:**
```powershell
python -c "import rank_bm25, neo4j, sentence_transformers, spacy; print('✅ OK')"
```

---

## 2. Demo ausführen (3 Minuten)

```powershell
python examples\demo_graph_rag.py
```

**Erwartete Ausgabe:**
```
🚀 COVINA GRAPH-RAG DEMO
================================================================================

DEMO 1: BM25 Keyword Indexer
✅ Index erstellt: 4 Dokumente
🔍 Query: 'Antrag Wohngeld'
   1. doc1 (Score: 15.342)

DEMO 2: Reciprocal Rank Fusion (RRF)
✅ Fusion abgeschlossen: 5 Dokumente
   1. doc1 (RRF-Score: 0.0456)

DEMO 3: Cross-Encoder Re-Ranking
✅ Modell geladen: ms-marco-MiniLM-L-6-v2
   1. doc1 (Rerank Score: 0.923)

DEMO 4: Graph-Context-Synthese
✅ 4 Entities gefunden:
   Type: LegalReference, Value: §1 Abs. 1 WoGG

✅ Demo abgeschlossen!
```

---

## 3. Backend-Endpoint testen (2 Minuten)

**Backend starten:**
```powershell
# Anderes Terminal
python backend.py
```

**API-Request (Mock):**
```powershell
# PowerShell
$headers = @{"Content-Type"="application/json"}
$body = @{
    query = "Antrag Wohngeld"
    top_k = 5
    include_graph_context = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/graph-rag/search" -Method Post -Body $body -Headers $headers
```

**Erwartete Response:**
```json
{
  "query": "Antrag Wohngeld",
  "documents": [
    {
      "doc_id": "doc_0",
      "text": "Mock Graph-RAG result...",
      "score": 0.95,
      "graph_context": {
        "entities": [
          {"type": "LegalReference", "value": "§123 BGB"},
          {"type": "ProcessStep", "value": "Antrag Wohngeld"}
        ],
        "legal_refs": {"§123 BGB": "Anfechtbarkeit..."}
      }
    }
  ],
  "latency_ms": 45.2
}
```

**Swagger UI:** http://localhost:8000/docs → `/graph-rag/search` testen

---

## 4. Python API nutzen (3 Minuten)

**Beispiel-Script:**
```python
import asyncio
from ingestion.retrieval.bm25_indexer import BM25DocumentIndex
from ingestion.retrieval.fusion import ReciprocalRankFusion
from ingestion.retrieval.reranker import CrossEncoderReranker

async def main():
    # 1. BM25 Index erstellen
    docs = [
        {"id": "doc1", "text": "Antrag auf Wohngeld gemäß § 1 WoGG."},
        {"id": "doc2", "text": "BAföG-Antrag für Studierende."},
    ]
    
    indexer = BM25DocumentIndex()
    await indexer.add_documents(docs)
    
    # 2. Suche
    results = await indexer.search("Antrag Wohngeld", top_k=5)
    
    for res in results:
        print(f"{res.doc_id}: {res.score:.3f}")
    
    # 3. Re-Ranking (optional)
    from ingestion.retrieval.reranker import RerankCandidate
    
    reranker = CrossEncoderReranker()
    candidates = [
        RerankCandidate(r.doc_id, r.text, r.score)
        for r in results
    ]
    
    reranked = await reranker.rerank("Antrag Wohngeld", candidates)
    
    for r in reranked:
        print(f"{r.doc_id}: {r.rerank_score:.3f}")

asyncio.run(main())
```

**Ausführen:**
```powershell
python my_graph_rag_test.py
```

---

## 5. Vollständige Pipeline (Advanced)

**Voraussetzungen:**
- ✅ ChromaDB läuft auf 192.168.178.94:8000
- ✅ Neo4j läuft auf 192.168.178.94:7687
- ✅ Neo4j Schema eingerichtet (siehe unten)

**Neo4j Schema:**
```cypher
// In Neo4j Browser: http://192.168.178.94:7474

// Nodes erstellen
CREATE (doc:Document {id: "doc1", title: "Wohngeld-Antrag"})
CREATE (ref:LegalReference {reference: "§1 WoGG", fulltext: "Wohngeld wird als Zuschuss..."})
CREATE (step:ProcessStep {name: "FormA-2023"})

// Relationships
CREATE (doc)-[:REFERENCES]->(ref)
CREATE (doc)-[:REQUIRES]->(step)

// Indexes für Performance
CREATE INDEX document_id FOR (d:Document) ON (d.id)
CREATE INDEX legal_ref FOR (l:LegalReference) ON (l.reference)
```

**Python:**
```python
from ingestion.retrieval.hybrid_retriever import create_hybrid_retriever

retriever = await create_hybrid_retriever(
    bm25_documents=docs,
    neo4j_uri="neo4j://192.168.178.94:7687",
    neo4j_auth=("neo4j", "v3f3b1d7"),
    vector_retriever=chroma_client,  # Optional
)

result = await retriever.retrieve("Antrag Wohngeld", top_k=10)

for doc in result.documents:
    print(f"{doc.doc_id}: {doc.score:.3f}")
    print(f"  Entities: {len(doc.graph_context.entities)}")
    print(f"  Legal Refs: {list(doc.graph_context.legal_refs.keys())}")
```

---

## 6. Benchmarks ausführen

**Test-Queries definieren:**
```python
from tests.benchmarks.graph_rag_benchmark import create_test_queries, quick_benchmark

test_queries = create_test_queries([
    ("Antrag Wohngeld", {"doc1", "doc3", "doc7"}),
    ("BAföG Studierende", {"doc2", "doc5"}),
    ("Bescheid Bewilligung", {"doc4", "doc6"}),
])

summary = await quick_benchmark(retriever, test_queries)
print(summary)
```

**Erwartete Ausgabe:**
```
=== GRAPH-RAG BENCHMARK ERGEBNISSE ===
Queries: 3

Ranking-Qualität:
  MRR:          0.850 (Ziel: 0.800) ✅
  NDCG@10:      0.782 (Ziel: 0.750) ✅
  Precision@5:  0.800
  
Graph-Kontext:
  Relevance:    0.720 (Nutzen des Graph-Kontexts)
  
Performance:
  Latency:      425.3ms (Ziel: 500.0ms) ✅
```

---

## 7. Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'rank_bm25'`

**Lösung:**
```powershell
pip install rank-bm25
```

### Problem: Neo4j Connection Error

**Prüfen:**
```powershell
# Neo4j erreichbar?
Test-NetConnection -ComputerName 192.168.178.94 -Port 7687
```

**Credentials prüfen:**
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "neo4j://192.168.178.94:7687",
    auth=("neo4j", "v3f3b1d7")
)
driver.verify_connectivity()
print("✅ Neo4j erreichbar")
```

### Problem: Cross-Encoder zu langsam

**GPU nutzen:**
```python
reranker = CrossEncoderReranker(
    model_name="ms-marco-mini",
    device="cuda"  # Statt "cpu"
)
```

**Oder kleineres Modell:**
```python
# Schnellere Alternative
reranker = CrossEncoderReranker(model_name="ms-marco-mini")  # Statt "ms-marco-base"
```

### Problem: Demo funktioniert nicht

**Logs aktivieren:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Einzelne Komponenten testen:**
```python
# Nur BM25
from ingestion.retrieval.bm25_indexer import BM25DocumentIndex
indexer = BM25DocumentIndex()
print("✅ BM25 OK")

# Nur Re-Ranker
from ingestion.retrieval.reranker import CrossEncoderReranker
reranker = CrossEncoderReranker()
print("✅ Re-Ranker OK")
```

---

## 8. Nächste Schritte

✅ **Demo läuft** → Integration in Backend

1. **Backend-Integration aktivieren:**
   ```python
   # backend.py, Zeile ~3650
   # TODO-Kommentare entfernen
   ```

2. **Neo4j Schema einrichten:**
   ```bash
   # Cypher-Script ausführen
   cat scripts/neo4j_schema_setup.cypher | cypher-shell -a neo4j://192.168.178.94:7687 -u neo4j -p v3f3b1d7
   ```

3. **Performance-Tests:**
   ```python
   # Latency < 500ms?
   result = await retriever.retrieve("Query", return_timings=True)
   print(f"Latency: {result.latency_ms:.1f}ms")
   ```

4. **Produktions-Deployment:**
   - Monitoring hinzufügen (Prometheus/Grafana)
   - Caching aktivieren
   - Skalierung testen

---

## 📚 Weitere Ressourcen

- **Vollständige Analyse:** `docs/COVINA_GRAPH_RAG_ANALYSE.md`
- **Todo-Liste:** `docs/GRAPH_RAG_TODO.md`
- **Implementierungsbericht:** `docs/GRAPH_RAG_PHASE1_BERICHT.md`
- **Code-Beispiele:** `examples/demo_graph_rag.py`

---

## ❓ Hilfe

**Fragen?** Siehe Dokumentation oder:
```python
# Hilfe in Python
from ingestion.retrieval import bm25_indexer
help(bm25_indexer.BM25DocumentIndex)
```

**GitHub Issues:** (Falls Repository vorhanden)

---

**Version:** 1.0  
**Datum:** 6. Oktober 2025  
**Ziel:** Graph-RAG in 10 Minuten zum Laufen bringen ✅
