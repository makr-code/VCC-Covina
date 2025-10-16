"""
Debug-Skript für Covina v4.0.1
==============================

Testet UI-Layout und Navigation
"""

import tkinter as tk
from tkinter import ttk
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Covina app
from covina_app_phase4 import CovinaApp

def debug_widget_tree(widget, indent=0):
    """Print widget tree for debugging"""
    prefix = "  " * indent
    widget_info = f"{prefix}{widget.__class__.__name__}"
    
    if hasattr(widget, 'winfo_manager'):
        manager = widget.winfo_manager()
        widget_info += f" [manager: {manager}]"
    
    if hasattr(widget, 'winfo_ismapped'):
        mapped = widget.winfo_ismapped()
        widget_info += f" [visible: {mapped}]"
    
    if hasattr(widget, 'winfo_width'):
        width = widget.winfo_width()
        height = widget.winfo_height()
        widget_info += f" [size: {width}x{height}]"
    
    print(widget_info)
    
    # Recurse for children
    for child in widget.winfo_children():
        debug_widget_tree(child, indent + 1)

def main():
    """Run debug test"""
    print("=" * 60)
    print("Covina v4.0.1 - Debug Test")
    print("=" * 60)
    
    # Create app
    app = CovinaApp()
    
    # Wait for UI to render
    app.update()
    
    print("\n" + "=" * 60)
    print("Widget Tree:")
    print("=" * 60)
    debug_widget_tree(app)
    
    print("\n" + "=" * 60)
    print("ViewManager Status:")
    print("=" * 60)
    print(f"Registered views: {list(app.view_manager.views.keys())}")
    print(f"Current view: {app.view_manager.current_view_name}")
    print(f"Current view instance: {app.view_manager.current_view}")
    
    print("\n" + "=" * 60)
    print("UI Components:")
    print("=" * 60)
    print(f"Toolbar: {app.toolbar} [visible: {app.toolbar.winfo_ismapped()}]")
    print(f"Sidebar Left: {app.sidebar_left} [visible: {app.sidebar_left.winfo_ismapped()}]")
    print(f"Sidebar Right: {app.sidebar_right} [visible: {app.sidebar_right.winfo_ismapped()}]")
    print(f"Terminal: {app.terminal} [visible: {app.terminal.winfo_ismapped()}]")
    print(f"Status Bar: {app.status_bar} [visible: {app.status_bar.winfo_ismapped()}]")
    print(f"Content Area: {app.content_area} [visible: {app.content_area.winfo_ismapped()}]")
    
    print("\n" + "=" * 60)
    print("Testing Navigation...")
    print("=" * 60)
    
    # Test view switching
    test_views = ["home", "recovery", "uds3"]
    for view_name in test_views:
        print(f"\nSwitching to: {view_name}")
        success = app.view_manager.switch_view(view_name)
        print(f"  Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"  Current view: {app.view_manager.current_view_name}")
        app.update()
    
    print("\n" + "=" * 60)
    print("Starting main loop...")
    print("=" * 60)
    print("Window should be visible with all UI components.")
    print("Try clicking navigation items in left sidebar.")
    print("Close window to exit.")
    
    # Run app
    app.mainloop()

if __name__ == "__main__":
    main()
