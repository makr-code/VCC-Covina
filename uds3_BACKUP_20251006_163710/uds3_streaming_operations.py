"""
UDS3 Streaming Operations Module
=================================

Provides efficient streaming capabilities for large files (300+ MB):
- Chunked Upload/Download (memory-efficient)
- Resume Support (continue after interruption)
- Progress Tracking (real-time monitoring)
- Large File Processing (PDFs with embedded images)
- Chunked Vector DB Operations (large embeddings)

Design Philosophy:
- Never load entire file into memory
- Support files >1GB
- Resumable operations (fault-tolerant)
- Progress callbacks for UI integration
- Memory-efficient chunking

Author: UDS3 Team
Date: 2. Oktober 2025
Version: 1.0.0
"""

import os
import hashlib
import uuid
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class SagaRollbackRequired(Exception):
    """
    Exception signalisiert: Saga muss Rollback durchführen
    
    Raised when:
    - Resume attempts exhausted
    - Critical error (file not found, metadata corrupt)
    - Timeout exceeded
    - Integrity check failed
    """
    def __init__(
        self,
        reason: str,
        message: str,
        operation_id: Optional[str] = None,
        retry_count: int = 0,
        last_error: Optional[str] = None
    ):
        self.reason = reason
        self.message = message
        self.operation_id = operation_id
        self.retry_count = retry_count
        self.last_error = last_error
        super().__init__(message)


class ChunkMetadataCorruptError(Exception):
    """Chunk metadata is corrupted or inconsistent"""
    pass


class StorageBackendError(Exception):
    """Storage backend unreachable or malfunctioning"""
    pass


class CompensationError(Exception):
    """Error during saga compensation (rollback)"""
    pass


# ============================================================================
# Configuration
# ============================================================================

# Default chunk size: 5MB (adjustable based on network/memory)
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB
LARGE_CHUNK_SIZE = 10 * 1024 * 1024   # 10 MB (for fast networks)
SMALL_CHUNK_SIZE = 1 * 1024 * 1024    # 1 MB (for slow networks)


# ============================================================================
# Enums
# ============================================================================

class StreamingStatus(Enum):
    """Status of streaming operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StreamingOperation(Enum):
    """Type of streaming operation"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    PROCESSING = "processing"


# ============================================================================
# Progress Tracking
# ============================================================================

