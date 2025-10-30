"""
Neo4j Verification Script - Phase L5B
Validates BELONGS_TO relationships and domain distribution.
"""

import sys
sys.path.insert(0, 'C:/VCC/uds3')

from database.database_api_neo4j import Neo4jGraphBackend

def verify_relationships():
    """Verify BELONGS_TO relationship count."""
    g = Neo4jGraphBackend()
    g.connect()  # Ensure connection
    
    print("=" * 60)
    print("Phase L5B - Neo4j Verification")
    print("=" * 60)
    
    # 1. Count BELONGS_TO relationships
    query1 = "MATCH ()-[r:BELONGS_TO]->() RETURN count(r) as count"
    result1 = g.execute_query(query1)
    
    if not result1:
        print("❌ ERROR: No result from Neo4j - driver not connected?")
        return
    
    total_belongs_to = result1[0]['count']
    print(f"\n✅ BELONGS_TO relationships: {total_belongs_to:,}")
    
    # 2. Count Document nodes
    query2 = "MATCH (d:Document) RETURN count(d) as count"
    result2 = g.execute_query(query2)
    total_docs = result2[0]['count']
    print(f"✅ Document nodes: {total_docs:,}")
    
    # 3. Count Domain nodes
    query3 = "MATCH (d:Domain) RETURN count(d) as count"
    result3 = g.execute_query(query3)
    total_domains = result3[0]['count']
    print(f"✅ Domain nodes: {total_domains:,}")
    
    # 4. Domain distribution
    query4 = """
    MATCH (d:Document)-[:BELONGS_TO]->(dom:Domain)
    RETURN dom.name as domain, count(d) as doc_count
    ORDER BY doc_count DESC
    LIMIT 20
    """
    result4 = g.execute_query(query4)
    
    print(f"\n📊 Domain Distribution (Top 20):")
    print("-" * 60)
    for row in result4:
        domain = row['domain']
        count = row['doc_count']
        percentage = (count / total_belongs_to * 100) if total_belongs_to > 0 else 0
        print(f"  {domain:30s} {count:>8,} docs ({percentage:5.2f}%)")
    
    # 5. Documents without domain
    query5 = """
    MATCH (d:Document)
    WHERE NOT (d)-[:BELONGS_TO]->()
    RETURN count(d) as count
    """
    result5 = g.execute_query(query5)
    docs_without_domain = result5[0]['count']
    
    print(f"\n⚠️  Documents without BELONGS_TO: {docs_without_domain:,}")
    
    # Calculate coverage
    coverage = (total_belongs_to / total_docs * 100) if total_docs > 0 else 0
    print(f"\n📈 Coverage: {coverage:.2f}% ({total_belongs_to:,}/{total_docs:,})")
    
    print("=" * 60)
    
    # Validation
    expected_belongs_to = 168264  # From migration summary
    if total_belongs_to == expected_belongs_to:
        print(f"✅ VERIFICATION PASSED: {total_belongs_to:,} relationships (expected: {expected_belongs_to:,})")
    else:
        print(f"⚠️  VERIFICATION WARNING: {total_belongs_to:,} relationships (expected: {expected_belongs_to:,})")
        print(f"   Difference: {total_belongs_to - expected_belongs_to:,}")
    
    print("=" * 60)

if __name__ == "__main__":
    verify_relationships()
