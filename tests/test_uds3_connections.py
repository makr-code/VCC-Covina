#!/usr/bin/env python3
"""
Test UDS3 Database Connections

Tests all 4 UDS3 database backends:
- PostgreSQL (Relational)
- CouchDB (Document)
- ChromaDB (Vector)
- Neo4j (Graph)
"""

import sys
import traceback

print("=" * 60)
print("UDS3 Database Connection Test")
print("=" * 60)
print()

# Test 1: PostgreSQL
print("1️⃣  Testing PostgreSQL (Relational)...")
try:
    from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend
    
    pg_config = {
        'host': '192.168.178.94',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',
        'database': 'postgres',
        'schema': 'public'
    }
    
    pg = PostgreSQLRelationalBackend(pg_config)
    connected = pg.connect()
    
    if connected:
        # Test query
        count = pg.get_document_count()
        print(f"   ✅ PostgreSQL: Connected ({count} documents)")
    else:
        print(f"   ❌ PostgreSQL: Connection failed")
        
except Exception as e:
    print(f"   ❌ PostgreSQL: Error - {e}")
    traceback.print_exc()

print()

# Test 2: CouchDB
print("2️⃣  Testing CouchDB (Document)...")
try:
    from uds3.database.database_api_couchdb import CouchDBAdapter
    
    couch_config = {
        "host": "192.168.178.94",
        "port": 32931,
        "database": "covina_documents",
        "username": "couchdb",
        "password": "couchdb"
    }
    
    couch = CouchDBAdapter(couch_config)
    
    # Test connection by getting database info
    try:
        info = couch.get_database_info()
        doc_count = info.get('doc_count', 0)
        print(f"   ✅ CouchDB: Connected ({doc_count} documents)")
    except:
        print(f"   ❌ CouchDB: Connection failed")
        
except Exception as e:
    print(f"   ❌ CouchDB: Error - {e}")
    traceback.print_exc()

print()

# Test 3: ChromaDB
print("3️⃣  Testing ChromaDB (Vector)...")
try:
    from uds3.database.database_api_chromadb_remote import ChromaRemoteVectorBackend
    
    chroma_config = {
        "collection": "covina_documents",
        "remote": {
            "host": "192.168.178.94",
            "port": 8000,
            "protocol": "http"
        },
        "tenant": "default_tenant",
        "database": "default_database"
    }
    
    chroma = ChromaRemoteVectorBackend(chroma_config)
    connected = chroma.connect()
    
    if connected:
        # Check if available
        if chroma.is_available():
            # Try to get collection info
            try:
                # ChromaDB doesn't have a direct count method, but we can check availability
                print(f"   ✅ ChromaDB: Connected (collection: {chroma.collection_name})")
            except Exception as e:
                print(f"   ⚠️ ChromaDB: Connected but collection access failed - {e}")
        else:
            print(f"   ❌ ChromaDB: Not available")
    else:
        print(f"   ❌ ChromaDB: Connection failed")
        
except Exception as e:
    print(f"   ❌ ChromaDB: Error - {e}")
    traceback.print_exc()

print()

# Test 4: Neo4j
print("4️⃣  Testing Neo4j (Graph)...")
try:
    from uds3.uds3_relations_core import UDS3RelationsCore
    
    neo4j = UDS3RelationsCore(
        neo4j_uri="neo4j://192.168.178.94:7687",
        neo4j_auth=("neo4j", "v3f3b1d7")
    )
    
    # Test by counting nodes
    try:
        with neo4j.neo4j_session() as session:
            result = session.run("MATCH (n:Document) RETURN count(n) as count")
            count = result.single()['count'] if result else 0
            print(f"   ✅ Neo4j: Connected ({count} document nodes)")
    except Exception as e:
        print(f"   ❌ Neo4j: Query failed - {e}")
        
except Exception as e:
    print(f"   ❌ Neo4j: Error - {e}")
    traceback.print_exc()

print()
print("=" * 60)
print("Test Complete")
print("=" * 60)
