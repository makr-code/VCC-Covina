from __future__ import annotations
from typing import List, Dict, Any, Optional
from .schemas import DocumentMeta, Signals, InferredStep, InferredPath, InferenceResult
from .guidelines import RuleEngine
import re


def _extract_signals(doc: DocumentMeta, rules: RuleEngine) -> Dict[str, Any]:
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
    """OOP-Pipeline für selbstlernende Prozessinferenz (Batch/Online).

    Komponenten:
    - RuleEngine (YAML Leitlinien)
    - Signals-Extraktion (Metadaten/Regex)
    - Evidenz-Aggregation (gewichtete Summe, Normalisierung)
    - Confidence pro Step und Transition
    - Ergebnis als InferenceResult für Persistenz in PG/Graph/Vector
    """

    def __init__(self, rule_engine: RuleEngine):
        self.rules = rule_engine

    def infer_batch(self, process_key: str, docs: List[DocumentMeta]) -> InferenceResult:
        step_scores: Dict[str, float] = {}
        tr_scores: Dict[str, float] = {}
        stats = {"docs": len(docs)}

        for doc in docs:
            sig = _extract_signals(doc, self.rules)
            for ev in self.rules.infer_steps(sig):
                step_scores[ev.rule_id] = step_scores.get(ev.rule_id, 0.0) + ev.weight
            for ev in self.rules.infer_transitions(sig):
                tr_scores[ev.rule_id] = tr_scores.get(ev.rule_id, 0.0) + ev.weight

        # Normalize to [0,1] by max (simple MVP, later: Bayesian/LLM prior)
        def _normalize(scores: Dict[str, float]) -> Dict[str, float]:
            if not scores:
                return {}
            max_v = max(scores.values()) or 1.0
            return {k: round(v / max_v, 4) for k, v in scores.items()}

        step_conf = _normalize(step_scores)
        tr_conf = _normalize(tr_scores)

        # Compose paths (MVP: single default path based on top transitions)
        steps_sorted = sorted(step_conf.items(), key=lambda x: x[1], reverse=True)
        inferred_steps = [InferredStep(step_key=k, label=k, confidence=c) for k, c in steps_sorted]
        inferred_paths = [InferredPath(path_key="default", steps=inferred_steps, confidence=1.0, evidence={"transitions": tr_conf})]

        return InferenceResult(
            process_key=process_key,
            paths=inferred_paths,
            node_confidence=step_conf,
            path_confidence={"default": 1.0},
            stats=stats,
        )
