"""
Enhanced StatusBar Widget - Phase 2: UI Components

Bottom status bar showing:
- Backend health indicators (main + ingestion)
- Active jobs count
- System resources (CPU/RAM from ResourceMonitor)
- Last update timestamp
- Progress indicator (for uploads)

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 2)
Date: 14.10.2025, 10:05 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any
from datetime import datetime
from frontend.core.event_bus import EventType


class BackendHealthIndicator(ttk.Frame):
    """Backend connection health indicator."""
    
    def __init__(self, parent, label: str, **kwargs):
        super().__init__(parent, **kwargs)
        self._label_text = label
        self._connected = False
        self._build_ui()
    
    def _build_ui(self):
        """Build the indicator UI."""
        # Icon
        self._icon_label = ttk.Label(
            self,
            text="⚪",
            font=("Segoe UI", 10)
        )
        self._icon_label.pack(side="left", padx=2)
        
        # Label
        self._text_label = ttk.Label(
            self,
            text=f"{self._label_text}: Disconnected",
            font=("Segoe UI", 9)
        )
        self._text_label.pack(side="left")
    
    def set_connected(self, connected: bool):
        """Set connection status."""
        self._connected = connected
        
        if connected:
            self._icon_label.config(text="🟢")
            self._text_label.config(
                text=f"{self._label_text}: Connected",
                foreground="green"
            )
        else:
            self._icon_label.config(text="🔴")
            self._text_label.config(
                text=f"{self._label_text}: Disconnected",
                foreground="red"
            )
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected


class JobsIndicator(ttk.Frame):
    """Active jobs indicator."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._active_count = 0
        self._build_ui()
    
    def _build_ui(self):
        """Build the indicator UI."""
        # Icon
        icon_label = ttk.Label(
            self,
            text="📋",
            font=("Segoe UI", 10)
        )
        icon_label.pack(side="left", padx=2)
        
        # Count label
        self._count_label = ttk.Label(
            self,
            text="Jobs: 0",
            font=("Segoe UI", 9)
        )
        self._count_label.pack(side="left")
    
    def set_count(self, count: int):
        """Set active jobs count."""
        self._active_count = count
        
        color = "orange" if count > 0 else "black"
        self._count_label.config(
            text=f"Jobs: {count}",
            foreground=color
        )
    
    def get_count(self) -> int:
        """Get active jobs count."""
        return self._active_count


class ResourceIndicator(ttk.Frame):
    """System resources indicator (CPU/RAM)."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._cpu_usage = 0.0
        self._ram_usage = 0.0
        self._build_ui()
    
    def _build_ui(self):
        """Build the indicator UI."""
        # Icon
        icon_label = ttk.Label(
            self,
            text="💻",
            font=("Segoe UI", 10)
        )
        icon_label.pack(side="left", padx=2)
        
        # CPU label
        self._cpu_label = ttk.Label(
            self,
            text="CPU: 0%",
            font=("Segoe UI", 9)
        )
        self._cpu_label.pack(side="left", padx=5)
        
        # RAM label
        self._ram_label = ttk.Label(
            self,
            text="RAM: 0%",
            font=("Segoe UI", 9)
        )
        self._ram_label.pack(side="left")
    
    def set_cpu_usage(self, usage: float):
        """Set CPU usage percentage."""
        self._cpu_usage = usage
        
        # Color coding
        color = "red" if usage >= 80 else "orange" if usage >= 60 else "black"
        
        self._cpu_label.config(
            text=f"CPU: {usage:.1f}%",
            foreground=color
        )
    
    def set_ram_usage(self, usage: float):
        """Set RAM usage percentage."""
        self._ram_usage = usage
        
        # Color coding
        color = "red" if usage >= 80 else "orange" if usage >= 60 else "black"
        
        self._ram_label.config(
            text=f"RAM: {usage:.1f}%",
            foreground=color
        )
    
    def update(self, cpu: float, ram: float):
        """Update both CPU and RAM."""
        self.set_cpu_usage(cpu)
        self.set_ram_usage(ram)


class ProgressIndicator(ttk.Frame):
    """Upload/processing progress indicator."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._visible = False
        self._build_ui()
        self.pack_forget()  # Hidden by default
    
    def _build_ui(self):
        """Build the indicator UI."""
        # Progress bar
        self._progress = ttk.Progressbar(
            self,
            mode="determinate",
            length=200
        )
        self._progress.pack(side="left", padx=5)
        
        # Status label
        self._status_label = ttk.Label(
            self,
            text="",
            font=("Segoe UI", 9)
        )
        self._status_label.pack(side="left")
    
    def show(self, message: str = "Processing..."):
        """Show progress indicator."""
        if not self._visible:
            self.pack(side="left", padx=10)
            self._visible = True
        self._status_label.config(text=message)
    
    def hide(self):
        """Hide progress indicator."""
        if self._visible:
            self.pack_forget()
            self._visible = False
    
    def set_progress(self, value: float, message: Optional[str] = None):
        """
        Set progress value.
        
        Args:
            value: Progress value (0-100)
            message: Optional status message
        """
        self._progress["value"] = value
        if message:
            self._status_label.config(text=message)
    
    def set_indeterminate(self, enabled: bool = True):
        """Set indeterminate mode (spinning)."""
        if enabled:
            self._progress["mode"] = "indeterminate"
            self._progress.start(10)
        else:
            self._progress.stop()
            self._progress["mode"] = "determinate"
    
    def is_visible(self) -> bool:
        """Check if indicator is visible."""
        return self._visible


