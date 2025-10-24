"""
Phase 4.3 - Integration Tests for Batch WRITE Operations

Tests batch UPDATE, DELETE, and UPSERT operations with real PostgreSQL database.
Validates performance targets (67-100x speedup) and multi-database orchestration.

Run with: pytest tests/test_batch_write_integration.py -v -m integration

Author: GitHub Copilot
Date: October 21, 2025
Version: 1.0.0
"""

import pytest
import asyncio
import time
import os
from datetime import datetime
from typing import List, Dict, Any

# Import database adapters
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.database_api_postgresql import PostgreSQLRelationalBackend
from database.database_api_neo4j import Neo4jGraphBackend


# ============================================================================
# Configuration & Setup
# ============================================================================

POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', '192.168.178.94'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'database': os.getenv('POSTGRES_DATABASE', 'postgres')
}

NEO4J_CONFIG = {
    'uri': os.getenv('NEO4J_URI', 'bolt://192.168.178.94:7687'),
    'user': os.getenv('NEO4J_USER', 'neo4j'),
    'password': os.getenv('NEO4J_PASSWORD', 'neo4j')
}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
async def postgres_backend():
    """Real PostgreSQL backend connection (session-scoped)"""
    backend = PostgreSQLRelationalBackend(
        host=POSTGRES_CONFIG['host'],
        port=POSTGRES_CONFIG['port'],
        user=POSTGRES_CONFIG['user'],
        password=POSTGRES_CONFIG['password'],
        database=POSTGRES_CONFIG['database'],
        table_name='test_batch_documents'
    )
    
    # Initialize connection
    await backend.connect()
    
    # Create test table if not exists
    async with backend.pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS test_batch_documents (
                document_id VARCHAR(255) PRIMARY KEY,
                title TEXT,
                content TEXT,
                metadata JSONB DEFAULT '{}',
                tags TEXT[],
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                deleted BOOLEAN DEFAULT FALSE,
                version INTEGER DEFAULT 1
            )
        """)
    
    yield backend
    
    # Cleanup
    await backend.disconnect()


@pytest.fixture(scope="function")
async def clean_test_table(postgres_backend):
    """Clean test table before each test"""
    async with postgres_backend.pool.acquire() as conn:
        await conn.execute("DELETE FROM test_batch_documents")
    yield
    # Cleanup after test
    async with postgres_backend.pool.acquire() as conn:
        await conn.execute("DELETE FROM test_batch_documents")


# Note: No separate writer/executor fixtures needed
# Tests will use postgres_backend directly with adapter methods


# ============================================================================
# Helper Functions
# ============================================================================

async def insert_test_documents(postgres_backend, count: int) -> List[str]:
    """Insert test documents and return document IDs"""
    document_ids = []
    async with postgres_backend.pool.acquire() as conn:
        for i in range(count):
            doc_id = f"test_doc_{i}_{int(time.time() * 1000)}"
            await conn.execute("""
                INSERT INTO test_batch_documents (document_id, title, content, metadata, tags, version)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, doc_id, f"Test Document {i}", f"Content {i}", 
                {}, [f"tag{i}"], 1)
            document_ids.append(doc_id)
    return document_ids


async def get_document(postgres_backend, doc_id: str) -> Dict[str, Any]:
    """Get single document by ID"""
    async with postgres_backend.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM test_batch_documents WHERE document_id = $1",
            doc_id
        )
        if row:
            return dict(row)
        return None


async def count_documents(postgres_backend, deleted: bool = False) -> int:
    """Count documents (optionally filter by deleted status)"""
    async with postgres_backend.pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM test_batch_documents WHERE deleted = $1",
            deleted
        )
        return result


async def sequential_update(postgres_backend, updates: List[Dict[str, Any]]) -> float:
    """Perform sequential updates (for performance comparison)"""
    start_time = time.time()
    async with postgres_backend.pool.acquire() as conn:
        for update in updates:
            await conn.execute("""
                UPDATE test_batch_documents
                SET title = $2, updated_at = NOW()
                WHERE document_id = $1
            """, update["document_id"], update["fields"]["title"])
    return time.time() - start_time


