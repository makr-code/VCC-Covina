#!/usr/bin/env python3
"""
Covina Ingestion Backend - Exception Hierarchy
==============================================

OOP-Based Exception System für strukturierte Fehlerbehandlung.

Best Practices:
- Typed Exceptions (specific error types)
- Error Codes (machine-readable)
- Context Information (debugging details)
- Recovery Hints (actionable suggestions)
- DSGVO-compliant (no PII in error messages)

Author: Covina System
Date: 28. Oktober 2025
Version: 1.0.0
"""

from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime


class ErrorCode(Enum):
    """Machine-readable error codes for monitoring & alerting"""
    
    # Worker Pool Errors (1000-1099)
    WORKER_POOL_EXHAUSTED = 1000
    WORKER_CRASH = 1001
    WORKER_TIMEOUT = 1002
    WORKER_OOM = 1003
    
    # Database Errors (1100-1199)
    DB_CONNECTION_FAILED = 1100
    DB_TIMEOUT = 1101
    DB_CONSTRAINT_VIOLATION = 1102
    DB_TRANSACTION_FAILED = 1103
    DB_WRITE_ERROR = 1104
    
    # File Processing Errors (1200-1299)
    FILE_NOT_FOUND = 1200
    FILE_CORRUPTED = 1201
    FILE_TOO_LARGE = 1202
    FILE_PERMISSION_DENIED = 1203
    FILE_UNSUPPORTED_FORMAT = 1204
    
    # Memory Errors (1300-1399)
    MEMORY_LIMIT_EXCEEDED = 1300
    MEMORY_LEAK_DETECTED = 1301
    
    # Network Errors (1400-1499)
    NETWORK_TIMEOUT = 1400
    NETWORK_CONNECTION_REFUSED = 1401
    NETWORK_DNS_FAILURE = 1402
    
    # Business Logic Errors (1500-1599)
    VALIDATION_FAILED = 1500
    DUPLICATE_JOB = 1501
    JOB_NOT_FOUND = 1502
    
    # System Errors (1600-1699)
    CIRCUIT_BREAKER_OPEN = 1600
    RATE_LIMIT_EXCEEDED = 1601
    SHUTDOWN_IN_PROGRESS = 1602
    
    # Unknown (9999)
    UNKNOWN_ERROR = 9999


class ErrorSeverity(Enum):
    """Error severity levels for monitoring"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CovinaException(Exception):
    """
    Base Exception für alle Covina-spezifischen Fehler
    
    Provides:
    - Error code (machine-readable)
    - Severity (for monitoring)
    - Context (debugging info)
    - Recovery hints (actionable)
    - Timestamp (when error occurred)
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.recovery_hint = recovery_hint
        self.cause = cause
        self.timestamp = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to structured dict for logging/API responses"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code.value,
            "severity": self.severity.value,
            "context": self.context,
            "recovery_hint": self.recovery_hint,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        """Human-readable error representation"""
        parts = [
            f"[{self.error_code.name}] {self.message}",
        ]
        if self.recovery_hint:
            parts.append(f"Recovery: {self.recovery_hint}")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " | ".join(parts)


# ================================================================
# Worker Pool Exceptions
# ================================================================

class WorkerException(CovinaException):
    """Base exception for worker-related errors"""
    pass


class WorkerPoolExhaustedException(WorkerException):
    """Worker pool has no available workers"""
    
    def __init__(
        self,
        pool_type: str,
        queue_size: int,
        max_workers: int,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{pool_type} worker pool exhausted: {queue_size} items in queue, {max_workers} max workers",
            error_code=ErrorCode.WORKER_POOL_EXHAUSTED,
            severity=ErrorSeverity.WARNING,
            context={
                "pool_type": pool_type,
                "queue_size": queue_size,
                "max_workers": max_workers,
                **(context or {})
            },
            recovery_hint="Increase worker pool size or implement backpressure"
        )


class WorkerCrashException(WorkerException):
    """Worker process/thread crashed unexpectedly"""
    
    def __init__(
        self,
        worker_id: str,
        worker_type: str,
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{worker_type} worker {worker_id} crashed",
            error_code=ErrorCode.WORKER_CRASH,
            severity=ErrorSeverity.CRITICAL,
            context={
                "worker_id": worker_id,
                "worker_type": worker_type,
                **(context or {})
            },
            recovery_hint="Check worker logs for stack trace, may need to restart worker pool",
            cause=cause
        )


