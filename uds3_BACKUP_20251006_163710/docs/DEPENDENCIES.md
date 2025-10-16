# UDS3 Dependencies

Diese Datei listet empfohlene Python-Pakete und optionale Integrationen. Viele Komponenten sind optional; das Core-Paket funktioniert auch mit reduzierter Funktionalität.

Empfohlene Python-Version

- Python 3.11 oder 3.12

Minimale Abhängigkeiten (Beispiel) - `requirements.txt` empfohlen

- typing_extensions (falls nötig)
- dataclasses (eingebaut in 3.7+, nicht extra notwendig für 3.11)
- numpy (optional für Embedding/Vector-Workflows)
- requests
- pydantic (wenn Modelle genutzt werden)

Optionale Integrationen (je nach Setup)

- Vector DB Clients: chromadb, pinecone-client, milvus
- Graph DB Clients: neo4j, arangojs (python-arango)
- Relationale DB: psycopg2-binary (Postgres), sqlite3 (standard)
- LLM-Clients: ollama-py (oder lokale LLM-Adapter)
- Security & Quality: interne Module `uds3_security`, `uds3_quality` (meist Teil des Repo)

Beispiel `requirements.txt` (Entwickler/Testing)

```
# Minimal
requests==2.31.0
numpy==1.26.1
pydantic==2.7.0

# Optional (Kommentar out/aktivieren bei Bedarf)
# chromadb==0.3.XX
# pinecone-client==2.2.XX
# neo4j==5.9.0
# psycopg2-binary==2.9.9
```

Installation

- Lege ein virtuelles Environment an und installiere die Pakete (siehe `docs/QUICKSTART.md`).

Wenn Du möchtest, erstelle ich eine echte `requirements.txt` aus den importierten Modulen der Codebasis. Das kann automatisiert werden, wenn Du das wünschst.
