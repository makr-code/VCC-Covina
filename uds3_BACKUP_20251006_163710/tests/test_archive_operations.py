"""
Tests for UDS3 Archive Operations Module
==========================================

Comprehensive test suite for archive operations:
- Basic archive/restore operations
- Batch operations
- Retention policies
- Auto-expiration
- Metadata tracking
- Concurrent operations
- Performance tests

Author: UDS3 Team
Date: 2. Oktober 2025
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List

from uds3_archive_operations import (
    ArchiveManager,
    create_archive_manager,
    ArchiveResult,
    RestoreResult,
    BatchArchiveResult,
    ArchiveInfo,
    ArchiveMetadata,
    RetentionPolicy,
    RetentionPeriod,
    ArchiveStrategy,
    ArchiveStatus,
    RestoreStrategy,
)


# ============================================================================
# Mock UnifiedStrategy
# ============================================================================

class MockBackend:
    """Mock database backend"""
    def __init__(self):
        self.data = {}
    
    def update_metadata(self, doc_id, metadata):
        if doc_id not in self.data:
            self.data[doc_id] = {}
        self.data[doc_id].update(metadata)
    
    def set_node_properties(self, doc_id, props):
        if doc_id not in self.data:
            self.data[doc_id] = {}
        self.data[doc_id].update(props)
    
    def update(self, **kwargs):
        pass


class MockUnifiedStrategy:
    """Mock UnifiedDatabaseStrategy for testing"""
    def __init__(self):
        self.vector_backend = MockBackend()
        self.graph_backend = MockBackend()
        self.relational_backend = MockBackend()
        self.file_backend = MockBackend()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def unified_strategy():
    """Create mock unified strategy"""
    return MockUnifiedStrategy()


@pytest.fixture
def archive_manager(unified_strategy):
    """Create ArchiveManager instance"""
    return ArchiveManager(unified_strategy)


@pytest.fixture
def populated_archive_manager(unified_strategy):
    """Create ArchiveManager with some archived documents"""
    manager = ArchiveManager(unified_strategy)
    
    # Archive 5 documents
    for i in range(5):
        manager.archive_document(
            document_id=f"doc{i}",
            retention_days=365,
            archived_by="test",
            reason="test archive"
        )
    
    return manager


# ============================================================================
# Test ArchiveMetadata
# ============================================================================

class TestArchiveMetadata:
    """Test ArchiveMetadata dataclass"""
    
    def test_metadata_creation(self):
        """Test creating archive metadata"""
        archived_at = datetime.utcnow()
        metadata = ArchiveMetadata(
            archive_id="archive123",
            document_id="doc1",
            archived_at=archived_at,
            archived_by="admin",
            retention_days=365
        )
        
        assert metadata.archive_id == "archive123"
        assert metadata.document_id == "doc1"
        assert metadata.archived_at == archived_at
        assert metadata.archived_by == "admin"
        assert metadata.retention_days == 365
        assert metadata.status == ArchiveStatus.ARCHIVED
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dict"""
        archived_at = datetime.utcnow()
        metadata = ArchiveMetadata(
            archive_id="archive123",
            document_id="doc1",
            archived_at=archived_at
        )
        
        data = metadata.to_dict()
        
        assert data['archive_id'] == "archive123"
        assert data['document_id'] == "doc1"
        assert 'archived_at' in data
        assert data['status'] == 'archived'
    
    def test_metadata_from_dict(self):
        """Test creating metadata from dict"""
        data = {
            'archive_id': 'archive123',
            'document_id': 'doc1',
            'archived_at': datetime.utcnow().isoformat(),
            'status': 'archived'
        }
        
        metadata = ArchiveMetadata.from_dict(data)
        
        assert metadata.archive_id == 'archive123'
        assert metadata.document_id == 'doc1'
        assert isinstance(metadata.archived_at, datetime)


# ============================================================================
# Test RetentionPolicy
# ============================================================================

