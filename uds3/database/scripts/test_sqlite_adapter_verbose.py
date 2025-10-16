#!/usr/bin/env python3
import sys
import traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    print('Starting verbose SQLite adapter smoke test')
    from database.database_api_sqlite import SQLiteRelationalBackend
    backend = SQLiteRelationalBackend({'database_path': './data/test_adapter_verbose.db'})
    print('instantiated backend')
    ok = backend.connect()
    print('connect returned:', ok)
    print('create_table result:', backend.create_table('test_table_verbose', {'id':'TEXT PRIMARY KEY','name':'TEXT'}))
    print('insert id:', backend.insert_record('test_table_verbose', {'name':'Alice'}))
    print('select:', backend.select('test_table_verbose'))
    backend.disconnect()
    print('Verbose test complete')
except Exception as e:
    print('Exception during verbose test:')
    traceback.print_exc()
    raise
