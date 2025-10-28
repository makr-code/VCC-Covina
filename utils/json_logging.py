"""
JSON Structured Logging Module

Provides JSON-formatted logging with correlation ID tracking for request tracing.

Features:
- JSON log format for machine-readable logs (ELK, Splunk, etc.)
- Correlation ID context for distributed request tracing
- Custom fields: service_name, environment, version
- Thread-safe correlation ID storage

Usage:
    from utils.json_logging import setup_json_logging, set_correlation_id

    # Setup JSON logging for backend
    setup_json_logging("main_backend", level=logging.INFO)

    # In FastAPI middleware
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    set_correlation_id(correlation_id)
    # Now all logs will include correlation_id field

Dependencies:
    - pythonjsonlogger

Author: Covina Team
Date: 2025-01-17
"""

import logging
import os
import sys
from contextvars import ContextVar
from typing import Optional
from pythonjsonlogger import jsonlogger


# ContextVar for thread-safe correlation ID storage
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID for current async context.
    
    Args:
        correlation_id: Unique ID for request tracing (e.g., UUID)
    
    Example:
        set_correlation_id("550e8400-e29b-41d4-a716-446655440000")
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """
    Get correlation ID from current async context.
    
    Returns:
        Correlation ID or None if not set
    """
    return correlation_id_var.get()


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation_id to log records.
    
    Retrieves correlation ID from ContextVar and adds it to LogRecord
    so it can be included in JSON output.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to log record."""
        record.correlation_id = get_correlation_id() or "N/A"
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields.
    
    Adds:
    - service_name: Backend service identifier
    - environment: dev/staging/production
    - version: Application version
    - correlation_id: Request tracing ID (from filter)
    """
    
    def __init__(self, service_name: str = "covina", environment: str = "development", 
                 version: str = "1.0.0", *args, **kwargs):
        """
        Initialize JSON formatter with custom fields.
        
        Args:
            service_name: Name of the service (e.g., "main_backend")
            environment: Environment name (e.g., "production")
            version: Application version (e.g., "3.4.10")
        """
        self.service_name = service_name
        self.environment = environment
        self.version = version
        super().__init__(*args, **kwargs)
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """
        Add custom fields to JSON log record.
        
        Args:
            log_record: Dictionary to be JSON-serialized
            record: LogRecord instance
            message_dict: Dictionary from getMessage()
        """
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields manually (python-json-logger doesn't auto-add)
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        
        # Add custom fields
        log_record["service_name"] = self.service_name
        log_record["environment"] = self.environment
        log_record["version"] = self.version
        
        # correlation_id added by CorrelationIdFilter
        if not hasattr(record, "correlation_id"):
            log_record["correlation_id"] = "N/A"


def setup_json_logging(
    service_name: str = "covina",
    level: int = logging.INFO,
    environment: str = "development",
    version: str = "1.0.0"
) -> None:
    """
    Setup JSON structured logging for backend service.
    
    Configures:
    - JSON formatter with custom fields
    - Correlation ID filter
    - Console output (stdout)
    
    Args:
        service_name: Name of the service (e.g., "main_backend", "ingestion_backend")
        level: Logging level (default: INFO)
        environment: Environment name (default: "development")
        version: Application version (default: "1.0.0")
    
    Example:
        setup_json_logging("main_backend", level=logging.INFO, 
                          environment="production", version="3.4.10")
    
    Log Output Example:
        {
            "timestamp": "2025-01-17T10:30:45.123456",
            "level": "INFO",
            "name": "uvicorn.access",
            "message": "GET /health 200 OK",
            "service_name": "main_backend",
            "environment": "production",
            "version": "3.4.10",
            "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """
    # Create JSON formatter
    formatter = CustomJsonFormatter(
        service_name=service_name,
        environment=environment,
        version=version
        # No custom fmt - use default fields from python-json-logger
    )
    
    # Create correlation ID filter
    correlation_filter = CorrelationIdFilter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers (avoid duplicate logs)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(correlation_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)

    # Optional: Also log to file if environment variables are set
    # Use COVINA_LOG_FILE for all logs and COVINA_ERR_FILE for errors only
    log_file = os.getenv("COVINA_LOG_FILE")
    err_file = os.getenv("COVINA_ERR_FILE")
    
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(correlation_filter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # Fall back silently to console-only if file cannot be opened
            logging.getLogger(__name__).warning(f"Could not attach file logger '{log_file}': {e}")
    
    if err_file:
        try:
            err_handler = logging.FileHandler(err_file, encoding="utf-8")
            err_handler.setLevel(logging.ERROR)
            err_handler.setFormatter(formatter)
            err_handler.addFilter(correlation_filter)
            root_logger.addHandler(err_handler)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not attach error file logger '{err_file}': {e}")
    
    # Log setup confirmation (console + optional files)
    logging.info(f"JSON structured logging initialized for {service_name}")


def create_correlation_id_middleware():
    """
    Create FastAPI middleware for automatic correlation ID injection.
    
    Returns:
        Middleware function for FastAPI app.add_middleware()
    
    Example:
        from fastapi import FastAPI
        from utils.json_logging import create_correlation_id_middleware
        
        app = FastAPI()
        app.middleware("http")(create_correlation_id_middleware())
    
    Behavior:
        - Checks X-Correlation-ID header
        - Generates UUID if not provided
        - Sets correlation ID in context
        - Adds X-Correlation-ID to response headers
    """
    import uuid
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    
    async def correlation_middleware(request: Request, call_next):
        """Middleware that adds correlation ID to request context."""
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set in context
        set_correlation_id(correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    return correlation_middleware


# Example usage
if __name__ == "__main__":
    # Setup JSON logging
    setup_json_logging("example_service", level=logging.DEBUG, 
                      environment="development", version="1.0.0")
    
    # Set correlation ID
    set_correlation_id("test-correlation-id-12345")
    
    # Test logs
    logging.debug("Debug message")
    logging.info("Info message")
    logging.warning("Warning message")
    logging.error("Error message")
    
    # Without correlation ID
    set_correlation_id(None)
    logging.info("Log without correlation ID")
    
    print("\n--- Expected Output ---")
    print("Each log should be valid JSON with:")
    print("- timestamp, level, name, message")
    print("- service_name: example_service")
    print("- environment: development")
    print("- version: 1.0.0")
    print("- correlation_id: test-correlation-id-12345 (or N/A)")
