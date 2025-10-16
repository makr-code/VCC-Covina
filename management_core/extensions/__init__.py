# -*- coding: utf-8 -*-
"""
Management Core Extensions Package

Integration Package für Gap Detection und AI Judge Systeme
in die Management Core Architektur.

Autor: Covina Team
Lizenz: AGPL-3.0
"""

from .extensions_api import (
    create_extensions_router,
    get_extensions_scopes,
    register_extensions_with_management_core
)

from .extensions_cli import (
    ManagementCoreExtensionsCLI,
    register_extensions_with_cli
)

from .extensions_observability import (
    ExtensionsObservabilityCollector,
    ExtensionsPerformanceMonitor,
    GapDetectionMetric,
    AIEvaluationMetric,
    SchedulerMetric,
    create_extensions_observability,
    create_performance_monitor
)

from .extensions_integration import (
    ManagementCoreExtensionsIntegration,
    create_extensions_integration,
    quick_setup
)

# Version information
__version__ = "1.0.0"
__author__ = "Covina Team"
__license__ = "AGPL-3.0"

# Package exports
__all__ = [
    # API Integration
    "create_extensions_router",
    "get_extensions_scopes", 
    "register_extensions_with_management_core",
    
    # CLI Integration
    "ManagementCoreExtensionsCLI",
    "register_extensions_with_cli",
    
    # Observability Integration
    "ExtensionsObservabilityCollector",
    "ExtensionsPerformanceMonitor",
    "GapDetectionMetric",
    "AIEvaluationMetric", 
    "SchedulerMetric",
    "create_extensions_observability",
    "create_performance_monitor",
    
    # Main Integration
    "ManagementCoreExtensionsIntegration",
    "create_extensions_integration",
    "quick_setup",
    
    # Version info
    "__version__",
    "__author__",
    "__license__"
]