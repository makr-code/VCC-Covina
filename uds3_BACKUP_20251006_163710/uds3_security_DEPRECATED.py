#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPRECATED: uds3_security.py

⚠️ Diese Datei ist DEPRECATED und wird nicht mehr verwendet!

GRUND: DataSecurityManager existierte als Duplikat in 2 Dateien:
- uds3_security.py (26KB) ← DEPRECATED
- uds3_security_quality.py (36KB) ← AKTIV

MIGRATION: Alle Imports wurden konsolidiert nach uds3_security_quality.py

Verwende stattdessen:
```python
from uds3_security_quality import (
    SecurityLevel,
    DataSecurityManager,
    SecurityConfig,
    create_security_manager,
    validate_document_security,
)
```

Diese Datei wird in einer zukünftigen Version entfernt.

Datum der Deprecation: 1. Oktober 2025
Grund: Todo #1 - Duplicate Security Manager Konsolidierung
"""

# Backward Compatibility: Re-export aus uds3_security_quality.py
import warnings

warnings.warn(
    "uds3_security.py ist deprecated! Verwende uds3_security_quality.py",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export für Backward Compatibility
try:
    from uds3_security_quality import (
        SecurityLevel,
        AdministrativeClassification,  # Falls vorhanden
        SecurityConfig,
        DataSecurityManager,
        create_security_manager,
        validate_document_security,
    )

    __all__ = [
        "SecurityLevel",
        "AdministrativeClassification",
        "SecurityConfig",
        "DataSecurityManager",
        "create_security_manager",
        "validate_document_security",
    ]

except ImportError as e:
    raise ImportError(
        f"uds3_security_quality.py konnte nicht importiert werden: {e}\n"
        "uds3_security.py ist deprecated und alle Funktionen wurden nach "
        "uds3_security_quality.py verschoben."
    )

# Legacy-Support-Hinweis
print(
    "⚠️  DEPRECATION WARNING: uds3_security.py ist veraltet!\n"
    "   Bitte imports auf uds3_security_quality.py umstellen.\n"
    "   Diese Datei wird in einer zukünftigen Version entfernt."
)
