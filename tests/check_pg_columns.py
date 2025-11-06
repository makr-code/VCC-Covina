import psycopg2

conn = psycopg2.connect(
    host='192.168.178.94',
    port=5432,
    user='postgres',
    password='postgres',
    database='postgres'
)

cursor = conn.cursor()
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name='documents' 
    ORDER BY ordinal_position
""")

print("PostgreSQL 'documents' table columns:")
print("-" * 40)
for col_name, col_type in cursor.fetchall():
    print(f"{col_name:20s} {col_type}")

cursor.close()
conn.close()
