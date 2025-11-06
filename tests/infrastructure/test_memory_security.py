"""
Tests for Memory Manager, JWT Auth, and Retry Logic

Tests:
- Memory monitoring and limits
- Memory leak detection
- JWT token creation and validation
- Retry logic with exponential backoff
- Request timeout middleware
"""
from __future__ import annotations

import pytest
import time
import asyncio
import jwt as pyjwt
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from ingestion.infrastructure.memory.memory_manager import MemoryManager, MemoryStats
from ingestion.infrastructure.security.jwt_auth import JWTAuth, JWTUser, configure_jwt_auth, get_current_user
from ingestion.infrastructure.resilience.retry_logic import (
    retry_with_backoff,
    calculate_backoff_delay,
    RetryExhaustedError,
    configure_timeout_middleware,
)


# Memory Manager Tests

def test_memory_manager_initialization():
    """Test MemoryManager initialization."""
    manager = MemoryManager(max_memory_mb=1024, warning_threshold=0.7, critical_threshold=0.9)
    
    assert manager.max_memory_mb == 1024
    assert manager.warning_threshold == 0.7
    assert manager.critical_threshold == 0.9


def test_memory_manager_get_stats():
    """Test getting current memory statistics."""
    manager = MemoryManager()
    stats = manager.get_current_stats()
    
    assert isinstance(stats, MemoryStats)
    assert stats.total_mb > 0
    assert stats.available_mb > 0
    assert stats.process_mb > 0
    assert 0 <= stats.percent <= 100


def test_memory_manager_availability():
    """Test memory availability check."""
    # Use realistic memory limit based on current system usage
    stats = MemoryManager().get_current_stats()
    current_process_mb = stats.process_mb
    
    # Set limit well above current usage
    manager = MemoryManager(max_memory_mb=current_process_mb + 1000)
    
    # Small allocation should be available
    assert manager.is_memory_available(10) is True
    
    # Huge allocation should not be available
    assert manager.is_memory_available(999999) is False


def test_memory_manager_cleanup_callback():
    """Test cleanup callback registration and execution."""
    manager = MemoryManager()
    
    cleanup_called = []
    
    def cleanup_callback():
        cleanup_called.append(True)
    
    manager.register_cleanup_callback(cleanup_callback)
    manager.force_cleanup()
    
    assert len(cleanup_called) == 1


def test_memory_manager_leak_detection():
    """Test memory leak detection."""
    manager = MemoryManager()
    
    # Add fake stats showing growth
    for i in range(15):
        stats = manager.get_current_stats()
        stats.process_mb = 100 + (i * 20)  # Simulate 20MB growth per sample
        manager._stats_history.append(stats)
    
    # Should detect leak (200MB growth over 10 samples)
    assert manager.detect_leak(growth_threshold_mb=100, window_size=10) is True


# JWT Auth Tests

def test_jwt_create_and_verify():
    """Test JWT token creation and verification."""
    jwt_auth = JWTAuth(secret_key="test-secret-key")
    
    token = jwt_auth.create_token(
        user_id="user123",
        email="user@example.com",
        roles=["admin", "user"]
    )
    
    user = jwt_auth.verify_token(token)
    
    assert user.sub == "user123"
    assert user.email == "user@example.com"
    assert "admin" in user.roles
    assert user.exp is not None


def test_jwt_expired_token():
    """Test JWT token expiration."""
    jwt_auth = JWTAuth(secret_key="test-secret-key")
    
    # Create token that expires immediately
    token = jwt_auth.create_token(
        user_id="user123",
        expires_delta=timedelta(seconds=-1)  # Negative = already expired
    )
    
    with pytest.raises(Exception) as exc_info:
        jwt_auth.verify_token(token)
    
    assert exc_info.value.status_code == 401


def test_jwt_invalid_token():
    """Test JWT invalid token handling."""
    jwt_auth = JWTAuth(secret_key="test-secret-key")
    
    with pytest.raises(Exception) as exc_info:
        jwt_auth.verify_token("invalid-token")
    
    assert exc_info.value.status_code == 401


