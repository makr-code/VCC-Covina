"""
Integration Tests for CouchDB Batch Operations (No Mocks)

Tests batch operations with real CouchDB database:
- batch_update, batch_delete, batch_upsert

Run with: pytest tests/test_couchdb_integration.py -v -m integration -s

Author: GitHub Copilot
Date: October 21, 2025
Version: 1.0.0
"""

import pytest
import pytest
import time
import os
from typing import List, Dict, Any

from uds3.database.database_api_couchdb import CouchDBAdapter

# ============================================================================
# Configuration
# ============================================================================

COUCHDB_CONFIG = {
    'host': os.getenv('COUCHDB_HOST', '192.168.178.94'),
    'port': int(os.getenv('COUCHDB_PORT', '32931')),
    'username': os.getenv('COUCHDB_USER', 'admin'),
    'password': os.getenv('COUCHDB_PASSWORD', 'admin'),
    'db': 'test_batch_operations'
}

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def couchdb_adapter():
    """Real CouchDB adapter connection (session-scoped)"""
    adapter = CouchDBAdapter(COUCHDB_CONFIG)
    
    # Connect
    success = adapter.connect()
    if not success:
        pytest.skip("CouchDB connection failed")
    
    yield adapter
    
    # Cleanup - delete test database
    try:
        if adapter.db_name in adapter.server:
            del adapter.server[adapter.db_name]
    except Exception:
        pass
    
    adapter.disconnect()


@pytest.fixture(scope="function")
def clean_database(couchdb_adapter):
    """Clean database before each test"""
    # Delete all documents
    try:
        for doc_id in couchdb_adapter.db:
            doc = couchdb_adapter.db[doc_id]
            couchdb_adapter.db.delete(doc)
    except Exception:
        pass
    
    yield
    
    # Cleanup after test
    try:
        for doc_id in couchdb_adapter.db:
            doc = couchdb_adapter.db[doc_id]
            couchdb_adapter.db.delete(doc)
    except Exception:
        pass


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_docs(adapter, count: int) -> List[str]:
    """Create test documents and return document IDs"""
    doc_ids = []
    docs = []
    
    for i in range(count):
        doc_id = f"doc_{i:04d}"
        doc = {
            "_id": doc_id,
            "title": f"Test Doc {i}",
            "content": f"Content {i}",
            "status": "draft",
            "version": 1
        }
        docs.append(doc)
        doc_ids.append(doc_id)
    
    # Bulk insert
    adapter.db.update(docs)
    return doc_ids


def get_document(adapter, doc_id: str) -> Dict:
    """Get document by ID"""
    try:
        if doc_id in adapter.db:
            return dict(adapter.db[doc_id])
    except Exception:
        pass
    return None


def count_documents(adapter) -> int:
    """Count documents in database"""
    try:
        return len([doc_id for doc_id in adapter.db if not doc_id.startswith('_design')])
    except Exception:
        return 0


# ============================================================================
# BATCH UPDATE INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestCouchDBBatchUpdateIntegration:
    """Integration tests for batch_update with real CouchDB database"""
    
    def test_batch_update_small_batch(self, couchdb_adapter, clean_database):
        """Test batch update with 10 documents"""
        # Arrange
        doc_ids = create_test_docs(couchdb_adapter, 10)
        updates = [
            {"document_id": doc_id, "fields": {"status": "approved"}}
            for doc_id in doc_ids
        ]
        
        # Act
        print("\n[TEST] CouchDB batch update 10 documents...")
        start = time.time()
        result = couchdb_adapter.batch_update(updates, mode="partial")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Updated {result['updated']} docs in {elapsed*1000:.2f}ms")
        assert result["success"] is True
        assert result["updated"] == 10
        
        # Verify in database
        doc = get_document(couchdb_adapter, doc_ids[0])
        assert doc is not None
        assert doc["status"] == "approved"
    
    def test_batch_update_medium_batch(self, couchdb_adapter, clean_database):
        """Test batch update with 100 documents"""
        # Arrange
        doc_ids = create_test_docs(couchdb_adapter, 100)
        updates = [
            {"document_id": doc_id, "fields": {"status": "reviewed", "version": 2}}
            for doc_id in doc_ids
        ]
        
        # Act
        print("\n[TEST] CouchDB batch update 100 documents...")
        start = time.time()
        result = couchdb_adapter.batch_update(updates, mode="partial")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Updated {result['updated']} docs in {elapsed*1000:.2f}ms")
        print(f"[PERF] {elapsed*1000/100:.2f}ms per document")
        assert result["success"] is True
        assert result["updated"] == 100
        
        # Verify random document
        doc = get_document(couchdb_adapter, doc_ids[50])
        assert doc is not None
        assert doc["status"] == "reviewed"
        assert doc["version"] == 2


