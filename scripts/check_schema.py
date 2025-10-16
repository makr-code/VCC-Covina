#!/usr/bin/env python3
"""Check documents table schema"""
from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend

backend = PostgreSQLRelationalBackend({
    'host': '192.168.178.94',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'postgres'
})

backend.connect()

backend.cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name='documents' 
    ORDER BY ordinal_position
""")

print("documents table columns:")
print("-" * 50)
for row in backend.cursor.fetchall():
    print(f"{row['column_name']:30} {row['data_type']}")
