"""
SidebarLeft Widget - Navigation Sidebar
========================================

Collapsible navigation sidebar with icon-based menu items.

Features:
- 10 Navigation items (Home, Status, UDS3, etc.)
- Icons + Labels
- Active state highlighting
- Collapsible (min 50px, max 250px)
- Smooth animations
- Event-driven navigation

Version: 4.0.0 (Frontend Modernization)
Date: 14. Oktober 2025
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from frontend.core import EventBus, EventType
from frontend.core.event_bus import EventType

logger = logging.getLogger(__name__)


# Navigation Items Configuration
NAV_ITEMS = [
    ("home", "🏠", "Home Dashboard"),
    ("status", "📊", "System Status"),
    ("uds3", "📚", "UDS3 Datasets"),
    ("ingestion", "📥", "Ingestion"),
    ("db_health", "🗄️", "Database Health"),
    ("saga", "🔄", "SAGA Monitor"),
    ("security", "🔒", "Security & Audit"),
    ("errors", "❌", "Error Tracking"),
    ("golden", "⭐", "Golden Dataset"),
    ("recovery", "🔧", "Recovery"),  # NEW v3.4.8
]


class NavigationItem(ttk.Frame):
    """
    Single navigation item with icon and label
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        item_id: str,
        icon: str,
        label: str,
        on_click: Callable,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.item_id = item_id
        self.icon = icon
        self.label_text = label
        self.on_click = on_click
        self.is_active = False
        self.is_collapsed = False
        
        self._build_ui()
    
    def _build_ui(self):
        """Build navigation item UI"""
        # Button frame (acts as clickable area)
        self.button_frame = ttk.Frame(self, cursor="hand2")
        self.button_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Icon
        self.icon_label = ttk.Label(
            self.button_frame,
            text=self.icon,
            font=("Arial", 16),
            width=3,
            anchor=tk.W
        )
        self.icon_label.pack(side=tk.LEFT, padx=(5, 10))
        
        # Label
        self.text_label = ttk.Label(
            self.button_frame,
            text=self.label_text,
            font=("Arial", 10),
            anchor=tk.W
        )
        self.text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Bind click events
        self.button_frame.bind("<Button-1>", lambda e: self._on_clicked())
        self.icon_label.bind("<Button-1>", lambda e: self._on_clicked())
        self.text_label.bind("<Button-1>", lambda e: self._on_clicked())
        
        # Hover effects
        self.button_frame.bind("<Enter>", self._on_hover_enter)
        self.button_frame.bind("<Leave>", self._on_hover_leave)
    
    def _on_clicked(self):
        """Handle click"""
        self.on_click(self.item_id)
    
    def _on_hover_enter(self, event):
        """Handle mouse enter"""
        if not self.is_active:
            self.button_frame.configure(style="Hover.TFrame")
    
    def _on_hover_leave(self, event):
        """Handle mouse leave"""
        if not self.is_active:
            self.button_frame.configure(style="")
    
    def set_active(self, active: bool):
        """Set active state"""
        self.is_active = active
        if active:
            self.button_frame.configure(style="Active.TFrame")
            self.text_label.configure(font=("Arial", 10, "bold"))
        else:
            self.button_frame.configure(style="")
            self.text_label.configure(font=("Arial", 10))
    
    def set_collapsed(self, collapsed: bool):
        """Set collapsed state"""
        self.is_collapsed = collapsed
        if collapsed:
            self.text_label.pack_forget()
        else:
            self.text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)


