#!/usr/bin/env python3
"""
UDS3 Database Exceptions
========================

✅ **COMPLETE IMPLEMENTATION** ✅

Custom exception classes for all UDS3 database operations.
Provides base DatabaseException and specialized exceptions for different error scenarios.

**Status:** COMPLETE - Production ready
**Created:** 16. Oktober 2025, 09:00 Uhr
**Purpose:** Fix missing module error in ChromaDB and Neo4j backends

This module provides:
- Base DatabaseException class
- Connection-related exceptions (ConnectionException, ConnectionError alias)
- Query-related exceptions (QueryException, QueryError alias)
- Data validation exceptions (ValidationException)
- Timeout and duplicate handling exceptions
- Not found exceptions (NotFoundException, CollectionNotFoundError alias)
- Configuration exceptions

All exceptions include compatibility aliases for backward compatibility
with existing database backend code.

Custom Exception Classes für Database Operations

Autor: UDS3 System
Datum: Oktober 2025
"""


class DatabaseException(Exception):
    """Base Exception für alle Database-Operationen"""
    pass


class ConnectionException(DatabaseException):
    """Database Connection Fehler"""
    pass


# Alias für Kompatibilität
ConnectionError = ConnectionException


class QueryException(DatabaseException):
    """Query Execution Fehler"""
    pass


# Alias für Kompatibilität
QueryError = QueryException


class ValidationException(DatabaseException):
    """Data Validation Fehler"""
    pass


class TimeoutException(DatabaseException):
    """Database Timeout Fehler"""
    pass


class DuplicateException(DatabaseException):
    """Duplicate Entry Fehler"""
    pass


class InsertException(DatabaseException):
    """Insert Operation Fehler"""
    pass


# Alias für Kompatibilität
InsertError = InsertException


class NotFoundException(DatabaseException):
    """Entry Not Found Fehler"""
    pass


# Alias für Kompatibilität
CollectionNotFoundError = NotFoundException


class ConfigurationException(DatabaseException):
    """Database Configuration Fehler"""
    pass


# ================================================================
# HELPER FUNCTIONS (Stub)
# ================================================================

def log_operation_start(operation: str, backend: str = "unknown", **kwargs):
    """
    Stub function for logging database operation start.
    
    Args:
        operation: Operation name (e.g., "insert", "query")
        backend: Backend name (e.g., "PostgreSQL", "ChromaDB")
        **kwargs: Additional context
    """
    pass  # Stub implementation - can be extended later


def log_operation_end(operation: str, backend: str = "unknown", success: bool = True, **kwargs):
    """
    Stub function for logging database operation end.
    
    Args:
        operation: Operation name
        backend: Backend name
        success: Whether operation succeeded
        **kwargs: Additional context (duration, error, etc.)
    """
    pass  # Stub implementation - can be extended later


def log_operation_success(operation: str, backend: str = "unknown", **kwargs):
    """Stub for logging a successful database operation (compat)."""
    pass


def log_operation_failure(operation: str, backend: str = "unknown", error: Exception | str = None, **kwargs):
    """Stub for logging a failed database operation (compat)."""
    pass


def log_operation_warning(operation: str, backend: str = "unknown", warning: Exception | str = None, **kwargs):
    """Stub for logging a warning-level database operation (compat)."""
    pass


def log_operation_info(operation: str, backend: str = "unknown", **kwargs):
    """Stub for logging an info-level database operation (compat)."""
    pass
