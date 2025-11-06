"""
Phase L5: Graph Queries & Analytics
Cypher-based Legal Document Discovery & Knowledge Graph Analytics.

Available Data (Phase L4 Output):
- 1,369 LegalConcept Nodes
- 5 LegalNorm Nodes  
- 24 Authority Nodes
- 37 Document Nodes
- 1,696 Relations (MENTIONS, CITES, REFERENCES_AUTHORITY)
"""

from typing import List, Dict, Any, Optional
from uds3.core.relations import UDS3RelationsCore


class LegalGraphAnalytics:
    """Analytics for Legal Knowledge Graph (Neo4j)."""
    
    def __init__(self, neo4j_uri: str, neo4j_auth: tuple):
        """Initialize with Neo4j connection."""
        self.neo4j = UDS3RelationsCore(
            neo4j_uri=neo4j_uri,
            neo4j_auth=neo4j_auth
        )
    
    def find_similar_documents(self, min_shared: int = 3) -> List[Dict[str, Any]]:
        """Find documents with shared Legal Concepts."""
        query = '''
        MATCH (d1:Document)-[:MENTIONS]->(c:LegalConcept)<-[:MENTIONS]-(d2:Document)
        WHERE d1.file_path < d2.file_path
        WITH d1, d2, COLLECT(c.name) AS shared_concepts, COUNT(c) AS shared_count
        WHERE shared_count >= $min_shared
        RETURN 
            d1.file_path AS doc1,
            d2.file_path AS doc2,
            shared_count,
            shared_concepts[..5] AS top_shared_concepts
        ORDER BY shared_count DESC
        LIMIT 20
        '''
        
        with self.neo4j.neo4j_session() as session:
            result = session.run(query, {"min_shared": min_shared})
            return [dict(record) for record in result]
    
    def get_entity_cooccurrence(self, min_docs: int = 2) -> List[Dict[str, Any]]:
        """Get entity co-occurrence patterns."""
        query = '''
        MATCH (c1:LegalConcept)<-[:MENTIONS]-(d:Document)-[:MENTIONS]->(c2:LegalConcept)
        WHERE c1.name < c2.name
        WITH c1.name AS concept1, c2.name AS concept2, COUNT(DISTINCT d) AS co_occurrence
        WHERE co_occurrence >= $min_docs
        RETURN concept1, concept2, co_occurrence
        ORDER BY co_occurrence DESC
        LIMIT 20
        '''
        
        with self.neo4j.neo4j_session() as session:
            result = session.run(query, {"min_docs": min_docs})
            return [dict(record) for record in result]
    
    def get_citation_network(self) -> List[Dict[str, Any]]:
        """Analyze LegalNorm citation patterns."""
        query = '''
        MATCH (d:Document)-[:CITES]->(n:LegalNorm)
        WITH n.name AS norm, 
             COUNT(DISTINCT d) AS citation_count,
             COLLECT(DISTINCT d.file_path) AS citing_docs
        RETURN norm, citation_count, citing_docs
        ORDER BY citation_count DESC
        '''
        
        with self.neo4j.neo4j_session() as session:
            result = session.run(query)
            return [dict(record) for record in result]
    
    def get_authority_network(self) -> List[Dict[str, Any]]:
        """Analyze Authority reference patterns."""
        query = '''
        MATCH (d:Document)-[:REFERENCES_AUTHORITY]->(a:Authority)
        WITH a.name AS authority,
             COUNT(DISTINCT d) AS reference_count,
             COLLECT(DISTINCT d.file_path) AS referencing_docs
        RETURN authority, reference_count, referencing_docs
        ORDER BY reference_count DESC
        '''
        
        with self.neo4j.neo4j_session() as session:
            result = session.run(query)
            return [dict(record) for record in result]
    
    def get_top_entities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most connected Legal Concepts (degree centrality)."""
        query = '''
        MATCH (c:LegalConcept)<-[:MENTIONS]-(d:Document)
        WITH c.name AS concept, 
             c.label AS type,
             COUNT(DISTINCT d) AS document_count,
             c.extraction_count AS total_extractions
        RETURN concept, type, document_count, total_extractions
        ORDER BY document_count DESC
        LIMIT $limit
        '''
        
        with self.neo4j.neo4j_session() as session:
            result = session.run(query, {"limit": limit})
            return [dict(record) for record in result]
    
    def get_document_entities(self, doc_path: str) -> Dict[str, Any]:
        """Get all entities for a specific document."""
        query = '''
        MATCH (d:Document {file_path: $doc_path})
        OPTIONAL MATCH (d)-[:MENTIONS]->(c:LegalConcept)
        OPTIONAL MATCH (d)-[:CITES]->(n:LegalNorm)
        OPTIONAL MATCH (d)-[:REFERENCES_AUTHORITY]->(a:Authority)
        RETURN 
            d.file_path AS document,
            COLLECT(DISTINCT c.name) AS mentioned_concepts,
            COLLECT(DISTINCT n.name) AS cited_norms,
            COLLECT(DISTINCT a.name) AS referenced_authorities
        '''
        
        with self.neo4j.neo4j_session() as session:
            result = session.run(query, {"doc_path": doc_path})
            record = result.single()
            return dict(record) if record else {}
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get overall graph statistics."""
        stats = {}
        
        with self.neo4j.neo4j_session() as session:
            # Node counts
            result = session.run('''
                MATCH (n)
                RETURN labels(n)[0] AS node_type, COUNT(n) AS count
                ORDER BY count DESC
            ''')
            stats['node_counts'] = [dict(r) for r in result]
            
            # Relation counts
            result = session.run('''
                MATCH ()-[r]->()
                RETURN type(r) AS relation_type, COUNT(r) AS count
                ORDER BY count DESC
            ''')
            stats['relation_counts'] = [dict(r) for r in result]
            
            # Degree distribution
            result = session.run('''
                MATCH (c:LegalConcept)
                OPTIONAL MATCH (c)<-[:MENTIONS]-(d)
                WITH c, COUNT(d) AS degree
                RETURN 
                    CASE 
                        WHEN degree = 0 THEN '0 (isolated)'
                        WHEN degree <= 5 THEN '1-5'
                        WHEN degree <= 10 THEN '6-10'
                        WHEN degree <= 20 THEN '11-20'
                        ELSE '20+'
                    END AS degree_bucket,
                    COUNT(c) AS concept_count
                ORDER BY degree_bucket
            ''')
            stats['degree_distribution'] = [dict(r) for r in result]
            
            # Average entities per document
            result = session.run('''
                MATCH (d:Document)
                OPTIONAL MATCH (d)-[:MENTIONS]->(c:LegalConcept)
                WITH d, COUNT(c) AS entity_count
                RETURN 
                    AVG(entity_count) AS avg_entities_per_doc,
                    MIN(entity_count) AS min,
                    MAX(entity_count) AS max
            ''')
            record = result.single()
            stats['document_stats'] = dict(record) if record else {}
        
        return stats


