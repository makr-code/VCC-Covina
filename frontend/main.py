import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.config import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, COLORS, FONTS
)
from frontend.utils.theme import setup_theme
from frontend.utils.live_updater import live_updater

# Import all views
from frontend.views.home_dashboard_threaded import ThreadedHomeDashboardView  # Thread-based version
from frontend.views.system_status_view import SystemStatusView
from frontend.views.database_health_view import DatabaseHealthView
from frontend.views.ingestion_view import IngestionView
from frontend.views.security_view import SecurityView
from frontend.views.error_tracking_view import ErrorTrackingView
from frontend.views.golden_dataset_view import GoldenDatasetView

# Import widgets
from frontend.widgets.uds3_dataset_widget import UDS3DatasetWidget
from frontend.widgets.saga_monitor_widget import SAGAMonitorWidget

import os
import atexit


class CovinaLiveViewApp:
    """Hauptfenster für Covina LiveView Dashboard"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # ✅ Create PID file to identify this process
        self.pid_file = Path(__file__).parent.parent / "frontend.pid"
        self._create_pid_file()
        
        # Configure root window
        self.root.configure(bg=COLORS["background"])
        
        # Setup theme
        self.theme = setup_theme(root)
        
        # Initialize components
        self._create_menu()
        self._create_main_layout()
        self._create_status_bar()
        
        # Initialize live updater
        self._setup_live_updates()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _create_menu(self):
        """Create Menu Bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Refresh All", command=self.refresh_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="🏠 Home", command=lambda: self.notebook.select(0))
        view_menu.add_command(label="System Status", command=lambda: self.notebook.select(1))
        view_menu.add_command(label="UDS3 Datasets", command=lambda: self.notebook.select(2))
        view_menu.add_command(label="Ingestion", command=lambda: self.notebook.select(3))
        view_menu.add_command(label="Databases", command=lambda: self.notebook.select(4))
        view_menu.add_command(label="SAGA Monitor", command=lambda: self.notebook.select(5))
        view_menu.add_command(label="Security", command=lambda: self.notebook.select(6))
        view_menu.add_command(label="Errors", command=lambda: self.notebook.select(7))
        view_menu.add_command(label="Golden Dataset", command=lambda: self.notebook.select(8))
        
        # Settings Menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Configure Backend URL", command=self.configure_backend)
        settings_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        
        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def _create_main_layout(self):
        """Create main layout with tabs"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create all view instances
        self.views = {}
        
        # Home Dashboard (NEW: Thread-based First tab)
        self.views["Home"] = ThreadedHomeDashboardView(self.notebook)
        self.notebook.add(self.views["Home"], text="🏠 Home")
        
        # System Status
        self.views["System Status"] = SystemStatusView(self.notebook)
        self.notebook.add(self.views["System Status"], text="System Status")
        
        # UDS3 Datasets
        self.views["UDS3 Datasets"] = UDS3DatasetWidget(self.notebook)
        self.notebook.add(self.views["UDS3 Datasets"], text="UDS3 Datasets")
        
        # Ingestion
        self.views["Ingestion"] = IngestionView(self.notebook)
        self.notebook.add(self.views["Ingestion"], text="Ingestion")
        
        # Database Health
        self.views["Database Health"] = DatabaseHealthView(self.notebook)
        self.notebook.add(self.views["Database Health"], text="Database Health")
        
        # SAGA Monitor
        self.views["SAGA Monitor"] = SAGAMonitorWidget(self.notebook)
        self.notebook.add(self.views["SAGA Monitor"], text="SAGA Monitor")
        
        # Security
        self.views["Security"] = SecurityView(self.notebook)
        self.notebook.add(self.views["Security"], text="Security & Audit")
        
        # Error Tracking
        self.views["Errors"] = ErrorTrackingView(self.notebook)
        self.notebook.add(self.views["Errors"], text="Error Tracking")
        
        # Golden Dataset
        self.views["Golden Dataset"] = GoldenDatasetView(self.notebook)
        self.notebook.add(self.views["Golden Dataset"], text="Golden Dataset")
    
    def _create_status_bar(self):
        """Create status bar at bottom"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Connection status
        self.connection_status = tk.Label(status_frame,
                                         text="● Checking connection...",
                                         font=FONTS["small"],
                                         fg=COLORS["warning"],
                                         bg=COLORS["background"],
                                         anchor=tk.W)
        self.connection_status.pack(side=tk.LEFT, padx=10)
        
        # Last update timestamp
        self.last_update = tk.Label(status_frame,
                                   text="Last Update: Never",
                                   font=FONTS["small"],
                                   fg=COLORS["foreground"],
                                   bg=COLORS["background"],
                                   anchor=tk.E)
        self.last_update.pack(side=tk.RIGHT, padx=10)
    
    def _setup_live_updates(self):
        """Setup live updater with callbacks"""
        # Register critical callbacks (5s) - Mission-critical views
        live_updater.register_critical_callback(self._update_home_dashboard)
        live_updater.register_critical_callback(self._update_system_status)
        live_updater.register_critical_callback(self._update_ingestion)
        
        # Register normal callbacks (10s) - Important views
        live_updater.register_normal_callback(self._update_datasets)
        live_updater.register_normal_callback(self._update_databases)
        live_updater.register_normal_callback(self._update_saga_monitor)
        
        # Register slow callbacks (30s) - Less critical views
        live_updater.register_slow_callback(self._update_security)
        live_updater.register_slow_callback(self._update_errors)
        live_updater.register_slow_callback(self._update_golden_dataset)
        
        # Start live updater
        live_updater.start()
        
        # Start processing updates in main thread
        self.root.after(100, lambda: live_updater.process_updates(self.root))
        
        # Initial update (delayed to allow window to show first)
        self.root.after(3000, self.refresh_all)
    
    def _update_home_dashboard(self):
        """Update home dashboard view (only if visible)"""
        if "Home" in self.views and self.notebook.index("current") == 0:
            self.views["Home"].refresh()
    
    def _update_system_status(self):
        """Update system status view (only if visible)"""
        view_name = "System Status"
        if view_name in self.views:
            # Always update connection indicator (status bar)
            self._update_connection_indicator()
            # Only refresh view if visible
            try:
                current_tab = self.notebook.tab(self.notebook.select(), "text")
                if current_tab == view_name:
                    self.views[view_name].refresh()
            except:
                pass
    
    def _update_datasets(self):
        """Update datasets view (only if visible)"""
        view_name = "UDS3 Datasets"
        if view_name in self.views:
            try:
                current_tab = self.notebook.tab(self.notebook.select(), "text")
                if current_tab == view_name:
                    self.views[view_name].refresh()
            except:
                pass
    
    def _update_databases(self):
        """Update database health view (only if visible)"""
        view_name = "Database Health"
        if view_name in self.views:
            try:
                current_tab = self.notebook.tab(self.notebook.select(), "text")
                if current_tab == view_name:
                    self.views[view_name].refresh()
            except:
                pass
    
    def _update_ingestion(self):
        """Update ingestion view (only if visible)"""
        view_name = "Ingestion"
        if view_name in self.views:
            try:
                current_tab = self.notebook.tab(self.notebook.select(), "text")
                if current_tab == view_name:
                    self.views[view_name].refresh()
            except:
                pass
    
    def _update_saga_monitor(self):
        """Update SAGA monitor widget (only if visible)"""
        view_name = "SAGA Monitor"
        if view_name in self.views:
            try:
                current_tab = self.notebook.tab(self.notebook.select(), "text")
                if current_tab == view_name:
                    self.views[view_name].refresh()
            except:
                pass
    
    def _update_security(self):
        """Update security view (only if visible)"""
        view_name = "Security"
        if view_name in self.views:
            try:
                current_tab = self.notebook.tab(self.notebook.select(), "text")
                if current_tab == view_name:
                    self.views[view_name].refresh()
            except:
                pass
    
    def _update_errors(self):
        """Update error tracking view (only if visible)"""
        view_name = "Errors"
        if view_name in self.views:
            try:
                current_tab = self.notebook.tab(self.notebook.select(), "text")
                if current_tab == view_name:
                    self.views[view_name].refresh()
            except:
                pass
    
    def _update_golden_dataset(self):
        """Update golden dataset view (only if visible)"""
        view_name = "Golden Dataset"
        if view_name in self.views:
            try:
                current_tab = self.notebook.tab(self.notebook.select(), "text")
                if current_tab == view_name:
                    self.views[view_name].refresh()
            except:
                pass
    
    def _update_connection_indicator(self):
        """Update connection status indicator in status bar"""
        from frontend.services.api_client import api_client
        
        conn_status = api_client.get_connection_status()
        
        if conn_status.get("connected"):
            self.connection_status.config(
                text=f"● Connected ({conn_status.get('latency_ms', 0):.0f}ms)",
                fg=COLORS["success"]
            )
        else:
            self.connection_status.config(
                text=f"● Disconnected ({conn_status.get('error', 'unknown')})",
                fg=COLORS["error"]
            )
        
        # Update timestamp
        self.last_update.config(text=f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
    
    def refresh_all(self):
        """Refresh all views"""
        print("Refreshing all views...")
        
        for view_name, view in self.views.items():
            if hasattr(view, 'refresh'):
                try:
                    view.refresh()
                except Exception as e:
                    print(f"Error refreshing {view_name}: {e}")
        
        self._update_connection_indicator()
    
    def configure_backend(self):
        """Configure backend URL"""
        from frontend.config import BACKEND_URL
        messagebox.showinfo("Backend URL", 
                          f"Current Backend URL:\n{BACKEND_URL}\n\n"
                          "Edit frontend/config.py to change")
    
    def toggle_theme(self):
        """Toggle between dark and light theme"""
        self.theme.toggle_theme()
        messagebox.showinfo("Theme", f"Theme switched to: {self.theme.get_current_theme()}")
    
    def show_about(self):
        """Show about dialog"""
        from frontend import __version__, __author__
        messagebox.showinfo("About Covina LiveView",
                          f"Covina LiveView Dashboard\n"
                          f"Version {__version__}\n\n"
                          f"Real-time monitoring for Covina Backend\n\n"
                          f"By {__author__}")
    
    def _create_pid_file(self):
        """Create PID file to identify this process"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            # Register cleanup on exit
            atexit.register(self._cleanup_pid_file)
        except Exception as e:
            print(f"Warning: Could not create PID file: {e}")
    
    def _cleanup_pid_file(self):
        """Remove PID file on exit"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass
    
    def on_closing(self):
        """Handle window closing with graceful shutdown"""
        if messagebox.askokcancel("Quit", "Do you want to quit Covina LiveView?"):
            print("\n" + "="*60)
            print("🛑 Shutting down Covina LiveView...")
            print("="*60)
            
            try:
                # 1. Stop LiveUpdater first (no more refresh requests)
                print("1/4 Stopping LiveUpdater...")
                live_updater.stop()
                print("    ✅ LiveUpdater stopped")
            except Exception as e:
                print(f"    ⚠️ LiveUpdater stop error: {e}")
            
            try:
                # 2. Shutdown all view resources (chart pools, websockets)
                print("2/4 Shutting down views...")
                for view_name, view in self.views.items():
                    if hasattr(view, 'destroy'):
                        try:
                            print(f"    - Shutting down {view_name}...")
                            view.destroy()
                        except Exception as e:
                            print(f"    ⚠️ {view_name} shutdown error: {e}")
                print("    ✅ All views shut down")
            except Exception as e:
                print(f"    ⚠️ Views shutdown error: {e}")
            
            try:
                # 3. Cleanup PID file
                print("3/4 Cleaning up PID file...")
                self._cleanup_pid_file()
                print("    ✅ PID file cleaned")
            except Exception as e:
                print(f"    ⚠️ PID cleanup error: {e}")
            
            try:
                # 4. Destroy root window
                print("4/4 Destroying GUI...")
                self.root.destroy()
                print("    ✅ GUI destroyed")
            except Exception as e:
                print(f"    ⚠️ GUI destroy error: {e}")
            
            print("="*60)
            print("✅ Shutdown complete!")
            print("="*60 + "\n")
            
            # Exit cleanly
            sys.exit(0)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = CovinaLiveViewApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
