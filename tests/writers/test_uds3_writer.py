"""
Tests for UDS3Writer with DatabaseManager integration.

Tests the UDS3Writer's ability to coordinate writes using the
UDS3 DatabaseManager (same pattern as ingestion.py uses).

Uses mocked DatabaseManager to verify orchestration logic without
requiring real database connections.
"""

from typing import Dict
from unittest.mock import Mock, patch, MagicMock
import pytest

from ingestion.core.interfaces import Chunk, ChunkClassification, ChunkMetadata
from ingestion.writers.uds3_adapter import UDS3Writer


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_chunk() -> Chunk:
    """Create a sample chunk for testing."""
    return Chunk(
        text="This is a test chunk for UDS3 integration.",
        metadata=ChunkMetadata(
            source_file="test.pdf",
            chunk_index=0,
            total_chunks=5,
            classification=ChunkClassification.UNBEKANNT,
            confidence=0.95,
        ),
    )


@pytest.fixture
def uds3_config() -> Dict:
    """Mock configuration for UDS3Writer (DatabaseManager format)."""
    return {
        "relational": {"enabled": True},  # PostgreSQL
        "vector": {"enabled": True},      # ChromaDB
        "graph": {"enabled": True},       # Neo4j
        "file": {"enabled": True}         # CouchDB
    }


# ============================================================================
# Initialization Tests
# ============================================================================

@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_uds3_writer_initialization(mock_db_manager_class, uds3_config):
    """Test that UDS3Writer creates DatabaseManager instance."""
    # Create mock DatabaseManager instance
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = Mock()
    mock_db_instance.vector_backend = Mock()
    mock_db_instance.graph_backend = Mock()
    mock_db_instance.file_backend = Mock()
    mock_db_manager_class.return_value = mock_db_instance
    
    # Create UDS3Writer
    writer = UDS3Writer(uds3_config)
    
    # Initialize should create DatabaseManager
    import asyncio
    asyncio.run(writer.initialize())
    
    # Verify DatabaseManager was created with correct config
    mock_db_manager_class.assert_called_once_with(uds3_config, autostart=True)
    
    # Verify writer is initialized
    assert writer._initialized is True
    assert writer.db_manager is mock_db_instance


@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_uds3_writer_partial_backends(mock_db_manager_class):
    """Test initialization with only some backends enabled."""
    # Config with only PostgreSQL and ChromaDB
    partial_config = {
        "relational": {"enabled": True},
        "vector": {"enabled": True},
    }
    
    # Mock DatabaseManager with partial backends
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = Mock()
    mock_db_instance.vector_backend = Mock()
    mock_db_instance.graph_backend = None  # Not enabled
    mock_db_instance.file_backend = None   # Not enabled
    mock_db_manager_class.return_value = mock_db_instance
    
    writer = UDS3Writer(partial_config)
    import asyncio
    asyncio.run(writer.initialize())
    
    # Verify backend_status reflects partial initialization
    assert writer.backend_status["postgresql"] is True
    assert writer.backend_status["chromadb"] is True
    assert writer.backend_status["neo4j"] is False
    assert writer.backend_status["couchdb"] is False


# ============================================================================
# Write Tests (Single Chunk)
# ============================================================================

@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_write_success_all_backends(mock_db_manager_class, uds3_config, sample_chunk):
    """Test successful write to all backends."""
    # Mock all backends
    mock_relational = Mock()
    mock_relational.insert_document.return_value = {"success": True}
    
    mock_vector = Mock()
    mock_vector.add_documents.return_value = True
    
    mock_graph = Mock()
    mock_graph.execute_query.return_value = True
    
    mock_file = Mock()
    mock_file.add_documents.return_value = True
    
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = mock_relational
    mock_db_instance.vector_backend = mock_vector
    mock_db_instance.graph_backend = mock_graph
    mock_db_instance.file_backend = mock_file
    mock_db_manager_class.return_value = mock_db_instance
    
    writer = UDS3Writer(uds3_config)
    
    # Write chunk
    import asyncio
    result = asyncio.run(writer.write(sample_chunk))
    
    # Verify all backends were called
    mock_relational.insert_document.assert_called_once()
    mock_vector.add_documents.assert_called_once()
    assert mock_graph.execute_query.call_count == 2  # Document + Chunk nodes
    mock_file.add_documents.assert_called_once()
    
    # Verify success
    assert result is True


@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_write_partial_success(mock_db_manager_class, uds3_config, sample_chunk):
    """Test write with some backends failing."""
    # PostgreSQL succeeds, others fail
    mock_relational = Mock()
    mock_relational.insert_document.return_value = {"success": True}
    
    mock_vector = Mock()
    mock_vector.add_documents.side_effect = Exception("ChromaDB connection failed")
    
    mock_graph = Mock()
    mock_graph.execute_query.side_effect = Exception("Neo4j connection failed")
    
    mock_file = Mock()
    mock_file.add_documents.side_effect = Exception("CouchDB connection failed")
    
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = mock_relational
    mock_db_instance.vector_backend = mock_vector
    mock_db_instance.graph_backend = mock_graph
    mock_db_instance.file_backend = mock_file
    mock_db_manager_class.return_value = mock_db_instance
    
    writer = UDS3Writer(uds3_config)
    
    # Write should succeed if at least one backend succeeds
    import asyncio
    result = asyncio.run(writer.write(sample_chunk))
    
    assert result is True  # PostgreSQL succeeded


