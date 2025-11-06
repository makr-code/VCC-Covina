# Process Module

Strikte Trennung von Belangen für VPB-basierte Prozessmodellierung und selbstlernende Inferenz.

## Struktur

```
processes/
├── domain/           # UPS Entitäten (Process, Step, Role, OrgUnit, System, Control, LegalRef, InfoObject)
│   ├── __init__.py
│   └── models.py
├── mining/           # Self-learning Pipeline (Signals, RuleEngine, ProcessMiningPipeline, Confidence)
│   ├── __init__.py
│   ├── schemas.py    # DocumentMeta, Signals, InferredStep/Path, InferenceResult
│   ├── guidelines.py # YAML RuleEngine, RuleEvidence
│   └── pipeline.py   # ProcessMiningPipeline
├── persistence/      # UDS3 Storage (PostgreSQL, CouchDB, ChromaDB, Neo4j)
│   └── __init__.py
├── graph/            # Neo4j Graph Layer (Temporal Canon, ProcessGraphWriter, Indices)
│   ├── __init__.py
│   └── temporal_canon.py
├── api/              # FastAPI Routes (Ingestion, Queries, Maintenance)
│   └── __init__.py
├── guidelines/       # YAML Domain Knowledge
│   └── process_inference.yml
└── __init__.py
```

## Konzept

**Self-learning & Dynamisierung:**
- Aus tausenden realen Verfahren Prozesswissen ableiten
- YAML-Leitlinien für Domain-Regeln (versioniert, auditierbar)
- Signals aus Metadaten (Datum, Behörde, Aktenzeichen)
- Confidence-Aggregation (gewichtete Evidenz)
- Persistenz in UDS3 (PG, Couch, Neo4j, Chroma)

**Temporal Modeling:**
- Kanonische Zeitknoten: Year, Month, Day, Date
- Relationen: OCCURS_ON, SCHEDULED_FOR, EFFECTIVE_FROM/UNTIL
- Integration mit created_at/updated_at (datetime())

**OOP Best Practices:**
- Strikte Schichtenarchitektur
- Domain-Driven Design (UPS-Entitäten)
- Strategy Pattern (austauschbare Miner)
- Testbarkeit (Mock-fähig)

## Verwendung

### Mining Pipeline

```python
from processes.mining import RuleEngine, ProcessMiningPipeline, DocumentMeta

# Load domain guidelines
engine = RuleEngine(yaml_path="processes/guidelines/process_inference.yml")
pipeline = ProcessMiningPipeline(engine)

# Infer from document batch
docs = [
    DocumentMeta(doc_id="1", date="2025-10-30", authority="LK Potsdam", aktenzeichen="AZ-123/2025"),
    DocumentMeta(doc_id="2", date="2025-11-06", authority="LK Potsdam", aktenzeichen="AZ-123/2025"),
]
result = pipeline.infer_batch("bauleitplanung", docs)

# Access results
print(result.node_confidence)  # {'intake': 0.85, 'review': 0.62, ...}
print(result.paths[0].steps)   # [InferredStep(...), ...]
```

### Domain Models

```python
from processes.domain import Process, Step, Role

process = Process(
    id="uuid-here",
    key="bauleitplanung_brandenburg",
    title="Bauleitplanung Brandenburg",
    version="2023-10",
    domain="bau"
)

step = Step(
    id="uuid-here",
    process_id=process.id,
    order=1,
    key="intake",
    title="Antragseingang",
    required=True
)
```

### Temporal Canon

```python
from processes.graph import TemporalCanon

canon = TemporalCanon(graph_adapter)

# Create temporal nodes
canon.upsert_date('2025-10-30')

# Link process step to date
canon.link_occurs_on('Step', 'step_123', '2025-10-30')

# Link effective range
canon.link_effective_range('Control', 'control_456', '2025-01-01', '2025-12-31')
```

## Integration

- **Ingestion:** `POST /ingestion/processes` (siehe `api/`)
- **Queries:** `GET /processes` (siehe `api/`)
- **Persistence:** UDS3 (siehe `persistence/`)
- **Graph:** Neo4j via UDS3 (siehe `graph/`)

## Strategie

Details in: `VPB/strategieVBP-Covina.md`

- UPS Schema
- Self-learning Architecture
- Temporal Modeling
- Gap Detection
- Mining Algorithms
- Governance
