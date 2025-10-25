"""
SAGA Controller - UDS3 SAGA Orchestrator (PostgreSQL-based)
============================================================

Provides SAGA Orchestrator access via PostgreSQL queries:
- SAGA status queries (saga_state table)
- Recent transactions list
- Timeline visualization data
- Error tracking

Features:
- PostgreSQL direct access (via UDS3 backend)
- No HTTP dependency
- Real-time status from database

Author: VCC-Covina Team
Version: 2.0.1 (PostgreSQL-based with Cursor Access)
Date: 2025-10-24
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class SAGAController:
    """UDS3 SAGA Orchestrator Controller (PostgreSQL-based)."""
    
    def __init__(self, uds3_manager):
        """
        Initialize SAGA Controller.
        
        Args:
            uds3_manager: UDS3 PolyglotManager instance with relational_backend
        """
        self.uds3 = uds3_manager
        self.backend = None
        
        if uds3_manager:
            # Access PostgreSQL backend for saga_state table
            self.backend = getattr(uds3_manager, 'relational_backend', None)
            if self.backend:
                print(f"[OK] SAGAController: PostgreSQL Backend from UDS3")
            else:
                print(f"[WARNING] SAGAController: No PostgreSQL Backend")
        else:
            print(f"[ERROR] SAGAController: No UDS3 Manager provided")
    
    def is_connected(self) -> bool:
        """Check if PostgreSQL Backend is connected."""
        if not self.backend:
            return False
        
        # Check if pool exists and is usable
        if not hasattr(self.backend, 'pool') or self.backend.pool is None:
            return False
        
        # Try a quick connection test
        try:
            with self.backend.pool.connection() as conn:
                return not conn.closed
        except Exception:
            return False
    
    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute SQL query on PostgreSQL backend (wrapper for cursor access).
        
        Args:
            query: SQL query string
            params: Query parameters tuple
        
        Returns:
            List of result rows as dicts
        """
        if not self.is_connected():
            print(f"[ERROR] SAGA Query failed: Not connected")
            return []
        
        try:
            # Use connection pool context manager
            with self.backend.pool.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                # Fetch results
                results = cursor.fetchall()
                
                # Convert rows to dicts (access by index)
                if results:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in results]
                else:
                    return []
            
        except Exception as e:
            print(f"[ERROR] SAGA Query failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_saga_status(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """
        Get SAGA status by ID from PostgreSQL.
        
        Args:
            saga_id: SAGA instance ID
        
        Returns:
            SAGA status dict or None
        """
        if not self.backend:
            return None
        
        try:
            query = """
            SELECT 
                saga_id,
                status,
                context,
                created_at,
                updated_at,
                completed_at,
                error_message,
                retry_count
            FROM saga_state
            WHERE saga_id = %s
            """
            
            results = self._execute_query(query, (saga_id,))
            
            if results:
                row = results[0]
                return {
                    'saga_id': row.get('saga_id'),
                    'status': row.get('status'),
                    'context': row.get('context'),
                    'created_at': row.get('created_at'),
                    'updated_at': row.get('updated_at'),
                    'completed_at': row.get('completed_at'),
                    'error_message': row.get('error_message'),
                    'retry_count': row.get('retry_count')
                }
            else:
                print(f"[WARNING] SAGA not found: {saga_id}")
                return None
        
        except Exception as e:
            print(f"[ERROR] Get SAGA error: {e}")
            return None
    
    def list_recent_sagas(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List recent SAGA transactions.
        
        Args:
            limit: Maximum number of SAGAs to return
        
        Returns:
            List of SAGA summaries (most recent first)
        """
        if not self.backend:
            return []
        
        try:
            query = """
            SELECT 
                saga_id,
                status,
                created_at,
                completed_at,
                error_message,
                retry_count
            FROM saga_state
            ORDER BY created_at DESC
            LIMIT %s
            """
            
            results = self._execute_query(query, (limit,))
            
            sagas = []
            for row in results:
                sagas.append({
                    'saga_id': row.get('saga_id'),
                    'status': row.get('status'),
                    'created_at': row.get('created_at'),
                    'completed_at': row.get('completed_at'),
                    'error_message': row.get('error_message'),
                    'retry_count': row.get('retry_count')
                })
            
            return sagas
        
        except Exception as e:
            print(f"[ERROR] List SAGAs error: {e}")
            return []
    
    def get_saga_steps(self, saga_id: str) -> List[Dict[str, Any]]:
        """
        Get SAGA steps for a transaction.
        
        Args:
            saga_id: SAGA instance ID
        
        Returns:
            List of steps with status
        """
        if not self.backend:
            return []
        
        try:
            query = """
            SELECT 
                step_id,
                backend_name,
                operation,
                status,
                started_at,
                completed_at,
                error_message,
                retry_count,
                step_order
            FROM saga_steps
            WHERE saga_id = %s
            ORDER BY step_order
            """
            
            results = self._execute_query(query, (saga_id,))
            
            steps = []
            for row in results:
                steps.append({
                    'step_id': row.get('step_id'),
                    'backend_name': row.get('backend_name'),
                    'operation': row.get('operation'),
                    'status': row.get('status'),
                    'started_at': row.get('started_at'),
                    'completed_at': row.get('completed_at'),
                    'error_message': row.get('error_message'),
                    'retry_count': row.get('retry_count'),
                    'step_order': row.get('step_order', 0)
                })
            
            return steps
        
        except Exception as e:
            print(f"[ERROR] Get SAGA steps error: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get SAGA statistics.
        
        Returns:
            Dict with counts by status
        """
        if not self.backend:
            return {'total': 0, 'completed': 0, 'compensated': 0, 'pending': 0, 'failed': 0}
        
        try:
            query = """
            SELECT 
                status,
                COUNT(*) as count
            FROM saga_state
            GROUP BY status
            """
            
            results = self._execute_query(query, ())
            
            stats = {
                'total': 0,
                'completed': 0,
                'compensated': 0,
                'pending': 0,
                'failed': 0
            }
            
            for row in results:
                status = row.get('status')
                count = row.get('count', 0)
                stats['total'] += count
                
                if status in stats:
                    stats[status] = count
            
            return stats
        
        except Exception as e:
            print(f"[ERROR] Get statistics error: {e}")
            return {'total': 0, 'completed': 0, 'compensated': 0, 'pending': 0, 'failed': 0}
    
    def get_failed_sagas(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get failed/compensated SAGAs.
        
        Args:
            limit: Max results
        
        Returns:
            List of failed SAGA summaries
        """
        if not self.backend:
            return []
        
        try:
            query = """
            SELECT 
                saga_id,
                status,
                created_at,
                completed_at,
                error_message,
                retry_count
            FROM saga_state
            WHERE status IN ('compensated', 'failed')
            ORDER BY created_at DESC
            LIMIT %s
            """
            
            results = self._execute_query(query, (limit,))
            
            sagas = []
            for row in results:
                sagas.append({
                    'saga_id': row.get('saga_id'),
                    'status': row.get('status'),
                    'created_at': row.get('created_at'),
                    'completed_at': row.get('completed_at'),
                    'error_message': row.get('error_message'),
                    'retry_count': row.get('retry_count')
                })
            
            return sagas
        
        except Exception as e:
            print(f"[ERROR] Get failed SAGAs error: {e}")
            return []
    
    def get_health(self) -> Dict[str, Any]:
        """
        Get SAGA system health (database connectivity).
        
        Returns:
            Health status dict
        """
        try:
            if self.is_connected():
                # Try a simple query
                result = self._execute_query("SELECT 1", ())
                if result:
                    return {
                        'status': 'healthy',
                        'backend': 'postgresql',
                        'connected': True
                    }
            
            return {
                'status': 'unhealthy',
                'backend': 'postgresql',
                'connected': False
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'backend': 'postgresql',
                'connected': False,
                'error': str(e)
            }
