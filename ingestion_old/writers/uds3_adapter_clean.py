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
        >>> # Simple config - DatabaseManager auto-configures credentials from config.py
        >>> config = {
        ...     "relational": {"enabled": True},  # PostgreSQL
        ...     "vector": {"enabled": True},      # ChromaDB
        ...     "graph": {"enabled": True},       # Neo4j
        ...     "file": {"enabled": True}         # CouchDB
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
                doc_id = f"{chunk.metadata.source_file}_{chunk.metadata.chunk_index}"
                result = self.db_manager.relational_backend.insert_document(
                    document_id=doc_id,
                    file_path=chunk.metadata.source_file,
                    classification=chunk.metadata.classification.value if hasattr(chunk.metadata, 'classification') else "unknown",
                    content_length=len(chunk.content),
                    legal_terms_count=0,  # TODO: Extract from metadata if available
                    created_at=datetime.now().isoformat(),
                    quality_score=chunk.metadata.confidence if hasattr(chunk.metadata, 'confidence') else None,
                )
                if result.get("success"):
                    success_count += 1
                    logger.debug(f"✅ PostgreSQL write succeeded: {doc_id}")
            except Exception as e:
                logger.error(f"❌ PostgreSQL write failed: {e}")
        
        # Write to ChromaDB (Vector)
        if self.db_manager.vector_backend:
            total_attempts += 1
            try:
                # Prepare document for ChromaDB
                doc_data = {
                    "id": chunk.chunk_id,
                    "content": chunk.content,
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
                    logger.debug(f"✅ ChromaDB write succeeded: {chunk.chunk_id}")
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
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content[:1000],  # Limit content size in graph
                    "chunk_index": chunk.metadata.chunk_index,
                    "created_at": datetime.now().isoformat(),
                }
                
                # Execute queries (DatabaseManager has execute_query method)
                self.db_manager.graph_backend.execute_query(doc_node_query, params_doc)
                self.db_manager.graph_backend.execute_query(chunk_query, params_chunk)
                
                success_count += 1
                logger.debug(f"✅ Neo4j write succeeded: {chunk.chunk_id}")
            except Exception as e:
                logger.error(f"❌ Neo4j write failed: {e}")
        
        # Write to CouchDB (Document Storage)
        if self.db_manager.file_backend:
            total_attempts += 1
            try:
                # CouchDB stores full documents
                doc_data = {
                    "_id": chunk.chunk_id,
                    "content": chunk.content,
                    "metadata": asdict(chunk.metadata),
                    "chunk_type": chunk.chunk_type.value,
                    "created_at": datetime.now().isoformat(),
                }
                
                # add_documents expects List[Dict]
                if self.db_manager.file_backend.add_documents([doc_data]):
                    success_count += 1
                    logger.debug(f"✅ CouchDB write succeeded: {chunk.chunk_id}")
            except Exception as e:
                logger.error(f"❌ CouchDB write failed: {e}")
        
        # Return True if at least one backend succeeded
        success = success_count > 0
        logger.info(
            f"Write completed: {success_count}/{total_attempts} backends succeeded "
            f"for chunk {chunk.chunk_id}"
        )
        return success
    
    async def write_batch(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """
        Write multiple chunks in a batch operation.
        
        Writes to all configured backends using their batch operations.
        
        Args:
            chunks: List of chunks to persist
            
        Returns:
            Dictionary with write results:
            {
                "success": bool,
                "written": int,
                "failed": int,
                "errors": List[str],
                "backend_results": Dict[str, Dict]
            }
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info(
            f"Batch write: {len(chunks)} chunks",
            extra={
                "correlation_id": chunks[0].metadata.correlation_id if chunks else None,
                "job_id": chunks[0].metadata.job_id if chunks else None,
            }
        )
        
        # Write to all backends
        backend_results = {}
        for name, backend in self._backends.items():
            try:
                result = await backend.write_batch(chunks)
                backend_results[name] = result
                logger.info(
                    f"{name} batch: {result['written']} written, "
                    f"{result['failed']} failed"
                )
            except Exception as e:
                logger.error(f"{name} batch error: {e}")
                backend_results[name] = {
                    "success": False,
                    "written": 0,
                    "failed": len(chunks),
                    "errors": [str(e)],
                }
        
        # Aggregate results
        total_written = sum(r["written"] for r in backend_results.values())
        total_failed = sum(r["failed"] for r in backend_results.values())
        all_errors = []
        for name, result in backend_results.items():
            for error in result.get("errors", []):
                all_errors.append(f"{name}: {error}")
        
        return {
            "success": any(r["success"] for r in backend_results.values()),
            "written": total_written,
            "failed": total_failed,
            "errors": all_errors,
            "backend_results": backend_results,
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
        for name, backend in self._backends.items():
            try:
                is_healthy = await backend.health_check()
                health_status[name] = is_healthy
                logger.debug(f"{name} health: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            except Exception as e:
                logger.error(f"{name} health check error: {e}")
                health_status[name] = False
        
        # Return True only if all backends are healthy
        return all(health_status.values())
    
    async def initialize(self) -> None:
        """
        Initialize all UDS3 backend connections.
        """
        if self._initialized:
            return
        
        logger.info("Initializing UDS3 backends...")
        
        # Initialize all backends
        for name, backend in self._backends.items():
            try:
                await backend.initialize()
                logger.info(f"✅ {name} initialized")
            except Exception as e:
                logger.error(f"❌ {name} initialization failed: {e}")
                raise RuntimeError(f"{name} initialization failed: {e}")
        
        self._initialized = True
        logger.info(f"✅ UDS3Writer initialized ({len(self._backends)} backends)")
    
    async def close(self) -> None:
        """
        Close all UDS3 backend connections.
        """
        if not self._initialized:
            return
        
        logger.info("Closing UDS3 backends...")
        
        # Close all backends
        for name, backend in self._backends.items():
            try:
                await backend.close()
                logger.info(f"✅ {name} closed")
            except Exception as e:
                logger.error(f"❌ {name} close error: {e}")
        
        self._initialized = False
        logger.info("✅ UDS3Writer closed")
    
    @property
    def backend_status(self) -> Dict[str, bool]:
        """
        Get status of all UDS3 backends.
        
        Returns:
            Dictionary mapping backend names to initialization status
        """
        return {
            name: (name in self._backends)
            for name in ["postgresql", "chromadb", "neo4j", "couchdb"]
        }
