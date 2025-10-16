"""
Frontend Widgets Module
========================

Reusable UI components for Covina Frontend.

Components (Phase 2 - COMPLETE):
- TopToolbar: Top header with hamburger menu, logo, settings, profile
- SidebarLeft: Collapsible navigation sidebar (10 items)
- SidebarRight: Quick stats, activity feed, quick actions
- AITerminal: AI-powered command interface with history
- EnhancedStatusBar: Backend health, jobs, resources display

Version: 4.0.0 (Frontend Modernization - Phase 2)
Date: 14. Oktober 2025, 10:10 Uhr
"""

from .top_toolbar import TopToolbar
from .sidebar_left import SidebarLeft, NAV_ITEMS
from .sidebar_right import SidebarRight
from .ai_terminal import AITerminal
from .status_bar import EnhancedStatusBar

__all__ = [
    "TopToolbar",
    "SidebarLeft",
    "NAV_ITEMS",
    "SidebarRight",
    "AITerminal",
    "EnhancedStatusBar",
]
