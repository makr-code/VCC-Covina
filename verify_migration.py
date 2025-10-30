"""Verify Phase L5A migration results in Neo4j."""
from database.database_manager import DatabaseManager

dm = DatabaseManager({"graph": {"enabled": True}}, autostart=True)
backend = dm.graph_backend

# Query domain distribution
result = backend.execute_query("""
    MATCH (d:Document)-[:BELONGS_TO]->(domain:LegalDomain)
    RETURN domain.id AS domain, domain.name AS name, COUNT(d) AS doc_count
    ORDER BY doc_count DESC
""")

print("\n" + "=" * 70)
print("Phase L5A - Production Migration Results")
print("=" * 70)
print("\nDomain Distribution:")
print("-" * 70)

total = 0
for i, r in enumerate(result, 1):
    doc_count = r["doc_count"]
    total += doc_count
    domain_id = r["domain"]
    name = r.get("name", "N/A")
    print(f"{i:2d}. {domain_id:30s}: {doc_count:>7,d} docs")

print("-" * 70)
print(f"Total Documents Linked: {total:,}")
print("=" * 70)

# Verify relationship properties
sample = backend.execute_query("""
    MATCH (d:Document)-[r:BELONGS_TO]->(domain:LegalDomain)
    RETURN r.confidence AS confidence, r.method AS method
    LIMIT 5
""")

print("\nSample Relationship Properties:")
for i, r in enumerate(sample, 1):
    print(f"  {i}. Confidence: {r.get('confidence', 'N/A')}, Method: {r.get('method', 'N/A')}")

print()
