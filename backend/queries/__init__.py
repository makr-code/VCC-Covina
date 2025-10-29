"""
Backend Query Endpoints

REST API endpoints for querying data from various backends.
"""

from .legal_graph_queries import router as legal_graph_router

__all__ = ["legal_graph_router"]
