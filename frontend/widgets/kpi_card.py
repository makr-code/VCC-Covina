"""
KPI Card Widget
===============

Lightweight KPI display card for dashboard metrics.

Features:
- Large value display (36pt font)
- Optional trend indicator (↑/↓ with percentage)
- Icon support (emoji or text)
- Last updated timestamp
- Status color coding (success/warning/error)
- Minimal memory footprint (pure Tkinter, no matplotlib)

Usage:
    card = KPICard(parent, title="Total Documents", value="6,523", 
                   trend="↑ +234", icon="📚")
    card.update_value("6,757", trend="↑ +234")
    card.set_status("success")  # Green color
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from datetime import datetime


class KPICard(ttk.Frame):
    """
    Simple KPI display card
    
    Args:
        parent: Parent widget
        title: Card title (e.g., "Total Documents")
        value: Initial value (e.g., "6,523")
        trend: Optional trend indicator (e.g., "↑ +234" or "↓ -12%")
        icon: Optional icon (emoji or text, e.g., "📚")
        style: Tkinter style name (default: 'Card.TFrame')
    """
    
    def __init__(
        self, 
        parent, 
        title: str, 
        value: str = "N/A",
        trend: Optional[str] = None, 
        icon: str = "📊",
        style: str = 'Card.TFrame'
    ):
        super().__init__(parent, style=style)
        
        self.title_text = title
        self.icon = icon
        self._last_update: Optional[datetime] = None
        
        # Configure padding
        self.configure(padding=10)
        
        self._create_widgets(value, trend)
    
    def _create_widgets(self, value: str, trend: Optional[str]):
        """Create internal widgets"""
        
        # Header with icon and title
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.header_label = ttk.Label(
            header_frame,
            text=f"{self.icon} {self.title_text}",
            style='Subtitle.TLabel'
        )
        self.header_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # Large value display
        self.value_label = ttk.Label(
            self,
            text=value,
            font=('Segoe UI', 36, 'bold')
        )
        self.value_label.pack(pady=(5, 5))
        
        # Trend indicator (optional)
        self.trend_label = ttk.Label(
            self,
            text=trend or "",
            style='Body.TLabel',
            font=('Segoe UI', 12)
        )
        if trend:
            self.trend_label.pack(pady=(0, 5))
        
        # Spacer to push timestamp to bottom
        spacer = ttk.Frame(self)
        spacer.pack(fill=tk.BOTH, expand=True)
        
        # Timestamp at bottom
        self.timestamp_label = ttk.Label(
            self,
            text="Last updated: Never",
            style='Caption.TLabel',
            font=('Segoe UI', 10)
        )
        self.timestamp_label.pack(side=tk.BOTTOM, pady=(5, 0))
    
    def update_value(self, value: str, trend: Optional[str] = None):
        """
        Update KPI value and timestamp
        
        Args:
            value: New value to display (e.g., "6,757")
            trend: Optional trend indicator (e.g., "↑ +234")
        """
        self.value_label.config(text=value)
        
        if trend is not None:
            self.trend_label.config(text=trend)
            if not self.trend_label.winfo_ismapped():
                # Show trend label if it was hidden
                self.trend_label.pack(pady=(0, 5), before=self.timestamp_label.master)
        
        # Update timestamp
        self._last_update = datetime.now()
        self.timestamp_label.config(text="Last updated: just now")
    
    def update_timestamp(self):
        """
        Update the 'last updated' text based on elapsed time
        
        Call this periodically (e.g., every second) to show elapsed time
        """
        if self._last_update is None:
            self.timestamp_label.config(text="Last updated: Never")
            return
        
        elapsed = (datetime.now() - self._last_update).total_seconds()
        
        if elapsed < 5:
            text = "Last updated: just now"
        elif elapsed < 60:
            text = f"Last updated: {int(elapsed)}s ago"
        elif elapsed < 3600:
            minutes = int(elapsed / 60)
            text = f"Last updated: {minutes}m ago"
        else:
            hours = int(elapsed / 3600)
            text = f"Last updated: {hours}h ago"
        
        self.timestamp_label.config(text=text)
    
    def set_status(self, status: str):
        """
        Set visual status indicator via color
        
        Args:
            status: "success" (green), "warning" (yellow), 
                   "error" (red), "unknown" (gray)
        """
        colors = {
            "success": "#28a745",   # Green
            "warning": "#ffc107",   # Yellow
            "error": "#dc3545",     # Red
            "unknown": "#6c757d"    # Gray
        }
        color = colors.get(status, colors["unknown"])
        self.value_label.config(foreground=color)
    
    def set_icon(self, icon: str):
        """
        Update the icon
        
        Args:
            icon: New icon (emoji or text)
        """
        self.icon = icon
        self.header_label.config(text=f"{self.icon} {self.title_text}")
    
    def set_title(self, title: str):
        """
        Update the title
        
        Args:
            title: New title text
        """
        self.title_text = title
        self.header_label.config(text=f"{self.icon} {self.title_text}")
    
    def reset(self):
        """Reset to initial state (N/A)"""
        self.value_label.config(text="N/A", foreground="")
        self.trend_label.config(text="")
        self._last_update = None
        self.timestamp_label.config(text="Last updated: Never")


# Convenience function for creating KPI cards with common styles
def create_kpi_grid(parent, kpi_definitions: list, columns: int = 4, rows: int = None, cols: int = None):
    """
    Create a grid of KPI cards
    
    Args:
        parent: Parent widget
        kpi_definitions: List of tuples (key, title, value) or dicts with keys: title, value, trend, icon
        columns: Number of columns in grid (default: 4) - DEPRECATED, use cols
        rows: Number of rows (optional, for explicit grid layout)
        cols: Number of columns (preferred parameter name)
    
    Returns:
        dict: Mapping of key (or title) -> KPICard instance
    
    Example:
        # New style (tuple format with key):
        kpis = create_kpi_grid(frame, [
            ("total_docs", "📚 Total Docs", "6,523"),
            ("vectors", "🔍 Vectors", "87,910")
        ], cols=2)
        
        # Old style (dict format):
        kpis = create_kpi_grid(frame, [
            {"title": "Total Docs", "value": "6,523", "trend": "↑ +234", "icon": "📚"},
            {"title": "Vectors", "value": "87,910", "trend": "↑ +1,245", "icon": "🔍"}
        ], columns=2)
        
        # Later update:
        kpis["total_docs"].update_value("6,757", "↑ +234")
    """
    # Handle parameter aliases (cols preferred over columns)
    num_columns = cols if cols is not None else columns
    
    kpi_frame = ttk.Frame(parent)
    kpi_frame.pack(fill=tk.X, pady=10, padx=20)
    
    # Configure grid columns
    for col in range(num_columns):
        kpi_frame.grid_columnconfigure(col, weight=1)
    
    # Create KPI cards
    cards = {}
    for idx, kpi_def in enumerate(kpi_definitions):
        row = idx // num_columns
        col = idx % num_columns
        
        # Support both tuple and dict formats
        if isinstance(kpi_def, tuple):
            # Tuple format: (key, title, value)
            key, title, value = kpi_def
            # Extract icon from title if present (e.g., "📚 Total Docs")
            if " " in title:
                parts = title.split(" ", 1)
                if len(parts[0]) == 1 or parts[0].startswith("🔍") or parts[0].startswith("📊"):
                    icon = parts[0]
                    title_text = parts[1]
                else:
                    icon = "📊"
                    title_text = title
            else:
                icon = "📊"
                title_text = title
            
            card = KPICard(
                kpi_frame,
                title=title_text,
                value=value,
                icon=icon
            )
        else:
            # Dict format (legacy)
            key = kpi_def.get("title", "Unknown")
            card = KPICard(
                kpi_frame,
                title=kpi_def.get("title", "Unknown"),
                value=kpi_def.get("value", "N/A"),
                trend=kpi_def.get("trend"),
                icon=kpi_def.get("icon", "📊")
            )
        
        card.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
        cards[key] = card
    
    return cards


if __name__ == "__main__":
    # Demo/Test
    root = tk.Tk()
    root.title("KPI Card Demo")
    root.geometry("800x400")
    
    # Configure styles
    style = ttk.Style()
    style.configure('Card.TFrame', background='#2b2b2b', relief='raised', borderwidth=2)
    style.configure('Subtitle.TLabel', background='#2b2b2b', foreground='white', 
                   font=('Segoe UI', 12, 'bold'))
    style.configure('Body.TLabel', background='#2b2b2b', foreground='white')
    style.configure('Caption.TLabel', background='#2b2b2b', foreground='#999999')
    
    # Create demo cards
    cards = create_kpi_grid(root, [
        {"title": "Total Documents", "value": "6,523", "trend": "↑ +234", "icon": "📚"},
        {"title": "Vector DB", "value": "87,910", "trend": "↑ +1,245", "icon": "🔍"},
        {"title": "Active Jobs", "value": "3", "icon": "⚙️"},
        {"title": "Uptime", "value": "4h 23m", "icon": "⏱️"}
    ], columns=4)
    
    # Demo: Update after 2 seconds
    def update_demo():
        cards["Total Documents"].update_value("6,757", "↑ +468")
        cards["Total Documents"].set_status("success")
        cards["Active Jobs"].update_value("5")
        cards["Active Jobs"].set_status("warning")
    
    root.after(2000, update_demo)
    
    root.mainloop()
