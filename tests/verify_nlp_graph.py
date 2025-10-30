"""Verify NLP graph persistence in Neo4j."""
from uds3.core.relations import UDS3RelationsCore

neo4j = UDS3RelationsCore(
    neo4j_uri='bolt://192.168.178.94:7687',
    neo4j_auth=('neo4j', 'v3f3b1d7')
)

print("=" * 60)
print("NLP GRAPH PERSISTENCE VERIFICATION")
print("=" * 60)

with neo4j.neo4j_session() as session:
    # Total nodes before
    print("\n1. Node Counts:")
    
    result = session.run("MATCH (n:LegalConcept) RETURN count(n) as count")
    legal_concepts = result.single()['count']
    print(f"   LegalConcept nodes: {legal_concepts:,}")
    
    result = session.run("MATCH (n:LegalNorm) RETURN count(n) as count")
    legal_norms = result.single()['count']
    print(f"   LegalNorm nodes: {legal_norms:,}")
    
    result = session.run("MATCH (n:Authority) RETURN count(n) as count")
    authorities = result.single()['count']
    print(f"   Authority nodes: {authorities:,}")
    
    # Sample nodes
    print("\n2. Sample LegalConcept Nodes:")
    result = session.run("""
        MATCH (c:LegalConcept)
        RETURN c.id as id, c.name as name, c.label as label, c.extraction_count as count
        ORDER BY c.extraction_count DESC
        LIMIT 5
    """)
    for record in result:
        print(f"   - {record['name']} ({record['label']}) - {record['count']}x extracted")
    
    print("\n3. Sample LegalNorm Nodes:")
    result = session.run("""
        MATCH (n:LegalNorm)
        RETURN n.id as id, n.name as name, n.citation_count as count
        ORDER BY n.citation_count DESC
        LIMIT 5
    """)
    for record in result:
        print(f"   - {record['name']} - {record['count']}x cited")
    
    print("\n4. Relation Counts:")
    
    result = session.run("MATCH ()-[r:MENTIONS]->() RETURN count(r) as count")
    mentions = result.single()['count']
    print(f"   MENTIONS relations: {mentions:,}")
    
    result = session.run("MATCH ()-[r:CITES]->() RETURN count(r) as count")
    cites = result.single()['count']
    print(f"   CITES relations: {cites:,}")
    
    result = session.run("MATCH ()-[r:REFERENCES_AUTHORITY]->() RETURN count(r) as count")
    refs = result.single()['count']
    print(f"   REFERENCES_AUTHORITY relations: {refs:,}")
    
    print("\n5. Sample Relations:")
    result = session.run("""
        MATCH (d:Document)-[r:MENTIONS]->(c:LegalConcept)
        RETURN d.id as doc, c.name as concept
        LIMIT 5
    """)
    for record in result:
        print(f"   - {record['doc']} → MENTIONS → {record['concept']}")

print("\n" + "=" * 60)
print("✅ VERIFICATION COMPLETE")
print("=" * 60)
