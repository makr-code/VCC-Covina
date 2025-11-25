"""
VCC Integration Module
Phase 2: VCC Ecosystem Integration

This module provides integration adapters for the VCC ecosystem components:
- VERITAS (Legal Intelligence)
- Themis (Unified Database)
- Clara (Document Intelligence)
- Argus (Media Management)

All integrations are designed for on-premise deployment without external vendor dependencies.
"""

__version__ = "1.0.0"
__author__ = "VCC-Covina Team"

from .events import EventPublisher, EventConsumer
from .auth import VCCAuthenticator, VCCTokenValidator
from .adapters import (
    VeritasAdapter,
    ThemisAdapter,
    ClaraAdapter,
    ArgusAdapter
)

__all__ = [
    "EventPublisher",
    "EventConsumer",
    "VCCAuthenticator",
    "VCCTokenValidator",
    "VeritasAdapter",
    "ThemisAdapter",
    "ClaraAdapter",
    "ArgusAdapter"
]
