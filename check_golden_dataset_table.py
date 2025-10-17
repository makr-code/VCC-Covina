#!/usr/bin/env python3
"""Check if golden_dataset table exists in PostgreSQL"""

import psycopg
from psycopg.rows import dict_row

try:
    conn = psycopg.connect(
        host="192.168.178.94",
        port=5432,
        user="postgres",
        password="postgres",
        dbname="postgres",
        row_factory=dict_row
    )
    
    cur = conn.cursor()
    
    # Check for golden_dataset table
    cur.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname='public' AND tablename='golden_dataset'
    """)
    
    result = cur.fetchall()
    
    if result:
        print("✅ golden_dataset table EXISTS")
        print(f"   Table: {result}")
        
        # Get row count
        cur.execute("SELECT COUNT(*) as count FROM golden_dataset")
        count = cur.fetchone()
        print(f"   Rows: {count['count']}")
    else:
        print("❌ golden_dataset table NOT FOUND")
        print("\nAvailable tables:")
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        tables = cur.fetchall()
        for table in tables:
            print(f"   - {table['tablename']}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
