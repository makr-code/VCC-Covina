"""
Data Transformation Tool - Transform Existing Data to New Formats

Transforms existing data in databases without re-uploading files:
- Polyglot optimization (add embeddings, relationships)
- CouchDB migration (copy data from PostgreSQL)
- Embedding regeneration (update ChromaDB with new model)
- Graph relationship updates (rebuild Neo4j relationships)

Author: GitHub Copilot
Date: 31. Oktober 2025
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class DataTransformationJob:
    """
    Tracks progress of a data transformation job.
    """
    
    def __init__(self, job_id: str, config: Dict[str, Any]):
        self.job_id = job_id
        self.config = config
        self.status = "queued"
        self.created_at = datetime.now().isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        
        self.total_items = 0
        self.processed_items = 0
        self.succeeded_items = 0
        self.failed_items = 0
        self.skipped_items = 0
        
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.cancelled = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Export job status as dict for API response"""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "config": self.config,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": {
                "total": self.total_items,
                "processed": self.processed_items,
                "succeeded": self.succeeded_items,
                "failed": self.failed_items,
                "skipped": self.skipped_items,
                "percentage": round((self.processed_items / self.total_items * 100) if self.total_items > 0 else 0, 2)
            },
            "errors": self.errors[-10:],  # Last 10 errors
            "warnings": self.warnings[-10:],  # Last 10 warnings
            "cancelled": self.cancelled
        }


