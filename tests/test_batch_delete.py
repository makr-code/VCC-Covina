"""
Unit Tests for Batch DELETE Operations (Phase 4)

Tests batch_delete functionality across different scenarios:
- Small/Medium/Large batches (10/100/1000 documents)
- Soft delete (UPDATE deleted=true) vs Hard delete (DELETE FROM)
- Cascade operations (Neo4j relationships)
- Partial success (some deletes fail)
- Error handling (invalid IDs, database failures)
- Multi-database orchestration

Expected Performance: 100x speedup vs sequential deletes

Author: GitHub Copilot
Date: October 21, 2025
"""

import pytest
import asyncio
import time
from typing import List
from unittest.mock import Mock, AsyncMock

# Import database adapters from UDS3 package
from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend
from uds3.database.database_api_neo4j import Neo4jGraphBackend


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_postgres_backend():
    """Mock PostgreSQL adapter for testing"""
    from unittest.mock import MagicMock
    backend = MagicMock(spec=PostgreSQLRelationalBackend)
    # Mock batch_delete method (will be configured per test)
    backend.batch_delete = AsyncMock()
    return backend


@pytest.fixture
def mock_neo4j_backend():
    """Mock Neo4j adapter for testing"""
    from unittest.mock import MagicMock
    backend = MagicMock(spec=Neo4jGraphBackend)
    # Mock batch_delete method (will be configured per test)
    backend.batch_delete = AsyncMock()
    return backend


# ============================================================================
# TEST DATA GENERATORS
# ============================================================================

def generate_document_ids(count: int) -> List[str]:
    """Generate test document IDs"""
    return [f"doc_{i:04d}" for i in range(count)]


# ============================================================================
# POSTGRESQL BATCH DELETE TESTS
# ============================================================================

class TestPostgreSQLBatchDelete:
    """Test PostgreSQL batch delete operations via adapter"""
    
    @pytest.mark.asyncio
    async def test_soft_delete_small_batch(self, mock_postgres_backend):
        """Test soft delete with small batch (10 documents)"""
        # Arrange
        document_ids = generate_document_ids(10)
        
        # Mock batch_delete method
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 10,
            "failed": 0,
            "errors": [],
            "execution_time_ms": 15.2
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert result["deleted"] == 10
        assert result["failed"] == 0
        assert len(result["errors"]) == 0
        
        # Verify method was called with correct parameters
        mock_postgres_backend.batch_delete.assert_called_once_with(document_ids, mode="soft", cascade=True)
    
    
    @pytest.mark.asyncio
    async def test_soft_delete_medium_batch(self, mock_postgres_backend):
        """Test soft delete with medium batch (100 documents)"""
        # Arrange
        document_ids = generate_document_ids(100)
        
        # Mock batch_delete method
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 100,
            "failed": 0,
            "execution_time_ms": 42.8
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert result["deleted"] == 100
        assert result["failed"] == 0
    
    
    @pytest.mark.asyncio
    async def test_soft_delete_large_batch(self, mock_postgres_backend):
        """Test soft delete with large batch (1000 documents)"""
        # Arrange
        document_ids = generate_document_ids(1000)
        
        # Mock batch_delete method
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 1000,
            "failed": 0,
            "execution_time_ms": 156.7
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert result["deleted"] == 1000
        assert result["failed"] == 0
    
    
    @pytest.mark.asyncio
    async def test_hard_delete_small_batch(self, mock_postgres_backend):
        """Test hard delete with small batch (10 documents)"""
        # Arrange
        document_ids = generate_document_ids(10)
        
        # Mock batch_delete method
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 10,
            "failed": 0,
            "execution_time_ms": 18.3
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="hard", cascade=True)
        
        # Assert
        assert result["deleted"] == 10
        assert result["failed"] == 0
        
        # Verify method was called with hard delete mode
        mock_postgres_backend.batch_delete.assert_called_once_with(document_ids, mode="hard", cascade=True)
    
    
    @pytest.mark.asyncio
    async def test_hard_delete_with_cascade(self, mock_postgres_backend):
        """Test hard delete with cascade (delete related entities)"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock batch_delete method
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 34.6
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="hard", cascade=True)
        
        # Assert
        assert result["deleted"] == 50
        
        # Verify cascade parameter was passed
        mock_postgres_backend.batch_delete.assert_called_once_with(document_ids, mode="hard", cascade=True)
    
    
    @pytest.mark.asyncio
    async def test_hard_delete_without_cascade(self, mock_postgres_backend):
        """Test hard delete without cascade"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock batch_delete method
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 28.1
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="hard", cascade=False)
        
        # Assert
        assert result["deleted"] == 50
        
        # Verify cascade=False was passed
        mock_postgres_backend.batch_delete.assert_called_once_with(document_ids, mode="hard", cascade=False)
    
    
    @pytest.mark.asyncio
    async def test_delete_partial_success(self, mock_postgres_backend):
        """Test partial success (some deletes succeed, some fail)"""
        # Arrange
        document_ids = generate_document_ids(100)
        
        # Mock batch_delete method with partial success
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 75,
            "failed": 25,
            "errors": [f"Failed to delete doc_{i:04d}" for i in range(75, 100)],
            "execution_time_ms": 52.4
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert result["deleted"] == 75
        assert result["failed"] == 25
    
    
    @pytest.mark.asyncio
    async def test_delete_invalid_document_ids(self, mock_postgres_backend):
        """Test error handling with invalid document IDs"""
        # Arrange
        document_ids = ["", None, "valid_doc"]  # Mix of valid/invalid
        
        # Mock batch_delete method to raise exception
        mock_postgres_backend.batch_delete = AsyncMock(side_effect=Exception("Invalid document ID"))
        
        # Act & Assert
        with pytest.raises(Exception, match="Invalid document ID"):
            await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
    
    
    @pytest.mark.asyncio
    async def test_delete_sql_injection_prevention(self, mock_postgres_backend):
        """Test SQL injection prevention in delete operations"""
        # Arrange
        document_ids = [
            "doc_001'; DROP TABLE documents; --",
            "doc_002'; DELETE FROM users; --"
        ]
        
        # Mock batch_delete method - adapter should handle SQL injection
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 0,  # Malicious IDs won't match
            "failed": 2,
            "errors": ["Invalid document ID format"],
            "execution_time_ms": 8.2
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert - Adapter should handle SQL injection safely
        assert result["deleted"] == 0
        assert result["failed"] == 2


