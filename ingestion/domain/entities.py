from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass(frozen=True)
class DocumentId:
    value: str

@dataclass(frozen=True)
class ChunkId:
    value: str

@dataclass
class Document:
    id: DocumentId
    title: Optional[str]
    source_path: Optional[str]
    content_hash: Optional[str]
    chunks: List["DocumentChunk"] = field(default_factory=list)

@dataclass
class DocumentChunk:
    id: ChunkId
    document_id: DocumentId
    text: str
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class ExtractionResult:
    entities: List[Dict]
    concepts: List[Dict]
    norms: List[Dict]
    authorities: List[Dict]
    jurisdictions: List[Dict]

