from database.database_api_neo4j import Neo4jGraphBackend

cfg = {
    'uri': 'bolt://192.168.178.94:7687',
    'user': 'neo4j',
    'password': 'v3f3b1d7'
}

adapter = Neo4jGraphBackend(cfg)
adapter.connect()

# Create test node
print("Creating test node...")
adapter.execute_query("CREATE (n:TestDocument {document_id: 'test123', title: 'Test'})")

# Count nodes
r1 = adapter.execute_query("MATCH (n:TestDocument) RETURN count(n) as count")
print(f"After create: {r1[0]['count'] if r1 else 0}")

# Delete nodes
print("Deleting test nodes...")
adapter.execute_query("MATCH (n:TestDocument) DETACH DELETE n")

# Count again
r2 = adapter.execute_query("MATCH (n:TestDocument) RETURN count(n) as count")
print(f"After delete: {r2[0]['count'] if r2 else 0}")

adapter.disconnect()
print("✅ Cleanup test complete!")
