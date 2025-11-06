from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DocumentMeta:
    doc_id: str
    title: Optional[str] = None
    date: Optional[str] = None           # ISO YYYY-MM-DD
    authority: Optional[str] = None      # Behördenbezeichnung
    aktenzeichen: Optional[str] = None   # Docket/Reference
    text: Optional[str] = None           # optional fulltext for NLP
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Signals:
    date_iso: Optional[str]
    authority_norm: Optional[str]
    aktenzeichen_norm: Optional[str]
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferredStep:
    step_key: str
    label: str
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferredPath:
    path_key: str
    steps: List[InferredStep]
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResult:
    process_key: str
    paths: List[InferredPath]
    node_confidence: Dict[str, float] = field(default_factory=dict)
    path_confidence: Dict[str, float] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
