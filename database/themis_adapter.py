"""
Themis Database Adapter - Core Infrastructure

Main adapter class providing UDS3-compatible interface to Themis DB via HTTP API.
Supports all 4 backend types: Relational, Vector, Graph, Document.

Author: VCC Covina Team
Created: 2025-11-07
Version: 1.0.0
"""

import httpx
import logging
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class ThemisConfig:
    """
    Themis Connection Configuration
    
    Attributes:
        url: Themis server base URL (default: http://localhost:8765)
        timeout: HTTP request timeout in seconds (default: 30)
        max_retries: Maximum retry attempts for failed requests (default: 3)
        pool_size: HTTP connection pool size (default: 100)
        auth_token: Optional authentication token
        retry_backoff_factor: Exponential backoff factor (default: 2.0)
        retry_statuses: HTTP status codes to retry (default: 500, 502, 503, 504)
    """
    url: str = "http://localhost:8765"
    timeout: int = 30
    max_retries: int = 3
    pool_size: int = 100
    auth_token: Optional[str] = None
    retry_backoff_factor: float = 2.0
    retry_statuses: tuple = field(default_factory=lambda: (500, 502, 503, 504))
    
    @classmethod
    def from_env(cls) -> 'ThemisConfig':
        """Create configuration from environment variables"""
        import os
        return cls(
            url=os.getenv("THEMIS_URL", "http://localhost:8765"),
            timeout=int(os.getenv("THEMIS_TIMEOUT", "30")),
            max_retries=int(os.getenv("THEMIS_MAX_RETRIES", "3")),
            pool_size=int(os.getenv("THEMIS_POOL_SIZE", "100")),
            auth_token=os.getenv("THEMIS_AUTH_TOKEN")
        )


