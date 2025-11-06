import pytest
import time
from ingestion.infrastructure.circuit_breakers.circuit_breaker import (
    CircuitBreaker, CircuitBreakerError, CircuitState
)


def test_circuit_closed_initially():
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_successful_calls_keep_circuit_closed():
    breaker = CircuitBreaker(failure_threshold=3)
    
    @breaker.call
    def success_func():
        return "ok"
    
    for _ in range(5):
        assert success_func() == "ok"
    
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_failures_open_circuit():
    breaker = CircuitBreaker(failure_threshold=3)
    
    @breaker.call
    def failing_func():
        raise RuntimeError("fail")
    
    # First 2 failures
    for _ in range(2):
        with pytest.raises(RuntimeError):
            failing_func()
    
    assert breaker.state == CircuitState.CLOSED  # Still closed
    assert breaker.failure_count == 2
    
    # Third failure opens circuit
    with pytest.raises(RuntimeError):
        failing_func()
    
    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 3


def test_open_circuit_rejects_calls():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=10)
    
    @breaker.call
    def failing_func():
        raise RuntimeError("fail")
    
    # Open the circuit
    for _ in range(2):
        with pytest.raises(RuntimeError):
            failing_func()
    
    assert breaker.state == CircuitState.OPEN
    
    # Now calls should be rejected immediately
    with pytest.raises(CircuitBreakerError):
        failing_func()


def test_half_open_recovery():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)  # Fast recovery for test
    
    call_count = 0
    
    @breaker.call
    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise RuntimeError("fail")
        return "ok"
    
    # Open circuit
    for _ in range(2):
        with pytest.raises(RuntimeError):
            flaky_func()
    
    assert breaker.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.15)
    
    # Next call should attempt recovery (HALF_OPEN)
    assert flaky_func() == "ok"
    assert breaker.state == CircuitState.CLOSED  # Success closes circuit


def test_manual_reset():
    breaker = CircuitBreaker(failure_threshold=2)
    
    @breaker.call
    def failing_func():
        raise RuntimeError("fail")
    
    # Open circuit
    for _ in range(2):
        with pytest.raises(RuntimeError):
            failing_func()
    
    assert breaker.state == CircuitState.OPEN
    
    # Manual reset
    breaker.reset()
    
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0
