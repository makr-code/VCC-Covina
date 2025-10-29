"""
Unit Tests for Core Ingestion Interfaces

Tests the foundational data structures and protocols:
- Chunk and ChunkMetadata validation
- Protocol compliance (Writer, Extractor, Classifier)
- Data serialization (to_dict methods)
"""

import pytest
from datetime import datetime
from pathlib import Path

from ingestion.core.interfaces import (
    Chunk,
    ChunkMetadata,
    ChunkClassification,
    ExtractionResult,
    WriteResult,
)


class TestChunkMetadata:
    """Test ChunkMetadata data structure."""
    
    def test_create_minimal_metadata(self):
        """Test creating metadata with minimal required fields."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        
        assert metadata.source_file == "test.pdf"
        assert metadata.chunk_index == 0
        assert metadata.total_chunks == 1
        assert metadata.classification == ChunkClassification.UNBEKANNT
        assert metadata.confidence == 0.0
        assert isinstance(metadata.extracted_at, datetime)
    
    def test_metadata_with_classification(self):
        """Test metadata with explicit classification."""
        metadata = ChunkMetadata(
            source_file="invoice.pdf",
            chunk_index=0,
            total_chunks=1,
            classification=ChunkClassification.RECHNUNG,
            confidence=0.95,
        )
        
        assert metadata.classification == ChunkClassification.RECHNUNG
        assert metadata.confidence == 0.95
    
    def test_metadata_with_correlation_id(self):
        """Test metadata with correlation/job IDs."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
            correlation_id="corr-123",
            job_id="job-456",
        )
        
        assert metadata.correlation_id == "corr-123"
        assert metadata.job_id == "job-456"
    
    def test_metadata_to_dict(self):
        """Test metadata serialization to dictionary."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
            classification=ChunkClassification.RECHNUNG,
            confidence=0.85,
            correlation_id="corr-123",
        )
        
        result = metadata.to_dict()
        
        assert result["source_file"] == "test.pdf"
        assert result["chunk_index"] == 0
        assert result["total_chunks"] == 1
        assert result["classification"] == "Rechnung"
        assert result["confidence"] == 0.85
        assert result["correlation_id"] == "corr-123"
        assert "extracted_at" in result
    
    def test_metadata_extras(self):
        """Test metadata extras field for custom attributes."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
            extras={"custom_field": "custom_value", "page_number": 5},
        )
        
        assert metadata.extras["custom_field"] == "custom_value"
        assert metadata.extras["page_number"] == 5


class TestChunk:
    """Test Chunk data structure."""
    
    def test_create_valid_chunk(self):
        """Test creating a valid chunk."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        
        chunk = Chunk(
            text="This is a test document.",
            metadata=metadata,
        )
        
        assert chunk.text == "This is a test document."
        assert chunk.metadata.source_file == "test.pdf"
        assert chunk.raw_content is None
        assert chunk.embeddings is None
    
    def test_chunk_with_embeddings(self):
        """Test chunk with embedding vectors."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        
        chunk = Chunk(
            text="Test text",
            metadata=metadata,
            embeddings=[0.1, 0.2, 0.3],
        )
        
        assert chunk.embeddings == [0.1, 0.2, 0.3]
    
    def test_chunk_validation_empty_text(self):
        """Test that empty text raises ValueError."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        
        with pytest.raises(ValueError, match="Chunk text cannot be empty"):
            Chunk(text="", metadata=metadata)
    
    def test_chunk_validation_whitespace_only(self):
        """Test that whitespace-only text raises ValueError."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        
        with pytest.raises(ValueError, match="Chunk text cannot be empty"):
            Chunk(text="   \n  \t  ", metadata=metadata)
    
    def test_chunk_validation_negative_index(self):
        """Test that negative chunk_index raises ValueError."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=-1,
            total_chunks=1,
        )
        
        with pytest.raises(ValueError, match="chunk_index must be non-negative"):
            Chunk(text="Test", metadata=metadata)
    
    def test_chunk_validation_zero_total(self):
        """Test that total_chunks=0 raises ValueError."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=0,
        )
        
        with pytest.raises(ValueError, match="total_chunks must be positive"):
            Chunk(text="Test", metadata=metadata)
    
    def test_chunk_validation_index_out_of_range(self):
        """Test that chunk_index >= total_chunks raises ValueError."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=5,
            total_chunks=5,
        )
        
        with pytest.raises(ValueError, match="chunk_index must be less than total_chunks"):
            Chunk(text="Test", metadata=metadata)
    
    def test_chunk_to_dict(self):
        """Test chunk serialization to dictionary."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        
        chunk = Chunk(
            text="Test content",
            metadata=metadata,
            embeddings=[0.1, 0.2],
        )
        
        result = chunk.to_dict()
        
        assert result["text"] == "Test content"
        assert "metadata" in result
        assert result["has_embeddings"] is True
        assert result["has_raw_content"] is False


class TestChunkClassification:
    """Test ChunkClassification enum."""
    
    def test_classification_values(self):
        """Test that all classification values are strings."""
        assert ChunkClassification.RECHNUNG.value == "Rechnung"
        assert ChunkClassification.VERTRAG.value == "Vertrag"
        assert ChunkClassification.EMAIL.value == "E-Mail"
        assert ChunkClassification.HANDELSREGISTER.value == "Handelsregister"
        assert ChunkClassification.GEODATA.value == "Geodaten"
        assert ChunkClassification.UNBEKANNT.value == "Unbekannt"
    
    def test_classification_from_string(self):
        """Test creating classification from string."""
        classification = ChunkClassification("Rechnung")
        assert classification == ChunkClassification.RECHNUNG


class TestExtractionResult:
    """Test ExtractionResult data structure."""
    
    def test_success_result(self):
        """Test successful extraction result."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        chunk = Chunk(text="Test", metadata=metadata)
        
        result = ExtractionResult(
            success=True,
            chunks=[chunk],
            file_path="test.pdf",
        )
        
        assert result.success is True
        assert len(result.chunks) == 1
        assert result.error is None
    
    def test_failure_result(self):
        """Test failed extraction result."""
        result = ExtractionResult(
            success=False,
            error="File not found",
            file_path="missing.pdf",
        )
        
        assert result.success is False
        assert len(result.chunks) == 0
        assert result.error == "File not found"
    
    def test_extraction_result_to_dict(self):
        """Test extraction result serialization."""
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        chunk = Chunk(text="Test", metadata=metadata)
        
        result = ExtractionResult(
            success=True,
            chunks=[chunk],
            file_path="test.pdf",
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["success"] is True
        assert dict_result["chunk_count"] == 1
        assert "chunks" in dict_result


class TestWriteResult:
    """Test WriteResult data structure."""
    
    def test_success_write_result(self):
        """Test successful write result."""
        result = WriteResult(
            chunk_id="chunk-123",
            success=True,
            database="postgresql",
        )
        
        assert result.success is True
        assert result.error is None
    
    def test_failure_write_result(self):
        """Test failed write result."""
        result = WriteResult(
            chunk_id="chunk-456",
            success=False,
            error="Connection timeout",
            database="chromadb",
        )
        
        assert result.success is False
        assert result.error == "Connection timeout"
    
    def test_write_result_to_dict(self):
        """Test write result serialization."""
        result = WriteResult(
            chunk_id="chunk-789",
            success=True,
            database="neo4j",
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["chunk_id"] == "chunk-789"
        assert dict_result["success"] is True
        assert dict_result["database"] == "neo4j"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
