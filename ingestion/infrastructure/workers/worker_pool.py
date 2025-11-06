"""
Worker Pool Manager

Provides:
- Thread (I/O) and Process (CPU) pools
- Bounded queues with backpressure
- Graceful start/stop
- Simple metrics

Usage:
    from ingestion.infrastructure.workers.worker_pool import WorkerPoolManager

    pool = WorkerPoolManager(io_workers=10, cpu_workers=4)
    pool.start()

    fut = pool.submit_io(func, 1, 2)
    result = fut.result(timeout=5)

    pool.stop()
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from queue import Queue, Full, Empty
from typing import Callable, Any, Optional, Tuple

from prometheus_client import Gauge, Counter


# Prometheus metrics
IO_QUEUE_SIZE = Gauge("worker_io_queue_size", "Current size of IO task queue")
CPU_QUEUE_SIZE = Gauge("worker_cpu_queue_size", "Current size of CPU task queue")
IO_TASKS_TOTAL = Counter("worker_io_tasks_total", "Total IO tasks processed", ["status"]) 
CPU_TASKS_TOTAL = Counter("worker_cpu_tasks_total", "Total CPU tasks processed", ["status"]) 


@dataclass
class _Task:
    func: Callable
    args: Tuple[Any, ...]
    kwargs: dict
    future: Future


class WorkerPoolManager:
    def __init__(
        self,
        io_workers: int = 10,
        cpu_workers: int = 4,
        io_queue_size: int = 100,
        cpu_queue_size: int = 100,
        name: str = "worker_pool",
    ) -> None:
        self.io_workers = io_workers
        self.cpu_workers = cpu_workers
        self.io_queue_size = io_queue_size
        self.cpu_queue_size = cpu_queue_size
        self.name = name

        self._io_queue: Queue[_Task] = Queue(maxsize=io_queue_size)
        self._cpu_queue: Queue[_Task] = Queue(maxsize=cpu_queue_size)

        self._io_executor: Optional[ThreadPoolExecutor] = None
        self._cpu_executor: Optional[ProcessPoolExecutor] = None

        self._io_dispatcher: Optional[threading.Thread] = None
        self._cpu_dispatcher: Optional[threading.Thread] = None

        self._running = False
        self._lock = threading.Lock()
        # Capacity semaphores implement backpressure across executor+queue
        self._io_capacity = threading.BoundedSemaphore(self.io_workers + self.io_queue_size)
        self._cpu_capacity = threading.BoundedSemaphore(self.cpu_workers + self.cpu_queue_size)

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True

            self._io_executor = ThreadPoolExecutor(max_workers=self.io_workers, thread_name_prefix=f"{self.name}-io")
            self._cpu_executor = ProcessPoolExecutor(max_workers=self.cpu_workers)

            self._io_dispatcher = threading.Thread(target=self._dispatch_loop, args=(self._io_queue, self._io_executor, IO_QUEUE_SIZE, IO_TASKS_TOTAL), daemon=True)
            self._cpu_dispatcher = threading.Thread(target=self._dispatch_loop, args=(self._cpu_queue, self._cpu_executor, CPU_QUEUE_SIZE, CPU_TASKS_TOTAL), daemon=True)

            self._io_dispatcher.start()
            self._cpu_dispatcher.start()

    def stop(self, wait: bool = True, timeout: Optional[float] = 10.0) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False

        # Wait dispatchers
        if wait:
            if self._io_dispatcher:
                self._io_dispatcher.join(timeout=timeout)
            if self._cpu_dispatcher:
                self._cpu_dispatcher.join(timeout=timeout)

        # Shutdown executors
        if self._io_executor:
            self._io_executor.shutdown(wait=wait, cancel_futures=True)
        if self._cpu_executor:
            self._cpu_executor.shutdown(wait=wait, cancel_futures=True)

    def _dispatch_loop(self, queue: Queue[_Task], executor, queue_gauge: Gauge, counter: Counter):
        while self._running or not queue.empty():
            try:
                queue_gauge.set(queue.qsize())
                task = queue.get(timeout=0.1)
            except Empty:
                continue

            # ThreadPool path can run a closure directly; ProcessPool must run picklable target
            if isinstance(executor, ProcessPoolExecutor):
                exec_future = executor.submit(task.func, *task.args, **task.kwargs)

                def on_done(fut):
                    try:
                        res = fut.result()
                        task.future.set_result(res)
                        counter.labels(status="success").inc()
                    except Exception as e:
                        task.future.set_exception(e)
                        counter.labels(status="error").inc()
                    finally:
                        queue.task_done()
                        # release capacity
                        try:
                            self._cpu_capacity.release()
                        except ValueError:
                            pass

                exec_future.add_done_callback(lambda f: on_done(f))
            else:
                def run_task(t: _Task):
                    try:
                        res = t.func(*t.args, **t.kwargs)
                        t.future.set_result(res)
                        counter.labels(status="success").inc()
                    except Exception as e:
                        t.future.set_exception(e)
                        counter.labels(status="error").inc()
                    finally:
                        queue.task_done()
                        # release capacity
                        try:
                            self._io_capacity.release()
                        except ValueError:
                            pass

                # Submit to executor
                executor.submit(run_task, task)

    def _ensure_running(self):
        if not self._running:
            raise RuntimeError("WorkerPoolManager is not running. Call start() first.")

    def submit_io(self, func: Callable, *args, timeout: Optional[float] = None, **kwargs) -> Future:
        """Submit a task to the IO thread pool via bounded queue.
        If queue is full and timeout elapses, raise TimeoutError.
        """
        self._ensure_running()
        task = _Task(func=func, args=args, kwargs=kwargs, future=Future())
        try:
            # acquire capacity token (executor slots + queue slots)
            acquired = self._io_capacity.acquire(timeout=timeout) if timeout is not None else self._io_capacity.acquire()
            if not acquired:
                raise TimeoutError("IO capacity exhausted")
            self._io_queue.put(task, timeout=timeout)
            IO_QUEUE_SIZE.set(self._io_queue.qsize())
            return task.future
        except Full:
            # failed to enqueue, release acquired capacity
            try:
                self._io_capacity.release()
            except ValueError:
                pass
            raise TimeoutError("IO queue is full")

    def submit_cpu(self, func: Callable, *args, timeout: Optional[float] = None, **kwargs) -> Future:
        """Submit a task to the CPU process pool via bounded queue.
        If queue is full and timeout elapses, raise TimeoutError.
        Note: func must be picklable.
        """
        self._ensure_running()
        task = _Task(func=func, args=args, kwargs=kwargs, future=Future())
        try:
            acquired = self._cpu_capacity.acquire(timeout=timeout) if timeout is not None else self._cpu_capacity.acquire()
            if not acquired:
                raise TimeoutError("CPU capacity exhausted")
            self._cpu_queue.put(task, timeout=timeout)
            CPU_QUEUE_SIZE.set(self._cpu_queue.qsize())
            return task.future
        except Full:
            try:
                self._cpu_capacity.release()
            except ValueError:
                pass
            raise TimeoutError("CPU queue is full")

    # Introspection helpers
    def io_queue_size(self) -> int:
        return self._io_queue.qsize()

    def cpu_queue_size(self) -> int:
        return self._cpu_queue.qsize()
