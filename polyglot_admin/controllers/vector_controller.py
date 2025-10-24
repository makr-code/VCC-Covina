"""
Vector Controller - ChromaDB via UDS3 PolyglotManager
======================================================

Bezieht ChromaDB Backend aus UDS3 Strategy (wie main_backend.py).

Author: VCC-Covina Team
Version: 3.0.0 (UDS3 PolyglotManager Pattern)
Date: 2025-10-24
"""

from typing import List, Dict, Any, Optional


class VectorController:
    """ChromaDB Vector Controller via UDS3."""
    
    def __init__(self, uds3_manager):
        """Initialize Vector Controller."""
        self.uds3 = uds3_manager
        self.backend = None
        
        if uds3_manager:
            # Backend wird nach Initialisierung als Attribut gesetzt
            self.backend = getattr(uds3_manager, 'vector_backend', None)
            if self.backend:
                print(f"[OK] VectorController: ChromaDB Backend from UDS3")
            else:
                print(f"[WARNING] VectorController: No ChromaDB Backend")
        else:
            print(f"[ERROR] VectorController: No UDS3 Manager provided")
    
    def is_connected(self) -> bool:
        """Check if ChromaDB is connected."""
        if not self.backend:
            return False
        return self.backend.is_available()
    
    def query_similar(self, query_text: str, n_results: int = 10, 
                     filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Semantic similarity search."""
        if not self.backend:
            return []
        
        try:
            results = self.backend.search_similar_vectors(
                query_vector=None,
                query_text=query_text,
                top_k=n_results,
                metadata_filter=filters
            )
            
            chunks = []
            for result in results:
                chunks.append({
                    'id': result.get('id'),
                    'distance': result.get('distance'),
                    'similarity': 1.0 - result.get('distance', 0) if result.get('distance') else None,
                    'metadata': result.get('metadata', {}),
                    'content': result.get('document', '')
                })
            
            return chunks
        
        except Exception as e:
            print(f"[ERROR] ChromaDB query error: {e}")
            return []
