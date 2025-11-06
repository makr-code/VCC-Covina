"""
Circuit Breaker Pattern Implementation

Features:
- Configurable failure threshold and recovery timeout
- States: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
- Thread-safe implementation
- Automatic state transitions

Usage:
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    
    @breaker.call
    def risky_operation():
        # Database call, HTTP request, etc.
        pass
"""
from __future__ import annotations

import time
import threading
from enum import Enum
from typing import Callable, Any, TypeVar
from functools import wraps


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


T = TypeVar('T')


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """Circuit Breaker to prevent cascading failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception
    ):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery (HALF_OPEN)
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state (thread-safe)."""
        with self._lock:
            return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count (thread-safe)."""
        with self._lock:
            return self._failure_count
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed for recovery attempt."""
        return time.time() - self._last_failure_time >= self.recovery_timeout
    
    def call(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with circuit breaker.
        
        Usage:
            @breaker.call
            def database_query():
                ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with self._lock:
                if self._state == CircuitState.OPEN:
                    if self._should_attempt_reset():
                        self._state = CircuitState.HALF_OPEN
                        self._failure_count = 0
                    else:
                        raise CircuitBreakerError(
                            f"Circuit breaker OPEN (failures: {self._failure_count}, "
                            f"recovery in {self.recovery_timeout - (time.time() - self._last_failure_time):.1f}s)"
                        )
            
            try:
                result = func(*args, **kwargs)
                
                # Success: close circuit if half-open
                with self._lock:
                    if self._state == CircuitState.HALF_OPEN:
                        self._state = CircuitState.CLOSED
                        self._failure_count = 0
                
                return result
                
            except self.expected_exception as e:
                with self._lock:
                    self._failure_count += 1
                    self._last_failure_time = time.time()
                    
                    if self._failure_count >= self.failure_threshold:
                        self._state = CircuitState.OPEN
                
                raise e
        
        return wrapper
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0
