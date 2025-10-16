"""
Live Updater Thread
===================

Background Thread für periodische API-Calls mit Queue-basierter Kommunikation
"""

import threading
import queue
import time
import logging
from typing import Callable, Optional

from frontend.config import REFRESH_INTERVAL_CRITICAL, REFRESH_INTERVAL_NORMAL, REFRESH_INTERVAL_SLOW

logger = logging.getLogger(__name__)


class LiveUpdater:
    """Background thread für Live-Updates"""
    
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.update_queue = queue.Queue()
        
        # Registered update callbacks
        self.critical_callbacks = []   # 5s
        self.normal_callbacks = []     # 10s
        self.slow_callbacks = []       # 30s
        
        # Timers
        self.last_critical_update = 0
        self.last_normal_update = 0
        self.last_slow_update = 0
    
    def register_critical_callback(self, callback: Callable):
        """Register callback for critical updates (5s interval)"""
        self.critical_callbacks.append(callback)
    
    def register_normal_callback(self, callback: Callable):
        """Register callback for normal updates (10s interval)"""
        self.normal_callbacks.append(callback)
    
    def register_slow_callback(self, callback: Callable):
        """Register callback for slow updates (30s interval)"""
        self.slow_callbacks.append(callback)
    
    def start(self):
        """Start background thread"""
        if self.running:
            logger.warning("LiveUpdater already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info("LiveUpdater started")
    
    def stop(self):
        """Stop background thread gracefully"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("LiveUpdater stopped")
    
    def _update_loop(self):
        """Main update loop (runs in background thread)"""
        while self.running:
            try:
                current_time = time.time()
                
                # Critical updates (5s)
                if current_time - self.last_critical_update >= REFRESH_INTERVAL_CRITICAL:
                    self._execute_callbacks(self.critical_callbacks)
                    self.last_critical_update = current_time
                
                # Normal updates (10s)
                if current_time - self.last_normal_update >= REFRESH_INTERVAL_NORMAL:
                    self._execute_callbacks(self.normal_callbacks)
                    self.last_normal_update = current_time
                
                # Slow updates (30s)
                if current_time - self.last_slow_update >= REFRESH_INTERVAL_SLOW:
                    self._execute_callbacks(self.slow_callbacks)
                    self.last_slow_update = current_time
                
                # Sleep briefly to avoid tight loop
                time.sleep(1)
            
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(5)  # Back off on error
    
    def _execute_callbacks(self, callbacks):
        """Execute all callbacks in list"""
        for callback in callbacks:
            try:
                # Queue update for main thread
                self.update_queue.put(('callback', callback))
            except Exception as e:
                logger.error(f"Error executing callback {callback}: {e}")
    
    def process_updates(self, root):
        """
        Process queued updates in main thread (call from Tkinter after())
        
        Args:
            root: Tkinter root window
        """
        try:
            while True:
                # Non-blocking get
                update_type, callback = self.update_queue.get_nowait()
                
                if update_type == 'callback':
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")
        
        except queue.Empty:
            pass
        
        # Schedule next check (100ms)
        if self.running:
            root.after(100, lambda: self.process_updates(root))


# Global instance
live_updater = LiveUpdater()
