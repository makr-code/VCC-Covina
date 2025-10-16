"""
Base View - Abstract Base Class for Frontend Views
===================================================

Enforces strict separation of UI and business logic.
All views must inherit from BaseView and implement abstract methods.

Version: 4.0.0 (Frontend Modernization)
Date: 14. Oktober 2025
"""

import logging
import tkinter as tk
from abc import ABC, abstractmethod
from tkinter import ttk
from typing import Any, Dict, Optional

from frontend.core.event_bus import EventBus

logger = logging.getLogger(__name__)


# ============================================================================
# BaseView Abstract Class
# ============================================================================

class BaseView(ttk.Frame, ABC):
    """
    Abstract Base Class für alle Frontend-Views
    
    Enforces strict OOP and separation of concerns:
    - build_ui(): Pure UI construction (no business logic)
    - update_data(): Pure business logic (no UI construction)
    - on_activate(): Lifecycle hook when view becomes visible
    - on_deactivate(): Lifecycle hook when view becomes hidden
    
    Features:
    - Event-driven architecture via EventBus
    - Lifecycle management
    - Thread-safe data updates
    - Consistent view pattern
    
    Example:
        >>> class MyView(BaseView):
        >>>     def build_ui(self):
        >>>         self.label = ttk.Label(self, text="Hello World")
        >>>         self.label.pack()
        >>>     
        >>>     def update_data(self, data: Dict[str, Any]):
        >>>         self.label.config(text=data.get("message", ""))
        >>>     
        >>>     def on_activate(self):
        >>>         self.event_bus.subscribe(EventType.BACKEND_CONNECTED, self._on_backend_connected)
        >>>     
        >>>     def on_deactivate(self):
        >>>         self.event_bus.unsubscribe(EventType.BACKEND_CONNECTED, self._on_backend_connected)
        >>>     
        >>>     def _on_backend_connected(self, event):
        >>>         self.update_data({"message": "Backend connected!"})
    """
    
    def __init__(self, parent: tk.Widget, event_bus: EventBus, **kwargs):
        """
        Initialize BaseView
        
        Args:
            parent: Parent widget
            event_bus: EventBus instance for event subscription
            **kwargs: Additional arguments for ttk.Frame
        """
        super().__init__(parent, **kwargs)
        self.event_bus = event_bus
        self.data: Optional[Dict[str, Any]] = None
        self._is_active = False
        
        # Build UI (pure UI construction)
        self.build_ui()
        
        logger.debug(f"{self.__class__.__name__} initialized")
    
    # ========================================================================
    # Abstract Methods (MUST be implemented by subclasses)
    # ========================================================================
    
    @abstractmethod
    def build_ui(self):
        """
        Build UI components (pure UI construction)
        
        This method should ONLY create UI widgets, set layouts, and configure styles.
        NO business logic, NO data fetching, NO event subscriptions.
        
        Example:
            def build_ui(self):
                # Create widgets
                self.title_label = ttk.Label(self, text="My View", font=("Arial", 16, "bold"))
                self.content_frame = ttk.Frame(self)
                self.status_label = ttk.Label(self, text="Status: Unknown")
                
                # Layout
                self.title_label.pack(pady=10)
                self.content_frame.pack(fill=tk.BOTH, expand=True)
                self.status_label.pack(pady=5)
        """
        pass
    
    @abstractmethod
    def update_data(self, data: Dict[str, Any]):
        """
        Update view with new data (pure business logic)
        
        This method should ONLY process data and update widget values.
        NO UI construction, NO widget creation, NO event subscriptions.
        
        Args:
            data: Dictionary with data to display
        
        Example:
            def update_data(self, data: Dict[str, Any]):
                # Store data
                self.data = data
                
                # Update widgets
                self.status_label.config(text=f"Status: {data.get('status', 'Unknown')}")
                
                # Update content
                for widget in self.content_frame.winfo_children():
                    widget.destroy()
                
                for item in data.get('items', []):
                    label = ttk.Label(self.content_frame, text=item['name'])
                    label.pack()
        """
        pass
    
    @abstractmethod
    def on_activate(self):
        """
        Lifecycle hook: View becomes visible
        
        This method is called when the view tab is selected or window is shown.
        Use this to:
        - Subscribe to events
        - Start timers
        - Fetch initial data
        - Enable auto-refresh
        
        Example:
            def on_activate(self):
                # Subscribe to events
                self.event_bus.subscribe(EventType.JOB_STATUS_CHANGED, self._on_job_status_changed)
                
                # Fetch initial data
                self.fetch_data()
                
                # Start auto-refresh
                self._refresh_timer_active = True
                self._auto_refresh()
        """
        pass
    
    @abstractmethod
    def on_deactivate(self):
        """
        Lifecycle hook: View becomes hidden
        
        This method is called when another view tab is selected or window is hidden.
        Use this to:
        - Unsubscribe from events
        - Stop timers
        - Cancel pending operations
        - Disable auto-refresh
        
        Example:
            def on_deactivate(self):
                # Unsubscribe from events
                self.event_bus.unsubscribe(EventType.JOB_STATUS_CHANGED, self._on_job_status_changed)
                
                # Stop auto-refresh
                self._refresh_timer_active = False
        """
        pass
    
    # ========================================================================
    # Helper Methods (provided by BaseView)
    # ========================================================================
    
    def is_active(self) -> bool:
        """Check if view is currently active"""
        return self._is_active
    
    def set_active(self, active: bool):
        """
        Set view active state and trigger lifecycle hooks
        
        Args:
            active: True if view becomes visible, False if hidden
        """
        if active and not self._is_active:
            self._is_active = True
            self.on_activate()
            logger.debug(f"{self.__class__.__name__} activated")
        elif not active and self._is_active:
            self._is_active = False
            self.on_deactivate()
            logger.debug(f"{self.__class__.__name__} deactivated")
    
    def safe_update_data(self, data: Dict[str, Any]):
        """
        Thread-safe data update wrapper
        
        Ensures update_data() is called on the main Tkinter thread.
        Use this when updating from background threads (e.g., TaskExecutor callbacks).
        
        Args:
            data: Dictionary with data to display
        """
        if self.winfo_exists():
            self.after(0, lambda: self.update_data(data))
        else:
            logger.warning(f"{self.__class__.__name__}.safe_update_data() called on destroyed widget")
    
    def show_message(self, title: str, message: str, message_type: str = "info"):
        """
        Show message box (convenience method)
        
        Args:
            title: Message box title
            message: Message text
            message_type: "info", "warning", "error", "success"
        """
        from tkinter import messagebox
        
        if message_type == "error":
            messagebox.showerror(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        elif message_type == "success":
            messagebox.showinfo(title, message)
        else:
            messagebox.showinfo(title, message)
    
    def destroy(self):
        """Override destroy to ensure cleanup"""
        if self._is_active:
            self.set_active(False)
        super().destroy()
        logger.debug(f"{self.__class__.__name__} destroyed")


# ============================================================================
# Example Implementation (for documentation)
# ============================================================================

"""
Example View Implementation:

```python
from frontend.core.event_bus import EventType
from frontend.views.base_view import BaseView

class ExampleView(BaseView):
    '''Example view demonstrating BaseView usage'''
    
    def build_ui(self):
        # Header
        self.title_label = ttk.Label(
            self, 
            text="Example View", 
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(pady=10)
        
        # Content
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Status bar
        self.status_label = ttk.Label(self, text="Status: Waiting...")
        self.status_label.pack(pady=5)
        
        # Refresh button
        self.refresh_button = ttk.Button(
            self, 
            text="Refresh", 
            command=self.fetch_data
        )
        self.refresh_button.pack(pady=10)
    
    def update_data(self, data: Dict[str, Any]):
        # Store data
        self.data = data
        
        # Update status
        status = data.get('status', 'Unknown')
        self.status_label.config(text=f"Status: {status}")
        
        # Update content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        items = data.get('items', [])
        if items:
            for item in items:
                label = ttk.Label(
                    self.content_frame, 
                    text=f"• {item['name']}"
                )
                label.pack(anchor=tk.W)
        else:
            no_data_label = ttk.Label(
                self.content_frame, 
                text="No data available"
            )
            no_data_label.pack()
    
    def on_activate(self):
        # Subscribe to events
        self.event_bus.subscribe(
            EventType.BACKEND_CONNECTED, 
            self._on_backend_connected
        )
        self.event_bus.subscribe(
            EventType.JOB_STATUS_CHANGED, 
            self._on_job_status_changed
        )
        
        # Fetch initial data
        self.fetch_data()
    
    def on_deactivate(self):
        # Unsubscribe from events
        self.event_bus.unsubscribe(
            EventType.BACKEND_CONNECTED, 
            self._on_backend_connected
        )
        self.event_bus.unsubscribe(
            EventType.JOB_STATUS_CHANGED, 
            self._on_job_status_changed
        )
    
    def fetch_data(self):
        '''Fetch data from backend (example)'''
        # This would typically call backend_service methods
        # which emit events that trigger update_data()
        pass
    
    def _on_backend_connected(self, event):
        '''Handle backend connected event'''
        self.safe_update_data({"status": "Connected"})
    
    def _on_job_status_changed(self, event):
        '''Handle job status changed event'''
        jobs = event.data.get('jobs', [])
        self.safe_update_data({"status": "Jobs Updated", "items": jobs})
```
"""