class ThemisAdapter:
    """
    Main Themis Database Adapter
    
    Provides UDS3-compatible interface to Themis DB via HTTP API.
    Supports all 4 backend types: Relational, Vector, Graph, Document.
    
    Usage:
        config = ThemisConfig(url="http://localhost:8765")
        adapter = ThemisAdapter(config)
        
        relational = adapter.get_relational_backend()
        results = await relational.execute_query("SELECT * FROM users")
        
        await adapter.close()
    """
    
    def __init__(self, config: Optional[ThemisConfig] = None):
        """
        Initialize Themis adapter
        
        Args:
            config: Themis configuration (uses defaults if not provided)
        """
        self.config = config or ThemisConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # HTTP Client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.config.url,
            timeout=self.config.timeout,
            limits=httpx.Limits(
                max_connections=self.config.pool_size,
                max_keepalive_connections=20
            ),
            headers=self._build_headers()
        )
        
        # Backend instances (lazy-initialized)
        self._relational_backend: Optional['ThemisRelationalBackend'] = None
        self._vector_backend: Optional['ThemisVectorBackend'] = None
        self._graph_backend: Optional['ThemisGraphBackend'] = None
        self._document_backend: Optional['ThemisDocumentBackend'] = None
        
        # Transaction management
        self._active_transaction: Optional[int] = None
        self._transaction_lock = asyncio.Lock()
        
        self.logger.info(f"Themis adapter initialized: {self.config.url}")
    
    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers including auth token"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"
        return headers
    
    # =============================================================================
    # UDS3-compatible backend getters (matching DatabaseManager interface)
    # =============================================================================
    
    def get_relational_backend(self) -> 'ThemisRelationalBackend':
        """
        Get relational backend (UDS3 interface compatible)
        
        Returns:
            ThemisRelationalBackend instance for SQL-like operations
        """
        if self._relational_backend is None:
            from .themis_relational import ThemisRelationalBackend
            self._relational_backend = ThemisRelationalBackend(self)
            self.logger.debug("Relational backend initialized")
        return self._relational_backend
    
    def get_vector_backend(self) -> 'ThemisVectorBackend':
        """
        Get vector backend (UDS3 interface compatible)
        
        Returns:
            ThemisVectorBackend instance for k-NN search operations
        """
        if self._vector_backend is None:
            from .themis_vector import ThemisVectorBackend
            self._vector_backend = ThemisVectorBackend(self)
            self.logger.debug("Vector backend initialized")
        return self._vector_backend
    
    def get_graph_backend(self) -> 'ThemisGraphBackend':
        """
        Get graph backend (UDS3 interface compatible)
        
        Returns:
            ThemisGraphBackend instance for graph traversal operations
        """
        if self._graph_backend is None:
            from .themis_graph import ThemisGraphBackend
            self._graph_backend = ThemisGraphBackend(self)
            self.logger.debug("Graph backend initialized")
        return self._graph_backend
    
    def get_document_backend(self) -> 'ThemisDocumentBackend':
        """
        Get document backend (UDS3 interface compatible)
        
        Returns:
            ThemisDocumentBackend instance for document storage operations
        """
        if self._document_backend is None:
            from .themis_document import ThemisDocumentBackend
            self._document_backend = ThemisDocumentBackend(self)
            self.logger.debug("Document backend initialized")
        return self._document_backend
    
    # =============================================================================
    # HTTP Request Helpers with Retry Logic
    # =============================================================================
    
    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Execute HTTP request with exponential backoff retry
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Request URL (relative to base_url)
            **kwargs: Additional httpx.request arguments
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.HTTPStatusError: On final failure after retries
        """
        from .themis_exceptions import ThemisConnectionError, map_http_error
        
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                
                # Check if status code requires retry
                if response.status_code in self.config.retry_statuses:
                    if attempt < self.config.max_retries:
                        backoff = self.config.retry_backoff_factor ** attempt
                        self.logger.warning(
                            f"HTTP {response.status_code} on {method} {url}, "
                            f"retry {attempt + 1}/{self.config.max_retries} "
                            f"after {backoff}s"
                        )
                        await asyncio.sleep(backoff)
                        continue
                
                # Raise for 4xx/5xx errors (non-retryable)
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                last_error = map_http_error(e.response.status_code, str(e))
                if attempt == self.config.max_retries:
                    raise last_error
                    
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = ThemisConnectionError(f"Connection failed: {e}")
                if attempt < self.config.max_retries:
                    backoff = self.config.retry_backoff_factor ** attempt
                    self.logger.warning(
                        f"Connection error on {method} {url}, "
                        f"retry {attempt + 1}/{self.config.max_retries} "
                        f"after {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise last_error
        
        # Should never reach here
        raise last_error or ThemisConnectionError("Request failed after retries")
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET request with retry"""
        return await self._request_with_retry("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST request with retry"""
        return await self._request_with_retry("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """PUT request with retry"""
        return await self._request_with_retry("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """DELETE request with retry"""
        return await self._request_with_retry("DELETE", url, **kwargs)
    
    # =============================================================================
    # Transaction Management (Themis native support!)
    # =============================================================================
    
    async def begin_transaction(self, isolation: str = "read_committed") -> int:
        """
        Begin ACID transaction
        
        Args:
            isolation: Isolation level ("read_committed" or "snapshot")
            
        Returns:
            transaction_id (int)
            
        Raises:
            ThemisTransactionError: If transaction cannot be started
        """
        from .themis_exceptions import ThemisTransactionError
        
        async with self._transaction_lock:
            if self._active_transaction is not None:
                raise ThemisTransactionError(
                    f"Transaction {self._active_transaction} already active"
                )
            
            try:
                response = await self.post(
                    "/transaction/begin",
                    json={"isolation": isolation}
                )
                data = response.json()
                self._active_transaction = data["transaction_id"]
                
                self.logger.info(
                    f"Transaction {self._active_transaction} started "
                    f"(isolation: {isolation})"
                )
                return self._active_transaction
                
            except Exception as e:
                raise ThemisTransactionError(f"Failed to begin transaction: {e}")
    
    async def commit_transaction(self, transaction_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Commit transaction
        
        Args:
            transaction_id: Transaction ID (uses active if not specified)
            
        Returns:
            Dict with commit result
            
        Raises:
            ThemisTransactionError: If commit fails
        """
        from .themis_exceptions import ThemisTransactionError
        
        async with self._transaction_lock:
            txn_id = transaction_id or self._active_transaction
            if txn_id is None:
                raise ThemisTransactionError("No active transaction to commit")
            
            try:
                response = await self.post(
                    "/transaction/commit",
                    json={"transaction_id": txn_id}
                )
                result = response.json()
                
                if transaction_id is None or transaction_id == self._active_transaction:
                    self._active_transaction = None
                
                self.logger.info(f"Transaction {txn_id} committed")
                return result
                
            except Exception as e:
                raise ThemisTransactionError(f"Failed to commit transaction: {e}")
    
    async def rollback_transaction(self, transaction_id: Optional[int] = None):
        """
        Rollback transaction
        
        Args:
            transaction_id: Transaction ID (uses active if not specified)
        """
        from .themis_exceptions import ThemisTransactionError
        
        async with self._transaction_lock:
            txn_id = transaction_id or self._active_transaction
            if txn_id is None:
                self.logger.warning("No active transaction to rollback")
                return
            
            try:
                await self.post(
                    "/transaction/rollback",
                    json={"transaction_id": txn_id}
                )
                
                if transaction_id is None or transaction_id == self._active_transaction:
                    self._active_transaction = None
                
                self.logger.info(f"Transaction {txn_id} rolled back")
                
            except Exception as e:
                self.logger.error(f"Failed to rollback transaction {txn_id}: {e}")
                # Always clear active transaction on rollback attempt
                if transaction_id is None or transaction_id == self._active_transaction:
                    self._active_transaction = None
    
    @asynccontextmanager
    async def transaction(self, isolation: str = "read_committed"):
        """
        Transaction context manager
        
        Usage:
            async with adapter.transaction() as txn_id:
                await relational.insert("users", {"name": "Alice"})
                await relational.insert("users", {"name": "Bob"})
            # Auto-commits on success, auto-rollbacks on exception
        """
        txn_id = await self.begin_transaction(isolation)
        try:
            yield txn_id
            await self.commit_transaction(txn_id)
        except Exception:
            await self.rollback_transaction(txn_id)
            raise
    
    @property
    def has_active_transaction(self) -> bool:
        """Check if transaction is active"""
        return self._active_transaction is not None
    
    @property
    def active_transaction_id(self) -> Optional[int]:
        """Get active transaction ID"""
        return self._active_transaction
    
    # =============================================================================
    # Health & Stats
    # =============================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Themis server health
        
        Returns:
            Dict with health status
        """
        try:
            response = await self.get("/health")
            return response.json()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get Themis server statistics
        
        Returns:
            Dict with server stats (entities, vectors, transactions, etc.)
        """
        try:
            response = await self.get("/stats")
            return response.json()
        except Exception as e:
            self.logger.error(f"Stats retrieval failed: {e}")
            return {"error": str(e)}
    
    async def get_transaction_stats(self) -> Dict[str, Any]:
        """
        Get transaction statistics
        
        Returns:
            Dict with transaction stats (active, committed, rolled back)
        """
        try:
            response = await self.get("/transaction/stats")
            return response.json()
        except Exception as e:
            self.logger.error(f"Transaction stats retrieval failed: {e}")
            return {"error": str(e)}
    
    # =============================================================================
    # Lifecycle
    # =============================================================================
    
    async def close(self):
        """
        Close HTTP client connection pool
        
        Automatically rolls back active transaction before closing.
        """
        if self._active_transaction is not None:
            self.logger.warning(
                f"Rolling back active transaction {self._active_transaction} "
                "before closing adapter"
            )
            await self.rollback_transaction()
        
        await self.client.aclose()
        self.logger.info("Themis adapter closed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# =============================================================================
# Convenience Functions
# =============================================================================

def create_adapter_from_env() -> ThemisAdapter:
    """
    Create Themis adapter from environment variables
    
    Environment Variables:
        THEMIS_URL: Themis server URL (default: http://localhost:8765)
        THEMIS_TIMEOUT: Request timeout in seconds (default: 30)
        THEMIS_MAX_RETRIES: Maximum retry attempts (default: 3)
        THEMIS_POOL_SIZE: Connection pool size (default: 100)
        THEMIS_AUTH_TOKEN: Optional authentication token
        
    Returns:
        Configured ThemisAdapter instance
    """
    config = ThemisConfig.from_env()
    return ThemisAdapter(config)


async def test_connection(config: Optional[ThemisConfig] = None) -> bool:
    """
    Test Themis connection
    
    Args:
        config: Themis configuration (uses defaults if not provided)
        
    Returns:
        True if connection successful, False otherwise
    """
    adapter = ThemisAdapter(config)
    try:
        health = await adapter.health_check()
        return health.get("status") == "healthy"
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
    finally:
        await adapter.close()


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ThemisAdapter",
    "ThemisConfig",
    "create_adapter_from_env",
    "test_connection"
]