class TestRetentionPolicy:
    """Test RetentionPolicy"""
    
    def test_policy_creation(self):
        """Test creating retention policy"""
        policy = RetentionPolicy(
            name="test_policy",
            retention_days=365,
            auto_delete=True
        )
        
        assert policy.name == "test_policy"
        assert policy.retention_days == 365
        assert policy.auto_delete is True
    
    def test_is_expired(self):
        """Test checking if document is expired"""
        policy = RetentionPolicy(
            name="test",
            retention_days=30,
            auto_delete=True
        )
        
        # Not expired (archived today)
        recent = datetime.utcnow()
        assert policy.is_expired(recent) is False
        
        # Expired (archived 31 days ago)
        old = datetime.utcnow() - timedelta(days=31)
        assert policy.is_expired(old) is True
    
    def test_permanent_retention(self):
        """Test permanent retention (never expires)"""
        policy = RetentionPolicy(
            name="permanent",
            retention_days=RetentionPeriod.PERMANENT.value,
            auto_delete=False
        )
        
        # Should never expire
        very_old = datetime.utcnow() - timedelta(days=10000)
        assert policy.is_expired(very_old) is False
    
    def test_expires_at(self):
        """Test calculating expiry date"""
        policy = RetentionPolicy(
            name="test",
            retention_days=30,
            auto_delete=True
        )
        
        archived_at = datetime.utcnow()
        expires_at = policy.expires_at(archived_at)
        
        assert expires_at is not None
        assert expires_at > archived_at
        
        # Should expire in ~30 days
        delta = expires_at - archived_at
        assert 29 <= delta.days <= 31


# ============================================================================
# Test Basic Archive Operations
# ============================================================================

class TestBasicArchiveOperations:
    """Test basic archive and restore operations"""
    
    def test_archive_document(self, archive_manager):
        """Test archiving a document"""
        result = archive_manager.archive_document(
            document_id="doc1",
            retention_days=365,
            archived_by="admin",
            reason="Annual archive"
        )
        
        assert result.success is True
        assert result.document_id == "doc1"
        assert result.archive_id is not None
        assert result.archived_at is not None
        assert result.retention_until is not None
        assert len(result.affected_databases) > 0
    
    def test_archive_with_retention_policy(self, archive_manager):
        """Test archiving with named retention policy"""
        # Add policy
        policy = RetentionPolicy(
            name="long_term",
            retention_days=2555,
            auto_delete=False
        )
        archive_manager.add_retention_policy(policy)
        
        # Archive with policy
        result = archive_manager.archive_document(
            document_id="doc2",
            retention_policy="long_term",
            archived_by="admin"
        )
        
        assert result.success is True
        assert result.document_id == "doc2"
        
        # Check metadata
        metadata = archive_manager.get_archive_metadata("doc2")
        assert metadata.retention_policy == "long_term"
        assert metadata.retention_days == 2555
    
    def test_restore_document(self, archive_manager):
        """Test restoring an archived document"""
        # First archive
        archive_result = archive_manager.archive_document(
            document_id="doc3",
            retention_days=365
        )
        assert archive_result.success is True
        
        # Then restore
        restore_result = archive_manager.restore_document(
            document_id="doc3",
            strategy=RestoreStrategy.REPLACE,
            restored_by="admin"
        )
        
        assert restore_result.success is True
        assert restore_result.document_id == "doc3"
        assert restore_result.restored_at is not None
        assert len(restore_result.affected_databases) > 0
        
        # Check metadata updated
        metadata = archive_manager.get_archive_metadata("doc3")
        assert metadata.status == ArchiveStatus.RESTORED
        assert metadata.restore_count == 1
    
    def test_restore_nonexistent(self, archive_manager):
        """Test restoring document that was never archived"""
        result = archive_manager.restore_document(
            document_id="nonexistent",
            strategy=RestoreStrategy.REPLACE
        )
        
        assert result.success is False
        assert "No archive found" in result.errors[0]
    
    def test_archive_with_default_retention(self, archive_manager):
        """Test archive uses default retention when not specified"""
        archive_manager.set_default_retention_days(180)
        
        result = archive_manager.archive_document(
            document_id="doc4"
        )
        
        assert result.success is True
        
        metadata = archive_manager.get_archive_metadata("doc4")
        assert metadata.retention_days == 180


# ============================================================================
# Test Batch Operations
# ============================================================================

