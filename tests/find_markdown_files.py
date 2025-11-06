import psycopg2

conn = psycopg2.connect(
    host='192.168.178.94',
    port=5432,
    user='postgres',
    password='postgres',
    database='postgres'
)

cursor = conn.cursor()
cursor.execute("SELECT file_path FROM documents WHERE file_path LIKE 'Y:%.md' LIMIT 5")

print("Sample markdown files in PostgreSQL:")
for row in cursor.fetchall():
    print(f"  {row[0]}")

cursor.close()
conn.close()
