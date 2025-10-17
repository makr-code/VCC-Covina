# -*- coding: utf-8 -*-
"""
Knowledge Gap Database
=====================

PostgreSQL-basierte Datenbank für Knowledge Gaps im Covina-System.
Nutzt direkte psycopg2 Connection für flexible SQL-Queries.

Autor: Covina Team
Lizenz: AGPL-3.0
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)


class KnowledgeGapDB:
    """PostgreSQL-Datenbank für Knowledge Gap Management"""
    
    def __init__(self, db_path: str = "./data/knowledge_gaps.db"):
        """
        Initialize Knowledge Gap Database using direct PostgreSQL connection
        
        Args:
            db_path: Ignored (kept for compatibility), uses PostgreSQL instead
        """
        if not POSTGRES_AVAILABLE:
            raise RuntimeError("psycopg2 is not installed. Install with: pip install psycopg2-binary")
        
        logger.info("Initializing Knowledge Gap Database with PostgreSQL")
        
        # PostgreSQL configuration from copilot-instructions.md
        self.connection = None
        self.config = {
            'host': '192.168.178.94',
            'port': 5432,
            'database': 'postgres',
            'user': 'postgres',
            'password': 'postgres'
        }
        
        self._connect()
        self._initialize_tables()
    
    def _connect(self):
        """Establish PostgreSQL connection"""
        try:
            self.connection = psycopg2.connect(**self.config)
            self.connection.autocommit = False  # Use transactions
            logger.info(f"✅ Connected to PostgreSQL: {self.config['host']}:{self.config['port']}/{self.config['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise RuntimeError(f"PostgreSQL connection failed: {e}")
    
    def _initialize_tables(self):
        """Create tables if they don't exist using direct SQL"""
        cursor = self.connection.cursor()
        
        try:
            # Knowledge Gaps Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_gaps (
                    id SERIAL PRIMARY KEY,
                    gap_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'open',
                    source TEXT,
                    context TEXT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolution TEXT,
                    assigned_to TEXT,
                    tags JSONB,
                    metadata JSONB
                )
            """)
            logger.info("✅ knowledge_gaps table created/verified")
            
            # Gap Relations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gap_relations (
                    id SERIAL PRIMARY KEY,
                    gap_id INTEGER NOT NULL,
                    related_gap_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (gap_id) REFERENCES knowledge_gaps(id),
                    FOREIGN KEY (related_gap_id) REFERENCES knowledge_gaps(id)
                )
            """)
            logger.info("✅ gap_relations table created/verified")
            
            # Gap History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gap_history (
                    id SERIAL PRIMARY KEY,
                    gap_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    username TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (gap_id) REFERENCES knowledge_gaps(id)
                )
            """)
            logger.info("✅ gap_history table created/verified")
            
            self.connection.commit()
            logger.info("✅ All tables initialized successfully")
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to initialize tables: {e}")
            raise
        finally:
            cursor.close()
    
    def add_gap(self, gap_type: str, description: str, **kwargs) -> int:
        """
        Add a new knowledge gap
        
        Args:
            gap_type: Type of gap (e.g., 'missing_regulation', 'unclear_process')
            description: Description of the gap
            **kwargs: Additional fields (severity, source, context, tags, metadata)
        
        Returns:
            int: ID of created gap
        """
        fields = {
            'gap_type': gap_type,
            'description': description,
            'severity': kwargs.get('severity', 'medium'),
            'status': kwargs.get('status', 'open'),
            'source': kwargs.get('source'),
            'context': kwargs.get('context'),
            'assigned_to': kwargs.get('assigned_to'),
            'tags': json.dumps(kwargs.get('tags', [])) if isinstance(kwargs.get('tags'), list) else kwargs.get('tags'),
            'metadata': json.dumps(kwargs.get('metadata', {})) if isinstance(kwargs.get('metadata'), dict) else kwargs.get('metadata')
        }
        
        # Remove None values
        fields = {k: v for k, v in fields.items() if v is not None}
        
        columns = ', '.join(fields.keys())
        placeholders = ', '.join(['%s' for _ in fields])
        
        query = f"INSERT INTO knowledge_gaps ({columns}) VALUES ({placeholders}) RETURNING id"
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, list(fields.values()))
            gap_id = cursor.fetchone()[0]
            self.connection.commit()
            
            # Log history
            self._add_history(gap_id, 'created', details=f"Gap created: {gap_type}")
            logger.info(f"✅ Created knowledge gap {gap_id}: {gap_type}")
            
            return gap_id
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to add gap: {e}")
            return None
        finally:
            cursor.close()
    
    def get_gaps(self, status: Optional[str] = None, gap_type: Optional[str] = None, 
                 severity: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
        """
        Retrieve knowledge gaps with optional filters
        
        Args:
            status: Filter by status (open, in_progress, resolved, closed)
            gap_type: Filter by gap type
            severity: Filter by severity (low, medium, high, critical)
            limit: Maximum number of results
        
        Returns:
            List of gap dictionaries
        """
        query = "SELECT * FROM knowledge_gaps WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        if gap_type:
            query += " AND gap_type = %s"
            params.append(gap_type)
        
        if severity:
            query += " AND severity = %s"
            params.append(severity)
        
        query += " ORDER BY detected_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(query, params if params else None)
            result = cursor.fetchall()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Failed to get gaps: {e}")
            return []
        finally:
            cursor.close()
    
    def get_gap(self, gap_id: int) -> Optional[Dict]:
        """Get a single gap by ID"""
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("SELECT * FROM knowledge_gaps WHERE id = %s", (gap_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get gap {gap_id}: {e}")
            return None
        finally:
            cursor.close()
    
    def update_gap(self, gap_id: int, **kwargs) -> bool:
        """
        Update a knowledge gap
        
        Args:
            gap_id: Gap ID
            **kwargs: Fields to update
        
        Returns:
            bool: Success status
        """
        # Build update query
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['gap_type', 'description', 'severity', 'status', 'source', 
                      'context', 'resolution', 'assigned_to', 'tags', 'metadata']:
                updates.append(f"{key} = %s")
                
                # Serialize JSON fields
                if key in ['tags', 'metadata'] and isinstance(value, (list, dict)):
                    value = json.dumps(value)
                
                values.append(value)
        
        if not updates:
            return False
        
        values.append(gap_id)
        query = f"UPDATE knowledge_gaps SET {', '.join(updates)} WHERE id = %s"
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, values)
            self.connection.commit()
            
            # Log history
            self._add_history(gap_id, 'updated', details=f"Updated: {', '.join(kwargs.keys())}")
            logger.info(f"✅ Updated gap {gap_id}")
            return True
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to update gap {gap_id}: {e}")
            return False
        finally:
            cursor.close()
    
    def resolve_gap(self, gap_id: int, resolution: str, user: Optional[str] = None) -> bool:
        """
        Mark a gap as resolved
        
        Args:
            gap_id: Gap ID
            resolution: Resolution description
            user: User who resolved the gap
        
        Returns:
            bool: Success status
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                UPDATE knowledge_gaps 
                SET status = 'resolved', 
                    resolution = %s,
                    resolved_at = %s
                WHERE id = %s
            """, (resolution, datetime.now(), gap_id))
            self.connection.commit()
            
            # Log history
            self._add_history(gap_id, 'resolved', user=user, details=resolution)
            logger.info(f"✅ Resolved gap {gap_id}")
            return True
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to resolve gap {gap_id}: {e}")
            return False
        finally:
            cursor.close()
    
    def delete_gap(self, gap_id: int) -> bool:
        """Delete a gap (soft delete by setting status to 'deleted')"""
        return self.update_gap(gap_id, status='deleted')
    
    def _add_history(self, gap_id: int, action: str, user: Optional[str] = None, 
                    details: Optional[str] = None):
        """Add history entry for a gap"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO gap_history (gap_id, action, username, details)
                VALUES (%s, %s, %s, %s)
            """, (gap_id, action, user, details))
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to add history for gap {gap_id}: {e}")
        finally:
            cursor.close()
    
    def get_gap_history(self, gap_id: int) -> List[Dict]:
        """Get history for a specific gap"""
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("""
                SELECT * FROM gap_history 
                WHERE gap_id = %s
                ORDER BY timestamp DESC
            """, (gap_id,))
            result = cursor.fetchall()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Failed to get history for gap {gap_id}: {e}")
            return []
        finally:
            cursor.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Total gaps
            cursor.execute("SELECT COUNT(*) as total FROM knowledge_gaps WHERE status != 'deleted'")
            result = cursor.fetchone()
            stats['total'] = result['total'] if result else 0
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM knowledge_gaps 
                WHERE status != 'deleted'
                GROUP BY status
            """)
            result = cursor.fetchall()
            stats['by_status'] = {row['status']: row['count'] for row in result}
            
            # By severity
            cursor.execute("""
                SELECT severity, COUNT(*) as count 
                FROM knowledge_gaps 
                WHERE status != 'deleted'
                GROUP BY severity
            """)
            result = cursor.fetchall()
            stats['by_severity'] = {row['severity']: row['count'] for row in result}
            
            # By type
            cursor.execute("""
                SELECT gap_type, COUNT(*) as count 
                FROM knowledge_gaps 
                WHERE status != 'deleted'
                GROUP BY gap_type
                ORDER BY count DESC
                LIMIT 10
            """)
            result = cursor.fetchall()
            stats['top_types'] = {row['gap_type']: row['count'] for row in result}
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
        finally:
            cursor.close()
        
        return stats
    
    def get_knowledge_gaps(self, filters: Optional[Dict] = None, limit: Optional[int] = None) -> List[Dict]:
        """
        Alias for get_gaps() - for backward compatibility with GUI
        
        Args:
            filters: Dictionary with optional keys: status, gap_type, severity
            limit: Maximum number of results
        
        Returns:
            List of gap dictionaries
        """
        if filters is None:
            filters = {}
        
        return self.get_gaps(
            status=filters.get('status'),
            gap_type=filters.get('gap_type'),
            severity=filters.get('severity'),
            limit=limit
        )
    
    def close(self):
        """Close database connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self.connection = None
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()