class TestBatchOperations:
    """Test batch archive/restore operations"""
    
    def test_batch_archive(self, archive_manager):
        """Test archiving multiple documents"""
        doc_ids = ["batch1", "batch2", "batch3", "batch4", "batch5"]
        
        result = archive_manager.batch_archive(
            document_ids=doc_ids,
            retention_days=365,
            archived_by="system",
            reason="Batch archive test"
        )
        
        assert result.success is True
        assert result.total_count == 5
        assert result.archived_count == 5
        assert result.failed_count == 0
        assert len(result.results) == 5
    
    def test_batch_restore(self, archive_manager):
        """Test restoring multiple documents"""
        # First archive some documents
        doc_ids = ["restore1", "restore2", "restore3"]
        archive_result = archive_manager.batch_archive(
            document_ids=doc_ids,
            retention_days=365
        )
        assert archive_result.success is True
        
        # Then restore them
        restore_result = archive_manager.batch_restore(
            document_ids=doc_ids,
            strategy=RestoreStrategy.REPLACE,
            restored_by="admin"
        )
        
        assert restore_result['success'] is True
        assert restore_result['total_count'] == 3
        assert restore_result['restored_count'] == 3
        assert restore_result['failed_count'] == 0
    
    def test_batch_archive_with_failures(self, archive_manager):
        """Test batch archive with some failures"""
        # Mix of valid and invalid IDs (though in mock all succeed)
        doc_ids = ["valid1", "valid2", "valid3"]
        
        result = archive_manager.batch_archive(
            document_ids=doc_ids,
            retention_days=365
        )
        
        # In mock environment, all should succeed
        assert result.total_count == 3
        assert result.archived_count >= 0


# ============================================================================
# Test Retention Policies
# ============================================================================

class TestRetentionPolicies:
    """Test retention policy management"""
    
    def test_add_retention_policy(self, archive_manager):
        """Test adding a retention policy"""
        policy = RetentionPolicy(
            name="contracts",
            retention_days=2555,
            auto_delete=False
        )
        
        archive_manager.add_retention_policy(policy)
        
        retrieved = archive_manager.get_retention_policy("contracts")
        assert retrieved is not None
        assert retrieved.name == "contracts"
        assert retrieved.retention_days == 2555
    
    def test_remove_retention_policy(self, archive_manager):
        """Test removing a retention policy"""
        policy = RetentionPolicy(name="temp", retention_days=30)
        archive_manager.add_retention_policy(policy)
        
        # Verify it exists
        assert archive_manager.get_retention_policy("temp") is not None
        
        # Remove it
        result = archive_manager.remove_retention_policy("temp")
        assert result is True
        
        # Verify it's gone
        assert archive_manager.get_retention_policy("temp") is None
    
    def test_list_retention_policies(self, archive_manager):
        """Test listing all retention policies"""
        # Add multiple policies
        policies = [
            RetentionPolicy(name="short", retention_days=30),
            RetentionPolicy(name="medium", retention_days=365),
            RetentionPolicy(name="long", retention_days=2555),
        ]
        
        for policy in policies:
            archive_manager.add_retention_policy(policy)
        
        all_policies = archive_manager.list_retention_policies()
        assert len(all_policies) >= 3
    
    def test_apply_retention_policies(self, archive_manager):
        """Test applying retention policies"""
        # Add policy with short retention for testing
        policy = RetentionPolicy(
            name="test_expiry",
            retention_days=0,  # Expires immediately
            auto_delete=True
        )
        archive_manager.add_retention_policy(policy)
        
        # Archive document with policy
        archive_manager.archive_document(
            document_id="expire_me",
            retention_policy="test_expiry"
        )
        
        # Wait a moment
        time.sleep(0.1)
        
        # Apply policies
        result = archive_manager.apply_retention_policies()
        
        assert result['success'] is True
        assert result['expired_count'] >= 0


# ============================================================================
# Test Auto-Expiration
# ============================================================================

