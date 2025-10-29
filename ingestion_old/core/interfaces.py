"""
Core Interfaces for Modular Ingestion

Defines Protocols (structural typing) for pluggable components:
- Chunk: Standardized document chunk representation
- Writer: Database persistence abstraction
- Extractor: Format-specific text extraction
- Classifier: Document classification logic

These interfaces establish contracts for loose coupling and testability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol, Optional, Dict, Any, List
from pathlib import Path


# ============================================================================
# Chunk Data Model
# ============================================================================

class ChunkClassification(str, Enum):
    """
    Document classification categories.
    
    Used for routing chunks to appropriate processing pipelines.
    """
    RECHNUNG = "Rechnung"
    VERTRAG = "Vertrag"
    EMAIL = "E-Mail"
    HANDELSREGISTER = "Handelsregister"
    GEODATA = "Geodaten"
    UNBEKANNT = "Unbekannt"


@dataclass
class ChunkMetadata:
    """
    Metadata for a document chunk.
    
    Tracks provenance, classification, and processing status.
    """
    # Provenance
    source_file: str
    chunk_index: int
    total_chunks: int
    
    # Classification
    classification: ChunkClassification = ChunkClassification.UNBEKANNT
    confidence: float = 0.0
    
    # Processing
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    processor_version: str = "1.0.0"
    
    # Correlation
    correlation_id: Optional[str] = None
    job_id: Optional[str] = None
    
    # Additional attributes
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source_file": self.source_file,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "classification": self.classification.value,
            "confidence": self.confidence,
            "extracted_at": self.extracted_at.isoformat(),
            "processor_version": self.processor_version,
            "correlation_id": self.correlation_id,
            "job_id": self.job_id,
            "extras": self.extras,
        }


@dataclass
class Chunk:
    """
    Standardized document chunk.
    
    Core data structure for the ingestion pipeline. All extractors
    must produce Chunk instances with consistent structure.
    """
    # Content
    text: str
    
    # Metadata
    metadata: ChunkMetadata
    
    # Optional fields
    raw_content: Optional[bytes] = None
    embeddings: Optional[List[float]] = None
    
    def __post_init__(self):
        """Validate chunk after initialization."""
        if not self.text or not self.text.strip():
            raise ValueError("Chunk text cannot be empty")
        if self.metadata.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")
        if self.metadata.total_chunks <= 0:
            raise ValueError("total_chunks must be positive")
        if self.metadata.chunk_index >= self.metadata.total_chunks:
            raise ValueError("chunk_index must be less than total_chunks")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "metadata": self.metadata.to_dict(),
            "has_raw_content": self.raw_content is not None,
            "has_embeddings": self.embeddings is not None,
        }


# ============================================================================
# Component Protocols (Interfaces)
# ============================================================================

class Writer(Protocol):
    """
    Database writer interface.
    
    Implementations persist chunks to specific databases (PostgreSQL,
    ChromaDB, Neo4j, CouchDB). Writers should be idempotent and
    handle transient errors gracefully.
    """
    
    async def write(self, chunk: Chunk) -> bool:
        """
        Write a single chunk to the database.
        
        Args:
            chunk: Chunk to persist
            
        Returns:
            True if write succeeded, False otherwise
            
        Raises:
            RuntimeError: On critical errors (connection failure, etc.)
        """
        ...
    
    async def write_batch(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """
        Write multiple chunks in a batch operation.
        
        Args:
            chunks: List of chunks to persist
            
        Returns:
            Dictionary with write results:
            {
                "success": bool,
                "written": int,
                "failed": int,
                "errors": List[str]
            }
        """
        ...
    
    async def health_check(self) -> bool:
        """
        Check if the writer's database is available.
        
        Returns:
            True if database is healthy, False otherwise
        """
        ...


class Extractor(Protocol):
    """
    Format-specific text extraction interface.
    
    Implementations handle specific file formats (PDF, DOCX, MSG, SHP, etc.)
    and convert them to standardized Chunk instances.
    """
    
    def can_extract(self, file_path: Path) -> bool:
        """
        Check if this extractor supports the given file.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if extractor can handle this file format
        """
        ...
    
    async def extract(
        self,
        file_path: Path,
        correlation_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Extract text from file and convert to chunks.
        
        Args:
            file_path: Path to file to extract
            correlation_id: Optional correlation ID for tracing
            job_id: Optional job ID for tracking
            
        Returns:
            List of extracted chunks
            
        Raises:
            RuntimeError: On extraction failure
        """
        ...
    
    @property
    def supported_formats(self) -> List[str]:
        """
        Get list of supported file extensions.
        
        Returns:
            List of extensions (e.g., [".pdf", ".docx"])
        """
        ...


class Classifier(Protocol):
    """
    Document classification interface.
    
    Implementations classify chunks into categories (Rechnung, Vertrag, etc.)
    using various strategies (LLM, heuristics, ML models).
    """
    
    async def classify(self, chunk: Chunk) -> ChunkClassification:
        """
        Classify a chunk into a category.
        
        Args:
            chunk: Chunk to classify
            
        Returns:
            Classification result
        """
        ...
    
    async def classify_with_confidence(
        self, chunk: Chunk
    ) -> tuple[ChunkClassification, float]:
        """
        Classify chunk and return confidence score.
        
        Args:
            chunk: Chunk to classify
            
        Returns:
            Tuple of (classification, confidence_score)
            where confidence_score is in range [0.0, 1.0]
        """
        ...
    
    @property
    def strategy_name(self) -> str:
        """
        Get name of classification strategy.
        
        Returns:
            Strategy identifier (e.g., "llm", "heuristic", "ml")
        """
        ...


# ============================================================================
# Utility Types
# ============================================================================

@dataclass
class ExtractionResult:
    """
    Result of an extraction operation.
    
    Wraps chunks with success/failure metadata for error handling.
    """
    success: bool
    chunks: List[Chunk] = field(default_factory=list)
    error: Optional[str] = None
    file_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "chunks": [c.to_dict() for c in self.chunks],
            "error": self.error,
            "file_path": self.file_path,
            "chunk_count": len(self.chunks),
        }


@dataclass
class WriteResult:
    """
    Result of a write operation.
    
    Tracks success/failure at chunk level for retry logic.
    """
    chunk_id: str
    success: bool
    error: Optional[str] = None
    database: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "success": self.success,
            "error": self.error,
            "database": self.database,
        }