class WorkerTimeoutException(WorkerException):
    """Worker exceeded maximum execution time"""
    
    def __init__(
        self,
        worker_id: str,
        timeout_seconds: int,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Worker {worker_id} timeout after {timeout_seconds}s during {operation}",
            error_code=ErrorCode.WORKER_TIMEOUT,
            severity=ErrorSeverity.ERROR,
            context={
                "worker_id": worker_id,
                "timeout_seconds": timeout_seconds,
                "operation": operation,
                **(context or {})
            },
            recovery_hint="Increase timeout or optimize worker operation"
        )


class WorkerOOMException(WorkerException):
    """Worker ran out of memory"""
    
    def __init__(
        self,
        worker_id: str,
        memory_mb: float,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Worker {worker_id} out of memory ({memory_mb:.2f} MB)",
            error_code=ErrorCode.WORKER_OOM,
            severity=ErrorSeverity.CRITICAL,
            context={
                "worker_id": worker_id,
                "memory_mb": memory_mb,
                **(context or {})
            },
            recovery_hint="Reduce batch size or increase worker memory limit"
        )


# ================================================================
# Database Exceptions
# ================================================================

class DatabaseException(CovinaException):
    """Base exception for database-related errors"""
    pass


class DatabaseConnectionException(DatabaseException):
    """Database connection failed"""
    
    def __init__(
        self,
        db_type: str,
        host: str,
        port: int,
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Failed to connect to {db_type} at {host}:{port}",
            error_code=ErrorCode.DB_CONNECTION_FAILED,
            severity=ErrorSeverity.CRITICAL,
            context={
                "db_type": db_type,
                "host": host,
                "port": port,
                **(context or {})
            },
            recovery_hint="Check database is running and credentials are correct",
            cause=cause
        )


class DatabaseTimeoutException(DatabaseException):
    """Database operation timed out"""
    
    def __init__(
        self,
        db_type: str,
        operation: str,
        timeout_seconds: float,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{db_type} {operation} timeout after {timeout_seconds}s",
            error_code=ErrorCode.DB_TIMEOUT,
            severity=ErrorSeverity.ERROR,
            context={
                "db_type": db_type,
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                **(context or {})
            },
            recovery_hint="Increase timeout or optimize query"
        )


class DatabaseWriteException(DatabaseException):
    """Database write operation failed"""
    
    def __init__(
        self,
        database_type: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None
    ):
        super().__init__(
            message=f"{database_type} write failed during {operation}",
            error_code=ErrorCode.DB_WRITE_ERROR,
            severity=ErrorSeverity.ERROR,
            context={
                "database_type": database_type,
                "operation": operation,
                **(context or {})
            },
            recovery_hint=recovery_hint or f"Check {database_type} logs for write errors. Verify data format and constraints."
        )


# ================================================================
# File Processing Exceptions
# ================================================================

class FileProcessingException(CovinaException):
    """Base exception for file processing errors"""
    pass


class FileNotFoundException(FileProcessingException):
    """File not found at specified path"""
    
    def __init__(
        self,
        file_path: str,
        context: Optional[Dict[str, Any]] = None
    ):
        # DSGVO: Don't include full path in message (may contain PII)
        super().__init__(
            message=f"File not found: {Path(file_path).name}",
            error_code=ErrorCode.FILE_NOT_FOUND,
            severity=ErrorSeverity.WARNING,
            context={
                "file_name": Path(file_path).name,
                **(context or {})
            },
            recovery_hint="Check file exists and path is correct"
        )


class FileCorruptedException(FileProcessingException):
    """File is corrupted or unreadable"""
    
    def __init__(
        self,
        file_path: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"File corrupted: {Path(file_path).name} - {reason}",
            error_code=ErrorCode.FILE_CORRUPTED,
            severity=ErrorSeverity.ERROR,
            context={
                "file_name": Path(file_path).name,
                "reason": reason,
                **(context or {})
            },
            recovery_hint="Re-upload file or check file integrity"
        )


