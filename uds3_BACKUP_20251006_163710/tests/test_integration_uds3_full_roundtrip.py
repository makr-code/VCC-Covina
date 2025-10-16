import sys
import pathlib
import os
import pytest
from typing import Dict, Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uds3_core import UnifiedDatabaseStrategy
from database.database_manager import DatabaseManager
# Ensure tests/ directory is importable for helper modules
TESTS_DIR = str(pathlib.Path(__file__).resolve().parents[0])
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)
from uds3_plan_db_utils import apply_relational_operations_from_plan


def test_uds3_to_sqlite_roundtrip(tmp_path):
    db_file = tmp_path / "uds3_roundtrip.db"
    backend_cfg = {
        'relational': {
            'enabled': True,
            'backend': 'sqlite',
            'database_path': str(db_file),
        }
    }

    mgr = DatabaseManager(backend_cfg, autostart=False)
    # start relational backend
    res = mgr.start_all_backends(['relational'], timeout_per_backend=5)
    assert res.get('relational', False) is True
    rel = mgr.get_relational_backend()
    assert rel is not None
    assert rel.is_available()

    # Build a UDS3 plan
    uds = UnifiedDatabaseStrategy()
    content = 'Das ist ein Testdokument. Enthält mehrere Wörter zum Test.'
    chunks = ['Das ist ein', 'Testdokument.']
    plan = uds.create_document_operation('testfile.pdf', content, chunks, title='UDS3 Test')

    assert 'databases' in plan and 'relational' in plan['databases']
    ops = plan['databases']['relational'].get('operations', [])
    assert isinstance(ops, list) and len(ops) >= 1

    # Apply relational plan using helper that creates compatible tables and inserts
    apply_relational_operations_from_plan(rel, plan['databases']['relational'], plan['document_id'])

    # Read back document metadata by document_id
    rows = rel.select('documents_metadata', {'document_id': plan['document_id']})
    assert isinstance(rows, list) and len(rows) == 1
    r = rows[0]
    assert r.get('title') == 'UDS3 Test'

    mgr.disconnect_all()
    if os.path.exists(str(db_file)):
        try:
            os.remove(str(db_file))
        except Exception:
            pass
