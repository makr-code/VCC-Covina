"""
Backend Query Endpoints

REST API endpoints for querying data from various backends.
"""

from .legal_graph_queries import router as legal_graph_router
from .legal_analytics_queries import router as legal_analytics_router
from .process_queries import router as process_router

__all__ = ["legal_graph_router", "legal_analytics_router", "process_router"]
