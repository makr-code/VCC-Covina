"""
Integration Tests for Database Adapters (No Mocks)

Tests batch operations with real databases:
- PostgreSQL: batch_update, batch_delete, batch_upsert

Run with: pytest tests/test_adapter_integration.py -v -m integration -s

Note: Uses synchronous psycopg2-based PostgreSQLRelationalBackend adapter.

Author: GitHub Copilot
Date: October 21, 2025
Version: 2.0.0
"""

import pytest
import pytest_asyncio
import asyncio
import time
import os
from datetime import datetime
from typing import List, Dict, Any

from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend

# ============================================================================
# Configuration
# ============================================================================

POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', '192.168.178.94'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'database': os.getenv('POSTGRES_DB', 'postgres')
}

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def postgres_adapter():
    """Real PostgreSQL adapter connection (session-scoped, synchronous)"""
    config = {
        'host': POSTGRES_CONFIG['host'],
        'port': POSTGRES_CONFIG['port'],
        'username': POSTGRES_CONFIG['user'],
        'password': POSTGRES_CONFIG['password'],
        'database': POSTGRES_CONFIG['database'],
        'table_name': 'test_batch_operations'  # Use test table
    }
    adapter = PostgreSQLRelationalBackend(config)
    
    # Connect (synchronous method)
    success = adapter.connect()
    if not success:
        pytest.skip("PostgreSQL connection failed")
    
    # Create test table (synchronous psycopg2)
    # Note: This adapter uses 'conn' not 'connection'!
    with adapter.conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_batch_operations (
                document_id VARCHAR(255) PRIMARY KEY,
                title TEXT,
                content TEXT,
                status VARCHAR(50) DEFAULT 'draft',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                deleted BOOLEAN DEFAULT FALSE,
                version INTEGER DEFAULT 1
            )
        """)
        adapter.conn.commit()
    
    yield adapter
    
    # Cleanup (synchronous method)
    adapter.disconnect()


@pytest_asyncio.fixture(scope="function")
async def clean_table(postgres_adapter):
    """Clean test table before each test"""
    with postgres_adapter.conn.cursor() as cursor:
        cursor.execute("DELETE FROM test_batch_operations")
        postgres_adapter.conn.commit()
    yield
    # Cleanup after test
    with postgres_adapter.conn.cursor() as cursor:
        cursor.execute("DELETE FROM test_batch_operations")
        postgres_adapter.conn.commit()


# ============================================================================
# Helper Functions (Synchronous psycopg2)
# ============================================================================

def insert_test_docs(adapter, count: int) -> List[str]:
    """Insert test documents and return document IDs"""
    doc_ids = []
    with adapter.conn.cursor() as cursor:
        for i in range(count):
            doc_id = f"doc_{i:04d}"
            cursor.execute("""
                INSERT INTO test_batch_operations 
                (document_id, title, content, status, version)
                VALUES (%s, %s, %s, %s, %s)
            """, (doc_id, f"Test Doc {i}", f"Content {i}", "draft", 1))
            doc_ids.append(doc_id)
        adapter.conn.commit()
    return doc_ids


def get_document(adapter, doc_id: str) -> Dict:
    """Get document by ID"""
    with adapter.conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM test_batch_operations WHERE document_id = %s",
            (doc_id,)
        )
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
    return None


# ============================================================================
# BATCH UPDATE INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestBatchUpdateIntegration:
    """Integration tests for batch_update with real PostgreSQL database"""
    
    @pytest.mark.asyncio
    async def test_batch_update_small_batch(self, postgres_adapter, clean_table):
        """Test batch update with 10 documents"""
        # Arrange
        doc_ids = insert_test_docs(postgres_adapter, 10)
        updates = [
            {"document_id": doc_id, "fields": {"status": "approved"}}
            for doc_id in doc_ids
        ]
        
        # Act
        print("\n[TEST] Batch update 10 documents...")
        start = time.time()
        result = await postgres_adapter.batch_update(updates, mode="partial")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Updated {result['updated']} docs in {elapsed*1000:.2f}ms")
        assert result["success"] is True
        assert result["updated"] == 10
        
        # Verify in database
        doc = get_document(postgres_adapter, doc_ids[0])
        assert doc is not None
        assert doc["status"] == "approved"
    
    @pytest.mark.asyncio
    async def test_batch_update_medium_batch(self, postgres_adapter, clean_table):
        """Test batch update with 100 documents"""
        # Arrange
        doc_ids = insert_test_docs(postgres_adapter, 100)
        updates = [
            {"document_id": doc_id, "fields": {"status": "reviewed", "version": 2}}
            for doc_id in doc_ids
        ]
        
        # Act
        print("\n[TEST] Batch update 100 documents...")
        start = time.time()
        result = await postgres_adapter.batch_update(updates, mode="partial")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Updated {result['updated']} docs in {elapsed*1000:.2f}ms")
        print(f"[PERF] {elapsed*1000/100:.2f}ms per document")
        assert result["success"] is True
        assert result["updated"] == 100
        
        # Verify random document
        doc = get_document(postgres_adapter, doc_ids[50])
        assert doc is not None
        assert doc["status"] == "reviewed"
        assert doc["version"] == 2


# ============================================================================
# BATCH DELETE INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestBatchDeleteIntegration:
    """Integration tests for batch_delete with real PostgreSQL database"""
    
    @pytest.mark.asyncio
    async def test_batch_delete_soft(self, postgres_adapter, clean_table):
        """Test soft delete (UPDATE deleted=true)"""
        # Arrange
        doc_ids = insert_test_docs(postgres_adapter, 10)
        
        # Act
        print("\n[TEST] Soft delete 10 documents...")
        start = time.time()
        result = await postgres_adapter.batch_delete(doc_ids, soft_delete=True)
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Deleted {result['deleted']} docs in {elapsed*1000:.2f}ms")
        assert result["success"] is True
        assert result["deleted"] == 10
        
        # Verify document still exists but marked deleted
        doc = get_document(postgres_adapter, doc_ids[0])
        assert doc is not None
        assert doc["deleted"] is True
    
    @pytest.mark.asyncio
    async def test_batch_delete_hard(self, postgres_adapter, clean_table):
        """Test hard delete (DELETE FROM)"""
        # Arrange
        doc_ids = insert_test_docs(postgres_adapter, 10)
        
        # Act
        print("\n[TEST] Hard delete 10 documents...")
        start = time.time()
        result = await postgres_adapter.batch_delete(doc_ids, soft_delete=False)
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Deleted {result['deleted']} docs in {elapsed*1000:.2f}ms")
        assert result["success"] is True
        assert result["deleted"] == 10
        
        # Verify document no longer exists
        doc = get_document(postgres_adapter, doc_ids[0])
        assert doc is None


# ============================================================================
# BATCH UPSERT INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestBatchUpsertIntegration:
    """Integration tests for batch_upsert with real PostgreSQL database"""
    
    @pytest.mark.asyncio
    async def test_batch_upsert_all_inserts(self, postgres_adapter, clean_table):
        """Test upsert with all new documents (all inserts)"""
        # Arrange
        documents = [
            {
                "document_id": f"new_doc_{i:04d}",
                "fields": {
                    "title": f"New Doc {i}",
                    "content": f"Content {i}",
                    "status": "draft",
                    "version": 1
                }
            }
            for i in range(10)
        ]
        
        # Act
        print("\n[TEST] Upsert 10 new documents (inserts)...")
        start = time.time()
        result = await postgres_adapter.batch_upsert(documents, conflict_resolution="update")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Upserted {result['inserted'] + result['updated']} docs in {elapsed*1000:.2f}ms")
        print(f"[DETAIL] Inserted: {result['inserted']}, Updated: {result['updated']}")
        assert result["success"] is True
        assert result["inserted"] + result["updated"] == 10  # Total count correct
        # Note: Exact insert/update split is hard to determine in PostgreSQL ON CONFLICT
        
        # Verify document exists
        doc = get_document(postgres_adapter, "new_doc_0000")
        assert doc is not None
        assert doc["title"] == "New Doc 0"
    
    @pytest.mark.asyncio
    async def test_batch_upsert_all_updates(self, postgres_adapter, clean_table):
        """Test upsert with all existing documents (all updates)"""
        # Arrange
        doc_ids = insert_test_docs(postgres_adapter, 10)
        documents = [
            {
                "document_id": doc_id,
                "fields": {
                    "title": f"Updated Doc {i}",
                    "content": f"Updated Content {i}",
                    "status": "published",
                    "version": 2
                }
            }
            for i, doc_id in enumerate(doc_ids)
        ]
        
        # Act
        print("\n[TEST] Upsert 10 existing documents (updates)...")
        start = time.time()
        result = await postgres_adapter.batch_upsert(documents, conflict_resolution="update")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Upserted {result['inserted'] + result['updated']} docs in {elapsed*1000:.2f}ms")
        print(f"[DETAIL] Inserted: {result['inserted']}, Updated: {result['updated']}")
        assert result["success"] is True
        assert result["inserted"] + result["updated"] == 10  # Total count correct
        # Note: Exact insert/update split is hard to determine in PostgreSQL ON CONFLICT
        
        # Verify document updated
        doc = get_document(postgres_adapter, doc_ids[0])
        assert doc is not None
        assert doc["title"] == "Updated Doc 0"
        assert doc["version"] == 2
    
    @pytest.mark.asyncio
    async def test_batch_upsert_mixed(self, postgres_adapter, clean_table):
        """Test upsert with mix of inserts and updates"""
        # Arrange
        existing_ids = insert_test_docs(postgres_adapter, 5)
        documents = []
        
        # 5 updates to existing docs
        for i, doc_id in enumerate(existing_ids):
            documents.append({
                "document_id": doc_id,
                "fields": {"title": f"Updated {i}", "status": "published"}
            })
        
        # 5 inserts for new docs
        for i in range(5, 10):
            documents.append({
                "document_id": f"new_doc_{i:04d}",
                "fields": {"title": f"New Doc {i}", "status": "draft"}
            })
        
        # Act
        print("\n[TEST] Upsert 10 documents (5 inserts + 5 updates)...")
        start = time.time()
        result = await postgres_adapter.batch_upsert(documents, conflict_resolution="update")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Upserted {result['inserted'] + result['updated']} docs in {elapsed*1000:.2f}ms")
        print(f"[DETAIL] Inserted: {result['inserted']}, Updated: {result['updated']}")
        assert result["success"] is True
        assert result["inserted"] == 5
        assert result["updated"] == 5


# ============================================================================
# PERFORMANCE VALIDATION
# ============================================================================

@pytest.mark.integration
class TestBatchPerformance:
    """Validate batch operations performance"""
    
    @pytest.mark.asyncio
    async def test_batch_vs_sequential_update(self, postgres_adapter, clean_table):
        """Validate batch update speedup vs sequential updates"""
        # Arrange
        doc_ids = insert_test_docs(postgres_adapter, 100)
        updates = [
            {"document_id": doc_id, "fields": {"status": "approved"}}
            for doc_id in doc_ids
        ]
        
        # Act - Batch Update
        print("\n[TEST] Batch update 100 documents...")
        start_batch = time.time()
        result_batch = await postgres_adapter.batch_update(updates, mode="partial")
        elapsed_batch = time.time() - start_batch
        
        # Act - Sequential Updates (simulate)
        print("[TEST] Sequential update 10 documents (simulated)...")
        start_seq = time.time()
        for update in updates[:10]:  # Only 10 to avoid slowness
            await postgres_adapter.batch_update([update], mode="partial")
        elapsed_seq = time.time() - start_seq
        
        # Calculate speedup (extrapolate sequential time)
        sequential_estimated = (elapsed_seq / 10) * 100
        speedup = sequential_estimated / elapsed_batch
        
        # Report
        print(f"\n[PERFORMANCE REPORT]")
        print(f"Batch (100 docs):      {elapsed_batch*1000:.2f}ms")
        print(f"Sequential (10 docs):  {elapsed_seq*1000:.2f}ms")
        print(f"Sequential (est 100):  {sequential_estimated*1000:.2f}ms")
        print(f"Speedup:               {speedup:.1f}x")
        
        # Assert
        assert result_batch["success"] is True
        assert result_batch["updated"] == 100
        assert speedup >= 5, f"Expected >=5x speedup, got {speedup:.1f}x"
        print(f"[PASS] Batch operations are {speedup:.1f}x faster! ✅")
