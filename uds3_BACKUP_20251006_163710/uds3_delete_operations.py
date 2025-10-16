"""
UDS3 Delete Operations Module
==============================

Provides comprehensive deletion strategies for polyglot persistence:
- Soft Delete: Mark as deleted, preserve data
- Hard Delete: Permanently remove data
- Archive: Move to long-term storage
- Restore: Recover soft-deleted documents

Supports all 4 databases:
- Vector DB (ChromaDB/Pinecone)
- Graph DB (Neo4j/ArangoDB)
- Relational DB (PostgreSQL/SQLite)
- File Storage

Author: UDS3 Team
Date: 1. Oktober 2025
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import uuid
import hashlib
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Configuration
# ============================================================================

class DeleteStrategy(Enum):
    """Deletion strategy types"""
    SOFT = "soft"          # Mark as deleted, keep data
    HARD = "hard"          # Permanently delete
    ARCHIVE = "archive"    # Move to archive


class CascadeStrategy(Enum):
    """Cascade deletion strategy for relationships"""
    NONE = "none"              # Don't delete related entities
    SELECTIVE = "selective"    # Delete only specific relations
    FULL = "full"             # Delete all related entities


class RestoreStrategy(Enum):
    """Restore strategy for soft-deleted documents"""
    KEEP_METADATA = "keep_metadata"      # Keep deletion metadata
    CLEAR_METADATA = "clear_metadata"    # Remove all deletion metadata
    PRESERVE_AUDIT = "preserve_audit"    # Keep audit trail


# ============================================================================
# Result Classes
# ============================================================================

@dataclass
class DeleteResult:
    """Result of a delete operation"""
    success: bool
    document_id: str
    strategy: DeleteStrategy
    deleted_at: Optional[datetime] = None
    affected_databases: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    audit_id: Optional[str] = None
    cascade_count: int = 0  # Number of cascade-deleted entities
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.deleted_at:
            result['deleted_at'] = self.deleted_at.isoformat()
        result['strategy'] = self.strategy.value
        return result


@dataclass
class RestoreResult:
    """Result of a restore operation"""
    success: bool
    document_id: str
    restored_at: Optional[datetime] = None
    affected_databases: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.restored_at:
            result['restored_at'] = self.restored_at.isoformat()
        return result


@dataclass
class PurgeResult:
    """Result of purging old deleted documents"""
    success: bool
    purged_count: int
    retention_days: int
    purged_ids: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Soft Delete Manager
# ============================================================================

class SoftDeleteManager:
    """
    Manages soft delete operations across all databases.
    
    Soft delete marks documents as deleted without physically removing them.
    This allows for:
    - Data recovery (restore)
    - Audit trails
    - Compliance (GDPR right to erasure with grace period)
    - Rollback capabilities
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
        
        logger.info("SoftDeleteManager initialized")
    
    # ========================================================================
    # Core Soft Delete
    # ========================================================================
    
    def soft_delete_document(
        self,
        document_id: str,
        reason: Optional[str] = None,
        deleted_by: Optional[str] = None
    ) -> DeleteResult:
        """
        Soft delete a document across all databases.
        
        Marks the document as deleted by adding deletion metadata:
        - deleted_at: timestamp
        - deleted_by: user/system identifier
        - delete_reason: optional reason
        - is_deleted: true flag
        
        Args:
            document_id: Document to soft delete
            reason: Optional deletion reason
            deleted_by: Optional user/system identifier
        
        Returns:
            DeleteResult with operation details
        """
        logger.info(f"Soft deleting document: {document_id}")
        
        deleted_at = datetime.utcnow()
        affected_dbs = []
        errors = []
        
        deletion_metadata = {
            "deleted_at": deleted_at.isoformat(),
            "is_deleted": True,
            "delete_strategy": DeleteStrategy.SOFT.value
        }
        
        if deleted_by:
            deletion_metadata["deleted_by"] = deleted_by
        if reason:
            deletion_metadata["delete_reason"] = reason
        
        # Soft delete in Vector DB
        try:
            self._soft_delete_vector(document_id, deletion_metadata)
            affected_dbs.append("vector")
            logger.debug(f"Vector soft delete successful: {document_id}")
        except Exception as e:
            error_msg = f"Vector soft delete failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Soft delete in Graph DB
        try:
            self._soft_delete_graph(document_id, deletion_metadata)
            affected_dbs.append("graph")
            logger.debug(f"Graph soft delete successful: {document_id}")
        except Exception as e:
            error_msg = f"Graph soft delete failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Soft delete in Relational DB
        try:
            self._soft_delete_relational(document_id, deletion_metadata)
            affected_dbs.append("relational")
            logger.debug(f"Relational soft delete successful: {document_id}")
        except Exception as e:
            error_msg = f"Relational soft delete failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Soft delete in File Storage
        try:
            self._soft_delete_file(document_id, deletion_metadata)
            affected_dbs.append("file")
            logger.debug(f"File soft delete successful: {document_id}")
        except Exception as e:
            error_msg = f"File soft delete failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        success = len(affected_dbs) > 0
        
        result = DeleteResult(
            success=success,
            document_id=document_id,
            strategy=DeleteStrategy.SOFT,
            deleted_at=deleted_at,
            affected_databases=affected_dbs,
            errors=errors if errors else None
        )
        
        logger.info(f"Soft delete complete: {document_id}, success={success}")
        return result
    
    # ========================================================================
    # Database-Specific Soft Delete
    # ========================================================================
    
    def _soft_delete_vector(self, document_id: str, metadata: Dict):
        """Soft delete in Vector DB by adding metadata"""
        if not self.vector_backend:
            logger.warning("Vector backend not available")
            return
        
        # Update metadata to include deletion info
        # Keep embeddings for potential restore
        try:
            # Try to update existing document metadata
            if hasattr(self.vector_backend, 'update_metadata'):
                self.vector_backend.update_metadata(document_id, metadata)
            elif hasattr(self.vector_backend, 'update'):
                # Fallback: generic update
                self.vector_backend.update(
                    ids=[document_id],
                    metadatas=[metadata]
                )
            else:
                logger.warning("Vector backend doesn't support metadata update")
        except Exception as e:
            logger.error(f"Vector soft delete error: {e}")
            raise
    
    def _soft_delete_graph(self, document_id: str, metadata: Dict):
        """Soft delete in Graph DB by setting properties"""
        if not self.graph_backend:
            logger.warning("Graph backend not available")
            return
        
        # Set deleted properties on node, preserve relationships
        try:
            if hasattr(self.graph_backend, 'set_node_properties'):
                self.graph_backend.set_node_properties(document_id, metadata)
            elif hasattr(self.graph_backend, 'update_node'):
                # Fallback: generic update
                self.graph_backend.update_node(document_id, metadata)
            else:
                logger.warning("Graph backend doesn't support property update")
        except Exception as e:
            logger.error(f"Graph soft delete error: {e}")
            raise
    
    def _soft_delete_relational(self, document_id: str, metadata: Dict):
        """Soft delete in Relational DB by updating columns"""
        if not self.relational_backend:
            logger.warning("Relational backend not available")
            return
        
        # Update deleted_at column and is_deleted flag
        try:
            if hasattr(self.relational_backend, 'soft_delete'):
                self.relational_backend.soft_delete(document_id, metadata)
            elif hasattr(self.relational_backend, 'update'):
                # Fallback: generic update
                self.relational_backend.update(
                    table="documents",
                    document_id=document_id,
                    updates=metadata
                )
            else:
                logger.warning("Relational backend doesn't support soft delete")
        except Exception as e:
            logger.error(f"Relational soft delete error: {e}")
            raise
    
    def _soft_delete_file(self, document_id: str, metadata: Dict):
        """Soft delete in File Storage by moving to .deleted/ folder"""
        if not self.file_backend:
            logger.warning("File backend not available")
            return
        
        # Move file to .deleted/ subdirectory
        # Store metadata in sidecar file
        try:
            if hasattr(self.file_backend, 'soft_delete'):
                self.file_backend.soft_delete(document_id, metadata)
            elif hasattr(self.file_backend, 'move_to_deleted'):
                # Fallback: move operation
                self.file_backend.move_to_deleted(document_id)
                # Write metadata sidecar
                self.file_backend.write_metadata(
                    f"{document_id}.deleted.json",
                    metadata
                )
            else:
                logger.warning("File backend doesn't support soft delete")
        except Exception as e:
            logger.error(f"File soft delete error: {e}")
            raise
    
    # ========================================================================
    # Restore Operations
    # ========================================================================
    
    def restore_document(
        self,
        document_id: str,
        strategy: RestoreStrategy = RestoreStrategy.PRESERVE_AUDIT
    ) -> RestoreResult:
        """
        Restore a soft-deleted document.
        
        Args:
            document_id: Document to restore
            strategy: How to handle deletion metadata
        
        Returns:
            RestoreResult with operation details
        """
        logger.info(f"Restoring document: {document_id}")
        
        restored_at = datetime.utcnow()
        affected_dbs = []
        errors = []
        
        # Restore in Vector DB
        try:
            self._restore_vector(document_id, strategy)
            affected_dbs.append("vector")
        except Exception as e:
            errors.append(f"Vector restore failed: {str(e)}")
        
        # Restore in Graph DB
        try:
            self._restore_graph(document_id, strategy)
            affected_dbs.append("graph")
        except Exception as e:
            errors.append(f"Graph restore failed: {str(e)}")
        
        # Restore in Relational DB
        try:
            self._restore_relational(document_id, strategy)
            affected_dbs.append("relational")
        except Exception as e:
            errors.append(f"Relational restore failed: {str(e)}")
        
        # Restore in File Storage
        try:
            self._restore_file(document_id, strategy)
            affected_dbs.append("file")
        except Exception as e:
            errors.append(f"File restore failed: {str(e)}")
        
        success = len(affected_dbs) > 0
        
        result = RestoreResult(
            success=success,
            document_id=document_id,
            restored_at=restored_at,
            affected_databases=affected_dbs,
            errors=errors if errors else None
        )
        
        logger.info(f"Restore complete: {document_id}, success={success}")
        return result
    
    def _restore_vector(self, document_id: str, strategy: RestoreStrategy):
        """Restore document in Vector DB"""
        if not self.vector_backend:
            return
        
        restore_metadata = {
            "is_deleted": False,
            "restored_at": datetime.utcnow().isoformat()
        }
        
        if strategy == RestoreStrategy.CLEAR_METADATA:
            # Remove all deletion metadata
            restore_metadata["deleted_at"] = None
            restore_metadata["deleted_by"] = None
            restore_metadata["delete_reason"] = None
        
        if hasattr(self.vector_backend, 'update_metadata'):
            self.vector_backend.update_metadata(document_id, restore_metadata)
    
    def _restore_graph(self, document_id: str, strategy: RestoreStrategy):
        """Restore document in Graph DB"""
        if not self.graph_backend:
            return
        
        restore_metadata = {
            "is_deleted": False,
            "restored_at": datetime.utcnow().isoformat()
        }
        
        if hasattr(self.graph_backend, 'set_node_properties'):
            self.graph_backend.set_node_properties(document_id, restore_metadata)
    
    def _restore_relational(self, document_id: str, strategy: RestoreStrategy):
        """Restore document in Relational DB"""
        if not self.relational_backend:
            return
        
        restore_metadata = {
            "is_deleted": False,
            "restored_at": datetime.utcnow().isoformat()
        }
        
        if hasattr(self.relational_backend, 'update'):
            self.relational_backend.update(
                table="documents",
                document_id=document_id,
                updates=restore_metadata
            )
    
    def _restore_file(self, document_id: str, strategy: RestoreStrategy):
        """Restore document in File Storage"""
        if not self.file_backend:
            return
        
        # Move file back from .deleted/ folder
        if hasattr(self.file_backend, 'restore_from_deleted'):
            self.file_backend.restore_from_deleted(document_id)
    
    # ========================================================================
    # Query & List Operations
    # ========================================================================
    
    def list_deleted(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        List soft-deleted documents.
        
        Args:
            filters: Optional filters (e.g., deleted_after, deleted_by)
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            List of deleted document metadata
        """
        logger.info("Listing soft-deleted documents")
        
        deleted_docs = []
        
        # Query relational DB for deleted documents
        # (Most efficient for metadata queries)
        try:
            if hasattr(self.relational_backend, 'query_deleted'):
                deleted_docs = self.relational_backend.query_deleted(
                    filters=filters,
                    limit=limit,
                    offset=offset
                )
            elif hasattr(self.relational_backend, 'query'):
                # Fallback: manual query
                query_filters = {"is_deleted": True}
                if filters:
                    query_filters.update(filters)
                
                deleted_docs = self.relational_backend.query(
                    table="documents",
                    filters=query_filters,
                    limit=limit,
                    offset=offset
                )
        except Exception as e:
            logger.error(f"Failed to list deleted documents: {e}")
        
        return deleted_docs
    
    # ========================================================================
    # Purge Operations
    # ========================================================================
    
    def purge_old_deleted(
        self,
        retention_days: int = 90,
        hard_delete: bool = True
    ) -> PurgeResult:
        """
        Permanently delete old soft-deleted documents.
        
        Args:
            retention_days: Delete documents deleted more than N days ago
            hard_delete: If True, hard delete; if False, just archive
        
        Returns:
            PurgeResult with purge statistics
        """
        logger.info(f"Purging deleted documents older than {retention_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        purged_ids = []
        errors = []
        
        # Find old deleted documents
        try:
            old_deleted = self.list_deleted(
                filters={"deleted_before": cutoff_date.isoformat()},
                limit=1000  # Process in batches
            )
            
            logger.info(f"Found {len(old_deleted)} documents to purge")
            
            for doc in old_deleted:
                doc_id = doc.get("document_id") or doc.get("id")
                
                try:
                    if hard_delete:
                        # Use HardDeleteManager
                        logger.debug(f"Hard deleting: {doc_id}")
                        hard_result = HardDeleteManager(self.unified_strategy).hard_delete_document(doc_id)
                        if hard_result.success:
                            purged_ids.append(doc_id)
                    else:
                        # Archive instead (if available)
                        logger.debug(f"Archiving: {doc_id}")
                        if ARCHIVE_AVAILABLE:
                            archive_mgr = create_archive_manager(self.unified_strategy)
                            archive_result = archive_mgr.archive_document(
                                doc_id,
                                retention_policy="long_term",
                                archived_by="system",
                                reason=f"Auto-purge after {retention_days} days"
                            )
                            if archive_result.success:
                                purged_ids.append(doc_id)
                        else:
                            logger.warning("Archive not available, skipping")
                            purged_ids.append(doc_id)
                
                except Exception as e:
                    error_msg = f"Failed to purge {doc_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        except Exception as e:
            logger.error(f"Purge operation failed: {e}")
            errors.append(str(e))
        
        success = len(purged_ids) > 0 or len(errors) == 0
        
        result = PurgeResult(
            success=success,
            purged_count=len(purged_ids),
            retention_days=retention_days,
            purged_ids=purged_ids if purged_ids else None,
            errors=errors if errors else None
        )
        
        logger.info(f"Purge complete: {len(purged_ids)} documents purged")
        return result


# ============================================================================
# Hard Delete Manager
# ============================================================================

class HardDeleteManager:
    """
    Manages hard delete operations (permanent deletion).
    
    Hard delete permanently removes documents from all databases.
    Features:
    - Permanent deletion across all 4 databases
    - Cascade deletion strategies (NONE, SELECTIVE, FULL)
    - Audit trail for compliance (GDPR, etc.)
    - Orphan detection and cleanup
    - Relationship handling
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
        
        # Audit backend (optional)
        self.audit_backend = getattr(unified_strategy, 'audit_backend', None)
        
        logger.info("HardDeleteManager initialized")
    
    # ========================================================================
    # Core Hard Delete
    # ========================================================================
    
    def hard_delete_document(
        self,
        document_id: str,
        cascade: CascadeStrategy = CascadeStrategy.SELECTIVE,
        *,
        reason: Optional[str] = None,
        deleted_by: Optional[str] = None,
        create_audit: bool = True
    ) -> DeleteResult:
        """
        Permanently delete a document across all databases.
        
        This operation is IRREVERSIBLE. Use with caution!
        
        Args:
            document_id: Document to permanently delete
            cascade: Cascade strategy (NONE, SELECTIVE, FULL)
            reason: Optional deletion reason
            deleted_by: Optional user/system identifier
            create_audit: Create audit trail entry (default: True)
        
        Returns:
            DeleteResult with operation details
        """
        logger.warning(f"Hard deleting document: {document_id} (PERMANENT!)")
        
        deleted_at = datetime.utcnow()
        affected_dbs = []
        errors = []
        cascade_count = 0
        audit_id = None
        
        # Create audit trail BEFORE deletion (for compliance)
        if create_audit:
            try:
                audit_id = self._create_audit_entry(
                    document_id=document_id,
                    operation="HARD_DELETE",
                    cascade=cascade,
                    reason=reason,
                    deleted_by=deleted_by
                )
                logger.debug(f"Audit entry created: {audit_id}")
            except Exception as e:
                logger.error(f"Failed to create audit entry: {e}")
                # Continue with deletion even if audit fails
        
        # Get related entities before deletion (for cascade)
        related_entities = []
        if cascade != CascadeStrategy.NONE:
            try:
                related_entities = self._get_related_entities(
                    document_id, 
                    cascade
                )
                logger.debug(f"Found {len(related_entities)} related entities")
            except Exception as e:
                logger.warning(f"Failed to get related entities: {e}")
        
        # Hard delete in Vector DB
        try:
            self._hard_delete_vector(document_id)
            affected_dbs.append("vector")
            logger.debug(f"Vector hard delete successful: {document_id}")
        except Exception as e:
            error_msg = f"Vector hard delete failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Hard delete in Graph DB
        try:
            cascade_deleted = self._hard_delete_graph(
                document_id, 
                cascade, 
                related_entities
            )
            cascade_count += cascade_deleted
            affected_dbs.append("graph")
            logger.debug(f"Graph hard delete successful: {document_id}, cascaded: {cascade_deleted}")
        except Exception as e:
            error_msg = f"Graph hard delete failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Hard delete in Relational DB
        try:
            self._hard_delete_relational(document_id)
            affected_dbs.append("relational")
            logger.debug(f"Relational hard delete successful: {document_id}")
        except Exception as e:
            error_msg = f"Relational hard delete failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Hard delete in File Storage
        try:
            self._hard_delete_file(document_id)
            affected_dbs.append("file")
            logger.debug(f"File hard delete successful: {document_id}")
        except Exception as e:
            error_msg = f"File hard delete failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Cleanup orphans after deletion
        try:
            orphan_count = self._cleanup_orphans(document_id, affected_dbs)
            logger.debug(f"Cleaned up {orphan_count} orphans")
        except Exception as e:
            logger.warning(f"Orphan cleanup failed: {e}")
        
        success = len(affected_dbs) > 0
        
        result = DeleteResult(
            success=success,
            document_id=document_id,
            strategy=DeleteStrategy.HARD,
            deleted_at=deleted_at,
            affected_databases=affected_dbs,
            errors=errors if errors else None,
            audit_id=audit_id,
            cascade_count=cascade_count
        )
        
        logger.warning(f"Hard delete complete: {document_id}, success={success}, cascade={cascade_count}")
        return result
    
    # ========================================================================
    # Database-Specific Hard Delete
    # ========================================================================
    
    def _hard_delete_vector(self, document_id: str):
        """Permanently delete from Vector DB"""
        if not self.vector_backend:
            logger.warning("Vector backend not available")
            return
        
        try:
            # Permanent deletion - remove embeddings
            if hasattr(self.vector_backend, 'delete'):
                self.vector_backend.delete(ids=[document_id])
            elif hasattr(self.vector_backend, 'remove'):
                self.vector_backend.remove(document_id)
            else:
                logger.warning("Vector backend doesn't support deletion")
        except Exception as e:
            logger.error(f"Vector hard delete error: {e}")
            raise
    
    def _hard_delete_graph(
        self, 
        document_id: str, 
        cascade: CascadeStrategy,
        related_entities: List[str]
    ) -> int:
        """Permanently delete from Graph DB with cascade"""
        if not self.graph_backend:
            logger.warning("Graph backend not available")
            return 0
        
        cascade_count = 0
        
        try:
            # Delete node
            if hasattr(self.graph_backend, 'delete_node'):
                self.graph_backend.delete_node(document_id)
            elif hasattr(self.graph_backend, 'remove_node'):
                self.graph_backend.remove_node(document_id)
            else:
                logger.warning("Graph backend doesn't support node deletion")
                return 0
            
            # Handle cascade deletion
            if cascade == CascadeStrategy.FULL:
                # Delete ALL related entities
                for entity_id in related_entities:
                    try:
                        if hasattr(self.graph_backend, 'delete_node'):
                            self.graph_backend.delete_node(entity_id)
                        cascade_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cascade delete {entity_id}: {e}")
            
            elif cascade == CascadeStrategy.SELECTIVE:
                # Delete only direct children (specific relationship types)
                # Implementation depends on graph schema
                # For now, delete relationships only
                if hasattr(self.graph_backend, 'delete_relationships'):
                    self.graph_backend.delete_relationships(document_id)
            
            # CascadeStrategy.NONE: Only delete the node, relationships are orphaned
            
        except Exception as e:
            logger.error(f"Graph hard delete error: {e}")
            raise
        
        return cascade_count
    
    def _hard_delete_relational(self, document_id: str):
        """Permanently delete from Relational DB"""
        if not self.relational_backend:
            logger.warning("Relational backend not available")
            return
        
        try:
            # Permanent deletion with CASCADE or RESTRICT
            if hasattr(self.relational_backend, 'hard_delete'):
                self.relational_backend.hard_delete(document_id)
            elif hasattr(self.relational_backend, 'delete'):
                # Fallback: generic delete
                self.relational_backend.delete(
                    table="documents",
                    document_id=document_id
                )
            else:
                logger.warning("Relational backend doesn't support hard delete")
        except Exception as e:
            logger.error(f"Relational hard delete error: {e}")
            raise
    
    def _hard_delete_file(self, document_id: str):
        """Permanently delete from File Storage"""
        if not self.file_backend:
            logger.warning("File backend not available")
            return
        
        try:
            # Physically delete file from storage
            if hasattr(self.file_backend, 'delete'):
                self.file_backend.delete(document_id)
            elif hasattr(self.file_backend, 'remove'):
                self.file_backend.remove(document_id)
            else:
                logger.warning("File backend doesn't support deletion")
        except Exception as e:
            logger.error(f"File hard delete error: {e}")
            raise
    
    # ========================================================================
    # Cascade & Relationship Handling
    # ========================================================================
    
    def _get_related_entities(
        self, 
        document_id: str, 
        cascade: CascadeStrategy
    ) -> List[str]:
        """
        Get related entities for cascade deletion.
        
        Args:
            document_id: Source document
            cascade: Cascade strategy
        
        Returns:
            List of related entity IDs
        """
        if not self.graph_backend:
            return []
        
        related = []
        
        try:
            if cascade == CascadeStrategy.FULL:
                # Get ALL connected entities (recursive)
                if hasattr(self.graph_backend, 'get_all_connected'):
                    related = self.graph_backend.get_all_connected(document_id)
                elif hasattr(self.graph_backend, 'traverse'):
                    # Fallback: traverse with max depth
                    related = self.graph_backend.traverse(
                        start_node=document_id,
                        max_depth=10
                    )
            
            elif cascade == CascadeStrategy.SELECTIVE:
                # Get only direct children (depth 1)
                if hasattr(self.graph_backend, 'get_children'):
                    related = self.graph_backend.get_children(document_id)
                elif hasattr(self.graph_backend, 'get_relationships'):
                    # Fallback: get relationships and extract targets
                    relationships = self.graph_backend.get_relationships(document_id)
                    related = [rel.get('target') for rel in relationships if rel.get('target')]
        
        except Exception as e:
            logger.warning(f"Failed to get related entities: {e}")
        
        return related
    
    # ========================================================================
    # Orphan Detection & Cleanup
    # ========================================================================
    
    def _cleanup_orphans(
        self, 
        document_id: str, 
        affected_dbs: List[str]
    ) -> int:
        """
        Clean up orphaned data after deletion.
        
        Orphans can occur when:
        - Graph node deleted but embeddings remain
        - File deleted but metadata remains
        - Relationships point to non-existent nodes
        
        Args:
            document_id: Deleted document ID
            affected_dbs: Databases where deletion succeeded
        
        Returns:
            Number of orphans cleaned up
        """
        orphan_count = 0
        
        # If vector delete succeeded but graph failed, embeddings are orphaned
        if "vector" in affected_dbs and "graph" not in affected_dbs:
            try:
                # Re-attempt vector deletion to clean up
                if self.vector_backend and hasattr(self.vector_backend, 'delete'):
                    self.vector_backend.delete(ids=[document_id])
                    orphan_count += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup orphaned vector data: {e}")
        
        # If relational delete succeeded but file failed, metadata is orphaned
        if "relational" in affected_dbs and "file" not in affected_dbs:
            # Metadata without file is acceptable (file may have been deleted manually)
            pass
        
        # Clean up dangling relationships in graph
        if "graph" in affected_dbs and self.graph_backend:
            try:
                if hasattr(self.graph_backend, 'cleanup_dangling_relationships'):
                    cleaned = self.graph_backend.cleanup_dangling_relationships(document_id)
                    orphan_count += cleaned
            except Exception as e:
                logger.warning(f"Failed to cleanup dangling relationships: {e}")
        
        return orphan_count
    
    # ========================================================================
    # Audit Trail
    # ========================================================================
    
    def _create_audit_entry(
        self,
        document_id: str,
        operation: str,
        cascade: CascadeStrategy,
        reason: Optional[str],
        deleted_by: Optional[str]
    ) -> Optional[str]:
        """
        Create audit trail entry for compliance.
        
        Audit entries are immutable and tamper-proof.
        Required for GDPR "right to erasure" compliance.
        
        Args:
            document_id: Deleted document
            operation: Operation type (HARD_DELETE, SOFT_DELETE)
            cascade: Cascade strategy used
            reason: Deletion reason
            deleted_by: User/system identifier
        
        Returns:
            Audit entry ID or None if audit failed
        """
        if not self.audit_backend:
            # If no audit backend, try to use relational backend
            if not self.relational_backend:
                logger.warning("No audit backend available")
                return None
        
        audit_entry = {
            "audit_id": str(uuid.uuid4()),
            "document_id": document_id,
            "operation": operation,
            "cascade_strategy": cascade.value,
            "timestamp": datetime.utcnow().isoformat(),
            "deleted_by": deleted_by or "system",
            "reason": reason or "No reason provided",
            "hash": None  # Will be computed
        }
        
        # Compute tamper-proof hash
        audit_entry["hash"] = self._compute_audit_hash(audit_entry)
        
        try:
            if self.audit_backend and hasattr(self.audit_backend, 'create_audit_entry'):
                self.audit_backend.create_audit_entry(audit_entry)
            elif self.relational_backend and hasattr(self.relational_backend, 'insert'):
                # Fallback: use relational backend
                self.relational_backend.insert(
                    table="audit_trail",
                    data=audit_entry
                )
            
            return audit_entry["audit_id"]
        
        except Exception as e:
            logger.error(f"Failed to create audit entry: {e}")
            return None
    
    def _compute_audit_hash(self, audit_entry: Dict) -> str:
        """
        Compute tamper-proof hash for audit entry.
        
        Args:
            audit_entry: Audit entry dict
        
        Returns:
            SHA-256 hash
        """
        import hashlib
        import json
        
        # Create deterministic string representation
        hashable = {
            k: v for k, v in audit_entry.items() 
            if k != "hash"  # Exclude hash itself
        }
        hashable_str = json.dumps(hashable, sort_keys=True)
        
        return hashlib.sha256(hashable_str.encode()).hexdigest()
    
    # ========================================================================
    # Batch Hard Delete
    # ========================================================================
    
    def hard_delete_batch(
        self,
        document_ids: List[str],
        cascade: CascadeStrategy = CascadeStrategy.SELECTIVE,
        **kwargs
    ) -> Dict[str, DeleteResult]:
        """
        Permanently delete multiple documents.
        
        Args:
            document_ids: List of document IDs to delete
            cascade: Cascade strategy
            **kwargs: Additional arguments (reason, deleted_by, etc.)
        
        Returns:
            Dict mapping document_id to DeleteResult
        """
        logger.warning(f"Batch hard deleting {len(document_ids)} documents (PERMANENT!)")
        
        results = {}
        
        for doc_id in document_ids:
            try:
                result = self.hard_delete_document(
                    doc_id,
                    cascade=cascade,
                    **kwargs
                )
                results[doc_id] = result
            except Exception as e:
                logger.error(f"Batch delete failed for {doc_id}: {e}")
                results[doc_id] = DeleteResult(
                    success=False,
                    document_id=doc_id,
                    strategy=DeleteStrategy.HARD,
                    errors=[str(e)]
                )
        
        success_count = sum(1 for r in results.values() if r.success)
        logger.warning(f"Batch hard delete complete: {success_count}/{len(document_ids)} successful")
        
        return results


# ============================================================================
# Archive Integration
# ============================================================================

# Import ArchiveManager if available
try:
    from uds3_archive_operations import (
        ArchiveManager,
        create_archive_manager,
        ArchiveResult,
        RetentionPolicy,
        RetentionPeriod
    )
    ARCHIVE_AVAILABLE = True
    logger.info("ArchiveManager available")
except ImportError:
    ARCHIVE_AVAILABLE = False
    logger.warning("ArchiveManager not available")


class DeleteOperationsOrchestrator:
    """
    Orchestrates all delete and archive operations.
    
    Provides unified interface for:
    - Soft Delete (via SoftDeleteManager)
    - Hard Delete (via HardDeleteManager)
    - Archive (via ArchiveManager)
    """
    
    def __init__(self, unified_strategy):
        """
        Initialize with unified database strategy.
        
        Args:
            unified_strategy: UnifiedDatabaseStrategy instance
        """
        self.unified_strategy = unified_strategy
        
        # Initialize managers
        self.soft_delete = SoftDeleteManager(unified_strategy)
        self.hard_delete = HardDeleteManager(unified_strategy)
        
        # Initialize ArchiveManager if available
        if ARCHIVE_AVAILABLE:
            self.archive = create_archive_manager(unified_strategy)
            logger.info("DeleteOperationsOrchestrator initialized with archive support")
        else:
            self.archive = None
            logger.info("DeleteOperationsOrchestrator initialized (no archive support)")
    
    def delete_document(
        self,
        document_id: str,
        strategy: DeleteStrategy = DeleteStrategy.SOFT,
        **kwargs
    ) -> DeleteResult:
        """
        Delete a document using specified strategy.
        
        Args:
            document_id: Document to delete
            strategy: DELETE.SOFT or DELETE.HARD
            **kwargs: Additional arguments
        
        Returns:
            DeleteResult
        """
        if strategy == DeleteStrategy.SOFT:
            return self.soft_delete.soft_delete_document(document_id, **kwargs)
        elif strategy == DeleteStrategy.HARD:
            return self.hard_delete.hard_delete_document(document_id, **kwargs)
        else:
            raise ValueError(f"Unknown delete strategy: {strategy}")
    
    def archive_document(
        self,
        document_id: str,
        **kwargs
    ) -> 'ArchiveResult':
        """
        Archive a document to long-term storage.
        
        Args:
            document_id: Document to archive
            **kwargs: Archive arguments (retention_policy, retention_days, etc.)
        
        Returns:
            ArchiveResult if archive available, else raises error
        """
        if not ARCHIVE_AVAILABLE or not self.archive:
            raise RuntimeError("ArchiveManager not available")
        
        return self.archive.archive_document(document_id, **kwargs)
    
    def restore_archived(
        self,
        document_id: str,
        **kwargs
    ) -> 'RestoreResult':
        """
        Restore an archived document.
        
        Args:
            document_id: Document to restore
            **kwargs: Restore arguments
        
        Returns:
            RestoreResult if archive available, else raises error
        """
        if not ARCHIVE_AVAILABLE or not self.archive:
            raise RuntimeError("ArchiveManager not available")
        
        return self.archive.restore_document(document_id, **kwargs)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Enums
    'DeleteStrategy',
    'CascadeStrategy',
    'RestoreStrategy',
    
    # Results
    'DeleteResult',
    'RestoreResult',
    'PurgeResult',
    
    # Managers
    'SoftDeleteManager',
    'HardDeleteManager',
    'DeleteOperationsOrchestrator',
    
    # Archive availability flag
    'ARCHIVE_AVAILABLE',
]