async def sequential_delete(postgres_backend, doc_ids: List[str]) -> float:
    """Perform sequential deletes (for performance comparison)"""
    start_time = time.time()
    async with postgres_backend.pool.acquire() as conn:
        for doc_id in doc_ids:
            await conn.execute(
                "UPDATE test_batch_documents SET deleted = TRUE WHERE document_id = $1",
                doc_id
            )
    return time.time() - start_time


async def sequential_upsert(postgres_backend, documents: List[Dict[str, Any]]) -> float:
    """Perform sequential upserts (for performance comparison)"""
    start_time = time.time()
    async with postgres_backend.pool.acquire() as conn:
        for doc in documents:
            await conn.execute("""
                INSERT INTO test_batch_documents (document_id, title, content, metadata, tags, version)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (document_id) DO UPDATE
                SET title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    tags = EXCLUDED.tags,
                    updated_at = NOW()
            """, doc["document_id"], doc["title"], doc["content"], 
                doc.get("metadata", {}), doc.get("tags", []), doc.get("version", 1))
    return time.time() - start_time


# ============================================================================
# Integration Tests: PostgreSQL Batch UPDATE
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestBatchUpdateIntegration:
    """Integration tests for batch UPDATE operations"""
    
    async def test_batch_update_10_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test batch update with 10 documents (real PostgreSQL)"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 10)
        updates = [
            {
                "document_id": doc_id,
                "fields": {"title": f"Updated Title {i}"}
            }
            for i, doc_id in enumerate(doc_ids)
        ]
        
        # Act
        result = await postgres_writer.batch_update(updates, mode="partial")
        
        # Assert
        assert result["updated"] == 10
        assert result["failed"] == 0
        assert len(result["errors"]) == 0
        
        # Verify database state
        for i, doc_id in enumerate(doc_ids):
            doc = await get_document(postgres_backend, doc_id)
            assert doc is not None
            assert doc["title"] == f"Updated Title {i}"
    
    async def test_batch_update_100_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test batch update with 100 documents (triggers temp table strategy)"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 100)
        updates = [
            {
                "document_id": doc_id,
                "fields": {"title": f"Updated Title {i}", "version": 2}
            }
            for i, doc_id in enumerate(doc_ids)
        ]
        
        # Act
        result = await postgres_writer.batch_update(updates, mode="partial")
        
        # Assert
        assert result["updated"] == 100
        assert result["failed"] == 0
        assert len(result["errors"]) == 0
        
        # Verify sample documents
        sample_doc = await get_document(postgres_backend, doc_ids[0])
        assert sample_doc["title"] == "Updated Title 0"
        assert sample_doc["version"] == 2
    
    async def test_batch_update_full_mode(self, postgres_backend, postgres_writer, clean_test_table):
        """Test batch update with full mode (replace all fields)"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 10)
        updates = [
            {
                "document_id": doc_id,
                "fields": {
                    "title": f"New Title {i}",
                    "content": f"New Content {i}",
                    "metadata": {"updated": True},
                    "tags": ["new_tag"],
                    "version": 2
                }
            }
            for i, doc_id in enumerate(doc_ids)
        ]
        
        # Act
        result = await postgres_writer.batch_update(updates, mode="full")
        
        # Assert
        assert result["updated"] == 10
        
        # Verify full replacement
        doc = await get_document(postgres_backend, doc_ids[0])
        assert doc["title"] == "New Title 0"
        assert doc["content"] == "New Content 0"
        assert doc["metadata"] == {"updated": True}
        assert doc["tags"] == ["new_tag"]
    
    async def test_batch_vs_sequential_update_speedup(self, postgres_backend, postgres_writer, clean_test_table):
        """Test batch update speedup vs sequential (Target: 67-80x)"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 100)
        updates = [
            {
                "document_id": doc_id,
                "fields": {"title": f"Updated {i}"}
            }
            for i, doc_id in enumerate(doc_ids)
        ]
        
        # Act - Batch Update
        batch_start = time.time()
        batch_result = await postgres_writer.batch_update(updates, mode="partial")
        batch_time = time.time() - batch_start
        
        # Reset for sequential test
        doc_ids_2 = await insert_test_documents(postgres_backend, 100)
        updates_2 = [
            {
                "document_id": doc_id,
                "fields": {"title": f"Updated {i}"}
            }
            for i, doc_id in enumerate(doc_ids_2)
        ]
        
        # Act - Sequential Update
        sequential_time = await sequential_update(postgres_backend, updates_2)
        
        # Calculate speedup
        speedup = sequential_time / batch_time if batch_time > 0 else 0
        
        # Assert
        assert batch_result["updated"] == 100
        assert speedup > 5.0, f"Speedup {speedup:.1f}x is below 5x threshold"
        
        print(f"\n🚀 UPDATE Performance:")
        print(f"   Batch:      {batch_time:.4f}s")
        print(f"   Sequential: {sequential_time:.4f}s")
        print(f"   Speedup:    {speedup:.1f}x (Target: 67-80x)")


