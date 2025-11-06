"""
Request Timeout and Retry Logic

Provides:
- Configurable request timeouts
- Exponential backoff retry logic
- Retry with jitter
- FastAPI timeout middleware

Usage:
    from ingestion.infrastructure.resilience.retry_logic import retry_with_backoff
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def unstable_operation():
        # Operation that may fail
        pass
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Callable, Optional, TypeVar, Any
from functools import wraps
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


T = TypeVar('T')


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


class TimeoutError(Exception):
    """Raised when operation times out."""
    pass


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> float:
    """Calculate backoff delay with exponential backoff and jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (exponential_base ** attempt), max_delay)
    
    if jitter:
        # Add random jitter (±25%)
        jitter_range = delay * 0.25
        delay = delay + random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: Optional[tuple[type[Exception], ...]] = None
):
    """Decorator for retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter
        retry_on: Tuple of exceptions to retry on (None = all exceptions)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry this exception
                    if retry_on and not isinstance(e, retry_on):
                        logger.warning(f"Exception {type(e).__name__} not in retry list, raising immediately")
                        raise
                    
                    # Last attempt, raise exception
                    if attempt == max_retries:
                        logger.error(f"All {max_retries} retry attempts exhausted for {func.__name__}")
                        raise RetryExhaustedError(f"Failed after {max_retries} retries") from e
                    
                    # Calculate delay and retry
                    delay = calculate_backoff_delay(
                        attempt,
                        base_delay=base_delay,
                        max_delay=max_delay,
                        exponential_base=exponential_base,
                        jitter=jitter
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception or RetryExhaustedError("Retry logic error")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry this exception
                    if retry_on and not isinstance(e, retry_on):
                        logger.warning(f"Exception {type(e).__name__} not in retry list, raising immediately")
                        raise
                    
                    # Last attempt, raise exception
                    if attempt == max_retries:
                        logger.error(f"All {max_retries} retry attempts exhausted for {func.__name__}")
                        raise RetryExhaustedError(f"Failed after {max_retries} retries") from e
                    
                    # Calculate delay and retry
                    delay = calculate_backoff_delay(
                        attempt,
                        base_delay=base_delay,
                        max_delay=max_delay,
                        exponential_base=exponential_base,
                        jitter=jitter
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception or RetryExhaustedError("Retry logic error")
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class TimeoutMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for request timeouts."""
    
    def __init__(self, app, timeout_seconds: float = 30.0):
        """Initialize timeout middleware.
        
        Args:
            app: FastAPI app
            timeout_seconds: Request timeout in seconds
        """
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        logger.info(f"TimeoutMiddleware initialized: timeout={timeout_seconds}s")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with timeout.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
            
        Raises:
            TimeoutError: If request times out
        """
        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request timed out after {self.timeout_seconds}s: {request.method} {request.url.path}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=504,
                content={"detail": f"Request timed out after {self.timeout_seconds}s"}
            )


def configure_timeout_middleware(app, timeout_seconds: float = 30.0):
    """Configure timeout middleware for FastAPI app.
    
    Args:
        app: FastAPI application
        timeout_seconds: Timeout in seconds
    """
    app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout_seconds)
    logger.info(f"Timeout middleware configured: {timeout_seconds}s")
