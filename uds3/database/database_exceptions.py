#!/usr/bin/env python3
"""
UDS3 Database Exceptions
========================

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


class NotFoundException(DatabaseException):
    """Entry Not Found Fehler"""
    pass


# Alias für Kompatibilität
CollectionNotFoundError = NotFoundException


class ConfigurationException(DatabaseException):
    """Database Configuration Fehler"""
    pass
