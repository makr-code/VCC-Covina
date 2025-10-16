"""
Task Executor - Thread-Pool Management
=======================================

Thread-Pool Executor mit Prioritäts-Queue und Cancellation-Support.

Version: 4.0.0 (Frontend Modernization)
Date: 14. Oktober 2025

Extracted from: covina_architecture.py (Lines 419-520)
"""

import logging
import queue
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Task Data Class
# ============================================================================

@dataclass
class Task:
    """Task-Datenklasse"""
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = 5  # 1-10, höher = wichtiger
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# TaskExecutor Implementation
# ============================================================================

class TaskExecutor:
    """
    Thread-Pool Executor mit Prioritäts-Queue und Cancellation-Support
    
    Features:
    - Priority Queue (1-10, höher = wichtiger)
    - Task Cancellation
    - Success/Error Callbacks
    - Thread-safe Task Management
    
    Example:
        >>> executor = TaskExecutor(max_workers=5)
        >>> executor.start()
        >>> 
        >>> def long_task(x, y):
        >>>     import time
        >>>     time.sleep(2)
        >>>     return x + y
        >>> 
        >>> def on_success(result):
        >>>     print(f"Result: {result}")
        >>> 
        >>> task = Task(
        >>>     task_id="add_task",
        >>>     func=long_task,
        >>>     args=(5, 3),
        >>>     priority=8,
        >>>     callback=on_success
        >>> )
        >>> executor.submit(task)
        >>> executor.stop()
    """
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="TaskExecutor"
        )
        self._active_tasks: Dict[str, Future] = {}
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._lock = threading.RLock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Startet Task-Scheduler"""
        if not self._running:
            self._running = True
            self._scheduler_thread = threading.Thread(
                target=self._schedule_loop,
                daemon=True,
                name="TaskExecutor-Scheduler"
            )
            self._scheduler_thread.start()
            logger.info(f"TaskExecutor gestartet ({self.max_workers} Workers)")
    
    def stop(self):
        """Stoppt TaskExecutor"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2.0)
        self._executor.shutdown(wait=True)
        logger.info("TaskExecutor gestoppt")
    
    def submit(self, task: Task) -> str:
        """
        Reicht Task zur Ausführung ein
        
        Args:
            task: Task-Objekt
        
        Returns:
            task_id
        """
        # Priority-Queue: Niedrigere Zahlen = höhere Priorität (invertieren!)
        priority = -task.priority
        self._task_queue.put((priority, task.created_at, task))
        logger.debug(f"Task {task.task_id} submitted (Priority: {task.priority})")
        return task.task_id
    
    def cancel(self, task_id: str) -> bool:
        """
        Versucht Task zu stornieren
        
        Returns:
            True wenn erfolgreich storniert
        """
        with self._lock:
            future = self._active_tasks.get(task_id)
            if future:
                cancelled = future.cancel()
                if cancelled:
                    del self._active_tasks[task_id]
                    logger.info(f"Task {task_id} storniert")
                return cancelled
        return False
    
    def _schedule_loop(self):
        """Task-Scheduling-Loop"""
        while self._running:
            try:
                # Performance-Optimierung: Kürzerer Timeout (100ms statt 500ms)
                # Reduziert Task-Submission-Latenz bei hoher Last
                _, _, task = self._task_queue.get(timeout=0.1)
                
                # Führe Task aus
                future = self._executor.submit(self._execute_task, task)
                
                with self._lock:
                    self._active_tasks[task.task_id] = future
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Fehler in Task-Scheduler: {e}")
    
    def _execute_task(self, task: Task):
        """Führt Task aus und ruft Callbacks auf"""
        try:
            logger.debug(f"Task {task.task_id} wird ausgeführt")
            result = task.func(*task.args, **task.kwargs)
            
            # Success-Callback
            if task.callback:
                task.callback(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Task {task.task_id} fehlgeschlagen: {e}")
            
            # Error-Callback
            if task.error_callback:
                task.error_callback(e)
            
            raise
        
        finally:
            # Task aus Active-Liste entfernen
            with self._lock:
                self._active_tasks.pop(task.task_id, None)
    
    def get_active_count(self) -> int:
        """Anzahl aktuell laufender Tasks"""
        with self._lock:
            return len(self._active_tasks)
    
    def get_pending_count(self) -> int:
        """Anzahl wartender Tasks"""
        return self._task_queue.qsize()
