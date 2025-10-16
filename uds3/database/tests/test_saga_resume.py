import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database.saga_orchestrator import SagaOrchestrator
from database.database_api_sqlite import SQLiteRelationalBackend


def make_orch(tmp_path):
    db_path = str(tmp_path / 'resume.db')
    conf = {'database_path': db_path}
    rel = SQLiteRelationalBackend(conf)
    rel._backend_connect()

    # ensure idempotency column exists for tests
    from database.db_migrations import ensure_idempotency_column
    ensure_idempotency_column(rel)

    from database.db_migrations import ensure_saga_schema
    ensure_saga_schema(rel)

    # make sure documents table exists
    rel.create_table('documents', {'id': 'TEXT PRIMARY KEY', 'content': 'TEXT'})

    from database.database_manager import DatabaseManager
    mgr = DatabaseManager({'relational': {'enabled': False}})
    mgr.relational_backend = rel
    orch = SagaOrchestrator(manager=mgr)
    return orch, rel


def test_resume_saga_executes_remaining(tmp_path):
    orch, rel = make_orch(tmp_path)

    steps = [
        {'step_id': 's1', 'backend': 'relational', 'operation': 'insert', 'payload': {'table': 'documents', 'record': {'id': 'r1', 'content': 'a'}, 'compensation': 'relational_delete'}},
        {'step_id': 's2', 'backend': 'relational', 'operation': 'insert', 'payload': {'table': 'documents', 'record': {'id': 'r2', 'content': 'b'}, 'compensation': 'relational_delete'}},
        {'step_id': 's3', 'backend': 'relational', 'operation': 'insert', 'payload': {'table': 'documents', 'record': {'id': 'r3', 'content': 'c'}, 'compensation': 'relational_delete'}},
    ]

    saga_id = orch.create_saga('resume_test', steps)

    # simulate first step succeeded
    orch.crud.write_saga_event(saga_id, 's1', 'SUCCESS', steps[0]['payload'])

    # second step pending (pretend started)
    orch.crud.write_saga_event(saga_id, 's2', 'PENDING', steps[1]['payload'])

    # now resume - should execute s2 and s3
    res = orch.resume_saga(saga_id)
    assert res.get('success')

    # s2 and s3 should have been inserted
    rows = rel.execute_query('SELECT id FROM documents WHERE id IN (?, ?, ?)', ('r1', 'r2', 'r3'))
    ids = {r['id'] for r in rows}
    assert 'r2' in ids and 'r3' in ids
