"""Simple DB migration helpers used by tests and setup scripts.

Provides runtime-safe function to ensure `idempotency_key` column exists on
`uds3_saga_events` and to create an index for it. Works for SQLite and Postgres
with best-effort semantics.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def ensure_idempotency_column(relational_backend: Any) -> None:
    """Ensure the `idempotency_key` column exists on uds3_saga_events.

    This function performs ALTER TABLE ADD COLUMN if necessary and creates an
    index. It's idempotent (best-effort) and logs failures but does not raise.
    """
    try:
        if not hasattr(relational_backend, 'execute_query'):
            return

        # Read schema if possible
        cols = None
        try:
            if hasattr(relational_backend, 'get_table_schema'):
                schema = relational_backend.get_table_schema('uds3_saga_events')
                cols = set(schema.keys()) if isinstance(schema, dict) else None
            else:
                rows = relational_backend.execute_query("PRAGMA table_info(uds3_saga_events)")
                cols = {r['name'] for r in rows} if rows else None
        except Exception:
            cols = None

        if cols and 'idempotency_key' in cols:
            return

        # Try SQLite ALTER TABLE
        try:
            relational_backend.execute_query('ALTER TABLE uds3_saga_events ADD COLUMN idempotency_key TEXT')
        except Exception:
            # Try Postgres syntax (IF NOT EXISTS)
            try:
                relational_backend.execute_query('ALTER TABLE uds3_saga_events ADD COLUMN IF NOT EXISTS idempotency_key TEXT')
            except Exception as exc:
                logger.debug('Could not add idempotency_key column: %s', exc)

        # Create index if possible
        try:
            relational_backend.execute_query('CREATE INDEX IF NOT EXISTS idx_saga_events_idempotency ON uds3_saga_events(idempotency_key)')
        except Exception:
            try:
                relational_backend.execute_query('CREATE INDEX idx_saga_events_idempotency ON uds3_saga_events(idempotency_key)')
            except Exception as exc:
                logger.debug('Could not create idempotency index: %s', exc)

    except Exception as exc:  # pragma: no cover - defensive
        logger.debug('ensure_idempotency_column failed: %s', exc)


def ensure_saga_schema(relational_backend: Any) -> None:
    """Ensure the minimal SAGA schema exists in the relational backend.

    Creates tables: uds3_sagas, uds3_saga_events, uds3_audit_log, uds3_saga_metrics
    with idempotent CREATE TABLE IF NOT EXISTS statements.
    """
    try:
        if not hasattr(relational_backend, 'execute_query'):
            return

        # Create tables (SQLite/Postgres compatible SQL)
        relational_backend.execute_query('''
            CREATE TABLE IF NOT EXISTS uds3_sagas (
                saga_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                trace_id TEXT,
                status TEXT NOT NULL,
                context TEXT,
                current_step TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        relational_backend.execute_query('''
            CREATE TABLE IF NOT EXISTS uds3_saga_events (
                event_id TEXT PRIMARY KEY,
                saga_id TEXT NOT NULL,
                trace_id TEXT,
                step_name TEXT,
                event_type TEXT NOT NULL,
                status TEXT,
                duration_ms INTEGER,
                payload TEXT,
                idempotency_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        relational_backend.execute_query('''
            CREATE TABLE IF NOT EXISTS uds3_audit_log (
                audit_id TEXT PRIMARY KEY,
                saga_id TEXT NOT NULL,
                saga_name TEXT,
                trace_id TEXT,
                identity_key TEXT,
                document_id TEXT,
                step_name TEXT,
                event_type TEXT,
                status TEXT,
                duration_ms INTEGER,
                details TEXT,
                actor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        relational_backend.execute_query('''
            CREATE TABLE IF NOT EXISTS uds3_saga_metrics (
                metric_id TEXT PRIMARY KEY,
                saga_id TEXT NOT NULL,
                saga_name TEXT,
                trace_id TEXT,
                identity_key TEXT,
                step_name TEXT,
                status TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                duration_ms INTEGER,
                error_message TEXT,
                details TEXT
            )
        ''')

        # Create basic indices
        try:
            relational_backend.execute_query('CREATE INDEX IF NOT EXISTS idx_sagas_status ON uds3_sagas(status)')
            relational_backend.execute_query('CREATE INDEX IF NOT EXISTS idx_saga_events_saga_id ON uds3_saga_events(saga_id)')
            relational_backend.execute_query('CREATE INDEX IF NOT EXISTS idx_audit_trace ON uds3_audit_log(trace_id)')
        except Exception:
            # best-effort indices
            pass

    except Exception as exc:
        logger.debug('ensure_saga_schema failed: %s', exc)