def test_jwt_role_verification():
    """Test JWT role verification."""
    jwt_auth = JWTAuth(secret_key="test-secret-key")
    
    token = jwt_auth.create_token(user_id="user123", roles=["user"])
    user = jwt_auth.verify_token(token)
    
    assert jwt_auth.verify_role(user, "user") is True
    assert jwt_auth.verify_role(user, "admin") is False


def test_jwt_fastapi_integration():
    """Test JWT with FastAPI."""
    configure_jwt_auth(secret_key="test-secret")
    
    app = FastAPI()
    
    @app.get("/protected")
    async def protected(user: JWTUser = Depends(get_current_user)):
        return {"user_id": user.sub}
    
    client = TestClient(app)
    
    # Create token
    jwt_auth = JWTAuth(secret_key="test-secret")
    token = jwt_auth.create_token(user_id="user123")
    
    # Request with token
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user123"
    
    # Request without token
    response = client.get("/protected")
    assert response.status_code == 403  # Forbidden


# Retry Logic Tests

def test_calculate_backoff_delay():
    """Test exponential backoff calculation."""
    # First attempt (0): base_delay
    delay0 = calculate_backoff_delay(0, base_delay=1.0, jitter=False)
    assert delay0 == 1.0
    
    # Second attempt (1): base_delay * 2
    delay1 = calculate_backoff_delay(1, base_delay=1.0, exponential_base=2.0, jitter=False)
    assert delay1 == 2.0
    
    # Third attempt (2): base_delay * 4
    delay2 = calculate_backoff_delay(2, base_delay=1.0, exponential_base=2.0, jitter=False)
    assert delay2 == 4.0
    
    # Max delay respected
    delay_max = calculate_backoff_delay(10, base_delay=1.0, max_delay=5.0, jitter=False)
    assert delay_max == 5.0


@pytest.mark.asyncio
async def test_retry_success_async():
    """Test async retry with eventual success."""
    attempts = []
    
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    async def flaky_operation():
        attempts.append(1)
        if len(attempts) < 2:
            raise ValueError("Temporary failure")
        return "success"
    
    result = await flaky_operation()
    
    assert result == "success"
    assert len(attempts) == 2  # Failed once, succeeded on second attempt


@pytest.mark.asyncio
async def test_retry_exhausted_async():
    """Test async retry exhaustion."""
    @retry_with_backoff(max_retries=2, base_delay=0.1)
    async def always_fails():
        raise ValueError("Always fails")
    
    with pytest.raises(RetryExhaustedError):
        await always_fails()


def test_retry_success_sync():
    """Test sync retry with eventual success."""
    attempts = []
    
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    def flaky_operation():
        attempts.append(1)
        if len(attempts) < 2:
            raise ValueError("Temporary failure")
        return "success"
    
    result = flaky_operation()
    
    assert result == "success"
    assert len(attempts) == 2


def test_retry_selective():
    """Test retry only on specific exceptions."""
    attempts = []
    
    @retry_with_backoff(max_retries=3, base_delay=0.1, retry_on=(ValueError,))
    def selective_retry():
        attempts.append(1)
        if len(attempts) == 1:
            raise ValueError("Retry this")
        raise TypeError("Don't retry this")
    
    with pytest.raises(TypeError):
        selective_retry()
    
    assert len(attempts) == 2  # Retried ValueError, then raised TypeError


@pytest.mark.asyncio
async def test_timeout_middleware():
    """Test request timeout middleware."""
    app = FastAPI()
    configure_timeout_middleware(app, timeout_seconds=0.5)
    
    @app.get("/fast")
    async def fast_endpoint():
        return {"status": "ok"}
    
    @app.get("/slow")
    async def slow_endpoint():
        await asyncio.sleep(1.0)  # Longer than timeout
        return {"status": "ok"}
    
    client = TestClient(app)
    
    # Fast endpoint should work
    response = client.get("/fast")
    assert response.status_code == 200
    
    # Slow endpoint should timeout
    response = client.get("/slow")
    assert response.status_code == 504  # Gateway Timeout
    assert "timed out" in response.json()["detail"].lower()
