"""
Covina Core Ingestion Module

Provides foundational interfaces and routing logic for modular document ingestion.
"""

from .interfaces import (
    Chunk,
    ChunkMetadata,
    Writer,
    Extractor,
    Classifier,
    ChunkClassification,
)
from .router import ChunkRouter

__all__ = [
    "Chunk",
    "ChunkMetadata",
    "Writer",
    "Extractor",
    "Classifier",
    "ChunkClassification",
    "ChunkRouter",
]
