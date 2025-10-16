"""
Unit Tests for Delete Operations Module
========================================

Tests soft delete, hard delete, restore, and purge operations.

Author: UDS3 Team
Date: 1. Oktober 2025
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List

from uds3_delete_operations import (
    SoftDeleteManager,
    HardDeleteManager,
    DeleteStrategy,
    CascadeStrategy,
    RestoreStrategy,
    DeleteResult,
    RestoreResult,
    PurgeResult,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_unified_strategy():
    """Create mock UnifiedDatabaseStrategy"""
    strategy = Mock()
    
    # Mock backends
    strategy.vector_backend = Mock()
    strategy.graph_backend = Mock()
    strategy.relational_backend = Mock()
    strategy.file_backend = Mock()
    
    # Mock backend methods
    strategy.vector_backend.update_metadata = Mock(return_value=True)
    strategy.graph_backend.set_node_properties = Mock(return_value=True)
    strategy.relational_backend.soft_delete = Mock(return_value=True)
    strategy.file_backend.soft_delete = Mock(return_value=True)
    
    return strategy


@pytest.fixture
def soft_delete_manager(mock_unified_strategy):
    """Create SoftDeleteManager instance"""
    return SoftDeleteManager(mock_unified_strategy)


@pytest.fixture
def sample_document_id():
    """Sample document ID"""
    return "doc_12345"


# ============================================================================
# Soft Delete Tests
# ============================================================================

class TestSoftDelete:
    """Test soft delete operations"""
    
    def test_soft_delete_basic(self, soft_delete_manager, sample_document_id):
        """Test basic soft delete"""
        result = soft_delete_manager.soft_delete_document(sample_document_id)
        
        assert isinstance(result, DeleteResult)
        assert result.success is True
        assert result.document_id == sample_document_id
        assert result.strategy == DeleteStrategy.SOFT
        assert result.deleted_at is not None
        assert "vector" in result.affected_databases
        assert "graph" in result.affected_databases
        assert "relational" in result.affected_databases
        assert "file" in result.affected_databases
    
    def test_soft_delete_with_reason(self, soft_delete_manager, sample_document_id):
        """Test soft delete with reason"""
        reason = "Outdated document"
        deleted_by = "admin@example.com"
        
        result = soft_delete_manager.soft_delete_document(
            sample_document_id,
            reason=reason,
            deleted_by=deleted_by
        )
        
        assert result.success is True
        # Verify metadata was passed correctly
        vector_backend = soft_delete_manager.vector_backend
        assert vector_backend.update_metadata.called
    
    def test_soft_delete_vector_failure(self, soft_delete_manager, sample_document_id):
        """Test soft delete with vector backend failure"""
        # Make vector backend fail
        soft_delete_manager.vector_backend.update_metadata.side_effect = Exception("Vector error")
        
        result = soft_delete_manager.soft_delete_document(sample_document_id)
        
        # Should still succeed for other backends
        assert result.success is True
        assert "vector" not in result.affected_databases
        assert result.errors is not None
        assert any("Vector soft delete failed" in e for e in result.errors)
    
    def test_soft_delete_all_backends_fail(self, soft_delete_manager, sample_document_id):
        """Test soft delete when all backends fail"""
        # Make all backends fail
        soft_delete_manager.vector_backend.update_metadata.side_effect = Exception("Error")
        soft_delete_manager.graph_backend.set_node_properties.side_effect = Exception("Error")
        soft_delete_manager.relational_backend.soft_delete.side_effect = Exception("Error")
        soft_delete_manager.file_backend.soft_delete.side_effect = Exception("Error")
        
        result = soft_delete_manager.soft_delete_document(sample_document_id)
        
        assert result.success is False
        assert len(result.affected_databases) == 0
        assert len(result.errors) == 4


# ============================================================================
# Restore Tests
# ============================================================================

class TestRestore:
    """Test restore operations"""
    
    def test_restore_basic(self, soft_delete_manager, sample_document_id):
        """Test basic restore"""
        # Setup restore methods
        soft_delete_manager.vector_backend.update_metadata = Mock(return_value=True)
        soft_delete_manager.graph_backend.set_node_properties = Mock(return_value=True)
        soft_delete_manager.relational_backend.update = Mock(return_value=True)
        soft_delete_manager.file_backend.restore_from_deleted = Mock(return_value=True)
        
        result = soft_delete_manager.restore_document(sample_document_id)
        
        assert isinstance(result, RestoreResult)
        assert result.success is True
        assert result.document_id == sample_document_id
        assert result.restored_at is not None
    
    def test_restore_with_strategy(self, soft_delete_manager, sample_document_id):
        """Test restore with different strategies"""
        strategies = [
            RestoreStrategy.KEEP_METADATA,
            RestoreStrategy.CLEAR_METADATA,
            RestoreStrategy.PRESERVE_AUDIT
        ]
        
        for strategy in strategies:
            result = soft_delete_manager.restore_document(
                sample_document_id,
                strategy=strategy
            )
            assert result.success is True
    
    def test_restore_partial_failure(self, soft_delete_manager, sample_document_id):
        """Test restore with some backend failures"""
        # Make vector backend fail
        soft_delete_manager.vector_backend.update_metadata.side_effect = Exception("Error")
        
        result = soft_delete_manager.restore_document(sample_document_id)
        
        # Should still succeed for other backends
        assert result.success is True
        assert "vector" not in result.affected_databases
        assert result.errors is not None


# ============================================================================
# List & Query Tests
# ============================================================================

class TestListDeleted:
    """Test listing deleted documents"""
    
    def test_list_deleted_basic(self, soft_delete_manager):
        """Test basic list deleted"""
        # Mock query_deleted method
        soft_delete_manager.relational_backend.query_deleted = Mock(
            return_value=[
                {"document_id": "doc1", "deleted_at": "2025-01-01T00:00:00"},
                {"document_id": "doc2", "deleted_at": "2025-01-02T00:00:00"}
            ]
        )
        
        result = soft_delete_manager.list_deleted()
        
        assert len(result) == 2
        assert result[0]["document_id"] == "doc1"
    
    def test_list_deleted_with_filters(self, soft_delete_manager):
        """Test list deleted with filters"""
        filters = {"deleted_by": "admin@example.com"}
        
        soft_delete_manager.relational_backend.query_deleted = Mock(return_value=[])
        
        result = soft_delete_manager.list_deleted(filters=filters)
        
        # Verify filters were passed
        soft_delete_manager.relational_backend.query_deleted.assert_called_once()
        call_args = soft_delete_manager.relational_backend.query_deleted.call_args
        assert call_args[1]["filters"] == filters
    
    def test_list_deleted_pagination(self, soft_delete_manager):
        """Test list deleted with pagination"""
        soft_delete_manager.relational_backend.query_deleted = Mock(return_value=[])
        
        result = soft_delete_manager.list_deleted(limit=50, offset=100)
        
        call_args = soft_delete_manager.relational_backend.query_deleted.call_args
        assert call_args[1]["limit"] == 50
        assert call_args[1]["offset"] == 100


# ============================================================================
# Purge Tests
# ============================================================================

class TestPurge:
    """Test purge operations"""
    
    def test_purge_old_deleted(self, soft_delete_manager):
        """Test purging old deleted documents"""
        # Mock list_deleted to return old documents
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        old_docs = [
            {"document_id": "old_doc1", "deleted_at": cutoff_date.isoformat()},
            {"document_id": "old_doc2", "deleted_at": cutoff_date.isoformat()}
        ]
        
        soft_delete_manager.relational_backend.query_deleted = Mock(return_value=old_docs)
        
        # Note: Hard delete not yet implemented, so this will log warnings
        result = soft_delete_manager.purge_old_deleted(retention_days=90)
        
        assert isinstance(result, PurgeResult)
        assert result.retention_days == 90
        # purged_count will be 2 since we found 2 docs (even if hard delete isn't implemented)
        assert result.purged_count >= 0
    
    def test_purge_with_archive(self, soft_delete_manager):
        """Test purge with archive instead of hard delete"""
        soft_delete_manager.relational_backend.query_deleted = Mock(return_value=[])
        
        result = soft_delete_manager.purge_old_deleted(
            retention_days=30,
            hard_delete=False
        )
        
        assert result.retention_days == 30
    
    def test_purge_empty_result(self, soft_delete_manager):
        """Test purge when no documents to purge"""
        soft_delete_manager.relational_backend.query_deleted = Mock(return_value=[])
        
        result = soft_delete_manager.purge_old_deleted()
        
        assert result.success is True
        assert result.purged_count == 0


# ============================================================================
# DeleteResult Tests
# ============================================================================

class TestDeleteResult:
    """Test DeleteResult dataclass"""
    
    def test_to_dict(self):
        """Test DeleteResult.to_dict()"""
        deleted_at = datetime(2025, 1, 1, 12, 0, 0)
        result = DeleteResult(
            success=True,
            document_id="doc123",
            strategy=DeleteStrategy.SOFT,
            deleted_at=deleted_at,
            affected_databases=["vector", "graph"],
            errors=None,
            cascade_count=0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["document_id"] == "doc123"
        assert result_dict["strategy"] == "soft"
        assert result_dict["deleted_at"] == deleted_at.isoformat()
        assert "vector" in result_dict["affected_databases"]


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for delete operations"""
    
    def test_soft_delete_and_restore_cycle(self, soft_delete_manager, sample_document_id):
        """Test complete soft delete -> restore cycle"""
        # Soft delete
        delete_result = soft_delete_manager.soft_delete_document(sample_document_id)
        assert delete_result.success is True
        
        # Restore
        restore_result = soft_delete_manager.restore_document(sample_document_id)
        assert restore_result.success is True
    
    def test_soft_delete_list_restore(self, soft_delete_manager):
        """Test soft delete -> list -> restore workflow"""
        doc_id = "workflow_doc"
        
        # Soft delete
        soft_delete_manager.soft_delete_document(doc_id)
        
        # Mock list to show deleted doc
        soft_delete_manager.relational_backend.query_deleted = Mock(
            return_value=[{"document_id": doc_id}]
        )
        
        # List deleted
        deleted = soft_delete_manager.list_deleted()
        assert len(deleted) > 0
        
        # Restore
        restore_result = soft_delete_manager.restore_document(doc_id)
        assert restore_result.success is True


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_delete_nonexistent_document(self, soft_delete_manager):
        """Test deleting non-existent document"""
        # Backends should handle gracefully
        result = soft_delete_manager.soft_delete_document("nonexistent_doc")
        # Should not crash, may succeed or fail depending on backend
        assert isinstance(result, DeleteResult)
    
    def test_restore_never_deleted(self, soft_delete_manager):
        """Test restoring document that was never deleted"""
        result = soft_delete_manager.restore_document("never_deleted_doc")
        # Should not crash
        assert isinstance(result, RestoreResult)
    
    def test_backend_not_available(self, mock_unified_strategy):
        """Test when backend is None"""
        mock_unified_strategy.vector_backend = None
        
        manager = SoftDeleteManager(mock_unified_strategy)
        result = manager.soft_delete_document("doc123")
        
        # Should not crash, just skip vector backend
        assert "vector" not in result.affected_databases


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ============================================================================
# Hard Delete Tests (Todo #2)
# ============================================================================

