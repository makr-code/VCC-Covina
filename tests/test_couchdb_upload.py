"""Quick test: Upload 10 documents to CouchDB"""
import sys
sys.path.insert(0, 'c:/VCC/Covina')

from ingestion.database_sync_pipeline import DatabaseSyncPipeline

# Monkey-patch for testing (only 10 docs)
original_sync = DatabaseSyncPipeline._sync_postgresql_to_couchdb

def test_sync(self):
    print("\n🧪 TEST MODE: Uploading only 10 documents\n")
    
    # Temporarily override batch size
    import psycopg2
    import requests
    from pathlib import Path
    from datetime import datetime
    import json
    
    couch_url = f"http://{self.couchdb_config['host']}:{self.couchdb_config['port']}"
    db_url = f"{couch_url}/{self.couchdb_config['database']}"
    
    # 1. Test connection
    print("1. Testing CouchDB connection...")
    response = requests.get(couch_url, timeout=5)
    print(f"   ✅ CouchDB {response.json().get('version')} connected\n")
    
    # 2. Fetch 10 documents
    print("2. Fetching 10 test documents from PostgreSQL...")
    conn = psycopg2.connect(**self.pg_config)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT document_id, file_path, classification, 
               content_length, legal_terms_count, created_at,
               quality_score, processing_status, company_metadata
        FROM documents
        ORDER BY file_path
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    print(f"   Fetched: {len(rows)} documents\n")
    
    # 3. Upload to CouchDB
    print("3. Uploading to CouchDB...")
    uploaded = 0
    errors = 0
    
    for doc_id, file_path, classification, content_length, legal_terms, created_at, quality, status, company_meta in rows:
        # Read file content
        content = ""
        if file_path and Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"   📄 {Path(file_path).name[:50]:50s} ({len(content):,} chars)")
            except Exception as e:
                content = f"[ERROR: {e}]"
                print(f"   ❌ {Path(file_path).name[:50]:50s} (read error)")
        else:
            print(f"   ⚠️  {file_path[:50]:50s} (not found)")
        
        doc = {
            '_id': doc_id,
            'file_path': file_path,
            'content': content,
            'classification': classification,
            'content_length': content_length,
            'legal_terms_count': legal_terms,
            'created_at': created_at,
            'quality_score': quality,
            'processing_status': status,
            'company_metadata': company_meta if company_meta else {},
            'uploaded_at': datetime.now().isoformat(),
            'source': 'postgresql_sync_test'
        }
        
        # Upload
        doc_url = f"{db_url}/{doc_id}"
        response = requests.put(
            doc_url,
            json=doc,
            auth=(self.couchdb_config['user'], self.couchdb_config['password'])
        )
        
        if response.status_code in [201, 202]:
            uploaded += 1
        else:
            errors += 1
            print(f"   ⚠️  Upload failed: {response.status_code}")
    
    cursor.close()
    conn.close()
    
    print(f"\n✅ Test complete: {uploaded}/10 uploaded, {errors} errors")
    self.stats['couchdb_uploaded'] = uploaded

DatabaseSyncPipeline._sync_postgresql_to_couchdb = test_sync

# Run test
pipeline = DatabaseSyncPipeline()
pipeline.run(skip_nlp=True, skip_neo4j=True)
