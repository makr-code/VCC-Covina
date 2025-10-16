import json
import uuid
import sys
import pathlib
import pytest

# Ensure repo root on path
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database.saga_orchestrator import SagaOrchestrator
from database.database_api_sqlite import SQLiteRelationalBackend
from database import saga_compensations


def make_orchestrator(tmp_path):
    db_path = str(tmp_path / 'orch.db')
    conf = {'database_path': db_path}
    rel = SQLiteRelationalBackend(conf)
    rel._backend_connect()

    # ensure idempotency column exists for tests
    from database.db_migrations import ensure_idempotency_column
    ensure_idempotency_column(rel)
    from database.db_migrations import ensure_saga_schema
    ensure_saga_schema(rel)

    # create table for documents
    rel.create_table('documents', {'id': 'TEXT PRIMARY KEY', 'content': 'TEXT'})

    # instantiate orchestrator with a manager that we temporarily adapt
    from database.database_manager import DatabaseManager
    mgr = DatabaseManager({'relational': {'enabled': False}})
    mgr.relational_backend = rel
    orch = SagaOrchestrator(manager=mgr)
    return orch, rel


def test_orchestrator_happy_path(tmp_path):
    orch, rel = make_orchestrator(tmp_path)

    # Define steps: insert a relational row
    steps = [
        {
            'step_id': 'insert_doc',
            'backend': 'relational',
            'operation': 'insert',
            'payload': {'table': 'documents', 'record': {'id': 'd1', 'content': 'hello'}, 'compensation': 'relational_delete'}
        }
    ]

    saga_id = orch.create_saga('create_doc', steps)
    res = orch.execute_saga(saga_id)
    assert res.get('success')

    # check document exists
    rows = rel.execute_query('SELECT id, content FROM documents WHERE id = ?', ('d1',))
    assert len(rows) == 1


def test_orchestrator_failure_triggers_compensation(tmp_path):
    orch, rel = make_orchestrator(tmp_path)

    # Step 1: insert docs (will succeed)
    # Step 2: unsupported operation -> will fail and trigger compensation
    steps = [
        {
            'step_id': 'insert_doc',
            'backend': 'relational',
            'operation': 'insert',
            'payload': {'table': 'documents', 'record': {'id': 'd2', 'content': 'to be removed'}, 'compensation': 'relational_delete'}
        },
        {
            'step_id': 'bad_step',
            'backend': 'vector',
            'operation': 'unsupported_op',
            'payload': {'some': 'data'}
        }
    ]

    saga_id = orch.create_saga('create_doc_fail', steps)
    res = orch.execute_saga(saga_id, max_retries=1)
    assert not res.get('success')

    # Check that the first document was compensated (deleted)
    rows = rel.execute_query('SELECT id FROM documents WHERE id = ?', ('d2',))
    assert len(rows) == 0
