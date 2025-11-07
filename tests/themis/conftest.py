"""
Pytest Configuration & Fixtures for Themis Adapter Tests
==========================================================

Provides:
- Mock HTTP client with request/response recording
- Common test data fixtures
- Async test support
- Environment configuration mocking
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

# Test Configuration
MOCK_THEMIS_URL = "http://localhost:8765"
MOCK_TIMEOUT = 30
MOCK_MAX_RETRIES = 3


class MockHTTPResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, status_code: int, json_data: Optional[Dict[str, Any]] = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
    
    def json(self) -> Dict[str, Any]:
        return self._json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=MagicMock(),
                response=self
            )


class MockAsyncClient:
    """Mock httpx.AsyncClient for testing"""
    
    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self.responses: Dict[str, MockHTTPResponse] = {}
        self.default_response = MockHTTPResponse(200, {"status": "ok"})
        self._closed = False
    
    def set_response(self, method: str, url: str, response: MockHTTPResponse):
        """Set a mock response for a specific method + URL"""
        key = f"{method.upper()}:{url}"
        self.responses[key] = response
    
    async def request(self, method: str, url: str, **kwargs) -> MockHTTPResponse:
        """Mock HTTP request"""
        # Record request
        self.requests.append({
            "method": method.upper(),
            "url": url,
            "kwargs": kwargs
        })
        
        # Return configured response or default
        key = f"{method.upper()}:{url}"
        return self.responses.get(key, self.default_response)
    
    async def get(self, url: str, **kwargs) -> MockHTTPResponse:
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> MockHTTPResponse:
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> MockHTTPResponse:
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> MockHTTPResponse:
        return await self.request("DELETE", url, **kwargs)
    
    async def aclose(self):
        """Mock close"""
        self._closed = True
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()


@pytest.fixture
def mock_http_client():
    """Fixture: Mock HTTP client"""
    return MockAsyncClient()


@pytest.fixture
def mock_themis_config():
    """Fixture: Mock Themis configuration"""
    return {
        "THEMIS_URL": MOCK_THEMIS_URL,
        "THEMIS_TIMEOUT": MOCK_TIMEOUT,
        "THEMIS_MAX_RETRIES": MOCK_MAX_RETRIES,
        "USE_THEMIS": True,
    }


@pytest.fixture
def sample_entity_data():
    """Fixture: Sample entity data for testing"""
    return {
        "id": "test_entity_123",
        "type": "document",
        "attributes": {
            "title": "Test Document",
            "content": "This is a test document.",
            "created_at": "2025-11-07T12:00:00Z",
        },
        "metadata": {
            "source": "test",
            "version": "1.0",
        }
    }


@pytest.fixture
def sample_vector_data():
    """Fixture: Sample vector data for testing"""
    return {
        "id": "vector_123",
        "embedding": [0.1] * 384,  # 384-dim vector
        "metadata": {
            "text": "Sample text chunk",
            "document_id": "doc_123",
        }
    }


@pytest.fixture
def sample_graph_data():
    """Fixture: Sample graph data for testing"""
    return {
        "nodes": [
            {"id": "node_1", "type": "Person", "properties": {"name": "Alice"}},
            {"id": "node_2", "type": "Company", "properties": {"name": "Acme Corp"}},
        ],
        "relationships": [
            {
                "from": "node_1",
                "to": "node_2",
                "type": "WORKS_AT",
                "properties": {"since": "2020-01-01"}
            }
        ]
    }


@pytest.fixture
def sample_document_data():
    """Fixture: Sample document data for testing"""
    return {
        "id": "doc_123",
        "content": "This is the full document content.",
        "mime_type": "text/plain",
        "metadata": {
            "filename": "test.txt",
            "size": 1024,
        }
    }


@pytest.fixture
def sample_transaction_data():
    """Fixture: Sample transaction data"""
    return {
        "transaction_id": "txn_abc123",
        "status": "active",
        "operations": [],
    }


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Async test marker
pytest_plugins = ('pytest_asyncio',)


def create_mock_response(status: int = 200, data: Optional[Dict] = None, text: str = "") -> MockHTTPResponse:
    """Helper: Create a mock HTTP response"""
    return MockHTTPResponse(status, data, text)


def create_success_response(data: Dict[str, Any]) -> MockHTTPResponse:
    """Helper: Create a successful response (200 OK)"""
    return MockHTTPResponse(200, data)


def create_error_response(status: int, error_message: str) -> MockHTTPResponse:
    """Helper: Create an error response"""
    return MockHTTPResponse(status, {"error": error_message})


# Export helpers
__all__ = [
    "mock_http_client",
    "mock_themis_config",
    "sample_entity_data",
    "sample_vector_data",
    "sample_graph_data",
    "sample_document_data",
    "sample_transaction_data",
    "MockHTTPResponse",
    "MockAsyncClient",
    "create_mock_response",
    "create_success_response",
    "create_error_response",
]