@dataclass
class StreamingProgress:
    """Progress information for streaming operation"""
    operation_id: str
    operation_type: StreamingOperation
    status: StreamingStatus
    
    # Progress metrics
    total_bytes: int
    transferred_bytes: int
    chunk_count: int
    current_chunk: int
    
    # Timing
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    # Performance
    bytes_per_second: float = 0.0
    estimated_time_remaining: Optional[float] = None
    
    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage"""
        if self.total_bytes == 0:
            return 0.0
        return (self.transferred_bytes / self.total_bytes) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete"""
        return self.status == StreamingStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if operation failed"""
        return self.status == StreamingStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type.value,
            'status': self.status.value,
            'total_bytes': self.total_bytes,
            'transferred_bytes': self.transferred_bytes,
            'progress_percent': self.progress_percent,
            'chunk_count': self.chunk_count,
            'current_chunk': self.current_chunk,
            'started_at': self.started_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'bytes_per_second': self.bytes_per_second,
        }
        
        if self.completed_at:
            result['completed_at'] = self.completed_at.isoformat()
        if self.estimated_time_remaining:
            result['estimated_time_remaining'] = self.estimated_time_remaining
        if self.error_message:
            result['error_message'] = self.error_message
        
        return result


@dataclass
class ChunkMetadata:
    """Metadata for individual chunk"""
    chunk_id: str
    chunk_index: int
    chunk_size: int
    chunk_hash: str
    uploaded_at: Optional[datetime] = None
    destination: Optional[str] = None  # Storage location for rollback


@dataclass
class StreamingSagaConfig:
    """Configuration for Streaming Saga with Rollback"""
    max_resume_attempts: int = 3
    resume_retry_delay: float = 5.0  # seconds
    hash_verification_enabled: bool = True
    rollback_on_timeout: bool = True
    timeout_seconds: float = 3600.0  # 1 hour
    auto_rollback_on_failure: bool = True


# ============================================================================
# Streaming Manager
# ============================================================================

class StreamingManager:
    """
    Manages streaming operations for large files.
    
    Features:
    - Chunked upload/download (memory-efficient)
    - Resume support (continue after interruption)
    - Progress tracking (real-time updates)
    - Concurrent operations (thread-safe)
    - Error recovery (automatic retry)
    """
    
    def __init__(
        self,
        storage_backend=None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        max_concurrent_operations: int = 5
    ):
        """
        Initialize StreamingManager.
        
        Args:
            storage_backend: Backend for file storage
            chunk_size: Size of each chunk in bytes
            max_concurrent_operations: Max concurrent streaming operations
        """
        self.storage_backend = storage_backend
        self.chunk_size = chunk_size
        self.max_concurrent_operations = max_concurrent_operations
        
        # Track active operations
        self._operations: Dict[str, StreamingProgress] = {}
        self._chunks: Dict[str, List[ChunkMetadata]] = {}
        self._lock = threading.Lock()
        
        logger.info(f"StreamingManager initialized (chunk_size={chunk_size/1024/1024:.1f}MB)")
    
    # ========================================================================
    # Chunked Upload
    # ========================================================================
    
    def upload_large_file(
        self,
        file_path: str,
        destination: str,
        chunk_size: Optional[int] = None,
        progress_callback: Optional[Callable[[StreamingProgress], None]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload a large file in chunks.
        
        Args:
            file_path: Path to file to upload
            destination: Destination path/identifier
            chunk_size: Override default chunk size
            progress_callback: Callback for progress updates
            metadata: Additional metadata
        
        Returns:
            Operation ID for tracking
        
        Example:
            ```python
            def on_progress(progress):
                print(f"Progress: {progress.progress_percent:.1f}%")
            
            op_id = manager.upload_large_file(
                "large_pdf.pdf",
                "storage/documents/large_pdf.pdf",
                progress_callback=on_progress
            )
            ```
        """
        # Validate file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        chunk_size = chunk_size or self.chunk_size
        
        # Calculate chunks
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        # Create operation
        operation_id = f"upload-{uuid.uuid4().hex[:12]}"
        progress = StreamingProgress(
            operation_id=operation_id,
            operation_type=StreamingOperation.UPLOAD,
            status=StreamingStatus.IN_PROGRESS,
            total_bytes=file_size,
            transferred_bytes=0,
            chunk_count=total_chunks,
            current_chunk=0,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with self._lock:
            self._operations[operation_id] = progress
            self._chunks[operation_id] = []
        
        logger.info(f"Starting upload: {file_path} → {destination} ({file_size/1024/1024:.1f}MB, {total_chunks} chunks)")
        
        try:
            # Open file and upload in chunks
            with open(file_path, 'rb') as f:
                chunk_index = 0
                start_time = time.time()
                
                while True:
                    # Read chunk
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Calculate chunk hash
                    chunk_hash = hashlib.sha256(chunk_data).hexdigest()
                    
                    # Upload chunk (simulate for now)
                    chunk_id = f"{operation_id}-chunk-{chunk_index}"
                    self._upload_chunk(destination, chunk_index, chunk_data)
                    
                    # Update progress
                    chunk_metadata = ChunkMetadata(
                        chunk_id=chunk_id,
                        chunk_index=chunk_index,
                        chunk_size=len(chunk_data),
                        chunk_hash=chunk_hash,
                        uploaded_at=datetime.utcnow()
                    )
                    
                    with self._lock:
                        self._chunks[operation_id].append(chunk_metadata)
                        progress.transferred_bytes += len(chunk_data)
                        progress.current_chunk = chunk_index + 1
                        progress.updated_at = datetime.utcnow()
                        
                        # Calculate speed
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            progress.bytes_per_second = progress.transferred_bytes / elapsed
                            remaining_bytes = progress.total_bytes - progress.transferred_bytes
                            progress.estimated_time_remaining = remaining_bytes / progress.bytes_per_second if progress.bytes_per_second > 0 else None
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(progress)
                    
                    chunk_index += 1
                    
                    logger.debug(f"Uploaded chunk {chunk_index}/{total_chunks} ({len(chunk_data)/1024:.1f}KB)")
            
            # Mark complete
            with self._lock:
                progress.status = StreamingStatus.COMPLETED
                progress.completed_at = datetime.utcnow()
                progress.updated_at = datetime.utcnow()
            
            if progress_callback:
                progress_callback(progress)
            
            logger.info(f"Upload complete: {operation_id} ({file_size/1024/1024:.1f}MB in {total_chunks} chunks)")
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            with self._lock:
                progress.status = StreamingStatus.FAILED
                progress.error_message = str(e)
                progress.updated_at = datetime.utcnow()
            
            if progress_callback:
                progress_callback(progress)
            
            raise
    
    def _upload_chunk(self, destination: str, chunk_index: int, chunk_data: bytes):
        """Upload a single chunk (internal)"""
        # In production, this would upload to actual storage backend
        # For now, simulate upload
        time.sleep(0.001)  # Simulate network delay
    
    # ========================================================================
    # Chunked Download
    # ========================================================================
    
    def download_large_file(
        self,
        source: str,
        output_path: str,
        chunk_size: Optional[int] = None,
        progress_callback: Optional[Callable[[StreamingProgress], None]] = None
    ) -> str:
        """
        Download a large file in chunks.
        
        Args:
            source: Source path/identifier
            output_path: Local output path
            chunk_size: Override default chunk size
            progress_callback: Callback for progress updates
        
        Returns:
            Operation ID for tracking
        """
        chunk_size = chunk_size or self.chunk_size
        
        # Get file size (would query backend in production)
        file_size = self._get_file_size(source)
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        # Create operation
        operation_id = f"download-{uuid.uuid4().hex[:12]}"
        progress = StreamingProgress(
            operation_id=operation_id,
            operation_type=StreamingOperation.DOWNLOAD,
            status=StreamingStatus.IN_PROGRESS,
            total_bytes=file_size,
            transferred_bytes=0,
            chunk_count=total_chunks,
            current_chunk=0,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with self._lock:
            self._operations[operation_id] = progress
        
        logger.info(f"Starting download: {source} → {output_path} ({file_size/1024/1024:.1f}MB, {total_chunks} chunks)")
        
        try:
            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Download chunks
            with open(output_path, 'wb') as f:
                start_time = time.time()
                
                for chunk_index in range(total_chunks):
                    # Download chunk
                    chunk_data = self._download_chunk(source, chunk_index, chunk_size)
                    f.write(chunk_data)
                    
                    # Update progress
                    with self._lock:
                        progress.transferred_bytes += len(chunk_data)
                        progress.current_chunk = chunk_index + 1
                        progress.updated_at = datetime.utcnow()
                        
                        # Calculate speed
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            progress.bytes_per_second = progress.transferred_bytes / elapsed
                            remaining_bytes = progress.total_bytes - progress.transferred_bytes
                            progress.estimated_time_remaining = remaining_bytes / progress.bytes_per_second if progress.bytes_per_second > 0 else None
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(progress)
                    
                    logger.debug(f"Downloaded chunk {chunk_index+1}/{total_chunks} ({len(chunk_data)/1024:.1f}KB)")
            
            # Mark complete
            with self._lock:
                progress.status = StreamingStatus.COMPLETED
                progress.completed_at = datetime.utcnow()
                progress.updated_at = datetime.utcnow()
            
            if progress_callback:
                progress_callback(progress)
            
            logger.info(f"Download complete: {operation_id}")
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            with self._lock:
                progress.status = StreamingStatus.FAILED
                progress.error_message = str(e)
                progress.updated_at = datetime.utcnow()
            
            if progress_callback:
                progress_callback(progress)
            
            raise
    
    def _download_chunk(self, source: str, chunk_index: int, chunk_size: int) -> bytes:
        """Download a single chunk (internal)"""
        # In production, this would download from actual storage backend
        # For now, simulate download with dummy data
        time.sleep(0.001)  # Simulate network delay
        return b'x' * min(chunk_size, 1024)  # Return dummy data
    
    def _get_file_size(self, source: str) -> int:
        """Get file size from backend (internal)"""
        # In production, query backend for file size
        # For now, return dummy size
        return 100 * 1024 * 1024  # 100 MB
    
    # ========================================================================
    # Resume Support
    # ========================================================================
    
    def resume_upload(
        self,
        operation_id: str,
        file_path: str,
        destination: str,
        progress_callback: Optional[Callable[[StreamingProgress], None]] = None
    ) -> str:
        """
        Resume an interrupted upload.
        
        Args:
            operation_id: Original operation ID
            file_path: Path to file
            destination: Destination path
            progress_callback: Callback for progress updates
        
        Returns:
            Operation ID (same as input)
        """
        # Get existing progress
        with self._lock:
            if operation_id not in self._operations:
                raise ValueError(f"Operation not found: {operation_id}")
            
            progress = self._operations[operation_id]
            uploaded_chunks = len(self._chunks.get(operation_id, []))
        
        logger.info(f"Resuming upload: {operation_id} from chunk {uploaded_chunks}")
        
        # Continue upload from last chunk
        file_size = os.path.getsize(file_path)
        chunk_size = self.chunk_size
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        try:
            with open(file_path, 'rb') as f:
                # Skip to resume point
                f.seek(uploaded_chunks * chunk_size)
                
                start_time = time.time()
                
                for chunk_index in range(uploaded_chunks, total_chunks):
                    # Read chunk
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Upload chunk
                    chunk_hash = hashlib.sha256(chunk_data).hexdigest()
                    chunk_id = f"{operation_id}-chunk-{chunk_index}"
                    self._upload_chunk(destination, chunk_index, chunk_data)
                    
                    # Update progress
                    chunk_metadata = ChunkMetadata(
                        chunk_id=chunk_id,
                        chunk_index=chunk_index,
                        chunk_size=len(chunk_data),
                        chunk_hash=chunk_hash,
                        uploaded_at=datetime.utcnow()
                    )
                    
                    with self._lock:
                        self._chunks[operation_id].append(chunk_metadata)
                        progress.transferred_bytes += len(chunk_data)
                        progress.current_chunk = chunk_index + 1
                        progress.status = StreamingStatus.IN_PROGRESS
                        progress.updated_at = datetime.utcnow()
                        
                        # Calculate speed
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            bytes_since_resume = progress.transferred_bytes - (uploaded_chunks * chunk_size)
                            progress.bytes_per_second = bytes_since_resume / elapsed
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(progress)
            
            # Mark complete
            with self._lock:
                progress.status = StreamingStatus.COMPLETED
                progress.completed_at = datetime.utcnow()
                progress.updated_at = datetime.utcnow()
            
            if progress_callback:
                progress_callback(progress)
            
            logger.info(f"Resume upload complete: {operation_id}")
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Resume upload failed: {e}")
            with self._lock:
                progress.status = StreamingStatus.FAILED
                progress.error_message = str(e)
                progress.updated_at = datetime.utcnow()
            
            if progress_callback:
                progress_callback(progress)
            
            raise
    
    # ========================================================================
    # Progress & Status
    # ========================================================================
    
    def get_progress(self, operation_id: str) -> Optional[StreamingProgress]:
        """Get progress for an operation"""
        with self._lock:
            return self._operations.get(operation_id)
    
    def list_operations(
        self,
        status: Optional[StreamingStatus] = None
    ) -> List[StreamingProgress]:
        """List all operations, optionally filtered by status"""
        with self._lock:
            operations = list(self._operations.values())
        
        if status:
            operations = [op for op in operations if op.status == status]
        
        return operations
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an operation"""
        with self._lock:
            if operation_id in self._operations:
                progress = self._operations[operation_id]
                if progress.status == StreamingStatus.IN_PROGRESS:
                    progress.status = StreamingStatus.CANCELLED
                    progress.updated_at = datetime.utcnow()
                    logger.info(f"Operation cancelled: {operation_id}")
                    return True
        return False
    
    def get_operation_chunks(self, operation_id: str) -> List[ChunkMetadata]:
        """Get list of chunks for an operation"""
        with self._lock:
            return self._chunks.get(operation_id, [])
    
    # ========================================================================
    # Saga Rollback Support
    # ========================================================================
    
    def chunked_upload_with_retry(
        self,
        file_path: str,
        destination: str,
        config: StreamingSagaConfig,
        progress_callback: Optional[Callable[[StreamingProgress], None]] = None
    ) -> Dict[str, Any]:
        """
        Chunked Upload mit automatischem Retry und Rollback
        
        Strategy:
        1. Versuche Upload
        2. Bei Fehler: Versuche Resume (max N mal)
        3. Wenn Resume fehlschlägt: Trigger Rollback
        4. Wenn Rollback fehlschlägt: Critical Error
        
        Args:
            file_path: Path to file
            destination: Destination path
            config: Saga configuration with retry settings
            progress_callback: Progress callback
        
        Returns:
            Dict with operation_id, uploaded_chunks, total_bytes, retry_count
        
        Raises:
            SagaRollbackRequired: When resume exhausted or critical error
        """
        retry_count = 0
        operation_id = None
        last_error = None
        
        while retry_count < config.max_resume_attempts:
            try:
                if operation_id is None:
                    # Initial upload attempt
                    logger.info(f"Starting chunked upload (attempt {retry_count + 1})")
                    operation_id = self.upload_large_file(
                        file_path=file_path,
                        destination=destination,
                        progress_callback=progress_callback
                    )
                else:
                    # Resume attempt
                    logger.info(f"Resuming upload (attempt {retry_count + 1})")
                    operation_id = self.resume_upload(
                        operation_id=operation_id,
                        file_path=file_path,
                        destination=destination,
                        progress_callback=progress_callback
                    )
                
                # Check if completed
                progress = self.get_progress(operation_id)
                
                if progress and progress.is_complete:
                    logger.info(f"Upload completed successfully after {retry_count + 1} attempts")
                    return {
                        'operation_id': operation_id,
                        'uploaded_chunks': progress.chunk_count,
                        'total_bytes': progress.total_bytes,
                        'retry_count': retry_count
                    }
                else:
                    # Upload incomplete but no exception
                    if progress:
                        last_error = f"Upload incomplete: {progress.progress_percent:.1f}%"
                    else:
                        last_error = "Upload incomplete: no progress available"
                    logger.warning(last_error)
                    retry_count += 1
                    time.sleep(config.resume_retry_delay)
                    
            except FileNotFoundError as e:
                # Critical: File was deleted/moved
                logger.error(f"File not found during upload: {e}")
                raise SagaRollbackRequired(
                    reason="FILE_NOT_FOUND",
                    message=f"Source file no longer exists: {file_path}",
                    operation_id=operation_id,
                    retry_count=retry_count
                )
                
            except ChunkMetadataCorruptError as e:
                # Critical: Chunk tracking lost
                logger.error(f"Chunk metadata corrupt: {e}")
                raise SagaRollbackRequired(
                    reason="METADATA_CORRUPT",
                    message="Cannot resume: chunk metadata corrupted",
                    operation_id=operation_id,
                    retry_count=retry_count
                )
                
            except StorageBackendError as e:
                # Retry-able error
                logger.warning(f"Storage backend error (attempt {retry_count + 1}): {e}")
                last_error = str(e)
                retry_count += 1
                time.sleep(config.resume_retry_delay)
                
            except Exception as e:
                # Unknown error
                logger.error(f"Unexpected error during upload (attempt {retry_count + 1}): {e}")
                last_error = str(e)
                retry_count += 1
                time.sleep(config.resume_retry_delay)
        
        # All retry attempts exhausted
        logger.error(f"Upload failed after {retry_count} attempts: {last_error}")
        raise SagaRollbackRequired(
            reason="MAX_RETRIES_EXCEEDED",
            message=f"Upload failed after {retry_count} resume attempts",
            operation_id=operation_id,
            retry_count=retry_count,
            last_error=last_error
        )
    
    def cleanup_chunks_with_verification(
        self,
        operation_id: str
    ) -> Dict[str, Any]:
        """
        Kompensation: Löscht Chunks mit Verifikation
        
        CRITICAL: Muss garantiert durchlaufen, auch bei Fehlern
        
        Strategy:
        1. Liste alle hochgeladenen Chunks
        2. Lösche jeden Chunk einzeln
        3. Verifiziere Löschung
        4. Bei Fehler: Logge, aber fahre fort (Best Effort)
        5. Am Ende: Status-Report
        
        Args:
            operation_id: Operation to clean up
        
        Returns:
            Dict with deleted_count, failed_deletions, success_rate
        
        Raises:
            CompensationError: If cleanup fails catastrophically
        """
        if not operation_id:
            logger.warning("No operation_id for cleanup - nothing to do")
            return {
                'deleted_count': 0,
                'total_chunks': 0,
                'failed_deletions': [],
                'success_rate': 100.0
            }
        
        try:
            # Cancel operation if still running
            if self.cancel_operation(operation_id):
                logger.info(f"Cancelled streaming operation: {operation_id}")
            
            # Get all uploaded chunks
            chunks = self.get_operation_chunks(operation_id)
            total_chunks = len(chunks)
            deleted_count = 0
            failed_deletions = []
            
            logger.info(f"Starting cleanup: {total_chunks} chunks to delete")
            
            # Delete each chunk with verification
            for chunk in chunks:
                try:
                    # Delete chunk from storage
                    self._delete_chunk(chunk.chunk_id)
                    
                    # Verify deletion
                    if not self._chunk_exists(chunk.chunk_id):
                        deleted_count += 1
                        logger.debug(f"Deleted chunk {chunk.chunk_index}: {chunk.chunk_id}")
                    else:
                        failed_deletions.append(chunk.chunk_id)
                        logger.warning(f"Chunk deletion verification failed: {chunk.chunk_id}")
                        
                except Exception as e:
                    # Log but continue (Best Effort)
                    failed_deletions.append(chunk.chunk_id)
                    logger.error(f"Failed to delete chunk {chunk.chunk_id}: {e}")
            
            # Cleanup operation metadata
            with self._lock:
                if operation_id in self._operations:
                    del self._operations[operation_id]
                if operation_id in self._chunks:
                    del self._chunks[operation_id]
            
            # Status Report
            success_rate = (deleted_count / total_chunks * 100) if total_chunks > 0 else 100.0
            logger.info(
                f"Cleanup complete: {deleted_count}/{total_chunks} chunks deleted "
                f"({success_rate:.1f}% success)"
            )
            
            if failed_deletions:
                logger.warning(
                    f"Failed to delete {len(failed_deletions)} chunks: {failed_deletions[:5]}..."
                )
                # Store for manual cleanup
                self._store_failed_deletions(operation_id, failed_deletions)
            
            return {
                'deleted_count': deleted_count,
                'total_chunks': total_chunks,
                'failed_deletions': failed_deletions,
                'success_rate': success_rate
            }
            
        except Exception as e:
            # Critical: Cleanup itself failed
            logger.critical(f"Cleanup failed catastrophically: {e}")
            # Store for manual intervention
            self._store_critical_cleanup_failure(operation_id, str(e))
            raise CompensationError(f"Chunk cleanup failed: {e}")
    
    def verify_integrity(
        self,
        operation_id: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Verifiziert Datei-Integrität nach Upload/Resume
        
        Checks:
        1. Alle Chunks vorhanden
        2. Chunk-Hashes korrekt
        3. Gesamt-Hash stimmt mit Original überein
        4. Datei-Größe korrekt
        
        Args:
            operation_id: Operation to verify
            file_path: Original file path
        
        Returns:
            Dict with verified, hash, size, chunk_count
        
        Raises:
            SagaRollbackRequired: Bei Fehler in Integrity Check
        """
        # Get upload metadata
        progress = self.get_progress(operation_id)
        chunks = self.get_operation_chunks(operation_id)
        
        if not progress:
            raise SagaRollbackRequired(
                reason="OPERATION_NOT_FOUND",
                message=f"Operation not found: {operation_id}",
                operation_id=operation_id
            )
        
        # Check 1: All chunks present
        expected_chunks = progress.chunk_count
        actual_chunks = len(chunks)
        
        if actual_chunks != expected_chunks:
            logger.error(
                f"Chunk count mismatch: expected {expected_chunks}, got {actual_chunks}"
            )
            raise SagaRollbackRequired(
                reason="CHUNK_COUNT_MISMATCH",
                message=f"Missing chunks: {expected_chunks - actual_chunks}",
                operation_id=operation_id
            )
        
        # Check 2: Verify file exists
        if not os.path.exists(file_path):
            raise SagaRollbackRequired(
                reason="FILE_NOT_FOUND",
                message=f"Original file not found: {file_path}",
                operation_id=operation_id
            )
        
        # Check 3: Calculate original file hash
        original_hash = self._calculate_file_hash(file_path)
        
        # Check 4: Calculate uploaded chunks hash
        uploaded_hash = self._calculate_chunks_hash([c.chunk_hash for c in chunks])
        
        if original_hash != uploaded_hash:
            logger.error(
                f"Hash mismatch: original={original_hash}, uploaded={uploaded_hash}"
            )
            raise SagaRollbackRequired(
                reason="HASH_MISMATCH",
                message="File was modified during upload or chunks corrupted",
                operation_id=operation_id
            )
        
        # Check 5: File size
        original_size = os.path.getsize(file_path)
        uploaded_size = sum(c.chunk_size for c in chunks)
        
        if original_size != uploaded_size:
            logger.error(
                f"Size mismatch: original={original_size}, uploaded={uploaded_size}"
            )
            raise SagaRollbackRequired(
                reason="SIZE_MISMATCH",
                message=f"Size difference: {original_size - uploaded_size} bytes",
                operation_id=operation_id
            )
        
        logger.info("✅ Integrity verification passed")
        return {
            'verified': True,
            'hash': original_hash,
            'size': original_size,
            'chunk_count': actual_chunks
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _delete_chunk(self, chunk_id: str) -> None:
        """Delete a chunk from storage (simulate)"""
        # In production: Delete from actual storage backend
        logger.debug(f"Deleting chunk: {chunk_id}")
    
    def _chunk_exists(self, chunk_id: str) -> bool:
        """Check if chunk exists (simulate)"""
        # In production: Check actual storage backend
        return False  # Assume deleted successfully
    
    def _store_failed_deletions(self, operation_id: str, failed_chunks: List[str]) -> None:
        """Store failed deletions for manual cleanup"""
        cleanup_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation_id': operation_id,
            'failed_chunks': failed_chunks,
            'status': 'PENDING_MANUAL_CLEANUP'
        }
        
        # Persist to database or log file
        log_file = 'failed_cleanups.json'
        try:
            with open(log_file, 'a') as f:
                import json
                f.write(json.dumps(cleanup_log) + '\n')
            logger.info(f"Stored {len(failed_chunks)} failed deletions for manual cleanup")
        except Exception as e:
            logger.error(f"Failed to store cleanup log: {e}")
    
    def _store_critical_cleanup_failure(self, operation_id: str, error: str) -> None:
        """Store critical cleanup failure for manual intervention"""
        failure_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation_id': operation_id,
            'error': error,
            'status': 'CRITICAL_FAILURE'
        }
        
        log_file = 'critical_failures.json'
        try:
            with open(log_file, 'a') as f:
                import json
                f.write(json.dumps(failure_record) + '\n')
            logger.critical(f"Stored critical failure for operation: {operation_id}")
        except Exception as e:
            logger.critical(f"Failed to store critical failure: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of entire file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _calculate_chunks_hash(self, chunk_hashes: List[str]) -> str:
        """Calculate combined hash from chunk hashes"""
        combined = "".join(chunk_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def pause_operation(self, operation_id: str) -> bool:
        """Pause an operation"""
        with self._lock:
            if operation_id in self._operations:
                progress = self._operations[operation_id]
                if progress.status == StreamingStatus.IN_PROGRESS:
                    progress.status = StreamingStatus.PAUSED
                    progress.updated_at = datetime.utcnow()
                    logger.info(f"Operation paused: {operation_id}")
                    return True
        return False
    
    def get_operation_chunks(self, operation_id: str) -> List[ChunkMetadata]:
        """Get uploaded chunks for an operation"""
        with self._lock:
            return self._chunks.get(operation_id, []).copy()
    
    # ========================================================================
    # Streaming Processing (for large embeddings)
    # ========================================================================
    
    def stream_to_vector_db(
        self,
        file_path: str,
        embedding_function: Callable[[str], List[float]],
        chunk_text_size: int = 1000,
        progress_callback: Optional[Callable[[StreamingProgress], None]] = None
    ) -> str:
        """
        Stream large document to vector DB in chunks.
        
        For large PDFs with embeddings, process in chunks to avoid memory issues.
        
        Args:
            file_path: Path to document
            embedding_function: Function to generate embeddings
            chunk_text_size: Size of text chunks (characters)
            progress_callback: Callback for progress updates
        
        Returns:
            Operation ID
        """
        file_size = os.path.getsize(file_path)
        
        # Create operation
        operation_id = f"embed-{uuid.uuid4().hex[:12]}"
        progress = StreamingProgress(
            operation_id=operation_id,
            operation_type=StreamingOperation.PROCESSING,
            status=StreamingStatus.IN_PROGRESS,
            total_bytes=file_size,
            transferred_bytes=0,
            chunk_count=0,  # Unknown until we process
            current_chunk=0,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with self._lock:
            self._operations[operation_id] = progress
        
        logger.info(f"Starting embedding stream: {file_path} ({file_size/1024/1024:.1f}MB)")
        
        try:
            # Read file in chunks and generate embeddings
            # (Simplified - in production would use PDF parser)
            with open(file_path, 'rb') as f:
                chunk_index = 0
                while True:
                    # Read chunk
                    chunk_data = f.read(self.chunk_size)
                    if not chunk_data:
                        break
                    
                    # Process chunk (simulate embedding generation)
                    # In production: extract text, generate embeddings, insert to vector DB
                    time.sleep(0.01)  # Simulate processing
                    
                    # Update progress
                    with self._lock:
                        progress.transferred_bytes += len(chunk_data)
                        progress.current_chunk = chunk_index + 1
                        progress.updated_at = datetime.utcnow()
                    
                    if progress_callback:
                        progress_callback(progress)
                    
                    chunk_index += 1
                    logger.debug(f"Processed embedding chunk {chunk_index}")
            
            # Mark complete
            with self._lock:
                progress.chunk_count = chunk_index
                progress.status = StreamingStatus.COMPLETED
                progress.completed_at = datetime.utcnow()
                progress.updated_at = datetime.utcnow()
            
            if progress_callback:
                progress_callback(progress)
            
            logger.info(f"Embedding stream complete: {operation_id} ({chunk_index} chunks)")
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Embedding stream failed: {e}")
            with self._lock:
                progress.status = StreamingStatus.FAILED
                progress.error_message = str(e)
                progress.updated_at = datetime.utcnow()
            
            if progress_callback:
                progress_callback(progress)
            
            raise
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    def cleanup_completed_operations(self, max_age_seconds: int = 3600):
        """Remove completed operations older than specified age"""
        now = datetime.utcnow()
        removed = 0
        
        with self._lock:
            to_remove = []
            for op_id, progress in self._operations.items():
                if progress.status in [StreamingStatus.COMPLETED, StreamingStatus.FAILED, StreamingStatus.CANCELLED]:
                    if progress.completed_at:
                        age = (now - progress.completed_at).total_seconds()
                        if age > max_age_seconds:
                            to_remove.append(op_id)
            
            for op_id in to_remove:
                del self._operations[op_id]
                if op_id in self._chunks:
                    del self._chunks[op_id]
                removed += 1
        
        logger.info(f"Cleaned up {removed} old operations")
        return removed


# ============================================================================
# Factory Function
# ============================================================================

def create_streaming_manager(
    storage_backend=None,
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> StreamingManager:
    """
    Factory function to create a StreamingManager.
    
    Args:
        storage_backend: Backend for file storage
        chunk_size: Size of each chunk in bytes
    
    Returns:
        Configured StreamingManager
    """
    return StreamingManager(
        storage_backend=storage_backend,
        chunk_size=chunk_size
    )


# ============================================================================
# Utility Functions
# ============================================================================

def calculate_optimal_chunk_size(
    file_size: int,
    available_memory: int,
    network_speed_mbps: float = 100.0
) -> int:
    """
    Calculate optimal chunk size based on constraints.
    
    Args:
        file_size: Total file size in bytes
        available_memory: Available memory in bytes
        network_speed_mbps: Network speed in Mbps
    
    Returns:
        Optimal chunk size in bytes
    """
    # Start with default
    chunk_size = DEFAULT_CHUNK_SIZE
    
    # Adjust for available memory (use max 10% of available)
    max_memory_chunk = int(available_memory * 0.1)
    chunk_size = min(chunk_size, max_memory_chunk)
    
    # Adjust for network speed (larger chunks for faster networks)
    if network_speed_mbps > 500:
        chunk_size = max(chunk_size, LARGE_CHUNK_SIZE)
    elif network_speed_mbps < 10:
        chunk_size = min(chunk_size, SMALL_CHUNK_SIZE)
    
    # Ensure reasonable bounds
    chunk_size = max(SMALL_CHUNK_SIZE, min(chunk_size, 50 * 1024 * 1024))  # 1-50 MB
    
    return chunk_size


def format_bytes(bytes_count: int) -> str:
    """Format bytes as human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"