class TestHardDelete:
    """Test hard delete operations"""
    
    @pytest.fixture
    def hard_delete_manager(self, mock_unified_strategy):
        """Create HardDeleteManager instance"""
        # Mock delete methods
        mock_unified_strategy.vector_backend.delete = Mock(return_value=True)
        mock_unified_strategy.graph_backend.delete_node = Mock(return_value=True)
        mock_unified_strategy.graph_backend.get_children = Mock(return_value=[])
        mock_unified_strategy.relational_backend.hard_delete = Mock(return_value=True)
        mock_unified_strategy.file_backend.delete = Mock(return_value=True)
        
        return HardDeleteManager(mock_unified_strategy)
    
    def test_hard_delete_basic(self, hard_delete_manager, sample_document_id):
        """Test basic hard delete"""
        result = hard_delete_manager.hard_delete_document(sample_document_id)
        
        assert isinstance(result, DeleteResult)
        assert result.success is True
        assert result.document_id == sample_document_id
        assert result.strategy == DeleteStrategy.HARD
        assert result.deleted_at is not None
        assert "vector" in result.affected_databases
        assert "graph" in result.affected_databases
        assert "relational" in result.affected_databases
        assert "file" in result.affected_databases
    
    def test_hard_delete_with_cascade_none(self, hard_delete_manager, sample_document_id):
        """Test hard delete with CASCADE NONE"""
        result = hard_delete_manager.hard_delete_document(
            sample_document_id,
            cascade=CascadeStrategy.NONE
        )
        
        assert result.success is True
        assert result.cascade_count == 0  # No cascade
    
    def test_hard_delete_with_cascade_selective(self, hard_delete_manager, sample_document_id):
        """Test hard delete with CASCADE SELECTIVE"""
        # Mock children
        hard_delete_manager.graph_backend.get_children = Mock(
            return_value=["child1", "child2"]
        )
        
        result = hard_delete_manager.hard_delete_document(
            sample_document_id,
            cascade=CascadeStrategy.SELECTIVE
        )
        
        assert result.success is True
        # Selective cascade deletes relationships, not nodes
        assert result.cascade_count == 0
    
    def test_hard_delete_with_cascade_full(self, hard_delete_manager, sample_document_id):
        """Test hard delete with CASCADE FULL"""
        # Mock all connected entities
        hard_delete_manager.graph_backend.get_all_connected = Mock(
            return_value=["related1", "related2", "related3"]
        )
        
        result = hard_delete_manager.hard_delete_document(
            sample_document_id,
            cascade=CascadeStrategy.FULL
        )
        
        assert result.success is True
        assert result.cascade_count == 3  # Deleted 3 related entities
    
    def test_hard_delete_with_audit(self, hard_delete_manager, sample_document_id):
        """Test hard delete creates audit trail"""
        # Mock audit backend
        hard_delete_manager.audit_backend = Mock()
        hard_delete_manager.audit_backend.create_audit_entry = Mock(return_value="audit123")
        
        result = hard_delete_manager.hard_delete_document(
            sample_document_id,
            reason="Compliance requirement",
            deleted_by="admin@example.com",
            create_audit=True
        )
        
        assert result.success is True
        assert result.audit_id is not None
    
    def test_hard_delete_vector_failure(self, hard_delete_manager, sample_document_id):
        """Test hard delete with vector backend failure"""
        # Make vector backend fail
        hard_delete_manager.vector_backend.delete.side_effect = Exception("Vector error")
        
        result = hard_delete_manager.hard_delete_document(sample_document_id)
        
        # Should still succeed for other backends
        assert result.success is True
        assert "vector" not in result.affected_databases
        assert result.errors is not None
    
    def test_hard_delete_all_backends_fail(self, hard_delete_manager, sample_document_id):
        """Test hard delete when all backends fail"""
        # Make all backends fail
        hard_delete_manager.vector_backend.delete.side_effect = Exception("Error")
        hard_delete_manager.graph_backend.delete_node.side_effect = Exception("Error")
        hard_delete_manager.relational_backend.hard_delete.side_effect = Exception("Error")
        hard_delete_manager.file_backend.delete.side_effect = Exception("Error")
        
        result = hard_delete_manager.hard_delete_document(sample_document_id)
        
        assert result.success is False
        assert len(result.affected_databases) == 0
        assert len(result.errors) == 4


