"""
View Manager - Phase 4: Integration & Polish

Manages dynamic view switching with lifecycle hooks.
Handles activation/deactivation of all views.

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 4)
Date: 14.10.2025, 11:35 Uhr
"""

import tkinter as tk
from typing import Dict, Optional
import logging

from frontend.views.base_view import BaseView


logger = logging.getLogger(__name__)


class ViewManager:
    """
    View Manager (Dynamic View Switching).
    
    Manages lifecycle of all views:
    - Activate view (subscribe to events, load data)
    - Deactivate view (unsubscribe, cleanup)
    - Switch views (deactivate old, activate new)
    """
    
    def __init__(self, container: tk.Widget):
        """
        Initialize ViewManager.
        
        Args:
            container: Parent widget where views will be displayed
        """
        self.container = container
        self.views: Dict[str, BaseView] = {}
        self.current_view_name: Optional[str] = None
        self.current_view: Optional[BaseView] = None
        
        logger.info("ViewManager initialized")
    
    def register_view(self, name: str, view: BaseView):
        """
        Register a view for management.
        
        Args:
            name: Unique identifier for the view (e.g., "home", "recovery")
            view: View instance (must inherit from BaseView)
        """
        if not isinstance(view, BaseView):
            raise TypeError(f"View must inherit from BaseView, got {type(view)}")
        
        if name in self.views:
            logger.warning(f"View '{name}' already registered, overwriting")
        
        self.views[name] = view
        logger.info(f"Registered view: {name} ({view.__class__.__name__})")
    
    def switch_view(self, view_name: str) -> bool:
        """
        Switch to a different view.
        
        Lifecycle:
        1. Deactivate current view (unsubscribe events, cleanup)
        2. Hide current view (pack_forget)
        3. Show new view (pack)
        4. Activate new view (subscribe events, load data)
        
        Args:
            view_name: Name of the view to switch to
        
        Returns:
            True if switch was successful, False otherwise
        """
        # Validate view exists
        if view_name not in self.views:
            logger.error(f"View '{view_name}' not registered")
            return False
        
        # Skip if already showing this view
        if self.current_view_name == view_name:
            logger.debug(f"View '{view_name}' already active")
            return True
        
        new_view = self.views[view_name]
        
        try:
            # Step 1 & 2: Deactivate and hide current view
            if self.current_view:
                logger.debug(f"Deactivating view: {self.current_view_name}")
                self.current_view.on_deactivate()
                self.current_view.pack_forget()
            
            # Step 3: Show new view
            logger.debug(f"Showing view: {view_name}")
            new_view.pack(fill="both", expand=True)
            
            # Step 4: Activate new view
            logger.debug(f"Activating view: {view_name}")
            new_view.on_activate()
            
            # Update state
            self.current_view_name = view_name
            self.current_view = new_view
            
            logger.info(f"✅ Switched to view: {view_name}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to switch to view '{view_name}': {e}", exc_info=True)
            
            # Try to recover by showing home view
            if view_name != "home" and "home" in self.views:
                logger.info("Attempting recovery: switching to home view")
                return self.switch_view("home")
            
            return False
    
    def get_current_view_name(self) -> Optional[str]:
        """Get name of currently active view."""
        return self.current_view_name
    
    def get_current_view(self) -> Optional[BaseView]:
        """Get currently active view instance."""
        return self.current_view
    
    def get_view(self, view_name: str) -> Optional[BaseView]:
        """
        Get view instance by name.
        
        Args:
            view_name: Name of the view
        
        Returns:
            View instance or None if not found
        """
        return self.views.get(view_name)
    
    def list_views(self) -> list[str]:
        """Get list of all registered view names."""
        return list(self.views.keys())
    
    def deactivate_current_view(self):
        """Deactivate and hide current view (cleanup)."""
        if self.current_view:
            logger.debug(f"Deactivating current view: {self.current_view_name}")
            self.current_view.on_deactivate()
            self.current_view.pack_forget()
            self.current_view = None
            self.current_view_name = None
    
    def cleanup(self):
        """Cleanup all views (call on app exit)."""
        logger.info("Cleaning up ViewManager...")
        
        # Deactivate current view
        self.deactivate_current_view()
        
        # Cleanup all views
        for name, view in self.views.items():
            try:
                if hasattr(view, 'cleanup'):
                    view.cleanup()
                view.destroy()
            except Exception as e:
                logger.error(f"Error cleaning up view '{name}': {e}")
        
        self.views.clear()
        logger.info("✅ ViewManager cleanup complete")


# Export
__all__ = ["ViewManager"]
