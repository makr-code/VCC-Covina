#!/usr/bin/env python3
"""
Covina Ingestion Backend - Circuit Breaker Pattern
==================================================

Verhindert Cascading Failures durch:
- Automatic failure detection
- Circuit opening (reject requests)
- Half-open state (test recovery)
- Automatic recovery
- Metrics & Monitoring

Author: Covina System
Date: 28. Oktober 2025
Version: 1.0.0
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional

from ingestion.exceptions import CircuitBreakerException

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0


class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementation
    
    States:
    - CLOSED: Normal operation, tracking failures
    - OPEN: Too many failures, rejecting all requests
    - HALF_OPEN: Testing if service recovered
    
    Transitions:
    - CLOSED → OPEN: When failure_threshold reached
    - OPEN → HALF_OPEN: After recovery_timeout
    - HALF_OPEN → CLOSED: When success_threshold reached
    - HALF_OPEN → OPEN: When any failure occurs
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,  # Open circuit after N failures
        recovery_timeout: int = 60,  # Try recovery after N seconds
        success_threshold: int = 2,  # Close circuit after N successes
        window_size: int = 60,  # Rolling window in seconds
        half_open_max_calls: int = 3  # Max test calls in half-open
    ):
        """
        Initialize Circuit Breaker
        
        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Consecutive failures to open circuit
            recovery_timeout: Seconds before trying recovery
            success_threshold: Consecutive successes to close circuit
            window_size: Rolling window for failure counting
            half_open_max_calls: Max calls to allow in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.window_size = window_size
        self.half_open_max_calls = half_open_max_calls
        
        # State
        self._state = CircuitState.CLOSED
        self._lock = threading.Lock()
        
        # Counters
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._half_open_calls = 0
        
        # Timestamps
        self._last_failure_time: Optional[datetime] = None
        self._last_state_change: datetime = datetime.utcnow()
        
        # Metrics
        self.metrics = CircuitMetrics()
        
        logger.info(
            f"[CIRCUIT] {name} initialized: "
            f"failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s"
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        with self._lock:
            return self._state
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerException: If circuit is open
            Exception: Original function exception
        """
        with self._lock:
            self.metrics.total_calls += 1
            
            # Check if we should allow the call
            if not self._can_attempt():
                self.metrics.rejected_calls += 1
                raise CircuitBreakerException(
                    service_name=self.name,
                    failure_count=self._consecutive_failures,
                    threshold=self.failure_threshold,
                    context={
                        "state": self._state.value,
                        "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None
                    }
                )
            
            # In HALF_OPEN, track test calls
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _can_attempt(self) -> bool:
        """Check if call should be attempted (NOT thread-safe, caller must lock)"""
        # CLOSED: Always allow
        if self._state == CircuitState.CLOSED:
            return True
        
        # OPEN: Check if recovery timeout passed
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                time_since_failure = (datetime.utcnow() - self._last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    logger.info(f"[CIRCUIT] {self.name}: OPEN → HALF_OPEN (recovery timeout)")
                    self._change_state(CircuitState.HALF_OPEN)
                    self._half_open_calls = 0
                    return True
            return False
        
        # HALF_OPEN: Allow limited test calls
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        
        return False
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self.metrics.successful_calls += 1
            self.metrics.last_success_time = datetime.utcnow()
            
            self._consecutive_failures = 0
            self._consecutive_successes += 1
            
            # HALF_OPEN → CLOSED: Enough successes
            if self._state == CircuitState.HALF_OPEN:
                if self._consecutive_successes >= self.success_threshold:
                    logger.info(
                        f"[CIRCUIT] {self.name}: HALF_OPEN → CLOSED "
                        f"({self._consecutive_successes} successes)"
                    )
                    self._change_state(CircuitState.CLOSED)
    
    def _on_failure(self, exception: Exception):
        """Handle failed call"""
        with self._lock:
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = datetime.utcnow()
            self._last_failure_time = datetime.utcnow()
            
            self._consecutive_successes = 0
            self._consecutive_failures += 1
            
            logger.warning(
                f"[CIRCUIT] {self.name}: Failure {self._consecutive_failures}/{self.failure_threshold} - {exception}"
            )
            
            # CLOSED → OPEN: Too many failures
            if self._state == CircuitState.CLOSED:
                if self._consecutive_failures >= self.failure_threshold:
                    logger.error(
                        f"[CIRCUIT] {self.name}: CLOSED → OPEN "
                        f"({self._consecutive_failures} failures)"
                    )
                    self._change_state(CircuitState.OPEN)
            
            # HALF_OPEN → OPEN: Any failure
            elif self._state == CircuitState.HALF_OPEN:
                logger.error(f"[CIRCUIT] {self.name}: HALF_OPEN → OPEN (recovery failed)")
                self._change_state(CircuitState.OPEN)
    
    def _change_state(self, new_state: CircuitState):
        """Change circuit state (NOT thread-safe, caller must lock)"""
        old_state = self._state
        self._state = new_state
        self._last_state_change = datetime.utcnow()
        self.metrics.state_changes += 1
        
        # Reset counters
        if new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0
            self._consecutive_successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._consecutive_successes = 0
            self._half_open_calls = 0
    
    def reset(self):
        """Manually reset circuit to CLOSED state"""
        with self._lock:
            logger.info(f"[CIRCUIT] {self.name}: Manual reset to CLOSED")
            self._change_state(CircuitState.CLOSED)
            self._consecutive_failures = 0
            self._consecutive_successes = 0
    
    def force_open(self):
        """Manually force circuit to OPEN state"""
        with self._lock:
            logger.warning(f"[CIRCUIT] {self.name}: Manually forced OPEN")
            self._change_state(CircuitState.OPEN)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        with self._lock:
            time_in_state = (datetime.utcnow() - self._last_state_change).total_seconds()
            
            success_rate = 0.0
            if self.metrics.total_calls > 0:
                success_rate = (self.metrics.successful_calls / self.metrics.total_calls) * 100
            
            return {
                "name": self.name,
                "state": self._state.value,
                "time_in_state_seconds": time_in_state,
                "calls": {
                    "total": self.metrics.total_calls,
                    "successful": self.metrics.successful_calls,
                    "failed": self.metrics.failed_calls,
                    "rejected": self.metrics.rejected_calls,
                    "success_rate_percent": success_rate
                },
                "failures": {
                    "consecutive": self._consecutive_failures,
                    "threshold": self.failure_threshold,
                    "last_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None
                },
                "successes": {
                    "consecutive": self._consecutive_successes,
                    "threshold": self.success_threshold,
                    "last_time": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None
                },
                "state_changes": self.metrics.state_changes
            }


# ================================================================
# Circuit Breaker Manager
# ================================================================

class CircuitBreakerManager:
    """Manages multiple circuit breakers"""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def get_or_create(
        self,
        name: str,
        **kwargs
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker"""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name=name, **kwargs)
            return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        with self._lock:
            return self._breakers.get(name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all circuit breakers"""
        with self._lock:
            return {
                name: breaker.get_metrics()
                for name, breaker in self._breakers.items()
            }
    
    def reset_all(self):
        """Reset all circuit breakers"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("[CIRCUIT] All breakers reset")


# ================================================================
# Global Instance
# ================================================================

_global_breaker_manager: Optional[CircuitBreakerManager] = None


def get_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager"""
    global _global_breaker_manager
    if _global_breaker_manager is None:
        _global_breaker_manager = CircuitBreakerManager()
    return _global_breaker_manager
