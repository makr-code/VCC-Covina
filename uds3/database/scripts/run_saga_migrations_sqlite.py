#!/usr/bin/env python3
"""Run saga migrations against a local SQLite file for testing.

This is a safe, non-destructive way to verify the idempotent migration helpers
in `db_migrations.py` without touching remote Postgres.
"""
import logging
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]  # project root (parent of 'database' package)
sys.path.insert(0, str(ROOT))

from database.database_api_sqlite import SQLiteRelationalBackend
from database.db_migrations import ensure_saga_schema, ensure_idempotency_column

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('saga_migrations_sqlite')

DB_PATH = str(Path(ROOT) / 'tmp' / 'saga_sqlite.db')
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

conf = {
    'database_path': DB_PATH
}

logger.info('Creating SQLite backend at %s', DB_PATH)
backend = SQLiteRelationalBackend(conf)
if not backend._backend_connect():
    logger.error('Could not connect to local SQLite DB')
    raise SystemExit(1)

logger.info('Ensuring saga schema...')
ensure_saga_schema(backend)
logger.info('Ensuring idempotency column...')
ensure_idempotency_column(backend)
logger.info('Migrations completed on local SQLite: %s', DB_PATH)

# Quick verification: list tables
try:
    rows = backend.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
    logger.info('Tables in SQLite DB: %s', [r.get('name') for r in rows])
except Exception:
    pass

backend.disconnect()

if __name__ == '__main__':
    raise SystemExit(0)
