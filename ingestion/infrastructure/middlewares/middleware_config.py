"""
FastAPI Middlewares for Production

Provides:
- CORS configuration
- GZip compression
- Rate limiting (slowapi)
- Request ID tracking
- JSON structured logging

Usage:
    from ingestion.infrastructure.middlewares.middleware_config import configure_middlewares
    
    app = FastAPI()
    configure_middlewares(app)
"""
from __future__ import annotations

import uuid
import logging
import json
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# Configure JSON logging
class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request_id if available
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        
        # Add exception info if available
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)


def configure_json_logging():
    """Configure JSON structured logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


# Request ID middleware
async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """Add unique request ID to each request."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Request logging middleware
async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    """Log all requests with timing information."""
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log request
    logger = logging.getLogger(__name__)
    extra = {"request_id": request_id}
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra=extra
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response with timing
    duration = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} ({duration*1000:.2f}ms)",
        extra=extra
    )
    
    return response


# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)


def configure_middlewares(
    app: FastAPI,
    enable_cors: bool = True,
    enable_gzip: bool = True,
    enable_rate_limiting: bool = True,
    enable_json_logging: bool = True
) -> None:
    """Configure all production middlewares for FastAPI app.
    
    Args:
        app: FastAPI application instance
        enable_cors: Enable CORS middleware
        enable_gzip: Enable GZip compression
        enable_rate_limiting: Enable rate limiting
        enable_json_logging: Enable JSON structured logging
    """
    
    # JSON Logging
    if enable_json_logging:
        configure_json_logging()
    
    # CORS
    if enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # GZip Compression
    if enable_gzip:
        app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Request ID
    app.middleware("http")(request_id_middleware)
    
    # Request Logging
    app.middleware("http")(request_logging_middleware)
    
    # Rate Limiting
    if enable_rate_limiting:
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