class SidebarLeft(ttk.Frame):
    """
    Left Navigation Sidebar
    
    Collapsible sidebar with icon-based navigation menu.
    
    Layout (Expanded - 250px):
    ┌──────────────────────┐
    │ 🏠 Home Dashboard    │
    │ 📊 System Status     │
    │ 📚 UDS3 Datasets     │
    │ 📥 Ingestion         │
    │ 🗄️ Database Health   │
    │ 🔄 SAGA Monitor      │
    │ 🔒 Security & Audit  │
    │ ❌ Error Tracking    │
    │ ⭐ Golden Dataset    │
    │ 🔧 Recovery          │
    └──────────────────────┘
    
    Layout (Collapsed - 50px):
    ┌────┐
    │ 🏠 │
    │ 📊 │
    │ 📚 │
    │ 📥 │
    │ 🗄️ │
    │ 🔄 │
    │ 🔒 │
    │ ❌ │
    │ ⭐ │
    │ 🔧 │
    └────┘
    
    Example:
        >>> sidebar = SidebarLeft(
        >>>     parent=root,
        >>>     event_bus=event_bus,
        >>>     on_navigate=lambda item_id: print(f"Navigate to: {item_id}")
        >>> )
        >>> sidebar.pack(side=tk.LEFT, fill=tk.Y)
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        event_bus: Optional[EventBus] = None,
        on_navigate: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        Initialize SidebarLeft
        
        Args:
            parent: Parent widget
            event_bus: EventBus instance
            on_navigate: Callback when navigation item is clicked (item_id)
            **kwargs: Additional arguments for ttk.Frame
        """
        super().__init__(parent, width=250, **kwargs)
        
        self.event_bus = event_bus
        self.on_navigate = on_navigate
        
        # State
        self._collapsed = False
        self._active_item = None
        self._nav_items: List[NavigationItem] = []
        
        # Build UI
        self._build_ui()
        
        # Set default active item
        self.set_active("home")
        
        logger.debug("SidebarLeft initialized")
    
    def _build_ui(self):
        """Build sidebar UI"""
        # Prevent frame from shrinking
        self.pack_propagate(False)
        
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(10, 5))
        
        self.header_label = ttk.Label(
            header_frame,
            text="Navigation",
            font=("Arial", 12, "bold"),
            anchor=tk.W
        )
        self.header_label.pack(padx=15)
        
        # Separator
        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=5)
        
        # Navigation items container
        nav_container = ttk.Frame(self)
        nav_container.pack(fill=tk.BOTH, expand=True)
        
        # Create navigation items
        for item_id, icon, label in NAV_ITEMS:
            nav_item = NavigationItem(
                parent=nav_container,
                item_id=item_id,
                icon=icon,
                label=label,
                on_click=self._on_item_clicked
            )
            nav_item.pack(fill=tk.X)
            self._nav_items.append(nav_item)
        
        # Footer (collapse button)
        footer_frame = ttk.Frame(self)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        self.collapse_button = ttk.Button(
            footer_frame,
            text="◀",
            width=3,
            command=self.toggle_collapse
        )
        self.collapse_button.pack(side=tk.RIGHT, padx=10)
    
    def _on_item_clicked(self, item_id: str):
        """Handle navigation item click"""
        logger.debug(f"Navigation: {item_id}")
        
        # Set active
        self.set_active(item_id)
        
        # Callback
        if self.on_navigate:
            self.on_navigate(item_id)
        
        # Emit navigation event
        if self.event_bus:
            # Get item label
            label = next((label for id, _, label in NAV_ITEMS if id == item_id), item_id)
            logger.info(f"Emitting navigation event for: {label}")
            
            self.event_bus.emit(
                EventType.SIDEBAR_LEFT_NAVIGATE,
                {
                    "view": label,  # Use label (e.g., "Home", "Recovery")
                    "item_id": item_id
                },
                source="SidebarLeft"
            )
    
    def set_active(self, item_id: str):
        """
        Set active navigation item
        
        Args:
            item_id: ID of the item to set as active
        """
        self._active_item = item_id
        
        for nav_item in self._nav_items:
            nav_item.set_active(nav_item.item_id == item_id)
        
        logger.debug(f"Active item set: {item_id}")
    
    def toggle_collapse(self):
        """Toggle sidebar collapse state"""
        self._collapsed = not self._collapsed
        
        if self._collapsed:
            # Collapse
            self.configure(width=50)
            self.header_label.pack_forget()
            self.collapse_button.configure(text="▶")
            
            for nav_item in self._nav_items:
                nav_item.set_collapsed(True)
        else:
            # Expand
            self.configure(width=250)
            self.header_label.pack(padx=15)
            self.collapse_button.configure(text="◀")
            
            for nav_item in self._nav_items:
                nav_item.set_collapsed(False)
        
        # Emit event
        if self.event_bus:
            self.event_bus.emit(
                EventType.BACKEND_CONNECTED,  # Placeholder
                {
                    "action": "sidebar_collapse",
                    "collapsed": self._collapsed
                },
                source="SidebarLeft"
            )
        
        logger.debug(f"Sidebar collapsed: {self._collapsed}")
    
    def is_collapsed(self) -> bool:
        """Check if sidebar is collapsed"""
        return self._collapsed
    
    def get_active_item(self) -> Optional[str]:
        """Get currently active item ID"""
        return self._active_item
