"""
System Status View - Phase 3: View Migration

Migrated to BaseView pattern with event-driven architecture.
Real-time backend health monitoring.

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 3)
Date: 14.10.2025, 11:05 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from frontend.views.base_view import BaseView
from frontend.core.event_bus import EventType
from frontend.views.system_status_view import SystemStatusView as LegacySystemStatus


class SystemStatusViewMigrated(BaseView):
    """
    System Status View (Event-Driven).
    
    Real-time backend health monitoring with auto-updates.
    """
    
    def __init__(self, parent, event_bus, backend_service, **kwargs):
        self.backend_service = backend_service
        self._legacy_view = None
        super().__init__(parent, event_bus, **kwargs)
    
    def build_ui(self):
        """Build System Status UI (Pure UI construction)."""
        # Embed legacy view
        self._legacy_view = LegacySystemStatus(self)
        self._legacy_view.pack(fill="both", expand=True)
    
    def update_data(self, data: Dict[str, Any]):
        """Update view with new data (Pure business logic)."""
        data_type = data.get("type")
        
        if data_type == "refresh":
            if self._legacy_view:
                self._legacy_view.refresh()
        
        elif data_type == "backend_status":
            # Update backend health indicators
            if self._legacy_view:
                self._legacy_view.connection_status = data.get("status")
                self._legacy_view._update_health_display()
    
    def on_activate(self):
        """Lifecycle: Subscribe to events when view becomes visible."""
        # Subscribe to backend events
        self.event_bus.subscribe(EventType.BACKEND_CONNECTED, self._on_backend_event)
        self.event_bus.subscribe(EventType.BACKEND_DISCONNECTED, self._on_backend_event)
        self.event_bus.subscribe(EventType.BACKEND_ERROR, self._on_backend_error)
        self.event_bus.subscribe(EventType.JOB_STATUS_CHANGED, self._on_job_status_changed)
        
        # Initial refresh
        if self._legacy_view:
            self._legacy_view.refresh()
    
    def on_deactivate(self):
        """Lifecycle: Unsubscribe from events when view becomes hidden."""
        self.event_bus.unsubscribe(EventType.BACKEND_CONNECTED, self._on_backend_event)
        self.event_bus.unsubscribe(EventType.BACKEND_DISCONNECTED, self._on_backend_event)
        self.event_bus.unsubscribe(EventType.BACKEND_ERROR, self._on_backend_error)
        self.event_bus.unsubscribe(EventType.JOB_STATUS_CHANGED, self._on_job_status_changed)
    
    # Event Handlers
    
    def _on_backend_event(self, event):
        """Handle backend connection events."""
        self.safe_update_data({"type": "refresh"})
    
    def _on_backend_error(self, event):
        """Handle backend error event."""
        # Could show error notification
        pass
    
    def _on_job_status_changed(self, event):
        """Handle job status change."""
        # Update active jobs count
        self.safe_update_data({"type": "refresh"})


# Export
__all__ = ["SystemStatusViewMigrated"]
