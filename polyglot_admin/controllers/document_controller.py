"""
Document Controller - PostgreSQL via UDS3 PolyglotManager
==========================================================

Bezieht PostgreSQL Backend aus UDS3 Strategy (wie main_backend.py).

Author: VCC-Covina Team  
Version: 3.0.0 (UDS3 PolyglotManager Pattern)
Date: 2025-10-24
"""

from typing import List, Dict, Any, Optional


class DocumentController:
    """PostgreSQL Document Controller via UDS3."""
    
    def __init__(self, uds3_manager):
        """
        Initialize Document Controller.
        
        Args:
            uds3_manager: UDS3PolyglotManager instance
        """
        self.uds3 = uds3_manager
        self.backend = None
        
        if uds3_manager:
            # Backend wird nach Initialisierung als Attribut gesetzt
            self.backend = getattr(uds3_manager, 'relational_backend', None)
            if self.backend:
                print(f"[OK] DocumentController: PostgreSQL Backend from UDS3")
            else:
                print(f"[WARNING] DocumentController: No PostgreSQL Backend")
        else:
            print(f"[ERROR] DocumentController: No UDS3 Manager provided")
    
    def is_connected(self) -> bool:
        """Check if PostgreSQL is connected."""
        if not self.backend:
            return False
        return hasattr(self.backend, 'pool') and self.backend.pool is not None
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        if not self.backend:
            return None
        
        try:
            query = """
            SELECT id, title, content, doc_type, created_at, metadata
            FROM documents
            WHERE id = %s
            """
            
            results = self.backend.execute_query(query, (doc_id,))
            
            if results and len(results) > 0:
                doc = results[0]
                return {
                    'id': doc[0],
                    'title': doc[1],
                    'content': doc[2],
                    'doc_type': doc[3],
                    'created_at': doc[4],
                    'metadata': doc[5] if len(doc) > 5 else {}
                }
        except Exception as e:
            print(f"[ERROR] Get document error: {e}")
        
        return None
    
    def search_documents(self, query: str, filters: Optional[Dict] = None, 
                        limit: int = 50) -> List[Dict[str, Any]]:
        """Search documents (Full-Text Search)."""
        if not self.backend:
            return []
        
        try:
            sql = """
            SELECT id, title, content, doc_type, created_at
            FROM documents
            WHERE title ILIKE %s OR content ILIKE %s
            """
            
            params = [f'%{query}%', f'%{query}%']
            
            if filters and 'doc_type' in filters:
                sql += " AND doc_type = %s"
                params.append(filters['doc_type'])
            
            sql += f" LIMIT {limit}"
            
            results = self.backend.execute_query(sql, tuple(params))
            
            documents = []
            for row in results:
                documents.append({
                    'id': row[0],
                    'title': row[1],
                    'content': row[2][:500] if row[2] else '',
                    'doc_type': row[3],
                    'created_at': row[4]
                })
            
            return documents
        
        except Exception as e:
            print(f"[ERROR] Search error: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        if not self.backend:
            return {'total_documents': 0}
        
        try:
            result = self.backend.execute_query("SELECT COUNT(*) as count FROM documents")
            total = result[0]['count'] if result else 0
            return {'total_documents': total}
        except:
            return {'total_documents': 0}
