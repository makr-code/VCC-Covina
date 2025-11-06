"""
Data Inventory Analysis - All 4 Databases
Checks current state of PostgreSQL, CouchDB, Neo4j, ChromaDB.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from uds3.core.relations import UDS3RelationsCore
import psycopg2
import requests
import os

print("=" * 70)
print("COVINA DATA INVENTORY - ALL DATABASES")
print("=" * 70)

# ===== 1. PostgreSQL =====
print("\n1. POSTGRESQL (Relational Master)")
print("-" * 70)

try:
    conn = psycopg2.connect(
        host="192.168.178.94",
        port=5432,
        user="postgres",
        password="postgres",
        database="postgres"
    )
    cursor = conn.cursor()
    
    # Document count
    cursor.execute("SELECT COUNT(*) FROM documents")
    pg_docs = cursor.fetchone()[0]
    print(f"   Documents: {pg_docs:,}")
    
    # Sample data
    cursor.execute("SELECT file_path FROM documents LIMIT 1")
    sample = cursor.fetchone()
    if sample:
        print(f"   Sample: {sample[0][:80]}...")
    
    cursor.close()
    conn.close()
    print("   Status: ✅ Connected")
except Exception as e:
    print(f"   Status: ❌ Error: {e}")

# ===== 2. CouchDB =====
print("\n2. COUCHDB (Document Store)")
print("-" * 70)

try:
    # Correct port from UDS3 config_local.py
    response = requests.get("http://192.168.178.94:32770/")
    if response.status_code == 200:
        print(f"   Server: ✅ CouchDB {response.json().get('version', 'unknown')}")
    
    # Check for covina database
    response = requests.get("http://192.168.178.94:32770/covina")
    if response.status_code == 200:
        data = response.json()
        doc_count = data.get('doc_count', 0)
        print(f"   Database 'covina': ✅ {doc_count:,} documents")
    elif response.status_code == 404:
        print("   Database 'covina': ⚠️ Does not exist (will be created)")
    else:
        print(f"   Database 'covina': ❌ Status {response.status_code}")
    
    # Check all databases
    response = requests.get("http://192.168.178.94:32770/_all_dbs")
    if response.status_code == 200:
        dbs = response.json()
        print(f"   Available DBs: {', '.join([db for db in dbs if not db.startswith('_')])}")
    
except Exception as e:
    print(f"   Status: ❌ Error: {e}")

# ===== 3. Neo4j =====
print("\n3. NEO4J (Knowledge Graph)")
print("-" * 70)

try:
    neo4j = UDS3RelationsCore(
        neo4j_uri='bolt://192.168.178.94:7687',
        neo4j_auth=('neo4j', 'v3f3b1d7')
    )
    
    if neo4j.neo4j_enabled:
        with neo4j.neo4j_session() as session:
            # Total nodes
            result = session.run("MATCH (n) RETURN count(n) as total")
            total_nodes = result.single()['total']
            print(f"   Total Nodes: {total_nodes:,}")
            
            # Node breakdown
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS count
                ORDER BY count DESC
                LIMIT 5
            """)
            for record in result:
                print(f"     - {record['label']}: {record['count']:,}")
            
            # Total relations
            result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
            total_rels = result.single()['total']
            print(f"   Total Relations: {total_rels:,}")
            
            # NLP-specific data
            result = session.run("MATCH (c:LegalConcept) RETURN count(c) as count")
            nlp_concepts = result.single()['count']
            
            result = session.run("MATCH ()-[r:MENTIONS]->() RETURN count(r) as count")
            nlp_mentions = result.single()['count']
            
            print(f"   NLP Data:")
            print(f"     - LegalConcept Nodes: {nlp_concepts:,}")
            print(f"     - MENTIONS Relations: {nlp_mentions:,}")
        
        print("   Status: ✅ Connected")
    else:
        print("   Status: ❌ Not connected")
except Exception as e:
    print(f"   Status: ❌ Error: {e}")

# ===== 4. ChromaDB =====
print("\n4. CHROMADB (Vector Store)")
print("-" * 70)

try:
    # ChromaDB now uses v2 API
    response = requests.get("http://192.168.178.94:8000/api/v2/heartbeat")
    if response.status_code == 200:
        heartbeat = response.json()
        print(f"   Server: ✅ ChromaDB Running (v2 API)")
        print(f"   Heartbeat: {heartbeat.get('nanosecond heartbeat', 'N/A')}")
        
        # Note: v2 API has different endpoints for collections
        # For detailed info, use ChromaDB Python client
        print("   💡 For collection details, use ChromaDB Python client")
        print("   Status: ✅ Connected")
    else:
        print(f"   Status: ❌ HTTP {response.status_code}")
except Exception as e:
    print(f"   Status: ❌ Error: {e}")

# ===== Summary =====
print("\n" + "=" * 70)
print("ANALYSIS SUMMARY")
print("=" * 70)

print("\nData Sources Identified:")
print("  - PostgreSQL: Master relational data (168k+ documents)")
print("  - Neo4j: Knowledge graph with NLP entities (144k+ docs)")
print("  - ChromaDB: Vector embeddings (needs verification)")
print("  - CouchDB: Full document storage (needs population)")

print("\nNext Steps:")
print("  1. Create CouchDB 'covina' database if missing")
print("  2. Sync PostgreSQL → CouchDB (full documents)")
print("  3. Run full NLP batch (435 → 3,618 files)")
print("  4. Persist NLP → Neo4j (760k entities expected)")
print("  5. Verify ChromaDB embeddings coverage")