class FileTooLargeException(FileProcessingException):
    """File exceeds maximum size limit"""
    
    def __init__(
        self,
        file_path: str,
        file_size_mb: float,
        max_size_mb: float,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"File too large: {Path(file_path).name} ({file_size_mb:.2f} MB > {max_size_mb:.2f} MB limit)",
            error_code=ErrorCode.FILE_TOO_LARGE,
            severity=ErrorSeverity.WARNING,
            context={
                "file_name": Path(file_path).name,
                "file_size_mb": file_size_mb,
                "max_size_mb": max_size_mb,
                **(context or {})
            },
            recovery_hint="Split file into smaller chunks or increase size limit"
        )


# ================================================================
# Memory Exceptions
# ================================================================

class MemoryException(CovinaException):
    """Base exception for memory-related errors"""
    pass


class MemoryLimitExceededException(MemoryException):
    """Memory usage exceeded configured limit"""
    
    def __init__(
        self,
        current_mb: float,
        limit_mb: float,
        component: str,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{component} memory limit exceeded: {current_mb:.2f} MB > {limit_mb:.2f} MB",
            error_code=ErrorCode.MEMORY_LIMIT_EXCEEDED,
            severity=ErrorSeverity.CRITICAL,
            context={
                "current_mb": current_mb,
                "limit_mb": limit_mb,
                "component": component,
                **(context or {})
            },
            recovery_hint="Reduce batch size or increase memory limit"
        )


# ================================================================
# System Exceptions
# ================================================================

class CircuitBreakerException(CovinaException):
    """Circuit breaker is open, rejecting requests"""
    
    def __init__(
        self,
        service_name: str,
        failure_count: int,
        threshold: int,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Circuit breaker open for {service_name}: {failure_count} failures (threshold: {threshold})",
            error_code=ErrorCode.CIRCUIT_BREAKER_OPEN,
            severity=ErrorSeverity.WARNING,
            context={
                "service_name": service_name,
                "failure_count": failure_count,
                "threshold": threshold,
                **(context or {})
            },
            recovery_hint="Wait for circuit breaker to reset or fix underlying service issue"
        )


class ShutdownInProgressException(CovinaException):
    """System is shutting down, rejecting new requests"""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="System shutdown in progress, rejecting new requests",
            error_code=ErrorCode.SHUTDOWN_IN_PROGRESS,
            severity=ErrorSeverity.WARNING,
            context=context or {},
            recovery_hint="Wait for system to restart"
        )


# ================================================================
# Helper Functions
# ================================================================

from pathlib import Path

def wrap_exception(e: Exception, context: Optional[Dict[str, Any]] = None, recovery_hint: Optional[str] = None) -> CovinaException:
    """
    Wrap generic exceptions into structured CovinaException
    
    Args:
        e: Original exception
        context: Additional context information
        recovery_hint: Optional recovery hint for the error
        
    Returns:
        CovinaException with appropriate error code and context
    """
    # Map common exception types
    if isinstance(e, FileNotFoundError):
        return FileNotFoundException(
            file_path=str(context.get("file_path", "unknown")) if context else "unknown",
            context=context,
            recovery_hint=recovery_hint
        )
    elif isinstance(e, MemoryError):
        return MemoryLimitExceededException(
            current_mb=0.0,  # Unknown
            limit_mb=0.0,    # Unknown
            component=context.get("component", "unknown") if context else "unknown",
            context=context,
            recovery_hint=recovery_hint
        )
    elif isinstance(e, TimeoutError):
        return WorkerTimeoutException(
            worker_id=context.get("worker_id", "unknown") if context else "unknown",
            timeout_seconds=context.get("timeout", 0) if context else 0,
            operation=context.get("operation", "unknown") if context else "unknown",
            context=context,
            recovery_hint=recovery_hint
        )
    else:
        # Generic wrapper for unknown exceptions
        return CovinaException(
            message=str(e),
            error_code=ErrorCode.UNKNOWN_ERROR,
            severity=ErrorSeverity.ERROR,
            context=context or {},
            recovery_hint=recovery_hint or "Check logs for detailed error trace",
            cause=e
        )
