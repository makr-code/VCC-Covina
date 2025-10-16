#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPRECATED MODULE - Use uds3_security_quality instead

This module is deprecated as of 1. Oktober 2025.
DataQualityManager has been consolidated into uds3_security_quality.py
to reduce code duplication and improve maintainability.

Migration Guide:
--------------
OLD:
    from uds3_quality import DataQualityManager, QualityMetric, QualityConfig

NEW:
    from uds3_security_quality import DataQualityManager, QualityMetric, QualityConfig

Why this change?
----------------
- Eliminated 35 KB of duplicate code
- Centralized Security + Quality management
- Single source of truth for data quality
- Better integration between security and quality features

This backward compatibility wrapper will be removed in a future release.
"""

import warnings

# Show deprecation warning
warnings.warn(
    "uds3_quality module is deprecated. "
    "Use 'from uds3_security_quality import DataQualityManager, QualityMetric, QualityConfig' instead. "
    "This compatibility wrapper will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from uds3_security_quality for backward compatibility
try:
    from uds3_security_quality import (
        # Main Classes
        DataQualityManager,
        QualityConfig,
        
        # Enums
        QualityMetric,
        
        # Factory Function
        create_quality_manager,
        
        # Quality Assessment Results (if defined)
    )
    
    __all__ = [
        'DataQualityManager',
        'QualityConfig',
        'QualityMetric',
        'create_quality_manager',
    ]
    
except ImportError as e:
    warnings.warn(
        f"Could not import from uds3_security_quality: {e}. "
        "Quality features may not be available.",
        ImportWarning
    )
    
    # Provide None fallbacks
    DataQualityManager = None
    QualityConfig = None
    QualityMetric = None
    create_quality_manager = None
    
    __all__ = []

# Version info for backward compatibility checks
__deprecated_since__ = "1.Oktober.2025"
__deprecated_version__ = "UDS3.0_optimized"
__replacement_module__ = "uds3_security_quality"
