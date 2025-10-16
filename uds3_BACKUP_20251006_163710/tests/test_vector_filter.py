"""
Unit Tests für UDS3 Vector Filter

Testet:
- VectorFilter class
- Similarity Search
- Metadata Filtering
- Collection Filtering
- Combined Queries
- ChromaDB Integration

Autor: UDS3 Team
Datum: 1. Oktober 2025
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, MagicMock, patch

from uds3_vector_filter import (
    VectorFilter,
    SimilarityQuery,
    VectorQueryResult,
    create_vector_filter,
)

try:
    from uds3_query_filters import FilterOperator
except ImportError:
    # Fallback for testing
    from enum import Enum
    class FilterOperator(Enum):
        EQ = "=="
        NE = "!="
        GT = ">"
        LT = "<"
        IN = "in"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_chromadb_backend():
    """Mock ChromaDB Backend"""
    backend = Mock()
    
    # Mock query_collection
    def mock_query(collection_name, query_embeddings, n_results=10, where=None, include=None):
        # Simulate ChromaDB response
        return {
            "ids": [["doc1", "doc2", "doc3"]],
            "documents": [["Document 1", "Document 2", "Document 3"]],
            "metadatas": [[
                {"status": "active", "priority": 10},
                {"status": "active", "priority": 5},
                {"status": "inactive", "priority": 3}
            ]],
            "distances": [[0.1, 0.3, 0.5]]
        }
    
    backend.query_collection = Mock(side_effect=mock_query)
    
    # Mock count_collection
    backend.count_collection = Mock(return_value=3)
    
    return backend


@pytest.fixture
def sample_embedding():
    """Sample embedding vector"""
    return [0.1] * 384  # Standard BERT embedding size


@pytest.fixture
def vector_filter(mock_chromadb_backend):
    """VectorFilter instance"""
    return VectorFilter(mock_chromadb_backend, "test_collection")


# ============================================================================
# TEST SIMILARITY QUERY
# ============================================================================


class TestSimilarityQuery:
    """Tests für SimilarityQuery dataclass"""
    
    def test_create_similarity_query(self, sample_embedding):
        """Test SimilarityQuery erstellen"""
        query = SimilarityQuery(
            query_embedding=sample_embedding,
            threshold=0.8,
            top_k=5,
            metric="cosine"
        )
        
        assert query.query_embedding == sample_embedding
        assert query.threshold == 0.8
        assert query.top_k == 5
        assert query.metric == "cosine"
    
    def test_similarity_query_defaults(self, sample_embedding):
        """Test SimilarityQuery default values"""
        query = SimilarityQuery(query_embedding=sample_embedding)
        
        assert query.threshold == 0.7
        assert query.top_k == 10
        assert query.metric == "cosine"
    
    def test_similarity_query_to_dict(self, sample_embedding):
        """Test SimilarityQuery.to_dict()"""
        query = SimilarityQuery(
            query_embedding=sample_embedding,
            threshold=0.9,
            top_k=3
        )
        
        result = query.to_dict()
        
        assert "query_embedding" in result
        assert result["threshold"] == 0.9
        assert result["top_k"] == 3
        assert result["metric"] == "cosine"


# ============================================================================
# TEST VECTORFILTER BASICS
# ============================================================================


class TestVectorFilterBasics:
    """Tests für VectorFilter Grundfunktionen"""
    
    def test_create_vector_filter(self, mock_chromadb_backend):
        """Test VectorFilter erstellen"""
        filter = VectorFilter(mock_chromadb_backend, "documents")
        
        assert filter.backend == mock_chromadb_backend
        assert filter.collection_name == "documents"
        assert filter.similarity_query is None
        assert len(filter.metadata_filters) == 0
    
    def test_create_vector_filter_factory(self, mock_chromadb_backend):
        """Test create_vector_filter factory"""
        filter = create_vector_filter(mock_chromadb_backend, "test")
        
        assert isinstance(filter, VectorFilter)
        assert filter.collection_name == "test"
    
    def test_vector_filter_default_collection(self, mock_chromadb_backend):
        """Test default collection name"""
        filter = VectorFilter(mock_chromadb_backend)
        
        assert filter.collection_name == "default"


# ============================================================================
# TEST SIMILARITY SEARCH
# ============================================================================


class TestSimilaritySearch:
    """Tests für Similarity Search Methods"""
    
    def test_by_similarity_basic(self, vector_filter, sample_embedding):
        """Test by_similarity basic"""
        result = vector_filter.by_similarity(
            query_embedding=sample_embedding,
            threshold=0.8,
            top_k=5
        )
        
        assert result == vector_filter  # Method chaining
        assert vector_filter.similarity_query is not None
        assert vector_filter.similarity_query.threshold == 0.8
        assert vector_filter.similarity_query.top_k == 5
        assert vector_filter.limit_value == 5  # Limit updated to match top_k
    
    def test_by_similarity_with_metric(self, vector_filter, sample_embedding):
        """Test by_similarity mit metric"""
        vector_filter.by_similarity(
            query_embedding=sample_embedding,
            metric="l2"
        )
        
        assert vector_filter.similarity_query.metric == "l2"
    
    def test_with_embedding_alias(self, vector_filter, sample_embedding):
        """Test with_embedding alias"""
        result = vector_filter.with_embedding(
            embedding=sample_embedding,
            min_similarity=0.85
        )
        
        assert result == vector_filter
        assert vector_filter.similarity_query.threshold == 0.85
    
    def test_similarity_search_defaults(self, vector_filter, sample_embedding):
        """Test similarity search defaults"""
        vector_filter.by_similarity(sample_embedding)
        
        assert vector_filter.similarity_query.threshold == 0.7
        assert vector_filter.similarity_query.top_k == 10
        assert vector_filter.similarity_query.metric == "cosine"


# ============================================================================
# TEST METADATA FILTERING
# ============================================================================


class TestMetadataFiltering:
    """Tests für Metadata Filtering Methods"""
    
    def test_by_metadata_basic(self, vector_filter):
        """Test by_metadata basic"""
        result = vector_filter.by_metadata("status", FilterOperator.EQ, "active")
        
        assert result == vector_filter  # Method chaining
        assert len(vector_filter.metadata_filters) == 1
        assert vector_filter.metadata_filters[0].field == "status"
        assert vector_filter.metadata_filters[0].value == "active"
    
    def test_by_metadata_string_operator(self, vector_filter):
        """Test by_metadata mit string operator"""
        vector_filter.by_metadata("priority", ">", 5)
        
        assert len(vector_filter.metadata_filters) == 1
        assert vector_filter.metadata_filters[0].operator == FilterOperator.GT
    
    def test_by_metadata_multiple(self, vector_filter):
        """Test multiple metadata filters"""
        vector_filter.by_metadata("status", FilterOperator.EQ, "active")
        vector_filter.by_metadata("priority", FilterOperator.GT, 5)
        
        assert len(vector_filter.metadata_filters) == 2
    
    def test_where_metadata_alias(self, vector_filter):
        """Test where_metadata alias"""
        result = vector_filter.where_metadata("status", "==", "active")
        
        assert result == vector_filter
        assert len(vector_filter.metadata_filters) == 1
    
    def test_metadata_operators(self, vector_filter):
        """Test verschiedene metadata operators"""
        # EQ
        vector_filter.by_metadata("field1", FilterOperator.EQ, "value1")
        # GT
        vector_filter.by_metadata("field2", FilterOperator.GT, 10)
        # IN
        vector_filter.by_metadata("field3", FilterOperator.IN, ["a", "b"])
        
        assert len(vector_filter.metadata_filters) == 3


# ============================================================================
# TEST COLLECTION FILTERING
# ============================================================================


class TestCollectionFiltering:
    """Tests für Collection Filtering Methods"""
    
    def test_by_collection(self, vector_filter):
        """Test by_collection"""
        result = vector_filter.by_collection("documents")
        
        assert result == vector_filter
        assert vector_filter.collection_name == "documents"
        assert "documents" in vector_filter.collection_filters
    
    def test_in_collection_alias(self, vector_filter):
        """Test in_collection alias"""
        result = vector_filter.in_collection("legal_docs")
        
        assert result == vector_filter
        assert vector_filter.collection_name == "legal_docs"
    
    def test_collection_override(self, vector_filter):
        """Test collection name override"""
        initial_collection = vector_filter.collection_name
        
        vector_filter.by_collection("new_collection")
        
        assert vector_filter.collection_name == "new_collection"
        assert vector_filter.collection_name != initial_collection


# ============================================================================
# TEST QUERY BUILDING
# ============================================================================


class TestQueryBuilding:
    """Tests für to_query() Method"""
    
    def test_to_query_basic(self, vector_filter):
        """Test to_query basic"""
        query = vector_filter.to_query()
        
        assert "collection_name" in query
        assert query["collection_name"] == "test_collection"
    
    def test_to_query_with_similarity(self, vector_filter, sample_embedding):
        """Test to_query mit similarity"""
        vector_filter.by_similarity(sample_embedding, threshold=0.8, top_k=5)
        
        query = vector_filter.to_query()
        
        assert "query_embeddings" in query
        assert query["query_embeddings"] == [sample_embedding]
        assert query["n_results"] == 5
    
    def test_to_query_with_metadata(self, vector_filter):
        """Test to_query mit metadata filters"""
        vector_filter.by_metadata("status", FilterOperator.EQ, "active")
        
        query = vector_filter.to_query()
        
        assert "where" in query
        assert "status" in query["where"]
    
    def test_to_query_combined(self, vector_filter, sample_embedding):
        """Test to_query mit combined filters"""
        vector_filter.by_similarity(sample_embedding, top_k=3)
        vector_filter.by_metadata("status", FilterOperator.EQ, "active")
        vector_filter.by_collection("documents")
        
        query = vector_filter.to_query()
        
        assert query["collection_name"] == "documents"
        assert "query_embeddings" in query
        assert "where" in query
        assert query["n_results"] == 3


# ============================================================================
# TEST WHERE CLAUSE BUILDING
# ============================================================================


class TestWhereClauseBuilding:
    """Tests für _build_where_clause()"""
    
    def test_build_where_single_filter(self, vector_filter):
        """Test where clause mit single filter"""
        vector_filter.by_metadata("status", FilterOperator.EQ, "active")
        
        where = vector_filter._build_where_clause()
        
        assert where is not None
        assert "status" in where
    
    def test_build_where_multiple_filters(self, vector_filter):
        """Test where clause mit multiple filters"""
        vector_filter.by_metadata("status", FilterOperator.EQ, "active")
        vector_filter.by_metadata("priority", FilterOperator.GT, 5)
        
        where = vector_filter._build_where_clause()
        
        assert where is not None
        assert "$and" in where
        assert len(where["$and"]) == 2
    
    def test_build_where_no_filters(self, vector_filter):
        """Test where clause ohne filters"""
        where = vector_filter._build_where_clause()
        
        assert where is None
    
    def test_condition_to_where_operators(self, vector_filter):
        """Test operator mapping in condition_to_where"""
        from uds3_query_filters import FilterCondition, LogicalOperator
        
        # EQ
        cond = FilterCondition("field", FilterOperator.EQ, "value")
        where = vector_filter._condition_to_where(cond)
        assert where == {"field": {"$eq": "value"}}
        
        # GT
        cond = FilterCondition("field", FilterOperator.GT, 10)
        where = vector_filter._condition_to_where(cond)
        assert where == {"field": {"$gt": 10}}
        
        # IN
        cond = FilterCondition("field", FilterOperator.IN, ["a", "b"])
        where = vector_filter._condition_to_where(cond)
        assert where == {"field": {"$in": ["a", "b"]}}


# ============================================================================
# TEST QUERY EXECUTION
# ============================================================================


class TestQueryExecution:
    """Tests für execute() Method"""
    
    def test_execute_basic(self, vector_filter, sample_embedding):
        """Test execute basic"""
        vector_filter.by_similarity(sample_embedding)
        
        result = vector_filter.execute()
        
        assert isinstance(result, VectorQueryResult)
        assert result.success is True
        assert len(result.results) > 0
    
    def test_execute_with_metadata(self, vector_filter, sample_embedding):
        """Test execute mit metadata filter"""
        vector_filter.by_similarity(sample_embedding)
        vector_filter.by_metadata("status", FilterOperator.EQ, "active")
        
        result = vector_filter.execute()
        
        assert result.success is True
        # Check that where clause was passed to backend
        vector_filter.backend.query_collection.assert_called_once()
        call_kwargs = vector_filter.backend.query_collection.call_args[1]
        assert "where" in call_kwargs
    
    def test_execute_without_backend(self):
        """Test execute ohne backend"""
        filter = VectorFilter(None)
        
        result = filter.execute()
        
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_execute_with_distances(self, vector_filter, sample_embedding):
        """Test execute returns distances"""
        vector_filter.by_similarity(sample_embedding)
        
        result = vector_filter.execute()
        
        assert result.distances is not None
        assert len(result.distances) > 0
    
    def test_execute_with_similarities(self, vector_filter, sample_embedding):
        """Test execute calculates similarities"""
        vector_filter.by_similarity(sample_embedding, metric="cosine")
        
        result = vector_filter.execute()
        
        assert result.similarities is not None
        assert len(result.similarities) > 0
        # Cosine similarity: 1 - distance
        assert result.similarities[0] == 1.0 - result.distances[0]
    
    def test_execute_collection_name(self, vector_filter, sample_embedding):
        """Test execute includes collection name"""
        vector_filter.by_collection("documents")
        vector_filter.by_similarity(sample_embedding)
        
        result = vector_filter.execute()
        
        assert result.collection == "documents"


# ============================================================================
# TEST COUNT
# ============================================================================


class TestCount:
    """Tests für count() Method"""
    
    def test_count_basic(self, vector_filter):
        """Test count basic"""
        count = vector_filter.count()
        
        assert count == 3  # Mock returns 3
    
    def test_count_without_backend(self):
        """Test count ohne backend"""
        filter = VectorFilter(None)
        
        count = filter.count()
        
        assert count == 0


# ============================================================================
# TEST COMBINED QUERIES
# ============================================================================


class TestCombinedQueries:
    """Tests für Combined Query Patterns"""
    
    def test_similarity_plus_metadata(self, vector_filter, sample_embedding):
        """Test similarity + metadata filter"""
        result = (vector_filter
                  .by_similarity(sample_embedding, threshold=0.8)
                  .by_metadata("status", FilterOperator.EQ, "active")
                  .execute())
        
        assert result.success is True
        assert vector_filter.similarity_query is not None
        assert len(vector_filter.metadata_filters) == 1
    
    def test_fluent_api_chaining(self, vector_filter, sample_embedding):
        """Test fluent API chaining"""
        result = (vector_filter
                  .by_collection("documents")
                  .by_similarity(sample_embedding, top_k=5)
                  .by_metadata("priority", FilterOperator.GT, 5)
                  .by_metadata("status", FilterOperator.NE, "deleted")
                  .execute())
        
        assert result.success is True
        assert vector_filter.collection_name == "documents"
        assert len(vector_filter.metadata_filters) == 2
    
    def test_complex_query(self, vector_filter, sample_embedding):
        """Test complex combined query"""
        filter = (vector_filter
                  .by_collection("legal_documents")
                  .with_embedding(sample_embedding, min_similarity=0.85)
                  .where_metadata("document_type", "==", "law")
                  .where_metadata("year", FilterOperator.GTE, 2020))
        
        query = filter.to_query()
        
        assert query["collection_name"] == "legal_documents"
        assert query["n_results"] == 10
        assert "where" in query
        assert len(filter.metadata_filters) == 2


# ============================================================================
# TEST INTEGRATION
# ============================================================================


class TestIntegration:
    """Integrationstests"""
    
    def test_full_workflow(self, mock_chromadb_backend, sample_embedding):
        """Test complete workflow"""
        # Create filter
        filter = create_vector_filter(mock_chromadb_backend, "documents")
        
        # Build query
        result = (filter
                  .by_similarity(sample_embedding, threshold=0.75, top_k=5)
                  .by_metadata("status", FilterOperator.EQ, "active")
                  .execute())
        
        # Verify
        assert result.success is True
        assert len(result.results) > 0
        assert result.collection == "documents"
        assert result.distances is not None
    
    def test_similarity_only(self, mock_chromadb_backend, sample_embedding):
        """Test similarity-only query"""
        filter = VectorFilter(mock_chromadb_backend)
        
        result = filter.by_similarity(sample_embedding).execute()
        
        assert result.success is True
    
    def test_metadata_only(self, mock_chromadb_backend):
        """Test metadata-only query"""
        filter = VectorFilter(mock_chromadb_backend)
        
        # Note: Metadata-only queries need similarity for vector DB
        # So we add a dummy embedding
        dummy_embedding = [0.0] * 384
        result = (filter
                  .by_similarity(dummy_embedding)
                  .by_metadata("status", FilterOperator.EQ, "active")
                  .execute())
        
        assert result.success is True


# ============================================================================
# TEST EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Tests für Edge Cases"""
    
    def test_empty_embedding(self, vector_filter):
        """Test mit empty embedding"""
        empty_embedding = []
        
        result = vector_filter.by_similarity(empty_embedding)
        
        assert result.similarity_query.query_embedding == []
    
    def test_very_high_threshold(self, vector_filter, sample_embedding):
        """Test mit sehr hohem threshold"""
        vector_filter.by_similarity(sample_embedding, threshold=0.99)
        
        assert vector_filter.similarity_query.threshold == 0.99
    
    def test_zero_top_k(self, vector_filter, sample_embedding):
        """Test mit top_k=0"""
        vector_filter.by_similarity(sample_embedding, top_k=0)
        
        assert vector_filter.similarity_query.top_k == 0
    
    def test_large_top_k(self, vector_filter, sample_embedding):
        """Test mit large top_k"""
        vector_filter.by_similarity(sample_embedding, top_k=1000)
        
        assert vector_filter.limit_value == 1000


# ============================================================================
# RUN TESTS
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
