#!/usr/bin/env python3
"""Run SAGA migrations against a local SQLite backend for quick verification.

This script uses the new `SQLiteRelationalBackend` implementation and calls the
helpers in `db_migrations.py`. It's safe, idempotent and intended for dev use.
"""
import logging
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database.database_api_sqlite import SQLiteRelationalBackend
from database.db_migrations import ensure_saga_schema, ensure_idempotency_column

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('saga_migrations_sqlite_local')


def main():
    cfg = {'database_path': './data/test_relational.db'}
    backend = SQLiteRelationalBackend(cfg)
    if not backend.connect():
        logger.error('Could not connect to local SQLite backend')
        return 2

    logger.info('Ensuring saga schema (SQLite local)')
    ensure_saga_schema(backend)
    ensure_idempotency_column(backend)

    logger.info('Done. Tables present: %s', backend.get_tables())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
