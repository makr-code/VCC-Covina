#!/usr/bin/env python3
"""
Covina Ingestion Backend - Memory Management System
===================================================

Production-Grade Memory Management mit:
- Memory Limits & Monitoring
- Garbage Collection Tuning
- Memory Leak Detection
- Resource Pooling
- Emergency Memory Release

Author: Covina System
Date: 28. Oktober 2025
Version: 1.0.0
"""

import gc
import logging
import psutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ingestion.exceptions import MemoryLimitExceededException

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: datetime
    rss_mb: float  # Resident Set Size (current memory usage)
    vms_mb: float  # Virtual Memory Size
    percent: float  # % of total system memory
    available_mb: float  # Available system memory
    
    @property
    def current_mb(self) -> float:
        """Alias for rss_mb (for API compatibility)"""
        return self.rss_mb


class MemoryManager:
    """
    Production-Grade Memory Manager
    
    Features:
    - Soft/Hard memory limits
    - Automatic garbage collection
    - Memory leak detection
    - Emergency memory release
    - Metrics collection
    """
    
    def __init__(
        self,
        soft_limit_mb: float = 4096.0,  # 4 GB - warning threshold
        hard_limit_mb: float = 6144.0,  # 6 GB - hard stop
        check_interval: int = 30,  # seconds
        gc_threshold_mb: float = 3072.0,  # 3 GB - trigger GC
        enable_auto_gc: bool = True,
        leak_detection_window: int = 300,  # 5 minutes
        leak_threshold_mb: float = 512.0  # 512 MB growth = leak
    ):
        """
        Initialize Memory Manager
        
        Args:
            soft_limit_mb: Warning threshold in MB
            hard_limit_mb: Hard limit - reject new tasks
            check_interval: Seconds between memory checks
            gc_threshold_mb: Trigger GC at this threshold
            enable_auto_gc: Automatically trigger GC
            leak_detection_window: Window for leak detection in seconds
            leak_threshold_mb: Memory growth threshold for leak detection
        """
        self.soft_limit_mb = soft_limit_mb
        self.hard_limit_mb = hard_limit_mb
        self.check_interval = check_interval
        self.gc_threshold_mb = gc_threshold_mb
        self.enable_auto_gc = enable_auto_gc
        self.leak_detection_window = leak_detection_window
        self.leak_threshold_mb = leak_threshold_mb
        
        # State
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Metrics
        self.snapshots: list[MemorySnapshot] = []
        self.max_snapshots = 1000  # Keep last 1000 snapshots
        self.gc_count = 0
        self.warnings_count = 0
        self.rejections_count = 0
        
        # Current state
        self.current_mb = 0.0
        self.peak_mb = 0.0
        self.last_gc_time: Optional[datetime] = None
        
        logger.info(
            "[MEMORY] Initialized with soft_limit=%d MB, hard_limit=%d MB",
            soft_limit_mb, hard_limit_mb
        )
    
    def start(self):
        """Start memory monitoring"""
        logger.info("[MEMORY] Starting memory monitor...")
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="memory_monitor"
        )
        self._monitor_thread.start()
        
        logger.info("[MEMORY] ✅ Memory monitor started")
    
    def stop(self):
        """Stop memory monitoring"""
        logger.info("[MEMORY] Stopping memory monitor...")
        self._monitoring_active = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        logger.info("[MEMORY] ✅ Memory monitor stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._monitoring_active:
            try:
                self._check_memory()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"[MEMORY] Monitor error: {e}", exc_info=True)
    
    def _check_memory(self):
        """Check current memory usage"""
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            sys_mem = psutil.virtual_memory()
            
            rss_mb = mem_info.rss / 1024 / 1024
            vms_mb = mem_info.vms / 1024 / 1024
            percent = process.memory_percent()
            available_mb = sys_mem.available / 1024 / 1024
            
            # Update current state
            with self._lock:
                self.current_mb = rss_mb
                if rss_mb > self.peak_mb:
                    self.peak_mb = rss_mb
                
                # Store snapshot
                snapshot = MemorySnapshot(
                    timestamp=datetime.utcnow(),
                    rss_mb=rss_mb,
                    vms_mb=vms_mb,
                    percent=percent,
                    available_mb=available_mb
                )
                self.snapshots.append(snapshot)
                
                # Trim old snapshots
                if len(self.snapshots) > self.max_snapshots:
                    self.snapshots = self.snapshots[-self.max_snapshots:]
            
            # Check thresholds
            if rss_mb > self.hard_limit_mb:
                logger.error(
                    f"[MEMORY] ❌ HARD LIMIT EXCEEDED: {rss_mb:.2f} MB > {self.hard_limit_mb:.2f} MB"
                )
                self.rejections_count += 1
                # Emergency GC
                self._emergency_gc()
                
            elif rss_mb > self.soft_limit_mb:
                logger.warning(
                    f"[MEMORY] ⚠️  Soft limit exceeded: {rss_mb:.2f} MB > {self.soft_limit_mb:.2f} MB"
                )
                self.warnings_count += 1
                
                # Trigger GC if enabled
                if self.enable_auto_gc and rss_mb > self.gc_threshold_mb:
                    self._trigger_gc()
            
            # Check for memory leaks
            self._check_memory_leak()
            
        except Exception as e:
            logger.error(f"[MEMORY] Check failed: {e}", exc_info=True)
    
    def _trigger_gc(self):
        """Trigger garbage collection"""
        logger.info("[MEMORY] Triggering garbage collection...")
        
        before_mb = self.current_mb
        
        # Run GC
        collected = gc.collect(generation=2)  # Full collection
        
        # Check memory after GC
        try:
            process = psutil.Process()
            after_mb = process.memory_info().rss / 1024 / 1024
            freed_mb = before_mb - after_mb
            
            with self._lock:
                self.gc_count += 1
                self.last_gc_time = datetime.utcnow()
            
            logger.info(
                f"[MEMORY] GC completed: collected {collected} objects, "
                f"freed {freed_mb:.2f} MB ({before_mb:.2f} → {after_mb:.2f} MB)"
            )
        except Exception as e:
            logger.error(f"[MEMORY] GC check failed: {e}")
    
    def _emergency_gc(self):
        """Emergency garbage collection + aggressive cleanup"""
        logger.warning("[MEMORY] 🚨 EMERGENCY GC triggered!")
        
        # Multiple GC passes
        for i in range(3):
            collected = gc.collect(generation=2)
            logger.info(f"[MEMORY] Emergency GC pass {i+1}/3: collected {collected} objects")
        
        # Force release of unreferenced memory
        try:
            import ctypes
            ctypes.CDLL('libc.so.6').malloc_trim(0)  # Linux only
            logger.info("[MEMORY] malloc_trim() executed")
        except:
            pass  # Not available on Windows
    
    def _check_memory_leak(self):
        """Detect potential memory leaks"""
        with self._lock:
            if len(self.snapshots) < 10:
                return  # Not enough data
            
            # Get snapshots from leak detection window
            window_start = datetime.utcnow() - timedelta(seconds=self.leak_detection_window)
            recent_snapshots = [
                s for s in self.snapshots
                if s.timestamp >= window_start
            ]
            
            if len(recent_snapshots) < 5:
                return  # Not enough data in window
            
            # Check if memory is continuously growing
            first_mb = recent_snapshots[0].rss_mb
            last_mb = recent_snapshots[-1].rss_mb
            growth_mb = last_mb - first_mb
            
            if growth_mb > self.leak_threshold_mb:
                logger.warning(
                    f"[MEMORY] 🔴 Potential memory leak detected: "
                    f"{growth_mb:.2f} MB growth in {self.leak_detection_window}s "
                    f"({first_mb:.2f} → {last_mb:.2f} MB)"
                )
    
    def check_can_allocate(self, required_mb: float) -> bool:
        """
        Check if we can allocate more memory
        
        Args:
            required_mb: Required memory in MB
            
        Returns:
            True if allocation is safe
            
        Raises:
            MemoryLimitExceededException: If hard limit would be exceeded
        """
        projected_mb = self.current_mb + required_mb
        
        if projected_mb > self.hard_limit_mb:
            raise MemoryLimitExceededException(
                current_mb=self.current_mb,
                limit_mb=self.hard_limit_mb,
                component="ingestion_backend",
                context={
                    "required_mb": required_mb,
                    "projected_mb": projected_mb
                }
            )
        
        if projected_mb > self.soft_limit_mb:
            logger.warning(
                f"[MEMORY] Allocation warning: {projected_mb:.2f} MB > soft limit {self.soft_limit_mb:.2f} MB"
            )
        
        return True
    
    def get_current_snapshot(self) -> MemorySnapshot:
        """
        Get current memory snapshot
        
        Returns:
            Current memory snapshot with latest metrics
        """
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            mem_percent = process.memory_percent()
            vm = psutil.virtual_memory()
            
            rss_mb = mem_info.rss / 1024 / 1024
            vms_mb = mem_info.vms / 1024 / 1024
            available_mb = vm.available / 1024 / 1024
            
            # Update current state
            with self._lock:
                self.current_mb = rss_mb
            
            return MemorySnapshot(
                timestamp=datetime.utcnow(),
                rss_mb=rss_mb,
                vms_mb=vms_mb,
                percent=mem_percent,
                available_mb=available_mb
            )
        except Exception as e:
            logger.error(f"[MEMORY] Failed to get snapshot: {e}")
            # Return empty snapshot
            return MemorySnapshot(
                timestamp=datetime.utcnow(),
                rss_mb=0.0,
                vms_mb=0.0,
                percent=0.0,
                available_mb=0.0
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current memory metrics"""
        with self._lock:
            # Calculate memory growth rate
            growth_rate_mb_per_min = 0.0
            if len(self.snapshots) >= 2:
                recent = self.snapshots[-10:]  # Last 10 snapshots
                if len(recent) >= 2:
                    time_diff_min = (recent[-1].timestamp - recent[0].timestamp).total_seconds() / 60
                    if time_diff_min > 0:
                        mb_diff = recent[-1].rss_mb - recent[0].rss_mb
                        growth_rate_mb_per_min = mb_diff / time_diff_min
            
            return {
                "current_mb": self.current_mb,
                "peak_mb": self.peak_mb,
                "limits": {
                    "soft_mb": self.soft_limit_mb,
                    "hard_mb": self.hard_limit_mb,
                    "soft_usage_percent": (self.current_mb / self.soft_limit_mb * 100) if self.soft_limit_mb > 0 else 0,
                    "hard_usage_percent": (self.current_mb / self.hard_limit_mb * 100) if self.hard_limit_mb > 0 else 0
                },
                "gc": {
                    "count": self.gc_count,
                    "last_time": self.last_gc_time.isoformat() if self.last_gc_time else None
                },
                "warnings": self.warnings_count,
                "rejections": self.rejections_count,
                "growth_rate_mb_per_min": growth_rate_mb_per_min,
                "health": {
                    "status": self._get_health_status(),
                    "within_soft_limit": self.current_mb <= self.soft_limit_mb,
                    "within_hard_limit": self.current_mb <= self.hard_limit_mb
                }
            }
    
    def _get_health_status(self) -> str:
        """Get overall health status"""
        if self.current_mb > self.hard_limit_mb:
            return "critical"
        elif self.current_mb > self.soft_limit_mb:
            return "warning"
        else:
            return "healthy"


# ================================================================
# Global Instance
# ================================================================

_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global memory manager instance"""
    global _global_memory_manager
    if _global_memory_manager is None:
        raise RuntimeError("Memory manager not initialized")
    return _global_memory_manager


def initialize_memory_manager(**kwargs) -> MemoryManager:
    """Initialize global memory manager"""
    global _global_memory_manager
    _global_memory_manager = MemoryManager(**kwargs)
    _global_memory_manager.start()
    return _global_memory_manager


def shutdown_memory_manager():
    """Shutdown global memory manager"""
    global _global_memory_manager
    if _global_memory_manager is not None:
        _global_memory_manager.stop()
        _global_memory_manager = None
        logger.info("[MEMORY_MGR] Global memory manager shutdown complete")
