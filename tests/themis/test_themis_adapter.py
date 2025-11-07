"""
Unit Tests: ThemisAdapter Core
================================

Tests for core adapter functionality:
- Connection management & pooling
- Retry logic & error handling
- Transaction support
- Health checks & statistics
- Lifecycle management (startup/shutdown)
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from database.themis_adapter import ThemisAdapter
from database.themis_exceptions import (
    ThemisConnectionError,
    ThemisTimeoutError,
    ThemisAuthenticationError,
    ThemisNotFoundError,
    ThemisValidationError,
)
from tests.themis.conftest import (
    create_success_response,
    create_error_response,
    MockAsyncClient,
)


class TestThemisAdapterInitialization:
    """Test adapter initialization and configuration"""
    
    @pytest.mark.asyncio
    async def test_init_with_default_config(self):
        """Test: Initialize adapter with default config"""
        adapter = ThemisAdapter(
            base_url="http://localhost:8765",
            timeout=30,
            max_retries=3
        )
        
        assert adapter.base_url == "http://localhost:8765"
        assert adapter.timeout == 30
        assert adapter.max_retries == 3
        assert adapter._client is None  # Not initialized yet
    
    @pytest.mark.asyncio
    async def test_init_with_custom_config(self, mock_themis_config):
        """Test: Initialize adapter with custom config"""
        adapter = ThemisAdapter(
            base_url=mock_themis_config["THEMIS_URL"],
            timeout=60,
            max_retries=5
        )
        
        assert adapter.timeout == 60
        assert adapter.max_retries == 5


class TestConnectionManagement:
    """Test connection lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_initialize_creates_client(self):
        """Test: initialize() creates HTTP client"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MockAsyncClient()
            mock_client_class.return_value = mock_client
            
            await adapter.initialize()
            
            assert adapter._client is not None
            mock_client_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_closes_client(self):
        """Test: close() closes HTTP client"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = MockAsyncClient()
        
        await adapter.close()
        
        assert adapter._client._closed is True
    
    @pytest.mark.asyncio
    async def test_close_without_client_does_not_error(self):
        """Test: close() without client doesn't error"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        
        # Should not raise
        await adapter.close()


class TestHealthChecks:
    """Test health check functionality"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_http_client):
        """Test: health_check() returns True when Themis responds"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/health",
            create_success_response({"status": "healthy"})
        )
        
        is_healthy = await adapter.health_check()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_http_client):
        """Test: health_check() returns False when Themis fails"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/health",
            create_error_response(503, "Service unavailable")
        )
        
        is_healthy = await adapter.health_check()
        
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_get_stats_returns_connection_info(self):
        """Test: get_stats() returns connection statistics"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        
        stats = await adapter.get_stats()
        
        assert "base_url" in stats
        assert stats["base_url"] == "http://localhost:8765"
        assert "timeout" in stats
        assert stats["timeout"] == 30
        assert "max_retries" in stats
        assert stats["max_retries"] == 3


class TestRetryLogic:
    """Test retry mechanism for failed requests"""
    
    @pytest.mark.asyncio
    async def test_request_retries_on_timeout(self, mock_http_client):
        """Test: _request() retries on timeout"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        # First 2 attempts timeout, 3rd succeeds
        call_count = 0
        original_request = mock_http_client.request
        
        async def mock_request_with_timeout(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Simulate timeout
                raise asyncio.TimeoutError()
            return await original_request(method, url, **kwargs)
        
        mock_http_client.request = mock_request_with_timeout
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/test",
            create_success_response({"result": "ok"})
        )
        
        # Should succeed after retries
        response = await adapter._request("GET", "/test")
        
        assert call_count == 3  # 2 failures + 1 success
        assert response.json()["result"] == "ok"
    
    @pytest.mark.asyncio
    async def test_request_fails_after_max_retries(self, mock_http_client):
        """Test: _request() fails after max retries"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 2)  # max_retries=2
        adapter._client = mock_http_client
        
        # All attempts timeout
        async def mock_request_timeout(method, url, **kwargs):
            raise asyncio.TimeoutError()
        
        mock_http_client.request = mock_request_timeout
        
        # Should raise ThemisTimeoutError after exhausting retries
        with pytest.raises(ThemisTimeoutError):
            await adapter._request("GET", "/test")


class TestErrorHandling:
    """Test error mapping and exception handling"""
    
    @pytest.mark.asyncio
    async def test_404_raises_not_found_error(self, mock_http_client):
        """Test: 404 response raises ThemisNotFoundError"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/entity/missing",
            create_error_response(404, "Entity not found")
        )
        
        with pytest.raises(ThemisNotFoundError):
            await adapter._request("GET", "/entity/missing")
    
    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, mock_http_client):
        """Test: 401 response raises ThemisAuthenticationError"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/entity/protected",
            create_error_response(401, "Unauthorized")
        )
        
        with pytest.raises(ThemisAuthenticationError):
            await adapter._request("GET", "/entity/protected")
    
    @pytest.mark.asyncio
    async def test_400_raises_validation_error(self, mock_http_client):
        """Test: 400 response raises ThemisValidationError"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/entity",
            create_error_response(400, "Invalid request")
        )
        
        with pytest.raises(ThemisValidationError):
            await adapter._request("POST", "/entity", json={})
    
    @pytest.mark.asyncio
    async def test_500_raises_connection_error(self, mock_http_client):
        """Test: 500 response raises ThemisConnectionError"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/entity/test",
            create_error_response(500, "Internal server error")
        )
        
        with pytest.raises(ThemisConnectionError):
            await adapter._request("GET", "/entity/test")


class TestTransactionSupport:
    """Test transaction lifecycle"""
    
    @pytest.mark.asyncio
    async def test_begin_transaction_returns_id(self, mock_http_client):
        """Test: begin_transaction() returns transaction ID"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/begin",
            create_success_response({"transaction_id": "txn_123"})
        )
        
        txn_id = await adapter.begin_transaction()
        
        assert txn_id == "txn_123"
    
    @pytest.mark.asyncio
    async def test_commit_transaction_success(self, mock_http_client):
        """Test: commit_transaction() succeeds"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/txn_123/commit",
            create_success_response({"status": "committed"})
        )
        
        # Should not raise
        await adapter.commit_transaction("txn_123")
    
    @pytest.mark.asyncio
    async def test_rollback_transaction_success(self, mock_http_client):
        """Test: rollback_transaction() succeeds"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/txn_123/rollback",
            create_success_response({"status": "rolled_back"})
        )
        
        # Should not raise
        await adapter.rollback_transaction("txn_123")
    
    @pytest.mark.asyncio
    async def test_transaction_context_manager_commits_on_success(self, mock_http_client):
        """Test: Transaction context manager commits on success"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        # Mock begin
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/begin",
            create_success_response({"transaction_id": "txn_456"})
        )
        
        # Mock commit
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/txn_456/commit",
            create_success_response({"status": "committed"})
        )
        
        # Use context manager
        async with adapter.transaction() as txn_id:
            assert txn_id == "txn_456"
        
        # Check commit was called
        commit_request = [r for r in mock_http_client.requests if "commit" in r["url"]]
        assert len(commit_request) == 1
    
    @pytest.mark.asyncio
    async def test_transaction_context_manager_rolls_back_on_error(self, mock_http_client):
        """Test: Transaction context manager rolls back on error"""
        adapter = ThemisAdapter("http://localhost:8765", 30, 3)
        adapter._client = mock_http_client
        
        # Mock begin
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/begin",
            create_success_response({"transaction_id": "txn_789"})
        )
        
        # Mock rollback
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/transaction/txn_789/rollback",
            create_success_response({"status": "rolled_back"})
        )
        
        # Use context manager with exception
        with pytest.raises(ValueError):
            async with adapter.transaction() as txn_id:
                raise ValueError("Test error")
        
        # Check rollback was called
        rollback_request = [r for r in mock_http_client.requests if "rollback" in r["url"]]
        assert len(rollback_request) == 1


# Run tests with: pytest tests/themis/test_themis_adapter.py -v