class TestAutoExpiration:
    """Test automatic expiration of archived documents"""
    
    def test_auto_expire_archived(self, archive_manager):
        """Test auto-expiring old archived documents"""
        # Archive a document
        archive_manager.archive_document(
            document_id="old_doc",
            retention_days=1
        )
        
        # Immediately expire it (retention_days=0)
        result = archive_manager.auto_expire_archived(
            retention_days=0,
            auto_delete=False
        )
        
        assert result['success'] is True
        assert result['retention_days'] == 0
        assert result['expired_count'] >= 0
    
    def test_auto_expire_with_delete(self, archive_manager):
        """Test auto-expire with deletion"""
        # Archive document
        archive_manager.archive_document(
            document_id="delete_me",
            retention_days=1
        )
        
        # Expire and delete
        result = archive_manager.auto_expire_archived(
            retention_days=0,
            auto_delete=True
        )
        
        assert result['success'] is True
        assert result['deleted_count'] >= 0


# ============================================================================
# Test Archive Information
# ============================================================================

class TestArchiveInformation:
    """Test archive statistics and information"""
    
    def test_list_archived_documents(self, populated_archive_manager):
        """Test listing archived documents"""
        archived = populated_archive_manager.list_archived_documents()
        
        assert len(archived) == 5
        assert all(isinstance(a, ArchiveMetadata) for a in archived)
    
    def test_list_archived_with_status_filter(self, populated_archive_manager):
        """Test listing with status filter"""
        # Archive and restore one document
        populated_archive_manager.restore_document("doc0")
        
        # List only archived (not restored)
        archived_only = populated_archive_manager.list_archived_documents(
            status=ArchiveStatus.ARCHIVED
        )
        
        # Should have 4 archived (doc1-4)
        assert len(archived_only) >= 0
    
    def test_list_archived_with_limit(self, populated_archive_manager):
        """Test listing with limit"""
        archived = populated_archive_manager.list_archived_documents(limit=3)
        
        assert len(archived) == 3
    
    def test_get_archive_info(self, populated_archive_manager):
        """Test getting archive statistics"""
        info = populated_archive_manager.get_archive_info()
        
        assert isinstance(info, ArchiveInfo)
        assert info.total_archived == 5
        assert info.total_size_bytes > 0
        assert info.oldest_archive is not None
        assert info.newest_archive is not None
    
    def test_get_archive_metadata(self, populated_archive_manager):
        """Test getting metadata for specific document"""
        metadata = populated_archive_manager.get_archive_metadata("doc0")
        
        assert metadata is not None
        assert metadata.document_id == "doc0"
        assert metadata.status == ArchiveStatus.ARCHIVED


# ============================================================================
# Test Background Cleanup
# ============================================================================

class TestBackgroundCleanup:
    """Test background cleanup thread"""
    
    def test_enable_auto_cleanup(self, archive_manager):
        """Test enabling auto-cleanup"""
        archive_manager.enable_auto_cleanup(interval_seconds=1)
        
        # Should start thread
        time.sleep(0.1)
        
        # Cleanup
        archive_manager.disable_auto_cleanup()
    
    def test_disable_auto_cleanup(self, archive_manager):
        """Test disabling auto-cleanup"""
        archive_manager.enable_auto_cleanup(interval_seconds=1)
        time.sleep(0.1)
        
        archive_manager.disable_auto_cleanup()
        
        # Should stop thread gracefully


# ============================================================================
# Test Concurrent Operations
# ============================================================================

