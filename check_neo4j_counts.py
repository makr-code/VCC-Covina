"""Check Neo4j Document node count."""
from database.database_manager import DatabaseManager

dm = DatabaseManager({"graph": {"enabled": True}}, autostart=True)
backend = dm.graph_backend

# Total documents
total = backend.execute_query("MATCH (d:Document) RETURN COUNT(d) AS total")
print(f"Total Document nodes in Neo4j: {total[0]['total']:,}")

# Documents with BELONGS_TO
linked = backend.execute_query("MATCH (d:Document)-[:BELONGS_TO]->() RETURN COUNT(d) AS linked")
print(f"Documents with BELONGS_TO:     {linked[0]['linked']:,}")

# Difference
diff = total[0]['total'] - linked[0]['linked']
print(f"Documents WITHOUT link:        {diff:,}")
print()
print(f"Coverage: {linked[0]['linked'] / total[0]['total'] * 100:.2f}%")
