"""
Database Health View - Phase 3: View Migration

Migrated to BaseView pattern with event-driven architecture.
Monitor all 4 database connections (PostgreSQL, ChromaDB, Neo4j, CouchDB).

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 3)
Date: 14.10.2025, 11:10 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from frontend.views.base_view import BaseView
from frontend.core.event_bus import EventType
from frontend.views.database_health_view import DatabaseHealthView as LegacyDBHealth


class DatabaseHealthViewMigrated(BaseView):
    """
    Database Health View (Event-Driven).
    
    Monitor all 4 database connections (PostgreSQL, ChromaDB, Neo4j, CouchDB).
    """
    
    def __init__(self, parent, event_bus, backend_service, **kwargs):
        self.backend_service = backend_service
        self._legacy_view = None
        super().__init__(parent, event_bus, **kwargs)
    
    def build_ui(self):
        """Build Database Health View UI (Pure UI construction)."""
        # Embed legacy view
        self._legacy_view = LegacyDBHealth(self)
        self._legacy_view.pack(fill="both", expand=True)
    
    def update_data(self, data: Dict[str, Any]):
        """Update view with new data (Pure business logic)."""
        data_type = data.get("type")
        
        if data_type == "refresh":
            if self._legacy_view and hasattr(self._legacy_view, 'refresh'):
                self._legacy_view.refresh()
        
        elif data_type == "data_update":
            # Handle specific data updates
            if self._legacy_view:
                # Update legacy view data
                for key, value in data.get("data", {}).items():
                    if hasattr(self._legacy_view, key):
                        setattr(self._legacy_view, key, value)
    
    def on_activate(self):
        """Lifecycle: Subscribe to events when view becomes visible."""
        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.DB_HEALTH_CHECK, self._on_event_generic)
        self.event_bus.subscribe(EventType.DB_CONNECTION_LOST, self._on_event_generic)
        self.event_bus.subscribe(EventType.DB_CONNECTION_RESTORED, self._on_event_generic)
        
        # Initial refresh
        if self._legacy_view and hasattr(self._legacy_view, 'refresh'):
            self._legacy_view.refresh()
    
    def on_deactivate(self):
        """Lifecycle: Unsubscribe from events when view becomes hidden."""
        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.DB_HEALTH_CHECK, self._on_event_generic)
        self.event_bus.unsubscribe(EventType.DB_CONNECTION_LOST, self._on_event_generic)
        self.event_bus.unsubscribe(EventType.DB_CONNECTION_RESTORED, self._on_event_generic)
    
    # Event Handlers
    
    def _on_event_generic(self, event):
        """Handle generic event."""
        self.safe_update_data({"type": "refresh"})


# Export
__all__ = ["DatabaseHealthViewMigrated"]
