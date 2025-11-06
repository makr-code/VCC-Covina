from __future__ import annotations
from typing import List, Dict, Any, Optional
from .schemas import DocumentMeta, Signals, InferredStep, InferredPath, InferenceResult
from .guidelines import RuleEngine
import re


def _extract_signals(doc: DocumentMeta, rules: RuleEngine) -> Dict[str, Any]:
    """Extract normalized signals from document metadata.
    
    Args:
        doc: Document metadata
        rules: RuleEngine for normalization
        
    Returns:
        Dictionary of extracted signals
    """
    # Normalize authority + aktenzeichen
    authority_norm = rules.normalize_authority(doc.authority)
    akten = rules.normalize_aktenzeichen(doc.aktenzeichen)

    # Date: prefer explicit, else try to parse from title/text
    date_iso = doc.date
    if not date_iso and doc.title:
        m = re.search(r"(20[0-9]{2}-[01][0-9]-[0-3][0-9])", doc.title)
        if m:
            date_iso = m.group(1)

    return {
        "date_iso": date_iso,
        "authority_norm": authority_norm,
        "aktenzeichen": akten,
        "doc_id": doc.doc_id,
    }


class ProcessMiningPipeline:
    """Self-learning OOP pipeline for process inference from document batches.
    
    Architecture:
    - RuleEngine: Domain knowledge from YAML guidelines
    - Signal Extraction: Metadata/regex-based feature extraction
    - Evidence Aggregation: Weighted sum with normalization
    - Confidence Calculation: Per-step and per-transition confidence
    - Result Persistence: InferenceResult for storage in PG/Graph/Vector
    
    Usage:
        engine = RuleEngine(yaml_path="guidelines/process_inference.yml")
        pipeline = ProcessMiningPipeline(engine)
        
        docs = [DocumentMeta(...), ...]
        result = pipeline.infer_batch("process_key", docs)
        
        # result.node_confidence['step_id'] -> 0.85
        # result.paths[0].steps -> [InferredStep(...), ...]
    """

    def __init__(self, rule_engine: RuleEngine):
        """Initialize pipeline with rule engine.
        
        Args:
            rule_engine: Configured RuleEngine instance
        """
        self.rules = rule_engine

    def infer_batch(
        self, 
        process_key: str, 
        docs: List[DocumentMeta]
    ) -> InferenceResult:
        """Infer process structure from a batch of documents.
        
        This method:
        1. Extracts signals from each document
        2. Evaluates YAML rules to gather evidence
        3. Aggregates evidence with weighted sum
        4. Normalizes confidence scores to [0, 1]
        5. Constructs paths from inferred steps
        
        Args:
            process_key: Identifier for the process being analyzed
            docs: List of document metadata
            
        Returns:
            InferenceResult with paths, steps, and confidence scores
        """
        step_scores: Dict[str, float] = {}
        tr_scores: Dict[str, float] = {}
        stats = {"docs": len(docs)}

        # Extract signals and gather evidence from each document
        for doc in docs:
            sig = _extract_signals(doc, self.rules)
            
            # Step evidence
            for ev in self.rules.infer_steps(sig):
                step_scores[ev.rule_id] = step_scores.get(ev.rule_id, 0.0) + ev.weight
            
            # Transition evidence
            for ev in self.rules.infer_transitions(sig):
                tr_scores[ev.rule_id] = tr_scores.get(ev.rule_id, 0.0) + ev.weight

        # Normalize scores to [0,1] by max (simple MVP, later: Bayesian/LLM prior)
        def _normalize(scores: Dict[str, float]) -> Dict[str, float]:
            if not scores:
                return {}
            max_v = max(scores.values()) or 1.0
            return {k: round(v / max_v, 4) for k, v in scores.items()}

        step_conf = _normalize(step_scores)
        tr_conf = _normalize(tr_scores)

        # Compose paths (MVP: single default path based on top transitions)
        steps_sorted = sorted(step_conf.items(), key=lambda x: x[1], reverse=True)
        inferred_steps = [
            InferredStep(step_key=k, label=k, confidence=c) 
            for k, c in steps_sorted
        ]
        
        inferred_paths = [
            InferredPath(
                path_key="default", 
                steps=inferred_steps, 
                confidence=1.0, 
                evidence={"transitions": tr_conf}
            )
        ]

        return InferenceResult(
            process_key=process_key,
            paths=inferred_paths,
            node_confidence=step_conf,
            path_confidence={"default": 1.0},
            stats=stats,
        )

    def infer_online(
        self, 
        process_key: str, 
        doc: DocumentMeta
    ) -> InferenceResult:
        """Infer from a single document (online mode).
        
        Useful for real-time processing or incremental updates.
        
        Args:
            process_key: Process identifier
            doc: Single document metadata
            
        Returns:
            InferenceResult for single document
        """
        return self.infer_batch(process_key, [doc])