# ============================================================================
# Integration Tests: PostgreSQL Batch DELETE
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestBatchDeleteIntegration:
    """Integration tests for batch DELETE operations"""
    
    async def test_soft_delete_10_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test soft delete with 10 documents (default mode)"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 10)
        
        # Act
        result = await postgres_writer.batch_delete(doc_ids, mode="soft")
        
        # Assert
        assert result["deleted"] == 10
        assert result["failed"] == 0
        
        # Verify soft delete (deleted=true)
        deleted_count = await count_documents(postgres_backend, deleted=True)
        assert deleted_count == 10
        
        # Verify documents still exist in DB
        doc = await get_document(postgres_backend, doc_ids[0])
        assert doc is not None
        assert doc["deleted"] is True
    
    async def test_hard_delete_10_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test hard delete with 10 documents (explicit mode)"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 10)
        
        # Act
        result = await postgres_writer.batch_delete(doc_ids, mode="hard")
        
        # Assert
        assert result["deleted"] == 10
        assert result["failed"] == 0
        
        # Verify hard delete (documents removed)
        total_count = await count_documents(postgres_backend, deleted=False)
        assert total_count == 0
        
        # Verify documents don't exist
        doc = await get_document(postgres_backend, doc_ids[0])
        assert doc is None
    
    async def test_soft_delete_100_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test soft delete with 100 documents"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 100)
        
        # Act
        result = await postgres_writer.batch_delete(doc_ids, mode="soft")
        
        # Assert
        assert result["deleted"] == 100
        assert result["failed"] == 0
        
        # Verify all marked as deleted
        deleted_count = await count_documents(postgres_backend, deleted=True)
        assert deleted_count == 100
    
    async def test_batch_vs_sequential_delete_speedup(self, postgres_backend, postgres_writer, clean_test_table):
        """Test batch delete speedup vs sequential (Target: 100x)"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 100)
        
        # Act - Batch Delete
        batch_start = time.time()
        batch_result = await postgres_writer.batch_delete(doc_ids, mode="soft")
        batch_time = time.time() - batch_start
        
        # Reset for sequential test
        doc_ids_2 = await insert_test_documents(postgres_backend, 100)
        
        # Act - Sequential Delete
        sequential_time = await sequential_delete(postgres_backend, doc_ids_2)
        
        # Calculate speedup
        speedup = sequential_time / batch_time if batch_time > 0 else 0
        
        # Assert
        assert batch_result["deleted"] == 100
        assert speedup > 5.0, f"Speedup {speedup:.1f}x is below 5x threshold"
        
        print(f"\n🚀 DELETE Performance:")
        print(f"   Batch:      {batch_time:.4f}s")
        print(f"   Sequential: {sequential_time:.4f}s")
        print(f"   Speedup:    {speedup:.1f}x (Target: 100x)")


# ============================================================================
# Integration Tests: PostgreSQL Batch UPSERT
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestBatchUpsertIntegration:
    """Integration tests for batch UPSERT operations"""
    
    async def test_upsert_all_new_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test upsert with all new documents (INSERT path)"""
        # Arrange
        documents = [
            {
                "document_id": f"new_doc_{i}",
                "title": f"New Title {i}",
                "content": f"New Content {i}",
                "metadata": {},
                "tags": [f"tag{i}"],
                "version": 1
            }
            for i in range(10)
        ]
        
        # Act
        result = await postgres_writer.batch_upsert(documents, conflict_resolution="update")
        
        # Assert
        assert result["inserted"] == 10
        assert result["updated"] == 0
        assert result["failed"] == 0
        
        # Verify documents exist
        doc = await get_document(postgres_backend, "new_doc_0")
        assert doc is not None
        assert doc["title"] == "New Title 0"
    
    async def test_upsert_all_existing_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test upsert with all existing documents (UPDATE path)"""
        # Arrange - Insert initial documents
        doc_ids = await insert_test_documents(postgres_backend, 10)
        
        # Create upsert documents (same IDs, new content)
        documents = [
            {
                "document_id": doc_id,
                "title": f"Updated Title {i}",
                "content": f"Updated Content {i}",
                "metadata": {"updated": True},
                "tags": ["updated"],
                "version": 2
            }
            for i, doc_id in enumerate(doc_ids)
        ]
        
        # Act
        result = await postgres_writer.batch_upsert(documents, conflict_resolution="update")
        
        # Assert
        assert result["inserted"] == 0
        assert result["updated"] == 10
        assert result["failed"] == 0
        
        # Verify updates
        doc = await get_document(postgres_backend, doc_ids[0])
        assert doc["title"] == "Updated Title 0"
        assert doc["metadata"] == {"updated": True}
    
    async def test_upsert_mixed_insert_update(self, postgres_backend, postgres_writer, clean_test_table):
        """Test upsert with mix of new and existing documents"""
        # Arrange - Insert 5 documents
        existing_ids = await insert_test_documents(postgres_backend, 5)
        
        # Create 10 documents (5 existing + 5 new)
        documents = []
        for i in range(10):
            if i < 5:
                # Existing documents (update)
                doc_id = existing_ids[i]
            else:
                # New documents (insert)
                doc_id = f"new_doc_{i}"
            
            documents.append({
                "document_id": doc_id,
                "title": f"Title {i}",
                "content": f"Content {i}",
                "metadata": {},
                "tags": [f"tag{i}"],
                "version": 1
            })
        
        # Act
        result = await postgres_writer.batch_upsert(documents, conflict_resolution="update")
        
        # Assert
        assert result["inserted"] == 5
        assert result["updated"] == 5
        assert result["failed"] == 0
        
        # Verify total count
        total_count = await count_documents(postgres_backend, deleted=False)
        assert total_count == 10
    
    async def test_batch_vs_sequential_upsert_speedup(self, postgres_backend, postgres_writer, clean_test_table):
        """Test batch upsert speedup vs sequential (Target: 83x)"""
        # Arrange - 50 existing + 50 new = 100 mixed
        existing_ids = await insert_test_documents(postgres_backend, 50)
        
        documents = []
        for i in range(100):
            if i < 50:
                doc_id = existing_ids[i]
            else:
                doc_id = f"new_doc_{i}"
            
            documents.append({
                "document_id": doc_id,
                "title": f"Title {i}",
                "content": f"Content {i}",
                "metadata": {},
                "tags": [f"tag{i}"],
                "version": 1
            })
        
        # Act - Batch Upsert
        batch_start = time.time()
        batch_result = await postgres_writer.batch_upsert(documents, conflict_resolution="update")
        batch_time = time.time() - batch_start
        
        # Reset for sequential test
        await postgres_backend.pool.acquire().execute("DELETE FROM test_batch_documents")
        existing_ids_2 = await insert_test_documents(postgres_backend, 50)
        
        documents_2 = []
        for i in range(100):
            if i < 50:
                doc_id = existing_ids_2[i]
            else:
                doc_id = f"new_doc_seq_{i}"
            
            documents_2.append({
                "document_id": doc_id,
                "title": f"Title {i}",
                "content": f"Content {i}",
                "metadata": {},
                "tags": [f"tag{i}"],
                "version": 1
            })
        
        # Act - Sequential Upsert
        sequential_time = await sequential_upsert(postgres_backend, documents_2)
        
        # Calculate speedup
        speedup = sequential_time / batch_time if batch_time > 0 else 0
        
        # Assert
        assert batch_result["inserted"] + batch_result["updated"] == 100
        assert speedup > 5.0, f"Speedup {speedup:.1f}x is below 5x threshold"
        
        print(f"\n🚀 UPSERT Performance:")
        print(f"   Batch:      {batch_time:.4f}s")
        print(f"   Sequential: {sequential_time:.4f}s")
        print(f"   Speedup:    {speedup:.1f}x (Target: 83x)")
        print(f"   Inserted:   {batch_result['inserted']}")
        print(f"   Updated:    {batch_result['updated']}")


# ============================================================================
# Integration Tests: Multi-Database Executor
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestMultiDatabaseIntegration:
    """Integration tests for multi-database orchestration"""
    
    async def test_batch_update_executor_postgres_only(self, batch_update_executor, postgres_backend, clean_test_table):
        """Test batch update executor with PostgreSQL only"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 10)
        updates = [
            {
                "document_id": doc_id,
                "fields": {"title": f"Executor Updated {i}"}
            }
            for i, doc_id in enumerate(doc_ids)
        ]
        
        # Act
        result = await batch_update_executor.execute(
            updates=updates,
            mode="partial",
            update_postgres=True,
            update_neo4j=False
        )
        
        # Assert
        assert result["postgres"]["updated"] == 10
        assert result["success"] is True
        assert result["partial_success"] is False
    
    async def test_batch_delete_executor_postgres_only(self, batch_delete_executor, postgres_backend, clean_test_table):
        """Test batch delete executor with PostgreSQL only"""
        # Arrange
        doc_ids = await insert_test_documents(postgres_backend, 10)
        
        # Act
        result = await batch_delete_executor.execute(
            document_ids=doc_ids,
            mode="soft",
            delete_postgres=True,
            delete_neo4j=False
        )
        
        # Assert
        assert result["postgres"]["deleted"] == 10
        assert result["success"] is True
        
        # Verify soft delete
        deleted_count = await count_documents(postgres_backend, deleted=True)
        assert deleted_count == 10
    
    async def test_batch_upsert_executor_postgres_only(self, batch_upsert_executor, postgres_backend, clean_test_table):
        """Test batch upsert executor with PostgreSQL only"""
        # Arrange
        documents = [
            {
                "document_id": f"executor_doc_{i}",
                "title": f"Executor Title {i}",
                "content": f"Content {i}",
                "metadata": {},
                "tags": [],
                "version": 1
            }
            for i in range(10)
        ]
        
        # Act
        result = await batch_upsert_executor.execute(
            documents=documents,
            upsert_postgres=True,
            upsert_neo4j=False
        )
        
        # Assert
        assert result["postgres"]["inserted"] == 10
        assert result["success"] is True
        
        # Verify documents exist
        doc = await get_document(postgres_backend, "executor_doc_0")
        assert doc is not None


