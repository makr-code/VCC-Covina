"""
Home Dashboard View - Phase 3: View Migration

Migrated to BaseView pattern with event-driven architecture.
Wraps existing HomeDashboardView with lifecycle management.

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 3)
Date: 14.10.2025, 11:00 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from frontend.views.base_view import BaseView
from frontend.core.event_bus import EventType
from frontend.views.home_dashboard_view import HomeDashboardView as LegacyHomeDashboard


class HomeView(BaseView):
    """
    Home Dashboard View (Event-Driven).
    
    Wraps legacy HomeDashboardView with BaseView lifecycle.
    Subscribes to system events for auto-refresh.
    """
    
    def __init__(self, parent, event_bus, backend_service, **kwargs):
        self.backend_service = backend_service
        self._legacy_view = None
        self._auto_refresh_enabled = True
        super().__init__(parent, event_bus, **kwargs)
    
    def build_ui(self):
        """Build Home Dashboard UI (Pure UI construction)."""
        # Embed legacy view
        self._legacy_view = LegacyHomeDashboard(self)
        self._legacy_view.pack(fill="both", expand=True)
    
    def update_data(self, data: Dict[str, Any]):
        """Update view with new data (Pure business logic)."""
        data_type = data.get("type")
        
        if data_type == "refresh":
            # Trigger refresh on legacy view
            if self._legacy_view:
                self._legacy_view.refresh()
        
        elif data_type == "health_update":
            # Health data updated
            if self._legacy_view:
                self._legacy_view.health_data = data.get("health_data")
                self._legacy_view._create_system_health_chart()
        
        elif data_type == "job_complete":
            # Auto-refresh on job completion
            if self._auto_refresh_enabled and self._legacy_view:
                self.after(1000, self._legacy_view.refresh)
    
    def on_activate(self):
        """Lifecycle: Subscribe to events when view becomes visible."""
        # Subscribe to system events
        self.event_bus.subscribe(EventType.BACKEND_CONNECTED, self._on_backend_connected)
        self.event_bus.subscribe(EventType.BACKEND_DISCONNECTED, self._on_backend_disconnected)
        self.event_bus.subscribe(EventType.JOB_COMPLETED, self._on_job_completed)
        self.event_bus.subscribe(EventType.DB_HEALTH_CHECK, self._on_db_health_check)
        
        # Initial refresh
        if self._legacy_view:
            self._legacy_view.refresh()
    
    def on_deactivate(self):
        """Lifecycle: Unsubscribe from events when view becomes hidden."""
        # Unsubscribe from system events
        self.event_bus.unsubscribe(EventType.BACKEND_CONNECTED, self._on_backend_connected)
        self.event_bus.unsubscribe(EventType.BACKEND_DISCONNECTED, self._on_backend_disconnected)
        self.event_bus.unsubscribe(EventType.JOB_COMPLETED, self._on_job_completed)
        self.event_bus.unsubscribe(EventType.DB_HEALTH_CHECK, self._on_db_health_check)
    
    # Event Handlers
    
    def _on_backend_connected(self, event):
        """Handle backend connection event."""
        self.safe_update_data({"type": "refresh"})
    
    def _on_backend_disconnected(self, event):
        """Handle backend disconnection event."""
        # Could show "disconnected" overlay
        pass
    
    def _on_job_completed(self, event):
        """Handle job completion event."""
        self.safe_update_data({"type": "job_complete"})
    
    def _on_db_health_check(self, event):
        """Handle database health check event."""
        # Could update specific DB charts
        pass


# Export
__all__ = ["HomeView"]
