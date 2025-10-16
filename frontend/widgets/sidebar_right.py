"""
SidebarRight Widget - Phase 2: UI Components

Right sidebar showing:
- Quick Stats (Backend status, jobs, documents, success rate)
- Recent Activity Feed (last 10 events, auto-scroll)
- Quick Actions (Upload, Query, Logs buttons)

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 2)
Date: 14.10.2025, 09:50 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
from frontend.core.event_bus import EventType


class QuickStatsCard(ttk.Frame):
    """Quick statistics card showing system metrics."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()
    
    def _build_ui(self):
        """Build the quick stats UI."""
        # Header
        header = ttk.Label(
            self,
            text="📊 Quick Stats",
            font=("Segoe UI", 11, "bold")
        )
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        # Stats container
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Backend Status
        self._backend_frame = self._create_stat_row(
            stats_frame,
            "Backend:",
            "⚪ Disconnected",
            row=0
        )
        
        # Active Jobs
        self._jobs_frame = self._create_stat_row(
            stats_frame,
            "Active Jobs:",
            "0",
            row=1
        )
        
        # Total Documents
        self._docs_frame = self._create_stat_row(
            stats_frame,
            "Documents:",
            "0",
            row=2
        )
        
        # Success Rate
        self._success_frame = self._create_stat_row(
            stats_frame,
            "Success Rate:",
            "0%",
            row=3
        )
        
        # Separator
        separator = ttk.Separator(self, orient="horizontal")
        separator.pack(fill="x", padx=10, pady=10)
    
    def _create_stat_row(self, parent, label_text: str, value_text: str, row: int):
        """Create a single stat row."""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=3)
        parent.columnconfigure(0, weight=1)
        
        # Label
        label = ttk.Label(
            frame,
            text=label_text,
            font=("Segoe UI", 9)
        )
        label.pack(side="left")
        
        # Value
        value = ttk.Label(
            frame,
            text=value_text,
            font=("Segoe UI", 9, "bold")
        )
        value.pack(side="right")
        
        return {"label": label, "value": value}
    
    def update_backend_status(self, connected: bool):
        """Update backend connection status."""
        if connected:
            self._backend_frame["value"].config(
                text="🟢 Connected",
                foreground="green"
            )
        else:
            self._backend_frame["value"].config(
                text="🔴 Disconnected",
                foreground="red"
            )
    
    def update_active_jobs(self, count: int):
        """Update active jobs count."""
        self._jobs_frame["value"].config(text=str(count))
    
    def update_total_documents(self, count: int):
        """Update total documents count."""
        self._docs_frame["value"].config(text=f"{count:,}")
    
    def update_success_rate(self, rate: float):
        """Update success rate percentage."""
        color = "green" if rate >= 90 else "orange" if rate >= 70 else "red"
        self._success_frame["value"].config(
            text=f"{rate:.1f}%",
            foreground=color
        )


class ActivityFeedItem(ttk.Frame):
    """Single activity feed item."""
    
    def __init__(self, parent, timestamp: str, message: str, **kwargs):
        super().__init__(parent, **kwargs)
        self._timestamp = timestamp
        self._message = message
        self._build_ui()
    
    def _build_ui(self):
        """Build the activity item UI."""
        # Container with padding
        container = ttk.Frame(self)
        container.pack(fill="x", padx=5, pady=2)
        
        # Timestamp
        time_label = ttk.Label(
            container,
            text=self._timestamp,
            font=("Segoe UI", 8),
            foreground="gray"
        )
        time_label.pack(anchor="w")
        
        # Message
        msg_label = ttk.Label(
            container,
            text=self._message,
            font=("Segoe UI", 9),
            wraplength=250
        )
        msg_label.pack(anchor="w")
        
        # Separator
        separator = ttk.Separator(self, orient="horizontal")
        separator.pack(fill="x", pady=2)