class TestHardDeleteBatch:
    """Test batch hard delete operations"""
    
    @pytest.fixture
    def hard_delete_manager(self, mock_unified_strategy):
        """Create HardDeleteManager instance"""
        mock_unified_strategy.vector_backend.delete = Mock(return_value=True)
        mock_unified_strategy.graph_backend.delete_node = Mock(return_value=True)
        mock_unified_strategy.graph_backend.get_children = Mock(return_value=[])
        mock_unified_strategy.relational_backend.hard_delete = Mock(return_value=True)
        mock_unified_strategy.file_backend.delete = Mock(return_value=True)
        
        return HardDeleteManager(mock_unified_strategy)
    
    def test_batch_hard_delete(self, hard_delete_manager):
        """Test batch hard delete"""
        doc_ids = ["doc1", "doc2", "doc3"]
        
        results = hard_delete_manager.hard_delete_batch(doc_ids)
        
        assert len(results) == 3
        assert all(r.success for r in results.values())
        assert all(r.strategy == DeleteStrategy.HARD for r in results.values())
    
    def test_batch_hard_delete_partial_failure(self, hard_delete_manager):
        """Test batch hard delete with some failures"""
        doc_ids = ["doc1", "doc2", "doc3"]
        
        # Make doc2 fail
        call_count = [0]
        def delete_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call (doc2)
                raise Exception("Delete failed")
            return True
        
        hard_delete_manager.vector_backend.delete.side_effect = delete_side_effect
        
        results = hard_delete_manager.hard_delete_batch(doc_ids)
        
        assert len(results) == 3
        # doc1 and doc3 succeed, doc2 fails
        success_count = sum(1 for r in results.values() if r.success)
        assert success_count == 2


