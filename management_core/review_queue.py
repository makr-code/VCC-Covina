"""
PostgreSQL Review Queue for Covina Backend
==========================================

PostgreSQL-based review queue system for tracking data quality gaps.

Created: 17. Oktober 2025
"""

import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Review task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class TaskSeverity(Enum):
    """Task severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GapType(Enum):
    """Gap type classification"""
    MISSING_REGISTER_NUMBER = "missing_register_number"
    MISSING_REGISTER_COURT = "missing_register_court"
    VERIFICATION_FAILED = "verification_failed"
    CLASSIFICATION_UNCERTAIN = "classification_uncertain"
    QUALITY_CHECK_FAILED = "quality_check_failed"
    COMPLIANCE_ISSUE = "compliance_issue"


class ReviewQueue:
    """
    PostgreSQL-based Review Queue for data quality gap tracking.
    
    Manages review tasks stored in PostgreSQL review_tasks table.
    
    Args:
        postgres_backend: PostgreSQLRelationalBackend instance
    """
    
    def __init__(self, postgres_backend):
        """Initialize Review Queue with PostgreSQL backend"""
        self.postgres_backend = postgres_backend
        logger.info("ReviewQueue initialized with PostgreSQL backend")
    
    def add_item(self, review_item: Dict[str, Any]) -> Optional[str]:
        """
        Add review task to queue.
        
        Args:
            review_item: Dictionary with keys:
                - document_id (str, required)
                - file_path (str, optional)
                - gap_type (str, required)
                - firma (str, optional)
                - severity (str, required): low, medium, high, critical
                - message (str, required)
                - status (str, optional): Default 'pending'
                - assigned_to (str, optional)
                - metadata (dict, optional)
        
        Returns:
            review_id (UUID string) or None on failure
        """
        try:
            review_id = str(uuid.uuid4())
            
            # Extract fields
            document_id = review_item.get('document_id')
            file_path = review_item.get('file_path')
            gap_type = review_item.get('gap_type')
            firma = review_item.get('firma')
            severity = review_item.get('severity', 'medium')
            message = review_item.get('message')
            status = review_item.get('status', 'pending')
            assigned_to = review_item.get('assigned_to')
            metadata = review_item.get('metadata', {})
            
            # Validate required fields
            if not document_id or not gap_type or not message:
                logger.error("Missing required fields: document_id, gap_type, or message")
                return None
            
            # Insert into PostgreSQL
            self.postgres_backend.connect()
            
            query = """
            INSERT INTO review_tasks (
                review_id, document_id, file_path, gap_type, firma,
                severity, message, status, created_at, assigned_to, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                review_id, document_id, file_path, gap_type, firma,
                severity, message, status, datetime.now(), assigned_to,
                str(metadata) if metadata else None
            )
            
            self.postgres_backend.cursor.execute(query, params)
            self.postgres_backend.conn.commit()
            
            logger.info(f"Review task {review_id} added for document {document_id}")
            return review_id
            
        except Exception as e:
            logger.error(f"Error adding review task: {e}")
            if self.postgres_backend.conn:
                self.postgres_backend.conn.rollback()
            return None
    
    def get_task(self, review_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single review task by ID.
        
        Args:
            review_id: Review task UUID
        
        Returns:
            Task dictionary or None if not found
        """
        try:
            self.postgres_backend.connect()
            
            query = """
            SELECT review_id, document_id, file_path, gap_type, firma,
                   severity, message, status, created_at, updated_at,
                   assigned_to, resolved_at, resolution_notes, metadata
            FROM review_tasks
            WHERE review_id = %s
            """
            
            self.postgres_backend.cursor.execute(query, (review_id,))
            row = self.postgres_backend.cursor.fetchone()
            
            if row:
                return {
                    'review_id': row[0],
                    'document_id': row[1],
                    'file_path': row[2],
                    'gap_type': row[3],
                    'firma': row[4],
                    'severity': row[5],
                    'message': row[6],
                    'status': row[7],
                    'created_at': str(row[8]),
                    'updated_at': str(row[9]) if row[9] else None,
                    'assigned_to': row[10],
                    'resolved_at': str(row[11]) if row[11] else None,
                    'resolution_notes': row[12],
                    'metadata': row[13]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting task {review_id}: {e}")
            return None
    
    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all tasks with given status.
        
        Args:
            status: Task status (pending, in_progress, resolved, dismissed)
        
        Returns:
            List of task dictionaries
        """
        try:
            self.postgres_backend.connect()
            
            query = """
            SELECT review_id, document_id, file_path, gap_type, firma,
                   severity, message, status, created_at, updated_at,
                   assigned_to, resolved_at, resolution_notes, metadata
            FROM review_tasks
            WHERE status = %s
            ORDER BY created_at DESC
            """
            
            self.postgres_backend.cursor.execute(query, (status,))
            rows = self.postgres_backend.cursor.fetchall()
            
            tasks = []
            for row in rows:
                tasks.append({
                    'review_id': row[0],
                    'document_id': row[1],
                    'file_path': row[2],
                    'gap_type': row[3],
                    'firma': row[4],
                    'severity': row[5],
                    'message': row[6],
                    'status': row[7],
                    'created_at': str(row[8]),
                    'updated_at': str(row[9]) if row[9] else None,
                    'assigned_to': row[10],
                    'resolved_at': str(row[11]) if row[11] else None,
                    'resolution_notes': row[12],
                    'metadata': row[13]
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks by status {status}: {e}")
            return []
    
    def get_tasks_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """
        Get all tasks with given severity.
        
        Args:
            severity: Task severity (low, medium, high, critical)
        
        Returns:
            List of task dictionaries
        """
        try:
            self.postgres_backend.connect()
            
            query = """
            SELECT review_id, document_id, file_path, gap_type, firma,
                   severity, message, status, created_at, updated_at,
                   assigned_to, resolved_at, resolution_notes, metadata
            FROM review_tasks
            WHERE severity = %s
            ORDER BY created_at DESC
            """
            
            self.postgres_backend.cursor.execute(query, (severity,))
            rows = self.postgres_backend.cursor.fetchall()
            
            tasks = []
            for row in rows:
                tasks.append({
                    'review_id': row[0],
                    'document_id': row[1],
                    'file_path': row[2],
                    'gap_type': row[3],
                    'firma': row[4],
                    'severity': row[5],
                    'message': row[6],
                    'status': row[7],
                    'created_at': str(row[8]),
                    'updated_at': str(row[9]) if row[9] else None,
                    'assigned_to': row[10],
                    'resolved_at': str(row[11]) if row[11] else None,
                    'resolution_notes': row[12],
                    'metadata': row[13]
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks by severity {severity}: {e}")
            return []
    
    def get_tasks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks for a specific document.
        
        Args:
            document_id: Document ID
        
        Returns:
            List of task dictionaries
        """
        try:
            self.postgres_backend.connect()
            
            query = """
            SELECT review_id, document_id, file_path, gap_type, firma,
                   severity, message, status, created_at, updated_at,
                   assigned_to, resolved_at, resolution_notes, metadata
            FROM review_tasks
            WHERE document_id = %s
            ORDER BY created_at DESC
            """
            
            self.postgres_backend.cursor.execute(query, (document_id,))
            rows = self.postgres_backend.cursor.fetchall()
            
            tasks = []
            for row in rows:
                tasks.append({
                    'review_id': row[0],
                    'document_id': row[1],
                    'file_path': row[2],
                    'gap_type': row[3],
                    'firma': row[4],
                    'severity': row[5],
                    'message': row[6],
                    'status': row[7],
                    'created_at': str(row[8]),
                    'updated_at': str(row[9]) if row[9] else None,
                    'assigned_to': row[10],
                    'resolved_at': str(row[11]) if row[11] else None,
                    'resolution_notes': row[12],
                    'metadata': row[13]
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks for document {document_id}: {e}")
            return []
    
    def update_status(
        self, 
        review_id: str, 
        status: str, 
        resolution_notes: Optional[str] = None
    ) -> bool:
        """
        Update task status.
        
        Args:
            review_id: Review task UUID
            status: New status (pending, in_progress, resolved, dismissed)
            resolution_notes: Optional resolution notes (required for 'resolved')
        
        Returns:
            True on success, False on failure
        """
        try:
            self.postgres_backend.connect()
            
            if status == 'resolved':
                query = """
                UPDATE review_tasks
                SET status = %s, updated_at = %s, resolved_at = %s, resolution_notes = %s
                WHERE review_id = %s
                """
                params = (status, datetime.now(), datetime.now(), resolution_notes, review_id)
            else:
                query = """
                UPDATE review_tasks
                SET status = %s, updated_at = %s
                WHERE review_id = %s
                """
                params = (status, datetime.now(), review_id)
            
            self.postgres_backend.cursor.execute(query, params)
            self.postgres_backend.conn.commit()
            
            logger.info(f"Review task {review_id} status updated to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating status for task {review_id}: {e}")
            if self.postgres_backend.conn:
                self.postgres_backend.conn.rollback()
            return False
    
    def assign_task(self, review_id: str, assigned_to: str) -> bool:
        """
        Assign task to user/team.
        
        Args:
            review_id: Review task UUID
            assigned_to: User email or ID
        
        Returns:
            True on success, False on failure
        """
        try:
            self.postgres_backend.connect()
            
            query = """
            UPDATE review_tasks
            SET assigned_to = %s, updated_at = %s
            WHERE review_id = %s
            """
            
            self.postgres_backend.cursor.execute(
                query, 
                (assigned_to, datetime.now(), review_id)
            )
            self.postgres_backend.conn.commit()
            
            logger.info(f"Review task {review_id} assigned to {assigned_to}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning task {review_id}: {e}")
            if self.postgres_backend.conn:
                self.postgres_backend.conn.rollback()
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregated statistics across all tasks.
        
        Returns:
            Statistics dictionary with:
            - total_tasks: Total number of tasks
            - by_status: Task count by status
            - by_severity: Task count by severity
            - by_gap_type: Task count by gap type
            - avg_resolution_time_hours: Average resolution time (or None)
        """
        try:
            self.postgres_backend.connect()
            
            # Total tasks
            self.postgres_backend.cursor.execute("SELECT COUNT(*) FROM review_tasks")
            total_tasks = self.postgres_backend.cursor.fetchone()[0]
            
            # By status
            self.postgres_backend.cursor.execute("""
                SELECT status, COUNT(*) FROM review_tasks GROUP BY status
            """)
            by_status = {row[0]: row[1] for row in self.postgres_backend.cursor.fetchall()}
            
            # By severity
            self.postgres_backend.cursor.execute("""
                SELECT severity, COUNT(*) FROM review_tasks GROUP BY severity
            """)
            by_severity = {row[0]: row[1] for row in self.postgres_backend.cursor.fetchall()}
            
            # By gap type
            self.postgres_backend.cursor.execute("""
                SELECT gap_type, COUNT(*) FROM review_tasks GROUP BY gap_type
            """)
            by_gap_type = {row[0]: row[1] for row in self.postgres_backend.cursor.fetchall()}
            
            # Average resolution time
            self.postgres_backend.cursor.execute("""
                SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/3600)
                FROM review_tasks
                WHERE status = 'resolved' AND resolved_at IS NOT NULL
            """)
            result = self.postgres_backend.cursor.fetchone()
            avg_resolution_time_hours = float(result[0]) if result[0] else None
            
            return {
                'total_tasks': total_tasks,
                'by_status': by_status,
                'by_severity': by_severity,
                'by_gap_type': by_gap_type,
                'avg_resolution_time_hours': avg_resolution_time_hours
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_tasks': 0,
                'by_status': {},
                'by_severity': {},
                'by_gap_type': {},
                'avg_resolution_time_hours': None
            }
    
    def delete_task(self, review_id: str) -> bool:
        """
        Delete review task.
        
        Args:
            review_id: Review task UUID
        
        Returns:
            True on success, False on failure
        """
        try:
            self.postgres_backend.connect()
            
            query = "DELETE FROM review_tasks WHERE review_id = %s"
            self.postgres_backend.cursor.execute(query, (review_id,))
            self.postgres_backend.conn.commit()
            
            logger.info(f"Review task {review_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting task {review_id}: {e}")
            if self.postgres_backend.conn:
                self.postgres_backend.conn.rollback()
            return False
