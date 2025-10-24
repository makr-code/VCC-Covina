"""
Graph Controller - Neo4j via UDS3 PolyglotManager
==================================================

Bezieht Neo4j Backend aus UDS3 Strategy (wie main_backend.py).

Author: VCC-Covina Team
Version: 3.0.0 (UDS3 PolyglotManager Pattern)
Date: 2025-10-24
"""

from typing import List, Dict, Any, Optional


class GraphController:
    """Neo4j Graph Controller via UDS3."""
    
    def __init__(self, uds3_manager):
        """Initialize Graph Controller."""
        self.uds3 = uds3_manager
        self.backend = None
        
        if uds3_manager:
            # Backend wird nach Initialisierung als Attribut gesetzt
            self.backend = getattr(uds3_manager, 'graph_backend', None)
            if self.backend:
                print(f"[OK] GraphController: Neo4j Backend from UDS3")
            else:
                print(f"[WARNING] GraphController: No Neo4j Backend")
        else:
            print(f"[ERROR] GraphController: No UDS3 Manager provided")
    
    def is_connected(self) -> bool:
        """Check if Neo4j is connected."""
        if not self.backend:
            return False
        return self.backend.is_available()
    
    def execute_cypher(self, query: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute raw Cypher query."""
        if not self.backend:
            return []
        
        try:
            results = self.backend.execute_query(query, parameters or {})
            return results if results else []
        
        except Exception as e:
            print(f"[ERROR] Neo4j query error: {e}")
            return []
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node by ID."""
        query = """
        MATCH (n)
        WHERE elementId(n) = $node_id
        RETURN n, labels(n) as labels
        """
        
        results = self.execute_cypher(query, {"node_id": node_id})
        if results:
            node_data = results[0].get('n', {})
            labels = results[0].get('labels', [])
            node_data['labels'] = labels
            return node_data
        return None
    
    def get_statistics(self) -> Dict[str, int]:
        """Get graph statistics."""
        stats = {
            'nodes': 0,
            'relationships': 0,
            'node_labels': 0,
            'relationship_types': 0
        }
        
        if not self.backend:
            return stats
        
        try:
            # Count nodes
            node_result = self.execute_cypher("MATCH (n) RETURN count(n) as count")
            if node_result:
                stats['nodes'] = node_result[0].get('count', 0)
            
            # Count relationships
            rel_result = self.execute_cypher("MATCH ()-[r]->() RETURN count(r) as count")
            if rel_result:
                stats['relationships'] = rel_result[0].get('count', 0)
            
            # Count node labels
            label_result = self.execute_cypher("CALL db.labels() YIELD label RETURN count(label) as count")
            if label_result:
                stats['node_labels'] = label_result[0].get('count', 0)
            
            # Count relationship types
            type_result = self.execute_cypher("CALL db.relationshipTypes() YIELD relationshipType RETURN count(relationshipType) as count")
            if type_result:
                stats['relationship_types'] = type_result[0].get('count', 0)
        
        except Exception as e:
            print(f"[ERROR] Neo4j statistics error: {e}")
        
        return stats
