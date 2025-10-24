"""
Polyglot Admin Tool - Launcher Script

Convenience launcher for Polyglot Admin Tool from tools/ directory.

Usage:
    python tools/polyglot_admin.py

Author: Covina System
Date: 24. Oktober 2025
"""

import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import and run main application
from polyglot_admin.main import main

if __name__ == "__main__":
    main()
