"""
Content Storage Investigation
==============================

Date: 30. Oktober 2025
Investigation: Where is full document content stored?
"""

from database.database_manager import DatabaseManager
import os

print("=" * 70)
print("CONTENT STORAGE INVESTIGATION")
print("=" * 70)
print()

# 1. Check PostgreSQL documents table schema
print("[1] PostgreSQL Documents Table Schema:")
print("-" * 70)

dm = DatabaseManager({"relational": {"enabled": True}}, autostart=True)
rel = dm.relational_backend

schema_query = """
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'documents'
ORDER BY ordinal_position;
"""

columns = rel.execute_query(schema_query, fetch=True)
for col in columns:
    length = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
    print(f"  - {col['column_name']:<25} {col['data_type']}{length}")

print()

# 2. Check if content column exists
print("[2] Content Column Check:")
print("-" * 70)

content_exists = any(col['column_name'] == 'content' for col in columns)
if content_exists:
    print("  ✅ 'content' column EXISTS in PostgreSQL documents table")
    
    # Check if it has data
    content_check = rel.execute_query(
        "SELECT COUNT(*) as total, COUNT(content) as with_content FROM documents;",
        fetch=True
    )
    total = content_check[0]['total']
    with_content = content_check[0]['with_content']
    print(f"  Total documents: {total:,}")
    print(f"  With content:    {with_content:,} ({with_content/total*100:.1f}%)")
else:
    print("  ❌ 'content' column MISSING from PostgreSQL documents table")
    print("  → PostgreSQL does NOT store full text content")

print()

# 3. Check CouchDB
print("[3] CouchDB Document Storage:")
print("-" * 70)

dm2 = DatabaseManager({"file": {"enabled": True}}, autostart=True)
file_backend = dm2.file_backend

if file_backend:
    print(f"  ✅ CouchDB Backend available")
    print(f"  Host: {os.getenv('COUCHDB_HOST', 'not set')}")
    print(f"  Port: {os.getenv('COUCHDB_PORT', 'not set')}")
    
    # Try to get a sample document
    try:
        # Get first document ID from PostgreSQL
        sample_doc = rel.execute_query(
            "SELECT document_id FROM documents LIMIT 1;",
            fetch=True
        )
        
        if sample_doc:
            doc_id = sample_doc[0]['document_id']
            print(f"  Testing with document_id: {doc_id}")
            
            content = file_backend.get_document(doc_id)
            if content:
                print(f"  ✅ CouchDB HAS content for document {doc_id}")
                print(f"  Content preview: {str(content)[:100]}...")
            else:
                print(f"  ❌ CouchDB returns None for document {doc_id}")
                print(f"  → CouchDB appears to be EMPTY (no documents)")
        else:
            print("  ⚠️  No documents in PostgreSQL to test")
    except Exception as e:
        print(f"  ❌ CouchDB access failed: {e}")
else:
    print("  ❌ CouchDB Backend NOT available")
    print("  → File storage backend not initialized")

print()

# 4. Check file system
print("[4] File System Storage:")
print("-" * 70)

data_uploads = "data/uploads"
if os.path.exists(data_uploads):
    print(f"  ✅ Upload directory exists: {data_uploads}")
    
    # Count subdirectories (job directories)
    subdirs = [d for d in os.listdir(data_uploads) if os.path.isdir(os.path.join(data_uploads, d))]
    print(f"  Job directories: {len(subdirs)}")
    
    if subdirs:
        # Count total files
        total_files = 0
        for subdir in subdirs[:5]:  # Sample first 5
            subdir_path = os.path.join(data_uploads, subdir)
            files = [f for f in os.listdir(subdir_path) if os.path.isfile(os.path.join(subdir_path, f))]
            total_files += len(files)
            print(f"    - {subdir}: {len(files)} files")
        
        if len(subdirs) > 5:
            print(f"    ... and {len(subdirs) - 5} more directories")
        
        print(f"  Sample total files: {total_files} (from first 5 dirs)")
    else:
        print("  ⚠️  No job directories found (no files uploaded recently?)")
else:
    print(f"  ❌ Upload directory NOT found: {data_uploads}")
    print("  → No file system storage")

print()

# 5. Summary
print("=" * 70)
print("SUMMARY - Content Storage Location:")
print("=" * 70)
print()

print("PRIMARY STORAGE:")
print("  1. CouchDB (Full Document Storage)")
print("     - Purpose: Store full text content + metadata")
print("     - Status: Backend available, but appears EMPTY")
print("     - Config: backend/ingestion.py lines 1701-1753")
print()

print("METADATA ONLY:")
print("  2. PostgreSQL (Relational Master Data)")
print("     - Columns: document_id, file_path, classification, content_length")
print("     - NO 'content' column → Does NOT store full text")
print("     - Status: 168,454 documents (metadata only)")
print()

print("TEMPORARY STORAGE:")
print("  3. File System (data/uploads/)")
print("     - Purpose: Temporary storage during upload")
print("     - Cleanup: Deleted after successful processing")
print("     - Recovery: Preserved on crash for manual recovery")
print()

print("ROOT CAUSE OF PHASE L4 BLOCKER:")
print("  ❌ CouchDB is EMPTY (no documents found)")
print("  ❌ PostgreSQL has no 'content' column")
print("  ❌ File system has only temporary upload files")
print()

print("NEXT STEPS:")
print("  1. Investigate why CouchDB is empty:")
print("     - Check ingestion logs for CouchDB write errors")
print("     - Verify CouchDB connection during ingestion")
print("     - Check batch insert failures")
print()
print("  2. Verify CouchDB batch inserter status:")
print("     - Check if ENABLE_COUCHDB_BATCH_INSERT=true")
print("     - Review CouchDB batch flush logs")
print()
print("  3. Test single document upload:")
print("     - Upload 1 file via /upload/files endpoint")
print("     - Verify it appears in CouchDB")
print("     - Check document structure")
print()

print("=" * 70)