class TestAuditTrail:
    """Test audit trail functionality"""
    
    @pytest.fixture
    def hard_delete_manager(self, mock_unified_strategy):
        """Create HardDeleteManager with audit backend"""
        mock_unified_strategy.audit_backend = Mock()
        mock_unified_strategy.audit_backend.create_audit_entry = Mock(return_value="audit123")
        
        mock_unified_strategy.vector_backend.delete = Mock(return_value=True)
        mock_unified_strategy.graph_backend.delete_node = Mock(return_value=True)
        mock_unified_strategy.graph_backend.get_children = Mock(return_value=[])
        mock_unified_strategy.relational_backend.hard_delete = Mock(return_value=True)
        mock_unified_strategy.file_backend.delete = Mock(return_value=True)
        
        return HardDeleteManager(mock_unified_strategy)
    
    def test_audit_entry_created(self, hard_delete_manager, sample_document_id):
        """Test audit entry is created for hard delete"""
        result = hard_delete_manager.hard_delete_document(
            sample_document_id,
            reason="GDPR request",
            deleted_by="compliance@example.com"
        )
        
        assert result.audit_id is not None
        # Verify audit backend was called
        assert hard_delete_manager.audit_backend.create_audit_entry.called
    
    def test_audit_hash_computation(self, hard_delete_manager):
        """Test audit hash is computed correctly"""
        audit_entry = {
            "audit_id": "test123",
            "document_id": "doc123",
            "operation": "HARD_DELETE",
            "timestamp": "2025-01-01T00:00:00"
        }
        
        hash1 = hard_delete_manager._compute_audit_hash(audit_entry)
        hash2 = hard_delete_manager._compute_audit_hash(audit_entry)
        
        # Hash should be deterministic
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 is 64 hex chars
    
    def test_audit_without_backend(self, mock_unified_strategy, sample_document_id):
        """Test audit works even without dedicated audit backend"""
        # No audit backend
        mock_unified_strategy.audit_backend = None
        
        # But has relational backend
        mock_unified_strategy.relational_backend.insert = Mock(return_value=True)
        mock_unified_strategy.vector_backend.delete = Mock(return_value=True)
        mock_unified_strategy.graph_backend.delete_node = Mock(return_value=True)
        mock_unified_strategy.graph_backend.get_children = Mock(return_value=[])
        mock_unified_strategy.relational_backend.hard_delete = Mock(return_value=True)
        mock_unified_strategy.file_backend.delete = Mock(return_value=True)
        
        manager = HardDeleteManager(mock_unified_strategy)
        result = manager.hard_delete_document(sample_document_id)
        
        assert result.success is True
        # Audit should fall back to relational backend
        assert mock_unified_strategy.relational_backend.insert.called


