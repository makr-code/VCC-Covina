#!/usr/bin/env python3
"""Check if test_doc files are in PostgreSQL"""

import psycopg2

try:
    conn = psycopg2.connect(
        host="192.168.178.94",
        port=5432,
        dbname="postgres",
        user="postgres",
        password="postgres"
    )
    
    cur = conn.cursor()
    
    # Count test_doc files
    cur.execute("SELECT COUNT(*) FROM documents WHERE file_path LIKE '%test_doc%'")
    count = cur.fetchone()[0]
    print(f"Test docs in PostgreSQL: {count}")
    
    # Show recent test_doc entries
    if count > 0:
        cur.execute("""
            SELECT document_id, file_path, classification, created_at 
            FROM documents 
            WHERE file_path LIKE '%test_doc%'
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        print("\nRecent test documents:")
        for row in cur.fetchall():
            print(f"  {row[0]} - {row[2]} - {row[1]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
