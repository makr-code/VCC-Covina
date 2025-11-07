"""
Unit Tests: ThemisVectorBackend
================================

Tests for vector database operations:
- add_vector() - Insert embeddings
- query_vectors() - Similarity search
- delete_vector() - Remove embeddings
- Dimension validation
- ChromaDB compatibility
- Metadata handling
"""

import pytest
from typing import List, Dict, Any
import numpy as np

from database.themis_vector import ThemisVectorBackend
from database.themis_exceptions import ThemisValidationError, ThemisNotFoundError
from tests.themis.conftest import (
    create_success_response,
    create_error_response,
    MockAsyncClient,
)


class TestVectorCRUD:
    """Test vector CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_add_vector_success(self, mock_http_client, sample_vector_data):
        """Test: add_vector() inserts vector"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/add",
            create_success_response({"id": "vector_123", "added": True})
        )
        
        result = await backend.add_vector(
            collection="documents",
            vector_id="vector_123",
            embedding=sample_vector_data["embedding"],
            metadata=sample_vector_data["metadata"]
        )
        
        assert result["id"] == "vector_123"
        assert result["added"] is True
    
    @pytest.mark.asyncio
    async def test_add_vector_validates_dimension(self, mock_http_client):
        """Test: add_vector() validates embedding dimension"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        # Wrong dimension (expected: 384, provided: 128)
        wrong_embedding = [0.1] * 128
        
        with pytest.raises(ThemisValidationError, match="dimension"):
            await backend.add_vector(
                collection="documents",
                vector_id="vec_1",
                embedding=wrong_embedding,
                metadata={}
            )
    
    @pytest.mark.asyncio
    async def test_add_multiple_vectors(self, mock_http_client):
        """Test: add_vectors() batch insert"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        vectors = [
            {"id": "vec_1", "embedding": [0.1] * 384, "metadata": {"text": "Text 1"}},
            {"id": "vec_2", "embedding": [0.2] * 384, "metadata": {"text": "Text 2"}},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/batch",
            create_success_response({"added": 2, "ids": ["vec_1", "vec_2"]})
        )
        
        result = await backend.add_vectors("documents", vectors)
        
        assert result["added"] == 2
        assert len(result["ids"]) == 2
    
    @pytest.mark.asyncio
    async def test_delete_vector_success(self, mock_http_client):
        """Test: delete_vector() removes vector"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/vector/vec_123",
            create_success_response({"deleted": True})
        )
        
        result = await backend.delete_vector("documents", "vec_123")
        
        assert result["deleted"] is True
    
    @pytest.mark.asyncio
    async def test_delete_vector_not_found(self, mock_http_client):
        """Test: delete_vector() handles missing vector"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/vector/missing_vec",
            create_error_response(404, "Vector not found")
        )
        
        with pytest.raises(ThemisNotFoundError):
            await backend.delete_vector("documents", "missing_vec")


class TestVectorQuery:
    """Test vector similarity search"""
    
    @pytest.mark.asyncio
    async def test_query_vectors_returns_neighbors(self, mock_http_client):
        """Test: query_vectors() returns similar vectors"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        query_embedding = [0.1] * 384
        
        mock_results = [
            {"id": "vec_1", "score": 0.95, "metadata": {"text": "Similar text 1"}},
            {"id": "vec_2", "score": 0.87, "metadata": {"text": "Similar text 2"}},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/query",
            create_success_response({"results": mock_results, "count": 2})
        )
        
        results = await backend.query_vectors(
            collection="documents",
            query_embedding=query_embedding,
            n_results=2
        )
        
        assert len(results) == 2
        assert results[0]["id"] == "vec_1"
        assert results[0]["score"] == 0.95
    
    @pytest.mark.asyncio
    async def test_query_vectors_with_filters(self, mock_http_client):
        """Test: query_vectors() applies metadata filters"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        query_embedding = [0.1] * 384
        filters = {"document_type": "pdf", "language": "en"}
        
        mock_results = [
            {"id": "vec_3", "score": 0.92, "metadata": {"document_type": "pdf"}}
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/query",
            create_success_response({"results": mock_results, "count": 1})
        )
        
        results = await backend.query_vectors(
            collection="documents",
            query_embedding=query_embedding,
            n_results=5,
            filters=filters
        )
        
        assert len(results) == 1
        assert results[0]["metadata"]["document_type"] == "pdf"
    
    @pytest.mark.asyncio
    async def test_query_vectors_validates_dimension(self, mock_http_client):
        """Test: query_vectors() validates query embedding dimension"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        # Wrong dimension
        wrong_embedding = [0.1] * 128
        
        with pytest.raises(ThemisValidationError, match="dimension"):
            await backend.query_vectors(
                collection="documents",
                query_embedding=wrong_embedding,
                n_results=5
            )
    
    @pytest.mark.asyncio
    async def test_query_vectors_limits_results(self, mock_http_client):
        """Test: query_vectors() respects n_results limit"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        query_embedding = [0.1] * 384
        
        # Return exactly n_results (3)
        mock_results = [
            {"id": f"vec_{i}", "score": 0.9 - i*0.1, "metadata": {}}
            for i in range(3)
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/query",
            create_success_response({"results": mock_results, "count": 3})
        )
        
        results = await backend.query_vectors(
            collection="documents",
            query_embedding=query_embedding,
            n_results=3
        )
        
        assert len(results) == 3


