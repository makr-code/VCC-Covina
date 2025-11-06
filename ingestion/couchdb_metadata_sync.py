"""
Quick CouchDB Sync - Metadata Only (No File Content Reading)
Synchronizes PostgreSQL metadata to CouchDB without reading actual files.
Much faster for network shares.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import psycopg2
from datetime import datetime

# Configuration
PG_CONFIG = {
    'host': '192.168.178.94',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'postgres'
}

COUCH_CONFIG = {
    'host': '192.168.178.94',
    'port': 32770,
    'user': 'couchdb',
    'password': 'couchdb',
    'database': 'covina'
}

BATCH_SIZE = 500  # Larger batches (no file reading)

print("=" * 80)
print("COUCHDB METADATA SYNC (Fast Mode - No File Content)")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Connect to PostgreSQL
print("1. Connecting to PostgreSQL...")
conn = psycopg2.connect(**PG_CONFIG)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM documents")
total_docs = cursor.fetchone()[0]
print(f"   Total documents: {total_docs:,}\n")

# Setup CouchDB
print("2. Setting up CouchDB...")
couch_url = f"http://{COUCH_CONFIG['host']}:{COUCH_CONFIG['port']}"
db_url = f"{couch_url}/{COUCH_CONFIG['database']}"
auth = (COUCH_CONFIG['user'], COUCH_CONFIG['password'])

# Create database if needed
response = requests.put(db_url, auth=auth)
if response.status_code == 201:
    print(f"   ✅ Database '{COUCH_CONFIG['database']}' created\n")
elif response.status_code == 412:
    print(f"   ✅ Database '{COUCH_CONFIG['database']}' exists\n")
else:
    print(f"   ⚠️  Status: {response.status_code}\n")

# Bulk upload
print("3. Uploading documents (metadata only)...")
print(f"   Batch size: {BATCH_SIZE}\n")

offset = 0
uploaded = 0
updated = 0
errors = 0

while offset < total_docs:
    # Fetch batch
    cursor.execute("""
        SELECT document_id, file_path, classification, 
               content_length, legal_terms_count, created_at,
               quality_score, processing_status, company_metadata
        FROM documents
        ORDER BY file_path
        LIMIT %s OFFSET %s
    """, (BATCH_SIZE, offset))
    
    rows = cursor.fetchall()
    if not rows:
        break
    
    # Prepare bulk docs
    bulk_docs = []
    
    for doc_id, file_path, classification, content_length, legal_terms, created_at, quality, status, company_meta in rows:
        doc = {
            '_id': doc_id,
            'file_path': file_path,
            'classification': classification,
            'content_length': content_length,
            'legal_terms_count': legal_terms,
            'created_at': created_at,
            'quality_score': quality,
            'processing_status': status,
            'company_metadata': company_meta if company_meta else {},
            'uploaded_at': datetime.now().isoformat(),
            'source': 'postgresql_metadata_sync',
            'note': 'Metadata only - file content not included'
        }
        bulk_docs.append(doc)
    
    # Bulk upload to CouchDB
    bulk_url = f"{db_url}/_bulk_docs"
    response = requests.post(
        bulk_url,
        json={'docs': bulk_docs},
        auth=auth
    )
    
    if response.status_code == 201:
        # Check results
        results = response.json()
        for result in results:
            if result.get('ok'):
                if result.get('rev', '').startswith('1-'):
                    uploaded += 1
                else:
                    updated += 1
            else:
                errors += 1
    else:
        errors += len(bulk_docs)
        print(f"   ⚠️  Batch upload failed: HTTP {response.status_code}")
    
    offset += BATCH_SIZE
    
    # Progress
    progress_pct = min(100, (offset / total_docs) * 100)
    print(f"   Progress: {offset:,}/{total_docs:,} ({progress_pct:.1f}%) | "
          f"New: {uploaded:,} | Updated: {updated:,} | Errors: {errors}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("SYNC COMPLETE")
print("=" * 80)
print(f"Documents uploaded: {uploaded:,}")
print(f"Documents updated: {updated:,}")
print(f"Errors: {errors}")
print("\n💡 Note: Only metadata synced (file content NOT included)")
print("💡 For full content, files must be read from Y:\\data\\ (slow)")
print("=" * 80)
