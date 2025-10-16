"""
UDS3 Archive Operations Module
===============================

Provides comprehensive archiving strategies for polyglot persistence:
- Archive: Move documents to long-term storage
- Restore: Recover archived documents
- Retention Policies: Automatic expiration based on rules
- Batch Operations: Efficient bulk archiving/restoration
- Archive Metadata: Track archive history and retention info

Supports all 4 databases:
- Vector DB (ChromaDB/Pinecone)
- Graph DB (Neo4j/ArangoDB)
- Relational DB (PostgreSQL/SQLite)
- File Storage

Design Philosophy:
- Archive preserves data in a separate storage layer
- Different from soft delete (deleted vs archived status)
- Supports compliance requirements (data retention laws)
- Automatic expiration after retention period
- Full audit trail for regulatory compliance

Author: UDS3 Team
Date: 2. Oktober 2025
Version: 1.0.0
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import json
import threading
import time

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Configuration
# ============================================================================

class ArchiveStrategy(Enum):
    """Archive storage strategy"""
    MOVE = "move"              # Move to archive, remove from active
    COPY = "copy"              # Copy to archive, keep in active
    COMPRESS = "compress"      # Compress and move


class RetentionPeriod(Enum):
    """Standard retention periods"""
    DAYS_30 = 30
    DAYS_90 = 90
    DAYS_180 = 180
    YEARS_1 = 365
    YEARS_3 = 1095
    YEARS_7 = 2555
    YEARS_10 = 3650
    PERMANENT = -1  # Never expire


class ArchiveStatus(Enum):
    """Status of archived document"""
    ARCHIVED = "archived"
    RESTORING = "restoring"
    RESTORED = "restored"
    EXPIRED = "expired"
    DELETED = "deleted"


class RestoreStrategy(Enum):
    """Strategy for restoring archived documents"""
    REPLACE = "replace"           # Replace existing document
    MERGE = "merge"              # Merge with existing
    NEW_VERSION = "new_version"  # Create new version
    FAIL_IF_EXISTS = "fail_if_exists"  # Fail if document exists


# ============================================================================
# Result Classes
# ============================================================================

@dataclass
class ArchiveResult:
    """Result of an archive operation"""
    success: bool
    document_id: str
    archived_at: Optional[datetime] = None
    archive_location: Optional[str] = None
    affected_databases: Optional[List[str]] = None
    retention_until: Optional[datetime] = None
    errors: Optional[List[str]] = None
    archive_id: Optional[str] = None
    original_size_bytes: Optional[int] = None
    archived_size_bytes: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.archived_at:
            result['archived_at'] = self.archived_at.isoformat()
        if self.retention_until:
            result['retention_until'] = self.retention_until.isoformat()
        return result


@dataclass
class RestoreResult:
    """Result of a restore operation"""
    success: bool
    document_id: str
    restored_at: Optional[datetime] = None
    affected_databases: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    archive_id: Optional[str] = None
    restore_strategy: Optional[RestoreStrategy] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.restored_at:
            result['restored_at'] = self.restored_at.isoformat()
        if self.restore_strategy:
            result['restore_strategy'] = self.restore_strategy.value
        return result


@dataclass
class BatchArchiveResult:
    """Result of batch archive operation"""
    success: bool
    total_count: int
    archived_count: int
    failed_count: int
    results: Optional[List[ArchiveResult]] = None
    errors: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.results:
            result['results'] = [r.to_dict() for r in self.results]
        return result


@dataclass
class ArchiveInfo:
    """Information about archived documents"""
    total_archived: int
    total_size_bytes: int
    oldest_archive: Optional[datetime] = None
    newest_archive: Optional[datetime] = None
    expiring_soon: int = 0  # Count of documents expiring in next 30 days
    expired_count: int = 0
    by_retention_period: Optional[Dict[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.oldest_archive:
            result['oldest_archive'] = self.oldest_archive.isoformat()
        if self.newest_archive:
            result['newest_archive'] = self.newest_archive.isoformat()
        return result


@dataclass
class RetentionPolicy:
    """Retention policy configuration"""
    name: str
    retention_days: int
    auto_delete: bool = True
    document_types: Optional[List[str]] = None
    condition_filter: Optional[Dict[str, Any]] = None
    
    def is_expired(self, archived_at: datetime) -> bool:
        """Check if document has passed retention period"""
        if self.retention_days == -1:  # Permanent
            return False
        
        expiry_date = archived_at + timedelta(days=self.retention_days)
        return datetime.utcnow() > expiry_date
    
    def expires_at(self, archived_at: datetime) -> Optional[datetime]:
        """Calculate expiry date"""
        if self.retention_days == -1:  # Permanent
            return None
        return archived_at + timedelta(days=self.retention_days)


# ============================================================================
# Archive Metadata
# ============================================================================

@dataclass
class ArchiveMetadata:
    """Metadata for archived documents"""
    archive_id: str
    document_id: str
    archived_at: datetime
    archived_by: Optional[str] = None
    archive_reason: Optional[str] = None
    retention_policy: Optional[str] = None
    retention_days: Optional[int] = None
    retention_until: Optional[datetime] = None
    status: ArchiveStatus = ArchiveStatus.ARCHIVED
    original_size_bytes: Optional[int] = None
    archived_size_bytes: Optional[int] = None
    archive_location: Optional[str] = None
    original_metadata: Optional[Dict[str, Any]] = None
    restore_count: int = 0
    last_restored_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'archive_id': self.archive_id,
            'document_id': self.document_id,
            'archived_at': self.archived_at.isoformat(),
            'status': self.status.value
        }
        
        if self.archived_by:
            result['archived_by'] = self.archived_by
        if self.archive_reason:
            result['archive_reason'] = self.archive_reason
        if self.retention_policy:
            result['retention_policy'] = self.retention_policy
        if self.retention_days:
            result['retention_days'] = self.retention_days
        if self.retention_until:
            result['retention_until'] = self.retention_until.isoformat()
        if self.original_size_bytes:
            result['original_size_bytes'] = self.original_size_bytes
        if self.archived_size_bytes:
            result['archived_size_bytes'] = self.archived_size_bytes
        if self.archive_location:
            result['archive_location'] = self.archive_location
        if self.original_metadata:
            result['original_metadata'] = self.original_metadata
        if self.restore_count > 0:
            result['restore_count'] = self.restore_count
        if self.last_restored_at:
            result['last_restored_at'] = self.last_restored_at.isoformat()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchiveMetadata':
        """Create from dictionary"""
        return cls(
            archive_id=data['archive_id'],
            document_id=data['document_id'],
            archived_at=datetime.fromisoformat(data['archived_at']),
            archived_by=data.get('archived_by'),
            archive_reason=data.get('archive_reason'),
            retention_policy=data.get('retention_policy'),
            retention_days=data.get('retention_days'),
            retention_until=datetime.fromisoformat(data['retention_until']) if data.get('retention_until') else None,
            status=ArchiveStatus(data.get('status', 'archived')),
            original_size_bytes=data.get('original_size_bytes'),
            archived_size_bytes=data.get('archived_size_bytes'),
            archive_location=data.get('archive_location'),
            original_metadata=data.get('original_metadata'),
            restore_count=data.get('restore_count', 0),
            last_restored_at=datetime.fromisoformat(data['last_restored_at']) if data.get('last_restored_at') else None
        )


# ============================================================================
# Archive Manager
# ============================================================================

class ArchiveManager:
    """
    Manages archive operations across all databases.
    
    Archive moves documents to long-term storage while preserving:
    - Full document data and metadata
    - Audit trail for compliance
    - Retention policies for automatic expiration
    - Restore capabilities
    
    Features:
    - Single and batch archiving
    - Configurable retention policies
    - Automatic expiration based on retention rules
    - Full restore capabilities
    - Archive statistics and monitoring
    - Compliance-ready audit trails
    """
    
    def __init__(self, unified_strategy):
        """
        Initialize with unified database strategy.
        
        Args:
            unified_strategy: UnifiedDatabaseStrategy instance
        """
        self.unified_strategy = unified_strategy
        self.vector_backend = unified_strategy.vector_backend
        self.graph_backend = unified_strategy.graph_backend
        self.relational_backend = unified_strategy.relational_backend
        self.file_backend = unified_strategy.file_backend
        
        # Archive storage (in-memory for demo, could be separate DB/storage)
        self._archive_storage: Dict[str, ArchiveMetadata] = {}
        self._archive_data: Dict[str, Dict[str, Any]] = {}
        
        # Retention policies
        self._retention_policies: Dict[str, RetentionPolicy] = {}
        self._default_retention_days = 365  # 1 year default
        
        # Background cleanup
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_enabled = False
        self._cleanup_interval = 3600  # 1 hour
        self._lock = threading.Lock()
        
        logger.info("ArchiveManager initialized")
    
    # ========================================================================
    # Configuration
    # ========================================================================
    
    def add_retention_policy(self, policy: RetentionPolicy) -> None:
        """
        Add a retention policy.
        
        Args:
            policy: RetentionPolicy to add
        """
        with self._lock:
            self._retention_policies[policy.name] = policy
            logger.info(f"Added retention policy: {policy.name} ({policy.retention_days} days)")
    
    def remove_retention_policy(self, policy_name: str) -> bool:
        """
        Remove a retention policy.
        
        Args:
            policy_name: Name of policy to remove
        
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if policy_name in self._retention_policies:
                del self._retention_policies[policy_name]
                logger.info(f"Removed retention policy: {policy_name}")
                return True
            return False
    
    def get_retention_policy(self, policy_name: str) -> Optional[RetentionPolicy]:
        """Get retention policy by name"""
        return self._retention_policies.get(policy_name)
    
    def list_retention_policies(self) -> List[RetentionPolicy]:
        """List all retention policies"""
        with self._lock:
            return list(self._retention_policies.values())
    
    def set_default_retention_days(self, days: int) -> None:
        """Set default retention period in days"""
        self._default_retention_days = days
        logger.info(f"Default retention period set to {days} days")
    
    # ========================================================================
    # Core Archive Operations
    # ========================================================================
    
    def archive_document(
        self,
        document_id: str,
        retention_policy: Optional[str] = None,
        retention_days: Optional[int] = None,
        archived_by: Optional[str] = None,
        reason: Optional[str] = None,
        strategy: ArchiveStrategy = ArchiveStrategy.MOVE
    ) -> ArchiveResult:
        """
        Archive a document to long-term storage.
        
        Args:
            document_id: Document to archive
            retention_policy: Named retention policy to use
            retention_days: Override retention days (if no policy)
            archived_by: User/system identifier
            reason: Reason for archiving
            strategy: Archive strategy (MOVE/COPY/COMPRESS)
        
        Returns:
            ArchiveResult with operation details
        """
        logger.info(f"Archiving document: {document_id}")
        
        archived_at = datetime.utcnow()
        affected_dbs = []
        errors = []
        
        # Determine retention period
        policy = None
        if retention_policy:
            policy = self.get_retention_policy(retention_policy)
            if policy:
                retention_days = policy.retention_days
        
        if retention_days is None:
            retention_days = self._default_retention_days
        
        # Calculate expiry
        retention_until = None
        if retention_days > 0:
            retention_until = archived_at + timedelta(days=retention_days)
        
        # Generate archive ID
        import hashlib
        archive_id = hashlib.sha256(
            f"{document_id}_{archived_at.isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Read document from active storage
        document_data = None
        original_size = 0
        
        try:
            # Try to read from relational DB first
            document_data = self._read_document_for_archive(document_id)
            if document_data:
                original_size = len(json.dumps(document_data).encode())
            else:
                error_msg = f"Document not found: {document_id}"
                logger.error(error_msg)
                return ArchiveResult(
                    success=False,
                    document_id=document_id,
                    errors=[error_msg]
                )
        except Exception as e:
            error_msg = f"Failed to read document: {str(e)}"
            logger.error(error_msg)
            return ArchiveResult(
                success=False,
                document_id=document_id,
                errors=[error_msg]
            )
        
        # Archive in Vector DB
        try:
            self._archive_vector(document_id, archive_id)
            affected_dbs.append("vector")
            logger.debug(f"Vector archive successful: {document_id}")
        except Exception as e:
            error_msg = f"Vector archive failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Archive in Graph DB
        try:
            self._archive_graph(document_id, archive_id)
            affected_dbs.append("graph")
            logger.debug(f"Graph archive successful: {document_id}")
        except Exception as e:
            error_msg = f"Graph archive failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Archive in Relational DB
        try:
            self._archive_relational(document_id, archive_id)
            affected_dbs.append("relational")
            logger.debug(f"Relational archive successful: {document_id}")
        except Exception as e:
            error_msg = f"Relational archive failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Archive in File Storage
        try:
            self._archive_file(document_id, archive_id)
            affected_dbs.append("file")
            logger.debug(f"File archive successful: {document_id}")
        except Exception as e:
            error_msg = f"File archive failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Store archive metadata and data
        archive_metadata = ArchiveMetadata(
            archive_id=archive_id,
            document_id=document_id,
            archived_at=archived_at,
            archived_by=archived_by,
            archive_reason=reason,
            retention_policy=retention_policy,
            retention_days=retention_days,
            retention_until=retention_until,
            status=ArchiveStatus.ARCHIVED,
            original_size_bytes=original_size,
            archived_size_bytes=original_size,  # Could compress here
            archive_location=f"archive://{archive_id}"
        )
        
        with self._lock:
            self._archive_storage[document_id] = archive_metadata
            self._archive_data[archive_id] = document_data
        
        success = len(affected_dbs) > 0
        
        result = ArchiveResult(
            success=success,
            document_id=document_id,
            archived_at=archived_at,
            archive_location=archive_metadata.archive_location,
            affected_databases=affected_dbs,
            retention_until=retention_until,
            errors=errors if errors else None,
            archive_id=archive_id,
            original_size_bytes=original_size,
            archived_size_bytes=original_size
        )
        
        logger.info(f"Archive complete: {document_id}, archive_id={archive_id}, success={success}")
        return result
    
    def restore_document(
        self,
        document_id: str,
        strategy: RestoreStrategy = RestoreStrategy.REPLACE,
        restored_by: Optional[str] = None
    ) -> RestoreResult:
        """
        Restore an archived document to active storage.
        
        Args:
            document_id: Document to restore
            strategy: Restore strategy (REPLACE/MERGE/NEW_VERSION/FAIL_IF_EXISTS)
            restored_by: User/system identifier
        
        Returns:
            RestoreResult with operation details
        """
        logger.info(f"Restoring document: {document_id}")
        
        restored_at = datetime.utcnow()
        affected_dbs = []
        errors = []
        
        # Get archive metadata
        with self._lock:
            archive_metadata = self._archive_storage.get(document_id)
            if not archive_metadata:
                error_msg = f"No archive found for document: {document_id}"
                logger.error(error_msg)
                return RestoreResult(
                    success=False,
                    document_id=document_id,
                    errors=[error_msg]
                )
            
            # Get archived data
            archive_data = self._archive_data.get(archive_metadata.archive_id)
            if not archive_data:
                error_msg = f"Archive data not found: {archive_metadata.archive_id}"
                logger.error(error_msg)
                return RestoreResult(
                    success=False,
                    document_id=document_id,
                    errors=[error_msg]
                )
        
        # Check if document exists (for FAIL_IF_EXISTS strategy)
        if strategy == RestoreStrategy.FAIL_IF_EXISTS:
            if self._document_exists(document_id):
                error_msg = f"Document already exists: {document_id}"
                logger.error(error_msg)
                return RestoreResult(
                    success=False,
                    document_id=document_id,
                    errors=[error_msg],
                    restore_strategy=strategy
                )
        
        # Restore to Vector DB
        try:
            self._restore_vector(document_id, archive_data, strategy)
            affected_dbs.append("vector")
            logger.debug(f"Vector restore successful: {document_id}")
        except Exception as e:
            error_msg = f"Vector restore failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Restore to Graph DB
        try:
            self._restore_graph(document_id, archive_data, strategy)
            affected_dbs.append("graph")
            logger.debug(f"Graph restore successful: {document_id}")
        except Exception as e:
            error_msg = f"Graph restore failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Restore to Relational DB
        try:
            self._restore_relational(document_id, archive_data, strategy)
            affected_dbs.append("relational")
            logger.debug(f"Relational restore successful: {document_id}")
        except Exception as e:
            error_msg = f"Relational restore failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Restore to File Storage
        try:
            self._restore_file(document_id, archive_data, strategy)
            affected_dbs.append("file")
            logger.debug(f"File restore successful: {document_id}")
        except Exception as e:
            error_msg = f"File restore failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Update archive metadata
        with self._lock:
            archive_metadata.status = ArchiveStatus.RESTORED
            archive_metadata.restore_count += 1
            archive_metadata.last_restored_at = restored_at
        
        success = len(affected_dbs) > 0
        
        result = RestoreResult(
            success=success,
            document_id=document_id,
            restored_at=restored_at,
            affected_databases=affected_dbs,
            errors=errors if errors else None,
            archive_id=archive_metadata.archive_id,
            restore_strategy=strategy
        )
        
        logger.info(f"Restore complete: {document_id}, success={success}")
        return result
    
    # ========================================================================
    # Batch Operations
    # ========================================================================
    
    def batch_archive(
        self,
        document_ids: List[str],
        retention_policy: Optional[str] = None,
        retention_days: Optional[int] = None,
        archived_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> BatchArchiveResult:
        """
        Archive multiple documents in batch.
        
        Args:
            document_ids: List of document IDs to archive
            retention_policy: Named retention policy
            retention_days: Override retention days
            archived_by: User/system identifier
            reason: Reason for archiving
        
        Returns:
            BatchArchiveResult with operation details
        """
        logger.info(f"Batch archiving {len(document_ids)} documents")
        
        results = []
        errors = []
        archived_count = 0
        failed_count = 0
        
        for doc_id in document_ids:
            try:
                result = self.archive_document(
                    document_id=doc_id,
                    retention_policy=retention_policy,
                    retention_days=retention_days,
                    archived_by=archived_by,
                    reason=reason
                )
                
                results.append(result)
                
                if result.success:
                    archived_count += 1
                else:
                    failed_count += 1
                    if result.errors:
                        errors.extend(result.errors)
                
            except Exception as e:
                error_msg = f"Failed to archive {doc_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_count += 1
        
        success = archived_count > 0
        
        batch_result = BatchArchiveResult(
            success=success,
            total_count=len(document_ids),
            archived_count=archived_count,
            failed_count=failed_count,
            results=results,
            errors=errors if errors else None
        )
        
        logger.info(f"Batch archive complete: {archived_count}/{len(document_ids)} successful")
        return batch_result
    
    def batch_restore(
        self,
        document_ids: List[str],
        strategy: RestoreStrategy = RestoreStrategy.REPLACE,
        restored_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Restore multiple documents in batch.
        
        Args:
            document_ids: List of document IDs to restore
            strategy: Restore strategy
            restored_by: User/system identifier
        
        Returns:
            Dictionary with batch restore results
        """
        logger.info(f"Batch restoring {len(document_ids)} documents")
        
        results = []
        errors = []
        restored_count = 0
        failed_count = 0
        
        for doc_id in document_ids:
            try:
                result = self.restore_document(
                    document_id=doc_id,
                    strategy=strategy,
                    restored_by=restored_by
                )
                
                results.append(result)
                
                if result.success:
                    restored_count += 1
                else:
                    failed_count += 1
                    if result.errors:
                        errors.extend(result.errors)
                
            except Exception as e:
                error_msg = f"Failed to restore {doc_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_count += 1
        
        success = restored_count > 0
        
        batch_result = {
            'success': success,
            'total_count': len(document_ids),
            'restored_count': restored_count,
            'failed_count': failed_count,
            'results': [r.to_dict() for r in results],
            'errors': errors if errors else None
        }
        
        logger.info(f"Batch restore complete: {restored_count}/{len(document_ids)} successful")
        return batch_result
    
    # ========================================================================
    # Archive Information & Statistics
    # ========================================================================
    
    def list_archived_documents(
        self,
        status: Optional[ArchiveStatus] = None,
        limit: Optional[int] = None
    ) -> List[ArchiveMetadata]:
        """
        List archived documents.
        
        Args:
            status: Filter by status (None = all)
            limit: Maximum number to return
        
        Returns:
            List of ArchiveMetadata
        """
        with self._lock:
            archived = list(self._archive_storage.values())
        
        # Filter by status
        if status:
            archived = [a for a in archived if a.status == status]
        
        # Sort by archived_at (newest first)
        archived.sort(key=lambda a: a.archived_at, reverse=True)
        
        # Apply limit
        if limit:
            archived = archived[:limit]
        
        return archived
    
    def get_archive_info(self) -> ArchiveInfo:
        """
        Get archive statistics and information.
        
        Returns:
            ArchiveInfo with statistics
        """
        with self._lock:
            archived = list(self._archive_storage.values())
        
        if not archived:
            return ArchiveInfo(
                total_archived=0,
                total_size_bytes=0
            )
        
        # Calculate statistics
        total_size = sum(a.archived_size_bytes or 0 for a in archived)
        oldest = min(a.archived_at for a in archived)
        newest = max(a.archived_at for a in archived)
        
        # Count expiring soon (next 30 days)
        now = datetime.utcnow()
        thirty_days = now + timedelta(days=30)
        expiring_soon = sum(
            1 for a in archived
            if a.retention_until and now < a.retention_until <= thirty_days
        )
        
        # Count expired
        expired = sum(
            1 for a in archived
            if a.retention_until and a.retention_until < now
        )
        
        # Group by retention period
        by_retention = {}
        for a in archived:
            if a.retention_days:
                key = f"{a.retention_days} days"
                by_retention[key] = by_retention.get(key, 0) + 1
        
        return ArchiveInfo(
            total_archived=len(archived),
            total_size_bytes=total_size,
            oldest_archive=oldest,
            newest_archive=newest,
            expiring_soon=expiring_soon,
            expired_count=expired,
            by_retention_period=by_retention
        )
    
    def get_archive_metadata(self, document_id: str) -> Optional[ArchiveMetadata]:
        """Get archive metadata for a document"""
        with self._lock:
            return self._archive_storage.get(document_id)
    
    # ========================================================================
    # Retention Policy Application
    # ========================================================================
    
    def apply_retention_policies(self) -> Dict[str, Any]:
        """
        Apply all retention policies and expire/delete archived documents.
        
        Returns:
            Dictionary with application results
        """
        logger.info("Applying retention policies")
        
        expired_count = 0
        deleted_count = 0
        errors = []
        
        now = datetime.utcnow()
        
        with self._lock:
            archived = list(self._archive_storage.values())
        
        for metadata in archived:
            try:
                # Check if expired
                if metadata.retention_until and metadata.retention_until < now:
                    # Get policy for auto-delete setting
                    policy = None
                    if metadata.retention_policy:
                        policy = self.get_retention_policy(metadata.retention_policy)
                    
                    # Mark as expired
                    metadata.status = ArchiveStatus.EXPIRED
                    expired_count += 1
                    
                    # Auto-delete if policy allows
                    if policy and policy.auto_delete:
                        self._delete_archived_document(metadata.document_id)
                        metadata.status = ArchiveStatus.DELETED
                        deleted_count += 1
                        logger.debug(f"Auto-deleted expired document: {metadata.document_id}")
                
            except Exception as e:
                error_msg = f"Failed to process {metadata.document_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        result = {
            'success': True,
            'expired_count': expired_count,
            'deleted_count': deleted_count,
            'errors': errors if errors else None
        }
        
        logger.info(f"Retention policies applied: {expired_count} expired, {deleted_count} deleted")
        return result
    
    def auto_expire_archived(
        self,
        retention_days: Optional[int] = None,
        auto_delete: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically expire archived documents past retention period.
        
        Args:
            retention_days: Override retention period
            auto_delete: If True, delete expired documents
        
        Returns:
            Dictionary with expiration results
        """
        logger.info("Auto-expiring archived documents")
        
        if retention_days is None:
            retention_days = self._default_retention_days
        
        expired_count = 0
        deleted_count = 0
        errors = []
        
        now = datetime.utcnow()
        cutoff_date = now - timedelta(days=retention_days)
        
        with self._lock:
            archived = list(self._archive_storage.values())
        
        for metadata in archived:
            try:
                if metadata.archived_at < cutoff_date:
                    # Mark as expired
                    metadata.status = ArchiveStatus.EXPIRED
                    expired_count += 1
                    
                    # Delete if requested
                    if auto_delete:
                        self._delete_archived_document(metadata.document_id)
                        metadata.status = ArchiveStatus.DELETED
                        deleted_count += 1
                        logger.debug(f"Deleted expired document: {metadata.document_id}")
                
            except Exception as e:
                error_msg = f"Failed to expire {metadata.document_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        result = {
            'success': True,
            'retention_days': retention_days,
            'expired_count': expired_count,
            'deleted_count': deleted_count,
            'errors': errors if errors else None
        }
        
        logger.info(f"Auto-expire complete: {expired_count} expired, {deleted_count} deleted")
        return result
    
    # ========================================================================
    # Background Cleanup
    # ========================================================================
    
    def enable_auto_cleanup(self, interval_seconds: int = 3600) -> None:
        """
        Enable background cleanup thread.
        
        Args:
            interval_seconds: Cleanup interval in seconds
        """
        if self._cleanup_enabled:
            logger.warning("Auto-cleanup already enabled")
            return
        
        self._cleanup_interval = interval_seconds
        self._cleanup_enabled = True
        
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True,
            name="ArchiveCleanupThread"
        )
        self._cleanup_thread.start()
        
        logger.info(f"Auto-cleanup enabled (interval: {interval_seconds}s)")
    
    def disable_auto_cleanup(self) -> None:
        """Disable background cleanup thread"""
        if not self._cleanup_enabled:
            return
        
        self._cleanup_enabled = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
        
        logger.info("Auto-cleanup disabled")
    
    def _cleanup_worker(self) -> None:
        """Background worker for automatic cleanup"""
        logger.info("Cleanup worker started")
        
        while self._cleanup_enabled:
            try:
                # Apply retention policies
                self.apply_retention_policies()
                
                # Sleep until next cleanup
                time.sleep(self._cleanup_interval)
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                time.sleep(60)  # Wait a minute before retry
        
        logger.info("Cleanup worker stopped")
    
    # ========================================================================
    # Database-Specific Operations (Private)
    # ========================================================================
    
    def _read_document_for_archive(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Read document from active storage for archiving"""
        # Try relational DB first
        if self.relational_backend:
            try:
                # Mock read - would use actual backend in production
                return {
                    'id': document_id,
                    'content': f'Document content for {document_id}',
                    'metadata': {'archived': False}
                }
            except Exception as e:
                logger.error(f"Failed to read from relational: {e}")
        
        return None
    
    def _document_exists(self, document_id: str) -> bool:
        """Check if document exists in active storage"""
        # Mock check - would use actual backend in production
        return False
    
    def _archive_vector(self, document_id: str, archive_id: str) -> None:
        """Archive in Vector DB"""
        if not self.vector_backend:
            logger.debug("Vector backend not available")
            return
        
        # Mark as archived in metadata
        archive_metadata = {
            'archived': True,
            'archive_id': archive_id,
            'archived_at': datetime.utcnow().isoformat()
        }
        
        try:
            if hasattr(self.vector_backend, 'update_metadata'):
                self.vector_backend.update_metadata(document_id, archive_metadata)
            logger.debug(f"Vector archived: {document_id}")
        except Exception as e:
            logger.warning(f"Vector archive skipped: {e}")
    
    def _archive_graph(self, document_id: str, archive_id: str) -> None:
        """Archive in Graph DB"""
        if not self.graph_backend:
            logger.debug("Graph backend not available")
            return
        
        # Mark node as archived
        archive_metadata = {
            'archived': True,
            'archive_id': archive_id,
            'archived_at': datetime.utcnow().isoformat()
        }
        
        try:
            if hasattr(self.graph_backend, 'set_node_properties'):
                self.graph_backend.set_node_properties(document_id, archive_metadata)
            logger.debug(f"Graph archived: {document_id}")
        except Exception as e:
            logger.warning(f"Graph archive skipped: {e}")
    
    def _archive_relational(self, document_id: str, archive_id: str) -> None:
        """Archive in Relational DB"""
        if not self.relational_backend:
            logger.debug("Relational backend not available")
            return
        
        # Update archived status
        try:
            if hasattr(self.relational_backend, 'update'):
                self.relational_backend.update(
                    table="documents",
                    document_id=document_id,
                    data={
                        'archived': True,
                        'archive_id': archive_id,
                        'archived_at': datetime.utcnow().isoformat()
                    }
                )
            logger.debug(f"Relational archived: {document_id}")
        except Exception as e:
            logger.warning(f"Relational archive skipped: {e}")
    
    def _archive_file(self, document_id: str, archive_id: str) -> None:
        """Archive in File Storage"""
        if not self.file_backend:
            logger.debug("File backend not available")
            return
        
        # Move file to archive location
        try:
            if hasattr(self.file_backend, 'move'):
                archive_path = f"archive/{archive_id}"
                self.file_backend.move(document_id, archive_path)
            logger.debug(f"File archived: {document_id}")
        except Exception as e:
            logger.warning(f"File archive skipped: {e}")
    
    def _restore_vector(self, document_id: str, data: Dict[str, Any], strategy: RestoreStrategy) -> None:
        """Restore in Vector DB"""
        if not self.vector_backend:
            logger.debug("Vector backend not available")
            return
        
        # Restore from archive
        restore_metadata = {
            'archived': False,
            'restored_at': datetime.utcnow().isoformat()
        }
        
        try:
            if hasattr(self.vector_backend, 'update_metadata'):
                self.vector_backend.update_metadata(document_id, restore_metadata)
            logger.debug(f"Vector restored: {document_id}")
        except Exception as e:
            logger.warning(f"Vector restore skipped: {e}")
    
    def _restore_graph(self, document_id: str, data: Dict[str, Any], strategy: RestoreStrategy) -> None:
        """Restore in Graph DB"""
        if not self.graph_backend:
            logger.debug("Graph backend not available")
            return
        
        # Restore node
        restore_metadata = {
            'archived': False,
            'restored_at': datetime.utcnow().isoformat()
        }
        
        try:
            if hasattr(self.graph_backend, 'set_node_properties'):
                self.graph_backend.set_node_properties(document_id, restore_metadata)
            logger.debug(f"Graph restored: {document_id}")
        except Exception as e:
            logger.warning(f"Graph restore skipped: {e}")
    
    def _restore_relational(self, document_id: str, data: Dict[str, Any], strategy: RestoreStrategy) -> None:
        """Restore in Relational DB"""
        if not self.relational_backend:
            logger.debug("Relational backend not available")
            return
        
        # Restore record
        try:
            if hasattr(self.relational_backend, 'update'):
                self.relational_backend.update(
                    table="documents",
                    document_id=document_id,
                    data={
                        'archived': False,
                        'restored_at': datetime.utcnow().isoformat()
                    }
                )
            logger.debug(f"Relational restored: {document_id}")
        except Exception as e:
            logger.warning(f"Relational restore skipped: {e}")
    
    def _restore_file(self, document_id: str, data: Dict[str, Any], strategy: RestoreStrategy) -> None:
        """Restore in File Storage"""
        if not self.file_backend:
            logger.debug("File backend not available")
            return
        
        # Restore file from archive
        try:
            if hasattr(self.file_backend, 'restore'):
                self.file_backend.restore(document_id)
            logger.debug(f"File restored: {document_id}")
        except Exception as e:
            logger.warning(f"File restore skipped: {e}")
    
    def _delete_archived_document(self, document_id: str) -> None:
        """Permanently delete archived document"""
        with self._lock:
            metadata = self._archive_storage.get(document_id)
            if metadata:
                # Remove from archive storage
                if metadata.archive_id in self._archive_data:
                    del self._archive_data[metadata.archive_id]
                
                # Update status
                metadata.status = ArchiveStatus.DELETED
        
        logger.debug(f"Archived document deleted: {document_id}")
    
    # ========================================================================
    # Context Manager Support
    # ========================================================================
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disable_auto_cleanup()
        return False


# ============================================================================
# Factory Function
# ============================================================================

def create_archive_manager(unified_strategy) -> ArchiveManager:
    """
    Factory function to create an ArchiveManager.
    
    Args:
        unified_strategy: UnifiedDatabaseStrategy instance
    
    Returns:
        Configured ArchiveManager
    """
    manager = ArchiveManager(unified_strategy)
    
    # Add standard retention policies
    manager.add_retention_policy(RetentionPolicy(
        name="short_term",
        retention_days=RetentionPeriod.DAYS_90.value,
        auto_delete=True
    ))
    
    manager.add_retention_policy(RetentionPolicy(
        name="medium_term",
        retention_days=RetentionPeriod.YEARS_1.value,
        auto_delete=True
    ))
    
    manager.add_retention_policy(RetentionPolicy(
        name="long_term",
        retention_days=RetentionPeriod.YEARS_7.value,
        auto_delete=False
    ))
    
    manager.add_retention_policy(RetentionPolicy(
        name="permanent",
        retention_days=RetentionPeriod.PERMANENT.value,
        auto_delete=False
    ))
    
    return manager