class EnhancedStatusBar(ttk.Frame):
    """
    Enhanced status bar for main window.
    
    Features:
    - Backend health indicators (main + ingestion)
    - Active jobs count display
    - System resources (CPU/RAM from ResourceMonitor)
    - Last update timestamp
    - Progress indicator (for uploads)
    - Height: 30px fixed
    
    Example:
        statusbar = EnhancedStatusBar(parent, event_bus)
        statusbar.pack(side="bottom", fill="x")
        
        # Update backend status
        statusbar.set_backend_connected("main", True)
        statusbar.set_backend_connected("ingestion", True)
        
        # Update jobs
        statusbar.set_active_jobs(5)
        
        # Update resources
        statusbar.update_resources(45.2, 67.8)
        
        # Show progress
        statusbar.show_progress("Uploading files...")
        statusbar.set_progress(50, "Uploading... 50/100 files")
    """
    
    def __init__(self, parent, event_bus, **kwargs):
        super().__init__(parent, **kwargs)
        self._event_bus = event_bus
        
        self.config(height=30, relief="sunken", borderwidth=1)
        self.pack_propagate(False)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the status bar UI."""
        # Container with padding
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=5, pady=2)
        
        # Left side: Backend indicators
        left_frame = ttk.Frame(container)
        left_frame.pack(side="left", fill="y")
        
        # Main backend indicator
        self._main_backend = BackendHealthIndicator(left_frame, "Main")
        self._main_backend.pack(side="left", padx=5)
        
        # Separator
        ttk.Separator(left_frame, orient="vertical").pack(side="left", fill="y", padx=5)
        
        # Ingestion backend indicator
        self._ingestion_backend = BackendHealthIndicator(left_frame, "Ingestion")
        self._ingestion_backend.pack(side="left", padx=5)
        
        # Separator
        ttk.Separator(left_frame, orient="vertical").pack(side="left", fill="y", padx=5)
        
        # Jobs indicator
        self._jobs = JobsIndicator(left_frame)
        self._jobs.pack(side="left", padx=5)
        
        # Separator
        ttk.Separator(left_frame, orient="vertical").pack(side="left", fill="y", padx=5)
        
        # Resources indicator
        self._resources = ResourceIndicator(left_frame)
        self._resources.pack(side="left", padx=5)
        
        # Center: Progress indicator (hidden by default)
        self._progress = ProgressIndicator(container)
        
        # Right side: Last update timestamp
        right_frame = ttk.Frame(container)
        right_frame.pack(side="right", fill="y")
        
        self._timestamp_label = ttk.Label(
            right_frame,
            text="",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self._timestamp_label.pack(side="right", padx=5)
        
        # Initialize timestamp
        self._update_timestamp()
    
    def _update_timestamp(self):
        """Update last update timestamp."""
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S")
        self._timestamp_label.config(text=f"Updated: {timestamp}")
    
    # Backend Health Methods
    
    def set_backend_connected(self, backend: str, connected: bool):
        """
        Set backend connection status.
        
        Args:
            backend: Backend name ("main" or "ingestion")
            connected: Connection status
        """
        if backend == "main":
            self._main_backend.set_connected(connected)
        elif backend == "ingestion":
            self._ingestion_backend.set_connected(connected)
        
        self._update_timestamp()
        
        # Emit event
        if self._event_bus:
            self._event_bus.emit_sync(
                "STATUS_BAR_BACKEND_UPDATE",
                {"backend": backend, "connected": connected}
            )
    
    def is_backend_connected(self, backend: str) -> bool:
        """Check if backend is connected."""
        if backend == "main":
            return self._main_backend.is_connected()
        elif backend == "ingestion":
            return self._ingestion_backend.is_connected()
        return False
    
    # Jobs Methods
    
    def set_active_jobs(self, count: int):
        """Set active jobs count."""
        self._jobs.set_count(count)
        self._update_timestamp()
        
        # Emit event
        if self._event_bus:
            self._event_bus.emit_sync(
                "STATUS_BAR_JOBS_UPDATE",
                {"count": count}
            )
    
    def get_active_jobs(self) -> int:
        """Get active jobs count."""
        return self._jobs.get_count()
    
    # Resources Methods
    
    def update_resources(self, cpu: float, ram: float):
        """
        Update system resources.
        
        Args:
            cpu: CPU usage percentage (0-100)
            ram: RAM usage percentage (0-100)
        """
        self._resources.update(cpu, ram)
        self._update_timestamp()
        
        # Emit event
        if self._event_bus:
            self._event_bus.emit_sync(
                "STATUS_BAR_RESOURCES_UPDATE",
                {"cpu": cpu, "ram": ram}
            )
    
    def set_cpu_usage(self, usage: float):
        """Set CPU usage."""
        self._resources.set_cpu_usage(usage)
        self._update_timestamp()
    
    def set_ram_usage(self, usage: float):
        """Set RAM usage."""
        self._resources.set_ram_usage(usage)
        self._update_timestamp()
    
    # Progress Methods
    
    def show_progress(self, message: str = "Processing..."):
        """Show progress indicator."""
        self._progress.show(message)
        self._update_timestamp()
    
    def hide_progress(self):
        """Hide progress indicator."""
        self._progress.hide()
        self._update_timestamp()
    
    def set_progress(self, value: float, message: Optional[str] = None):
        """
        Set progress value.
        
        Args:
            value: Progress value (0-100)
            message: Optional status message
        """
        if not self._progress.is_visible():
            self._progress.show()
        
        self._progress.set_progress(value, message)
        self._update_timestamp()
        
        # Emit event
        if self._event_bus:
            self._event_bus.emit_sync(
                "STATUS_BAR_PROGRESS_UPDATE",
                {"value": value, "message": message}
            )
    
    def set_indeterminate_progress(self, enabled: bool = True, message: str = "Processing..."):
        """Set indeterminate progress mode."""
        if enabled:
            self._progress.show(message)
            self._progress.set_indeterminate(True)
        else:
            self._progress.set_indeterminate(False)
            self._progress.hide()
        
        self._update_timestamp()
    
    def is_progress_visible(self) -> bool:
        """Check if progress is visible."""
        return self._progress.is_visible()
    
    # General Methods
    
    def update_all(self, data: Dict[str, Any]):
        """
        Update all status bar elements at once.
        
        Args:
            data: Dictionary with keys:
                - main_connected (bool)
                - ingestion_connected (bool)
                - active_jobs (int)
                - cpu_usage (float)
                - ram_usage (float)
        """
        if "main_connected" in data:
            self.set_backend_connected("main", data["main_connected"])
        
        if "ingestion_connected" in data:
            self.set_backend_connected("ingestion", data["ingestion_connected"])
        
        if "active_jobs" in data:
            self.set_active_jobs(data["active_jobs"])
        
        if "cpu_usage" in data and "ram_usage" in data:
            self.update_resources(data["cpu_usage"], data["ram_usage"])
        elif "cpu_usage" in data:
            self.set_cpu_usage(data["cpu_usage"])
        elif "ram_usage" in data:
            self.set_ram_usage(data["ram_usage"])


# Export
__all__ = [
    "EnhancedStatusBar",
    "BackendHealthIndicator",
    "JobsIndicator",
    "ResourceIndicator",
    "ProgressIndicator",
]
