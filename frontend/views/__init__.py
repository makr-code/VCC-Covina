"""
Frontend Views Module - Phase 3 COMPLETE ✅
===========================================

Event-driven Views für Covina Frontend.
Alle Views erben von BaseView.

Phase 3 Views (10/10 migrated):
- RecoveryView: Failed file recovery management (NEW v3.4.8)
- HomeView: Dashboard with 12 charts (wrapper)
- SystemStatusView: Backend health monitoring (wrapper)
- IngestionView: Upload & job management (wrapper)
- DatabaseHealthView: Multi-DB health monitoring (wrapper)
- SecurityView: Security audit & alerts (wrapper)
- ErrorTrackingView: Error logs & tracking (wrapper)
- GoldenDatasetView: Golden dataset management (wrapper)
- UDS3View: Multi-database dataset management (NEW)
- SAGAView: SAGA orchestration monitoring (NEW)

Version: 4.0.0 (Frontend Modernization - Phase 3 COMPLETE)
Date: 14. Oktober 2025, 11:30 Uhr
"""

from .base_view import BaseView
from .home_dashboard_view import HomeDashboardView

# Phase 3 Migrated Views (10)
from .recovery_view import RecoveryView
from .home_view import HomeView
from .system_status_view_migrated import SystemStatusViewMigrated
from .ingestion_view_migrated import IngestionViewMigrated
from .database_health_view_migrated import DatabaseHealthViewMigrated
from .security_view_migrated import SecurityViewMigrated
from .error_tracking_view_migrated import ErrorTrackingViewMigrated
from .golden_dataset_view_migrated import GoldenDatasetViewMigrated
from .uds3_view import UDS3View
from .saga_view import SAGAView

__all__ = [
    # Core
    "BaseView",
    "HomeDashboardView",
    
    # Phase 3 Views (10)
    "RecoveryView",
    "HomeView",
    "SystemStatusViewMigrated",
    "IngestionViewMigrated",
    "DatabaseHealthViewMigrated",
    "SecurityViewMigrated",
    "ErrorTrackingViewMigrated",
    "GoldenDatasetViewMigrated",
    "UDS3View",
    "SAGAView",
]
