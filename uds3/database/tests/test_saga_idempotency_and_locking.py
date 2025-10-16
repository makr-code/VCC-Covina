import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database.saga_orchestrator import SagaOrchestrator
from database.database_api_sqlite import SQLiteRelationalBackend


def make_orch(tmp_path):
    db_path = str(tmp_path / 'idemp.db')
    conf = {'database_path': db_path}
    rel = SQLiteRelationalBackend(conf)
    rel._backend_connect()

    # ensure idempotency column exists for tests
    from database.db_migrations import ensure_idempotency_column
    ensure_idempotency_column(rel)

    from database.db_migrations import ensure_saga_schema
    ensure_saga_schema(rel)

    # ensure documents table exists
    rel.create_table('documents', {'id': 'TEXT PRIMARY KEY', 'content': 'TEXT'})

    from database.database_manager import DatabaseManager
    mgr = DatabaseManager({'relational': {'enabled': False}})
    mgr.relational_backend = rel
    orch = SagaOrchestrator(manager=mgr)
    return orch, rel


def test_idempotency_skips_duplicate(tmp_path):
    orch, rel = make_orch(tmp_path)

    steps = [
        {'step_id': 's1', 'backend': 'relational', 'operation': 'insert', 'idempotency_key': 'key1', 'payload': {'table': 'documents', 'record': {'id': 'ix1', 'content': 'x'}, 'idempotency_key': 'key1', 'compensation': 'relational_delete'}}
    ]

    saga_id = orch.create_saga('idemp_test', steps)
    res1 = orch.execute_saga(saga_id)
    assert res1.get('success')

    # Running again should detect idempotency and skip (no duplicate insert)
    res2 = orch.execute_saga(saga_id)
    assert res2.get('success')

    rows = rel.execute_query('SELECT id FROM documents WHERE id = ?', ('ix1',))
    assert len(rows) == 1


def test_acquire_lock_returns_tuple_for_sqlite(tmp_path):
    orch, rel = make_orch(tmp_path)
    # call private method to acquire lock
    lock = orch._acquire_lock('lock_test')
    # for sqlite fallback, we expect a tuple like ('sqlite', None, backend)
    assert lock is not None
    assert isinstance(lock, tuple) and lock[0] in ('sqlite', 'pg')
    orch._release_lock(lock)
