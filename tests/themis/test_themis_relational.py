"""
Unit Tests: ThemisRelationalBackend
====================================

Tests for relational database operations:
- CRUD operations (create, read, update, delete)
- Query execution (SELECT, WHERE, JOIN)
- SQL→AQL translation
- Aggregate functions (COUNT, SUM, AVG, etc.)
- Transaction support
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import patch

from database.themis_relational import ThemisRelationalBackend
from database.themis_exceptions import ThemisNotFoundError, ThemisValidationError
from tests.themis.conftest import (
    create_success_response,
    create_error_response,
    MockAsyncClient,
)


class TestRelationalCRUD:
    """Test CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_entity_success(self, mock_http_client, sample_entity_data):
        """Test: create_entity() inserts entity"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/entities",
            create_success_response({"id": "test_entity_123", "created": True})
        )
        
        result = await backend.create_entity("documents", sample_entity_data)
        
        assert result["id"] == "test_entity_123"
        assert result["created"] is True
    
    @pytest.mark.asyncio
    async def test_get_entity_success(self, mock_http_client, sample_entity_data):
        """Test: get_entity() retrieves entity by ID"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/entities/test_entity_123",
            create_success_response(sample_entity_data)
        )
        
        result = await backend.get_entity("documents", "test_entity_123")
        
        assert result["id"] == "test_entity_123"
        assert result["attributes"]["title"] == "Test Document"
    
    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, mock_http_client):
        """Test: get_entity() raises NotFoundError for missing entity"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/entities/missing_id",
            create_error_response(404, "Entity not found")
        )
        
        with pytest.raises(ThemisNotFoundError):
            await backend.get_entity("documents", "missing_id")
    
    @pytest.mark.asyncio
    async def test_update_entity_success(self, mock_http_client):
        """Test: update_entity() updates entity"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        update_data = {"attributes": {"title": "Updated Title"}}
        
        mock_http_client.set_response(
            "PUT",
            "http://localhost:8765/entities/test_entity_123",
            create_success_response({"id": "test_entity_123", "updated": True})
        )
        
        result = await backend.update_entity("documents", "test_entity_123", update_data)
        
        assert result["updated"] is True
    
    @pytest.mark.asyncio
    async def test_delete_entity_success(self, mock_http_client):
        """Test: delete_entity() deletes entity"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/entities/test_entity_123",
            create_success_response({"deleted": True})
        )
        
        result = await backend.delete_entity("documents", "test_entity_123")
        
        assert result["deleted"] is True


class TestQueryExecution:
    """Test query execution"""
    
    @pytest.mark.asyncio
    async def test_execute_query_returns_results(self, mock_http_client):
        """Test: execute_query() returns query results"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_results = [
            {"id": "doc_1", "title": "Doc 1"},
            {"id": "doc_2", "title": "Doc 2"},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/query/aql",
            create_success_response({"results": mock_results, "count": 2})
        )
        
        results = await backend.execute_query("SELECT * FROM documents")
        
        assert len(results) == 2
        assert results[0]["id"] == "doc_1"
    
    @pytest.mark.asyncio
    async def test_execute_query_with_parameters(self, mock_http_client):
        """Test: execute_query() supports parameterized queries"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_results = [{"id": "doc_1", "title": "Specific Doc"}]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/query/aql",
            create_success_response({"results": mock_results, "count": 1})
        )
        
        results = await backend.execute_query(
            "SELECT * FROM documents WHERE id = @id",
            {"id": "doc_1"}
        )
        
        assert len(results) == 1
        assert results[0]["id"] == "doc_1"
    
    @pytest.mark.asyncio
    async def test_query_entities_with_filters(self, mock_http_client):
        """Test: query_entities() applies filters"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_results = [{"id": "doc_1", "status": "active"}]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/query/aql",
            create_success_response({"results": mock_results, "count": 1})
        )
        
        filters = {"status": "active", "type": "document"}
        results = await backend.query_entities("documents", filters)
        
        assert len(results) == 1
        assert results[0]["status"] == "active"


class TestSQLToAQLTranslation:
    """Test SQL → AQL translation"""
    
    @pytest.mark.asyncio
    async def test_translate_simple_select(self):
        """Test: Translate simple SELECT statement"""
        backend = ThemisRelationalBackend(MockAsyncClient(), "http://localhost:8765")
        
        sql = "SELECT * FROM documents"
        aql = backend._translate_sql_to_aql(sql)
        
        assert "FOR doc IN documents" in aql
        assert "RETURN doc" in aql
    
    @pytest.mark.asyncio
    async def test_translate_select_with_where(self):
        """Test: Translate SELECT with WHERE clause"""
        backend = ThemisRelationalBackend(MockAsyncClient(), "http://localhost:8765")
        
        sql = "SELECT * FROM documents WHERE status = 'active'"
        aql = backend._translate_sql_to_aql(sql)
        
        assert "FOR doc IN documents" in aql
        assert "FILTER" in aql
        assert "doc.status == 'active'" in aql or "doc.status = 'active'" in aql
    
    @pytest.mark.asyncio
    async def test_translate_select_with_limit(self):
        """Test: Translate SELECT with LIMIT"""
        backend = ThemisRelationalBackend(MockAsyncClient(), "http://localhost:8765")
        
        sql = "SELECT * FROM documents LIMIT 10"
        aql = backend._translate_sql_to_aql(sql)
        
        assert "LIMIT 10" in aql
    
    @pytest.mark.asyncio
    async def test_translate_select_specific_columns(self):
        """Test: Translate SELECT with specific columns"""
        backend = ThemisRelationalBackend(MockAsyncClient(), "http://localhost:8765")
        
        sql = "SELECT id, title FROM documents"
        aql = backend._translate_sql_to_aql(sql)
        
        # Should return only specified fields
        assert "id" in aql or "title" in aql


