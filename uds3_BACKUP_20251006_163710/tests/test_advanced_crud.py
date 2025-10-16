"""
Unit Tests für UDS3 Advanced CRUD Operations

Testet:
- Batch Read Operations
- Conditional Update Operations
- Upsert Operations
- Batch Update Operations
- Edge Cases & Error Handling

Autor: UDS3 Team
Datum: 1. Oktober 2025
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch

from uds3_advanced_crud import (
    AdvancedCRUDManager,
    BatchReadResult,
    ConditionalUpdateResult,
    UpsertResult,
    Condition,
    ConditionOperator,
    MergeStrategy,
    ReadStrategy,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_backend():
    """Mock UDS3CoreOrchestrator Backend"""
    backend = Mock()
    
    # Mock read_document_operation
    def mock_read(doc_id, include_content=True, include_relationships=False):
        if doc_id == "existing_doc":
            return {
                "document_id": doc_id,
                "title": "Test Document",
                "version": 5,
                "status": "active",
                "priority": 10
            }
        elif doc_id == "error_doc":
            raise Exception("Read error")
        else:
            raise Exception(f"Document {doc_id} not found")
    
    backend.read_document_operation = Mock(side_effect=mock_read)
    
    # Mock update_secure_document
    def mock_update(doc_id, updates):
        return {
            "success": True,
            "document_id": doc_id,
            "database_operations": {
                "vector": {"status": "success"},
                "graph": {"status": "success"},
                "relational": {"status": "success"}
            },
            "issues": []
        }
    
    backend.update_secure_document = Mock(side_effect=mock_update)
    
    # Mock ingest_document_polyglot
    def mock_ingest(doc_id, data):
        return {
            "success": True,
            "document_id": doc_id,
            "database_operations": {
                "vector": {"status": "success"},
                "graph": {"status": "success"},
                "relational": {"status": "success"},
                "file": {"status": "success"}
            },
            "issues": []
        }
    
    backend.ingest_document_polyglot = Mock(side_effect=mock_ingest)
    
    return backend


@pytest.fixture
def crud_manager(mock_backend):
    """AdvancedCRUDManager Instance"""
    return AdvancedCRUDManager(mock_backend)


# ============================================================================
# TEST CONDITION CLASS
# ============================================================================


class TestCondition:
    """Tests für Condition class"""
    
    def test_create_condition(self):
        """Test Condition erstellen"""
        cond = Condition(
            field="status",
            operator=ConditionOperator.EQ,
            value="active"
        )
        
        assert cond.field == "status"
        assert cond.operator == ConditionOperator.EQ
        assert cond.value == "active"
    
    def test_condition_equality(self):
        """Test EQ operator"""
        cond = Condition("status", ConditionOperator.EQ, "active")
        
        assert cond.evaluate({"status": "active"}) is True
        assert cond.evaluate({"status": "inactive"}) is False
        assert cond.evaluate({}) is False
    
    def test_condition_not_equal(self):
        """Test NE operator"""
        cond = Condition("status", ConditionOperator.NE, "deleted")
        
        assert cond.evaluate({"status": "active"}) is True
        assert cond.evaluate({"status": "deleted"}) is False
    
    def test_condition_greater_than(self):
        """Test GT operator"""
        cond = Condition("priority", ConditionOperator.GT, 5)
        
        assert cond.evaluate({"priority": 10}) is True
        assert cond.evaluate({"priority": 5}) is False
        assert cond.evaluate({"priority": 3}) is False
    
    def test_condition_less_than(self):
        """Test LT operator"""
        cond = Condition("priority", ConditionOperator.LT, 10)
        
        assert cond.evaluate({"priority": 5}) is True
        assert cond.evaluate({"priority": 10}) is False
        assert cond.evaluate({"priority": 15}) is False
    
    def test_condition_gte(self):
        """Test GTE operator"""
        cond = Condition("priority", ConditionOperator.GTE, 5)
        
        assert cond.evaluate({"priority": 5}) is True
        assert cond.evaluate({"priority": 10}) is True
        assert cond.evaluate({"priority": 3}) is False
    
    def test_condition_lte(self):
        """Test LTE operator"""
        cond = Condition("priority", ConditionOperator.LTE, 10)
        
        assert cond.evaluate({"priority": 10}) is True
        assert cond.evaluate({"priority": 5}) is True
        assert cond.evaluate({"priority": 15}) is False
    
    def test_condition_exists(self):
        """Test EXISTS operator"""
        cond = Condition("metadata", ConditionOperator.EXISTS)
        
        assert cond.evaluate({"metadata": {}}) is True
        assert cond.evaluate({"metadata": None}) is True
        assert cond.evaluate({}) is False
    
    def test_condition_not_exists(self):
        """Test NOT_EXISTS operator"""
        cond = Condition("deleted_at", ConditionOperator.NOT_EXISTS)
        
        assert cond.evaluate({}) is True
        assert cond.evaluate({"status": "active"}) is True
        assert cond.evaluate({"deleted_at": "2025-01-01"}) is False
    
    def test_condition_to_dict(self):
        """Test Condition.to_dict()"""
        cond = Condition("status", ConditionOperator.EQ, "active")
        
        result = cond.to_dict()
        
        assert result["field"] == "status"
        assert result["operator"] == "=="
        assert result["value"] == "active"


# ============================================================================
# TEST BATCH READ
# ============================================================================


class TestBatchRead:
    """Tests für Batch Read Operations"""
    
    def test_batch_read_empty_list(self, crud_manager):
        """Test batch read mit leerer Liste"""
        result = crud_manager.batch_read_documents([])
        
        assert result.success is True
        assert result.total_requested == 0
        assert result.total_read == 0
        assert len(result.documents) == 0
        assert len(result.errors) == 0
    
    def test_batch_read_single_document(self, crud_manager):
        """Test batch read mit einem Dokument"""
        result = crud_manager.batch_read_documents(
            ["existing_doc"],
            strategy=ReadStrategy.SEQUENTIAL
        )
        
        assert result.success is True
        assert result.total_requested == 1
        assert result.total_read == 1
        assert "existing_doc" in result.documents
        assert len(result.errors) == 0
        assert result.success_rate == 100.0
    
    def test_batch_read_multiple_documents_parallel(self, crud_manager):
        """Test batch read parallel"""
        result = crud_manager.batch_read_documents(
            ["existing_doc", "existing_doc"],
            strategy=ReadStrategy.PARALLEL,
            max_workers=2
        )
        
        assert result.total_requested == 2
        # Note: Duplicate IDs result in single document (dict key overwrite)
        assert result.total_read == 1
        assert result.strategy == ReadStrategy.PARALLEL
    
    def test_batch_read_multiple_documents_sequential(self, crud_manager):
        """Test batch read sequential"""
        result = crud_manager.batch_read_documents(
            ["existing_doc", "existing_doc"],
            strategy=ReadStrategy.SEQUENTIAL
        )
        
        assert result.total_requested == 2
        # Note: Duplicate IDs result in single document (dict key overwrite)
        assert result.total_read == 1
        assert result.strategy == ReadStrategy.SEQUENTIAL
    
    def test_batch_read_with_errors(self, crud_manager):
        """Test batch read mit Fehlern"""
        result = crud_manager.batch_read_documents(
            ["existing_doc", "nonexistent_doc", "error_doc"],
            strategy=ReadStrategy.SEQUENTIAL
        )
        
        assert result.success is False
        assert result.total_requested == 3
        assert result.total_read == 1
        assert len(result.errors) == 2
        assert "nonexistent_doc" in result.errors
        assert "error_doc" in result.errors
        assert result.success_rate < 100.0
    
    def test_batch_read_partial_success(self, crud_manager):
        """Test batch read mit partial success"""
        result = crud_manager.batch_read_documents(
            ["existing_doc", "nonexistent_doc"],
            strategy=ReadStrategy.PARALLEL
        )
        
        assert result.success is False
        assert result.total_read == 1
        assert len(result.errors) == 1
        assert result.success_rate == 50.0
    
    def test_batch_read_with_content_options(self, crud_manager):
        """Test batch read mit include_content/relationships"""
        result = crud_manager.batch_read_documents(
            ["existing_doc"],
            include_content=True,
            include_relationships=True
        )
        
        assert result.success is True
        assert result.total_read == 1
    
    def test_batch_read_priority_strategy(self, crud_manager):
        """Test batch read mit PRIORITY strategy"""
        result = crud_manager.batch_read_documents(
            ["existing_doc", "existing_doc"],
            strategy=ReadStrategy.PRIORITY
        )
        
        # PRIORITY sollte auf PARALLEL zurückfallen
        # Note: Duplicate IDs result in single document
        assert result.total_read == 1
    
    def test_batch_read_result_to_dict(self, crud_manager):
        """Test BatchReadResult.to_dict()"""
        result = crud_manager.batch_read_documents(["existing_doc"])
        
        result_dict = result.to_dict()
        
        assert "success" in result_dict
        assert "total_requested" in result_dict
        assert "total_read" in result_dict
        assert "documents" in result_dict
        assert "errors" in result_dict
        assert "success_rate" in result_dict
    
    def test_batch_read_execution_time(self, crud_manager):
        """Test execution time tracking"""
        result = crud_manager.batch_read_documents(["existing_doc"])
        
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0


# ============================================================================
# TEST CONDITIONAL UPDATE
# ============================================================================


class TestConditionalUpdate:
    """Tests für Conditional Update Operations"""
    
    def test_conditional_update_basic(self, crud_manager):
        """Test basic conditional update"""
        conditions = [
            Condition("status", ConditionOperator.EQ, "active")
        ]
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            conditions
        )
        
        assert result.success is True
        assert result.updated is True
        assert result.condition_met is True
        assert result.version_before == 5
        assert result.version_after == 6
    
    def test_conditional_update_condition_not_met(self, crud_manager):
        """Test conditional update wenn condition nicht erfüllt"""
        conditions = [
            Condition("status", ConditionOperator.EQ, "inactive")
        ]
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            conditions
        )
        
        assert result.success is False
        assert result.updated is False
        assert result.condition_met is False
        assert result.version_before == 5
        assert result.version_after == 5  # Unchanged
    
    def test_conditional_update_multiple_conditions(self, crud_manager):
        """Test conditional update mit mehreren conditions"""
        conditions = [
            Condition("status", ConditionOperator.EQ, "active"),
            Condition("priority", ConditionOperator.GT, 5)
        ]
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"priority": 15},
            conditions
        )
        
        assert result.success is True
        assert result.condition_met is True
        assert len(result.conditions_evaluated) == 2
    
    def test_conditional_update_version_check(self, crud_manager):
        """Test conditional update mit version check"""
        conditions = []
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            conditions,
            version_check=5
        )
        
        assert result.success is True
        assert result.version_before == 5
        assert result.version_after == 6
    
    def test_conditional_update_version_conflict(self, crud_manager):
        """Test conditional update mit version conflict"""
        conditions = []
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            conditions,
            version_check=3  # Wrong version
        )
        
        assert result.success is False
        assert result.conflict_detected is True
        assert "Version conflict" in result.errors[0]
    
    def test_conditional_update_nonexistent_document(self, crud_manager):
        """Test conditional update für nicht existierendes Dokument"""
        conditions = []
        
        result = crud_manager.conditional_update_document(
            "nonexistent_doc",
            {"status": "completed"},
            conditions
        )
        
        assert result.success is False
        assert result.updated is False
    
    def test_conditional_update_field_exists(self, crud_manager):
        """Test conditional update mit EXISTS condition"""
        conditions = [
            Condition("priority", ConditionOperator.EXISTS)
        ]
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"priority": 20},
            conditions
        )
        
        assert result.success is True
        assert result.condition_met is True
    
    def test_conditional_update_field_not_exists(self, crud_manager):
        """Test conditional update mit NOT_EXISTS condition"""
        conditions = [
            Condition("deleted_at", ConditionOperator.NOT_EXISTS)
        ]
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            conditions
        )
        
        assert result.success is True
        assert result.condition_met is True
    
    def test_conditional_update_affected_databases(self, crud_manager):
        """Test affected_databases tracking"""
        conditions = [
            Condition("status", ConditionOperator.EQ, "active")
        ]
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            conditions
        )
        
        assert len(result.affected_databases) > 0
        assert "vector" in result.affected_databases
        assert "graph" in result.affected_databases
    
    def test_conditional_update_to_dict(self, crud_manager):
        """Test ConditionalUpdateResult.to_dict()"""
        conditions = [Condition("status", ConditionOperator.EQ, "active")]
        
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            conditions
        )
        
        result_dict = result.to_dict()
        
        assert "success" in result_dict
        assert "document_id" in result_dict
        assert "updated" in result_dict
        assert "condition_met" in result_dict
        assert "version_before" in result_dict
        assert "version_after" in result_dict


# ============================================================================
# TEST UPSERT
# ============================================================================


class TestUpsert:
    """Tests für Upsert Operations"""
    
    def test_upsert_create_new_document(self, crud_manager):
        """Test upsert erstellt neues Dokument"""
        result = crud_manager.upsert_document(
            "new_doc",
            {"title": "New Document", "status": "draft"}
        )
        
        assert result.success is True
        assert result.operation == "created"
        assert result.existed_before is False
        assert len(result.created_fields) > 0
        assert len(result.updated_fields) == 0
    
    def test_upsert_update_existing_document_merge(self, crud_manager):
        """Test upsert updated existierendes Dokument (MERGE)"""
        result = crud_manager.upsert_document(
            "existing_doc",
            {"priority": 20, "new_field": "value"},
            merge_strategy=MergeStrategy.MERGE
        )
        
        assert result.success is True
        assert result.operation == "updated"
        assert result.existed_before is True
        assert result.merge_strategy == MergeStrategy.MERGE
        assert len(result.updated_fields) > 0
    
    def test_upsert_update_existing_document_replace(self, crud_manager):
        """Test upsert mit REPLACE strategy"""
        result = crud_manager.upsert_document(
            "existing_doc",
            {"new_data": "only this"},
            merge_strategy=MergeStrategy.REPLACE
        )
        
        assert result.success is True
        assert result.operation == "updated"
        assert result.merge_strategy == MergeStrategy.REPLACE
    
    def test_upsert_update_existing_document_keep(self, crud_manager):
        """Test upsert mit KEEP_EXISTING strategy"""
        result = crud_manager.upsert_document(
            "existing_doc",
            {"priority": 20, "new_field": "value"},
            merge_strategy=MergeStrategy.KEEP_EXISTING
        )
        
        assert result.success is True
        assert result.operation == "updated"
        assert result.merge_strategy == MergeStrategy.KEEP_EXISTING
    
    def test_upsert_create_if_missing_false(self, crud_manager):
        """Test upsert mit create_if_missing=False"""
        result = crud_manager.upsert_document(
            "nonexistent_doc",
            {"title": "Test"},
            create_if_missing=False
        )
        
        assert result.success is False
        assert result.operation == "none"
        assert "create_if_missing=False" in result.errors[0]
    
    def test_upsert_affected_databases(self, crud_manager):
        """Test affected_databases tracking"""
        result = crud_manager.upsert_document(
            "new_doc",
            {"title": "Test"}
        )
        
        assert len(result.affected_databases) > 0
    
    def test_upsert_created_fields_tracking(self, crud_manager):
        """Test created_fields tracking"""
        result = crud_manager.upsert_document(
            "new_doc",
            {"title": "Test", "status": "draft", "priority": 5}
        )
        
        assert "title" in result.created_fields
        assert "status" in result.created_fields
        assert "priority" in result.created_fields
    
    def test_upsert_updated_fields_tracking_merge(self, crud_manager):
        """Test updated_fields tracking bei MERGE"""
        result = crud_manager.upsert_document(
            "existing_doc",
            {"priority": 20},
            merge_strategy=MergeStrategy.MERGE
        )
        
        assert "priority" in result.updated_fields
    
    def test_upsert_error_handling(self, crud_manager):
        """Test upsert error handling"""
        # Save original mock
        original_read = crud_manager.backend.read_document_operation.side_effect
        original_ingest = crud_manager.backend.ingest_document_polyglot.side_effect
        
        # Simulate error on both read AND create
        crud_manager.backend.read_document_operation.side_effect = Exception("Test error")
        crud_manager.backend.ingest_document_polyglot.side_effect = Exception("Ingest error")
        
        result = crud_manager.upsert_document(
            "error_doc",
            {"title": "Test"}
        )
        
        # Should fail because both read and create failed
        assert result.success is False
        assert len(result.errors) > 0
        
        # Restore original mocks
        crud_manager.backend.read_document_operation.side_effect = original_read
        crud_manager.backend.ingest_document_polyglot.side_effect = original_ingest
    
    def test_upsert_to_dict(self, crud_manager):
        """Test UpsertResult.to_dict()"""
        result = crud_manager.upsert_document(
            "new_doc",
            {"title": "Test"}
        )
        
        result_dict = result.to_dict()
        
        assert "success" in result_dict
        assert "document_id" in result_dict
        assert "operation" in result_dict
        assert "existed_before" in result_dict
        assert "merge_strategy" in result_dict
        assert "created_fields" in result_dict
        assert "updated_fields" in result_dict


# ============================================================================
# TEST BATCH UPDATE
# ============================================================================


class TestBatchUpdate:
    """Tests für Batch Update Operations"""
    
    def test_batch_update_single_document(self, crud_manager):
        """Test batch update mit einem Dokument"""
        updates = {
            "existing_doc": {"status": "completed"}
        }
        
        results = crud_manager.batch_update_documents(updates)
        
        assert len(results) == 1
        assert "existing_doc" in results
        assert results["existing_doc"].success is True
    
    def test_batch_update_multiple_documents(self, crud_manager):
        """Test batch update mit mehreren Dokumenten"""
        updates = {
            "doc1": {"status": "completed"},
            "doc2": {"priority": 15},
            "doc3": {"status": "archived"}
        }
        
        results = crud_manager.batch_update_documents(updates)
        
        assert len(results) == 3
        assert all(r.success for r in results.values())
    
    def test_batch_update_with_errors_continue(self, crud_manager):
        """Test batch update mit Fehlern (continue_on_error=True)"""
        # Simulate error for one document
        def mock_update_with_error(doc_id, updates):
            if doc_id == "error_doc":
                raise Exception("Update failed")
            return {
                "success": True,
                "document_id": doc_id,
                "database_operations": {},
                "issues": []
            }
        
        crud_manager.backend.update_secure_document.side_effect = mock_update_with_error
        
        updates = {
            "existing_doc": {"status": "completed"},
            "error_doc": {"status": "failed"}
        }
        
        results = crud_manager.batch_update_documents(
            updates,
            continue_on_error=True
        )
        
        assert len(results) == 2
        assert results["existing_doc"].success is True
        assert results["error_doc"].success is False
    
    def test_batch_update_max_workers(self, crud_manager):
        """Test batch update mit max_workers"""
        updates = {
            f"doc{i}": {"status": "completed"}
            for i in range(5)
        }
        
        results = crud_manager.batch_update_documents(
            updates,
            max_workers=2
        )
        
        assert len(results) == 5


# ============================================================================
# TEST INTEGRATION
# ============================================================================


class TestIntegration:
    """Integrationstests für Advanced CRUD"""
    
    def test_batch_read_then_conditional_update(self, crud_manager):
        """Test: Batch read → Conditional update"""
        # 1. Batch read
        read_result = crud_manager.batch_read_documents(
            ["existing_doc"],
            strategy=ReadStrategy.SEQUENTIAL
        )
        
        assert read_result.success is True
        
        # 2. Conditional update basierend auf read result
        conditions = [
            Condition("status", ConditionOperator.EQ, "active")
        ]
        
        update_result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            conditions
        )
        
        assert update_result.success is True
        assert update_result.condition_met is True
    
    def test_upsert_then_batch_read(self, crud_manager):
        """Test: Upsert → Batch read"""
        # 1. Upsert
        upsert_result = crud_manager.upsert_document(
            "new_doc",
            {"title": "New Document"}
        )
        
        assert upsert_result.success is True
        
        # 2. Batch read (sollte jetzt existieren)
        # Mock anpassen für new_doc
        def mock_read_with_new(doc_id, include_content=True, include_relationships=False):
            if doc_id in ["existing_doc", "new_doc"]:
                return {"document_id": doc_id, "title": "Test"}
            raise Exception(f"Document {doc_id} not found")
        
        crud_manager.backend.read_document_operation = Mock(side_effect=mock_read_with_new)
        
        read_result = crud_manager.batch_read_documents(["new_doc"])
        
        assert read_result.success is True
        assert "new_doc" in read_result.documents
    
    def test_conditional_update_workflow(self, crud_manager):
        """Test: Complete conditional update workflow"""
        # 1. Read current state
        read_result = crud_manager.batch_read_documents(["existing_doc"])
        doc = read_result.documents["existing_doc"]["data"]
        
        # 2. Conditional update mit version check
        conditions = [
            Condition("status", ConditionOperator.EQ, doc["status"])
        ]
        
        update_result = crud_manager.conditional_update_document(
            "existing_doc",
            {"priority": 20},
            conditions,
            version_check=doc["version"]
        )
        
        assert update_result.success is True
        assert update_result.version_after == doc["version"] + 1


# ============================================================================
# TEST EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Tests für Edge Cases & Error Handling"""
    
    def test_batch_read_empty_document_ids(self, crud_manager):
        """Test batch read mit leerer ID-Liste"""
        result = crud_manager.batch_read_documents([])
        
        assert result.success is True
        assert result.total_requested == 0
    
    def test_conditional_update_empty_conditions(self, crud_manager):
        """Test conditional update ohne conditions"""
        result = crud_manager.conditional_update_document(
            "existing_doc",
            {"status": "completed"},
            []
        )
        
        assert result.success is True
        assert result.condition_met is True
    
    def test_upsert_empty_data(self, crud_manager):
        """Test upsert mit leeren Daten"""
        result = crud_manager.upsert_document(
            "new_doc",
            {}
        )
        
        assert result.success is True
    
    def test_batch_update_empty_updates(self, crud_manager):
        """Test batch update mit leeren Updates"""
        results = crud_manager.batch_update_documents({})
        
        assert len(results) == 0
    
    def test_condition_evaluation_with_none_value(self):
        """Test condition evaluation mit None value"""
        cond = Condition("field", ConditionOperator.EQ, None)
        
        assert cond.evaluate({"field": None}) is True
        assert cond.evaluate({"field": "value"}) is False
    
    def test_batch_read_result_success_rate_zero_requested(self):
        """Test success_rate mit zero requested"""
        result = BatchReadResult(
            success=True,
            total_requested=0,
            total_read=0,
            documents={}
        )
        
        assert result.success_rate == 0.0


# ============================================================================
# RUN TESTS
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
