"""
Check graph_golden_dataset table schema
"""

import psycopg
import os

# Connect to PostgreSQL
try:
    conn = psycopg.connect(
        host='192.168.178.94',
        port=5432,
        user='postgres',
        password='postgres',
        dbname='postgres',
        connect_timeout=5
    )
    
    cur = conn.cursor()
    
    # Check if table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'graph_golden_dataset'
        );
    """)
    
    exists = cur.fetchone()[0]
    
    if exists:
        print("✅ Table 'graph_golden_dataset' exists")
        
        # Get column information
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'graph_golden_dataset'
            ORDER BY ordinal_position;
        """)
        
        columns = cur.fetchall()
        print(f"\nColumns ({len(columns)} total):")
        print("-" * 80)
        for col in columns:
            print(f"  {col[0]:30} {col[1]:20} {'NULL' if col[2] == 'YES' else 'NOT NULL':10} {col[3] or ''}")
        
        # Check for any data
        cur.execute("SELECT COUNT(*) FROM graph_golden_dataset;")
        count = cur.fetchone()[0]
        print(f"\n✅ Row count: {count}")
        
    else:
        print("❌ Table 'graph_golden_dataset' does NOT exist!")
        print("\nAvailable tables:")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        for table in tables:
            print(f"  - {table[0]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