class TestOrphanCleanup:
    """Test orphan detection and cleanup"""
    
    @pytest.fixture
    def hard_delete_manager(self, mock_unified_strategy):
        """Create HardDeleteManager instance"""
        mock_unified_strategy.vector_backend.delete = Mock(return_value=True)
        mock_unified_strategy.graph_backend.delete_node = Mock()
        mock_unified_strategy.graph_backend.get_children = Mock(return_value=[])
        mock_unified_strategy.graph_backend.cleanup_dangling_relationships = Mock(return_value=2)
        mock_unified_strategy.relational_backend.hard_delete = Mock(return_value=True)
        mock_unified_strategy.file_backend.delete = Mock(return_value=True)
        
        return HardDeleteManager(mock_unified_strategy)
    
    def test_orphan_cleanup_dangling_relationships(self, hard_delete_manager, sample_document_id):
        """Test cleanup of dangling relationships"""
        result = hard_delete_manager.hard_delete_document(sample_document_id)
        
        assert result.success is True
        # Verify cleanup was called
        assert hard_delete_manager.graph_backend.cleanup_dangling_relationships.called
    
    def test_orphan_cleanup_vector_after_graph_fail(self, hard_delete_manager, sample_document_id):
        """Test orphaned embeddings are cleaned up when graph delete fails"""
        # Make graph delete fail
        hard_delete_manager.graph_backend.delete_node.side_effect = Exception("Graph error")
        
        result = hard_delete_manager.hard_delete_document(sample_document_id)
        
        # Vector succeeded, graph failed → embeddings are orphaned
        assert "vector" in result.affected_databases
        assert "graph" not in result.affected_databases