class TestAggregations:
    """Test aggregate functions"""
    
    @pytest.mark.asyncio
    async def test_count_entities(self, mock_http_client):
        """Test: count() returns entity count"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/query/aql",
            create_success_response({"results": [{"count": 42}]})
        )
        
        count = await backend.count("documents")
        
        assert count == 42
    
    @pytest.mark.asyncio
    async def test_count_with_filter(self, mock_http_client):
        """Test: count() with filter"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/query/aql",
            create_success_response({"results": [{"count": 15}]})
        )
        
        count = await backend.count("documents", {"status": "active"})
        
        assert count == 15
    
    @pytest.mark.asyncio
    async def test_aggregate_sum(self, mock_http_client):
        """Test: aggregate() with SUM"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/query/aql",
            create_success_response({"results": [{"sum_size": 1024000}]})
        )
        
        result = await backend.aggregate("documents", "SUM", "size")
        
        assert result == 1024000
    
    @pytest.mark.asyncio
    async def test_aggregate_avg(self, mock_http_client):
        """Test: aggregate() with AVG"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/query/aql",
            create_success_response({"results": [{"avg_score": 87.5}]})
        )
        
        result = await backend.aggregate("reviews", "AVG", "score")
        
        assert result == 87.5


class TestTransactions:
    """Test transaction support"""
    
    @pytest.mark.asyncio
    async def test_create_within_transaction(self, mock_http_client, sample_entity_data):
        """Test: create_entity() within transaction"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        # Mock begin transaction
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/begin",
            create_success_response({"transaction_id": "txn_123"})
        )
        
        # Mock entity creation
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/entities",
            create_success_response({"id": "test_entity_123", "created": True})
        )
        
        # Mock commit
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/txn_123/commit",
            create_success_response({"status": "committed"})
        )
        
        # Execute within transaction context
        async with backend.transaction() as txn_id:
            result = await backend.create_entity(
                "documents",
                sample_entity_data,
                transaction_id=txn_id
            )
            assert result["created"] is True
        
        # Verify commit was called
        commit_requests = [r for r in mock_http_client.requests if "commit" in r["url"]]
        assert len(commit_requests) == 1
    
    @pytest.mark.asyncio
    async def test_rollback_on_error(self, mock_http_client, sample_entity_data):
        """Test: Transaction rolls back on error"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        # Mock begin transaction
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/begin",
            create_success_response({"transaction_id": "txn_456"})
        )
        
        # Mock rollback
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/txn_456/rollback",
            create_success_response({"status": "rolled_back"})
        )
        
        # Execute with intentional error
        with pytest.raises(ValueError):
            async with backend.transaction() as txn_id:
                raise ValueError("Intentional error for rollback")
        
        # Verify rollback was called
        rollback_requests = [r for r in mock_http_client.requests if "rollback" in r["url"]]
        assert len(rollback_requests) == 1


class TestBatchOperations:
    """Test batch operations"""
    
    @pytest.mark.asyncio
    async def test_batch_create_entities(self, mock_http_client):
        """Test: batch_create() inserts multiple entities"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        entities = [
            {"id": "doc_1", "title": "Doc 1"},
            {"id": "doc_2", "title": "Doc 2"},
            {"id": "doc_3", "title": "Doc 3"},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/entities/batch",
            create_success_response({"created": 3, "ids": ["doc_1", "doc_2", "doc_3"]})
        )
        
        result = await backend.batch_create("documents", entities)
        
        assert result["created"] == 3
        assert len(result["ids"]) == 3
    
    @pytest.mark.asyncio
    async def test_batch_update_entities(self, mock_http_client):
        """Test: batch_update() updates multiple entities"""
        backend = ThemisRelationalBackend(mock_http_client, "http://localhost:8765")
        
        updates = [
            {"id": "doc_1", "status": "processed"},
            {"id": "doc_2", "status": "processed"},
        ]
        
        mock_http_client.set_response(
            "PUT",
            "http://localhost:8765/entities/batch",
            create_success_response({"updated": 2})
        )
        
        result = await backend.batch_update("documents", updates)
        
        assert result["updated"] == 2


# Run tests with: pytest tests/themis/test_themis_relational.py -v
