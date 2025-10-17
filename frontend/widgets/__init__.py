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
- KPICard: Lightweight KPI display card (NEW - Phase 4)

Version: 4.0.1 (KPI Cards Integration)
Date: 17. Oktober 2025, 07:10 Uhr
"""

from .top_toolbar import TopToolbar
from .sidebar_left import SidebarLeft, NAV_ITEMS
from .sidebar_right import SidebarRight
from .ai_terminal import AITerminal
from .status_bar import EnhancedStatusBar
from .kpi_card import KPICard, create_kpi_grid

__all__ = [
    "TopToolbar",
    "SidebarLeft",
    "NAV_ITEMS",
    "SidebarRight",
    "AITerminal",
    "EnhancedStatusBar",
    "KPICard",
    "create_kpi_grid",
]
