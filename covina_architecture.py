#!/usr/bin/env python3
"""
Covina Frontend Architecture - Business Logic Layer
===================================================

Trennung von Business-Logic und UI mit Thread-Queue-Integration.

Architektur-Komponenten:
- CovinaBackendService: Zentrale Business-Logic
- EventBus: Observer-Pattern für UI-Updates
- TaskExecutor: Thread-Pool Management

Autor: Covina System
Datum: 2025-10-09
"""

import logging
import queue
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, Future

import requests

# Logging Setup (MUSS VOR allen anderen Imports stehen, die logger nutzen!)
logger = logging.getLogger("covina_architecture")
logger.setLevel(logging.INFO)

# Optional WebSocket Support
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("⚠️ websocket-client nicht installiert - WebSocket Support deaktiviert")


# ============================================================================
# Event System - Observer Pattern
# ============================================================================

class EventType(Enum):
    """Event-Typen für EventBus"""
    # Job Events
    JOB_CREATED = "job_created"
    JOB_STATUS_CHANGED = "job_status_changed"
    JOB_PROGRESS_UPDATE = "job_progress_update"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    
    # Upload Events
    UPLOAD_STARTED = "upload_started"
    UPLOAD_PROGRESS = "upload_progress"
    UPLOAD_FILE_COMPLETE = "upload_file_complete"
    UPLOAD_BATCH_COMPLETE = "upload_batch_complete"
    UPLOAD_FINISHED = "upload_finished"
    UPLOAD_ERROR = "upload_error"
    
    # Backend Events
    BACKEND_CONNECTED = "backend_connected"
    BACKEND_DISCONNECTED = "backend_disconnected"
    BACKEND_ERROR = "backend_error"
    
    # WebSocket Events
    WEBSOCKET_CONNECTED = "websocket_connected"
    WEBSOCKET_DISCONNECTED = "websocket_disconnected"
    WEBSOCKET_ERROR = "websocket_error"
    WEBSOCKET_MESSAGE = "websocket_message"
    
    # Resource Events
    RESOURCE_UPDATE = "resource_update"
    
    # Directory Analysis Events
    DIRECTORY_ANALYSIS_STARTED = "directory_analysis_started"
    DIRECTORY_ANALYSIS_COMPLETE = "directory_analysis_complete"
    DIRECTORY_ANALYSIS_ERROR = "directory_analysis_error"


# ============================================================================
# Performance Profiler - Lightweight Method Profiling (definiert VOR EventBus!)
# ============================================================================

