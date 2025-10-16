"""Lightweight schema helpers for saga-related tables.

This module intentionally keeps the migrations minimal and idempotent so it can
be executed in unit tests and development environments without requiring an
external migration framework.  The helpers operate against the relational
backend abstraction that is already used by the orchestrator/saga tooling.
"""
from __future__ import annotations

import logging
from typing import Dict, Iterable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table blueprints
# ---------------------------------------------------------------------------
SAGA_EVENTS_SCHEMA: Dict[str, str] = {
    "event_id": "TEXT PRIMARY KEY",
    "saga_id": "TEXT NOT NULL",
    "trace_id": "TEXT",
    "step_name": "TEXT",
    "event_type": "TEXT",
    "status": "TEXT",
    "duration_ms": "INTEGER",
    "payload": "TEXT",
    "error": "TEXT",
    "idempotency_key": "TEXT",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}

SAGAS_SCHEMA: Dict[str, str] = {
    "saga_id": "TEXT PRIMARY KEY",
    "name": "TEXT",
    "trace_id": "TEXT",
    "status": "TEXT",
    "context": "TEXT",
    "current_step": "TEXT",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TIMESTAMP",
}

AUDIT_LOG_SCHEMA: Dict[str, str] = {
    "audit_id": "TEXT PRIMARY KEY",
    "saga_id": "TEXT",
    "saga_name": "TEXT",
    "trace_id": "TEXT",
    "identity_key": "TEXT",
    "document_id": "TEXT",
    "step_name": "TEXT",
    "event_type": "TEXT",
    "status": "TEXT",
    "duration_ms": "INTEGER",
    "details": "TEXT",
    "actor": "TEXT",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}

IDENTITY_TRACES_SCHEMA: Dict[str, str] = {
    "trace_id": "TEXT PRIMARY KEY",
    "aktenzeichen": "TEXT",
    "stage": "TEXT",
    "status": "TEXT",
    "details": "TEXT",
    "observed_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}

IDENTITY_METRICS_SCHEMA: Dict[str, str] = {
    "metric_id": "TEXT PRIMARY KEY",
    "aktenzeichen": "TEXT",
    "metric_name": "TEXT",
    "metric_value": "REAL",
    "units": "TEXT",
    "metadata": "TEXT",
    "observed_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}

# ---------------------------------------------------------------------------
# Helper primitives
# ---------------------------------------------------------------------------

def _table_exists(rel_backend, table: str) -> bool:
    try:
        if hasattr(rel_backend, "get_tables"):
            tables = rel_backend.get_tables() or []
            if table in tables:
                return True
    except Exception as exc:  # pragma: no cover
        logger.debug("get_tables failed for %s: %s", table, exc)
    # Fallback: attempt to fetch schema (works for SQLite/PG)
    try:
        schema = _get_schema(rel_backend, table)
        return bool(schema)
    except Exception:
        return False


def _get_schema(rel_backend, table: str) -> Dict[str, Dict[str, str]]:
    try:
        if hasattr(rel_backend, "get_table_schema"):
            schema = rel_backend.get_table_schema(table) or {}
            if isinstance(schema, dict):
                return schema
    except Exception as exc:  # pragma: no cover
        logger.debug("get_table_schema failed for %s: %s", table, exc)
    return {}


def _ensure_table(rel_backend, table: str, schema: Dict[str, str]) -> None:
    if not _table_exists(rel_backend, table):
        if hasattr(rel_backend, "create_table"):
            logger.debug("Creating table %s", table)
            rel_backend.create_table(table, schema)
        else:  # pragma: no cover - defensive branch
            columns = ", ".join(f"{col} {ctype}" for col, ctype in schema.items())
            rel_backend.execute_query(f"CREATE TABLE IF NOT EXISTS {table} ({columns})")
        return

    existing = _get_schema(rel_backend, table)
    for column, definition in schema.items():
        if column not in existing:
            _add_column(rel_backend, table, column, definition)


def _add_column(rel_backend, table: str, column: str, definition: str) -> None:
    try:
        logger.debug("Adding column %s.%s", table, column)
        rel_backend.execute_query(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except Exception as exc:  # pragma: no cover - harmless if column exists already
        logger.debug("ALTER TABLE %s ADD COLUMN %s failed or redundant: %s", table, column, exc)


def _create_index(rel_backend, name: str, table: str, columns: Iterable[str]) -> None:
    cols = ", ".join(columns)
    try:
        rel_backend.execute_query(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})")
    except Exception as exc:  # pragma: no cover
        logger.debug("CREATE INDEX %s failed: %s", name, exc)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def ensure_idempotency_column(rel_backend) -> None:
    """Guarantee that `uds3_saga_events` exposes an `idempotency_key` column.

    The helper is idempotent: it will create the events table if it is missing
    and add the column (plus a helpful index) when necessary.  The signature is
    intentionally backend-agnostic so test doubles or lightweight adapters can
    call it without pulling in heavy migration tooling.
    """
    _ensure_table(rel_backend, "uds3_saga_events", SAGA_EVENTS_SCHEMA)

    # Make sure the column exists; if _ensure_table created the table it already does.
    schema = _get_schema(rel_backend, "uds3_saga_events")
    if "idempotency_key" not in schema:
        _add_column(rel_backend, "uds3_saga_events", "idempotency_key", "TEXT")

    _create_index(rel_backend, "idx_uds3_saga_events_idempotency", "uds3_saga_events", ["saga_id", "step_name", "idempotency_key"])


def ensure_saga_schema(rel_backend) -> None:
    """Create or extend the saga-related tables used by orchestrator tests."""
    _ensure_table(rel_backend, "uds3_sagas", SAGAS_SCHEMA)
    _ensure_table(rel_backend, "uds3_saga_events", SAGA_EVENTS_SCHEMA)
    _ensure_table(rel_backend, "uds3_audit_log", AUDIT_LOG_SCHEMA)

    # Observability tables (best-effort)
    _ensure_table(rel_backend, "administrative_identity_traces", IDENTITY_TRACES_SCHEMA)
    _ensure_table(rel_backend, "administrative_identity_metrics", IDENTITY_METRICS_SCHEMA)

    # Helpful indexes for queries used in orchestrator/recovery workflow
    _create_index(rel_backend, "idx_uds3_sagas_status", "uds3_sagas", ["status"])
    _create_index(rel_backend, "idx_uds3_saga_events_saga_step", "uds3_saga_events", ["saga_id", "step_name"])


__all__ = [
    "ensure_idempotency_column",
    "ensure_saga_schema",
]
