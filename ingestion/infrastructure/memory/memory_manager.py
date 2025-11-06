"""
Memory Manager for Production

Provides:
- Memory usage monitoring
- Memory limit enforcement
- Automatic cleanup triggers
- Memory leak detection

Usage:
    from ingestion.infrastructure.memory.memory_manager import MemoryManager
    
    manager = MemoryManager(max_memory_mb=4096, warning_threshold=0.8)
    manager.start_monitoring()
    
    if manager.is_memory_available(required_mb=100):
        # Perform memory-intensive operation
        pass
"""
from __future__ import annotations

import psutil
import gc
import logging
import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory statistics snapshot."""
    timestamp: datetime
    total_mb: float
    available_mb: float
    used_mb: float
    percent: float
    process_mb: float


class MemoryManager:
    """Manages memory usage with limits and monitoring."""
    
    def __init__(
        self,
        max_memory_mb: Optional[int] = None,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95,
        check_interval: int = 30
    ):
        """Initialize memory manager.
        
        Args:
            max_memory_mb: Maximum memory limit in MB (None = use system total)
            warning_threshold: Warn when usage exceeds this fraction (0.0-1.0)
            critical_threshold: Critical when usage exceeds this fraction (0.0-1.0)
            check_interval: Seconds between memory checks
        """
        self.max_memory_mb = max_memory_mb or (psutil.virtual_memory().total / 1024 / 1024)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.check_interval = check_interval
        
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._cleanup_callbacks: list[Callable] = []
        self._stats_history: list[MemoryStats] = []
        self._max_history = 100
        
        logger.info(f"MemoryManager initialized: max={self.max_memory_mb:.0f}MB, warning={warning_threshold*100}%, critical={critical_threshold*100}%")
    
    def get_current_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        vm = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return MemoryStats(
            timestamp=datetime.now(),
            total_mb=vm.total / 1024 / 1024,
            available_mb=vm.available / 1024 / 1024,
            used_mb=vm.used / 1024 / 1024,
            percent=vm.percent,
            process_mb=process_memory
        )
    
    def is_memory_available(self, required_mb: float) -> bool:
        """Check if required memory is available.
        
        Args:
            required_mb: Required memory in MB
            
        Returns:
            True if memory is available
        """
        stats = self.get_current_stats()
        # Check system available memory
        system_available = stats.available_mb
        
        if system_available < required_mb:
            logger.warning(f"Insufficient system memory: need {required_mb:.0f}MB, available {system_available:.0f}MB")
            return False
        
        # Check against our process limit
        projected_usage = stats.process_mb + required_mb
        if projected_usage > self.max_memory_mb:
            logger.warning(f"Would exceed process limit: projected {projected_usage:.0f}MB > limit {self.max_memory_mb:.0f}MB")
            return False
        
        return True
    
    def force_cleanup(self):
        """Force garbage collection and memory cleanup."""
        logger.info("Forcing memory cleanup...")
        
        # Run garbage collection
        collected = gc.collect()
        logger.info(f"Garbage collected {collected} objects")
        
        # Run cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
    
    def register_cleanup_callback(self, callback: Callable):
        """Register callback to run during cleanup.
        
        Args:
            callback: Function to call during cleanup
        """
        self._cleanup_callbacks.append(callback)
        logger.info(f"Registered cleanup callback: {callback.__name__}")
    
    def _check_memory(self):
        """Check memory and trigger actions if needed."""
        stats = self.get_current_stats()
        
        # Store in history
        self._stats_history.append(stats)
        if len(self._stats_history) > self._max_history:
            self._stats_history.pop(0)
        
        # Calculate usage percentage against our limit
        usage_percent = (stats.process_mb / self.max_memory_mb) * 100
        
        # Check thresholds
        if usage_percent >= self.critical_threshold * 100:
            logger.critical(f"CRITICAL: Memory usage {usage_percent:.1f}% (process: {stats.process_mb:.0f}MB / {self.max_memory_mb:.0f}MB)")
            self.force_cleanup()
        elif usage_percent >= self.warning_threshold * 100:
            logger.warning(f"WARNING: Memory usage {usage_percent:.1f}% (process: {stats.process_mb:.0f}MB / {self.max_memory_mb:.0f}MB)")
        
        # Log stats
        logger.debug(f"Memory: process={stats.process_mb:.0f}MB, system={stats.percent:.1f}%, available={stats.available_mb:.0f}MB")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        logger.info("Memory monitoring started")
        
        while self._monitoring:
            try:
                self._check_memory()
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
            
            time.sleep(self.check_interval)
        
        logger.info("Memory monitoring stopped")
    
    def start_monitoring(self):
        """Start background memory monitoring."""
        if self._monitoring:
            logger.warning("Memory monitoring already running")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Memory monitoring thread started")
    
    def stop_monitoring(self):
        """Stop background memory monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Memory monitoring stopped")
    
    def get_stats_summary(self) -> dict:
        """Get summary of memory statistics.
        
        Returns:
            Dictionary with min/max/avg stats
        """
        if not self._stats_history:
            return {}
        
        process_mbs = [s.process_mb for s in self._stats_history]
        percents = [s.percent for s in self._stats_history]
        
        return {
            "samples": len(self._stats_history),
            "process_mb": {
                "min": min(process_mbs),
                "max": max(process_mbs),
                "avg": sum(process_mbs) / len(process_mbs),
                "current": process_mbs[-1],
            },
            "system_percent": {
                "min": min(percents),
                "max": max(percents),
                "avg": sum(percents) / len(percents),
                "current": percents[-1],
            },
            "limit_mb": self.max_memory_mb,
        }
    
    def detect_leak(self, growth_threshold_mb: float = 100, window_size: int = 10) -> bool:
        """Detect potential memory leak.
        
        Args:
            growth_threshold_mb: Threshold for leak detection (MB)
            window_size: Number of samples to analyze
            
        Returns:
            True if potential leak detected
        """
        if len(self._stats_history) < window_size:
            return False
        
        recent = self._stats_history[-window_size:]
        first = recent[0].process_mb
        last = recent[-1].process_mb
        growth = last - first
        
        if growth > growth_threshold_mb:
            logger.warning(f"Potential memory leak detected: {growth:.0f}MB growth over {window_size} samples")
            return True
        
        return False


# Global instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def configure_memory_manager(
    max_memory_mb: Optional[int] = None,
    warning_threshold: float = 0.8,
    critical_threshold: float = 0.95,
    check_interval: int = 30,
    start_monitoring: bool = True
) -> MemoryManager:
    """Configure and get global memory manager.
    
    Args:
        max_memory_mb: Maximum memory limit in MB
        warning_threshold: Warning threshold (0.0-1.0)
        critical_threshold: Critical threshold (0.0-1.0)
        check_interval: Seconds between checks
        start_monitoring: Start monitoring immediately
        
    Returns:
        Configured MemoryManager instance
    """
    global _memory_manager
    _memory_manager = MemoryManager(
        max_memory_mb=max_memory_mb,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        check_interval=check_interval
    )
    
    if start_monitoring:
        _memory_manager.start_monitoring()
    
    return _memory_manager
