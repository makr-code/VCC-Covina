"""
Frontend Core Module
====================

Core utilities für Frontend:
- EventBus: Event-driven architecture
- TaskExecutor: Thread-pool management
- ViewManager: Dynamic view switching (Phase 4)
- BackendService: API abstraction layer
- Chart Management: Threading utilities (legacy)

Version: 4.0.0 (Frontend Modernization - Phase 4)
Date: 14. Oktober 2025
"""

# Event-driven Architecture (NEW v4.0.0)
from frontend.core.event_bus import (
    EventBus,
    EventType,
    Event
)

from frontend.core.task_executor import (
    TaskExecutor,
    Task
)

from frontend.core.view_manager import (
    ViewManager
)

from frontend.core.backend_service import (
    CovinaBackendService
)

# Chart Management (Legacy)
from frontend.core.chart_threading import (
    ChartType,
    ChartStatus,
    ChartRequest,
    ChartResult,
    ChartWorker,
    ChartThreadPool
)

from frontend.core.chart_workers import CHART_WORKERS

__all__ = [
    # Event-driven Architecture
    'EventBus',
    'EventType',
    'Event',
    'TaskExecutor',
    'Task',
    'ViewManager',
    'CovinaBackendService',
    # Chart Management (Legacy)
    'ChartType',
    'ChartStatus',
    'ChartRequest',
    'ChartResult',
    'ChartWorker',
    'ChartThreadPool',
    'CHART_WORKERS',
]
