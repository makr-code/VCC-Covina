"""
Prometheus Instrumentation for FastAPI

Provides metrics endpoints and custom instrumentation:
- Request/response metrics (latency, count, errors)
- Database operation metrics
- Circuit breaker metrics

Usage:
    from ingestion.infrastructure.observability.prometheus_metrics import configure_prometheus
    
    app = FastAPI()
    configure_prometheus(app)
"""
from __future__ import annotations

from typing import Callable
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.registry import CollectorRegistry
import time


# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"]
)

# Database metrics
DB_OPERATION_COUNT = Counter(
    "db_operations_total",
    "Total database operations",
    ["database", "operation", "status"]
)

DB_OPERATION_LATENCY = Histogram(
    "db_operation_duration_seconds",
    "Database operation latency",
    ["database", "operation"]
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"]
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["service"]
)


async def prometheus_middleware(request: Request, call_next: Callable) -> Response:
    """Record Prometheus metrics for each request."""
    method = request.method
    endpoint = request.url.path
    
    # Track in-progress requests
    REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    
    # Measure latency
    start_time = time.time()
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception as e:
        status = 500
        raise
    finally:
        duration = time.time() - start_time
        
        # Record metrics
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
    
    return response


def configure_prometheus(app: FastAPI) -> None:
    """Configure Prometheus instrumentation for FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Add middleware
    app.middleware("http")(prometheus_middleware)
    
    # Add metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


# Helper functions for custom metrics
def record_db_operation(database: str, operation: str, duration: float, success: bool):
    """Record database operation metrics.
    
    Args:
        database: Database name (postgres, chromadb, neo4j, etc.)
        operation: Operation type (query, insert, update, etc.)
        duration: Operation duration in seconds
        success: Whether operation succeeded
    """
    status = "success" if success else "error"
    DB_OPERATION_COUNT.labels(database=database, operation=operation, status=status).inc()
    DB_OPERATION_LATENCY.labels(database=database, operation=operation).observe(duration)


def update_circuit_breaker_state(service: str, state: str):
    """Update circuit breaker state metric.
    
    Args:
        service: Service name (postgres, chromadb, neo4j, etc.)
        state: State name (closed, open, half_open)
    """
    state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state.lower(), -1)
    CIRCUIT_BREAKER_STATE.labels(service=service).set(state_value)


def record_circuit_breaker_failure(service: str):
    """Record circuit breaker failure.
    
    Args:
        service: Service name
    """
    CIRCUIT_BREAKER_FAILURES.labels(service=service).inc()
