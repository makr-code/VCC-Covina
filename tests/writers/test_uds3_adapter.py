"""
Unit Tests for UDS3 Writer Adapter

Tests the UDS3Writer stub implementation:
- Initialization
- Single chunk writes
- Batch writes
- Health checks
- Backend status
"""

import pytest
from typing import List

from ingestion.core.interfaces import Chunk, ChunkMetadata, ChunkClassification
from ingestion.writers.uds3_adapter import UDS3Writer


class TestUDS3WriterInitialization:
    """Test UDS3Writer initialization."""
    
    def test_init_without_config(self):
        """Test initialization without configuration."""
        writer = UDS3Writer()
        
        assert writer.config == {}
        assert writer._backends == {}
        assert writer._initialized is False
    
    def test_init_with_config(self):
        """Test initialization with configuration."""
        config = {
            "postgresql": {"host": "localhost", "port": 5432},
            "chromadb": {"host": "localhost", "port": 8000},
        }
        
        writer = UDS3Writer(config=config)
        
        assert writer.config == config
        assert writer._initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test backend initialization."""
        writer = UDS3Writer()
        
        await writer.initialize()
        
        assert writer._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize can be called multiple times."""
        writer = UDS3Writer()
        
        await writer.initialize()
        await writer.initialize()  # Should not raise
        
        assert writer._initialized is True
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test backend cleanup."""
        writer = UDS3Writer()
        await writer.initialize()
        
        await writer.close()
        
        assert writer._initialized is False


class TestUDS3WriterWrite:
    """Test UDS3Writer single chunk writes."""
    
    @pytest.mark.asyncio
    async def test_write_single_chunk(self):
        """Test writing a single chunk (STUB mode)."""
        writer = UDS3Writer()
        
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
            classification=ChunkClassification.RECHNUNG,
            correlation_id="corr-123",
            job_id="job-456",
        )
        chunk = Chunk(text="Test content", metadata=metadata)
        
        result = await writer.write(chunk)
        
        # STUB: Should always return True
        assert result is True
    
    @pytest.mark.asyncio
    async def test_write_multiple_chunks_sequential(self):
        """Test writing multiple chunks sequentially."""
        writer = UDS3Writer()
        
        chunks = []
        for i in range(3):
            metadata = ChunkMetadata(
                source_file="test.pdf",
                chunk_index=i,
                total_chunks=3,
            )
            chunks.append(Chunk(text=f"Chunk {i}", metadata=metadata))
        
        results = [await writer.write(chunk) for chunk in chunks]
        
        # STUB: All should succeed
        assert all(results)


class TestUDS3WriterBatch:
    """Test UDS3Writer batch operations."""
    
    @pytest.mark.asyncio
    async def test_write_batch_empty(self):
        """Test batch write with empty list."""
        writer = UDS3Writer()
        
        result = await writer.write_batch([])
        
        assert result["success"] is True
        assert result["written"] == 0
        assert result["failed"] == 0
        assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_write_batch_single_chunk(self):
        """Test batch write with single chunk."""
        writer = UDS3Writer()
        
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=1,
        )
        chunk = Chunk(text="Test", metadata=metadata)
        
        result = await writer.write_batch([chunk])
        
        assert result["success"] is True
        assert result["written"] == 1
        assert result["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_write_batch_multiple_chunks(self):
        """Test batch write with multiple chunks."""
        writer = UDS3Writer()
        
        chunks = []
        for i in range(10):
            metadata = ChunkMetadata(
                source_file="test.pdf",
                chunk_index=i,
                total_chunks=10,
                correlation_id="corr-batch",
                job_id="job-batch",
            )
            chunks.append(Chunk(text=f"Chunk {i}", metadata=metadata))
        
        result = await writer.write_batch(chunks)
        
        # STUB: All should succeed
        assert result["success"] is True
        assert result["written"] == 10
        assert result["failed"] == 0
        assert result["errors"] == []


class TestUDS3WriterHealth:
    """Test UDS3Writer health checks."""
    
    @pytest.mark.asyncio
    async def test_health_check_without_init(self):
        """Test health check before initialization."""
        writer = UDS3Writer()
        
        result = await writer.health_check()
        
        # STUB: Always returns True
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_after_init(self):
        """Test health check after initialization."""
        writer = UDS3Writer()
        await writer.initialize()
        
        result = await writer.health_check()
        
        # STUB: Always returns True
        assert result is True
    
    def test_backend_status(self):
        """Test getting backend status."""
        writer = UDS3Writer()
        
        status = writer.backend_status
        
        # STUB: All backends should be healthy
        assert status["postgresql"] is True
        assert status["chromadb"] is True
        assert status["neo4j"] is True
        assert status["couchdb"] is True
        assert len(status) == 4


class TestUDS3WriterIntegration:
    """Integration-style tests for UDS3Writer."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow: init -> write -> batch -> close."""
        writer = UDS3Writer()
        
        # Initialize
        await writer.initialize()
        assert writer._initialized is True
        
        # Single write
        metadata = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=2,
        )
        chunk1 = Chunk(text="First chunk", metadata=metadata)
        result1 = await writer.write(chunk1)
        assert result1 is True
        
        # Batch write
        metadata2 = ChunkMetadata(
            source_file="test.pdf",
            chunk_index=1,
            total_chunks=2,
        )
        chunk2 = Chunk(text="Second chunk", metadata=metadata2)
        batch_result = await writer.write_batch([chunk1, chunk2])
        assert batch_result["success"] is True
        
        # Health check
        health = await writer.health_check()
        assert health is True
        
        # Close
        await writer.close()
        assert writer._initialized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
