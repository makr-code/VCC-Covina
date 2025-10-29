"""
UDS3 Writer Adapter

Wraps UDS3 DatabaseManager and implements the Writer protocol
for the modular ingestion pipeline.

Uses existing UDS3 multi-database framework instead of duplicating
database writers. Delegates to DatabaseManager which orchestrates:
- PostgreSQL (Relational Master Data)
- ChromaDB (Vector Embeddings)
- Neo4j (Knowledge Graph)
- CouchDB (Full Content Storage)
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
import hashlib

# Add uds3 to Python path
uds3_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uds3'))
if os.path.exists(uds3_path) and uds3_path not in sys.path:
    sys.path.insert(0, uds3_path)

from ingestion.core.interfaces import Writer, Chunk

# Import UDS3 DatabaseManager
# Initialize logger
logger = logging.getLogger(__name__)

try:
    from database.database_manager import DatabaseManager
    UDS3_AVAILABLE = True
except ImportError as e:
    logging.warning(f"UDS3 DatabaseManager not available: {e}")
    UDS3_AVAILABLE = False
    DatabaseManager = None



class UDS3Writer:
    """
    UDS3 Multi-Database Writer using DatabaseManager.
    
    Implements the Writer protocol and delegates to UDS3 DatabaseManager
    which orchestrates writes across multiple databases:
    - PostgreSQL (Relational): Document metadata
    - ChromaDB (Vector): Semantic embeddings
    - Neo4j (Graph): Knowledge relationships
    - CouchDB (Document): Full content storage
    
    Example:
        >>> config = {
        ...     "relational": {"enabled": True, "backend": "postgresql", ...},
        ...     "vector": {"enabled": True, "backend": "chromadb", ...},
        ...     "graph": {"enabled": True, "backend": "neo4j", ...},
        ...     "file": {"enabled": True, "backend": "couchdb", ...},
        ... }
        >>> writer = UDS3Writer(config=config)
        >>> await writer.initialize()
        >>> await writer.write(chunk)
        True
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize UDS3 writer with DatabaseManager.
        
        Args:
            config: Configuration dictionary with database settings.
                   Uses DatabaseManager format (relational, vector, graph, file).
        """
        if not UDS3_AVAILABLE:
            raise RuntimeError("UDS3 DatabaseManager not available - check sys.path")
        
        self.config = config or {}
        self.db_manager: Optional[DatabaseManager] = None
        self._initialized = False
        
        logger.info(f"UDS3Writer created with config: {list(self.config.keys())}")
    
    async def initialize(self) -> None:
        """
        Initialize DatabaseManager and all backends.
        
        Raises:
            RuntimeError: If DatabaseManager initialization fails
        """
        if self._initialized:
            logger.debug("UDS3Writer already initialized")
            return
        
        try:
            # Create DatabaseManager (autostart=True starts all backends)
            logger.info("Initializing UDS3 DatabaseManager...")
            self.db_manager = DatabaseManager(self.config, autostart=True)
            
            # Log which backends are available
            backends_status = []
            if self.db_manager.relational_backend:
                backends_status.append("PostgreSQL")
            if self.db_manager.vector_backend:
                backends_status.append("ChromaDB")
            if self.db_manager.graph_backend:
                backends_status.append("Neo4j")
            if self.db_manager.file_backend:
                backends_status.append("CouchDB")
            
            logger.info(f"✅ UDS3Writer initialized with backends: {', '.join(backends_status)}")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize UDS3Writer: {e}")
            raise RuntimeError(f"UDS3Writer initialization failed: {e}")
    
    async def write(self, chunk: Chunk) -> bool:
        """
        Write a single chunk to all UDS3 databases.
        
        Delegates to DatabaseManager backends for multi-database writes.
        
        Args:
            chunk: Chunk to persist
            
        Returns:
            True if at least one write succeeded, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        # Generate chunk ID from source and index
        chunk_id = f"{chunk.metadata.source_file}_{chunk.metadata.chunk_index}"
        
        
        logger.debug(
            f"Writing chunk: {chunk.metadata.source_file} "
            f"(index {chunk.metadata.chunk_index}/{chunk.metadata.total_chunks})"
        )
        
        success_count = 0
        total_attempts = 0
        
        # Write to PostgreSQL (Relational)
        if self.db_manager.relational_backend:
            total_attempts += 1
            try:
                result = self.db_manager.relational_backend.insert_document(
                    document_id=chunk_id,
                    file_path=chunk.metadata.source_file,
                    classification=chunk.metadata.classification.value if hasattr(chunk.metadata, 'classification') else "unknown",
                    content_length=len(chunk.text),
                    legal_terms_count=0,  # TODO: Extract from metadata if available
                    created_at=datetime.now().isoformat(),
                    quality_score=chunk.metadata.confidence if hasattr(chunk.metadata, 'confidence') else None,
                )
                if result.get("success"):
                    success_count += 1
                    logger.debug(f"✅ PostgreSQL write succeeded: {chunk_id}")
            except Exception as e:
                logger.error(f"❌ PostgreSQL write failed: {e}")
        
        # Write to ChromaDB (Vector)
        if self.db_manager.vector_backend:
            total_attempts += 1
            try:
                # Prepare document for ChromaDB
                doc_data = {
                    "id": chunk_id,
                    "content": chunk.text,
                    "metadata": {
                        "source_file": chunk.metadata.source_file,
                        "chunk_index": chunk.metadata.chunk_index,
                        "total_chunks": chunk.metadata.total_chunks,
                        "created_at": datetime.now().isoformat(),
                    }
                }
                
                # add_documents expects List[Dict]
                if self.db_manager.vector_backend.add_documents([doc_data]):
                    success_count += 1
                    logger.debug(f"✅ ChromaDB write succeeded: {chunk_id}")
            except Exception as e:
                logger.error(f"❌ ChromaDB write failed: {e}")
        
        # Write to Neo4j (Graph) - Create Document/Chunk nodes
        if self.db_manager.graph_backend:
            total_attempts += 1
            try:
                # Create Document node if not exists
                doc_node_query = """
                MERGE (d:Document {file_path: $file_path})
                ON CREATE SET d.created_at = $created_at
                RETURN d
                """
                
                # Create Chunk node and relationship
                chunk_query = """
                MATCH (d:Document {file_path: $file_path})
                CREATE (c:Chunk {
                    chunk_id: $chunk_id,
                    content: $content,
                    chunk_index: $chunk_index,
                    created_at: $created_at
                })
                CREATE (d)-[:CONTAINS_CHUNK]->(c)
                RETURN c
                """
                
                params_doc = {
                    "file_path": chunk.metadata.source_file,
                    "created_at": datetime.now().isoformat(),
                }
                
                params_chunk = {
                    "file_path": chunk.metadata.source_file,
                    "chunk_id": chunk_id,
                    "content": chunk.text[:1000],  # Limit content size in graph
                    "chunk_index": chunk.metadata.chunk_index,
                    "created_at": datetime.now().isoformat(),
                }
                
                # Execute queries (DatabaseManager has execute_query method)
                self.db_manager.graph_backend.execute_query(doc_node_query, params_doc)
                self.db_manager.graph_backend.execute_query(chunk_query, params_chunk)
                
                success_count += 1
                logger.debug(f"✅ Neo4j write succeeded: {chunk_id}")
            except Exception as e:
                logger.error(f"❌ Neo4j write failed: {e}")
        
        # Write to CouchDB (Document Storage)
        if self.db_manager.file_backend:
            total_attempts += 1
            try:
                # CouchDB stores full documents
                doc_data = {
                    "_id": chunk_id,
                    "content": chunk.text,
                    "metadata": asdict(chunk.metadata),
                    "created_at": datetime.now().isoformat(),
                }
                
                # add_documents expects List[Dict]
                if self.db_manager.file_backend.add_documents([doc_data]):
                    success_count += 1
                    logger.debug(f"✅ CouchDB write succeeded: {chunk_id}")
            except Exception as e:
                logger.error(f"❌ CouchDB write failed: {e}")
        
        # Return True if at least one backend succeeded
        success = success_count > 0
        logger.info(
            f"Write completed: {success_count}/{total_attempts} backends succeeded "
            f"for chunk {chunk_id}"
        )
        return success
    
    async def write_batch(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """
        Write multiple chunks in a batch operation.
        
    Writes each chunk individually (backends don't have batch operations).
        
        Args:
            chunks: List of chunks to persist
            
        Returns:
            Dictionary with write results:
            {
                "success": bool,
                "written": int,
                "failed": int,
                "errors": List[str],
            }
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info(
            f"Batch write: {len(chunks)} chunks",
        )
        
        # Write each chunk individually
        written = 0
        failed = 0
        errors = []
        
        for chunk in chunks:
            try:
                success = await self.write(chunk)
                if success:
                    written += 1
                else:
                    failed += 1
                    errors.append(f"Chunk {chunk.metadata.source_file}_{chunk.metadata.chunk_index} failed")
            except Exception as e:
                failed += 1
                errors.append(f"Chunk {chunk.metadata.source_file}_{chunk.metadata.chunk_index}: {str(e)}")
                logger.error(f"Batch write error for chunk: {e}")
        
        return {
            "success": written > 0,
            "written": written,
            "failed": failed,
            "errors": errors,
        }
    
    async def health_check(self) -> bool:
        """
        Check if all UDS3 databases are available.
        
        Returns:
            True if all configured databases are healthy, False otherwise
        """
        if not self._initialized:
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Health check failed during initialization: {e}")
                return False
        
        # Check all backends
        health_status = {}
        
        # Check relational backend
        if self.db_manager.relational_backend:
            try:
                # Try a simple operation
                is_healthy = self.db_manager.relational_backend.get_document_count() is not None
                health_status["postgresql"] = is_healthy
                logger.debug(f"PostgreSQL health: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            except Exception as e:
                logger.error(f"PostgreSQL health check error: {e}")
                health_status["postgresql"] = False
        
        # Check vector backend
        if self.db_manager.vector_backend:
            try:
                is_healthy = self.db_manager.vector_backend.is_available()
                health_status["chromadb"] = is_healthy
                logger.debug(f"ChromaDB health: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            except Exception as e:
                logger.error(f"ChromaDB health check error: {e}")
                health_status["chromadb"] = False
        
        # Check graph backend
        if self.db_manager.graph_backend:
            try:
                # Simple Neo4j query
                result = self.db_manager.graph_backend.execute_query("RETURN 1", {})
                is_healthy = result is not None
                health_status["neo4j"] = is_healthy
                logger.debug(f"Neo4j health: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            except Exception as e:
                logger.error(f"Neo4j health check error: {e}")
                health_status["neo4j"] = False
        
        # Check file backend
        if self.db_manager.file_backend:
            try:
                is_healthy = self.db_manager.file_backend.is_available()
                health_status["couchdb"] = is_healthy
                logger.debug(f"CouchDB health: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            except Exception as e:
                logger.error(f"CouchDB health check error: {e}")
                health_status["couchdb"] = False
        
        # Return True only if all backends are healthy
        return all(health_status.values())
    
    @property
    def backend_status(self) -> Dict[str, bool]:
        """
        Get initialization status of all backends.
        
        Returns:
            Dictionary mapping backend names to initialization status
        """
        if not self._initialized or not self.db_manager:
            return {
                "postgresql": False,
                "chromadb": False,
                "neo4j": False,
                "couchdb": False,
            }
        
        return {
            "postgresql": self.db_manager.relational_backend is not None,
            "chromadb": self.db_manager.vector_backend is not None,
            "neo4j": self.db_manager.graph_backend is not None,
            "couchdb": self.db_manager.file_backend is not None,
        }
    

