"""
Complete UI Components Demo - Phase 2

Tests all 5 UI components together:
- TopToolbar
- SidebarLeft
- SidebarRight
- AITerminal
- EnhancedStatusBar

Author: Covina Development Team
Version: 4.0.0
Date: 14.10.2025, 10:15 Uhr
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
from datetime import datetime
import random

# Ensure correct working directory
if not os.path.exists("frontend"):
    os.chdir(r"C:\VCC\Covina")

# Add project root to path
sys.path.insert(0, os.getcwd())

from frontend.core.event_bus import EventBus, EventType
from frontend.widgets import (
    TopToolbar,
    SidebarLeft,
    SidebarRight,
    AITerminal,
    EnhancedStatusBar,
    NAV_ITEMS
)


class CompleteUIDemo:
    """Complete UI Components Demo Application."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Covina UI Components Demo - Phase 2 Complete")
        self.root.geometry("1400x900")
        
        # Event bus
        self.event_bus = EventBus()
        self.event_bus.start()
        
        # Build UI
        self._build_ui()
        
        # Subscribe to events
        self._subscribe_events()
        
        # Start demo updates
        self._start_demo_updates()
        
        print("\n" + "="*60)
        print("Covina UI Components Demo - Phase 2 COMPLETE")
        print("="*60)
        print("✅ TopToolbar initialized")
        print("✅ SidebarLeft initialized (10 navigation items)")
        print("✅ SidebarRight initialized (stats + activity)")
        print("✅ AITerminal initialized")
        print("✅ EnhancedStatusBar initialized")
        print("="*60)
        print("\nTest the following features:")
        print("  1. TopToolbar: Click hamburger, settings, profile")
        print("  2. SidebarLeft: Navigate between items, toggle collapse")
        print("  3. SidebarRight: Watch stats update, toggle collapse")
        print("  4. AITerminal: Type 'help', 'status', 'history', 'clear'")
        print("  5. StatusBar: Watch backend health and resources")
        print("="*60 + "\n")
    
    def _build_ui(self):
        """Build complete UI layout."""
        # Top Toolbar
        self.toolbar = TopToolbar(
            self.root,
            self.event_bus,
            on_hamburger_click=self._on_hamburger_click,
            on_settings_click=self._on_settings_click,
            on_profile_click=self._on_profile_click
        )
        self.toolbar.pack(side="top", fill="x")
        
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(side="top", fill="both", expand=True)
        
        # Sidebar Left
        self.sidebar_left = SidebarLeft(
            main_container,
            self.event_bus,
            on_navigate=self._on_navigate
        )
        self.sidebar_left.pack(side="left", fill="y")
        
        # Content area (center)
        content_frame = ttk.Frame(main_container)
        content_frame.pack(side="left", fill="both", expand=True)
        
        # Content header
        header_label = ttk.Label(
            content_frame,
            text="Main Content Area",
            font=("Segoe UI", 16, "bold")
        )
        header_label.pack(pady=20)
        
        # Event log
        log_label = ttk.Label(
            content_frame,
            text="Event Log:",
            font=("Segoe UI", 12, "bold")
        )
        log_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        # Event log text
        log_frame = ttk.Frame(content_frame)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        self.event_log = tk.Text(
            log_frame,
            wrap="word",
            font=("Consolas", 9),
            height=20
        )
        log_scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.event_log.yview
        )
        self.event_log.configure(yscrollcommand=log_scrollbar.set)
        
        log_scrollbar.pack(side="right", fill="y")
        self.event_log.pack(side="left", fill="both", expand=True)
        
        # Sidebar Right
        self.sidebar_right = SidebarRight(
            main_container,
            self.event_bus,
            on_upload=self._on_upload,
            on_query=self._on_query,
            on_logs=self._on_logs
        )
        self.sidebar_right.pack(side="right", fill="y")
        
        # AI Terminal
        self.ai_terminal = AITerminal(
            self.root,
            self.event_bus,
            on_command=self._on_ai_command
        )
        self.ai_terminal.pack(side="bottom", fill="x")
        
        # Status Bar
        self.status_bar = EnhancedStatusBar(
            self.root,
            self.event_bus
        )
        self.status_bar.pack(side="bottom", fill="x")
    
    def _subscribe_events(self):
        """Subscribe to all events for logging."""
        # Subscribe to all event types for demo
        event_types = [
            EventType.SIDEBAR_LEFT_NAVIGATE,
            EventType.SIDEBAR_LEFT_TOGGLED,
            EventType.SIDEBAR_RIGHT_TOGGLED,
            EventType.QUICK_ACTION_UPLOAD,
            EventType.QUICK_ACTION_QUERY,
            EventType.QUICK_ACTION_LOGS,
            EventType.AI_COMMAND_SUBMITTED,
            EventType.AI_TERMINAL_TOGGLED,
            EventType.STATUS_BAR_BACKEND_UPDATE,
            EventType.STATUS_BAR_JOBS_UPDATE,
            EventType.STATUS_BAR_RESOURCES_UPDATE,
            EventType.TOOLBAR_HAMBURGER_CLICKED,
            EventType.TOOLBAR_SETTINGS_CLICKED,
            EventType.TOOLBAR_PROFILE_CLICKED,
        ]
        
        for event_type in event_types:
            self.event_bus.subscribe(event_type, self._log_event)
    
    def _log_event(self, data):
        """Log event to text widget."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        event_type = data.get("type", "UNKNOWN")
        
        log_line = f"[{timestamp}] {event_type}\n"
        
        self.event_log.insert(tk.END, log_line)
        self.event_log.see(tk.END)
    
    def _start_demo_updates(self):
        """Start automatic demo updates."""
        # Initial backend status
        self.status_bar.set_backend_connected("main", True)
        self.status_bar.set_backend_connected("ingestion", True)
        
        # Update stats
        self._update_demo_stats()
    
    def _update_demo_stats(self):
        """Update demo statistics."""
        # Random job count
        jobs = random.randint(0, 10)
        self.status_bar.set_active_jobs(jobs)
        self.sidebar_right.update_active_jobs(jobs)
        
        # Random resources
        cpu = random.uniform(20, 80)
        ram = random.uniform(30, 70)
        self.status_bar.update_resources(cpu, ram)
        
        # Random documents
        docs = random.randint(5000, 7000)
        self.sidebar_right.update_total_documents(docs)
        
        # Random success rate
        success = random.uniform(85, 99)
        self.sidebar_right.update_success_rate(success)
        
        # Add random activity
        activities = [
            "Job #123 completed successfully",
            "Document processed: contract_2025.pdf",
            "Backend health check: OK",
            "User query executed",
            "File uploaded: invoice.pdf",
            "Database backup completed",
            "System maintenance started",
            "AI model inference complete",
        ]
        if random.random() > 0.7:
            activity = random.choice(activities)
            self.sidebar_right.add_activity(activity)
        
        # Schedule next update
        self.root.after(3000, self._update_demo_stats)
    
    # Event Handlers
    
    def _on_hamburger_click(self):
        """Handle hamburger menu click."""
        self.sidebar_left.toggle_collapse()
    
    def _on_settings_click(self):
        """Handle settings button click."""
        self.ai_terminal.append_info("Settings dialog would open here")
    
    def _on_profile_click(self):
        """Handle profile button click."""
        self.ai_terminal.append_info("Profile dialog would open here")
    
    def _on_navigate(self, item_id: str):
        """Handle navigation."""
        # Find item label
        label = "Unknown"
        for nav_id, icon, nav_label in NAV_ITEMS:
            if nav_id == item_id:
                label = nav_label
                break
        
        # Update toolbar title
        self.toolbar.set_title(f"Covina - {label}")
        
        # Log to terminal
        self.ai_terminal.append_success(f"Navigated to: {label}")
    
    def _on_upload(self):
        """Handle upload action."""
        self.ai_terminal.append_info("Upload dialog would open here")
        
        # Simulate upload progress
        self.status_bar.show_progress("Uploading files...")
        self._simulate_progress(0)
    
    def _simulate_progress(self, value: int):
        """Simulate upload progress."""
        if value <= 100:
            self.status_bar.set_progress(value, f"Uploading... {value}%")
            self.root.after(50, lambda: self._simulate_progress(value + 2))
        else:
            self.status_bar.hide_progress()
            self.ai_terminal.append_success("Upload complete!")
    
    def _on_query(self):
        """Handle query action."""
        self.ai_terminal.append_info("Search dialog would open here")
    
    def _on_logs(self):
        """Handle logs action."""
        self.ai_terminal.append_info("Logs view would open here")
    
    def _on_ai_command(self, command: str):
        """Handle AI command."""
        # Simulate AI processing
        responses = {
            "analyze": "Analysis complete. Document is classified as: Contract",
            "search": "Found 42 matching documents",
            "summarize": "Summary: This document describes...",
        }
        
        cmd = command.split()[0].lower()
        if cmd in responses:
            return responses[cmd]
        else:
            return f"Unknown command: {command}"
    
    def run(self):
        """Run the application."""
        self.root.mainloop()


if __name__ == "__main__":
    app = CompleteUIDemo()
    app.run()