class RecentActivityFeed(ttk.Frame):
    """Recent activity feed showing last events."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._max_items = 10
        self._items: List[ActivityFeedItem] = []
        self._build_ui()
    
    def _build_ui(self):
        """Build the activity feed UI."""
        # Header
        header = ttk.Label(
            self,
            text="📝 Recent Activity",
            font=("Segoe UI", 11, "bold")
        )
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        # Scrollable container
        canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        
        self._scrollable_frame = ttk.Frame(canvas)
        self._scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self._scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")
        
        self._canvas = canvas
        
        # Add placeholder if empty
        self._add_placeholder()
    
    def _add_placeholder(self):
        """Add placeholder text when feed is empty."""
        placeholder = ttk.Label(
            self._scrollable_frame,
            text="No recent activity",
            font=("Segoe UI", 9, "italic"),
            foreground="gray"
        )
        placeholder.pack(pady=20)
    
    def add_activity(self, message: str, timestamp: Optional[datetime] = None):
        """Add a new activity to the feed."""
        # Remove placeholder if exists
        for widget in self._scrollable_frame.winfo_children():
            widget.destroy()
        
        # Format timestamp
        if timestamp is None:
            timestamp = datetime.now()
        time_str = timestamp.strftime("%H:%M:%S")
        
        # Create new item
        item = ActivityFeedItem(
            self._scrollable_frame,
            timestamp=time_str,
            message=message
        )
        item.pack(fill="x")
        
        # Add to items list
        self._items.insert(0, item)
        
        # Limit to max items
        if len(self._items) > self._max_items:
            removed = self._items.pop()
            removed.destroy()
        
        # Auto-scroll to top (newest)
        self._canvas.yview_moveto(0)
    
    def clear(self):
        """Clear all activities."""
        for item in self._items:
            item.destroy()
        self._items.clear()
        self._add_placeholder()


class QuickActionsPanel(ttk.Frame):
    """Quick action buttons panel."""
    
    def __init__(
        self,
        parent,
        on_upload: Optional[Callable] = None,
        on_query: Optional[Callable] = None,
        on_logs: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self._on_upload = on_upload
        self._on_query = on_query
        self._on_logs = on_logs
        self._build_ui()
    
    def _build_ui(self):
        """Build the quick actions UI."""
        # Header
        header = ttk.Label(
            self,
            text="⚡ Quick Actions",
            font=("Segoe UI", 11, "bold")
        )
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        # Buttons container
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        # Upload button
        upload_btn = ttk.Button(
            buttons_frame,
            text="📤 Upload Files",
            command=self._on_upload_clicked
        )
        upload_btn.pack(fill="x", pady=3)
        
        # Query button
        query_btn = ttk.Button(
            buttons_frame,
            text="🔍 Search Documents",
            command=self._on_query_clicked
        )
        query_btn.pack(fill="x", pady=3)
        
        # Logs button
        logs_btn = ttk.Button(
            buttons_frame,
            text="📋 View Logs",
            command=self._on_logs_clicked
        )
        logs_btn.pack(fill="x", pady=3)
    
    def _on_upload_clicked(self):
        """Handle upload button click."""
        if self._on_upload:
            self._on_upload()
    
    def _on_query_clicked(self):
        """Handle query button click."""
        if self._on_query:
            self._on_query()
    
    def _on_logs_clicked(self):
        """Handle logs button click."""
        if self._on_logs:
            self._on_logs()


class SidebarRight(ttk.Frame):
    """
    Right sidebar with quick stats, activity feed, and quick actions.
    
    Features:
    - Quick Stats Card (backend status, jobs, documents, success rate)
    - Recent Activity Feed (last 10 events, auto-scroll)
    - Quick Actions Panel (upload, query, logs buttons)
    - Width: 300px (collapsible)
    - Event emission for all actions
    
    Example:
        sidebar = SidebarRight(
            parent,
            event_bus,
            on_upload=lambda: print("Upload"),
            on_query=lambda: print("Query"),
            on_logs=lambda: print("Logs")
        )
        sidebar.pack(side="right", fill="y")
        
        # Update stats
        sidebar.update_backend_status(True)
        sidebar.update_active_jobs(5)
        
        # Add activity
        sidebar.add_activity("Job #123 completed successfully")
    """
    
    def __init__(
        self,
        parent,
        event_bus,
        on_upload: Optional[Callable] = None,
        on_query: Optional[Callable] = None,
        on_logs: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self._event_bus = event_bus
        self._on_upload = on_upload
        self._on_query = on_query
        self._on_logs = on_logs
        self._collapsed = False
        
        self.config(width=300, relief="solid", borderwidth=1)
        self.pack_propagate(False)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the sidebar UI."""
        # Header with collapse button
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        header_label = ttk.Label(
            header_frame,
            text="Info & Actions",
            font=("Segoe UI", 12, "bold")
        )
        header_label.pack(side="left")
        
        # Collapse button
        self._collapse_btn = ttk.Button(
            header_frame,
            text="▶",
            width=3,
            command=self.toggle_collapse
        )
        self._collapse_btn.pack(side="right")
        
        # Content container (hidden when collapsed)
        self._content_frame = ttk.Frame(self)
        self._content_frame.pack(fill="both", expand=True)
        
        # Quick Stats Card
        self._stats_card = QuickStatsCard(self._content_frame)
        self._stats_card.pack(fill="x")
        
        # Recent Activity Feed
        self._activity_feed = RecentActivityFeed(self._content_frame)
        self._activity_feed.pack(fill="both", expand=True, pady=10)
        
        # Quick Actions Panel
        self._actions_panel = QuickActionsPanel(
            self._content_frame,
            on_upload=self._handle_upload,
            on_query=self._handle_query,
            on_logs=self._handle_logs
        )
        self._actions_panel.pack(fill="x")
    
    def toggle_collapse(self):
        """Toggle sidebar collapse state."""
        self._collapsed = not self._collapsed
        
        if self._collapsed:
            # Collapsed: Hide content, change button
            self._content_frame.pack_forget()
            self._collapse_btn.config(text="◀")
            self.config(width=50)
        else:
            # Expanded: Show content, change button
            self._content_frame.pack(fill="both", expand=True)
            self._collapse_btn.config(text="▶")
            self.config(width=300)
        
        # Emit event
        if self._event_bus:
            self._event_bus.emit_sync(
                "SIDEBAR_RIGHT_TOGGLED",
                {"collapsed": self._collapsed}
            )
    
    def is_collapsed(self) -> bool:
        """Check if sidebar is collapsed."""
        return self._collapsed
    
    # Stats Card Methods
    
    def update_backend_status(self, connected: bool):
        """Update backend connection status."""
        self._stats_card.update_backend_status(connected)
    
    def update_active_jobs(self, count: int):
        """Update active jobs count."""
        self._stats_card.update_active_jobs(count)
    
    def update_total_documents(self, count: int):
        """Update total documents count."""
        self._stats_card.update_total_documents(count)
    
    def update_success_rate(self, rate: float):
        """Update success rate percentage."""
        self._stats_card.update_success_rate(rate)
    
    # Activity Feed Methods
    
    def add_activity(self, message: str, timestamp: Optional[datetime] = None):
        """Add activity to feed."""
        self._activity_feed.add_activity(message, timestamp)
    
    def clear_activity(self):
        """Clear all activities."""
        self._activity_feed.clear()
    
    # Quick Actions Handlers
    
    def _handle_upload(self):
        """Handle upload action."""
        if self._event_bus:
            self._event_bus.emit_sync(EventType.QUICK_ACTION_UPLOAD, {})
        if self._on_upload:
            self._on_upload()
    
    def _handle_query(self):
        """Handle query action."""
        if self._event_bus:
            self._event_bus.emit_sync(EventType.QUICK_ACTION_QUERY, {})
        if self._on_query:
            self._on_query()
    
    def _handle_logs(self):
        """Handle logs action."""
        if self._event_bus:
            self._event_bus.emit_sync(EventType.QUICK_ACTION_LOGS, {})
        if self._on_logs:
            self._on_logs()


# Export
__all__ = [
    "SidebarRight",
    "QuickStatsCard",
    "RecentActivityFeed",
    "QuickActionsPanel",
]