class PerformanceProfiler:
    """
    Lightweight Performance-Profiler für Method-Tracking
    
    Features:
    - @profile Decorator für automatisches Method-Profiling
    - Thread-safe Metrics-Collection (< 1% Overhead)
    - Statistics-Berechnung (Mean, Median, P95, P99)
    - Top-N Slowest-Operations
    
    Verwendung:
        @PerformanceProfiler.profile
        def my_method(self):
            # ... code ...
        
        # Später:
        stats = PerformanceProfiler.get_stats("my_method")
        print(f"P95: {stats['p95']*1000:.2f}ms")
    """
    
    _metrics: Dict[str, List[float]] = {}
    _lock = threading.RLock()
    _enabled = True  # Global enable/disable
    
    @staticmethod
    def enable():
        """Aktiviert Profiling"""
        PerformanceProfiler._enabled = True
    
    @staticmethod
    def disable():
        """Deaktiviert Profiling (zero overhead)"""
        PerformanceProfiler._enabled = False
    
    @staticmethod
    def profile(func: Callable) -> Callable:
        """
        Decorator für Method-Profiling
        
        Args:
            func: Zu profilierende Funktion
        
        Returns:
            Wrapped function mit Profiling
        """
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not PerformanceProfiler._enabled:
                # Zero overhead wenn deaktiviert
                return func(*args, **kwargs)
            
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                PerformanceProfiler.record(func.__name__, duration)
        
        return wrapper
    
    @staticmethod
    def record(operation: str, duration: float):
        """
        Zeichnet Operation-Duration auf
        
        Args:
            operation: Name der Operation
            duration: Dauer in Sekunden
        """
        with PerformanceProfiler._lock:
            if operation not in PerformanceProfiler._metrics:
                PerformanceProfiler._metrics[operation] = []
            PerformanceProfiler._metrics[operation].append(duration)
    
    @staticmethod
    def get_stats(operation: str = None) -> Dict[str, Any]:
        """
        Gibt Statistiken zurück
        
        Args:
            operation: Name der Operation (None = alle)
        
        Returns:
            Dict mit Statistiken:
            - count: Anzahl Aufrufe
            - mean: Durchschnitt
            - median: Median
            - min: Minimum
            - max: Maximum
            - p50, p95, p99: Percentile
        """
        with PerformanceProfiler._lock:
            if operation:
                # Stats für spezifische Operation
                if operation not in PerformanceProfiler._metrics:
                    return {}
                
                durations = PerformanceProfiler._metrics[operation]
                if not durations:
                    return {}
                
                sorted_durations = sorted(durations)
                count = len(sorted_durations)
                
                return {
                    'operation': operation,
                    'count': count,
                    'mean': sum(sorted_durations) / count,
                    'median': sorted_durations[count // 2],
                    'min': sorted_durations[0],
                    'max': sorted_durations[-1],
                    'p50': sorted_durations[int(count * 0.50)],
                    'p95': sorted_durations[min(int(count * 0.95), count - 1)],
                    'p99': sorted_durations[min(int(count * 0.99), count - 1)],
                }
            else:
                # Stats für alle Operationen
                all_stats = {}
                for op in PerformanceProfiler._metrics:
                    all_stats[op] = PerformanceProfiler.get_stats(op)
                return all_stats
    
    @staticmethod
    def get_slowest_operations(limit: int = 10) -> List[tuple]:
        """
        Gibt Top-N langsamste Operationen zurück
        
        Args:
            limit: Max Anzahl Ergebnisse
        
        Returns:
            List of (operation, avg_duration) sortiert nach avg_duration
        """
        with PerformanceProfiler._lock:
            operation_avgs = []
            
            for operation, durations in PerformanceProfiler._metrics.items():
                if durations:
                    avg = sum(durations) / len(durations)
                    operation_avgs.append((operation, avg))
            
            # Sortiere nach avg_duration (absteigend)
            operation_avgs.sort(key=lambda x: x[1], reverse=True)
            
            return operation_avgs[:limit]
    
    @staticmethod
    def reset(operation: str = None):
        """
        Reset Metriken
        
        Args:
            operation: Spezifische Operation (None = alle)
        """
        with PerformanceProfiler._lock:
            if operation:
                if operation in PerformanceProfiler._metrics:
                    PerformanceProfiler._metrics[operation].clear()
            else:
                PerformanceProfiler._metrics.clear()
    
    @staticmethod
    def get_total_calls() -> int:
        """Gibt Gesamt-Anzahl aller Profiling-Calls zurück"""
        with PerformanceProfiler._lock:
            return sum(len(durations) for durations in PerformanceProfiler._metrics.values())
    
    @staticmethod
    def print_report(top_n: int = 10):
        """
        Druckt Performance-Report
        
        Args:
            top_n: Anzahl Top-Operationen
        """
        print("\n" + "=" * 80)
        print("PERFORMANCE PROFILING REPORT")
        print("=" * 80)
        
        total_calls = PerformanceProfiler.get_total_calls()
        print(f"Total Profiled Calls: {total_calls}")
        
        print(f"\nTop {top_n} Slowest Operations (by average duration):")
        print("-" * 80)
        print(f"{'Operation':<40} {'Avg (ms)':<12} {'P95 (ms)':<12} {'Calls':<10}")
        print("-" * 80)
        
        slowest = PerformanceProfiler.get_slowest_operations(limit=top_n)
        for operation, avg_duration in slowest:
            stats = PerformanceProfiler.get_stats(operation)
            print(f"{operation:<40} {avg_duration*1000:>10.2f}  {stats['p95']*1000:>10.2f}  {stats['count']:>8}")
        
        print("=" * 80 + "\n")


@dataclass
class Event:
    """Event-Datenklasse"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None


class EventBus:
    """
    Thread-safe Event-Bus für Observer-Pattern
    
    Ermöglicht lose Kopplung zwischen Business-Logic und UI.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, Set[Callable]] = defaultdict(set)
        self._event_queue: queue.Queue = queue.Queue()
        self._running = False
        self._dispatch_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
    
    def start(self):
        """Startet Event-Dispatcher-Thread"""
        if not self._running:
            self._running = True
            self._dispatch_thread = threading.Thread(
                target=self._dispatch_loop, 
                daemon=True,
                name="EventBus-Dispatcher"
            )
            self._dispatch_thread.start()
            logger.info("EventBus gestartet")
    
    def stop(self):
        """Stoppt Event-Dispatcher"""
        self._running = False
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=2.0)
        logger.info("EventBus gestoppt")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Abonniert Event-Typ
        
        Args:
            event_type: Typ des Events
            callback: Callback-Funktion (Event -> None)
        """
        with self._lock:
            self._subscribers[event_type].add(callback)
            logger.debug(f"Subscriber registriert für {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Entfernt Subscription"""
        with self._lock:
            self._subscribers[event_type].discard(callback)
    
    def emit(self, event_type: EventType, data: Dict[str, Any], source: Optional[str] = None):
        """
        Sendet Event (asynchron via Queue)
        
        Args:
            event_type: Event-Typ
            data: Event-Daten
            source: Quelle des Events (optional)
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source
        )
        self._event_queue.put(event)
    
    def emit_sync(self, event_type: EventType, data: Dict[str, Any], source: Optional[str] = None):
        """
        Sendet Event synchron (blockierend)
        
        Vorsicht: Kann zu Deadlocks führen wenn Callbacks blockieren!
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source
        )
        self._dispatch_event(event)
    
    def _dispatch_loop(self):
        """Event-Dispatch-Loop (läuft in eigenem Thread)"""
        while self._running:
            try:
                # Performance-Optimierung: Kürzerer Timeout für bessere Responsiveness
                # Trade-off: CPU-Last vs. Shutdown-Latenz (100ms ist guter Kompromiss)
                event = self._event_queue.get(timeout=0.1)
                self._dispatch_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Fehler in Event-Dispatch-Loop: {e}")
    
    @PerformanceProfiler.profile
    def _dispatch_event(self, event: Event):
        """Dispatched Event an alle Subscriber"""
        with self._lock:
            subscribers = self._subscribers.get(event.event_type, set()).copy()
        
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Fehler in Event-Callback für {event.event_type.value}: {e}")


# ============================================================================
# Task Executor - Thread-Pool Management
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


class TaskExecutor:
    """
    Thread-Pool Executor mit Prioritäts-Queue und Cancellation-Support
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
    
    @PerformanceProfiler.profile
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
            # Cleanup
            with self._lock:
                self._active_tasks.pop(task.task_id, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiken über TaskExecutor"""
        with self._lock:
            return {
                "max_workers": self.max_workers,
                "active_tasks": len(self._active_tasks),
                "queued_tasks": self._task_queue.qsize(),
                "running": self._running
            }