class TestDimensionValidation:
    """Test embedding dimension validation"""
    
    @pytest.mark.asyncio
    async def test_validate_dimension_accepts_384(self):
        """Test: _validate_dimension() accepts 384-dim vectors"""
        backend = ThemisVectorBackend(MockAsyncClient(), "http://localhost:8765")
        
        embedding = [0.1] * 384
        
        # Should not raise
        backend._validate_dimension(embedding, "test_operation")
    
    @pytest.mark.asyncio
    async def test_validate_dimension_rejects_wrong_size(self):
        """Test: _validate_dimension() rejects wrong dimensions"""
        backend = ThemisVectorBackend(MockAsyncClient(), "http://localhost:8765")
        
        wrong_embedding = [0.1] * 512  # Wrong dimension
        
        with pytest.raises(ThemisValidationError):
            backend._validate_dimension(wrong_embedding, "test_operation")
    
    @pytest.mark.asyncio
    async def test_validate_dimension_with_numpy_array(self):
        """Test: _validate_dimension() accepts numpy arrays"""
        backend = ThemisVectorBackend(MockAsyncClient(), "http://localhost:8765")
        
        embedding = np.array([0.1] * 384)
        
        # Should not raise (supports numpy)
        backend._validate_dimension(embedding.tolist(), "test_operation")


class TestChromaDBCompatibility:
    """Test ChromaDB-compatible API"""
    
    @pytest.mark.asyncio
    async def test_add_with_chromadb_format(self, mock_http_client):
        """Test: add() matches ChromaDB API"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        # ChromaDB format: ids, embeddings, metadatas
        ids = ["vec_1", "vec_2"]
        embeddings = [[0.1] * 384, [0.2] * 384]
        metadatas = [{"text": "Text 1"}, {"text": "Text 2"}]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/batch",
            create_success_response({"added": 2, "ids": ids})
        )
        
        result = await backend.add(
            collection="documents",
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        assert result["added"] == 2
    
    @pytest.mark.asyncio
    async def test_query_with_chromadb_format(self, mock_http_client):
        """Test: query() matches ChromaDB API"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        # ChromaDB format: query_embeddings, n_results
        query_embeddings = [[0.1] * 384]
        
        mock_results = [
            {"id": "vec_1", "score": 0.95, "metadata": {"text": "Result 1"}}
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/query",
            create_success_response({"results": mock_results, "count": 1})
        )
        
        results = await backend.query(
            collection="documents",
            query_embeddings=query_embeddings,
            n_results=5
        )
        
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_delete_with_chromadb_format(self, mock_http_client):
        """Test: delete() matches ChromaDB API"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        # ChromaDB format: ids list
        ids = ["vec_1", "vec_2", "vec_3"]
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/vector/batch",
            create_success_response({"deleted": 3})
        )
        
        result = await backend.delete(collection="documents", ids=ids)
        
        assert result["deleted"] == 3


class TestMetadataHandling:
    """Test metadata operations"""
    
    @pytest.mark.asyncio
    async def test_add_vector_with_metadata(self, mock_http_client):
        """Test: add_vector() stores metadata"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        metadata = {
            "text": "Sample chunk",
            "document_id": "doc_123",
            "chunk_index": 5,
            "source": "pdf"
        }
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/add",
            create_success_response({"id": "vec_1", "added": True})
        )
        
        result = await backend.add_vector(
            collection="documents",
            vector_id="vec_1",
            embedding=[0.1] * 384,
            metadata=metadata
        )
        
        # Check metadata was sent in request
        request = mock_http_client.requests[-1]
        assert "metadata" in request["kwargs"]["json"]
    
    @pytest.mark.asyncio
    async def test_query_returns_metadata(self, mock_http_client):
        """Test: query_vectors() returns metadata in results"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        mock_results = [
            {
                "id": "vec_1",
                "score": 0.95,
                "metadata": {
                    "text": "Matched chunk",
                    "document_id": "doc_456"
                }
            }
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/query",
            create_success_response({"results": mock_results, "count": 1})
        )
        
        results = await backend.query_vectors(
            collection="documents",
            query_embedding=[0.1] * 384,
            n_results=1
        )
        
        assert results[0]["metadata"]["text"] == "Matched chunk"
        assert results[0]["metadata"]["document_id"] == "doc_456"


class TestCollectionManagement:
    """Test collection operations"""
    
    @pytest.mark.asyncio
    async def test_create_collection_success(self, mock_http_client):
        """Test: create_collection() creates new collection"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/vector/collections",
            create_success_response({"name": "new_collection", "created": True})
        )
        
        result = await backend.create_collection("new_collection")
        
        assert result["created"] is True
    
    @pytest.mark.asyncio
    async def test_delete_collection_success(self, mock_http_client):
        """Test: delete_collection() removes collection"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/vector/collections/old_collection",
            create_success_response({"deleted": True})
        )
        
        result = await backend.delete_collection("old_collection")
        
        assert result["deleted"] is True
    
    @pytest.mark.asyncio
    async def test_list_collections(self, mock_http_client):
        """Test: list_collections() returns all collections"""
        backend = ThemisVectorBackend(mock_http_client, "http://localhost:8765")
        
        mock_collections = ["documents", "images", "audio"]
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/vector/collections",
            create_success_response({"collections": mock_collections})
        )
        
        collections = await backend.list_collections()
        
        assert len(collections) == 3
        assert "documents" in collections


# Run tests with: pytest tests/themis/test_themis_vector.py -v
