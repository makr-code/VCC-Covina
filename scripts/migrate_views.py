"""
Quick View Migration Script - Phase 3

Creates BaseView wrappers for all remaining legacy views.
Maintains backward compatibility while adding event-driven architecture.

Author: Covina Development Team
Date: 14.10.2025, 11:10 Uhr
"""

# Template for view migration
VIEW_TEMPLATE = '''"""
{view_name} - Phase 3: View Migration

Migrated to BaseView pattern with event-driven architecture.
{description}

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 3)
Date: 14.10.2025, 11:10 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from frontend.views.base_view import BaseView
from frontend.core.event_bus import EventType
{legacy_import}


class {class_name}(BaseView):
    """
    {view_name} (Event-Driven).
    
    {description}
    """
    
    def __init__(self, parent, event_bus, backend_service, **kwargs):
        self.backend_service = backend_service
        self._legacy_view = None
        super().__init__(parent, event_bus, **kwargs)
    
    def build_ui(self):
        """Build {view_name} UI (Pure UI construction)."""
        # Embed legacy view
        self._legacy_view = {legacy_class}(self)
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
                for key, value in data.get("data", {{}}).items():
                    if hasattr(self._legacy_view, key):
                        setattr(self._legacy_view, key, value)
    
    def on_activate(self):
        """Lifecycle: Subscribe to events when view becomes visible."""
        # Subscribe to relevant events
{event_subscriptions}
        
        # Initial refresh
        if self._legacy_view and hasattr(self._legacy_view, 'refresh'):
            self._legacy_view.refresh()
    
    def on_deactivate(self):
        """Lifecycle: Unsubscribe from events when view becomes hidden."""
        # Unsubscribe from events
{event_unsubscriptions}
    
    # Event Handlers
    
    def _on_event_generic(self, event):
        """Handle generic event."""
        self.safe_update_data({{"type": "refresh"}})


# Export
__all__ = ["{class_name}"]
'''

# View configurations
views = [
    {
        "view_name": "Ingestion View",
        "class_name": "IngestionViewMigrated",
        "description": "Upload and process documents with real-time progress.",
        "legacy_import": "from frontend.views.ingestion_view import IngestionView as LegacyIngestion",
        "legacy_class": "LegacyIngestion",
        "file_name": "ingestion_view_migrated.py",
        "events": [
            "EventType.UPLOAD_STARTED",
            "EventType.UPLOAD_PROGRESS",
            "EventType.UPLOAD_FINISHED",
            "EventType.JOB_CREATED",
        ]
    },
    {
        "view_name": "Database Health View",
        "class_name": "DatabaseHealthViewMigrated",
        "description": "Monitor all 4 database connections (PostgreSQL, ChromaDB, Neo4j, CouchDB).",
        "legacy_import": "from frontend.views.database_health_view import DatabaseHealthView as LegacyDBHealth",
        "legacy_class": "LegacyDBHealth",
        "file_name": "database_health_view_migrated.py",
        "events": [
            "EventType.DB_HEALTH_CHECK",
            "EventType.DB_CONNECTION_LOST",
            "EventType.DB_CONNECTION_RESTORED",
        ]
    },
    {
        "view_name": "Security & Audit View",
        "class_name": "SecurityViewMigrated",
        "description": "Security logs, audit trail, and access control monitoring.",
        "legacy_import": "from frontend.views.security_view import SecurityView as LegacySecurity",
        "legacy_class": "LegacySecurity",
        "file_name": "security_view_migrated.py",
        "events": [
            "EventType.SECURITY_AUDIT_LOG",
            "EventType.SECURITY_ALERT",
        ]
    },
    {
        "view_name": "Error Tracking View",
        "class_name": "ErrorTrackingViewMigrated",
        "description": "System errors, exceptions, and recovery suggestions.",
        "legacy_import": "from frontend.views.error_tracking_view import ErrorTrackingView as LegacyErrors",
        "legacy_class": "LegacyErrors",
        "file_name": "error_tracking_view_migrated.py",
        "events": [
            "EventType.ERROR_LOGGED",
            "EventType.ERROR_CLEARED",
            "EventType.BACKEND_ERROR",
        ]
    },
    {
        "view_name": "Golden Dataset View",
        "class_name": "GoldenDatasetViewMigrated",
        "description": "Curated high-quality dataset management and validation.",
        "legacy_import": "from frontend.views.golden_dataset_view import GoldenDatasetView as LegacyGolden",
        "legacy_class": "LegacyGolden",
        "file_name": "golden_dataset_view_migrated.py",
        "events": [
            "EventType.GOLDEN_DATASET_UPDATED",
            "EventType.GOLDEN_DATASET_VALIDATED",
        ]
    },
]

# Generate all views
for view_config in views:
    # Generate event subscriptions
    event_subs = []
    event_unsubs = []
    for event in view_config["events"]:
        event_subs.append(f"        self.event_bus.subscribe({event}, self._on_event_generic)")
        event_unsubs.append(f"        self.event_bus.unsubscribe({event}, self._on_event_generic)")
    
    event_subscriptions = "\\n".join(event_subs)
    event_unsubscriptions = "\\n".join(event_unsubs)
    
    # Generate code
    code = VIEW_TEMPLATE.format(
        view_name=view_config["view_name"],
        class_name=view_config["class_name"],
        description=view_config["description"],
        legacy_import=view_config["legacy_import"],
        legacy_class=view_config["legacy_class"],
        event_subscriptions=event_subscriptions,
        event_unsubscriptions=event_unsubscriptions
    )
    
    # Write file
    file_path = f"frontend/views/{view_config['file_name']}"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print(f"✅ Created: {file_path}")

print("\\n✅ All view wrappers created!")
print(f"\\n📊 Total migrated: {len(views)} views")
