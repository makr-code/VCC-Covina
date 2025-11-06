from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentMeta:
    """Metadata extracted from a document for process inference.
    
    Attributes:
        doc_id: Unique document identifier
        title: Document title (optional)
        date: Document date in ISO YYYY-MM-DD format (optional)
        authority: Authority/agency name (optional)
        aktenzeichen: Docket/reference number (optional)
        text: Full text content for NLP analysis (optional)
        extra: Additional metadata key-value pairs
    """
    doc_id: str
    title: Optional[str] = None
    date: Optional[str] = None           # ISO YYYY-MM-DD
    authority: Optional[str] = None      # Behördenbezeichnung
    aktenzeichen: Optional[str] = None   # Docket/Reference
    text: Optional[str] = None           # optional fulltext for NLP
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Signals:
    """Normalized signals extracted from document metadata.
    
    Attributes:
        date_iso: ISO date string
        authority_norm: Normalized authority name
        aktenzeichen_norm: Normalized docket number
        features: Additional extracted features
    """
    date_iso: Optional[str]
    authority_norm: Optional[str]
    aktenzeichen_norm: Optional[str]
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferredStep:
    """A single inferred process step.
    
    Attributes:
        step_key: Unique step identifier
        label: Human-readable step label
        confidence: Confidence score [0.0, 1.0]
        evidence: Supporting evidence for this inference
    """
    step_key: str
    label: str
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferredPath:
    """An inferred process path (sequence of steps).
    
    Attributes:
        path_key: Unique path identifier
        steps: Ordered list of steps in this path
        confidence: Overall path confidence [0.0, 1.0]
        evidence: Supporting evidence for this path
    """
    path_key: str
    steps: List[InferredStep]
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResult:
    """Complete process inference result.
    
    Attributes:
        process_key: Process identifier
        paths: List of inferred paths
        node_confidence: Confidence per step/node
        path_confidence: Confidence per path
        stats: Statistical metadata about inference
    """
    process_key: str
    paths: List[InferredPath]
    node_confidence: Dict[str, float] = field(default_factory=dict)
    path_confidence: Dict[str, float] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
