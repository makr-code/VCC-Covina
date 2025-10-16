import os
import sys
import pathlib
import pytest
from typing import Dict

# Ensure project root is on sys.path so `database` package can be imported when
# pytest's working directory or import roots differ. This mirrors how the
# application behaves when installed or run from project root.
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.database_manager import DatabaseManager


def test_real_sqlite_roundtrip(tmp_path):
    db_file = tmp_path / "test_udstest.db"
    backend_cfg = {
        'relational': {
            'enabled': True,
            # force using sqlite backend (default)
            'backend': 'sqlite',
            'database_path': str(db_file),
        }
    }

    mgr = DatabaseManager(backend_cfg, autostart=False)

    # Start relational backend only
    results = mgr.start_all_backends(['relational'], timeout_per_backend=5)
    assert results.get('relational', False) is True

    rel = mgr.get_relational_backend()
    assert rel is not None
    # Ensure connectivity
    assert rel.is_available()

    # Create a table with TEXT primary key so insert_record's UUID id works
    # (default create_database_if_missing uses INTEGER AUTOINCREMENT which conflicts)
    rel.create_table('test_table', {'id': 'TEXT PRIMARY KEY', 'data': 'TEXT'})

    # Insert a record (only use columns that are present in default schema)
    rec_id = rel.insert_record('test_table', {'data': 'hello'})
    assert rec_id is not None

    rows = rel.select('test_table', {'id': rec_id})
    assert isinstance(rows, list) and len(rows) == 1
    assert rows[0].get('data') == 'hello'

    # Update the record
    upd_ok = rel.update_record('test_table', rec_id, {'data': 'world'})
    assert upd_ok
    rows2 = rel.select('test_table', {'id': rec_id})
    assert rows2[0].get('data') == 'world'

    # Delete record
    del_ok = rel.delete('test_table', {'id': rec_id})
    assert del_ok
    rows3 = rel.select('test_table', {'id': rec_id})
    assert rows3 == []

    # Clean up
    mgr.disconnect_all()
    if os.path.exists(str(db_file)):
        try:
            os.remove(str(db_file))
        except Exception:
            pass
