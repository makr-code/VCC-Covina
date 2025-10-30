"""Quick test for Neo4j connection with correct password."""
from uds3.core.relations import UDS3RelationsCore

neo4j = UDS3RelationsCore(
    neo4j_uri='bolt://192.168.178.94:7687',
    neo4j_auth=('neo4j', 'v3f3b1d7')
)

print(f"Connected: {neo4j.neo4j_enabled}")
print(f"Driver: {neo4j.driver}")

if neo4j.neo4j_enabled:
    with neo4j.neo4j_session() as session:
        result = session.run('MATCH (n) RETURN count(n) as total')
        total = result.single()['total']
        print(f"✅ Total nodes in Neo4j: {total:,}")
else:
    print("❌ Neo4j not connected")
