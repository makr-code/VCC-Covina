"""Check Neo4j Document properties."""
from database.database_manager import DatabaseManager

dm = DatabaseManager({"graph": {"enabled": True}}, autostart=True)
backend = dm.graph_backend

result = backend.execute_query("MATCH (d:Document) RETURN d LIMIT 5")

print("\nNeo4j Document Node Properties (Sample):")
print("=" * 70)
for i, r in enumerate(result, 1):
    doc = dict(r["d"])
    print(f"\nDocument {i}:")
    for key, value in sorted(doc.items()):
        value_str = str(value)[:50] if len(str(value)) > 50 else str(value)
        print(f"  {key:20s}: {value_str}")
print("=" * 70)

# Check if any documents have domain information
domain_query = """
MATCH (d:Document)-[:BELONGS_TO]->(domain:LegalDomain)
RETURN COUNT(d) as linked_count
"""
result2 = backend.execute_query(domain_query)
print(f"\nDocuments already linked to LegalDomain: {result2[0]['linked_count']}")
