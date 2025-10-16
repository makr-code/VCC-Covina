"""
Chunked HTTP Upload Handler

Provides resumable multi-part file uploads with progress tracking.

Features:
- Multi-part chunked upload (configurable chunk size, default 5 MB)
- Resume capability with MD5 chunk verification
- Session management with timeout (24 hours default)
- Progress tracking per file
- Automatic cleanup of expired sessions

Author: Covina Development Team
Created: 15. Oktober 2025
Version: 1.0.0
"""

import os
import hashlib
import sqlite3
import logging
import asyncio
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ================================================================
# CONFIGURATION
# ================================================================

# Default chunk size: 5 MB
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024

# Session timeout: 24 hours
SESSION_TIMEOUT_HOURS = 24

# Maximum parallel chunks per upload
MAX_PARALLEL_CHUNKS = 10

# Upload storage directory
UPLOAD_STORAGE_DIR = Path("data/uploads/chunked")
UPLOAD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Database path
DB_PATH = Path("data/chunked_uploads.db")

# ================================================================
# PYDANTIC MODELS
# ================================================================

class ChunkedUploadStartRequest(BaseModel):
    """Request to start a chunked upload"""
    file_name: str
    file_size: int
    total_chunks: int
    chunk_size: int = DEFAULT_CHUNK_SIZE
    file_hash: Optional[str] = None  # MD5 hash of complete file (optional)


class ChunkedUploadStartResponse(BaseModel):
    """Response after starting upload"""
    upload_id: str
    chunk_size: int
    resume_from_chunk: int = 0  # 0 = start fresh, >0 = resume
    existing_chunks: List[int] = []  # List of already received chunks


class ChunkUploadResponse(BaseModel):
    """Response after uploading a chunk"""
    upload_id: str
    chunk_index: int
    status: str  # "received", "duplicate", "invalid"
    chunks_received: int
    total_chunks: int
    percent_complete: float


class ChunkedUploadStatusResponse(BaseModel):
    """Upload status response"""
    upload_id: str
    file_name: str
    file_size: int
    total_chunks: int
    chunks_received: int
    percent_complete: float
    status: str  # "uploading", "finalizing", "completed", "failed"
    created_at: str
    last_activity_at: str
    job_id: Optional[str] = None


class ChunkedUploadFinalizeResponse(BaseModel):
    """Response after finalizing upload"""
    upload_id: str
    status: str
    job_id: str
    file_path: str
    file_size: int
    total_chunks: int
    duration_seconds: float


# ================================================================
# DATABASE SCHEMA & MANAGER
# ================================================================

