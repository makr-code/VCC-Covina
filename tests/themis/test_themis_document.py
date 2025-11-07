"""
Unit Tests: ThemisDocumentBackend
==================================

Tests for document storage operations:
- store_document() - Store full documents
- get_document() - Retrieve documents
- store_blob() - Binary content storage
- get_chunks() - Retrieve document chunks
- MIME type handling
- Metadata management
"""

import pytest
from typing import Dict, Any
import base64

from database.themis_document import ThemisDocumentBackend
from database.themis_exceptions import ThemisNotFoundError, ThemisValidationError
from tests.themis.conftest import (
    create_success_response,
    create_error_response,
    MockAsyncClient,
)


class TestDocumentStorage:
    """Test document storage operations"""
    
    @pytest.mark.asyncio
    async def test_store_document_success(self, mock_http_client, sample_document_data):
        """Test: store_document() stores full document"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/documents",
            create_success_response({"id": "doc_123", "stored": True})
        )
        
        result = await backend.store_document(
            document_id="doc_123",
            content=sample_document_data["content"],
            metadata=sample_document_data["metadata"]
        )
        
        assert result["id"] == "doc_123"
        assert result["stored"] is True
    
    @pytest.mark.asyncio
    async def test_get_document_success(self, mock_http_client, sample_document_data):
        """Test: get_document() retrieves full document"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/content/documents/doc_123",
            create_success_response(sample_document_data)
        )
        
        result = await backend.get_document("doc_123")
        
        assert result["id"] == "doc_123"
        assert result["content"] == sample_document_data["content"]
        assert result["metadata"]["filename"] == "test.txt"
    
    @pytest.mark.asyncio
    async def test_get_document_not_found(self, mock_http_client):
        """Test: get_document() raises NotFoundError"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/content/documents/missing_doc",
            create_error_response(404, "Document not found")
        )
        
        with pytest.raises(ThemisNotFoundError):
            await backend.get_document("missing_doc")
    
    @pytest.mark.asyncio
    async def test_update_document_content(self, mock_http_client):
        """Test: update_document() updates content"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        new_content = "Updated document content"
        
        mock_http_client.set_response(
            "PUT",
            "http://localhost:8765/content/documents/doc_123",
            create_success_response({"id": "doc_123", "updated": True})
        )
        
        result = await backend.update_document("doc_123", content=new_content)
        
        assert result["updated"] is True
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self, mock_http_client):
        """Test: delete_document() removes document"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/content/documents/doc_123",
            create_success_response({"deleted": True})
        )
        
        result = await backend.delete_document("doc_123")
        
        assert result["deleted"] is True


class TestBlobStorage:
    """Test binary blob storage"""
    
    @pytest.mark.asyncio
    async def test_store_blob_success(self, mock_http_client):
        """Test: store_blob() stores binary data"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        binary_data = b"Binary PDF content..."
        blob_id = "blob_pdf_123"
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/blobs",
            create_success_response({"id": blob_id, "stored": True, "size": len(binary_data)})
        )
        
        result = await backend.store_blob(
            blob_id=blob_id,
            data=binary_data,
            mime_type="application/pdf"
        )
        
        assert result["stored"] is True
        assert result["size"] == len(binary_data)
    
    @pytest.mark.asyncio
    async def test_get_blob_success(self, mock_http_client):
        """Test: get_blob() retrieves binary data"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        binary_data = b"Binary content"
        encoded_data = base64.b64encode(binary_data).decode()
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/content/blobs/blob_123",
            create_success_response({
                "id": "blob_123",
                "data": encoded_data,
                "mime_type": "application/pdf"
            })
        )
        
        result = await backend.get_blob("blob_123")
        
        assert result["id"] == "blob_123"
        assert result["mime_type"] == "application/pdf"
    
    @pytest.mark.asyncio
    async def test_store_blob_with_large_file(self, mock_http_client):
        """Test: store_blob() handles large files"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        # Simulate 10MB file
        large_data = b"X" * (10 * 1024 * 1024)
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/blobs",
            create_success_response({"id": "blob_large", "stored": True, "size": len(large_data)})
        )
        
        result = await backend.store_blob(
            blob_id="blob_large",
            data=large_data,
            mime_type="application/octet-stream"
        )
        
        assert result["stored"] is True
        assert result["size"] == 10 * 1024 * 1024


