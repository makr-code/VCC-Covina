"""Process Mining Module.

Self-learning pipeline for process inference from document batches.

Components:
- schemas: Core data structures (DocumentMeta, Signals, InferredStep/Path, InferenceResult)
- guidelines: YAML-driven RuleEngine for domain knowledge
- pipeline: ProcessMiningPipeline orchestrating extraction, inference, and aggregation

Usage:
    from processes.mining import RuleEngine, ProcessMiningPipeline, DocumentMeta
    
    # Load domain guidelines
    engine = RuleEngine(yaml_path="processes/guidelines/process_inference.yml")
    pipeline = ProcessMiningPipeline(engine)
    
    # Infer from document batch
    docs = [DocumentMeta(doc_id="1", date="2025-10-30", authority="LK Potsdam"), ...]
    result = pipeline.infer_batch("bauleitplanung", docs)
    
    # Access results
    print(result.node_confidence)  # {'intake': 0.85, 'review': 0.62, ...}
    print(result.paths[0].steps)   # [InferredStep(...), ...]
"""

from .schemas import DocumentMeta, Signals, InferredStep, InferredPath, InferenceResult
from .guidelines import RuleEngine, RuleEvidence
from .pipeline import ProcessMiningPipeline

__all__ = [
    "DocumentMeta",
    "Signals",
    "InferredStep",
    "InferredPath",
    "InferenceResult",
    "RuleEngine",
    "RuleEvidence",
    "ProcessMiningPipeline",
]