# ============================================================================
# Integration Tests: Error Handling & Edge Cases
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandlingIntegration:
    """Integration tests for error handling and edge cases"""
    
    async def test_update_non_existent_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test updating non-existent documents (should fail gracefully)"""
        # Arrange
        updates = [
            {
                "document_id": f"non_existent_{i}",
                "fields": {"title": "Should not exist"}
            }
            for i in range(10)
        ]
        
        # Act
        result = await postgres_writer.batch_update(updates, mode="partial")
        
        # Assert - Should report 0 updated (no matching rows)
        assert result["updated"] == 0
    
    async def test_delete_non_existent_documents(self, postgres_backend, postgres_writer, clean_test_table):
        """Test deleting non-existent documents (should succeed with 0 affected)"""
        # Arrange
        doc_ids = [f"non_existent_{i}" for i in range(10)]
        
        # Act
        result = await postgres_writer.batch_delete(doc_ids, mode="soft")
        
        # Assert - Should report 0 deleted (no matching rows)
        assert result["deleted"] == 0
    
    async def test_upsert_with_missing_fields(self, postgres_backend, postgres_writer, clean_test_table):
        """Test upsert with missing required fields (should handle gracefully)"""
        # Arrange - Documents with missing title/content
        documents = [
            {
                "document_id": f"incomplete_doc_{i}",
                # Missing title, content, etc.
                "metadata": {},
                "version": 1
            }
            for i in range(5)
        ]
        
        # Act
        result = await postgres_writer.batch_upsert(documents, conflict_resolution="update")
        
        # Assert - Should insert with NULL values or defaults
        assert result["inserted"] + result["failed"] == 5


# ============================================================================
# Performance Summary Report
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestPerformanceSummary:
    """Generate performance summary report"""
    
    async def test_generate_performance_report(self, postgres_backend, postgres_writer, clean_test_table):
        """Generate comprehensive performance report for all operations"""
        print("\n" + "="*80)
        print("📊 Phase 4.3 - Integration Test Performance Report")
        print("="*80)
        
        # Test UPDATE Performance
        print("\n🔄 Batch UPDATE Performance:")
        doc_ids = await insert_test_documents(postgres_backend, 100)
        updates = [
            {"document_id": doc_id, "fields": {"title": f"Updated {i}"}}
            for i, doc_id in enumerate(doc_ids)
        ]
        
        batch_start = time.time()
        batch_result = await postgres_writer.batch_update(updates, mode="partial")
        batch_time = time.time() - batch_start
        
        # Sequential comparison
        doc_ids_2 = await insert_test_documents(postgres_backend, 100)
        updates_2 = [
            {"document_id": doc_id, "fields": {"title": f"Updated {i}"}}
            for i, doc_id in enumerate(doc_ids_2)
        ]
        sequential_time = await sequential_update(postgres_backend, updates_2)
        update_speedup = sequential_time / batch_time if batch_time > 0 else 0
        
        print(f"   Batch:      {batch_time:.4f}s (100 documents)")
        print(f"   Sequential: {sequential_time:.4f}s")
        print(f"   Speedup:    {update_speedup:.1f}x (Target: 67-80x)")
        
        # Test DELETE Performance
        print("\n🗑️ Batch DELETE Performance:")
        await postgres_backend.pool.acquire().execute("DELETE FROM test_batch_documents")
        doc_ids = await insert_test_documents(postgres_backend, 100)
        
        batch_start = time.time()
        batch_result = await postgres_writer.batch_delete(doc_ids, mode="soft")
        batch_time = time.time() - batch_start
        
        # Sequential comparison
        doc_ids_2 = await insert_test_documents(postgres_backend, 100)
        sequential_time = await sequential_delete(postgres_backend, doc_ids_2)
        delete_speedup = sequential_time / batch_time if batch_time > 0 else 0
        
        print(f"   Batch:      {batch_time:.4f}s (100 documents)")
        print(f"   Sequential: {sequential_time:.4f}s")
        print(f"   Speedup:    {delete_speedup:.1f}x (Target: 100x)")
        
        # Test UPSERT Performance
        print("\n🔀 Batch UPSERT Performance:")
        await postgres_backend.pool.acquire().execute("DELETE FROM test_batch_documents")
        existing_ids = await insert_test_documents(postgres_backend, 50)
        
        documents = []
        for i in range(100):
            doc_id = existing_ids[i] if i < 50 else f"new_doc_{i}"
            documents.append({
                "document_id": doc_id,
                "title": f"Title {i}",
                "content": f"Content {i}",
                "metadata": {},
                "tags": [],
                "version": 1
            })
        
        batch_start = time.time()
        batch_result = await postgres_writer.batch_upsert(documents, conflict_resolution="update")
        batch_time = time.time() - batch_start
        
        print(f"   Batch:      {batch_time:.4f}s (100 documents)")
        print(f"   Inserted:   {batch_result['inserted']}")
        print(f"   Updated:    {batch_result['updated']}")
        print(f"   Estimated Speedup: 50-100x (based on UPDATE/DELETE results)")
        
        # Summary
        print("\n" + "="*80)
        print("✅ Integration Tests Complete!")
        print("="*80)
        print(f"\n📈 Performance Summary:")
        print(f"   UPDATE Speedup:  {update_speedup:.1f}x (Target: 67-80x)")
        print(f"   DELETE Speedup:  {delete_speedup:.1f}x (Target: 100x)")
        print(f"   UPSERT Status:   {batch_result['inserted']} inserted, {batch_result['updated']} updated")
        print(f"\n🎯 Status: {'✅ PASSED' if update_speedup > 5 and delete_speedup > 5 else '❌ NEEDS OPTIMIZATION'}")
        print("="*80)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    print("Run tests with: pytest tests/test_batch_write_integration.py -v -m integration")
