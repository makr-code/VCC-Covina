# `database_api_chromadb.py`

Kurzbeschreibung
-----------------
Adapter für ChromaDB (lokale / disk-backed Vektor-DB). Eignet sich als
Default-Vector-Backend für Entwicklung und kleine produktive Anwendungen.

Analyse
-------
ChromaDB bietet gute lokale Persistenz für Embeddings; der Adapter kapselt
Collection-Management, Insert/Query-APIs und batch-Operationen. Ideal als
Test-Backend, weil keine externe Infrastruktur nötig ist.

Wichtigste Methoden
-------------------
- `connect()` / `disconnect()`
- `create_collection(name, metadata)`
- `add_documents(collection_name, documents, metadatas, ids)`
- `search_vectors(query_vector, top_k)`

Tests
-----
- Adapter wird in `tests/test_all_configured_backends.py` discoverbar gemacht.
- Integrationstests optional; Chroma lokal genutzt in dev.

Roadmap
-------
- Add metrics (ingest rate, avg latency)
- Improve batch retries

Beispiel
-------
```python
from database.database_api_chromadb import ChromaBackend
b = ChromaBackend({'path':'./chroma/vcc_vector_prod.db'})
b.connect()
b.add_documents('doc_chunks', ['text1','text2'], [{'k':1},{'k':2}], ['id1','id2'])
```