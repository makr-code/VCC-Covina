"""Check for markdown Document nodes."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from uds3.core.relations import UDS3RelationsCore

neo4j = UDS3RelationsCore(
    neo4j_uri='bolt://192.168.178.94:7687',
    neo4j_auth=('neo4j', 'v3f3b1d7')
)

with neo4j.neo4j_session() as session:
    # Count markdown documents
    result = session.run('MATCH (d:Document) WHERE d.file_path CONTAINS ".md" RETURN count(d) as total')
    md_count = result.single()['total']
    print(f"Markdown Documents in Neo4j: {md_count:,}")
    
    # Sample markdown document paths
    if md_count > 0:
        print("\nSample .md Document paths:")
        result = session.run('''
            MATCH (d:Document) 
            WHERE d.file_path CONTAINS ".md"
            RETURN d.id as id, d.file_path as path
            LIMIT 5
        ''')
        for record in result:
            print(f"  {record['id']}: {record['path']}")
    
    # Check path patterns
    print("\nAll file_path patterns:")
    result = session.run('''
        MATCH (d:Document)
        WHERE d.file_path IS NOT NULL
        WITH d.file_path as path
        WITH substring(path, size(path)-10, 10) as ext
        RETURN DISTINCT ext
        LIMIT 20
    ''')
    for record in result:
        print(f"  ...{record['ext']}")
