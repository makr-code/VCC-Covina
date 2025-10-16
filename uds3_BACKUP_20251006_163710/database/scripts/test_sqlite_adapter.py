#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database.database_api_sqlite import SQLiteRelationalBackend

print('Starting SQLite adapter smoke test')
backend = SQLiteRelationalBackend({'database_path': './data/test_adapter.db'})
print('connect:', backend.connect())

schema = {'id': 'TEXT PRIMARY KEY', 'name': 'TEXT', 'value': 'TEXT'}
print('create_table:', backend.create_table('test_table', schema))

print('insert -> id:', backend.insert_record('test_table', {'name': 'Alice', 'value': '42'}))
print('insert -> id:', backend.insert_record('test_table', {'name': 'Bob', 'value': '7'}))

print('select all:', backend.select('test_table'))

# update first row
rows = backend.select('test_table')
if rows:
    first_id = rows[0].get('id')
    print('update_record:', backend.update_record('test_table', first_id, {'value': '43'}))
    print('after update:', backend.select('test_table'))

# delete by id
if rows:
    fid = rows[0].get('id')
    print('delete:', backend.delete('test_table', {'id': fid}))
    print('after delete:', backend.select('test_table'))

print('tables:', backend.get_tables())
backend.disconnect()
print('Test complete')