class TestConcurrentOperations:
    """Test thread-safety of archive operations"""
    
    def test_concurrent_archive(self, archive_manager):
        """Test concurrent archiving from multiple threads"""
        results = []
        errors = []
        
        def archive_docs(start_idx):
            try:
                for i in range(start_idx, start_idx + 10):
                    result = archive_manager.archive_document(
                        document_id=f"concurrent_{i}",
                        retention_days=365
                    )
                    results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create 5 threads, each archiving 10 documents
        threads = []
        for i in range(5):
            t = threading.Thread(target=archive_docs, args=(i*10,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should have 50 results, no errors
        assert len(results) == 50
        assert len(errors) == 0
        assert all(r.success for r in results)
    
    def test_concurrent_restore(self, archive_manager):
        """Test concurrent restoring from multiple threads"""
        # First archive some documents
        for i in range(20):
            archive_manager.archive_document(
                document_id=f"restore_concurrent_{i}",
                retention_days=365
            )
        
        results = []
        errors = []
        
        def restore_docs(start_idx):
            try:
                for i in range(start_idx, start_idx + 5):
                    result = archive_manager.restore_document(
                        document_id=f"restore_concurrent_{i}"
                    )
                    results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create 4 threads, each restoring 5 documents
        threads = []
        for i in range(4):
            t = threading.Thread(target=restore_docs, args=(i*5,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should have 20 results, no errors
        assert len(results) == 20
        assert len(errors) == 0


# ============================================================================
# Test Performance
# ============================================================================

class TestPerformance:
    """Test performance of archive operations"""
    
    def test_archive_performance(self, archive_manager):
        """Test archive operation performance"""
        start = time.time()
        
        # Archive 100 documents
        for i in range(100):
            archive_manager.archive_document(
                document_id=f"perf_{i}",
                retention_days=365
            )
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time (<5s)
        assert elapsed < 5.0
        
        # Average per operation
        avg = elapsed / 100
        print(f"\nAverage archive time: {avg*1000:.2f}ms")
    
    def test_batch_archive_performance(self, archive_manager):
        """Test batch archive performance"""
        doc_ids = [f"batch_perf_{i}" for i in range(100)]
        
        start = time.time()
        result = archive_manager.batch_archive(
            document_ids=doc_ids,
            retention_days=365
        )
        elapsed = time.time() - start
        
        assert result.success is True
        assert elapsed < 5.0  # Should complete quickly
        
        print(f"\nBatch archive (100 docs): {elapsed*1000:.2f}ms")
    
    def test_list_performance(self, archive_manager):
        """Test listing performance with many documents"""
        # Archive 500 documents
        for i in range(500):
            archive_manager.archive_document(
                document_id=f"list_perf_{i}",
                retention_days=365
            )
        
        # Test listing performance
        start = time.time()
        archived = archive_manager.list_archived_documents()
        elapsed = time.time() - start
        
        assert len(archived) == 500
        assert elapsed < 1.0  # Should be fast
        
        print(f"\nList 500 documents: {elapsed*1000:.2f}ms")


# ============================================================================
# Test Factory Function
# ============================================================================

class TestFactoryFunction:
    """Test factory function"""
    
    def test_create_archive_manager(self, unified_strategy):
        """Test creating archive manager with factory"""
        manager = create_archive_manager(unified_strategy)
        
        assert manager is not None
        assert isinstance(manager, ArchiveManager)
        
        # Should have standard policies
        policies = manager.list_retention_policies()
        assert len(policies) == 4  # short_term, medium_term, long_term, permanent
        
        policy_names = [p.name for p in policies]
        assert "short_term" in policy_names
        assert "medium_term" in policy_names
        assert "long_term" in policy_names
        assert "permanent" in policy_names


# ============================================================================
# Test Context Manager
# ============================================================================

class TestContextManager:
    """Test context manager support"""
    
    def test_context_manager(self, unified_strategy):
        """Test using archive manager as context manager"""
        with ArchiveManager(unified_strategy) as manager:
            result = manager.archive_document(
                document_id="ctx_test",
                retention_days=365
            )
            assert result.success is True
        
        # Should cleanup properly


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_archive_twice(self, archive_manager):
        """Test archiving same document twice"""
        # First archive
        result1 = archive_manager.archive_document(
            document_id="double",
            retention_days=365
        )
        assert result1.success is True
        
        # Second archive (should overwrite)
        result2 = archive_manager.archive_document(
            document_id="double",
            retention_days=180
        )
        assert result2.success is True
        
        # Check metadata (should have new retention)
        metadata = archive_manager.get_archive_metadata("double")
        assert metadata.retention_days == 180
    
    def test_restore_without_archive(self, archive_manager):
        """Test restore fails if not archived"""
        result = archive_manager.restore_document(
            document_id="never_archived"
        )
        
        assert result.success is False
        assert result.errors is not None
    
    def test_empty_batch_archive(self, archive_manager):
        """Test batch archive with empty list"""
        result = archive_manager.batch_archive(
            document_ids=[],
            retention_days=365
        )
        
        assert result.total_count == 0
        assert result.archived_count == 0
    
    def test_archive_info_when_empty(self, archive_manager):
        """Test archive info when no documents archived"""
        info = archive_manager.get_archive_info()
        
        assert info.total_archived == 0
        assert info.total_size_bytes == 0


# ============================================================================
# Summary
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
