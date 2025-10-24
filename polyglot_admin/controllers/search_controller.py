"""
Search Controller - Universal Search via UDS3 PolyglotManager
==============================================================

Universal Search über PostgreSQL + ChromaDB + Neo4j via UDS3 Strategy.

Author: VCC-Covina Team
Version: 3.0.0 (UDS3 PolyglotManager Pattern)
Date: 2025-10-24
"""

from typing import List, Dict, Any, Optional
import time


class SearchController:
    """Universal Search Controller via UDS3."""
    
    def __init__(self, uds3_manager):
        """Initialize Search Controller."""
        self.uds3 = uds3_manager
        
        # Get backends from UDS3 Manager (gesetzt als Attribute nach Init)
        self.relational = None
        self.vector = None
        self.graph = None
        
        if uds3_manager:
            self.relational = getattr(uds3_manager, 'relational_backend', None)
            self.vector = getattr(uds3_manager, 'vector_backend', None)
            self.graph = getattr(uds3_manager, 'graph_backend', None)
            
            available = []
            if self.relational and hasattr(self.relational, 'pool') and self.relational.pool:
                available.append("PostgreSQL")
            if self.vector and self.vector.is_available():
                available.append("ChromaDB")
            if self.graph and self.graph.is_available():
                available.append("Neo4j")
            
            print(f"[OK] SearchController: Backends from UDS3: {', '.join(available) if available else 'None'}")
        else:
            print(f"[ERROR] SearchController: No UDS3 Manager provided")
    
    def universal_search(self, query: str, limit: int = 10, 
                        search_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute universal search across all backends."""
        if search_types is None:
            search_types = ['relational', 'vector', 'graph']
        
        results = {
            'query': query,
            'timestamp': time.time(),
            'relational': [],
            'vector': [],
            'graph': [],
            'total_results': 0
        }
        
        # PostgreSQL search
        if 'relational' in search_types and self.relational:
            results['relational'] = self._search_relational(query, limit)
        
        # ChromaDB search
        if 'vector' in search_types and self.vector:
            results['vector'] = self._search_vector(query, limit)
        
        # Neo4j search
        if 'graph' in search_types and self.graph:
            results['graph'] = self._search_graph(query, limit)
        
        results['total_results'] = (
            len(results['relational']) + 
            len(results['vector']) + 
            len(results['graph'])
        )
        
        return results
    
    def _search_relational(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search in PostgreSQL."""
        try:
            sql = """
            SELECT 
                document_id,
                title,
                file_name,
                content_preview,
                created_at
            FROM documents
            WHERE 
                title ILIKE %s OR 
                content_preview ILIKE %s OR
                file_name ILIKE %s
            ORDER BY created_at DESC
            LIMIT %s
            """
            
            search_pattern = f"%{query}%"
            results = self.relational.execute_query(
                sql, 
                (search_pattern, search_pattern, search_pattern, limit)
            )
            
            documents = []
            for row in results:
                documents.append({
                    'document_id': row[0],
                    'title': row[1],
                    'file_name': row[2],
                    'content_preview': row[3],
                    'created_at': row[4],
                    'source': 'PostgreSQL'
                })
            
            return documents
        
        except Exception as e:
            print(f"[ERROR] PostgreSQL search error: {e}")
            return []
    
    def _search_vector(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search in ChromaDB."""
        try:
            results = self.vector.search_similar_vectors(
                query_vector=None,
                query_text=query,
                top_k=limit
            )
            
            chunks = []
            for result in results:
                chunks.append({
                    'id': result.get('id'),
                    'distance': result.get('distance'),
                    'similarity': 1.0 - result.get('distance', 0) if result.get('distance') else None,
                    'metadata': result.get('metadata', {}),
                    'content': result.get('document', ''),
                    'source': 'ChromaDB'
                })
            
            return chunks
        
        except Exception as e:
            print(f"[ERROR] ChromaDB search error: {e}")
            return []
    
    def _search_graph(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search in Neo4j."""
        try:
            cypher = """
            MATCH (n)
            WHERE 
                toLower(n.title) CONTAINS toLower($query) OR
                toLower(n.name) CONTAINS toLower($query) OR
                toLower(n.content) CONTAINS toLower($query)
            RETURN 
                elementId(n) as id,
                labels(n) as labels,
                n as node
            LIMIT $limit
            """
            
            results = self.graph.execute_query(
                cypher,
                {"query": query, "limit": limit}
            )
            
            nodes = []
            for result in results:
                node_data = result.get('node', {})
                nodes.append({
                    'id': result.get('id'),
                    'labels': result.get('labels', []),
                    'properties': node_data,
                    'source': 'Neo4j'
                })
            
            return nodes
        
        except Exception as e:
            print(f"[ERROR] Neo4j search error: {e}")
            return []
