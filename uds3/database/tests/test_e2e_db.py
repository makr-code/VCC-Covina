import sys
import unittest
import os
import shutil
from pathlib import Path

# Ensure project root is on sys.path so 'database' package can be imported
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.database_manager import DatabaseManager

DB_PATH = os.path.abspath('./sqlite_db/e2e_test.db')

class TestE2EDatabase(unittest.TestCase):
    def setUp(self):
        # ensure clean sqlite dir
        d = os.path.dirname(DB_PATH)
        os.makedirs(d, exist_ok=True)
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

    def test_sqlite_e2e(self):
        cfg = {
            'vector': None,
            'graph': None,
            'relational': {
                'enabled': True,
                'backend': 'sqlite',
                'database_path': DB_PATH
            },
            'file': None,
            'key_value': None,
            'governance': {},
            'autostart': True
        }

        # create manager with autostart so start_all_backends runs
        mgr = DatabaseManager(cfg, autostart=True)

        # relational backend should be available
        rel = mgr.get_relational_backend()
        self.assertIsNotNone(rel)

        # Create table
        schema = {'id': 'TEXT PRIMARY KEY', 'data': 'TEXT'}
        ok = rel.create_table('e2e_table', schema)
        self.assertTrue(ok)

        # Insert a record
        rec = {'id': 'r1', 'data': 'hello'}
        inserted = rel.insert_record('e2e_table', rec)
        self.assertIsNotNone(inserted)

        # Query back
        rows = rel.execute_query('SELECT * FROM e2e_table')
        self.assertTrue(any(r.get('id') == 'r1' for r in rows))

    def tearDown(self):
        try:
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
        except Exception:
            pass

if __name__ == '__main__':
    unittest.main()
