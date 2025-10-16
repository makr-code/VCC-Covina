"""
Simple Navigation Test - Check if clicks work
"""
import tkinter as tk
from tkinter import ttk
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path
covina_root = Path(__file__).parent
sys.path.insert(0, str(covina_root))
os.chdir(covina_root)

# Disable WebSocket
os.environ['DISABLE_WEBSOCKET'] = '1'

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from frontend.core.event_bus import EventBus, EventType
from frontend.widgets.sidebar_left import SidebarLeft
from frontend.core.view_manager import ViewManager
from frontend.views.base_view import BaseView

print("=" * 60)
print("Navigation Test - v4.0.2")
print("=" * 60)
print()
print("Instructions:")
print("1. Click on navigation items in left sidebar")
print("2. Watch console for event logs")
print("3. Check if content area changes")
print()
print("=" * 60)

class TestView(BaseView):
    """Simple test view with label"""
    def __init__(self, parent, event_bus, view_name):
        self.view_name = view_name
        super().__init__(parent, event_bus)
    
    def build_ui(self):
        """Build UI"""
        label = ttk.Label(
            self,
            text=f"📄 {self.view_name} View\n\nNavigation working!",
            font=("Arial", 24),
            justify="center"
        )
        label.pack(expand=True)
        print(f"  ✅ Built {self.view_name} view")
    
    def on_activate(self):
        """Activate view"""
        print(f"  🟢 {self.view_name} activated")
    
    def on_deactivate(self):
        """Deactivate view"""
        print(f"  🔴 {self.view_name} deactivated")
    
    def update_data(self):
        """Update view data"""
        pass  # Not needed for test

root = tk.Tk()
root.title("Navigation Test - v4.0.2")
root.geometry("1000x600")

# Create EventBus
event_bus = EventBus()
event_bus.start()  # ⚠️ CRITICAL: Start dispatch thread!

# Layout
main_frame = ttk.Frame(root)
main_frame.pack(fill="both", expand=True)

# Left Sidebar
sidebar = SidebarLeft(
    main_frame,
    event_bus=event_bus,
    on_navigate=None
)
sidebar.pack(side="left", fill="y")

# Content Area
content_area = ttk.Frame(main_frame, relief="solid", borderwidth=2)
content_area.pack(side="left", fill="both", expand=True)

# ViewManager
view_manager = ViewManager(content_area)

# Register 10 test views
print("\nRegistering views:")
view_names = [
    "home", "recovery", "system_status", "ingestion", "database_health",
    "security", "error_tracking", "golden_dataset", "uds3", "saga"
]

for view_name in view_names:
    view = TestView(content_area, event_bus, view_name.upper())
    view_manager.register_view(view_name, view)

# Show initial view
print("\nShowing initial view (home)...")
view_manager.switch_view("home")

# Subscribe to navigation events
def on_navigate(event):
    """Handle navigation"""
    view_name = event.data.get("view")
    print(f"\n🔔 Navigation Event Received: {view_name}")
    
    # Map label to view name
    mapping = {
        "Home": "home",
        "Recovery": "recovery",
        "System Status": "system_status",
        "Ingestion": "ingestion",
        "Database Health": "database_health",
        "Security": "security",
        "Error Tracking": "error_tracking",
        "Golden Dataset": "golden_dataset",
        "UDS3": "uds3",
        "SAGA": "saga",
    }
    
    target = mapping.get(view_name, view_name.lower().replace(" ", "_"))
    print(f"  → Switching to: {target}")
    
    success = view_manager.switch_view(target)
    if success:
        print(f"  ✅ Switch successful!")
    else:
        print(f"  ❌ Switch failed!")

event_bus.subscribe(EventType.SIDEBAR_LEFT_NAVIGATE, on_navigate)

print("\n" + "=" * 60)
print("✅ Setup complete! Try clicking navigation items...")
print("=" * 60)

root.mainloop()
