"""
Themis Database Adapter - Exception Classes

Custom exceptions for Themis operations with HTTP status code mapping.

Author: VCC Covina Team
Created: 2025-11-07
Version: 1.0.0
"""

from typing import Optional


class ThemisError(Exception):
    """
    Base exception for Themis operations
    
    All Themis-specific exceptions inherit from this class.
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
    
    def __str__(self) -> str:
        if self.status_code:
            return f"[HTTP {self.status_code}] {self.message}"
        return self.message


class ThemisConnectionError(ThemisError):
    """
    Connection error to Themis server
    
    Raised when:
    - Cannot connect to Themis server
    - Timeout during request
    - Network error
    - HTTP 5xx server errors
    """
    pass


class ThemisNotFoundError(ThemisError):
    """
    Entity not found (HTTP 404)
    
    Raised when:
    - Entity does not exist
    - Collection not found
    - Resource not available
    """
    pass


class ThemisValidationError(ThemisError):
    """
    Invalid request (HTTP 400)
    
    Raised when:
    - Invalid query syntax (AQL)
    - Missing required fields
    - Invalid data format
    - Constraint violation
    """
    pass


class ThemisTransactionError(ThemisError):
    """
    Transaction conflict or error
    
    Raised when:
    - Transaction cannot be started (already active)
    - Commit fails (conflict, timeout)
    - Rollback fails
    - Optimistic concurrency conflict
    """
    pass


class ThemisAuthenticationError(ThemisError):
    """
    Authentication error (HTTP 401)
    
    Raised when:
    - Invalid or missing auth token
    - Expired credentials
    """
    pass


class ThemisPermissionError(ThemisError):
    """
    Permission error (HTTP 403)
    
    Raised when:
    - User lacks permission for operation
    - Resource access denied
    """
    pass


class ThemisConflictError(ThemisError):
    """
    Conflict error (HTTP 409)
    
    Raised when:
    - Entity already exists (duplicate key)
    - Concurrent modification conflict
    """
    pass


class ThemisQueryError(ThemisError):
    """
    Query execution error
    
    Raised when:
    - AQL query syntax error
    - Query timeout
    - Invalid query parameters
    """
    pass


class ThemisVectorError(ThemisError):
    """
    Vector operation error
    
    Raised when:
    - Invalid vector dimensions
    - Vector index not found
    - k-NN search error
    """
    pass


class ThemisGraphError(ThemisError):
    """
    Graph operation error
    
    Raised when:
    - Invalid graph traversal
    - Node/edge not found
    - Cypher translation error
    """
    pass


# =============================================================================
# HTTP Status Code Mapping
# =============================================================================

def map_http_error(status_code: int, message: str, response_text: Optional[str] = None) -> ThemisError:
    """
    Map HTTP status codes to Themis exceptions
    
    Args:
        status_code: HTTP status code
        message: Error message
        response_text: Optional response body text
        
    Returns:
        Appropriate ThemisError subclass instance
        
    Examples:
        >>> error = map_http_error(404, "Entity not found")
        >>> isinstance(error, ThemisNotFoundError)
        True
        
        >>> error = map_http_error(500, "Internal server error")
        >>> isinstance(error, ThemisConnectionError)
        True
    """
    full_message = f"{message} - {response_text}" if response_text else message
    
    # 4xx Client Errors
    if status_code == 400:
        return ThemisValidationError(full_message, status_code)
    elif status_code == 401:
        return ThemisAuthenticationError(full_message, status_code)
    elif status_code == 403:
        return ThemisPermissionError(full_message, status_code)
    elif status_code == 404:
        return ThemisNotFoundError(full_message, status_code)
    elif status_code == 409:
        return ThemisConflictError(full_message, status_code)
    elif 400 <= status_code < 500:
        return ThemisValidationError(full_message, status_code)
    
    # 5xx Server Errors
    elif status_code >= 500:
        return ThemisConnectionError(full_message, status_code)
    
    # Default
    else:
        return ThemisError(full_message, status_code)


# =============================================================================
# Context-Specific Error Factories
# =============================================================================

def create_query_error(message: str, query: Optional[str] = None) -> ThemisQueryError:
    """
    Create query error with optional query text
    
    Args:
        message: Error message
        query: Optional AQL query that failed
        
    Returns:
        ThemisQueryError instance
    """
    if query:
        return ThemisQueryError(f"{message}\nQuery: {query}")
    return ThemisQueryError(message)


def create_transaction_error(
    message: str,
    transaction_id: Optional[int] = None
) -> ThemisTransactionError:
    """
    Create transaction error with optional transaction ID
    
    Args:
        message: Error message
        transaction_id: Optional transaction ID that failed
        
    Returns:
        ThemisTransactionError instance
    """
    if transaction_id is not None:
        return ThemisTransactionError(f"Transaction {transaction_id}: {message}")
    return ThemisTransactionError(message)


def create_vector_error(
    message: str,
    vector_id: Optional[str] = None,
    expected_dim: Optional[int] = None,
    actual_dim: Optional[int] = None
) -> ThemisVectorError:
    """
    Create vector error with dimension information
    
    Args:
        message: Error message
        vector_id: Optional vector ID
        expected_dim: Expected vector dimension
        actual_dim: Actual vector dimension
        
    Returns:
        ThemisVectorError instance
    """
    parts = [message]
    if vector_id:
        parts.append(f"Vector ID: {vector_id}")
    if expected_dim and actual_dim:
        parts.append(f"Expected dim: {expected_dim}, got: {actual_dim}")
    return ThemisVectorError(" | ".join(parts))


def create_graph_error(
    message: str,
    query: Optional[str] = None,
    node_id: Optional[str] = None
) -> ThemisGraphError:
    """
    Create graph error with context
    
    Args:
        message: Error message
        query: Optional Cypher/AQL query
        node_id: Optional node ID
        
    Returns:
        ThemisGraphError instance
    """
    parts = [message]
    if node_id:
        parts.append(f"Node: {node_id}")
    if query:
        parts.append(f"Query: {query}")
    return ThemisGraphError(" | ".join(parts))


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Base
    "ThemisError",
    
    # Connection & Auth
    "ThemisConnectionError",
    "ThemisAuthenticationError",
    "ThemisPermissionError",
    
    # Data Operations
    "ThemisNotFoundError",
    "ThemisValidationError",
    "ThemisConflictError",
    
    # Transactions
    "ThemisTransactionError",
    
    # Specialized
    "ThemisQueryError",
    "ThemisVectorError",
    "ThemisGraphError",
    
    # Factories
    "map_http_error",
    "create_query_error",
    "create_transaction_error",
    "create_vector_error",
    "create_graph_error"
]
