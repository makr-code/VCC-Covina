"""
Persistent Job Storage for Ingestion Backend

Purpose: Store upload job metadata in SQLite for crash recovery
Author: Covina Development Team
Date: 14. Oktober 2025
"""

import sqlite3
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PersistentJobStorage:
    """
    SQLite-based persistent storage for upload jobs
    
    Features:
    - Automatic database initialization
    - Thread-safe operations
    - Job state tracking (pending, processing, completed, failed)
    - Crash recovery support
    - Temp file path tracking
    
    Database Schema:
    - jobs: Main job tracking table
    - scan_jobs: Directory scan job tracking
    - job_files: Individual file tracking per job
    """
    
    def __init__(self, db_path: str = "data/ingestion_jobs.db"):
        """
        Initialize persistent job storage
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._init_database()
        
        logger.info(f"✅ Persistent Job Storage initialized: {self.db_path}")
    
    def _init_database(self):
        """Create database tables if not exist"""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    file_count INTEGER NOT NULL,
                    processed_files INTEGER DEFAULT 0,
                    error_message TEXT,
                    metrics TEXT,
                    temp_directory TEXT,
                    scan_job_id TEXT
                )
            """)

            # Migration: Add correlation_id column if missing (idempotent)
            try:
                cursor.execute("ALTER TABLE jobs ADD COLUMN correlation_id TEXT")
            except Exception:
                # Column likely exists; ignore
                pass
            
            # Scan jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_jobs (
                    scan_job_id TEXT PRIMARY KEY,
                    directory_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    chunk_size INTEGER NOT NULL,
                    files_found INTEGER DEFAULT 0,
                    upload_jobs TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Job files table (for detailed file tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at TEXT,
                    recovery_blocked BOOLEAN DEFAULT 0,
                    block_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                )
            """)
            
            # Create indices for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status 
                ON jobs(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_created 
                ON jobs(created_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scan_jobs_status 
                ON scan_jobs(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_files_job_id 
                ON job_files(job_id)
            """)
            
            conn.commit()
            conn.close()
    
    def save_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Save or update job in database
        
        Args:
            job_data: Job dictionary with metadata
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO jobs 
                    (job_id, status, created_at, updated_at, file_count, 
                     processed_files, error_message, metrics, temp_directory, scan_job_id, correlation_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_data.get("job_id"),
                    job_data.get("status"),
                    job_data.get("created_at"),
                    job_data.get("updated_at"),
                    job_data.get("file_count", 0),
                    job_data.get("processed_files", 0),
                    job_data.get("error_message"),
                    json.dumps(job_data.get("metrics", {})),
                    job_data.get("temp_directory"),
                    job_data.get("scan_job_id"),
                    job_data.get("correlation_id")
                ))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to save job {job_data.get('job_id')}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve job from database
        
        Args:
            job_id: Job ID to retrieve
        
        Returns:
            Job dictionary or None if not found
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT job_id, status, created_at, updated_at, file_count,
                           processed_files, error_message, metrics, temp_directory, scan_job_id, correlation_id
                    FROM jobs WHERE job_id = ?
                """, (job_id,))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return {
                        "job_id": row[0],
                        "status": row[1],
                        "created_at": row[2],
                        "updated_at": row[3],
                        "file_count": row[4],
                        "processed_files": row[5],
                        "error_message": row[6],
                        "metrics": json.loads(row[7]) if row[7] else {},
                        "temp_directory": row[8],
                        "scan_job_id": row[9],
                        "correlation_id": row[10] if len(row) > 10 else None
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            return None
    
    def list_jobs(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List jobs from database
        
        Args:
            limit: Maximum number of jobs to return
            status: Optional status filter (e.g., 'pending', 'processing')
        
        Returns:
            List of job dictionaries
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                if status:
                    cursor.execute("""
                        SELECT job_id, status, created_at, updated_at, file_count,
                               processed_files, error_message, metrics, temp_directory, scan_job_id, correlation_id
                        FROM jobs WHERE status = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (status, limit))
                else:
                    cursor.execute("""
                        SELECT job_id, status, created_at, updated_at, file_count,
                               processed_files, error_message, metrics, temp_directory, scan_job_id, correlation_id
                        FROM jobs
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))
                
                rows = cursor.fetchall()
                conn.close()
                
                jobs = []
                for row in rows:
                    jobs.append({
                        "job_id": row[0],
                        "status": row[1],
                        "created_at": row[2],
                        "updated_at": row[3],
                        "file_count": row[4],
                        "processed_files": row[5],
                        "error_message": row[6],
                        "metrics": json.loads(row[7]) if row[7] else {},
                        "temp_directory": row[8],
                        "scan_job_id": row[9],
                        "correlation_id": row[10] if len(row) > 10 else None
                    })
                
                return jobs
                
        except Exception as e:
            logger.error(f"❌ Failed to list jobs: {e}")
            return []
    
    def save_scan_job(self, scan_data: Dict[str, Any]) -> bool:
        """
        Save directory scan job
        
        Args:
            scan_data: Scan job dictionary
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO scan_jobs
                    (scan_job_id, directory_path, status, chunk_size, files_found,
                     upload_jobs, error_message, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scan_data.get("scan_job_id"),
                    scan_data.get("directory_path"),
                    scan_data.get("status"),
                    scan_data.get("chunk_size", 50),
                    scan_data.get("files_found", 0),
                    json.dumps(scan_data.get("upload_jobs", [])),
                    scan_data.get("error_message"),
                    scan_data.get("created_at"),
                    scan_data.get("updated_at")
                ))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to save scan job: {e}")
            return False
    
    def get_scan_job(self, scan_job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve scan job from database
        
        Args:
            scan_job_id: Scan job ID
        
        Returns:
            Scan job dictionary or None
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT scan_job_id, directory_path, status, chunk_size,
                           files_found, upload_jobs, error_message, created_at, updated_at
                    FROM scan_jobs WHERE scan_job_id = ?
                """, (scan_job_id,))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return {
                        "scan_job_id": row[0],
                        "directory_path": row[1],
                        "status": row[2],
                        "chunk_size": row[3],
                        "files_found": row[4],
                        "upload_jobs": json.loads(row[5]) if row[5] else [],
                        "error_message": row[6],
                        "created_at": row[7],
                        "updated_at": row[8]
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get scan job: {e}")
            return None
    
    def get_incomplete_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all incomplete jobs for crash recovery
        
        Returns:
            List of jobs with status 'pending' or 'processing'
        """
        incomplete_statuses = ['pending', 'processing']
        jobs = []
        
        for status in incomplete_statuses:
            jobs.extend(self.list_jobs(limit=1000, status=status))
        
        return jobs
    
    def save_job_file(self, job_id: str, file_path: str, status: str = "pending") -> bool:
        """
        Track individual file in job
        
        Args:
            job_id: Job ID
            file_path: Path to file
            status: File processing status
        
        Returns:
            True if successful
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO job_files
                    (job_id, file_path, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (job_id, file_path, status, now, now))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to save job file: {e}")
            return False
    
    def update_job_file_status(self, job_id: str, file_path: str, status: str, error: Optional[str] = None) -> bool:
        """
        Update file processing status
        
        Args:
            job_id: Job ID
            file_path: Path to file
            status: New status
            error: Optional error message
        
        Returns:
            True if successful
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE job_files
                    SET status = ?, error_message = ?, updated_at = ?
                    WHERE job_id = ? AND file_path = ?
                """, (status, error, datetime.now().isoformat(), job_id, file_path))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to update job file status: {e}")
            return False
    
    def get_job_files(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get all files tracked for a job
        
        Args:
            job_id: Job ID
        
        Returns:
            List of file tracking entries
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT file_path, status, error_message, created_at, updated_at
                    FROM job_files
                    WHERE job_id = ?
                    ORDER BY created_at
                """, (job_id,))
                
                rows = cursor.fetchall()
                conn.close()
                
                files = []
                for row in rows:
                    files.append({
                        "file_path": row[0],
                        "status": row[1],
                        "error_message": row[2],
                        "created_at": row[3],
                        "updated_at": row[4]
                    })
                
                return files
                
        except Exception as e:
            logger.error(f"❌ Failed to get job files: {e}")
            return []
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Cleanup completed/failed jobs older than N days
        
        Args:
            days: Number of days to keep
        
        Returns:
            Number of jobs deleted
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
                cutoff_str = cutoff_date.isoformat()
                
                # Delete old completed/failed jobs
                cursor.execute("""
                    DELETE FROM jobs
                    WHERE status IN ('completed', 'failed')
                    AND created_at < ?
                """, (cutoff_str,))
                
                deleted_count = cursor.rowcount
                
                # Delete orphaned job_files
                cursor.execute("""
                    DELETE FROM job_files
                    WHERE job_id NOT IN (SELECT job_id FROM jobs)
                """)
                
                conn.commit()
                conn.close()
                
                logger.info(f"🗑️ Cleaned up {deleted_count} old jobs (>{days} days)")
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old jobs: {e}")
            return 0
    
    # ================================================================
    # RECOVERY METHODS
    # ================================================================
    
    def get_failed_files(self, job_id: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Get all failed files that are eligible for recovery
        
        Args:
            job_id: Job ID to filter by (or None for all jobs)
            max_retries: Maximum retry count before blocking recovery
        
        Returns:
            List of failed files with metadata
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                if job_id:
                    cursor.execute("""
                        SELECT id, job_id, file_path, error_message, retry_count, 
                               recovery_blocked, block_reason, created_at, updated_at
                        FROM job_files
                        WHERE job_id = ? AND status = 'failed' 
                        AND retry_count < ? AND recovery_blocked = 0
                        ORDER BY updated_at ASC
                    """, (job_id, max_retries))
                else:
                    cursor.execute("""
                        SELECT id, job_id, file_path, error_message, retry_count, 
                               recovery_blocked, block_reason, created_at, updated_at
                        FROM job_files
                        WHERE status = 'failed' 
                        AND retry_count < ? AND recovery_blocked = 0
                        ORDER BY updated_at ASC
                    """, (max_retries,))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [
                    {
                        "id": row[0],
                        "job_id": row[1],
                        "file_path": row[2],
                        "error_message": row[3],
                        "retry_count": row[4],
                        "recovery_blocked": bool(row[5]),
                        "block_reason": row[6],
                        "created_at": row[7],
                        "updated_at": row[8]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"❌ Failed to get failed files: {e}")
            return []
    
    def get_blocked_files(self, job_id: str = None) -> List[Dict[str, Any]]:
        """
        Get all recovery-blocked files (critical errors)
        
        Args:
            job_id: Optional job ID filter
        
        Returns:
            List of blocked files
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                if job_id:
                    cursor.execute("""
                        SELECT id, job_id, file_path, error_message, retry_count,
                               block_reason, created_at, updated_at
                        FROM job_files
                        WHERE job_id = ? AND recovery_blocked = 1
                        ORDER BY updated_at DESC
                    """, (job_id,))
                else:
                    cursor.execute("""
                        SELECT id, job_id, file_path, error_message, retry_count,
                               block_reason, created_at, updated_at
                        FROM job_files
                        WHERE recovery_blocked = 1
                        ORDER BY updated_at DESC
                    """)
                
                rows = cursor.fetchall()
                conn.close()
                
                return [
                    {
                        "id": row[0],
                        "job_id": row[1],
                        "file_path": row[2],
                        "error_message": row[3],
                        "retry_count": row[4],
                        "block_reason": row[5],
                        "created_at": row[6],
                        "updated_at": row[7]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"❌ Failed to get blocked files: {e}")
            return []
    
    def increment_retry_count(self, job_id: str, file_path: str) -> bool:
        """
        Increment retry counter for a file
        
        Args:
            job_id: Job ID
            file_path: File path
        
        Returns:
            True if successful
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                cursor.execute("""
                    UPDATE job_files
                    SET retry_count = retry_count + 1,
                        last_retry_at = ?,
                        updated_at = ?
                    WHERE job_id = ? AND file_path = ?
                """, (now, now, job_id, file_path))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to increment retry count: {e}")
            return False
    
    def block_file_recovery(self, job_id: str, file_path: str, reason: str) -> bool:
        """
        Block a file from automatic recovery (critical error)
        
        Args:
            job_id: Job ID
            file_path: File path
            reason: Reason for blocking
        
        Returns:
            True if successful
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE job_files
                    SET recovery_blocked = 1,
                        block_reason = ?,
                        updated_at = ?
                    WHERE job_id = ? AND file_path = ?
                """, (reason, datetime.now().isoformat(), job_id, file_path))
                
                conn.commit()
                conn.close()
                
                logger.warning(f"⚠️ Blocked file from recovery: {file_path} - {reason}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to block file recovery: {e}")
            return False
    
    def unblock_file_recovery(self, job_id: str, file_path: str, admin_override: bool = False) -> bool:
        """
        Unblock a file for recovery (requires admin override)
        
        Args:
            job_id: Job ID
            file_path: File path
            admin_override: Admin confirmation flag
        
        Returns:
            True if successful
        """
        if not admin_override:
            logger.error("❌ Admin override required to unblock file recovery")
            return False
        
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE job_files
                    SET recovery_blocked = 0,
                        block_reason = NULL,
                        retry_count = 0,
                        updated_at = ?
                    WHERE job_id = ? AND file_path = ?
                """, (datetime.now().isoformat(), job_id, file_path))
                
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Unblocked file for recovery (admin): {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to unblock file recovery: {e}")
            return False
    
    def reset_file_status(self, job_id: str, file_path: str, new_status: str = "pending") -> bool:
        """
        Reset file status for retry (e.g., failed → pending)
        
        Args:
            job_id: Job ID
            file_path: File path
            new_status: New status (default: pending)
        
        Returns:
            True if successful
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE job_files
                    SET status = ?,
                        error_message = NULL,
                        updated_at = ?
                    WHERE job_id = ? AND file_path = ?
                """, (new_status, datetime.now().isoformat(), job_id, file_path))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to reset file status: {e}")
            return False

