from __future__ import annotations

import time
import pytest
from concurrent.futures import TimeoutError as FuturesTimeoutError

from ingestion.infrastructure.workers.worker_pool import WorkerPoolManager


# Top-level functions for pickling with ProcessPoolExecutor

def add(a, b):
    return a + b


def slow(n):
    time.sleep(n)
    return n


def test_worker_pool_io_submission():
    pool = WorkerPoolManager(io_workers=2, cpu_workers=1)
    pool.start()

    try:
        fut = pool.submit_io(add, 1, 2, timeout=1.0)
        assert fut.result(timeout=2.0) == 3
    finally:
        pool.stop()


def test_worker_pool_cpu_submission():
    pool = WorkerPoolManager(io_workers=1, cpu_workers=1)
    pool.start()

    try:
        fut = pool.submit_cpu(add, 3, 4, timeout=1.0)
        assert fut.result(timeout=5.0) == 7
    finally:
        pool.stop()


def test_worker_pool_backpressure():
    pool = WorkerPoolManager(io_workers=1, cpu_workers=1, io_queue_size=1)
    pool.start()

    try:
        # Occupy worker and queue
        fut1 = pool.submit_io(slow, 0.5, timeout=0.1)  # uses worker
        fut2 = pool.submit_io(slow, 0.5, timeout=0.1)  # fills queue
        # Third submission should timeout due to full queue
        with pytest.raises(TimeoutError):
            pool.submit_io(add, 1, 1, timeout=0.01)
        # The first two tasks should complete
        assert fut1.result(timeout=2.0) == 0.5
        assert fut2.result(timeout=2.0) == 0.5
    finally:
        pool.stop()


def test_worker_pool_stop_and_submit_after_stop():
    pool = WorkerPoolManager(io_workers=1, cpu_workers=1)
    pool.start()
    pool.stop()

    with pytest.raises(RuntimeError):
        pool.submit_io(add, 1, 1)
