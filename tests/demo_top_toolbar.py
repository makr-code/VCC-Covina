"""
TopToolbar Demo - Phase 2 Test
===============================

Demo application for TopToolbar component.

Version: 4.0.0 (Frontend Modernization)
Date: 14. Oktober 2025
"""

import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.core import EventBus, EventType
from frontend.widgets.top_toolbar import TopToolbar


def main():
    """Demo application"""
    # Create window
    root = tk.Tk()
    root.title("TopToolbar Demo - Phase 2")
    root.geometry("900x600")
    
    # Create EventBus
    event_bus = EventBus()
    event_bus.start()
    
    # Event handler
    events_log = []
    
    def on_toolbar_event(event):
        action = event.data.get('action', 'unknown')
        timestamp = event.timestamp.strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {action}"
        events_log.append(log_entry)
        
        # Update UI
        log_text.delete('1.0', tk.END)
        log_text.insert('1.0', '\n'.join(reversed(events_log[-10:])))  # Last 10
        
        if action == 'sidebar_toggle':
            visible = event.data.get('visible', True)
            status_label.config(
                text=f"Status: Sidebar {'Visible' if visible else 'Hidden'}"
            )
        elif action == 'settings_open':
            status_label.config(text="Status: Settings opened")
        elif action == 'profile_open':
            status_label.config(text="Status: Profile opened")
    
    event_bus.subscribe(EventType.BACKEND_CONNECTED, on_toolbar_event)
    
    # Create toolbar
    toolbar = TopToolbar(
        parent=root,
        event_bus=event_bus,
        on_hamburger_click=lambda: print("✅ Hamburger clicked!"),
        on_settings_click=lambda: print("✅ Settings clicked!"),
        on_profile_click=lambda: print("✅ Profile clicked!")
    )
    toolbar.pack(side=tk.TOP, fill=tk.X)
    
    # Main content area
    content_frame = ttk.Frame(root)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Title
    title_label = ttk.Label(
        content_frame,
        text="TopToolbar Component Demo",
        font=("Arial", 16, "bold")
    )
    title_label.pack(pady=(0, 10))
    
    # Status
    status_label = ttk.Label(
        content_frame,
        text="Status: Ready",
        font=("Arial", 12)
    )
    status_label.pack(pady=10)
    
    # Instructions
    instructions_frame = ttk.LabelFrame(content_frame, text="Features", padding=10)
    instructions_frame.pack(fill=tk.X, pady=10)
    
    instructions_text = """
    ✅ Hamburger Menu (☰) - Toggle sidebar visibility
    ✅ Logo + Title - Application branding
    ✅ Settings (⚙️) - Open settings dialog
    ✅ Profile (👤) - User profile management
    
    All actions emit events via EventBus and trigger callbacks.
    """
    
    instructions_label = ttk.Label(
        instructions_frame,
        text=instructions_text,
        justify=tk.LEFT
    )
    instructions_label.pack()
    
    # Event Log
    log_frame = ttk.LabelFrame(content_frame, text="Event Log (Last 10)", padding=10)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
    log_text.pack(fill=tk.BOTH, expand=True)
    log_text.insert('1.0', "Waiting for events...\n")
    
    # Test buttons
    test_frame = ttk.LabelFrame(content_frame, text="Test Functions", padding=10)
    test_frame.pack(fill=tk.X, pady=10)
    
    def change_title():
        toolbar.set_title("COVINA - New Title Test")
        status_label.config(text="Status: Title changed")
    
    ttk.Button(
        test_frame,
        text="Change Title",
        command=change_title
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        test_frame,
        text="Reset Title",
        command=lambda: toolbar.set_title("COVINA Document Management")
    ).pack(side=tk.LEFT, padx=5)
    
    # Run
    print("\n" + "="*60)
    print("TopToolbar Demo - Phase 2")
    print("="*60)
    print("✅ Window created")
    print("✅ EventBus started")
    print("✅ TopToolbar initialized")
    print("\nClick buttons in the toolbar to test functionality!")
    print("="*60 + "\n")
    
    root.mainloop()
    
    # Cleanup
    event_bus.stop()
    print("\n✅ EventBus stopped")
    print("✅ Demo complete\n")


if __name__ == "__main__":
    main()
