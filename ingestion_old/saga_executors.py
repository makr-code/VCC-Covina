#!/usr/bin/env python3
"""
SAGA Executors for Covina Ingestion Backend

Custom SAGA executors that integrate with UDS3 database backends.
These executors perform forward operations and compensations for multi-database transactions.

Author: Covina System
Date: 13. Oktober 2025
"""

import logging
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)


class CovinaSAGAExecutor:
    """
    Base SAGA Executor for Covina with direct UDS3 backend integration
    """
    
    def __init__(self, backend, database_name: str):
        self.backend = backend
        self.database_name = database_name
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def execute_forward(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute forward operation"""
        raise NotImplementedError
    
    async def execute_compensation(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute compensation (rollback)"""
        raise NotImplementedError


class PostgreSQLSAGAExecutor(CovinaSAGAExecutor):
    """SAGA Executor for PostgreSQL operations"""
    
    async def execute_forward(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute PostgreSQL insert operation
        
        Expected operation:
        {
            'action': 'insert_document',
            'params': {
                'document_id': str,
                'file_path': str,
                'classification': str,
                'content_length': int,
                'legal_terms_count': int,
                'timestamp': str,
                'quality_score': float
            }
        }
        """
        try:
            action = operation.get('action')
            params = operation.get('params', {})
            
            if action == 'insert_document':
                # Call UDS3 backend (sync, run in thread pool)
                await asyncio.to_thread(
                    self.backend.insert_document,
                    params['document_id'],
                    params['file_path'],
                    params['classification'],
                    params['content_length'],
                    params['legal_terms_count'],
                    params['timestamp'],
                    params['quality_score']
                )
                
                self.logger.info(f"✅ PostgreSQL insert: {params['document_id']}")
                return {'success': True, 'document_id': params['document_id']}
            
            else:
                raise ValueError(f"Unknown PostgreSQL action: {action}")
        
        except Exception as e:
            self.logger.error(f"❌ PostgreSQL forward operation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_compensation(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback PostgreSQL insert (delete document)
        
        Expected rollback_data:
        {
            'document_id': str
        }
        """
        try:
            document_id = rollback_data.get('document_id')
            
            if not document_id:
                raise ValueError("document_id required for compensation")
            
            # Delete document from PostgreSQL
            await asyncio.to_thread(
                self.backend.execute_query,
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,)
            )
            
            self.logger.info(f"🔄 PostgreSQL compensation: deleted {document_id}")
            return {'success': True, 'compensated': True}
        
        except Exception as e:
            self.logger.error(f"❌ PostgreSQL compensation failed: {e}")
            return {'success': False, 'error': str(e)}


class CouchDBSAGAExecutor(CovinaSAGAExecutor):
    """SAGA Executor for CouchDB operations"""
    
    async def execute_forward(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute CouchDB create document operation
        
        Expected operation:
        {
            'action': 'create_document',
            'params': {
                'doc_id': str,
                'doc_data': dict
            }
        }
        """
        try:
            action = operation.get('action')
            params = operation.get('params', {})
            
            if action == 'create_document':
                # Call UDS3 backend (sync, run in thread pool)
                await asyncio.to_thread(
                    self.backend.create_document,
                    params['doc_data'],
                    params['doc_id']
                )
                
                self.logger.info(f"✅ CouchDB insert: {params['doc_id']}")
                return {'success': True, 'doc_id': params['doc_id']}
            
            else:
                raise ValueError(f"Unknown CouchDB action: {action}")
        
        except Exception as e:
            self.logger.error(f"❌ CouchDB forward operation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_compensation(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback CouchDB insert (delete document)
        
        Expected rollback_data:
        {
            'doc_id': str
        }
        """
        try:
            doc_id = rollback_data.get('doc_id')
            
            if not doc_id:
                raise ValueError("doc_id required for compensation")
            
            # Delete document from CouchDB
            await asyncio.to_thread(
                self.backend.delete_document,
                doc_id
            )
            
            self.logger.info(f"🔄 CouchDB compensation: deleted {doc_id}")
            return {'success': True, 'compensated': True}
        
        except Exception as e:
            self.logger.error(f"❌ CouchDB compensation failed: {e}")
            return {'success': False, 'error': str(e)}


class ChromaDBSAGAExecutor(CovinaSAGAExecutor):
    """SAGA Executor for ChromaDB operations"""
    
    async def execute_forward(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute ChromaDB vector insert operation
        
        Expected operation:
        {
            'action': 'add_vectors',
            'params': {
                'document_id': str,
                'chunks': list,
                'metadata': dict
            }
        }
        """
        try:
            action = operation.get('action')
            params = operation.get('params', {})
            
            if action == 'add_vectors':
                document_id = params['document_id']
                chunks = params['chunks']
                metadata = params['metadata']
                
                # Generate embeddings and add to ChromaDB
                for idx, chunk in enumerate(chunks):
                    chunk_id = f"{document_id}_chunk_{idx}"
                    
                    # Generate embedding (using hash-based for now, can be replaced with real embeddings)
                    import hashlib
                    chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
                    fake_vector = [float(int(chunk_hash[i:i+2], 16)) / 255.0 for i in range(0, 384*2, 2)]
                    
                    chunk_metadata = {
                        **metadata,
                        'chunk_index': idx,
                        'chunk_text': chunk[:100]
                    }
                    
                    # Add vector to ChromaDB
                    await asyncio.to_thread(
                        self.backend.add_vector,
                        fake_vector,
                        chunk_metadata,
                        chunk_id
                    )
                
                self.logger.info(f"✅ ChromaDB insert: {document_id} ({len(chunks)} chunks)")
                return {'success': True, 'document_id': document_id, 'chunks_added': len(chunks)}
            
            else:
                raise ValueError(f"Unknown ChromaDB action: {action}")
        
        except Exception as e:
            self.logger.error(f"❌ ChromaDB forward operation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_compensation(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback ChromaDB insert (delete vectors)
        
        Expected rollback_data:
        {
            'document_id': str
        }
        """
        try:
            document_id = rollback_data.get('document_id')
            
            if not document_id:
                raise ValueError("document_id required for compensation")
            
            # Delete all vectors for this document (filter by document_id prefix)
            await asyncio.to_thread(
                self.backend.delete_vectors_by_filter,
                {'document_id': document_id}
            )
            
            self.logger.info(f"🔄 ChromaDB compensation: deleted vectors for {document_id}")
            return {'success': True, 'compensated': True}
        
        except Exception as e:
            self.logger.error(f"❌ ChromaDB compensation failed: {e}")
            return {'success': False, 'error': str(e)}


class Neo4jSAGAExecutor(CovinaSAGAExecutor):
    """SAGA Executor for Neo4j operations"""
    
    async def execute_forward(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Neo4j create node operation
        
        Expected operation:
        {
            'action': 'create_node',
            'params': {
                'document_id': str,
                'properties': dict
            }
        }
        """
        try:
            action = operation.get('action')
            params = operation.get('params', {})
            
            if action == 'create_node':
                document_id = params['document_id']
                properties = params['properties']
                
                # Create node in Neo4j
                cypher = """
                CREATE (d:Document {
                    document_id: $document_id,
                    file_path: $file_path,
                    classification: $classification,
                    legal_terms_count: $legal_terms_count,
                    quality_score: $quality_score,
                    created_at: datetime()
                })
                RETURN d
                """
                
                await asyncio.to_thread(
                    self.backend.execute_cypher,
                    cypher,
                    {
                        'document_id': document_id,
                        **properties
                    }
                )
                
                self.logger.info(f"✅ Neo4j insert: {document_id}")
                return {'success': True, 'document_id': document_id}
            
            else:
                raise ValueError(f"Unknown Neo4j action: {action}")
        
        except Exception as e:
            self.logger.error(f"❌ Neo4j forward operation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_compensation(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback Neo4j insert (delete node)
        
        Expected rollback_data:
        {
            'document_id': str
        }
        """
        try:
            document_id = rollback_data.get('document_id')
            
            if not document_id:
                raise ValueError("document_id required for compensation")
            
            # Delete node from Neo4j
            cypher = """
            MATCH (d:Document {document_id: $document_id})
            DETACH DELETE d
            """
            
            await asyncio.to_thread(
                self.backend.execute_cypher,
                cypher,
                {'document_id': document_id}
            )
            
            self.logger.info(f"🔄 Neo4j compensation: deleted {document_id}")
            return {'success': True, 'compensated': True}
        
        except Exception as e:
            self.logger.error(f"❌ Neo4j compensation failed: {e}")
            return {'success': False, 'error': str(e)}
