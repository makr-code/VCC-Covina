"""
Covina v4.0.1 - Clean Start (No Backend Required)
==================================================

Startet die UI ohne Backend-Verbindung für UI-Tests
"""

import tkinter as tk
from tkinter import ttk
import logging

# Disable WebSocket attempts
import os
os.environ['DISABLE_WEBSOCKET'] = '1'

# Setup minimal logging
logging.basicConfig(
    level=logging.WARNING,  # Only warnings and errors
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Import and run Covina
from covina_app_phase4 import CovinaApp

if __name__ == "__main__":
    print("=" * 60)
    print("Covina v4.0.1 - UI Test (No Backend)")
    print("=" * 60)
    print()
    print("✅ Starting application...")
    print()
    print("Expected:")
    print("  - All UI components visible")
    print("  - Left sidebar clickable")
    print("  - Views switch on click")
    print("  - Right sidebar with stats")
    print("  - AI Terminal at bottom")
    print("  - Status bar at very bottom")
    print()
    print("Try clicking navigation items!")
    print()
    
    app = CovinaApp()
    app.mainloop()
