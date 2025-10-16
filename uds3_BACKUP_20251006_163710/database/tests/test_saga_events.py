import json
import os
import uuid
import sys
import pathlib

import pytest

# Ensure repo root is on path so we can import the package-style modules
# parents[2] points to the folder that contains the `database` package
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database.saga_crud import SagaDatabaseCRUD
from database.database_manager import DatabaseManager
from database import config


def test_write_saga_event_creates_rows(tmp_path):
    # Create a local SQLite relational backend on a temp path to avoid network ops
    from database.database_api_sqlite import SQLiteRelationalBackend

    db_path = str(tmp_path / "test_relational.db")
    sqlite_conf = {'database_path': db_path}
    sqlite_backend = SQLiteRelationalBackend(sqlite_conf)
    try:
        sqlite_backend._backend_connect()
    except Exception as exc:
        import traceback

        pytest.fail(f"SQLite backend.connect failed: {exc}\n{traceback.format_exc()}")

    # Instantiate DatabaseManager minimally and set relational backend directly
    dbm = DatabaseManager({'relational': {'enabled': False}})
    dbm.relational_backend = sqlite_backend
    crud = SagaDatabaseCRUD(manager=dbm)

    saga_id = str(uuid.uuid4())
    step_name = 'create_document'
    payload = {'document_id': 'doc-123', 'meta': {'user': 'tester'}}

    # Write PENDING event
    try:
        crud.write_saga_event(saga_id, step_name, 'PENDING', payload)
    except Exception as exc:
        import traceback

        pytest.fail(f"write_saga_event PENDING failed: {exc}\n{traceback.format_exc()}")

    # Now write SUCCESS event (should also create an audit row)
    try:
        crud.write_saga_event(saga_id, step_name, 'SUCCESS', payload)
    except Exception as exc:
        import traceback

        pytest.fail(f"write_saga_event SUCCESS failed: {exc}\n{traceback.format_exc()}")

    # Query relational sqlite directly via DatabaseManager
    rel = dbm.relational_backend
    assert rel is not None

    try:
        events = rel.execute_query("SELECT saga_id, step_name, status, payload FROM uds3_saga_events WHERE saga_id = ?", (saga_id,))
    except Exception as exc:
        import traceback

        pytest.fail(f"Query uds3_saga_events failed: {exc}\n{traceback.format_exc()}")
    assert len(events) >= 2

    statuses = [r['status'] for r in events]
    assert 'PENDING' in statuses
    assert 'SUCCESS' in statuses

    try:
        audits = rel.execute_query("SELECT saga_id, step_name, status, details FROM uds3_audit_log WHERE saga_id = ?", (saga_id,))
    except Exception as exc:
        import traceback

        pytest.fail(f"Query uds3_audit_log failed: {exc}\n{traceback.format_exc()}")
    # There should be at least one audit for SUCCESS
    assert any(a['status'] == 'SUCCESS' for a in audits)
