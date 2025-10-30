"""Debug document path matching."""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

from uds3.core.relations import UDS3RelationsCore

# Read first JSONL record
with open('data/nlp/entities.jsonl', encoding='utf-8') as f:
    first_record = json.loads(f.readline())
    jsonl_path = first_record['path']
    
print("=" * 60)
print("DOCUMENT PATH MATCHING DEBUG")
print("=" * 60)

print(f"\n1. JSONL Path:")
print(f"   {jsonl_path}")
print(f"   Type: {type(jsonl_path)}")
print(f"   Length: {len(jsonl_path)}")

# Connect to Neo4j
neo4j = UDS3RelationsCore(
    neo4j_uri='bolt://192.168.178.94:7687',
    neo4j_auth=('neo4j', 'v3f3b1d7')
)

with neo4j.neo4j_session() as session:
    # Search for exact match
    print("\n2. Exact Match Test:")
    result = session.run('''
        MATCH (d:Document)
        WHERE d.file_path = $path
        RETURN d.id as id, d.file_path as path
        LIMIT 1
    ''', {"path": jsonl_path})
    record = result.single()
    if record:
        print(f"   ✅ FOUND: {record['id']}")
        print(f"   Path: {record['path']}")
    else:
        print(f"   ❌ NOT FOUND")
    
    # Search for similar paths (contains)
    print("\n3. Similar Path Search (CONTAINS):")
    # Extract filename
    filename = jsonl_path.split('\\')[-1] if '\\' in jsonl_path else jsonl_path.split('/')[-1]
    print(f"   Filename: {filename}")
    
    result = session.run('''
        MATCH (d:Document)
        WHERE d.file_path CONTAINS $filename
        RETURN d.id as id, d.file_path as path
        LIMIT 3
    ''', {"filename": filename[:50]})  # First 50 chars to avoid long names
    
    found_count = 0
    for record in result:
        found_count += 1
        print(f"   Found #{found_count}:")
        print(f"     ID: {record['id']}")
        print(f"     Path: {record['path']}")
        print(f"     Match: {filename[:30] in record['path']}")
    
    if found_count == 0:
        print("   ❌ No similar paths found")
        
    # Sample Document paths from scan_scan_0a4f9af24886
    print("\n4. Sample paths from same scan:")
    result = session.run('''
        MATCH (d:Document)
        WHERE d.file_path CONTAINS "scan_0a4f9af24886"
        RETURN d.file_path as path
        LIMIT 5
    ''')
    for i, record in enumerate(result, 1):
        print(f"   {i}. {record['path']}")