if __name__ == "__main__":
    import os
    import json
    
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://192.168.178.94:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "v3f3b1d7")
    
    analytics = LegalGraphAnalytics(
        neo4j_uri=neo4j_uri,
        neo4j_auth=(neo4j_user, neo4j_password)
    )
    
    print("=" * 60)
    print("LEGAL KNOWLEDGE GRAPH ANALYTICS")
    print("=" * 60)
    
    # 1. Graph Statistics
    print("\n1. GRAPH STATISTICS")
    print("-" * 60)
    stats = analytics.get_graph_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 2. Top Entities
    print("\n2. TOP 10 MOST CONNECTED ENTITIES")
    print("-" * 60)
    top_entities = analytics.get_top_entities(limit=10)
    for i, entity in enumerate(top_entities, 1):
        print(f"{i}. {entity['concept']} ({entity['type']})")
        print(f"   Documents: {entity['document_count']}, Total Extractions: {entity['total_extractions']}")
    
    # 3. Entity Co-Occurrence
    print("\n3. ENTITY CO-OCCURRENCE (Top 10)")
    print("-" * 60)
    cooccurrence = analytics.get_entity_cooccurrence(min_docs=2)
    for i, pair in enumerate(cooccurrence[:10], 1):
        print(f"{i}. {pair['concept1']} + {pair['concept2']}: {pair['co_occurrence']} docs")
    
    # 4. Citation Network
    print("\n4. LEGAL NORM CITATIONS")
    print("-" * 60)
    citations = analytics.get_citation_network()
    for norm in citations:
        print(f"- {norm['norm']}: {norm['citation_count']} citations")
    
    # 5. Authority Network
    print("\n5. AUTHORITY REFERENCES")
    print("-" * 60)
    authorities = analytics.get_authority_network()
    for auth in authorities[:10]:
        print(f"- {auth['authority']}: {auth['reference_count']} references")