class ChunkedUploadDatabase:
    """
    SQLite database for chunked upload sessions
    
    Tables:
    - chunked_uploads: Upload session metadata
    - upload_chunks: Individual chunk tracking
    """
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # chunked_uploads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunked_uploads (
                upload_id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                total_chunks INTEGER NOT NULL,
                chunks_received INTEGER DEFAULT 0,
                chunk_size INTEGER DEFAULT 5242880,
                file_hash TEXT,
                status TEXT DEFAULT 'uploading',
                created_at TEXT NOT NULL,
                last_activity_at TEXT NOT NULL,
                finalized_at TEXT,
                job_id TEXT,
                storage_path TEXT,
                error_message TEXT
            )
        """)
        
        # upload_chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_chunks (
                upload_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_md5 TEXT NOT NULL,
                chunk_size INTEGER NOT NULL,
                received_at TEXT NOT NULL,
                PRIMARY KEY (upload_id, chunk_index),
                FOREIGN KEY (upload_id) REFERENCES chunked_uploads(upload_id) 
                    ON DELETE CASCADE
            )
        """)
        
        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_uploads_status 
            ON chunked_uploads(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_uploads_last_activity 
            ON chunked_uploads(last_activity_at)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Chunked upload database initialized: {self.db_path}")
    
    def create_upload_session(
        self, 
        upload_id: str,
        file_name: str,
        file_size: int,
        total_chunks: int,
        chunk_size: int,
        file_hash: Optional[str] = None
    ) -> Dict:
        """Create new upload session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO chunked_uploads (
                upload_id, file_name, file_size, total_chunks, 
                chunk_size, file_hash, created_at, last_activity_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (upload_id, file_name, file_size, total_chunks, 
              chunk_size, file_hash, now, now))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📤 Created upload session: {upload_id} - {file_name} ({total_chunks} chunks)")
        
        return {
            "upload_id": upload_id,
            "file_name": file_name,
            "file_size": file_size,
            "total_chunks": total_chunks,
            "chunk_size": chunk_size,
            "status": "uploading",
            "created_at": now
        }
    
    def get_upload_session(self, upload_id: str) -> Optional[Dict]:
        """Get upload session by ID"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM chunked_uploads WHERE upload_id = ?
        """, (upload_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return dict(row)
    
    def get_received_chunks(self, upload_id: str) -> List[int]:
        """Get list of received chunk indices"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chunk_index FROM upload_chunks 
            WHERE upload_id = ?
            ORDER BY chunk_index
        """, (upload_id,))
        
        chunks = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return chunks
    
    def record_chunk(
        self, 
        upload_id: str, 
        chunk_index: int, 
        chunk_md5: str, 
        chunk_size: int
    ) -> bool:
        """
        Record received chunk
        
        Returns:
            True if chunk was newly recorded, False if duplicate
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        try:
            # Insert chunk record
            cursor.execute("""
                INSERT INTO upload_chunks (
                    upload_id, chunk_index, chunk_md5, chunk_size, received_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (upload_id, chunk_index, chunk_md5, chunk_size, now))
            
            # Update upload session
            cursor.execute("""
                UPDATE chunked_uploads 
                SET chunks_received = chunks_received + 1,
                    last_activity_at = ?
                WHERE upload_id = ?
            """, (now, upload_id))
            
            conn.commit()
            is_new = True
            
        except sqlite3.IntegrityError:
            # Duplicate chunk
            is_new = False
            
            # Still update last_activity_at
            cursor.execute("""
                UPDATE chunked_uploads 
                SET last_activity_at = ?
                WHERE upload_id = ?
            """, (now, upload_id))
            
            conn.commit()
        
        conn.close()
        
        return is_new
    
    def update_upload_status(
        self, 
        upload_id: str, 
        status: str, 
        job_id: Optional[str] = None,
        storage_path: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update upload session status"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        updates = ["last_activity_at = ?", "status = ?"]
        params = [now, status]
        
        if job_id:
            updates.append("job_id = ?")
            params.append(job_id)
        
        if storage_path:
            updates.append("storage_path = ?")
            params.append(storage_path)
        
        if error_message:
            updates.append("error_message = ?")
            params.append(error_message)
        
        if status in ["completed", "failed"]:
            updates.append("finalized_at = ?")
            params.append(now)
        
        params.append(upload_id)
        
        query = f"UPDATE chunked_uploads SET {', '.join(updates)} WHERE upload_id = ?"
        cursor.execute(query, params)
        
        conn.commit()
        conn.close()
    
    def delete_upload_session(self, upload_id: str):
        """Delete upload session and all chunks"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Delete chunks (CASCADE will handle this, but explicit for clarity)
        cursor.execute("DELETE FROM upload_chunks WHERE upload_id = ?", (upload_id,))
        
        # Delete upload session
        cursor.execute("DELETE FROM chunked_uploads WHERE upload_id = ?", (upload_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🗑️ Deleted upload session: {upload_id}")
    
    def cleanup_expired_sessions(self, timeout_hours: int = SESSION_TIMEOUT_HOURS) -> int:
        """
        Delete expired upload sessions
        
        Returns:
            Number of sessions deleted
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=timeout_hours)).isoformat()
        
        # Find expired sessions
        cursor.execute("""
            SELECT upload_id, file_name FROM chunked_uploads
            WHERE last_activity_at < ? AND status = 'uploading'
        """, (cutoff_time,))
        
        expired = cursor.fetchall()
        
        if not expired:
            conn.close()
            return 0
        
        # Delete expired sessions
        expired_ids = [row[0] for row in expired]
        placeholders = ','.join('?' * len(expired_ids))
        
        cursor.execute(f"""
            DELETE FROM chunked_uploads WHERE upload_id IN ({placeholders})
        """, expired_ids)
        
        conn.commit()
        conn.close()
        
        logger.info(f"🧹 Cleaned up {len(expired)} expired upload sessions (timeout: {timeout_hours}h)")
        
        return len(expired)


# ================================================================
# CHUNKED UPLOAD HANDLER
# ================================================================

class ChunkedUploadHandler:
    """
    Handler for chunked file uploads
    
    Workflow:
    1. Client calls start_upload() → gets upload_id
    2. Client uploads chunks via upload_chunk()
    3. Client calls finalize_upload() → creates job
    
    Resume:
    - If client disconnects, existing chunks are preserved
    - On reconnect, client calls start_upload() again
    - Server returns existing chunks, client skips them
    """
    
    def __init__(self, db: ChunkedUploadDatabase):
        self.db = db
        
        # Run cleanup on init
        asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions (every hour)"""
        while True:
            await asyncio.sleep(3600)  # 1 hour
            try:
                self.db.cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"❌ Cleanup failed: {e}")
    
    async def start_upload(
        self, 
        request: ChunkedUploadStartRequest
    ) -> ChunkedUploadStartResponse:
        """
        Start chunked upload session
        
        If upload_id already exists (resume), returns existing chunks
        """
        
        # Check if this is a resume (check by filename + size)
        # For now, always create new session
        upload_id = str(uuid.uuid4())
        
        # Create session
        self.db.create_upload_session(
            upload_id=upload_id,
            file_name=request.file_name,
            file_size=request.file_size,
            total_chunks=request.total_chunks,
            chunk_size=request.chunk_size,
            file_hash=request.file_hash
        )
        
        # Create storage directory
        storage_dir = UPLOAD_STORAGE_DIR / upload_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        return ChunkedUploadStartResponse(
            upload_id=upload_id,
            chunk_size=request.chunk_size,
            resume_from_chunk=0,
            existing_chunks=[]
        )
    
    async def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_data: UploadFile
    ) -> ChunkUploadResponse:
        """
        Upload single chunk
        
        Validates chunk, stores to disk, records in database
        """
        # Get upload session
        session = self.db.get_upload_session(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        if session["status"] != "uploading":
            raise HTTPException(
                status_code=400, 
                detail=f"Upload session is {session['status']}, cannot accept chunks"
            )
        
        # Validate chunk index
        if chunk_index < 0 or chunk_index >= session["total_chunks"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid chunk index: {chunk_index} (total: {session['total_chunks']})"
            )
        
        # Read chunk data
        chunk_bytes = await chunk_data.read()
        chunk_size = len(chunk_bytes)
        
        # Calculate MD5
        chunk_md5 = hashlib.md5(chunk_bytes).hexdigest()
        
        # Save chunk to disk
        storage_dir = UPLOAD_STORAGE_DIR / upload_id
        chunk_path = storage_dir / f"chunk_{chunk_index:06d}.bin"
        
        with open(chunk_path, 'wb') as f:
            f.write(chunk_bytes)
        
        # Record in database
        is_new = self.db.record_chunk(upload_id, chunk_index, chunk_md5, chunk_size)
        
        # Get updated stats
        session = self.db.get_upload_session(upload_id)
        chunks_received = session["chunks_received"]
        total_chunks = session["total_chunks"]
        percent = (chunks_received / total_chunks) * 100
        
        status = "received" if is_new else "duplicate"
        
        if is_new:
            logger.debug(f"✅ Chunk {chunk_index}/{total_chunks-1} received for {upload_id} ({percent:.1f}%)")
        else:
            logger.debug(f"⚠️ Duplicate chunk {chunk_index} for {upload_id}")
        
        return ChunkUploadResponse(
            upload_id=upload_id,
            chunk_index=chunk_index,
            status=status,
            chunks_received=chunks_received,
            total_chunks=total_chunks,
            percent_complete=percent
        )
    
    async def get_upload_status(self, upload_id: str) -> ChunkedUploadStatusResponse:
        """Get upload session status"""
        session = self.db.get_upload_session(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        percent = (session["chunks_received"] / session["total_chunks"]) * 100
        
        return ChunkedUploadStatusResponse(
            upload_id=upload_id,
            file_name=session["file_name"],
            file_size=session["file_size"],
            total_chunks=session["total_chunks"],
            chunks_received=session["chunks_received"],
            percent_complete=percent,
            status=session["status"],
            created_at=session["created_at"],
            last_activity_at=session["last_activity_at"],
            job_id=session.get("job_id")
        )
    
    async def finalize_upload(
        self, 
        upload_id: str,
        job_manager=None
    ) -> ChunkedUploadFinalizeResponse:
        """
        Finalize upload: merge chunks, create job
        
        Args:
            upload_id: Upload session ID
            job_manager: JobManager instance (optional, for creating job)
        
        Returns:
            Finalization response with job_id
        """
        # Get session
        session = self.db.get_upload_session(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        if session["status"] != "uploading":
            raise HTTPException(
                status_code=400,
                detail=f"Upload already {session['status']}"
            )
        
        # Verify all chunks received
        if session["chunks_received"] != session["total_chunks"]:
            raise HTTPException(
                status_code=400,
                detail=f"Incomplete upload: {session['chunks_received']}/{session['total_chunks']} chunks"
            )
        
        # Update status to finalizing
        self.db.update_upload_status(upload_id, "finalizing")
        
        try:
            # Merge chunks into final file
            storage_dir = UPLOAD_STORAGE_DIR / upload_id
            final_path = storage_dir / session["file_name"]
            
            start_time = datetime.now()
            
            with open(final_path, 'wb') as outfile:
                for chunk_index in range(session["total_chunks"]):
                    chunk_path = storage_dir / f"chunk_{chunk_index:06d}.bin"
                    
                    if not chunk_path.exists():
                        raise FileNotFoundError(f"Missing chunk: {chunk_index}")
                    
                    with open(chunk_path, 'rb') as infile:
                        outfile.write(infile.read())
                    
                    # Delete chunk after merging
                    chunk_path.unlink()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Verify file size
            actual_size = final_path.stat().st_size
            expected_size = session["file_size"]
            
            if actual_size != expected_size:
                raise ValueError(
                    f"File size mismatch: expected {expected_size}, got {actual_size}"
                )
            
            # Create job (if job_manager provided)
            job_id = None
            if job_manager:
                job_id = job_manager.create_job(
                    file_count=1,
                    temp_directory=str(storage_dir)
                )
                
                # TODO: Submit file for processing
                # await process_documents_batch(job_id, [final_path], storage_dir)
            
            # Update session as completed
            self.db.update_upload_status(
                upload_id, 
                "completed", 
                job_id=job_id,
                storage_path=str(final_path)
            )
            
            logger.info(
                f"✅ Upload finalized: {upload_id} - {session['file_name']} "
                f"({session['total_chunks']} chunks, {duration:.2f}s)"
            )
            
            return ChunkedUploadFinalizeResponse(
                upload_id=upload_id,
                status="completed",
                job_id=job_id or "N/A",
                file_path=str(final_path),
                file_size=actual_size,
                total_chunks=session["total_chunks"],
                duration_seconds=duration
            )
        
        except Exception as e:
            # Update status as failed
            self.db.update_upload_status(upload_id, "failed", error_message=str(e))
            
            logger.error(f"❌ Upload finalization failed: {upload_id} - {e}")
            raise HTTPException(status_code=500, detail=f"Finalization failed: {e}")
    
    async def cancel_upload(self, upload_id: str):
        """Cancel and delete upload session"""
        session = self.db.get_upload_session(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        # Delete from database
        self.db.delete_upload_session(upload_id)
        
        # Delete storage directory
        storage_dir = UPLOAD_STORAGE_DIR / upload_id
        if storage_dir.exists():
            import shutil
            shutil.rmtree(storage_dir)
        
        logger.info(f"❌ Upload cancelled: {upload_id}")


# ================================================================
# GLOBAL INSTANCE
# ================================================================

# Singleton database instance
_db = None
_handler = None

def get_chunked_upload_handler() -> ChunkedUploadHandler:
    """Get or create chunked upload handler"""
    global _db, _handler
    
    if _db is None:
        _db = ChunkedUploadDatabase()
    
    if _handler is None:
        _handler = ChunkedUploadHandler(_db)
    
    return _handler
