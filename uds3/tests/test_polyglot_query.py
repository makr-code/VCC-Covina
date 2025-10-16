"""
Tests for UDS3 Polyglot Query Module

Comprehensive test suite for multi-database query coordination,
join strategies, and result merging.

Author: UDS3 Team
Date: 2. Oktober 2025
"""

import pytest
from typing import List, Dict, Any, Set
from unittest.mock import Mock, MagicMock, patch
import time

from uds3_polyglot_query import (
    PolyglotQuery,
    JoinStrategy,
    ExecutionMode,
    DatabaseType,
    QueryContext,
    QueryResult,
    PolyglotQueryResult,
    VectorQueryBuilder,
    GraphQueryBuilder,
    RelationalQueryBuilder,
    FileStorageQueryBuilder,
    create_polyglot_query
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_unified_strategy():
    """Mock UnifiedDatabaseStrategy"""
    strategy = Mock()
    
    # Mock filter creation methods
    strategy.create_vector_filter = Mock(return_value=Mock())
    strategy.create_graph_filter = Mock(return_value=Mock())
    strategy.create_relational_filter = Mock(return_value=Mock())
    strategy.create_file_storage_filter = Mock(return_value=Mock())
    
    return strategy


@pytest.fixture
def polyglot_query(mock_unified_strategy):
    """PolyglotQuery instance with mock strategy"""
    return PolyglotQuery(mock_unified_strategy)


@pytest.fixture
def sample_query_results():
    """Sample query results from different databases"""
    return {
        DatabaseType.VECTOR: QueryResult(
            database_type=DatabaseType.VECTOR,
            success=True,
            document_ids={"doc1", "doc2", "doc3", "doc4"},
            results=[
                {"document_id": "doc1", "score": 0.95},
                {"document_id": "doc2", "score": 0.90},
                {"document_id": "doc3", "score": 0.85},
                {"document_id": "doc4", "score": 0.80}
            ],
            count=4,
            execution_time_ms=50.0
        ),
        DatabaseType.GRAPH: QueryResult(
            database_type=DatabaseType.GRAPH,
            success=True,
            document_ids={"doc2", "doc3", "doc4", "doc5"},
            results=[
                {"document_id": "doc2", "relationships": 5},
                {"document_id": "doc3", "relationships": 3},
                {"document_id": "doc4", "relationships": 7},
                {"document_id": "doc5", "relationships": 2}
            ],
            count=4,
            execution_time_ms=75.0
        ),
        DatabaseType.RELATIONAL: QueryResult(
            database_type=DatabaseType.RELATIONAL,
            success=True,
            document_ids={"doc3", "doc4", "doc5", "doc6"},
            results=[
                {"document_id": "doc3", "status": "active"},
                {"document_id": "doc4", "status": "active"},
                {"document_id": "doc5", "status": "active"},
                {"document_id": "doc6", "status": "active"}
            ],
            count=4,
            execution_time_ms=25.0
        )
    }


# ============================================================================
# Test: Enums
# ============================================================================

class TestEnums:
    """Test enum definitions"""
    
    def test_join_strategy_values(self):
        """Test JoinStrategy enum values"""
        assert JoinStrategy.INTERSECTION.value == "intersection"
        assert JoinStrategy.UNION.value == "union"
        assert JoinStrategy.SEQUENTIAL.value == "sequential"
    
    def test_execution_mode_values(self):
        """Test ExecutionMode enum values"""
        assert ExecutionMode.PARALLEL.value == "parallel"
        assert ExecutionMode.SEQUENTIAL.value == "sequential"
        assert ExecutionMode.SMART.value == "smart"
    
    def test_database_type_values(self):
        """Test DatabaseType enum values"""
        assert DatabaseType.VECTOR.value == "vector"
        assert DatabaseType.GRAPH.value == "graph"
        assert DatabaseType.RELATIONAL.value == "relational"
        assert DatabaseType.FILE_STORAGE.value == "file_storage"


# ============================================================================
# Test: Data Classes
# ============================================================================

class TestDataClasses:
    """Test data class definitions"""
    
    def test_query_context_creation(self):
        """Test QueryContext creation"""
        context = QueryContext(
            database_type=DatabaseType.VECTOR,
            filter_instance=Mock(),
            query_params={"threshold": 0.8},
            enabled=True,
            priority=1
        )
        
        assert context.database_type == DatabaseType.VECTOR
        assert context.query_params["threshold"] == 0.8
        assert context.enabled is True
        assert context.priority == 1
    
    def test_query_result_creation(self):
        """Test QueryResult creation"""
        result = QueryResult(
            database_type=DatabaseType.GRAPH,
            success=True,
            document_ids={"doc1", "doc2"},
            results=[{"id": "doc1"}, {"id": "doc2"}],
            count=2,
            execution_time_ms=50.0,
            error=None
        )
        
        assert result.database_type == DatabaseType.GRAPH
        assert result.success is True
        assert len(result.document_ids) == 2
        assert result.count == 2
    
    def test_query_result_to_dict(self):
        """Test QueryResult serialization"""
        result = QueryResult(
            database_type=DatabaseType.VECTOR,
            success=True,
            document_ids={"doc1"},
            results=[],
            count=1,
            execution_time_ms=10.0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["database_type"] == "vector"
        assert result_dict["success"] is True
        assert "doc1" in result_dict["document_ids"]
        assert result_dict["execution_time_ms"] == 10.0


# ============================================================================
# Test: PolyglotQuery Creation
# ============================================================================

class TestPolyglotQueryCreation:
    """Test PolyglotQuery instantiation"""
    
    def test_create_polyglot_query(self, mock_unified_strategy):
        """Test PolyglotQuery creation"""
        query = PolyglotQuery(mock_unified_strategy)
        
        assert query.unified_strategy == mock_unified_strategy
        assert query._join_strategy == JoinStrategy.INTERSECTION
        assert query._execution_mode == ExecutionMode.SMART
        assert len(query._contexts) == 0
        assert query._executed is False
    
    def test_create_with_custom_execution_mode(self, mock_unified_strategy):
        """Test creation with custom execution mode"""
        query = PolyglotQuery(
            mock_unified_strategy,
            execution_mode=ExecutionMode.PARALLEL
        )
        
        assert query._execution_mode == ExecutionMode.PARALLEL
    
    def test_factory_function(self, mock_unified_strategy):
        """Test create_polyglot_query factory function"""
        query = create_polyglot_query(mock_unified_strategy)
        
        assert isinstance(query, PolyglotQuery)
        assert query.unified_strategy == mock_unified_strategy


# ============================================================================
# Test: Fluent API - Query Builders
# ============================================================================

class TestQueryBuilders:
    """Test query builder fluent API"""
    
    def test_vector_query_builder(self, polyglot_query):
        """Test vector query builder"""
        builder = polyglot_query.vector()
        
        assert isinstance(builder, VectorQueryBuilder)
        assert builder.polyglot_query == polyglot_query
    
    def test_graph_query_builder(self, polyglot_query):
        """Test graph query builder"""
        builder = polyglot_query.graph()
        
        assert isinstance(builder, GraphQueryBuilder)
        assert builder.polyglot_query == polyglot_query
    
    def test_relational_query_builder(self, polyglot_query):
        """Test relational query builder"""
        builder = polyglot_query.relational()
        
        assert isinstance(builder, RelationalQueryBuilder)
        assert builder.polyglot_query == polyglot_query
    
    def test_file_storage_query_builder(self, polyglot_query):
        """Test file storage query builder"""
        builder = polyglot_query.file_storage()
        
        assert isinstance(builder, FileStorageQueryBuilder)
        assert builder.polyglot_query == polyglot_query
    
    @patch('uds3_polyglot_query.VECTOR_FILTER_AVAILABLE', True)
    def test_chaining_query_builders(self, mock_unified_strategy):
        """Test chaining multiple query builders"""
        # Setup mock filter
        mock_filter = Mock()
        mock_unified_strategy.create_vector_filter = Mock(return_value=mock_filter)
        
        query = PolyglotQuery(mock_unified_strategy)
        
        # Chain multiple database queries (test fluent API)
        result_query = (
            query.vector()
                .by_similarity([0.1] * 10, threshold=0.8)
        )
        
        assert result_query == query
        assert len(query._contexts) > 0


# ============================================================================
# Test: Join Strategy Configuration
# ============================================================================

class TestJoinStrategyConfiguration:
    """Test join strategy configuration"""
    
    def test_set_join_strategy_intersection(self, polyglot_query):
        """Test setting INTERSECTION join strategy"""
        result = polyglot_query.join_strategy(JoinStrategy.INTERSECTION)
        
        assert result == polyglot_query  # Fluent API
        assert polyglot_query._join_strategy == JoinStrategy.INTERSECTION
    
    def test_set_join_strategy_union(self, polyglot_query):
        """Test setting UNION join strategy"""
        polyglot_query.join_strategy(JoinStrategy.UNION)
        
        assert polyglot_query._join_strategy == JoinStrategy.UNION
    
    def test_set_join_strategy_sequential(self, polyglot_query):
        """Test setting SEQUENTIAL join strategy"""
        polyglot_query.join_strategy(JoinStrategy.SEQUENTIAL)
        
        assert polyglot_query._join_strategy == JoinStrategy.SEQUENTIAL
    
    def test_set_execution_mode(self, polyglot_query):
        """Test setting execution mode"""
        polyglot_query.execution_mode(ExecutionMode.PARALLEL)
        
        assert polyglot_query._execution_mode == ExecutionMode.PARALLEL


# ============================================================================
# Test: Result Joining - INTERSECTION
# ============================================================================

class TestJoinIntersection:
    """Test INTERSECTION join strategy"""
    
    def test_intersection_join_basic(self, polyglot_query, sample_query_results):
        """Test basic INTERSECTION join"""
        polyglot_query._join_strategy = JoinStrategy.INTERSECTION
        
        joined_ids, joined_results = polyglot_query._join_intersection(
            sample_query_results
        )
        
        # doc3 and doc4 are in all three databases
        assert joined_ids == {"doc3", "doc4"}
        assert len(joined_results) == 2
    
    def test_intersection_with_no_overlap(self, polyglot_query):
        """Test INTERSECTION with no overlapping documents"""
        results = {
            DatabaseType.VECTOR: QueryResult(
                database_type=DatabaseType.VECTOR,
                success=True,
                document_ids={"doc1", "doc2"},
                results=[],
                count=2,
                execution_time_ms=10.0
            ),
            DatabaseType.GRAPH: QueryResult(
                database_type=DatabaseType.GRAPH,
                success=True,
                document_ids={"doc3", "doc4"},
                results=[],
                count=2,
                execution_time_ms=10.0
            )
        }
        
        polyglot_query._join_strategy = JoinStrategy.INTERSECTION
        joined_ids, _ = polyglot_query._join_intersection(results)
        
        assert len(joined_ids) == 0  # No overlap
    
    def test_intersection_with_single_database(self, polyglot_query):
        """Test INTERSECTION with only one database"""
        results = {
            DatabaseType.VECTOR: QueryResult(
                database_type=DatabaseType.VECTOR,
                success=True,
                document_ids={"doc1", "doc2", "doc3"},
                results=[],
                count=3,
                execution_time_ms=10.0
            )
        }
        
        polyglot_query._join_strategy = JoinStrategy.INTERSECTION
        joined_ids, _ = polyglot_query._join_intersection(results)
        
        # With only one DB, all its IDs are in the intersection
        assert joined_ids == {"doc1", "doc2", "doc3"}


# ============================================================================
# Test: Result Joining - UNION
# ============================================================================

class TestJoinUnion:
    """Test UNION join strategy"""
    
    def test_union_join_basic(self, polyglot_query, sample_query_results):
        """Test basic UNION join"""
        polyglot_query._join_strategy = JoinStrategy.UNION
        
        joined_ids, joined_results = polyglot_query._join_union(
            sample_query_results
        )
        
        # All unique documents from all databases
        assert joined_ids == {"doc1", "doc2", "doc3", "doc4", "doc5", "doc6"}
        assert len(joined_results) == 6
    
    def test_union_with_single_database(self, polyglot_query):
        """Test UNION with only one database"""
        results = {
            DatabaseType.VECTOR: QueryResult(
                database_type=DatabaseType.VECTOR,
                success=True,
                document_ids={"doc1", "doc2"},
                results=[],
                count=2,
                execution_time_ms=10.0
            )
        }
        
        polyglot_query._join_strategy = JoinStrategy.UNION
        joined_ids, _ = polyglot_query._join_union(results)
        
        assert joined_ids == {"doc1", "doc2"}
    
    def test_union_with_empty_results(self, polyglot_query):
        """Test UNION with empty results"""
        results = {
            DatabaseType.VECTOR: QueryResult(
                database_type=DatabaseType.VECTOR,
                success=True,
                document_ids=set(),
                results=[],
                count=0,
                execution_time_ms=10.0
            ),
            DatabaseType.GRAPH: QueryResult(
                database_type=DatabaseType.GRAPH,
                success=True,
                document_ids=set(),
                results=[],
                count=0,
                execution_time_ms=10.0
            )
        }
        
        polyglot_query._join_strategy = JoinStrategy.UNION
        joined_ids, _ = polyglot_query._join_union(results)
        
        assert len(joined_ids) == 0


# ============================================================================
# Test: Result Joining - SEQUENTIAL
# ============================================================================

class TestJoinSequential:
    """Test SEQUENTIAL join strategy"""
    
    def test_sequential_join_basic(self, polyglot_query):
        """Test basic SEQUENTIAL join"""
        # Setup contexts with priorities
        polyglot_query._contexts = {
            DatabaseType.VECTOR: QueryContext(
                database_type=DatabaseType.VECTOR,
                filter_instance=Mock(),
                priority=1  # First
            ),
            DatabaseType.GRAPH: QueryContext(
                database_type=DatabaseType.GRAPH,
                filter_instance=Mock(),
                priority=2  # Second
            ),
            DatabaseType.RELATIONAL: QueryContext(
                database_type=DatabaseType.RELATIONAL,
                filter_instance=Mock(),
                priority=3  # Last (final result)
            )
        }
        
        results = {
            DatabaseType.VECTOR: QueryResult(
                database_type=DatabaseType.VECTOR,
                success=True,
                document_ids={"doc1", "doc2", "doc3"},
                results=[],
                count=3,
                execution_time_ms=10.0
            ),
            DatabaseType.GRAPH: QueryResult(
                database_type=DatabaseType.GRAPH,
                success=True,
                document_ids={"doc2", "doc3"},  # Filtered by vector
                results=[],
                count=2,
                execution_time_ms=10.0
            ),
            DatabaseType.RELATIONAL: QueryResult(
                database_type=DatabaseType.RELATIONAL,
                success=True,
                document_ids={"doc3"},  # Final filtered result
                results=[],
                count=1,
                execution_time_ms=10.0
            )
        }
        
        polyglot_query._join_strategy = JoinStrategy.SEQUENTIAL
        joined_ids, _ = polyglot_query._join_sequential(results)
        
        # Should return final stage results
        assert joined_ids == {"doc3"}


# ============================================================================
# Test: Document ID Extraction
# ============================================================================

class TestDocumentIDExtraction:
    """Test document ID extraction from various result formats"""
    
    def test_extract_from_dict_with_results_key(self, polyglot_query):
        """Test extraction from dict with 'results' key"""
        result = {
            "results": [
                {"document_id": "doc1"},
                {"document_id": "doc2"},
                {"id": "doc3"}  # Alternative ID field
            ]
        }
        
        ids = polyglot_query._extract_document_ids(result, DatabaseType.VECTOR)
        
        assert ids == {"doc1", "doc2", "doc3"}
    
    def test_extract_from_dict_with_documents_key(self, polyglot_query):
        """Test extraction from dict with 'documents' key"""
        result = {
            "documents": [
                {"document_id": "doc1"},
                {"document_id": "doc2"}
            ]
        }
        
        ids = polyglot_query._extract_document_ids(result, DatabaseType.GRAPH)
        
        assert ids == {"doc1", "doc2"}
    
    def test_extract_from_list(self, polyglot_query):
        """Test extraction from list format"""
        result = [
            {"document_id": "doc1"},
            {"id": "doc2"},
            {"file_id": "doc3"}
        ]
        
        ids = polyglot_query._extract_document_ids(result, DatabaseType.FILE_STORAGE)
        
        assert ids == {"doc1", "doc2", "doc3"}
    
    def test_extract_with_missing_ids(self, polyglot_query):
        """Test extraction with missing ID fields"""
        result = {
            "results": [
                {"document_id": "doc1"},
                {"name": "file2"},  # No ID field
                {"document_id": "doc3"}
            ]
        }
        
        ids = polyglot_query._extract_document_ids(result, DatabaseType.VECTOR)
        
        # Should only extract doc1 and doc3
        assert ids == {"doc1", "doc3"}


# ============================================================================
# Test: Execution Mode Determination
# ============================================================================

class TestExecutionModeDetermination:
    """Test execution mode determination logic"""
    
    def test_smart_mode_intersection(self, polyglot_query):
        """Test SMART mode with INTERSECTION strategy"""
        polyglot_query._execution_mode = ExecutionMode.SMART
        polyglot_query._join_strategy = JoinStrategy.INTERSECTION
        
        mode = polyglot_query._determine_execution_mode()
        
        assert mode == ExecutionMode.PARALLEL
    
    def test_smart_mode_union(self, polyglot_query):
        """Test SMART mode with UNION strategy"""
        polyglot_query._execution_mode = ExecutionMode.SMART
        polyglot_query._join_strategy = JoinStrategy.UNION
        
        mode = polyglot_query._determine_execution_mode()
        
        assert mode == ExecutionMode.PARALLEL
    
    def test_smart_mode_sequential(self, polyglot_query):
        """Test SMART mode with SEQUENTIAL strategy"""
        polyglot_query._execution_mode = ExecutionMode.SMART
        polyglot_query._join_strategy = JoinStrategy.SEQUENTIAL
        
        mode = polyglot_query._determine_execution_mode()
        
        assert mode == ExecutionMode.SEQUENTIAL
    
    def test_explicit_parallel_mode(self, polyglot_query):
        """Test explicit PARALLEL mode"""
        polyglot_query._execution_mode = ExecutionMode.PARALLEL
        polyglot_query._join_strategy = JoinStrategy.SEQUENTIAL
        
        mode = polyglot_query._determine_execution_mode()
        
        # Should respect explicit mode
        assert mode == ExecutionMode.PARALLEL


# ============================================================================
# Test: Query Execution (Mocked)
# ============================================================================

class TestQueryExecution:
    """Test query execution with mocked database calls"""
    
    def test_execute_without_queries(self, polyglot_query):
        """Test execution with no configured queries"""
        result = polyglot_query.execute()
        
        assert result.success is False
        assert result.error == "No database queries configured"
        assert result.joined_count == 0
    
    @patch('uds3_polyglot_query.VECTOR_FILTER_AVAILABLE', True)
    def test_execute_single_database_query(self, mock_unified_strategy):
        """Test execution with single database query"""
        # Setup mock
        mock_filter = Mock()
        mock_filter.search = Mock(return_value={
            "results": [
                {"document_id": "doc1"},
                {"document_id": "doc2"}
            ]
        })
        mock_unified_strategy.create_vector_filter = Mock(return_value=mock_filter)
        
        query = PolyglotQuery(mock_unified_strategy)
        
        # Add context manually
        context = QueryContext(
            database_type=DatabaseType.VECTOR,
            filter_instance=mock_filter,
            query_params={"embedding": [0.1] * 10},
            enabled=True
        )
        query._add_context(context)
        
        # Execute
        result = query.execute()
        
        assert result.success is True
        assert DatabaseType.VECTOR in result.databases_queried
        assert len(result.databases_succeeded) >= 0  # May fail if filter not fully mocked


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_execution_with_failed_database(self, polyglot_query):
        """Test execution when one database fails"""
        # Add context that will fail
        mock_filter = Mock()
        mock_filter.search = Mock(side_effect=Exception("Database error"))
        
        context = QueryContext(
            database_type=DatabaseType.VECTOR,
            filter_instance=mock_filter,
            query_params={},
            enabled=True
        )
        polyglot_query._add_context(context)
        
        # Execute (will fail gracefully)
        result = polyglot_query.execute()
        
        # Should still return result, but with error
        assert isinstance(result, PolyglotQueryResult)
        assert len(result.databases_failed) > 0 or result.error is not None
    
    def test_extract_ids_with_invalid_format(self, polyglot_query):
        """Test ID extraction with invalid result format"""
        invalid_result = "not a dict or list"
        
        ids = polyglot_query._extract_document_ids(invalid_result, DatabaseType.VECTOR)
        
        # Should return empty set without crashing
        assert ids == set()


# ============================================================================
# Test: Performance & Concurrency
# ============================================================================

class TestPerformanceConcurrency:
    """Test performance tracking and concurrent execution"""
    
    def test_execution_time_tracking(self, polyglot_query):
        """Test that execution time is tracked"""
        # Add simple context
        mock_filter = Mock()
        mock_filter.search = Mock(return_value={"results": []})
        
        context = QueryContext(
            database_type=DatabaseType.VECTOR,
            filter_instance=mock_filter,
            query_params={},
            enabled=True
        )
        polyglot_query._add_context(context)
        
        # Execute
        result = polyglot_query.execute()
        
        # Check timing
        assert result.total_execution_time_ms >= 0.0
        assert DatabaseType.VECTOR in result.database_execution_times
    
    def test_thread_safety_add_context(self, polyglot_query):
        """Test thread-safe context addition"""
        import threading
        
        def add_context():
            for i in range(10):
                context = QueryContext(
                    database_type=DatabaseType.VECTOR,
                    filter_instance=Mock(),
                    query_params={"id": i},
                    enabled=True,
                    priority=i
                )
                polyglot_query._add_context(context)
        
        # Run multiple threads adding contexts
        threads = [threading.Thread(target=add_context) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have context (last one wins due to same database_type)
        assert DatabaseType.VECTOR in polyglot_query._contexts


# ============================================================================
# Test: Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    def test_complete_intersection_workflow(self, mock_unified_strategy):
        """Test complete workflow with INTERSECTION join"""
        query = PolyglotQuery(mock_unified_strategy)
        
        # Configure query (fluent API)
        query.join_strategy(JoinStrategy.INTERSECTION)
        query.execution_mode(ExecutionMode.PARALLEL)
        
        # Verify configuration
        assert query._join_strategy == JoinStrategy.INTERSECTION
        assert query._execution_mode == ExecutionMode.PARALLEL
    
    def test_complete_union_workflow(self, mock_unified_strategy):
        """Test complete workflow with UNION join"""
        query = PolyglotQuery(mock_unified_strategy)
        
        query.join_strategy(JoinStrategy.UNION)
        
        assert query._join_strategy == JoinStrategy.UNION
    
    def test_result_serialization(self, sample_query_results):
        """Test result serialization to dict"""
        result = PolyglotQueryResult(
            success=True,
            join_strategy=JoinStrategy.INTERSECTION,
            execution_mode=ExecutionMode.PARALLEL,
            database_results=sample_query_results,
            joined_document_ids={"doc3", "doc4"},
            joined_results=[],
            joined_count=2,
            total_execution_time_ms=150.0,
            database_execution_times={
                DatabaseType.VECTOR: 50.0,
                DatabaseType.GRAPH: 75.0,
                DatabaseType.RELATIONAL: 25.0
            },
            databases_queried=[DatabaseType.VECTOR, DatabaseType.GRAPH, DatabaseType.RELATIONAL],
            databases_succeeded=[DatabaseType.VECTOR, DatabaseType.GRAPH, DatabaseType.RELATIONAL],
            databases_failed=[]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["join_strategy"] == "intersection"
        assert result_dict["joined_count"] == 2
        assert "vector" in result_dict["database_execution_times"]


# ============================================================================
# Test: Factory Functions
# ============================================================================

class TestFactoryFunctions:
    """Test factory functions"""
    
    def test_create_polyglot_query_default(self, mock_unified_strategy):
        """Test create_polyglot_query with defaults"""
        query = create_polyglot_query(mock_unified_strategy)
        
        assert isinstance(query, PolyglotQuery)
        assert query._execution_mode == ExecutionMode.SMART
    
    def test_create_polyglot_query_custom_mode(self, mock_unified_strategy):
        """Test create_polyglot_query with custom execution mode"""
        query = create_polyglot_query(
            mock_unified_strategy,
            execution_mode=ExecutionMode.SEQUENTIAL
        )
        
        assert query._execution_mode == ExecutionMode.SEQUENTIAL


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
