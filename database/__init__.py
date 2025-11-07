"""
Themis Database Adapter Package

Python HTTP adapter for Themis DB providing UDS3-compatible interfaces.
Supports all 4 backend types: Relational, Vector, Graph, Document.

Author: VCC Covina Team
Created: 2025-11-07
Version: 1.0.0

Quick Start:
    from database import ThemisAdapter, ThemisConfig
    
    # Create adapter
    config = ThemisConfig(url="http://localhost:8765")
    adapter = ThemisAdapter(config)
    
    # Get backends
    relational = adapter.get_relational_backend()
    vector = adapter.get_vector_backend()
    graph = adapter.get_graph_backend()
    document = adapter.get_document_backend()
    
    # Use backends (async)
    results = await relational.execute_query("SELECT * FROM users")
    
    # Close adapter
    await adapter.close()
"""

from .themis_adapter import (
    ThemisAdapter,
    ThemisConfig,
    create_adapter_from_env,
    test_connection
)

from .themis_exceptions import (
    # Base
    ThemisError,
    
    # Connection & Auth
    ThemisConnectionError,
    ThemisAuthenticationError,
    ThemisPermissionError,
    
    # Data Operations
    ThemisNotFoundError,
    ThemisValidationError,
    ThemisConflictError,
    
    # Transactions
    ThemisTransactionError,
    
    # Specialized
    ThemisQueryError,
    ThemisVectorError,
    ThemisGraphError,
    
    # Factories
    map_http_error,
    create_query_error,
    create_transaction_error,
    create_vector_error,
    create_graph_error
)

__version__ = "1.0.0"
__author__ = "VCC Covina Team"

__all__ = [
    # Core
    "ThemisAdapter",
    "ThemisConfig",
    "create_adapter_from_env",
    "test_connection",
    
    # Exceptions
    "ThemisError",
    "ThemisConnectionError",
    "ThemisAuthenticationError",
    "ThemisPermissionError",
    "ThemisNotFoundError",
    "ThemisValidationError",
    "ThemisConflictError",
    "ThemisTransactionError",
    "ThemisQueryError",
    "ThemisVectorError",
    "ThemisGraphError",
    "map_http_error",
    "create_query_error",
    "create_transaction_error",
    "create_vector_error",
    "create_graph_error",
    
    # Version
    "__version__"
]