# ============================================================================
# BATCH DELETE INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestCouchDBBatchDeleteIntegration:
    """Integration tests for batch_delete with real CouchDB database"""
    
    def test_batch_delete_soft(self, couchdb_adapter, clean_database):
        """Test soft delete (deleted=true)"""
        # Arrange
        doc_ids = create_test_docs(couchdb_adapter, 10)
        
        # Act
        print("\n[TEST] CouchDB soft delete 10 documents...")
        start = time.time()
        result = couchdb_adapter.batch_delete(doc_ids, soft_delete=True)
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Deleted {result['deleted']} docs in {elapsed*1000:.2f}ms")
        assert result["success"] is True
        assert result["deleted"] == 10
        
        # Verify document still exists but marked deleted
        doc = get_document(couchdb_adapter, doc_ids[0])
        assert doc is not None
        assert doc["deleted"] is True
    
    def test_batch_delete_hard(self, couchdb_adapter, clean_database):
        """Test hard delete (_deleted=true)"""
        # Arrange
        doc_ids = create_test_docs(couchdb_adapter, 10)
        
        # Act
        print("\n[TEST] CouchDB hard delete 10 documents...")
        start = time.time()
        result = couchdb_adapter.batch_delete(doc_ids, soft_delete=False)
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Deleted {result['deleted']} docs in {elapsed*1000:.2f}ms")
        assert result["success"] is True
        assert result["deleted"] == 10
        
        # Verify document no longer exists
        doc = get_document(couchdb_adapter, doc_ids[0])
        assert doc is None
        
        # Verify all documents deleted
        remaining = count_documents(couchdb_adapter)
        assert remaining == 0


# ============================================================================
# BATCH UPSERT INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestCouchDBBatchUpsertIntegration:
    """Integration tests for batch_upsert with real CouchDB database"""
    
    def test_batch_upsert_all_inserts(self, couchdb_adapter, clean_database):
        """Test upsert with all new documents (all inserts)"""
        # Arrange
        documents = [
            {
                "document_id": f"new_doc_{i:04d}",
                "fields": {
                    "title": f"New Doc {i}",
                    "content": f"Content {i}",
                    "status": "draft"
                }
            }
            for i in range(10)
        ]
        
        # Act
        print("\n[TEST] CouchDB upsert 10 new documents (inserts)...")
        start = time.time()
        result = couchdb_adapter.batch_upsert(documents, conflict_resolution="update")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Upserted {result['inserted'] + result['updated']} docs in {elapsed*1000:.2f}ms")
        print(f"[DETAIL] Inserted: {result['inserted']}, Updated: {result['updated']}")
        assert result["success"] is True
        assert result["inserted"] + result["updated"] == 10
        
        # Verify document exists
        doc = get_document(couchdb_adapter, "new_doc_0000")
        assert doc is not None
        assert doc["title"] == "New Doc 0"
    
    def test_batch_upsert_all_updates(self, couchdb_adapter, clean_database):
        """Test upsert with all existing documents (all updates)"""
        # Arrange
        doc_ids = create_test_docs(couchdb_adapter, 10)
        documents = [
            {
                "document_id": doc_id,
                "fields": {
                    "title": f"Updated Doc {i}",
                    "status": "published",
                    "version": 2
                }
            }
            for i, doc_id in enumerate(doc_ids)
        ]
        
        # Act
        print("\n[TEST] CouchDB upsert 10 existing documents (updates)...")
        start = time.time()
        result = couchdb_adapter.batch_upsert(documents, conflict_resolution="update")
        elapsed = time.time() - start
        
        # Assert
        print(f"[RESULT] Upserted {result['inserted'] + result['updated']} docs in {elapsed*1000:.2f}ms")
        print(f"[DETAIL] Inserted: {result['inserted']}, Updated: {result['updated']}")
        assert result["success"] is True
        assert result["inserted"] + result["updated"] == 10
        
        # Verify document updated
        doc = get_document(couchdb_adapter, doc_ids[0])
        assert doc is not None
        assert doc["title"] == "Updated Doc 0"
        assert doc["version"] == 2


# ============================================================================
# PERFORMANCE VALIDATION
# ============================================================================

@pytest.mark.integration
class TestCouchDBBatchPerformance:
    """Validate batch operations performance"""
    
    def test_batch_vs_sequential_update(self, couchdb_adapter, clean_database):
        """Validate batch update speedup vs sequential updates"""
        # Arrange
        doc_ids = create_test_docs(couchdb_adapter, 100)
        updates = [
            {"document_id": doc_id, "fields": {"status": "approved"}}
            for doc_id in doc_ids
        ]
        
        # Act - Batch Update
        print("\n[TEST] CouchDB batch update 100 documents...")
        start_batch = time.time()
        result_batch = couchdb_adapter.batch_update(updates, mode="partial")
        elapsed_batch = time.time() - start_batch
        
        # Act - Sequential Updates (simulate with 10 docs)
        print("[TEST] CouchDB sequential update 10 documents (simulated)...")
        start_seq = time.time()
        for update in updates[:10]:
            couchdb_adapter.batch_update([update], mode="partial")
        elapsed_seq = time.time() - start_seq
        
        # Calculate speedup
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