class DataTransformer:
    """
    Transforms existing data in databases to new formats.
    
    Transformation Types:
    1. Polyglot Optimization: Add embeddings/relationships to existing data
    2. CouchDB Migration: Copy data from PostgreSQL to CouchDB
    3. Embedding Regeneration: Update ChromaDB vectors with new model
    4. Graph Rebuild: Recreate Neo4j relationships from metadata
    """
    
    def __init__(self, uds3_manager=None, postgres_backend=None, 
                 chromadb_backend=None, neo4j_backend=None, couchdb_backend=None):
        """
        Initialize transformer with database backends.
        
        Args:
            uds3_manager: UDS3 PolyglotManager instance
            postgres_backend: PostgreSQL backend adapter
            chromadb_backend: ChromaDB backend adapter
            neo4j_backend: Neo4j backend adapter
            couchdb_backend: CouchDB backend adapter
        """
        self.uds3 = uds3_manager
        self.postgres = postgres_backend
        self.chromadb = chromadb_backend
        self.neo4j = neo4j_backend
        self.couchdb = couchdb_backend
        
        logger.info("✅ DataTransformer initialized")
    
    # ========================================================================
    # TRANSFORMATION TYPE 1: POLYGLOT OPTIMIZATION
    # ========================================================================
    
    def transform_to_polyglot(self, job: DataTransformationJob, 
                              document_ids: Optional[List[str]] = None,
                              batch_size: int = 100) -> None:
        """
        Transform existing data to polyglot format.
        
        Adds:
        - ChromaDB: Semantic embeddings (if missing)
        - Neo4j: Graph relationships (if missing)
        - CouchDB: Full document content (if missing)
        
        Args:
            job: Job tracker
            document_ids: Specific document IDs (None = all)
            batch_size: Number of documents per batch
        """
        job.status = "running"
        job.started_at = datetime.now().isoformat()
        
        try:
            # 1. Select documents from PostgreSQL
            logger.info(f"[Job {job.job_id}] Selecting documents from PostgreSQL...")
            
            if document_ids:
                placeholders = ",".join(["%s"] * len(document_ids))
                query = f"SELECT * FROM documents WHERE document_id IN ({placeholders})"
                params = tuple(document_ids)
            else:
                query = "SELECT * FROM documents ORDER BY created_at ASC"
                params = None
            
            documents = self.postgres.execute_query(query, params, fetch=True)
            if documents is None:
                documents = []
            job.total_items = len(documents)
            
            logger.info(f"[Job {job.job_id}] Found {job.total_items} documents to transform")
            
            # 2. Process in batches
            for i in range(0, len(documents), batch_size):
                if job.cancelled:
                    logger.warning(f"[Job {job.job_id}] Cancelled by user")
                    job.status = "cancelled"
                    return
                
                batch = documents[i:i+batch_size]
                self._process_polyglot_batch(job, batch)
            
            job.status = "completed"
            job.completed_at = datetime.now().isoformat()
            
            logger.info(f"[Job {job.job_id}] ✅ Completed: {job.succeeded_items}/{job.total_items} succeeded")
            
        except Exception as e:
            job.status = "failed"
            job.errors.append({
                "phase": "transform_to_polyglot",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            logger.error(f"[Job {job.job_id}] ❌ Failed: {e}")
    
    def _process_polyglot_batch(self, job: DataTransformationJob, 
                                documents: List[Dict[str, Any]]) -> None:
        """Process a batch of documents for polyglot transformation"""
        from backend.utils.polyglot_transformer import PolyglotDataTransformer
        
        transformer = PolyglotDataTransformer()
        
        for doc in documents:
            try:
                document_id = doc.get("document_id")
                
                # Check what's missing
                needs_embedding = not self._has_chromadb_vector(document_id)
                needs_relationships = not self._has_neo4j_relationships(document_id)
                needs_couchdb = not self._has_couchdb_document(document_id)
                
                if not (needs_embedding or needs_relationships or needs_couchdb):
                    job.skipped_items += 1
                    job.processed_items += 1
                    continue
                
                # Transform data
                polyglot_data = transformer.transform_for_golden_dataset({
                    "document_id": document_id,
                    "classification": doc.get("classification") or "unknown",
                    "quality_score": doc.get("quality_score") or 0.0,  # Handle NULL from DB
                    "reviewed_by": doc.get("reviewed_by") or "system",
                    "notes": doc.get("notes") or "",
                    "metadata": doc.get("metadata") or {}
                })
                
                # Add missing data
                if needs_embedding and polyglot_data.get("vector"):
                    vector_data = polyglot_data["vector"]
                    # Only add if embeddings are actually generated
                    if vector_data.get("embeddings") is not None:
                        self._add_chromadb_vector(vector_data)
                    else:
                        job.warnings.append({
                            "document_id": document_id,
                            "warning": "Embeddings could not be generated (model unavailable)",
                            "timestamp": datetime.now().isoformat()
                        })
                
                if needs_relationships and polyglot_data.get("graph"):
                    self._add_neo4j_relationships(polyglot_data["graph"])
                
                if needs_couchdb and polyglot_data.get("document"):
                    self._add_couchdb_document(polyglot_data["document"])
                
                job.succeeded_items += 1
                
            except Exception as e:
                job.failed_items += 1
                job.errors.append({
                    "document_id": doc.get("document_id"),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            finally:
                job.processed_items += 1
    
    # ========================================================================
    # TRANSFORMATION TYPE 2: COUCHDB MIGRATION
    # ========================================================================
    
    def migrate_to_couchdb(self, job: DataTransformationJob,
                          document_ids: Optional[List[str]] = None,
                          batch_size: int = 100) -> None:
        """
        Copy documents from PostgreSQL to CouchDB.
        
        Args:
            job: Job tracker
            document_ids: Specific document IDs (None = all)
            batch_size: Number of documents per batch
        """
        job.status = "running"
        job.started_at = datetime.now().isoformat()
        
        try:
            # Select documents
            if document_ids:
                placeholders = ",".join(["%s"] * len(document_ids))
                query = f"SELECT * FROM documents WHERE document_id IN ({placeholders})"
                params = tuple(document_ids)
            else:
                query = "SELECT * FROM documents ORDER BY created_at ASC"
                params = None
            
            documents = self.postgres.execute_query(query, params, fetch=True)
            if documents is None:
                documents = []
            job.total_items = len(documents)
            
            logger.info(f"[Job {job.job_id}] Migrating {job.total_items} documents to CouchDB...")
            
            # Process in batches
            for i in range(0, len(documents), batch_size):
                if job.cancelled:
                    job.status = "cancelled"
                    return
                
                batch = documents[i:i+batch_size]
                self._migrate_couchdb_batch(job, batch)
            
            job.status = "completed"
            job.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            job.status = "failed"
            job.errors.append({"phase": "migrate_to_couchdb", "error": str(e)})
    
    def _migrate_couchdb_batch(self, job: DataTransformationJob,
                               documents: List[Dict[str, Any]]) -> None:
        """Migrate a batch of documents to CouchDB"""
        for doc in documents:
            try:
                # Convert PostgreSQL row to CouchDB document
                couchdb_doc = {
                    "_id": doc.get("document_id"),
                    "type": "document",
                    "classification": doc.get("classification"),
                    "content": doc.get("content", ""),
                    "metadata": json.loads(doc.get("metadata", "{}")) if isinstance(doc.get("metadata"), str) else doc.get("metadata", {}),
                    "created_at": doc.get("created_at"),
                    "updated_at": datetime.now().isoformat(),
                    "migrated_from": "postgresql"
                }
                
                # Save to CouchDB
                self.couchdb.save_document(couchdb_doc)
                job.succeeded_items += 1
                
            except Exception as e:
                job.failed_items += 1
                job.errors.append({
                    "document_id": doc.get("document_id"),
                    "error": str(e)
                })
            finally:
                job.processed_items += 1
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _has_chromadb_vector(self, document_id: str) -> bool:
        """Check if document has vector in ChromaDB"""
        if not self.chromadb:
            return False
        try:
            result = self.chromadb.get_vector(document_id)
            return result is not None
        except:
            return False
    
    def _has_neo4j_relationships(self, document_id: str) -> bool:
        """Check if document has relationships in Neo4j"""
        if not self.neo4j:
            return False
        try:
            query = "MATCH (d:Document {id: $doc_id})-[r]-() RETURN count(r) as count"
            result = self.neo4j.execute_query(query, {"doc_id": document_id})
            return result[0].get("count", 0) > 0 if result else False
        except:
            return False
    
    def _has_couchdb_document(self, document_id: str) -> bool:
        """Check if document exists in CouchDB"""
        if not self.couchdb:
            return False
        try:
            doc = self.couchdb.get_document(document_id)
            return doc is not None
        except:
            return False
    
    def _add_chromadb_vector(self, vector_data: Dict[str, Any]) -> None:
        """Add vector to ChromaDB"""
        if self.chromadb:
            # ChromaDB API: add_vector(vector_id, vector, metadata=None, collection_name=None)
            # Note: Local backend has different param order than Remote backend!
            self.chromadb.add_vector(
                vector_id=vector_data.get("document_id"),
                vector=vector_data.get("embeddings"),
                metadata=vector_data.get("metadata", {})
            )
    
    def _add_neo4j_relationships(self, graph_data: Dict[str, Any]) -> None:
        """Add relationships to Neo4j"""
        if self.neo4j:
            node = graph_data.get("node", {})
            relationships = graph_data.get("relationships", [])
            
            # Create node
            self.neo4j.create_node(node)
            
            # Create relationships
            for rel in relationships:
                self.neo4j.create_relationship(
                    source_id=node.get("id"),
                    target_id=rel.get("target"),
                    relationship_type=rel.get("type")
                )
    
    def _add_couchdb_document(self, doc_data: Dict[str, Any]) -> None:
        """Add document to CouchDB"""
        if self.couchdb:
            self.couchdb.save_document(doc_data)
