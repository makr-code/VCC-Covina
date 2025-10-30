"""Check Document node structure in Neo4j."""
from uds3.core.relations import UDS3RelationsCore

neo4j = UDS3RelationsCore(
    neo4j_uri='bolt://192.168.178.94:7687',
    neo4j_auth=('neo4j', 'v3f3b1d7')
)

print("=" * 60)
print("DOCUMENT NODE STRUCTURE ANALYSIS")
print("=" * 60)

with neo4j.neo4j_session() as session:
    # Sample Document nodes
    print("\n1. Sample Document Nodes (first 5):")
    result = session.run("""
        MATCH (d:Document)
        RETURN d.id as id, d.title as title, d.file_path as file_path, d.source as source
        LIMIT 5
    """)
    for record in result:
        print(f"   ID: {record['id']}")
        print(f"   Title: {record['title']}")
        print(f"   Path: {record['file_path']}")
        print(f"   Source: {record['source']}")
        print()
    
    # Document ID patterns
    print("2. Document ID Patterns:")
    result = session.run("""
        MATCH (d:Document)
        WHERE d.id IS NOT NULL
        RETURN d.id as id
        LIMIT 10
    """)
    ids = [record['id'] for record in result]
    for doc_id in ids:
        print(f"   - {doc_id}")
    
    # Check for markdown files
    print("\n3. Documents with .md in path:")
    result = session.run("""
        MATCH (d:Document)
        WHERE d.file_path CONTAINS '.md'
        RETURN d.id as id, d.file_path as path
        LIMIT 5
    """)
    for record in result:
        print(f"   ID: {record['id']}")
        print(f"   Path: {record['path']}")
        print()
