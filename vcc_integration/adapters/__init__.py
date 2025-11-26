"""
VCC Service Adapters
Phase 2: VCC Ecosystem Integration

Adapters for integrating with VCC ecosystem services:
- VERITAS (Legal Intelligence)
- Themis (Unified Database)
- Clara (Document Intelligence)
- Argus (Media Management)

All adapters are designed for on-premise deployment.
"""

from .veritas_adapter import VeritasAdapter
from .themis_adapter import ThemisAdapter
from .clara_adapter import ClaraAdapter
from .argus_adapter import ArgusAdapter
from .base_adapter import VCCServiceAdapter

__all__ = [
    "VCCServiceAdapter",
    "VeritasAdapter",
    "ThemisAdapter",
    "ClaraAdapter",
    "ArgusAdapter"
]