# ============================================================================
# Resilience Patterns - Circuit Breaker & Retry Logic
# ============================================================================

class CircuitState(Enum):
    """Circuit Breaker Zustände"""
    CLOSED = "closed"      # Normal - alle Requests durchlassen
    OPEN = "open"          # Fehler - Requests blockieren
    HALF_OPEN = "half_open"  # Test - einzelne Requests testen


@dataclass
class CircuitBreakerConfig:
    """Konfiguration für Circuit Breaker"""
    failure_threshold: int = 5  # Anzahl Fehler bis Circuit öffnet
    success_threshold: int = 2  # Anzahl Erfolge bis Circuit schließt (aus HALF_OPEN)
    timeout: float = 60.0  # Sekunden bis Circuit zu HALF_OPEN wechselt
    reset_timeout: float = 300.0  # Sekunden bis Fehler-Counter zurückgesetzt wird


class CircuitBreaker:
    """
    Circuit Breaker Pattern für Backend-Resilience
    
    Verhindert kaskadierende Fehler bei Backend-Ausfällen.
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()
        self._lock = threading.RLock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Führe Funktion mit Circuit Breaker Protection aus
        
        Args:
            func: Aufzurufende Funktion
            *args, **kwargs: Funktions-Argumente
            
        Returns:
            Funktions-Resultat
            
        Raises:
            Exception: Bei OPEN Circuit oder Funktions-Fehler
        """
        with self._lock:
            # Prüfe Circuit State
            self._update_state()
            
            if self.state == CircuitState.OPEN:
                raise Exception(
                    f"Circuit Breaker OPEN - Backend als down markiert "
                    f"(seit {(datetime.now() - self.last_state_change).seconds}s)"
                )
        
        # Führe Funktion aus
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise
    
    def _update_state(self):
        """Aktualisiere Circuit State basierend auf Zeit"""
        now = datetime.now()
        
        if self.state == CircuitState.OPEN:
            # Nach Timeout zu HALF_OPEN wechseln
            if self.last_failure_time:
                elapsed = (now - self.last_failure_time).total_seconds()
                if elapsed >= self.config.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self.last_state_change = now
                    logger.info("Circuit Breaker → HALF_OPEN (Test-Modus)")
    
    def _on_success(self):
        """Behandle erfolgreichen Request"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                
                if self.success_count >= self.config.success_threshold:
                    # Circuit schließen
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.last_state_change = datetime.now()
                    logger.info("Circuit Breaker → CLOSED (Backend erholt)")
            
            elif self.state == CircuitState.CLOSED:
                # Reset Fehler-Counter nach erfolgreichen Requests
                now = datetime.now()
                if self.last_failure_time:
                    elapsed = (now - self.last_failure_time).total_seconds()
                    if elapsed >= self.config.reset_timeout:
                        self.failure_count = 0
                        logger.debug("Circuit Breaker: Fehler-Counter zurückgesetzt")
    
    def _on_failure(self):
        """Behandle fehlgeschlagenen Request"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                # Bei Fehler in HALF_OPEN wieder zu OPEN
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.now()
                logger.warning("Circuit Breaker → OPEN (Test fehlgeschlagen)")
            
            elif self.state == CircuitState.CLOSED:
                # Bei Threshold zu OPEN wechseln
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.last_state_change = datetime.now()
                    logger.error(
                        f"Circuit Breaker → OPEN "
                        f"({self.failure_count} Fehler, Backend down)"
                    )
    
    def get_state(self) -> Dict[str, Any]:
        """Status-Informationen"""
        with self._lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
                "state_duration_seconds": (datetime.now() - self.last_state_change).total_seconds()
            }


@dataclass
class RetryConfig:
    """Konfiguration für Retry Logic"""
    max_retries: int = 3  # Maximale Anzahl Wiederholungen
    base_delay: float = 1.0  # Basis-Verzögerung in Sekunden
    max_delay: float = 30.0  # Maximale Verzögerung
    exponential_base: float = 2.0  # Basis für exponentielles Backoff
    jitter: bool = True  # Zufälliger Jitter zur Vermeidung von Thundering Herd


class RetryHelper:
    """
    Exponential Backoff Retry Logic
    
    Wiederholt fehlgeschlagene Requests mit zunehmender Verzögerung.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def execute(
        self,
        func: Callable,
        *args,
        retry_on: Optional[List[type]] = None,
        **kwargs
    ) -> Any:
        """
        Führe Funktion mit Retry Logic aus
        
        Args:
            func: Aufzurufende Funktion
            retry_on: Liste von Exception-Typen die Retry triggern (None = alle)
            *args, **kwargs: Funktions-Argumente
            
        Returns:
            Funktions-Resultat
            
        Raises:
            Exception: Nach allen Retries
        """
        retry_on = retry_on or [Exception]
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                # Prüfe ob Retry für diesen Exception-Typ
                should_retry = any(isinstance(e, exc_type) for exc_type in retry_on)
                
                if not should_retry or attempt >= self.config.max_retries:
                    raise
                
                # Berechne Backoff-Delay
                delay = self._calculate_delay(attempt)
                
                logger.warning(
                    f"Request fehlgeschlagen (Versuch {attempt + 1}/{self.config.max_retries + 1}): "
                    f"{type(e).__name__}: {e} - Retry in {delay:.2f}s"
                )
                
                time.sleep(delay)
        
        # Sollte nie erreicht werden
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Berechne Exponential Backoff Delay"""
        import random
        
        # Exponentielles Backoff
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        
        # Jitter hinzufügen (±25%)
        if self.config.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)  # Minimum 0.1s


# ============================================================================
# WebSocket Client - Optional Real-Time Updates
# ============================================================================

