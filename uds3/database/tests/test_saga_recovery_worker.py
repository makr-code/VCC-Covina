import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database.saga_recovery_worker import SagaRecoveryWorker
from database.database_api_sqlite import SQLiteRelationalBackend


def make_worker(tmp_path):
    db_path = str(tmp_path / 'worker.db')
    conf = {'database_path': db_path}
    rel = SQLiteRelationalBackend(conf)
    rel._backend_connect()

    # ensure idempotency column exists for tests
    from database.db_migrations import ensure_idempotency_column
    ensure_idempotency_column(rel)
    from database.db_migrations import ensure_saga_schema
    ensure_saga_schema(rel)

    from database.database_manager import DatabaseManager
    mgr = DatabaseManager({'relational': {'enabled': False}})
    mgr.relational_backend = rel
    worker = SagaRecoveryWorker(manager=mgr)
    return worker, rel


def test_recovery_worker_runs_and_resumes(tmp_path):
    worker, rel = make_worker(tmp_path)

    # create a saga directly in table (simulate create_saga)
    saga_id = 'saga-worker-1'
    rel.execute_query('INSERT INTO uds3_sagas (saga_id, name, status, context) VALUES (?, ?, ?, ?)', (saga_id, 'wtest', 'created', '{"steps": []}'))

    res = worker.run_once()
    # No steps -> resume returns nothing but should have attempted and returned a dict entry
    assert saga_id in res
