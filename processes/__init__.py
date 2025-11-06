"""Process Module - Complete process modeling and inference.

Strict separation of concerns across submodules:

- domain/      : Core UPS entities (Process, Step, Role, OrgUnit, System, Control, LegalRef, InfoObject)
- mining/      : Self-learning pipeline (Signals, RuleEngine, ProcessMiningPipeline, Confidence)
- persistence/ : UDS3 storage (PostgreSQL, CouchDB, ChromaDB, Neo4j)
- graph/       : Graph layer (TemporalCanon, ProcessGraphWriter, indices)
- api/         : FastAPI routes (ingestion, queries, maintenance)
- guidelines/  : YAML domain knowledge (process_inference.yml)

Usage:
    # Mining
    from processes.mining import RuleEngine, ProcessMiningPipeline, DocumentMeta
    engine = RuleEngine(yaml_path="processes/guidelines/process_inference.yml")
    pipeline = ProcessMiningPipeline(engine)
    result = pipeline.infer_batch("process_key", docs)
    
    # Domain
    from processes.domain import Process, Step, Role
    
    # Graph
    from processes.graph import TemporalCanon
    canon = TemporalCanon(graph_adapter)
    canon.link_occurs_on('Step', step_id, '2025-10-30')

Strategy: VPB/strategieVBP-Covina.md
"""

__all__ = []
