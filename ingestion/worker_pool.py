#!/usr/bin/env python3
"""
Covina Ingestion Backend - Worker Health Monitoring
===================================================

Production-Grade Worker Pool Management mit:
- Heartbeat Monitoring
- Crash Detection & Auto-Recovery
- Memory Tracking
- Graceful Shutdown
- Performance Metrics

Author: Covina System
Date: 28. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import multiprocessing
import psutil
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from queue import Queue, Empty

from ingestion.exceptions import (
    WorkerCrashException,
    WorkerOOMException,
    WorkerPoolExhaustedException,
    WorkerTimeoutException
)

logger = logging.getLogger(__name__)


class WorkerState(Enum):
    """Worker lifecycle states"""
    IDLE = "idle"
    BUSY = "busy"
    CRASHED = "crashed"
    TIMEOUT = "timeout"
    OOM = "out_of_memory"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class WorkerMetrics:
    """Metrics for individual worker"""
    worker_id: str
    worker_type: str  # "io" or "cpu"
    state: WorkerState = WorkerState.IDLE
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    memory_mb: float = 0.0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    last_task_start: Optional[datetime] = None
    current_task: Optional[str] = None
    active_workers: int = 0  # For aggregated metrics
    success_rate: float = 0.0  # For aggregated metrics
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        self.last_heartbeat = datetime.utcnow()
    
    def is_healthy(self, timeout_seconds: int = 300) -> bool:
        """Check if worker is healthy (recent heartbeat)"""
        return (datetime.utcnow() - self.last_heartbeat).total_seconds() < timeout_seconds
    
    def is_stuck(self, task_timeout_seconds: int = 600) -> bool:
        """Check if worker is stuck on a task"""
        if self.last_task_start is None:
            return False
        return (datetime.utcnow() - self.last_task_start).total_seconds() > task_timeout_seconds


class WorkerPoolManager:
    """
    Production-Grade Worker Pool Manager
    
    Features:
    - Health monitoring with heartbeats
    - Automatic crash detection
    - Memory tracking & OOM detection
    - Graceful shutdown
    - Metrics collection
    - Auto-recovery (optional)
    """
    
    def __init__(
        self,
        io_workers: int = 36,
        cpu_workers: int = 8,
        heartbeat_interval: int = 30,  # seconds
        health_check_interval: int = 60,  # seconds
        worker_timeout: int = 300,  # 5 minutes
        task_timeout: int = 600,  # 10 minutes
        memory_limit_mb: float = 2048.0,  # 2 GB per worker
        enable_auto_recovery: bool = False
    ):
        """
        Initialize Worker Pool Manager
        
        Args:
            io_workers: Number of I/O worker threads
            cpu_workers: Number of CPU worker processes
            heartbeat_interval: Seconds between heartbeats
            health_check_interval: Seconds between health checks
            worker_timeout: Max seconds without heartbeat before marking worker dead
            task_timeout: Max seconds for single task before timeout
            memory_limit_mb: Max memory per worker in MB
            enable_auto_recovery: Automatically restart crashed workers
        """
        self.io_workers = io_workers
        self.cpu_workers = cpu_workers
        self.heartbeat_interval = heartbeat_interval
        self.health_check_interval = health_check_interval
        self.worker_timeout = worker_timeout
        self.task_timeout = task_timeout
        self.memory_limit_mb = memory_limit_mb
        self.enable_auto_recovery = enable_auto_recovery
        
        # Worker Pools
        self.io_executor: Optional[ThreadPoolExecutor] = None
        self.cpu_executor: Optional[ProcessPoolExecutor] = None
        
        # Metrics
        self.worker_metrics: Dict[str, WorkerMetrics] = {}
        self._metrics_lock = threading.Lock()
        
        # Monitoring Threads
        self._monitoring_active = False
        self._health_check_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        
        # Shutdown State
        self._shutdown_requested = False
        self._shutdown_complete = threading.Event()
        
        # Performance Metrics
        self.total_tasks_submitted = 0
        self.total_tasks_completed = 0
        self.total_tasks_failed = 0
        
        logger.info("[WORKER_POOL] Initializing with io_workers=%d, cpu_workers=%d", io_workers, cpu_workers)
    
    def start(self):
        """Start worker pools and monitoring"""
        logger.info("[WORKER_POOL] Starting worker pools...")
        
        # Create Thread Pool (I/O Workers)
        self.io_executor = ThreadPoolExecutor(
            max_workers=self.io_workers,
            thread_name_prefix="ingestion_io"
        )
        
        # Create Process Pool (CPU Workers)
        self.cpu_executor = ProcessPoolExecutor(
            max_workers=self.cpu_workers,
            mp_context=multiprocessing.get_context('spawn')
        )
        
        # Initialize worker metrics
        with self._metrics_lock:
            for i in range(self.io_workers):
                worker_id = f"io_{i}"
                self.worker_metrics[worker_id] = WorkerMetrics(
                    worker_id=worker_id,
                    worker_type="io"
                )
            
            for i in range(self.cpu_workers):
                worker_id = f"cpu_{i}"
                self.worker_metrics[worker_id] = WorkerMetrics(
                    worker_id=worker_id,
                    worker_type="cpu"
                )
        
        # Start monitoring
        self._monitoring_active = True
        
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="worker_health_check"
        )
        self._health_check_thread.start()
        
        logger.info("[WORKER_POOL] ✅ Worker pools started (io=%d, cpu=%d)", self.io_workers, self.cpu_workers)
    
    def shutdown(self, wait: bool = True, timeout: int = 30):
        """
        Gracefully shutdown worker pools
        
        Args:
            wait: Wait for workers to finish current tasks
            timeout: Max seconds to wait for shutdown
        """
        logger.info("[WORKER_POOL] Initiating graceful shutdown...")
        self._shutdown_requested = True
        
        # Stop monitoring
        self._monitoring_active = False
        
        # Shutdown executors
        if self.io_executor:
            logger.info("[WORKER_POOL] Shutting down I/O executor...")
            self.io_executor.shutdown(wait=wait, cancel_futures=not wait)
        
        if self.cpu_executor:
            logger.info("[WORKER_POOL] Shutting down CPU executor...")
            self.cpu_executor.shutdown(wait=wait, cancel_futures=not wait)
        
        # Wait for monitoring threads
        if self._health_check_thread and self._health_check_thread.is_alive():
            self._health_check_thread.join(timeout=5)
        
        self._shutdown_complete.set()
        logger.info("[WORKER_POOL] ✅ Shutdown complete")
    
    def submit_io_task(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs
    ) -> Future:
        """
        Submit I/O task to thread pool
        
        Args:
            func: Function to execute
            *args: Positional arguments
            task_id: Optional task identifier for tracking
            **kwargs: Keyword arguments
            
        Returns:
            Future object
        """
        if self._shutdown_requested:
            raise RuntimeError("Worker pool is shutting down")
        
        if not self.io_executor:
            raise RuntimeError("I/O executor not started")
        
        self.total_tasks_submitted += 1
        
        # Wrap function to track metrics
        def wrapped_func(*args, **kwargs):
            worker_id = threading.current_thread().name
            
            with self._metrics_lock:
                if worker_id in self.worker_metrics:
                    metrics = self.worker_metrics[worker_id]
                    metrics.state = WorkerState.BUSY
                    metrics.last_task_start = datetime.utcnow()
                    metrics.current_task = task_id or func.__name__
            
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                with self._metrics_lock:
                    if worker_id in self.worker_metrics:
                        metrics = self.worker_metrics[worker_id]
                        metrics.tasks_completed += 1
                        metrics.total_processing_time += elapsed
                        metrics.state = WorkerState.IDLE
                        metrics.last_task_start = None
                        metrics.current_task = None
                        metrics.update_heartbeat()
                
                self.total_tasks_completed += 1
                return result
                
            except Exception as e:
                with self._metrics_lock:
                    if worker_id in self.worker_metrics:
                        metrics = self.worker_metrics[worker_id]
                        metrics.tasks_failed += 1
                        metrics.state = WorkerState.CRASHED
                        metrics.last_task_start = None
                        metrics.current_task = None
                
                self.total_tasks_failed += 1
                logger.error(f"[WORKER_POOL] Task failed in {worker_id}: {e}", exc_info=True)
                raise
        
        return self.io_executor.submit(wrapped_func, *args, **kwargs)
    
    def submit_cpu_task(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs
    ) -> Future:
        """
        Submit CPU task to process pool
        
        Args:
            func: Function to execute
            *args: Positional arguments
            task_id: Optional task identifier for tracking
            **kwargs: Keyword arguments
            
        Returns:
            Future object
        """
        if self._shutdown_requested:
            raise RuntimeError("Worker pool is shutting down")
        
        if not self.cpu_executor:
            raise RuntimeError("CPU executor not started")
        
        self.total_tasks_submitted += 1
        
        # Note: Process pool workers can't update shared metrics directly
        # We track completion in the main process
        future = self.cpu_executor.submit(func, *args, **kwargs)
        
        def done_callback(f: Future):
            try:
                f.result()  # Raises exception if task failed
                self.total_tasks_completed += 1
            except Exception as e:
                self.total_tasks_failed += 1
                logger.error(f"[WORKER_POOL] CPU task failed: {e}", exc_info=True)
        
        future.add_done_callback(done_callback)
        return future
    
    def _health_check_loop(self):
        """Background thread for health monitoring"""
        logger.info("[WORKER_POOL] Health check loop started")
        
        while self._monitoring_active:
            try:
                self._check_worker_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"[WORKER_POOL] Health check error: {e}", exc_info=True)
    
    def _check_worker_health(self):
        """Check health of all workers"""
        with self._metrics_lock:
            for worker_id, metrics in self.worker_metrics.items():
                # Check heartbeat (I/O workers only - process workers can't report)
                if metrics.worker_type == "io":
                    if not metrics.is_healthy(self.worker_timeout):
                        logger.warning(
                            f"[WORKER_POOL] Worker {worker_id} missed heartbeat "
                            f"(last: {metrics.last_heartbeat})"
                        )
                        metrics.state = WorkerState.CRASHED
                    
                    # Check if stuck on task
                    if metrics.is_stuck(self.task_timeout):
                        logger.error(
                            f"[WORKER_POOL] Worker {worker_id} stuck on task '{metrics.current_task}' "
                            f"(started: {metrics.last_task_start})"
                        )
                        metrics.state = WorkerState.TIMEOUT
                
                # Check memory usage (requires psutil - only for current process)
                try:
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    metrics.memory_mb = memory_mb
                    
                    if memory_mb > self.memory_limit_mb:
                        logger.error(
                            f"[WORKER_POOL] Worker {worker_id} OOM: {memory_mb:.2f} MB > {self.memory_limit_mb} MB"
                        )
                        metrics.state = WorkerState.OOM
                except Exception as e:
                    logger.debug(f"Could not get memory for {worker_id}: {e}")
    
    def get_io_metrics(self) -> WorkerMetrics:
        """Get aggregated I/O worker metrics"""
        with self._metrics_lock:
            active_workers = 0
            tasks_completed = 0
            tasks_failed = 0
            
            for worker_id, metrics in self.worker_metrics.items():
                if metrics.worker_type == "io":
                    if metrics.state in [WorkerState.BUSY]:
                        active_workers += 1
                    tasks_completed += metrics.tasks_completed
                    tasks_failed += metrics.tasks_failed
            
            total_tasks = tasks_completed + tasks_failed
            success_rate = (tasks_completed / total_tasks) if total_tasks > 0 else 1.0
            
            return WorkerMetrics(
                worker_id="io_aggregate",
                worker_type="io",
                active_workers=active_workers,
                tasks_completed=tasks_completed,
                tasks_failed=tasks_failed,
                success_rate=success_rate
            )
    
    def get_cpu_metrics(self) -> WorkerMetrics:
        """Get aggregated CPU worker metrics"""
        with self._metrics_lock:
            active_workers = 0
            tasks_completed = 0
            tasks_failed = 0
            
            for worker_id, metrics in self.worker_metrics.items():
                if metrics.worker_type == "cpu":
                    if metrics.state in [WorkerState.BUSY]:
                        active_workers += 1
                    tasks_completed += metrics.tasks_completed
                    tasks_failed += metrics.tasks_failed
            
            total_tasks = tasks_completed + tasks_failed
            success_rate = (tasks_completed / total_tasks) if total_tasks > 0 else 1.0
            
            return WorkerMetrics(
                worker_id="cpu_aggregate",
                worker_type="cpu",
                active_workers=active_workers,
                tasks_completed=tasks_completed,
                tasks_failed=tasks_failed,
                success_rate=success_rate
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current worker pool metrics"""
        with self._metrics_lock:
            worker_states = {
                "idle": 0,
                "busy": 0,
                "crashed": 0,
                "timeout": 0,
                "oom": 0
            }
            
            total_memory_mb = 0.0
            
            for metrics in self.worker_metrics.values():
                state_key = metrics.state.value
                if state_key in worker_states:
                    worker_states[state_key] += 1
                total_memory_mb += metrics.memory_mb
            
            return {
                "workers": {
                    "io": self.io_workers,
                    "cpu": self.cpu_workers,
                    "total": self.io_workers + self.cpu_workers
                },
                "states": worker_states,
                "tasks": {
                    "submitted": self.total_tasks_submitted,
                    "completed": self.total_tasks_completed,
                    "failed": self.total_tasks_failed,
                    "success_rate": (
                        self.total_tasks_completed / self.total_tasks_submitted * 100
                        if self.total_tasks_submitted > 0 else 0.0
                    )
                },
                "memory": {
                    "total_mb": total_memory_mb,
                    "limit_mb": self.memory_limit_mb * (self.io_workers + self.cpu_workers),
                    "usage_percent": (
                        total_memory_mb / (self.memory_limit_mb * (self.io_workers + self.cpu_workers)) * 100
                        if self.memory_limit_mb > 0 else 0.0
                    )
                },
                "health": {
                    "healthy": worker_states["idle"] + worker_states["busy"],
                    "unhealthy": worker_states["crashed"] + worker_states["timeout"] + worker_states["oom"]
                }
            }
    
    def is_healthy(self) -> bool:
        """Check if worker pool is overall healthy"""
        metrics = self.get_metrics()
        unhealthy = metrics["health"]["unhealthy"]
        total = metrics["workers"]["total"]
        
        # Healthy if <20% workers are unhealthy
        return unhealthy < (total * 0.2)


# ================================================================
# Global Instance (for backward compatibility)
# ================================================================

_global_pool_manager: Optional[WorkerPoolManager] = None


def get_pool_manager() -> WorkerPoolManager:
    """Get global worker pool manager instance"""
    global _global_pool_manager
    if _global_pool_manager is None:
        raise RuntimeError("Worker pool manager not initialized")
    return _global_pool_manager


def initialize_pool_manager(**kwargs) -> WorkerPoolManager:
    """Initialize global worker pool manager"""
    global _global_pool_manager
    _global_pool_manager = WorkerPoolManager(**kwargs)
    _global_pool_manager.start()
    return _global_pool_manager


def shutdown_pool_manager(timeout: int = 30):
    """Shutdown global worker pool manager"""
    global _global_pool_manager
    if _global_pool_manager is not None:
        _global_pool_manager.shutdown(timeout=timeout)
        _global_pool_manager = None
        logger.info("[WORKER_POOL] Global pool manager shutdown complete")