class WebSocketClient:
    """
    WebSocket-Client für Real-Time Backend-Updates
    
    Features:
    - Auto-Reconnect bei Verbindungsabbruch
    - Graceful Degradation (Fallback zu HTTP Polling)
    - Thread-safe Message Handling
    - Event-Bus Integration
    """
    
    def __init__(
        self,
        ws_url: str,
        event_bus: 'EventBus',
        auto_reconnect: bool = True,
        reconnect_interval: float = 5.0,
        ping_interval: float = 30.0
    ):
        self.ws_url = ws_url
        self.event_bus = event_bus
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.ping_interval = ping_interval
        
        # State
        self.connected = False
        self.enabled = WEBSOCKET_AVAILABLE
        self._ws: Optional['websocket.WebSocketApp'] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()
        
        if not self.enabled:
            logger.warning("WebSocket Support nicht verfügbar - Fallback zu HTTP Polling")
    
    def start(self):
        """Startet WebSocket-Verbindung (wenn verfügbar)"""
        if not self.enabled:
            logger.info("WebSocket deaktiviert - verwende HTTP Polling")
            return
        
        with self._lock:
            if self._running:
                logger.warning("WebSocket bereits gestartet")
                return
            
            self._running = True
            self._ws_thread = threading.Thread(
                target=self._connection_loop,
                daemon=True,
                name="WebSocketClient"
            )
            self._ws_thread.start()
            logger.info(f"WebSocket-Client gestartet: {self.ws_url}")
    
    def stop(self):
        """Stoppt WebSocket-Verbindung"""
        with self._lock:
            self._running = False
            if self._ws:
                self._ws.close()
            if self._ws_thread:
                self._ws_thread.join(timeout=2.0)
            logger.info("WebSocket-Client gestoppt")
    
    def _connection_loop(self):
        """Haupt-Loop mit Auto-Reconnect"""
        while self._running:
            try:
                self._connect()
            except Exception as e:
                logger.error(f"WebSocket-Fehler: {e}")
                self.event_bus.emit(
                    EventType.WEBSOCKET_ERROR,
                    {"error": str(e)},
                    source="WebSocketClient"
                )
            
            # Auto-Reconnect
            if self._running and self.auto_reconnect:
                logger.info(f"WebSocket-Reconnect in {self.reconnect_interval}s...")
                time.sleep(self.reconnect_interval)
    
    def _connect(self):
        """Erstellt WebSocket-Verbindung"""
        if not WEBSOCKET_AVAILABLE:
            return
        
        import websocket
        
        self._ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        # Run WebSocket (blocking)
        self._ws.run_forever(
            ping_interval=self.ping_interval,
            ping_timeout=10
        )
    
    def _on_open(self, ws):
        """WebSocket-Verbindung hergestellt"""
        with self._lock:
            self.connected = True
        
        logger.info(f"✅ WebSocket verbunden: {self.ws_url}")
        self.event_bus.emit(
            EventType.WEBSOCKET_CONNECTED,
            {"url": self.ws_url},
            source="WebSocketClient"
        )
    
    def _on_message(self, ws, message: str):
        """WebSocket-Nachricht empfangen"""
        try:
            import json
            data = json.loads(message)
            
            # Emit generic WebSocket message event
            self.event_bus.emit(
                EventType.WEBSOCKET_MESSAGE,
                {"message": data},
                source="WebSocketClient"
            )
            
            # Route to specific event types based on message type
            msg_type = data.get('type', '')
            
            if msg_type == 'job_update':
                self._handle_job_update(data)
            elif msg_type == 'upload_progress':
                self._handle_upload_progress(data)
            elif msg_type == 'backend_status':
                self._handle_backend_status(data)
            else:
                logger.debug(f"Unbekannter WebSocket-Nachrichtentyp: {msg_type}")
        
        except Exception as e:
            logger.error(f"WebSocket-Message-Fehler: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket-Fehler"""
        logger.error(f"❌ WebSocket-Error: {error}")
        self.event_bus.emit(
            EventType.WEBSOCKET_ERROR,
            {"error": str(error)},
            source="WebSocketClient"
        )
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket-Verbindung geschlossen"""
        with self._lock:
            self.connected = False
        
        logger.warning(f"WebSocket getrennt: {close_status_code} - {close_msg}")
        self.event_bus.emit(
            EventType.WEBSOCKET_DISCONNECTED,
            {"code": close_status_code, "message": close_msg},
            source="WebSocketClient"
        )
    
    def _handle_job_update(self, data: Dict):
        """Verarbeitet Job-Update-Nachricht"""
        jobs = data.get('jobs', [])
        if jobs:
            self.event_bus.emit(
                EventType.JOB_STATUS_CHANGED,
                {"jobs": jobs, "source": "websocket"},
                source="WebSocketClient"
            )
    
    def _handle_upload_progress(self, data: Dict):
        """Verarbeitet Upload-Progress-Nachricht"""
        self.event_bus.emit(
            EventType.UPLOAD_PROGRESS,
            data.get('progress', {}),
            source="WebSocketClient"
        )
    
    def _handle_backend_status(self, data: Dict):
        """Verarbeitet Backend-Status-Nachricht"""
        status = data.get('status', 'unknown')
        if status == 'online':
            self.event_bus.emit(
                EventType.BACKEND_CONNECTED,
                data,
                source="WebSocketClient"
            )
        elif status == 'offline':
            self.event_bus.emit(
                EventType.BACKEND_DISCONNECTED,
                data,
                source="WebSocketClient"
            )
    
    def send(self, message: Dict):
        """Sendet Nachricht an WebSocket-Server"""
        if not self.connected or not self._ws:
            logger.warning("WebSocket nicht verbunden - Nachricht wird verworfen")
            return False
        
        try:
            import json
            self._ws.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"WebSocket-Send-Fehler: {e}")
            return False
    
    def is_available(self) -> bool:
        """Prüft ob WebSocket verfügbar und verbunden ist"""
        return self.enabled and self.connected


# ============================================================================
# Covina Backend Service - Business Logic
# ============================================================================

class CovinaBackendService:
    """
    Zentrale Business-Logic-Schicht für Covina Frontend
    
    Trennt Business-Logic von UI-Code. Kommuniziert via EventBus.
    """
    
    def __init__(
        self, 
        base_url: str = "http://127.0.0.1:45678",
        ingestion_base_url: str = "http://127.0.0.1:45679",  # ✅ NEW: Ingestion Backend URL
        event_bus: Optional[EventBus] = None,
        task_executor: Optional[TaskExecutor] = None,
        enable_websocket: bool = True,
        ws_url: Optional[str] = None
    ):
        self.base_url = base_url
        self.ingestion_base_url = ingestion_base_url  # ✅ NEW: Separate Ingestion Backend
        self.event_bus = event_bus or EventBus()
        self.task_executor = task_executor or TaskExecutor(max_workers=5)
        
        # HTTP Session
        self.session = requests.Session()
        self.session.timeout = 30
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Resilience Patterns
        self.circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout=60.0,
                reset_timeout=300.0
            )
        )
        self.retry_helper = RetryHelper(
            RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True
            )
        )
        
        # WebSocket Client (Optional)
        self.websocket_client: Optional[WebSocketClient] = None
        self.enable_websocket = enable_websocket and WEBSOCKET_AVAILABLE
        
        if self.enable_websocket:
            # Auto-generate WebSocket URL if not provided
            if not ws_url:
                ws_url = self.base_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/jobs'
            
            self.websocket_client = WebSocketClient(
                ws_url=ws_url,
                event_bus=self.event_bus,
                auto_reconnect=True,
                reconnect_interval=5.0
            )
            logger.info(f"WebSocket-Client konfiguriert: {ws_url}")
        else:
            logger.info("WebSocket deaktiviert - verwende HTTP Polling")
        
        self.retry_helper = RetryHelper(
            RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True
            )
        )
        
        # State
        self.backend_online = False
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_check_running = False
        
        # Job Cache
        self._job_cache: Dict[str, Dict] = {}
        self._job_cache_lock = threading.RLock()
        
        # Job Refresh Loop
        self._job_refresh_running = False
        self._job_refresh_thread = None
        self._job_refresh_interval = 10  # Sekunden (optimiert)
        self._last_job_update: Optional[datetime] = None  # Smart Polling
    
    def start(self):
        """Startet Service (inkl. WebSocket wenn aktiviert)"""
        self.event_bus.start()
        self.task_executor.start()
        
        # WebSocket starten (wenn aktiviert)
        if self.websocket_client:
            self.websocket_client.start()
            logger.info("✅ WebSocket-Verbindung gestartet")
        
        self._start_health_check()
        self._start_job_refresh()
        logger.info("CovinaBackendService gestartet")
    
    def stop(self):
        """Stoppt Service (inkl. WebSocket)"""
        # WebSocket stoppen (wenn vorhanden)
        if self.websocket_client:
            self.websocket_client.stop()
            logger.info("✅ WebSocket-Verbindung geschlossen")
        
        self._stop_health_check()
        self._stop_job_refresh()
        self.task_executor.stop()
        self.event_bus.stop()
        self.session.close()
        logger.info("CovinaBackendService gestoppt")
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    def _make_request(
        self,
        method: str,
        url: str,
        use_circuit_breaker: bool = True,
        use_retry: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        Resiliente HTTP-Request-Wrapper
        
        Args:
            method: HTTP-Methode (GET, POST, etc.)
            url: URL
            use_circuit_breaker: Circuit Breaker aktivieren
            use_retry: Retry Logic aktivieren
            **kwargs: Zusätzliche Request-Parameter
            
        Returns:
            Response-Objekt
            
        Raises:
            Exception: Bei Fehler nach allen Retries
        """
        def _request():
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        
        # Mit Retry + Circuit Breaker
        if use_retry and use_circuit_breaker:
            return self.retry_helper.execute(
                lambda: self.circuit_breaker.call(_request),
                retry_on=[
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.HTTPError
                ]
            )
        
        # Nur Circuit Breaker
        elif use_circuit_breaker:
            return self.circuit_breaker.call(_request)
        
        # Nur Retry
        elif use_retry:
            return self.retry_helper.execute(
                _request,
                retry_on=[
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.HTTPError
                ]
            )
        
        # Ohne Resilience
        else:
            return _request()
    
    def _start_health_check(self):
        """Startet periodischen Health-Check"""
        self._health_check_running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="BackendHealthCheck"
        )
        self._health_check_thread.start()
    
    def _stop_health_check(self):
        """Stoppt Health-Check"""
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2.0)
    
    def _health_check_loop(self):
        """Health-Check-Loop (alle 10s) - ohne Circuit Breaker"""
        while self._health_check_running:
            try:
                # Health Check ohne Circuit Breaker (um Circuit zu testen)
                response = self._make_request(
                    "GET",
                    f"{self.base_url}/health",
                    use_circuit_breaker=False,
                    use_retry=False,
                    timeout=5
                )
                
                if not self.backend_online:
                    self.backend_online = True
                    self.event_bus.emit(
                        EventType.BACKEND_CONNECTED,
                        {"url": self.base_url, "circuit_state": self.circuit_breaker.get_state()},
                        source="HealthCheck"
                    )
                    logger.info("Backend verbunden")
                
            except Exception as e:
                if self.backend_online:
                    self.backend_online = False
                    self.event_bus.emit(
                        EventType.BACKEND_DISCONNECTED,
                        {"error": str(e), "circuit_state": self.circuit_breaker.get_state()},
                        source="HealthCheck"
                    )
                    logger.warning(f"Backend nicht erreichbar: {e}")
            
            time.sleep(10)
    
    # ========================================================================
    # Job Refresh Loop
    # ========================================================================
    
    def _start_job_refresh(self):
        """Startet periodischen Job-Refresh"""
        self._job_refresh_running = True
        self._job_refresh_thread = threading.Thread(
            target=self._job_refresh_loop,
            daemon=True,
            name="JobRefreshLoop"
        )
        self._job_refresh_thread.start()
    
    def _stop_job_refresh(self):
        """Stoppt Job-Refresh"""
        self._job_refresh_running = False
        if self._job_refresh_thread:
            self._job_refresh_thread.join(timeout=2.0)
    
    def _job_refresh_loop(self):
        """
        Job-Refresh-Loop (alle 10s, nur bei Änderungen)
        
        Features:
        - Skip HTTP Polling wenn WebSocket aktiv ist
        - Smart Polling mit Cache-basierter Änderungserkennung
        - Nur refreshen wenn Backend online
        """
        while self._job_refresh_running:
            try:
                # Skip HTTP Polling wenn WebSocket verbunden ist
                if self.websocket_client and self.websocket_client.is_available():
                    logger.debug("WebSocket aktiv - überspringe HTTP Job Polling")
                else:
                    # Fallback auf HTTP Polling
                    if self.backend_online:
                        self.list_jobs(limit=100)
            except Exception as e:
                logger.debug(f"Job-Refresh-Fehler: {e}")
            
            time.sleep(self._job_refresh_interval)
    
    # ========================================================================
    # Job Management
    # ========================================================================
    
    def list_jobs(self, limit: int = 100):
        """
        Liste alle Jobs (asynchron)
        
        Emits: JOB_STATUS_CHANGED mit allen Jobs
        """
        task = Task(
            task_id=f"list_jobs_{datetime.now().timestamp()}",
            func=self._list_jobs_sync,
            args=(limit,),
            callback=lambda jobs: self.event_bus.emit(
                EventType.JOB_STATUS_CHANGED,
                {"jobs": jobs},
                source="JobService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.BACKEND_ERROR,
                {"error": str(e), "operation": "list_jobs"},
                source="JobService"
            ),
            priority=7
        )
        self.task_executor.submit(task)
    
    @PerformanceProfiler.profile
    def _list_jobs_sync(self, limit: int) -> List[Dict]:
        """Synchrone Job-List-Implementierung mit Smart Polling + Resilience"""
        # ✅ UPDATED: Use Ingestion Backend for job queries
        response = self._make_request(
            "GET",
            f"{self.ingestion_base_url}/jobs",  # ✅ Changed from self.base_url
            params={"limit": limit},
            use_circuit_breaker=True,
            use_retry=True
        )
        jobs = response.json()
        
        # Smart Polling: Prüfe ob sich Jobs geändert haben
        jobs_changed = False
        current_update = datetime.now()
        
        with self._job_cache_lock:
            # Vergleiche mit Cache
            if len(jobs) != len(self._job_cache):
                jobs_changed = True
            else:
                for job in jobs:
                    job_id = job['job_id']
                    cached_job = self._job_cache.get(job_id)
                    
                    # Neue Job oder Status-Änderung?
                    if not cached_job or cached_job.get('status') != job.get('status'):
                        jobs_changed = True
                        break
                    
                    # Progress-Änderung?
                    if cached_job.get('progress') != job.get('progress'):
                        jobs_changed = True
                        break
            
            # Update Cache nur bei Änderungen
            if jobs_changed:
                for job in jobs:
                    self._job_cache[job['job_id']] = job
                self._last_job_update = current_update
                logger.debug(f"Jobs geändert - Cache aktualisiert ({len(jobs)} Jobs)")
            else:
                logger.debug(f"Keine Job-Änderungen - Cache unverändert")
        
        # Event nur bei Änderungen emittieren (spart UI-Updates)
        if jobs_changed:
            return jobs
        else:
            return []  # Empty list = keine Änderungen
    
    def get_job_details(self, job_id: str):
        """
        Holt detaillierte Job-Informationen inkl. Metriken (asynchron)
        
        Emits: JOB_DETAILS_LOADED mit Job-Details und Metriken
        """
        task = Task(
            task_id=f"get_job_details_{job_id}",
            func=self._get_job_details_sync,
            args=(job_id,),
            callback=lambda details: self.event_bus.emit(
                EventType.JOB_PROGRESS_UPDATE,  # Reuse existing event type
                {"job_id": job_id, "details": details},
                source="JobService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.BACKEND_ERROR,
                {"error": str(e), "operation": "get_job_details", "job_id": job_id},
                source="JobService"
            ),
            priority=7
        )
        self.task_executor.submit(task)
    
    def _get_job_details_sync(self, job_id: str) -> Dict:
        """Synchrone Job-Details-Implementierung mit Resilience"""
        # ✅ UPDATED: Use Ingestion Backend for job status
        status_response = self._make_request(
            "GET",
            f"{self.ingestion_base_url}/jobs/{job_id}/status",  # ✅ Changed from self.base_url
            use_circuit_breaker=True,
            use_retry=True
        )
        job_status = status_response.json()
        
        # Hole Job-Metriken (optional, ohne Circuit Breaker für Fehlertoleranz)
        try:
            metrics_response = self._make_request(
                "GET",
                f"{self.ingestion_base_url}/jobs/{job_id}/metrics",  # ✅ Changed from self.base_url
                use_circuit_breaker=False,
                use_retry=True
            )
            job_metrics = metrics_response.json()
        except Exception:
            job_metrics = {}
        
        # Kombiniere Status + Metriken
        details = {**job_status, "metrics": job_metrics}
        
        # Update Cache
        with self._job_cache_lock:
            self._job_cache[job_id] = details
        
        return details
    
    def pause_job(self, job_id: str):
        """Pausiert Job"""
        task = Task(
            task_id=f"pause_job_{job_id}",
            func=self._pause_job_sync,
            args=(job_id,),
            callback=lambda result: self.event_bus.emit(
                EventType.JOB_STATUS_CHANGED,
                {"job_id": job_id, "status": "paused", "result": result},
                source="JobService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.JOB_FAILED,
                {"job_id": job_id, "error": str(e)},
                source="JobService"
            ),
            priority=8
        )
        self.task_executor.submit(task)
    
    def _pause_job_sync(self, job_id: str) -> Dict:
        """Synchrone Pause-Implementierung"""
        response = self.session.post(f"{self.base_url}/jobs/{job_id}/pause")
        response.raise_for_status()
        return response.json()
    
    def resume_job(self, job_id: str):
        """Setzt Job fort"""
        task = Task(
            task_id=f"resume_job_{job_id}",
            func=self._resume_job_sync,
            args=(job_id,),
            callback=lambda result: self.event_bus.emit(
                EventType.JOB_STATUS_CHANGED,
                {"job_id": job_id, "status": "processing", "result": result},
                source="JobService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.JOB_FAILED,
                {"job_id": job_id, "error": str(e)},
                source="JobService"
            ),
            priority=8
        )
        self.task_executor.submit(task)
    
    def _resume_job_sync(self, job_id: str) -> Dict:
        """Synchrone Resume-Implementierung"""
        response = self.session.post(f"{self.base_url}/jobs/{job_id}/resume")
        response.raise_for_status()
        return response.json()
    
    def cancel_job(self, job_id: str):
        """Storniert Job"""
        task = Task(
            task_id=f"cancel_job_{job_id}",
            func=self._cancel_job_sync,
            args=(job_id,),
            callback=lambda result: self.event_bus.emit(
                EventType.JOB_STATUS_CHANGED,
                {"job_id": job_id, "status": "cancelled", "result": result},
                source="JobService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.JOB_FAILED,
                {"job_id": job_id, "error": str(e)},
                source="JobService"
            ),
            priority=9
        )
        self.task_executor.submit(task)
    
    def _cancel_job_sync(self, job_id: str) -> Dict:
        """Synchrone Cancel-Implementierung"""
        response = self.session.delete(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Upload Operations
    # ========================================================================
    
    @PerformanceProfiler.profile
    def upload_files(self, file_paths: List[str], batch_size: int = 10):
        """
        Upload Dateien (asynchron mit Progress-Events)
        
        Args:
            file_paths: Liste der Dateipfade
            batch_size: Batch-Größe
        """
        self.event_bus.emit(
            EventType.UPLOAD_STARTED,
            {
                "total_files": len(file_paths),
                "batch_size": batch_size
            },
            source="UploadService"
        )
        
        task = Task(
            task_id=f"upload_files_{datetime.now().timestamp()}",
            func=self._upload_files_sync,
            args=(file_paths, batch_size),
            callback=lambda result: self.event_bus.emit(
                EventType.UPLOAD_FINISHED,
                {"result": result},
                source="UploadService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.UPLOAD_ERROR,
                {"error": str(e)},
                source="UploadService"
            ),
            priority=9
        )
        self.task_executor.submit(task)
    
    def _upload_files_sync(self, file_paths: List[str], batch_size: int) -> Dict:
        """Synchrone Upload-Implementierung mit Progress-Events + Resilience"""
        results = []
        
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            files = []
            
            try:
                for file_path in batch:
                    files.append((
                        'files',
                        (Path(file_path).name, open(file_path, 'rb'), 'application/octet-stream')
                    ))
                
                # ✅ UPDATED: Use Ingestion Backend (Port 45679) instead of Main Backend
                response = self._make_request(
                    "POST",
                    f"{self.ingestion_base_url}/upload/files",  # ✅ Changed from self.base_url
                    files=files,
                    use_circuit_breaker=False,  # Uploads nicht im Circuit Breaker
                    use_retry=True  # Aber Retry bei transienten Fehlern
                )
                result = response.json()
                results.append(result)
                
                # Progress Event
                self.event_bus.emit(
                    EventType.UPLOAD_BATCH_COMPLETE,
                    {
                        "batch_num": (i // batch_size) + 1,
                        "files_count": len(batch),
                        "total_uploaded": min(i + batch_size, len(file_paths)),
                        "total_files": len(file_paths),
                        "result": result
                    },
                    source="UploadService"
                )
                
            finally:
                # Close files
                for _, file_tuple in files:
                    if hasattr(file_tuple[1], 'close'):
                        file_tuple[1].close()
        
        return {"batches": len(results), "results": results}
    
    # ========================================================================
    # Directory Analysis
    # ========================================================================
    
    def analyze_directory(self, directory_path: str):
        """
        Analysiert Verzeichnis (asynchron)
        
        Emits: DIRECTORY_ANALYSIS_COMPLETE mit Ergebnissen
        """
        from covina_gui import DirectoryAnalyzer  # Import hier um zirkuläre Imports zu vermeiden
        
        self.event_bus.emit(
            EventType.DIRECTORY_ANALYSIS_STARTED,
            {"path": directory_path},
            source="DirectoryAnalyzer"
        )
        
        task = Task(
            task_id=f"analyze_dir_{directory_path}",
            func=DirectoryAnalyzer.analyze_directory,
            args=(directory_path,),
            callback=lambda result: self.event_bus.emit(
                EventType.DIRECTORY_ANALYSIS_COMPLETE,
                {"path": directory_path, "analysis": result},
                source="DirectoryAnalyzer"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.DIRECTORY_ANALYSIS_ERROR,
                {"path": directory_path, "error": str(e)},
                source="DirectoryAnalyzer"
            ),
            priority=6
        )
        self.task_executor.submit(task)
    
    def upload_directory(self, directory_path: str, chunk_size: int = 50):
        """
        Uploaded Verzeichnis an Backend (asynchron)
        
        Args:
            directory_path: Pfad zum Verzeichnis
            chunk_size: Chunk-Größe für Backend-Verarbeitung
        
        Emits: UPLOAD_STARTED, UPLOAD_FINISHED, UPLOAD_ERROR
        
        Note: Uses NEW /upload/directory API (returns scan_job_id, requires polling)
        """
        def _upload_directory_sync():
            """Synchroner Directory-Upload mit Scan-Polling"""
            try:
                # ✅ Step 1: Start directory scan (returns scan_job_id immediately)
                response = self._make_request(
                    "POST",
                    f"{self.ingestion_base_url}/upload/directory",
                    data={
                        "directory_path": directory_path,
                        "chunk_size": chunk_size
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    use_circuit_breaker=False,
                    use_retry=True
                )
                result = response.json()
                scan_job_id = result.get('scan_job_id')
                
                if not scan_job_id:
                    raise ValueError("Backend returned no scan_job_id")
                
                logger.info(f"📂 Directory scan started: {scan_job_id}")
                
                # ✅ Step 2: Poll scan status until completed
                import time
                max_wait = 300  # 5 minutes timeout
                poll_interval = 2  # Poll every 2 seconds
                elapsed = 0
                
                while elapsed < max_wait:
                    time.sleep(poll_interval)
                    elapsed += poll_interval
                    
                    # Get scan status
                    scan_response = self._make_request(
                        "GET",
                        f"{self.ingestion_base_url}/scan/{scan_job_id}",
                        use_circuit_breaker=False,
                        use_retry=False
                    )
                    scan_status = scan_response.json()
                    
                    status = scan_status.get('status')
                    files_found = scan_status.get('files_found', 0)
                    jobs_created = scan_status.get('upload_jobs_created', 0)
                    
                    logger.info(f"📊 Scan {scan_job_id}: {status} | Files: {files_found} | Jobs: {jobs_created}")
                    
                    # Emit progress update
                    self.event_bus.emit(
                        EventType.UPLOAD_PROGRESS,
                        {
                            "directory": directory_path,
                            "scan_job_id": scan_job_id,
                            "status": status,
                            "files_found": files_found,
                            "jobs_created": jobs_created
                        },
                        source="DirectoryUpload"
                    )
                    
                    if status == "completed":
                        # Scan completed successfully
                        upload_job_ids = scan_status.get('upload_job_ids', [])
                        
                        # Emit success event
                        self.event_bus.emit(
                            EventType.UPLOAD_FINISHED,
                            {
                                "directory": directory_path,
                                "scan_job_id": scan_job_id,
                                "total_files": files_found,
                                "upload_jobs": upload_job_ids,
                                "result": scan_status
                            },
                            source="DirectoryUpload"
                        )
                        
                        return scan_status
                    
                    elif status == "error":
                        error_msg = scan_status.get('error', 'Unknown error')
                        raise RuntimeError(f"Scan failed: {error_msg}")
                
                # Timeout reached
                raise TimeoutError(f"Scan {scan_job_id} did not complete within {max_wait}s")
                
            except Exception as e:
                logger.error(f"❌ Directory-Upload fehlgeschlagen: {e}")
                self.event_bus.emit(
                    EventType.UPLOAD_ERROR,
                    {
                        "directory": directory_path,
                        "error": str(e)
                    },
                    source="DirectoryUpload"
                )
                raise
        
        # Emit UPLOAD_STARTED
        self.event_bus.emit(
            EventType.UPLOAD_STARTED,
            {
                "directory": directory_path,
                "total_files": 0,  # Unknown at this point
                "chunk_size": chunk_size
            },
            source="DirectoryUpload"
        )
        
        task = Task(
            task_id=f"upload_dir_{datetime.now().timestamp()}",
            func=_upload_directory_sync,
            priority=7
        )
        self.task_executor.submit(task)


# ============================================================================
# Beispiel-Nutzung (Unit-Test-freundlich)
# ============================================================================

if __name__ == "__main__":
    # Logging für Demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Service erstellen
    service = CovinaBackendService()
    
    # Event-Listener registrieren (UI würde das tun)
    def on_backend_connected(event: Event):
        print(f"✅ Backend verbunden: {event.data['url']}")
    
    def on_job_status_changed(event: Event):
        jobs = event.data.get('jobs', [])
        print(f"📊 Job-Status Update: {len(jobs)} Jobs")
    
    service.event_bus.subscribe(EventType.BACKEND_CONNECTED, on_backend_connected)
    service.event_bus.subscribe(EventType.JOB_STATUS_CHANGED, on_job_status_changed)
    
    # Service starten
    service.start()
    
    # Demo: Jobs abrufen
    print("Starte Demo...")
    service.list_jobs(limit=10)
    
    # Warte auf Events
    time.sleep(3)
    
    # Cleanup
    service.stop()
    print("Demo beendet")
