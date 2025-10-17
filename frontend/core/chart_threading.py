"""
Chart Threading Utilities
=========================

Provides:
- ChartType, ChartStatus enums
- ChartResult dataclass
- ChartWorker base class
- ChartThreadPool for background chart rendering

Designed to be lightweight and to avoid circular imports.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional


logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Chart types (reduced set - only active charts)
    
    🎯 OPTIMIZED (17. Oktober 2025):
    Removed 5 unused chart types:
    - CLASSIFICATION_PIE (removed from Database Health)
    - QUALITY_SPIDER (no data source)
    - BACKEND_MATRIX (removed from System Status)
    - PROCESSING_RATE (kept in Ingestion - wrong, but keeping for now)
    - STORAGE_USAGE (removed from Database Health)
    - SYSTEM_METRICS (removed from System Status)
    
    Active charts (7):
    - Home Dashboard: SYSTEM_HEALTH, BACKEND_STATUS, DOCUMENT_COUNTS, PERFORMANCE_GAUGE
    - Database Health: DATABASE_CONNECTIONS
    - Ingestion View: INGESTION_TIMELINE, PROCESSING_RATE
    """
    SYSTEM_HEALTH = "system_health"
    BACKEND_STATUS = "backend_status"
    DATABASE_CONNECTIONS = "database_connections"
    PERFORMANCE_GAUGE = "performance_gauge"
    DOCUMENT_COUNTS = "document_counts"
    INGESTION_TIMELINE = "ingestion_timeline"
    PROCESSING_RATE = "processing_rate"
    REFRESH_ALL = "refresh_all"


class ChartStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ChartResult:
    chart_id: str
    chart_type: ChartType
    status: ChartStatus
    figure: Optional[Any] = None
    error: Optional[str] = None
    render_time: float = 0.0


@dataclass
class ChartRequest:
    """Public request shape for compatibility with core.__init__ exports."""
    chart_id: str
    chart_type: ChartType
    data: Dict[str, Any]
    timeout: float = 10.0


class ChartWorker:
    """Base class for all chart workers."""

    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Any:
        raise NotImplementedError("render_chart must be implemented by subclasses")


class _ChartRequest:
    def __init__(
        self,
        chart_id: str,
        chart_type: ChartType,
        data: Dict[str, Any],
        callback: Callable[[ChartResult], None],
        timeout: float,
    ) -> None:
        self.chart_id = chart_id
        self.chart_type = chart_type
        self.data = data
        self.callback = callback
        self.timeout = max(0.0, float(timeout))


class ChartThreadPool:
    """
    Simple thread pool that renders charts using specialized ChartWorker classes.

    start(worker_mapping):
        worker_mapping: Dict[ChartType, Type[ChartWorker]]
    """

    def __init__(self, num_workers: int = 4) -> None:
        self.num_workers = max(1, int(num_workers))
        self._threads: list[threading.Thread] = []
        self._request_queue: "queue.Queue[_ChartRequest | None]" = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_mapping: Dict[ChartType, type[ChartWorker]] = {}
        self._active_tasks = 0
        self._lock = threading.Lock()

    def start(self, worker_mapping: Dict[ChartType, type[ChartWorker]]) -> None:
        self._worker_mapping = dict(worker_mapping)
        if self._threads:
            # Already started
            return
        self._stop_event.clear()
        for idx in range(self.num_workers):
            t = threading.Thread(target=self._worker_loop, name=f"ChartPool-{idx+1}", daemon=True)
            t.start()
            self._threads.append(t)
        logger.info(f"ChartThreadPool started with {len(self._threads)} workers")

    def submit_request(
        self,
        chart_id: str,
        chart_type: ChartType,
        data: Dict[str, Any],
        callback: Callable[[ChartResult], None],
        timeout: float = 10.0,
    ) -> bool:
        if self._stop_event.is_set():
            return False
        try:
            req = _ChartRequest(chart_id, chart_type, data, callback, timeout)
            self._request_queue.put_nowait(req)
            return True
        except queue.Full:
            return False

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active_tasks = self._active_tasks
        return {
            "workers": len(self._threads),
            "active_workers": sum(1 for t in self._threads if t.is_alive()),
            "request_queue_size": self._request_queue.qsize(),
            # We deliver results directly via callbacks, keep 0 for compatibility
            "result_queue_size": 0,
            "active_tasks": active_tasks,
        }

    def shutdown(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        # Send sentinels
        for _ in self._threads:
            self._request_queue.put(None)
        for t in self._threads:
            try:
                t.join(timeout=timeout)
            except Exception:
                pass
        self._threads.clear()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                req = self._request_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if req is None:
                # Sentinel for shutdown
                break

            with self._lock:
                self._active_tasks += 1

            start = time.perf_counter()
            result: Optional[ChartResult] = None
            try:
                worker_cls = self._worker_mapping.get(req.chart_type)
                if worker_cls is None:
                    raise RuntimeError(f"No worker registered for chart type: {req.chart_type}")
                worker = worker_cls()
                figure = worker.render_chart(req.data, config={})
                elapsed = time.perf_counter() - start
                status = ChartStatus.SUCCESS if elapsed <= req.timeout else ChartStatus.TIMEOUT
                # If timed out, we still deliver the result but mark as TIMEOUT
                result = ChartResult(
                    chart_id=req.chart_id,
                    chart_type=req.chart_type,
                    status=status,
                    figure=figure,
                    error=(f"Rendered in {elapsed:.2f}s > timeout {req.timeout:.2f}s" if status == ChartStatus.TIMEOUT else None),
                    render_time=elapsed,
                )
            except Exception as e:
                elapsed = time.perf_counter() - start
                result = ChartResult(
                    chart_id=req.chart_id,
                    chart_type=req.chart_type,
                    status=ChartStatus.ERROR,
                    figure=None,
                    error=str(e),
                    render_time=elapsed,
                )
                logger.error(f"Chart render error for {req.chart_type.value}: {e}")
            finally:
                try:
                    # Deliver result via callback
                    req.callback(result)  # type: ignore[arg-type]
                except Exception as cb_err:
                    logger.error(f"Chart callback error: {cb_err}")
                with self._lock:
                    self._active_tasks -= 1