class TestChunkOperations:
    """Test document chunk operations"""
    
    @pytest.mark.asyncio
    async def test_store_chunks_success(self, mock_http_client):
        """Test: store_chunks() stores document chunks"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        chunks = [
            {"index": 0, "text": "First chunk", "start": 0, "end": 100},
            {"index": 1, "text": "Second chunk", "start": 100, "end": 200},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/documents/doc_123/chunks",
            create_success_response({"document_id": "doc_123", "chunks_stored": 2})
        )
        
        result = await backend.store_chunks("doc_123", chunks)
        
        assert result["chunks_stored"] == 2
    
    @pytest.mark.asyncio
    async def test_get_chunks_success(self, mock_http_client):
        """Test: get_chunks() retrieves document chunks"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        mock_chunks = [
            {"index": 0, "text": "First chunk"},
            {"index": 1, "text": "Second chunk"},
            {"index": 2, "text": "Third chunk"},
        ]
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/content/documents/doc_123/chunks",
            create_success_response({"chunks": mock_chunks, "count": 3})
        )
        
        result = await backend.get_chunks("doc_123")
        
        assert len(result) == 3
        assert result[0]["text"] == "First chunk"
    
    @pytest.mark.asyncio
    async def test_get_chunk_by_index(self, mock_http_client):
        """Test: get_chunk() retrieves specific chunk"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        mock_chunk = {"index": 5, "text": "Specific chunk"}
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/content/documents/doc_123/chunks/5",
            create_success_response(mock_chunk)
        )
        
        result = await backend.get_chunk("doc_123", chunk_index=5)
        
        assert result["index"] == 5
        assert result["text"] == "Specific chunk"


class TestMIMETypeHandling:
    """Test MIME type operations"""
    
    @pytest.mark.asyncio
    async def test_store_document_with_mime_type(self, mock_http_client):
        """Test: store_document() stores MIME type"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/documents",
            create_success_response({"id": "doc_pdf", "stored": True})
        )
        
        result = await backend.store_document(
            document_id="doc_pdf",
            content="PDF content",
            metadata={"mime_type": "application/pdf"}
        )
        
        # Check MIME type was sent in request
        request = mock_http_client.requests[-1]
        assert "metadata" in request["kwargs"]["json"]
    
    @pytest.mark.asyncio
    async def test_detect_mime_type_from_filename(self):
        """Test: _detect_mime_type() from filename"""
        backend = ThemisDocumentBackend(MockAsyncClient(), "http://localhost:8765")
        
        mime_pdf = backend._detect_mime_type("document.pdf")
        assert mime_pdf == "application/pdf"
        
        mime_txt = backend._detect_mime_type("readme.txt")
        assert mime_txt == "text/plain"
        
        mime_json = backend._detect_mime_type("data.json")
        assert mime_json == "application/json"
    
    @pytest.mark.asyncio
    async def test_get_supported_mime_types(self):
        """Test: get_supported_mime_types() returns list"""
        backend = ThemisDocumentBackend(MockAsyncClient(), "http://localhost:8765")
        
        supported = backend.get_supported_mime_types()
        
        assert "application/pdf" in supported
        assert "text/plain" in supported
        assert "application/json" in supported
        assert "image/png" in supported


class TestMetadataOperations:
    """Test metadata management"""
    
    @pytest.mark.asyncio
    async def test_store_document_with_metadata(self, mock_http_client):
        """Test: store_document() stores rich metadata"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        metadata = {
            "filename": "report.pdf",
            "author": "John Doe",
            "created_at": "2025-11-07T12:00:00Z",
            "tags": ["report", "financial", "2025"],
            "size": 1024000,
        }
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/documents",
            create_success_response({"id": "doc_report", "stored": True})
        )
        
        result = await backend.store_document(
            document_id="doc_report",
            content="Report content",
            metadata=metadata
        )
        
        assert result["stored"] is True
    
    @pytest.mark.asyncio
    async def test_update_metadata_only(self, mock_http_client):
        """Test: update_metadata() updates metadata without content"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        new_metadata = {"tags": ["updated", "reviewed"], "status": "approved"}
        
        mock_http_client.set_response(
            "PATCH",
            "http://localhost:8765/content/documents/doc_123/metadata",
            create_success_response({"updated": True})
        )
        
        result = await backend.update_metadata("doc_123", new_metadata)
        
        assert result["updated"] is True
    
    @pytest.mark.asyncio
    async def test_get_metadata_only(self, mock_http_client):
        """Test: get_metadata() retrieves metadata without content"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        mock_metadata = {
            "filename": "test.txt",
            "size": 1024,
            "created_at": "2025-11-07T12:00:00Z"
        }
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/content/documents/doc_123/metadata",
            create_success_response(mock_metadata)
        )
        
        result = await backend.get_metadata("doc_123")
        
        assert result["filename"] == "test.txt"
        assert result["size"] == 1024


class TestSearchOperations:
    """Test document search"""
    
    @pytest.mark.asyncio
    async def test_search_documents_by_metadata(self, mock_http_client):
        """Test: search_documents() filters by metadata"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        filters = {"mime_type": "application/pdf", "tags": ["financial"]}
        
        mock_results = [
            {"id": "doc_1", "filename": "report1.pdf"},
            {"id": "doc_2", "filename": "report2.pdf"},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/documents/search",
            create_success_response({"results": mock_results, "count": 2})
        )
        
        result = await backend.search_documents(filters)
        
        assert len(result) == 2
        assert result[0]["filename"] == "report1.pdf"
    
    @pytest.mark.asyncio
    async def test_search_documents_full_text(self, mock_http_client):
        """Test: search_documents() supports full-text search"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        query = "financial report 2025"
        
        mock_results = [
            {"id": "doc_1", "snippet": "...financial report for 2025..."},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/documents/search",
            create_success_response({"results": mock_results, "count": 1})
        )
        
        result = await backend.search_documents({"query": query})
        
        assert len(result) == 1
        assert "financial" in result[0]["snippet"]


class TestBatchOperations:
    """Test batch document operations"""
    
    @pytest.mark.asyncio
    async def test_batch_store_documents(self, mock_http_client):
        """Test: batch_store() stores multiple documents"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        documents = [
            {"id": "doc_1", "content": "Content 1", "metadata": {}},
            {"id": "doc_2", "content": "Content 2", "metadata": {}},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/content/documents/batch",
            create_success_response({"stored": 2, "ids": ["doc_1", "doc_2"]})
        )
        
        result = await backend.batch_store(documents)
        
        assert result["stored"] == 2
    
    @pytest.mark.asyncio
    async def test_batch_delete_documents(self, mock_http_client):
        """Test: batch_delete() removes multiple documents"""
        backend = ThemisDocumentBackend(mock_http_client, "http://localhost:8765")
        
        doc_ids = ["doc_1", "doc_2", "doc_3"]
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/content/documents/batch",
            create_success_response({"deleted": 3})
        )
        
        result = await backend.batch_delete(doc_ids)
        
        assert result["deleted"] == 3


# Run tests with: pytest tests/themis/test_themis_document.py -v
