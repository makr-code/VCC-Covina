"""
File Discovery Service
======================

Automatische Überwachung von Verzeichnissen und Job-Erstellung für neue Dateien.

Basiert auf:
- ingestion/scanner.py (DirectoryScanner - bereits vorhanden!)
- ingestion/handlers/factory.py (HandlerFactory)
- ingestion/file_events.py (FileEvent, FileEventType)

Author: Covina System
Date: Oktober 2025 (Restored from corruption)
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime

# Imports from existing clean modules
from ingestion.scanner import DirectoryScanner, FileClassifier
from ingestion.file_events import FileEvent, FileEventType, FileSnapshot, FileCategory

logger = logging.getLogger(__name__)


class FileDiscoveryService:
    """
    Service für automatische Datei-Erkennung in überwachten Verzeichnissen.
    
    Workflow:
    1. Scan directories using DirectoryScanner
    2. Emit FileEvents (CREATED, MODIFIED, DELETED)
    3. Trigger callbacks for new files (optional)
    4. Integration with Job Manager via callback
    
    Example:
        >>> def on_files_discovered(events: List[FileEvent]):
        ...     print(f"{len(events)} neue Dateien gefunden!")
        >>> 
        >>> discovery = FileDiscoveryService(
        ...     watch_directories=[Path("data/incoming")],
        ...     on_discovery_callback=on_files_discovered
        ... )
        >>> discovery.start()
    """
    
    def __init__(
        self, 
        watch_directories: Optional[List[Path]] = None,
        on_discovery_callback: Optional[Callable[[List[FileEvent]], None]] = None,
        scan_interval_seconds: int = 60
    ):
        """
        Initialize File Discovery Service.
        
        Args:
            watch_directories: Verzeichnisse die überwacht werden sollen
            on_discovery_callback: Callback für neu entdeckte Dateien
            scan_interval_seconds: Scan-Intervall (Standard: 60s)
        """
        self.watch_directories = watch_directories or []
        self.on_discovery_callback = on_discovery_callback
        self.scan_interval = scan_interval_seconds
        
        # Scanner-Instanzen pro Verzeichnis
        self.scanners: Dict[Path, DirectoryScanner] = {}
        for directory in self.watch_directories:
            self.scanners[directory] = DirectoryScanner(
                root=directory,  # FIXED: root_path → root (16.10.2025, 12:05 Uhr)
                compute_hashes=False  # FIXED: recursive=True → compute_hashes (not needed for discovery)
            )
        
        # Service State
        self.is_running = False
        self._scan_task: Optional[asyncio.Task] = None
        self._discovered_files: List[FileEvent] = []
        
        # Statistics
        self.total_scans = 0
        self.total_files_discovered = 0
        self.last_scan_time: Optional[datetime] = None
        
        logger.info(
            f"FileDiscoveryService initialized: {len(self.watch_directories)} directories, "
            f"{scan_interval_seconds}s interval"
        )
    
    def start(self):
        """
        Start the discovery service (background scanning).
        
        Creates async task for periodic scanning.
        """
        if self.is_running:
            logger.warning("Discovery Service already running")
            return
        
        self.is_running = True
        
        # Start scan task if there is an event loop
        try:
            loop = asyncio.get_event_loop()
            self._scan_task = loop.create_task(self._scan_loop())
            logger.info("✅ Discovery Service started (async mode)")
        except RuntimeError:
            # No event loop - synchronous mode
            logger.info("✅ Discovery Service started (sync mode)")
    
    def stop(self):
        """Stop the discovery service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel scan task
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            logger.info("Scan task cancelled")
        
        logger.info("🛑 Discovery Service stopped")
    
    async def _scan_loop(self):
        """
        Async loop for periodic directory scanning.
        
        Runs every scan_interval seconds while is_running=True.
        """
        logger.info(f"Scan loop started (interval: {self.scan_interval}s)")
        
        while self.is_running:
            try:
                await self._perform_scan()
                await asyncio.sleep(self.scan_interval)
            except asyncio.CancelledError:
                logger.info("Scan loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scan loop: {e}", exc_info=True)
                await asyncio.sleep(self.scan_interval)
    
    async def _perform_scan(self):
        """
        Perform single scan of all watch directories.
        
        Emits FileEvents for new/modified/deleted files.
        """
        self.total_scans += 1
        self.last_scan_time = datetime.now()
        
        all_events: List[FileEvent] = []
        
        # Scan each directory
        for directory, scanner in self.scanners.items():
            try:
                # Use DirectoryScanner.scan_once() (bereits vorhanden!)
                events = scanner.scan_once()
                all_events.extend(events)
                
                logger.debug(
                    f"Scanned {directory}: {len(events)} events "
                    f"(CREATED: {sum(1 for e in events if e.event_type == FileEventType.CREATED)})"
                )
            except Exception as e:
                logger.error(f"Failed to scan {directory}: {e}")
        
        # Filter nur CREATED und MODIFIED Events (keine DELETED für Discovery)
        new_files = [
            e for e in all_events 
            if e.event_type in (FileEventType.CREATED, FileEventType.MODIFIED)
        ]
        
        if new_files:
            self.total_files_discovered += len(new_files)
            self._discovered_files.extend(new_files)
            
            logger.info(f"📁 Discovered {len(new_files)} new/modified files")
            
            # Trigger callback (async-aware - 16.10.2025, 12:00 Uhr)
            if self.on_discovery_callback:
                try:
                    import asyncio
                    import inspect
                    
                    # Check if callback is async (coroutine)
                    if inspect.iscoroutinefunction(self.on_discovery_callback):
                        # Async callback: schedule as task
                        asyncio.create_task(self.on_discovery_callback(new_files))
                    else:
                        # Sync callback: call directly
                        self.on_discovery_callback(new_files)
                except Exception as e:
                    logger.error(f"Discovery callback failed: {e}", exc_info=True)
    
    def scan_directory(self, directory: Path) -> List[FileEvent]:
        """
        Synchronous one-time directory scan.
        
        Args:
            directory: Verzeichnis zum Scannen
            
        Returns:
            List of FileEvents (CREATED events for all found files)
        """
        # Create temporary scanner
        scanner = DirectoryScanner(root=directory, compute_hashes=False)  # FIXED: root_path → root (16.10.2025, 12:05 Uhr)
        
        try:
            events = scanner.scan_once()
            logger.info(f"Scanned {directory}: {len(events)} files found")
            return events
        except Exception as e:
            logger.error(f"Failed to scan {directory}: {e}")
            return []
    
    def get_discovered_files(self) -> List[FileEvent]:
        """
        Get all discovered files since last retrieval.
        
        Returns:
            List of FileEvents, clears internal list
        """
        files = self._discovered_files.copy()
        self._discovered_files.clear()
        return files
    
    def trigger_scan(self):
        """
        Trigger immediate scan (bypasses interval).
        
        Useful for manual "Scan Now" buttons.
        """
        if not self.is_running:
            logger.warning("Discovery Service not running - start it first")
            return
        
        # Run scan asynchronously
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._perform_scan())
            logger.info("Manual scan triggered")
        except RuntimeError:
            # No event loop - run sync
            logger.warning("No event loop - cannot trigger async scan")
    
    @property
    def status(self) -> Dict:
        """
        Get service status information.
        
        Returns:
            Dict with service statistics
        """
        return {
            "running": self.is_running,
            "watch_directories": len(self.watch_directories),
            "total_scans": self.total_scans,
            "total_files_discovered": self.total_files_discovered,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "scan_interval_seconds": self.scan_interval,
            "pending_files": len(self._discovered_files)
        }


__all__ = ["FileDiscoveryService"]