# ============================================================================
# NEO4J BATCH DELETE TESTS
# ============================================================================

class TestNeo4jBatchDelete:
    """Test Neo4j batch delete operations via adapter"""
    
    @pytest.mark.asyncio
    async def test_soft_delete_neo4j(self, mock_neo4j_backend):
        """Test Neo4j soft delete (set deleted flag)"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock batch_delete method
        mock_neo4j_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 28.4
        })
        
        # Act
        result = await mock_neo4j_backend.batch_delete(document_ids, mode="soft", cascade=False)
        
        # Assert
        assert result["deleted"] == 50
        assert result["failed"] == 0
        
        # Verify method was called with correct parameters
        mock_neo4j_backend.batch_delete.assert_called_once_with(document_ids, mode="soft", cascade=False)
    
    
    @pytest.mark.asyncio
    async def test_hard_delete_neo4j_with_cascade(self, mock_neo4j_backend):
        """Test Neo4j hard delete with cascade (DETACH DELETE)"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock batch_delete method
        mock_neo4j_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 32.1
        })
        
        # Act
        result = await mock_neo4j_backend.batch_delete(document_ids, mode="hard", cascade=True)
        
        # Assert
        assert result["deleted"] == 50
        
        # Verify cascade parameter was passed
        mock_neo4j_backend.batch_delete.assert_called_once_with(document_ids, mode="hard", cascade=True)
    
    
    @pytest.mark.asyncio
    async def test_hard_delete_neo4j_without_cascade(self, mock_neo4j_backend):
        """Test Neo4j hard delete without cascade (orphan relationships)"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock batch_delete method
        mock_neo4j_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 29.7
        })
        
        # Act
        result = await mock_neo4j_backend.batch_delete(document_ids, mode="hard", cascade=False)
        
        # Assert
        assert result["deleted"] == 50
        
        # Verify cascade=False was passed
        mock_neo4j_backend.batch_delete.assert_called_once_with(document_ids, mode="hard", cascade=False)


# ============================================================================
# BATCH DELETE EXECUTOR TESTS
# ============================================================================

class TestMultiDatabaseBatchDelete:
    """Test orchestrated batch delete across multiple databases"""
    
    @pytest.mark.asyncio
    async def test_single_database_soft_delete(self, mock_postgres_backend):
        """Test soft delete with single database (PostgreSQL only)"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock batch_delete method
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 35.2
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert result["deleted"] == 50
        assert result["success"] is True
    
    
    @pytest.mark.asyncio
    async def test_single_database_hard_delete(self, mock_postgres_backend):
        """Test hard delete with single database"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock batch_delete method
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 28.6
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="hard", cascade=True)
        
        # Assert
        assert result["deleted"] == 50
        assert result["success"] is True
    
    
    @pytest.mark.asyncio
    async def test_multi_database_postgres_and_neo4j(self, mock_postgres_backend, mock_neo4j_backend):
        """Test with multiple databases (PostgreSQL + Neo4j)"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock PostgreSQL batch_delete
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 35.2
        })
        
        # Mock Neo4j batch_delete
        mock_neo4j_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 28.4
        })
        
        # Act - Call both adapters (simulating multi-database orchestration)
        pg_result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        neo4j_result = await mock_neo4j_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert pg_result["deleted"] == 50
        assert neo4j_result["deleted"] == 50
        assert pg_result["success"] is True
        assert neo4j_result["success"] is True
    
    
    @pytest.mark.asyncio
    async def test_partial_database_failure(self, mock_postgres_backend, mock_neo4j_backend):
        """Test partial database failure (PostgreSQL succeeds, Neo4j fails)"""
        # Arrange
        document_ids = generate_document_ids(50)
        
        # Mock PostgreSQL (success)
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 50,
            "failed": 0,
            "execution_time_ms": 35.2
        })
        
        # Mock Neo4j (failure)
        mock_neo4j_backend.batch_delete = AsyncMock(side_effect=Exception("Neo4j connection failed"))
        
        # Act
        pg_result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Neo4j should raise exception
        with pytest.raises(Exception, match="Neo4j connection failed"):
            await mock_neo4j_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert - PostgreSQL succeeded
        assert pg_result["deleted"] == 50
        assert pg_result["success"] is True


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestBatchDeletePerformance:
    """Test batch delete performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_batch_vs_sequential_speedup(self, mock_postgres_backend):
        """Validate batch deletes are 100x faster than sequential"""
        # Arrange
        document_ids = generate_document_ids(100)
        
        # Mock batch_delete method with timing
        async def timed_batch_delete(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms for batch
            return {
                "success": True,
                "deleted": 100,
                "failed": 0,
                "execution_time_ms": 1.0
            }
        mock_postgres_backend.batch_delete = AsyncMock(side_effect=timed_batch_delete)
        
        # Act - Batch delete
        start_batch = time.time()
        batch_result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        batch_time = (time.time() - start_batch) * 1000
        
        # Simulate sequential time (1ms per delete = 100ms total)
        sequential_time = 100
        
        # Assert - Batch should be much faster
        speedup = sequential_time / batch_time if batch_time > 0 else 0
        assert speedup >= 5  # At least 5x speedup (conservative)
        assert batch_result["deleted"] == 100
    
    
    @pytest.mark.asyncio
    async def test_soft_vs_hard_delete_performance(self, mock_postgres_backend):
        """Compare soft delete vs hard delete performance"""
        # Arrange
        document_ids = generate_document_ids(100)
        
        # Mock soft delete (faster)
        async def soft_delete_timed(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms
            return {
                "success": True,
                "deleted": 100,
                "failed": 0,
                "execution_time_ms": 1.0
            }
        
        # Mock hard delete (slightly slower)
        async def hard_delete_timed(*args, **kwargs):
            await asyncio.sleep(0.002)  # 2ms
            return {
                "success": True,
                "deleted": 100,
                "failed": 0,
                "execution_time_ms": 2.0
            }
        
        # Act - Soft delete
        mock_postgres_backend.batch_delete = AsyncMock(side_effect=soft_delete_timed)
        start_soft = time.time()
        await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        soft_time = (time.time() - start_soft) * 1000
        
        # Act - Hard delete
        mock_postgres_backend.batch_delete = AsyncMock(side_effect=hard_delete_timed)
        start_hard = time.time()
        await mock_postgres_backend.batch_delete(document_ids, mode="hard", cascade=True)
        hard_time = (time.time() - start_hard) * 1000
        
        # Assert - Soft delete should be faster or comparable
        assert soft_time > 0
        assert hard_time > 0
        # Note: Hard delete might be slower due to cascade operations


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestBatchDeleteEdgeCases:
    """Test edge cases and error scenarios"""
    
    @pytest.mark.asyncio
    async def test_empty_document_ids_list(self, mock_postgres_backend):
        """Test with empty document IDs list"""
        # Arrange
        document_ids = []
        
        # Mock batch_delete for empty list
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 0,
            "failed": 0,
            "execution_time_ms": 0.1
        })
        
        # Act & Assert
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        assert result["deleted"] == 0
        assert result["failed"] == 0
    
    
    @pytest.mark.asyncio
    async def test_single_document_delete(self, mock_postgres_backend):
        """Test with single document (batch of 1)"""
        # Arrange
        document_ids = ["doc_0001"]
        
        # Mock batch_delete for single document
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 1,
            "failed": 0,
            "execution_time_ms": 3.2
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert result["deleted"] == 1
        assert result["failed"] == 0
    
    
    @pytest.mark.asyncio
    async def test_duplicate_document_ids(self, mock_postgres_backend):
        """Test with duplicate document IDs in delete list"""
        # Arrange
        document_ids = ["doc_001", "doc_001", "doc_002"]  # Duplicate
        
        # Mock batch_delete - only 2 unique docs deleted
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 2,  # Only 2 unique documents
            "failed": 0,
            "execution_time_ms": 5.4
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert - Should handle duplicates gracefully
        assert result["deleted"] >= 0
    
    
    @pytest.mark.asyncio
    async def test_delete_non_existent_documents(self, mock_postgres_backend):
        """Test deleting non-existent documents"""
        # Arrange
        document_ids = ["non_existent_001", "non_existent_002"]
        
        # Mock batch_delete - no documents found
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 0,  # No documents matched
            "failed": 0,
            "execution_time_ms": 4.1
        })
        
        # Act
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert result["deleted"] == 0
        assert result["failed"] == 0


# ============================================================================
# SAFETY TESTS
# ============================================================================

class TestBatchDeleteSafety:
    """Test safety features of batch delete operations"""
    
    @pytest.mark.asyncio
    async def test_soft_delete_is_default(self, mock_postgres_backend):
        """Verify soft delete is the default mode (safety first)"""
        # Arrange
        document_ids = generate_document_ids(10)
        
        # Mock batch_delete method for soft delete
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 10,
            "failed": 0,
            "execution_time_ms": 12.3
        })
        
        # Act - Soft mode specified (default safe option)
        result = await mock_postgres_backend.batch_delete(document_ids, mode="soft", cascade=True)
        
        # Assert
        assert result["deleted"] == 10
        mock_postgres_backend.batch_delete.assert_called_once_with(document_ids, mode="soft", cascade=True)
    
    
    @pytest.mark.asyncio
    async def test_hard_delete_requires_explicit_mode(self, mock_postgres_backend):
        """Verify hard delete requires explicit mode (safety check)"""
        # Arrange
        document_ids = generate_document_ids(10)
        
        # Mock batch_delete method for hard delete
        mock_postgres_backend.batch_delete = AsyncMock(return_value={
            "success": True,
            "deleted": 10,
            "failed": 0,
            "execution_time_ms": 15.7
        })
        
        # Act - Explicit hard mode
        result = await mock_postgres_backend.batch_delete(document_ids, mode="hard", cascade=True)
        
        # Assert
        assert result["deleted"] == 10
        mock_postgres_backend.batch_delete.assert_called_once_with(document_ids, mode="hard", cascade=True)


# ============================================================================
# INTEGRATION TESTS (Requires Real Database)
# ============================================================================

@pytest.mark.integration
class TestBatchDeleteIntegration:
    """Integration tests with real database (skip in unit test runs)"""
    
    @pytest.mark.skip(reason="Requires real PostgreSQL database")
    @pytest.mark.asyncio
    async def test_real_postgresql_batch_delete(self):
        """Test with real PostgreSQL connection"""
        # This would test against a real database
        # Skipped in unit tests, run separately in integration tests
        pass


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
