# UDS3 Test Harness – Dokumentation

## Überblick

Dieses Verzeichnis enthält Integrationstests für das UDS3-System, die die Interaktion zwischen der UDS3-Strategieschicht und den verschiedenen Datenbank-Backends verifizieren.

## Quick Start (PowerShell)

```powershell
# Alle Tests ausführen
cd 'C:\VCC\Covina\uds3'
python -m pytest tests/ -v

# Einzelne Testdatei ausführen
python -m pytest tests/test_integration_ingestion_full_pipeline.py -v -s
```

## Verfügbare Tests

### 1. `test_integration_crud_saga.py`
**Zweck**: Testet CRUD-Operationen und Saga-Flows mit Mock-DatabaseManager.

**Was wird getestet**:
- Vector-DB CRUD-Operationen (create, read, update, delete)
- Relational-DB CRUD-Operationen
- Vereinfachte Saga-Transaktionen

### 2. `test_integration_real_backend_sqlite.py`
**Zweck**: Direkter Roundtrip-Test mit echtem SQLite-Backend.

**Was wird getestet**:
- Direktes Schreiben in SQLite
- Direktes Lesen aus SQLite
- Schema-Kompatibilität

### 3. `test_integration_uds3_full_roundtrip.py`
**Zweck**: End-to-End-Test über die UDS3-Strategie-Fassade.

**Was wird getestet**:
- Erstellung eines Processing-Plans mit `UnifiedDatabaseStrategy`
- Anwendung des Relational-Plans auf SQLite
- Readback-Verifikation

### 4. `test_integration_ingestion_full_pipeline.py` ⭐ **PRODUKTIONSREIF**
**Zweck**: Vollständiger End-to-End-Test der Dokument-Ingestion unter Realbedingungen.

**Was wird getestet**:
- Komplette Ingestion-Pipeline: Dokument mit Chunks + Metadaten
- Schreibvorgänge in **alle vier** DB-Typen:
  - **Vector DB** (ChromaDB): Chunks mit Embeddings ✅
  - **Relational DB** (SQLite): Strukturierte Metadaten in `documents_metadata` ✅
  - **Graph DB** (Neo4j): Document-Nodes und Properties ✅
  - **File Storage** (CouchDB, optional): Dokument-Attachments
- **Saga-Orchestrierung**: Koordinierte Schreibvorgänge über `create_secure_document`
- **Saga-Log-Kontrolle**: Verifizierung von Status, Errors, Compensation
- Cross-DB-Konsistenz: document_id in allen DBs

**Konfiguration**:
```powershell
# Standard (Vector + Relational + Graph):
python -m pytest tests/test_integration_ingestion_full_pipeline.py -v -s

# Mit CouchDB (File Storage):
$env:COUCHDB_DISABLED="false"
python -m pytest tests/test_integration_ingestion_full_pipeline.py -v -s

# Ohne Graph DB:
$env:NEO4J_DISABLED="true"
python -m pytest tests/test_integration_ingestion_full_pipeline.py -v -s
```

**Backend-Defaults** (aus `database/config.py`):
- **Neo4j**: `bolt://192.168.178.94:7687` (User: neo4j, Pass: v3f3b1d7)
- **CouchDB**: `http://192.168.178.94:32931` (User: couchdb, Pass: couchdb)

**Test-Szenario**:
1. Erstellt Testdokument (Baugenehmigung) mit 4 Chunks
2. Führt `create_secure_document` aus → schreibt in alle DBs
3. **Verifiziert Saga-Log**: Status, Errors, Compensations
4. **Verifiziert Vector DB**: Chunks mit Metadaten
5. **Verifiziert Relational DB**: Document-Metadaten in `documents_metadata`
6. **Verifiziert Graph DB**: Document-Node mit Cypher-Queries
7. **Verifiziert File Storage** (optional): CouchDB-Dokument

