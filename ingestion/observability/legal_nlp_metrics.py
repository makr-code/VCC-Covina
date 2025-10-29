from __future__ import annotations
import logging
import time
from typing import Any, Dict

from utils.metrics import metrics_registry, Counter, Histogram

logger = logging.getLogger("legal_nlp")

# Register metrics (idempotent via registry)
legal_extractions = metrics_registry.register(
    Counter("legal_nlp_extractions_total", "Total number of legal NLP extractions", ["status"]) 
)

legal_extraction_latency = metrics_registry.register(
    Histogram("legal_nlp_extraction_seconds", "Latency of legal NLP stages in seconds", ["stage"]) 
)

legal_entities_total = metrics_registry.register(
    Counter("legal_entities_extracted_total", "Extracted legal entities by kind", ["kind"]) 
)

legal_graph_upserts = metrics_registry.register(
    Counter("legal_graph_upserts_total", "Graph upserts by type and status", ["type", "status"]) 
)


def record_extraction_result(result: Dict[str, Any]) -> Dict[str, int]:
    """Increment entity counters based on extraction result and return a compact summary.

    Expected result shape (best-effort):
      {
        "entities": [...],
        "concepts": [...],
        "norms": [...],
        "authorities": [...],
        "jurisdictions": [...],
        "ecli": [...],
        "aktenzeichen": [...],
        "dates": [...],
        "laws": [...]
      }
    Unknown/missing keys are treated as empty.
    """
    keys_map = {
        "concepts": "concept",
        "norms": "norm",
        "authorities": "authority",
        "jurisdictions": "jurisdiction",
        "ecli": "ecli",
        "aktenzeichen": "aktenzeichen",
        "dates": "date",
        "laws": "law",
    }

    summary: Dict[str, int] = {}
    for key, label in keys_map.items():
        items = result.get(key) or []
        count = len(items) if isinstance(items, list) else int(items or 0)
        summary[label] = count
        if count:
            legal_entities_total.inc(count, labels={"kind": label})

    # Generic catch-all for flat "entities" list if present
    generic_entities = result.get("entities") or []
    if isinstance(generic_entities, list) and generic_entities:
        legal_entities_total.inc(len(generic_entities), labels={"kind": "entity"})
        summary["entity"] = len(generic_entities)

    return summary


def observe_latency(start: float, stage: str) -> float:
    """Observe latency for a stage and return elapsed seconds."""
    elapsed = max(0.0, time.perf_counter() - start)
    legal_extraction_latency.observe(elapsed, labels={"stage": stage})
    return elapsed


def record_graph_write(success: bool, item_type: str) -> None:
    """Record graph write outcome.

    Args:
        success: True if operation succeeded
        item_type: 'node' or 'relation'
    """
    legal_graph_upserts.inc(labels={"type": item_type, "status": "success" if success else "failed"})


def record_extraction_status(success: bool) -> None:
    legal_extractions.inc(labels={"status": "success" if success else "error"})
