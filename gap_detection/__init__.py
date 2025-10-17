# -*- coding: utf-8 -*-
"""
Gap Detection Package Init

Initialisierung des Knowledge Gap Detection Packages mit allen
Haupt-Komponenten und Utilities.

Autor: Covina Team
Lizenz: AGPL-3.0
"""

# Import only working modules (avoid corrupted files)
try:
    from .gap_database import KnowledgeGapDB
except ImportError as e:
    print(f"Warning: Could not import KnowledgeGapDB: {e}")
    KnowledgeGapDB = None

# Version information
# Version information
__version__ = "1.0.0"
__author__ = "Covina Team"
__license__ = "AGPL-3.0"

# Package exports (minimal for now)
__all__ = [
    "KnowledgeGapDB",
    "__version__",
    "__author__",
    "__license__"
]