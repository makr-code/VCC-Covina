"""
Test PostgreSQL documents table schema
"""
from database.database_api_postgresql import PostgreSQLRelationalBackend
import os

config = {
    'host': os.getenv('POSTGRES_HOST', '192.168.178.94'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DATABASE', 'postgres'),
    'username': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
}

backend = PostgreSQLRelationalBackend(config)
backend.connect()

# Get table schema
backend.cursor.execute("""
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name='documents' 
ORDER BY ordinal_position
""")

print("\n=== documents Table Schema ===")
for row in backend.cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check if content column exists
backend.cursor.execute("""
SELECT column_name 
FROM information_schema.columns 
WHERE table_name='documents' AND column_name='content'
""")

has_content = backend.cursor.fetchone()
print(f"\n=== Has 'content' column: {bool(has_content)} ===")

# Get document count
backend.cursor.execute("SELECT COUNT(*) FROM documents")
count = backend.cursor.fetchone()[0]
print(f"\n=== Total documents: {count} ===")

backend.conn.close()