@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_write_all_backends_fail(mock_db_manager_class, uds3_config, sample_chunk):
    """Test write when all backends fail."""
    # All backends fail
    mock_relational = Mock()
    mock_relational.insert_document.return_value = {"success": False}
    
    mock_vector = Mock()
    mock_vector.add_documents.return_value = False
    
    mock_graph = Mock()
    mock_graph.execute_query.side_effect = Exception("Neo4j failed")
    
    mock_file = Mock()
    mock_file.add_documents.return_value = False
    
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = mock_relational
    mock_db_instance.vector_backend = mock_vector
    mock_db_instance.graph_backend = mock_graph
    mock_db_instance.file_backend = mock_file
    mock_db_manager_class.return_value = mock_db_instance
    
    writer = UDS3Writer(uds3_config)
    
    import asyncio
    result = asyncio.run(writer.write(sample_chunk))
    
    assert result is False  # All failed


# ============================================================================
# Batch Write Tests
# ============================================================================

@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_write_batch_success(mock_db_manager_class, uds3_config):
    """Test successful batch write."""
    # Create 3 test chunks
    chunks = [
        Chunk(
            text=f"Test chunk {i}",
            metadata=ChunkMetadata(
                source_file="test.pdf",
                chunk_index=i,
                total_chunks=3,
            ),
        )
        for i in range(3)
    ]
    
    # Mock all backends to succeed
    mock_relational = Mock()
    mock_relational.insert_document.return_value = {"success": True}
    
    mock_vector = Mock()
    mock_vector.add_documents.return_value = True
    
    mock_graph = Mock()
    mock_graph.execute_query.return_value = True
    
    mock_file = Mock()
    mock_file.add_documents.return_value = True
    
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = mock_relational
    mock_db_instance.vector_backend = mock_vector
    mock_db_instance.graph_backend = mock_graph
    mock_db_instance.file_backend = mock_file
    mock_db_manager_class.return_value = mock_db_instance
    
    writer = UDS3Writer(uds3_config)
    
    import asyncio
    result = asyncio.run(writer.write_batch(chunks))
    
    # Verify aggregated result
    assert result["success"] is True
    assert result["written"] == 3
    assert result["failed"] == 0


# ============================================================================
# Health Check Tests
# ============================================================================

@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_health_check_all_healthy(mock_db_manager_class, uds3_config):
    """Test health check when all backends are healthy."""
    # Mock all backends as healthy
    mock_relational = Mock()
    mock_relational.get_document_count.return_value = 100
    
    mock_vector = Mock()
    mock_vector.is_available.return_value = True
    
    mock_graph = Mock()
    mock_graph.execute_query.return_value = [[1]]  # Simple query result
    
    mock_file = Mock()
    mock_file.is_available.return_value = True
    
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = mock_relational
    mock_db_instance.vector_backend = mock_vector
    mock_db_instance.graph_backend = mock_graph
    mock_db_instance.file_backend = mock_file
    mock_db_manager_class.return_value = mock_db_instance
    
    writer = UDS3Writer(uds3_config)
    
    import asyncio
    asyncio.run(writer.initialize())
    result = asyncio.run(writer.health_check())
    
    assert result is True


@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_health_check_one_unhealthy(mock_db_manager_class, uds3_config):
    """Test health check when one backend is unhealthy."""
    # PostgreSQL, ChromaDB, Neo4j healthy; CouchDB unhealthy
    mock_relational = Mock()
    mock_relational.get_document_count.return_value = 100
    
    mock_vector = Mock()
    mock_vector.is_available.return_value = True
    
    mock_graph = Mock()
    mock_graph.execute_query.return_value = [[1]]
    
    mock_file = Mock()
    mock_file.is_available.return_value = False  # Unhealthy!
    
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = mock_relational
    mock_db_instance.vector_backend = mock_vector
    mock_db_instance.graph_backend = mock_graph
    mock_db_instance.file_backend = mock_file
    mock_db_manager_class.return_value = mock_db_instance
    
    writer = UDS3Writer(uds3_config)
    
    import asyncio
    asyncio.run(writer.initialize())
    result = asyncio.run(writer.health_check())
    
    assert result is False  # One backend unhealthy = overall unhealthy


# ============================================================================
# Backend Status Tests
# ============================================================================

@patch("ingestion.writers.uds3_adapter.DatabaseManager")
def test_backend_status(mock_db_manager_class, uds3_config):
    """Test backend_status property."""
    # Mock partial backends
    mock_db_instance = Mock()
    mock_db_instance.relational_backend = Mock()  # Exists
    mock_db_instance.vector_backend = Mock()      # Exists
    mock_db_instance.graph_backend = None         # Not available
    mock_db_instance.file_backend = None          # Not available
    mock_db_manager_class.return_value = mock_db_instance
    
    writer = UDS3Writer(uds3_config)
    import asyncio
    asyncio.run(writer.initialize())
    
    status = writer.backend_status
    
    assert status["postgresql"] is True
    assert status["chromadb"] is True
    assert status["neo4j"] is False
    assert status["couchdb"] is False
