#!/usr/bin/env python3
"""Debug statistics query"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend
import psycopg2.extras

# Connect
backend = PostgreSQLRelationalBackend({
    'host': '192.168.178.94',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'postgres'
})

backend.connect()

print("=" * 70)
print("  DEBUG: Statistics Query")
print("=" * 70)

# Test 1: Count
print("\nTest 1: Count")
backend.cursor.execute("SELECT COUNT(*) as count FROM review_tasks")
result = backend.cursor.fetchone()
count = result['count']
print(f"✅ Count: {count}")

# Test 2: By status
print("\nTest 2: By status")
backend.cursor.execute("""
    SELECT status, COUNT(*) as count
    FROM review_tasks
    GROUP BY status
    ORDER BY count DESC
""")
by_status = {row['status']: row['count'] for row in backend.cursor.fetchall()}
print(f"✅ By status: {by_status}")

# Test 3: Average resolution time
print("\nTest 3: Average resolution time")
backend.cursor.execute("""
    SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/3600) as avg_hours
    FROM review_tasks
    WHERE resolved_at IS NOT NULL
""")
result = backend.cursor.fetchone()
print(f"✅ Raw result: {result}")
print(f"✅ Type: {type(result)}")
print(f"✅ Keys: {result.keys() if hasattr(result, 'keys') else 'N/A'}")

if result:
    avg_hours = result['avg_hours']
    print(f"✅ avg_hours value: {avg_hours}")
    print(f"✅ avg_hours type: {type(avg_hours)}")
    print(f"✅ avg_hours is None: {avg_hours is None}")
    print(f"✅ avg_hours truthiness: {bool(avg_hours)}")
    
    if avg_hours is not None:
        avg_hours_float = float(avg_hours)
        print(f"✅ avg_hours as float: {avg_hours_float}")
    else:
        print(f"✅ avg_hours is None (no resolved tasks)")

backend.close()
print("\n" + "=" * 70)