**Erwartetes Ergebnis**:
```
============================================================
[OK] END-TO-END INGESTION TEST PASSED
  Document ID: doc_c3d0c35da4f7424189cb469c9275d6fa
  Chunks: 4
  Vector DB: [OK]
  Relational DB: [OK]
  Graph DB: [OK]
  File Storage: disabled
============================================================
PASSED ✅
```

**Wichtige Features**:
- ✅ **Saga-Log-Überwachung**: Zeigt Status/Errors/Compensations
- ✅ **Neo4j MERGE**: Vermeidet Duplikate mit `merge_key`-Parameter
- ✅ **Optionale Backends**: Test läuft auch ohne CouchDB/Neo4j
- ✅ **Graph-Queries**: Cypher-basierte Relationship-Verifikation
- ✅ **Robuste Fehlerbehandlung**: Ignoriert optional fehlende Backends

**Implementierte Fixes**:
1. Neo4j `create_node()` erweitert um `merge_key`-Parameter
2. Saga-Log-Parsing und Verifikation
3. Optional-Backend-Handling (file_storage, graph)
4. Cross-DB-Konsistenz-Prüfung

**Siehe auch**: `TEST_RESULTS_INGESTION_PIPELINE.md` für detaillierte Testergebnisse.

---

## Helper-Utilities

### `uds3_plan_db_utils.py`

Stellt Hilfsfunktionen für die Integration mit relationalen Datenbanken bereit.

**Funktionen**:

#### `ensure_table_for_relational_operation(rel_backend, table_name, sample_data, pk_policy='document_id', verbose=False)`
Erstellt eine Tabelle basierend auf Sample-Daten, falls sie nicht existiert. Policy controls preferred PK selection.

#### `apply_relational_operations_from_plan(rel_backend, plan_rel, document_id, pk_policy='document_id', verbose=False)`
Wendet einen UDS3-Relational-Plan auf ein Backend an. Serialisiert dict/list-Werte als JSON wo nötig.

**Beispiel**:
```python
from tests.uds3_plan_db_utils import apply_relational_operations_from_plan
from uds3_core import UnifiedDatabaseStrategy

strategy = UnifiedDatabaseStrategy()
plan = strategy.create_optimized_processing_plan(
    file_path="test.pdf",
    content="Test content",
    chunks=["chunk1", "chunk2"],
    title="Test Document"
)

success = apply_relational_operations_from_plan(
    rel_backend=sqlite_backend,
    plan_rel=plan["databases"]["relational"],
    document_id=plan["document_id"],
    verbose=True
)
```

---

## Design-Hinweise

- Tests erstellen temporäre SQLite-Dateien und räumen sie nach dem Durchlauf auf
- Helpers sind konservativ: bevorzugen TEXT-Spalten und JSON-Serialisierung für komplexe Felder
- Die Tests fügen automatisch den Project-Root zu `sys.path` hinzu

## Troubleshooting

**ModuleNotFoundError für `database` oder `uds3` Module**:
- Stelle sicher, dass PYTHONPATH den Project-Root enthält
- Tests fügen den Root automatisch zu `sys.path` hinzu, aber deine IDE-Konfiguration kann abweichen

**Relational inserts schlagen fehl mit datatype mismatch**:
- Prüfe, ob die Tabellen-PK-Spalte `INTEGER` vs `TEXT` ist
- Passe helper `pk_policy` oder Tabellenerstellung entsprechend an

**Unicode-Fehler in der Ausgabe (Windows)**:
- Tests verwenden ASCII-Symbole `[OK]`, `[X]`, `[!]` statt Unicode-Zeichen

---

## Nächste Schritte

### CI/CD Integration
Für GitHub Actions CI kann ein Workflow erstellt werden:

```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_integration_*.py -v
```

### Erweitern der Tests
- Für Saga-Orchestrierung: Mock oder realen `database.saga_crud` bereitstellen
- Für Graph-DB-Tests: Neo4j-Container via Docker in CI
- Für Production: Migration-Helper unter `database/db_migrations.py` nutzen

Kontakt: Für weitere Hilfe mit CI oder Packaging dieser Tests kann ich einen vollständigen Workflow erstellen.
``` 
