"""Compatibility shim.

This module used to implement a lightweight Neo4j adapter named
`database_api_neo4j_simple`. The preferred, short name is now
`database_api_neo4j`. To preserve backwards compatibility we re-export
the main symbols and emit a deprecation warning when imported.
"""
from __future__ import annotations

import warnings
from typing import Any, Dict

warnings.warn(
    "Importing 'database.database_api_neo4j_simple' is deprecated; use 'database.database_api_neo4j' instead.",
    DeprecationWarning,
)

# Re-export everything from the new module
from .database_api_neo4j import *  # noqa: F401,F403

# Keep a get_backend_class for compatibility
def get_backend_class():
    try:
        from .database_api_neo4j import get_backend_class as _g

        return _g()
    except Exception:
        return None
