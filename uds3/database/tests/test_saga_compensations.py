import uuid
import sys
import pathlib
import pytest

# Ensure repo root is on sys.path so 'database' package imports work
# parents[2] points to workspace root (one level above the 'database' package)
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database import saga_compensations
from database.database_api_sqlite import SQLiteRelationalBackend


def test_relational_delete_handler(tmp_path):
    db_path = str(tmp_path / "comp.db")
    conf = {'database_path': db_path}
    backend = SQLiteRelationalBackend(conf)
    backend._backend_connect()

    # create a small table and insert a row
    backend.create_table('temp_items', {'id': 'TEXT PRIMARY KEY', 'value': 'TEXT'})
    item_id = str(uuid.uuid4())
    backend.insert('temp_items', {'id': item_id, 'value': 'to-delete'})

    # Sanity: row exists
    rows = backend.execute_query('SELECT id, value FROM temp_items WHERE id = ?', (item_id,))
    assert len(rows) == 1

    # Call handler via registry
    handler = saga_compensations.get('relational_delete')
    assert handler is not None

    success = handler({'table': 'temp_items', 'id': item_id}, {'relational_backend': backend})
    assert success

    rows_after = backend.execute_query('SELECT id FROM temp_items WHERE id = ?', (item_id,))
    assert len(rows_after) == 0

    # Calling the handler again should be idempotent (treat already-deleted as success)
    success_again = handler({'table': 'temp_items', 'id': item_id}, {'relational_backend': backend})
    assert success_again


def test_graph_and_vector_handlers_stub():
    # Simple stubs that expose expected method names
    class GraphStub:
        def delete_node(self, label, id_):
            return True

    class VectorStub:
        def delete_documents(self, ids):
            return True

    graph = GraphStub()
    vector = VectorStub()

    g_handler = saga_compensations.get('graph_delete_node')
    v_handler = saga_compensations.get('vector_delete_chunks')
    assert g_handler is not None
    assert v_handler is not None

    # Call handlers with expected payloads
    assert g_handler({'label': 'Doc', 'id': 'x'}, {'graph_backend': graph})
    assert v_handler({'ids': ['a', 'b']}, {'vector_backend': vector})
