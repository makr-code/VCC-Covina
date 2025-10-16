import importlib
import sys
import os
from pathlib import Path
import pytest

# Ensure repository package root is on sys.path for package imports
# parents[2] -> project root (one level above 'database' folder)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_kge_queue_enqueue_and_fetch(monkeypatch, tmp_path):
    # Force sqlite path for isolation and set env BEFORE import
    db_path = tmp_path / "test_kge.sqlite"
    monkeypatch.setenv('VERITAS_SQLITE_PATH', str(db_path))

    # Import package module after env set
    import database.database_api as dbapi
    importlib.reload(dbapi)

    # Ensure queue empty
    assert dbapi.kge_get_queue_size() == 0

    task_id = 'task-1'
    task_type = 'ingest'
    params = {'foo': 'bar'}

    # Enqueue task
    returned = dbapi.kge_enqueue_task(task_id, task_type, params, document_id=None, priority=5)
    assert returned == task_id

    # Queue size now 1
    assert dbapi.kge_get_queue_size() == 1

    # Fetch next pending task
    row = dbapi.kge_fetch_next_pending_task()
    assert row is not None
    assert row['task_id'] == task_id
    assert row['task_type'] == task_type

    # Set status
    dbapi.kge_set_task_status(task_id, 'running')
    # Mark as done and store result
    result_id = 'res-1'
    dbapi.kge_store_result(task_id, result_id, True, 0.1, 1, 0, None, {'meta': 'ok'})

    # Retrieve result
    res = dbapi.kge_get_task_result(task_id)
    assert res is not None
    assert res['task']['task_id'] == task_id
    assert res['result']['id'] == result_id


def test_enrichment_log(monkeypatch, tmp_path):
    db_path = tmp_path / "test_kge2.sqlite"
    monkeypatch.setenv('VERITAS_SQLITE_PATH', str(db_path))

    import database.database_api as dbapi
    importlib.reload(dbapi)

    # trigger init via reload
    dbapi.enrichment_log('ingest', 'started', {'x': 1}, triggered_by='tester')
    # simple check: one row present
    conn = dbapi._kge_get_conn()
    cur = conn.execute("SELECT COUNT(1) as c FROM enrichment_logs").fetchone()
    assert cur['c'] >= 1
