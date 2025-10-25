"""
Search Controller - Universal Search via UDS3 PolyglotManager
==============================================================

Universal Search über PostgreSQL + ChromaDB + Neo4j via UDS3 Strategy.

Features:
- Semantic Search (ChromaDB embeddings)
- Keyword Search (PostgreSQL full-text)
- Regex Search (PostgreSQL pattern matching)
- Hybrid Search (UDS3 multi-database)

Author: VCC-Covina Team
Version: 3.1.0 (Hybrid + Semantic + Regex)
Date: 2025-10-24
"""

from typing import List, Dict, Any, Optional
import time
import re


class SearchController:
    """Universal Search Controller via UDS3 with Hybrid/Semantic/Regex."""
    
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
    
    def detect_search_mode(self, query: str) -> str:
        """
        Detect search mode from query pattern.
        
        Returns:
            'regex' - If query contains regex patterns
            'semantic' - If query is natural language
            'keyword' - If query is simple keywords
        """
        # Check for regex patterns
        regex_indicators = [r'\^', r'\$', r'\[.*\]', r'\(.*\)', r'\*', r'\+', r'\?', r'\.']
        if any(re.search(pattern, query) for pattern in regex_indicators):
            return 'regex'
        
        # Check for semantic/natural language (multiple words, questions)
        if len(query.split()) >= 3 or any(q in query.lower() for q in ['what', 'how', 'why', 'when', 'where', 'who']):
            return 'semantic'
        
        return 'keyword'
    
    def hybrid_search(self, query: str, limit: int = 10,
                     mode: str = 'auto') -> Dict[str, Any]:
        """
        UDS3 Hybrid Search across all backends.
        
        Args:
            query: Search query
            limit: Max results per backend
            mode: Search mode ('auto', 'semantic', 'keyword', 'regex')
        
        Returns:
            Combined results from all backends with relevance scores
        """
        # Auto-detect mode if not specified
        if mode == 'auto':
            mode = self.detect_search_mode(query)
        
        print(f"[SEARCH] Mode: {mode}, Query: '{query[:50]}...'")
        
        results = {
            'query': query,
            'mode': mode,
            'timestamp': time.time(),
            'relational': [],
            'vector': [],
            'graph': [],
            'total_results': 0
        }
        
        # Execute search based on mode
        if mode == 'semantic':
            # Prioritize vector search for semantic queries
            results['vector'] = self._search_semantic(query, limit)
            results['relational'] = self._search_relational_fuzzy(query, limit // 2)
            results['graph'] = self._search_graph(query, limit // 2)
        
        elif mode == 'regex':
            # Only relational database supports regex
            results['relational'] = self._search_relational_regex(query, limit)
            # Try vector search with cleaned query
            clean_query = re.sub(r'[^\w\s]', '', query)
            if clean_query.strip():
                results['vector'] = self._search_semantic(clean_query, limit // 2)
        
        else:  # keyword mode
            # Standard multi-backend search
            results['relational'] = self._search_relational(query, limit)
            results['vector'] = self._search_vector(query, limit)
            results['graph'] = self._search_graph(query, limit)
        
        results['total_results'] = (
            len(results['relational']) + 
            len(results['vector']) + 
            len(results['graph'])
        )
        
        return results
    
    def _search_relational(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search PostgreSQL documents (keyword mode)."""
        if not self.relational:
            return []
        
        try:
            sql = """
                SELECT 
                    document_id,
                    title,
                    LEFT(content, 200) as content_preview,
                    metadata,
                    ingestion_timestamp
                FROM documents
                WHERE 
                    title ILIKE %s 
                    OR content ILIKE %s
                ORDER BY ingestion_timestamp DESC
                LIMIT %s
            """
            search_pattern = f"%{query}%"
            
            # Use _get_connection() context manager from PostgreSQLRelationalBackend
            with self.relational._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (search_pattern, search_pattern, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'document_id': row[0],
                        'title': row[1],
                        'preview': row[2],
                        'metadata': row[3],
                        'timestamp': row[4],
                        'source': 'PostgreSQL',
                        'relevance': 0.5  # Medium relevance for keyword match
                    })
                
                return results
        except Exception as e:
            print(f"[ERROR] PostgreSQL search failed: {e}")
            return []
    
    def _search_relational_fuzzy(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search PostgreSQL with fuzzy matching (for semantic mode)."""
        if not self.relational:
            return []
        
        try:
            # Use tsvector for better full-text search
            sql = """
                SELECT 
                    document_id,
                    title,
                    LEFT(content, 200) as content_preview,
                    metadata,
                    ingestion_timestamp,
                    ts_rank(to_tsvector('german', COALESCE(title, '') || ' ' || COALESCE(content, '')), 
                            plainto_tsquery('german', %s)) as rank
                FROM documents
                WHERE 
                    to_tsvector('german', COALESCE(title, '') || ' ' || COALESCE(content, '')) @@ 
                    plainto_tsquery('german', %s)
                ORDER BY rank DESC, ingestion_timestamp DESC
                LIMIT %s
            """
            
            with self.relational._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (query, query, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'document_id': row[0],
                        'title': row[1],
                        'preview': row[2],
                        'metadata': row[3],
                        'timestamp': row[4],
                        'source': 'PostgreSQL (FTS)',
                        'relevance': float(row[5]) if row[5] else 0.3  # ts_rank score
                    })
                
                return results
        except Exception as e:
            print(f"[WARN] PostgreSQL fuzzy search failed (fallback to basic): {e}")
            # Fallback to basic search
            return self._search_relational(query, limit)
    
    def _search_relational_regex(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search PostgreSQL with regex patterns."""
        if not self.relational:
            return []
        
        try:
            # Validate regex pattern first
            try:
                re.compile(query)
            except re.error as e:
                print(f"[ERROR] Invalid regex pattern: {e}")
                return []
            
            sql = """
                SELECT 
                    document_id,
                    title,
                    LEFT(content, 200) as content_preview,
                    metadata,
                    ingestion_timestamp
                FROM documents
                WHERE 
                    title ~ %s 
                    OR content ~ %s
                ORDER BY ingestion_timestamp DESC
                LIMIT %s
            """
            
            with self.relational._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (query, query, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'document_id': row[0],
                        'title': row[1],
                        'preview': row[2],
                        'metadata': row[3],
                        'timestamp': row[4],
                        'source': 'PostgreSQL (Regex)',
                        'relevance': 0.7  # High relevance for regex match
                    })
                
                return results
        except Exception as e:
            print(f"[ERROR] PostgreSQL regex search failed: {e}")
            return []
    
    def _search_vector(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search ChromaDB (basic vector search)."""
        if not self.vector:
            return []
        
        try:
            # Use search_vectors method from ChromaRemoteVectorBackend
            results = self.vector.search_vectors(
                query_text=query,
                top_k=limit
            )
            
            chunks = []
            for result in results:
                chunks.append({
                    'id': result.get('id'),
                    'distance': result.get('distance'),
                    'content': result.get('content', ''),
                    'metadata': result.get('metadata', {}),
                    'source': 'ChromaDB',
                    'relevance': 1.0 - result.get('distance', 1.0)  # Convert distance to relevance
                })
            
            return chunks
        
        except Exception as e:
            print(f"[ERROR] ChromaDB search error: {e}")
            return []
    
    def _search_semantic(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Semantic search via ChromaDB embeddings.
        
        Uses sentence-transformers embeddings for true semantic similarity.
        """
        if not self.vector:
            return []
        
        try:
            # Use ChromaDB's semantic search with embeddings
            results = self.vector.search_vectors(
                query_text=query,
                top_k=limit
            )
            
            chunks = []
            for result in results:
                # ChromaDB returns similarity scores (higher = better)
                distance = result.get('distance', 1.0)
                relevance = max(0.0, 1.0 - distance)  # Convert to 0-1 relevance
                
                chunks.append({
                    'id': result.get('id'),
                    'distance': distance,
                    'relevance': relevance,
                    'content': result.get('content', ''),
                    'metadata': result.get('metadata', {}),
                    'source': 'ChromaDB (Semantic)',
                    'doc_id': result.get('metadata', {}).get('document_id', 'unknown')
                })
            
            return chunks
        
        except Exception as e:
            print(f"[ERROR] ChromaDB semantic search error: {e}")
            return []
    
    def _search_graph(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search Neo4j graph database (keyword mode)."""
        if not self.graph:
            return []
        
        try:
            cypher = """
            MATCH (n)
            WHERE 
                toLower(COALESCE(n.title, '')) CONTAINS toLower($query) OR
                toLower(COALESCE(n.name, '')) CONTAINS toLower($query) OR
                toLower(COALESCE(n.content, '')) CONTAINS toLower($query)
            RETURN 
                elementId(n) as id,
                labels(n) as labels,
                n as node
            LIMIT $limit
            """
            
            # Use execute_query method from Neo4jGraphBackend
            results = self.graph.execute_query(cypher, {"query": query, "limit": limit})
            
            nodes = []
            for record in results:
                node_data = dict(record['node']) if record.get('node') else {}
                nodes.append({
                    'id': record.get('id'),
                    'labels': record.get('labels', []),
                    'properties': node_data,
                    'source': 'Neo4j',
                    'relevance': 0.4  # Lower relevance for graph matches
                })
            
            return nodes
        
        except Exception as e:
            print(f"[ERROR] Neo4j search error: {e}")
            return []
    
    def merge_and_rank_results(self, search_results: Dict[str, Any], 
                               weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Merge results from all backends and rank by relevance.
        
        Args:
            search_results: Dict with 'relational', 'vector', 'graph' results
            weights: Backend weights (default: vector=0.5, relational=0.3, graph=0.2)
        
        Returns:
            Unified list sorted by weighted relevance
        """
        if weights is None:
            weights = {
                'vector': 0.5,      # Highest weight for semantic search
                'relational': 0.3,  # Medium weight for document matches
                'graph': 0.2        # Lower weight for graph matches
            }
        
        merged = []
        
        # Add all relational results
        for doc in search_results.get('relational', []):
            doc['final_score'] = doc.get('relevance', 0.5) * weights['relational']
            merged.append(doc)
        
        # Add all vector results
        for chunk in search_results.get('vector', []):
            chunk['final_score'] = chunk.get('relevance', 0.8) * weights['vector']
            merged.append(chunk)
        
        # Add all graph results
        for node in search_results.get('graph', []):
            node['final_score'] = node.get('relevance', 0.4) * weights['graph']
            merged.append(node)
        
        # Sort by final score (descending)
        merged.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        return merged
