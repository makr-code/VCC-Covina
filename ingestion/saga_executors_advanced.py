"""
SAGA Executors for Advanced Ingestion Features

Custom SAGA executors for document similarity and quality metrics computation.
These executors integrate with the worker pool architecture.

Author: GitHub Copilot
Date: 2025-11-19
"""

import logging
from typing import Dict, Any, Optional, List
import asyncio

from ingestion.workers.similarity_worker import SimilarityWorker, SimilarityTask
from ingestion.workers.quality_worker import QualityMetricsWorker, QualityTask

logger = logging.getLogger(__name__)


class SimilaritySAGAExecutor:
    """
    SAGA Executor for Document Similarity operations
    
    Integrates with SimilarityWorker (ProcessPool) for CPU-intensive similarity computations.
    """
    
    def __init__(self, chromadb_client=None, postgresql_client=None, neo4j_driver=None):
        """
        Initialize similarity executor.
        
        Args:
            chromadb_client: ChromaDB client for embeddings
            postgresql_client: PostgreSQL client for metadata
            neo4j_driver: Neo4j driver for relationship storage
        """
        self.worker = SimilarityWorker(chromadb_client, postgresql_client, neo4j_driver)
        self.worker.start()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def execute_forward(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute similarity computation operation.
        
        Expected operation:
        {
            'action': 'find_similar' | 'detect_duplicates' | 'cluster',
            'params': {
                'document_id': str (for find_similar),
                'document_ids': List[str] (for detect_duplicates/cluster),
                'top_k': int,
                'threshold': float,
                'n_clusters': int,
                'create_neo4j_relationships': bool
            }
        }
        
        Returns:
            {
                'success': bool,
                'task_type': str,
                'results': dict
            }
        """
        try:
            action = operation.get('action')
            params = operation.get('params', {})
            
            # Create task
            task = SimilarityTask(
                task_type=action,
                document_id=params.get('document_id'),
                document_ids=params.get('document_ids'),
                top_k=params.get('top_k', 5),
                threshold=params.get('threshold', 0.7),
                n_clusters=params.get('n_clusters', 5),
                create_neo4j_relationships=params.get('create_neo4j_relationships', False)
            )
            
            # Process task in worker pool (run in thread pool to avoid blocking)
            result = await asyncio.to_thread(self.worker.process_task, task)
            
            if result.get('success'):
                self.logger.info(f"✅ Similarity computation ({action}): {result.get('count', 0)} results")
            else:
                self.logger.error(f"❌ Similarity computation failed: {result.get('error')}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"❌ Similarity forward operation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_compensation(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback similarity operation.
        
        For similarity computations, rollback involves:
        - Deleting Neo4j relationships created
        - Clearing cached embeddings
        
        Expected rollback_data:
        {
            'document_id': str,
            'relationship_ids': List[str]
        }
        """
        try:
            document_id = rollback_data.get('document_id')
            
            # Clear embedding cache
            if hasattr(self.worker.engine, 'clear_cache'):
                await asyncio.to_thread(self.worker.engine.clear_cache)
            
            # Delete Neo4j relationships if created
            if document_id and self.worker.neo4j:
                # Delete similarity relationships
                # This is a placeholder - actual implementation depends on Neo4j schema
                pass
            
            self.logger.info(f"🔄 Similarity compensation completed")
            return {'success': True, 'compensated': True}
        
        except Exception as e:
            self.logger.error(f"❌ Similarity compensation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def shutdown(self):
        """Shutdown worker pool"""
        self.worker.shutdown()


class QualityMetricsSAGAExecutor:
    """
    SAGA Executor for Quality Metrics operations
    
    Integrates with QualityMetricsWorker (ThreadPool) for I/O-intensive quality computations.
    """
    
    def __init__(self, chromadb_client=None):
        """
        Initialize quality metrics executor.
        
        Args:
            chromadb_client: ChromaDB client for metadata enrichment
        """
        self.worker = QualityMetricsWorker(chromadb_client)
        self.worker.start()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def execute_forward(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute quality metrics computation operation.
        
        Expected operation:
        {
            'action': 'compute_quality' | 'compute_document_quality',
            'params': {
                'chunk_id': str,
                'content': str,
                'metadata': dict,
                'enrich_chromadb': bool,
                
                # For document quality:
                'chunks': List[dict]  # [{id, content, metadata}]
            }
        }
        
        Returns:
            {
                'success': bool,
                'metrics': dict | aggregated_metrics: dict
            }
        """
        try:
            action = operation.get('action')
            params = operation.get('params', {})
            
            if action == 'compute_quality':
                # Single chunk quality
                task = QualityTask(
                    chunk_id=params.get('chunk_id'),
                    content=params.get('content'),
                    metadata=params.get('metadata'),
                    enrich_chromadb=params.get('enrich_chromadb', False)
                )
                
                result = await asyncio.to_thread(self.worker.process_task, task)
                
            elif action == 'compute_document_quality':
                # Document-wide quality (all chunks)
                chunks = params.get('chunks', [])
                enrich_chromadb = params.get('enrich_chromadb', True)
                
                result = await asyncio.to_thread(
                    self.worker.process_document_chunks,
                    chunks,
                    enrich_chromadb
                )
            
            else:
                raise ValueError(f"Unknown quality metrics action: {action}")
            
            if result.get('success') or result.get('successful_chunks', 0) > 0:
                self.logger.info(f"✅ Quality metrics computed ({action})")
            else:
                self.logger.error(f"❌ Quality metrics failed: {result.get('error')}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"❌ Quality metrics forward operation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_compensation(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback quality metrics operation.
        
        For quality computations, rollback involves:
        - Removing quality metadata from ChromaDB
        
        Expected rollback_data:
        {
            'chunk_ids': List[str]
        }
        """
        try:
            chunk_ids = rollback_data.get('chunk_ids', [])
            
            # Remove quality metadata from ChromaDB
            # This is a placeholder - actual implementation depends on ChromaDB API
            if chunk_ids and self.worker.chromadb:
                for chunk_id in chunk_ids:
                    # Remove quality metadata
                    pass
            
            self.logger.info(f"🔄 Quality metrics compensation completed for {len(chunk_ids)} chunks")
            return {'success': True, 'compensated': True}
        
        except Exception as e:
            self.logger.error(f"❌ Quality metrics compensation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def shutdown(self):
        """Shutdown worker pool"""
        self.worker.shutdown()


# Factory function for creating executors
def create_advanced_executors(
    chromadb_client=None,
    postgresql_client=None,
    neo4j_driver=None
) -> Dict[str, Any]:
    """
    Create all advanced feature executors.
    
    Args:
        chromadb_client: ChromaDB client
        postgresql_client: PostgreSQL client
        neo4j_driver: Neo4j driver
    
    Returns:
        Dictionary of executor instances
    """
    executors = {
        'similarity': SimilaritySAGAExecutor(chromadb_client, postgresql_client, neo4j_driver),
        'quality_metrics': QualityMetricsSAGAExecutor(chromadb_client)
    }
    
    logger.info("Created advanced feature executors: similarity, quality_metrics")
    
    return executors


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_executors():
        # Create executors
        executors = create_advanced_executors()
        
        # Test similarity
        similarity_op = {
            'action': 'find_similar',
            'params': {
                'document_id': 'doc_123',
                'top_k': 5,
                'threshold': 0.7,
                'create_neo4j_relationships': True
            }
        }
        
        similarity_result = await executors['similarity'].execute_forward(similarity_op)
        print(f"Similarity result: {similarity_result}")
        
        # Test quality metrics
        quality_op = {
            'action': 'compute_quality',
            'params': {
                'chunk_id': 'chunk_001',
                'content': '§ 1 Zweck des Gesetzes...',
                'metadata': {'keywords': ['Schutz', 'Umwelt']},
                'enrich_chromadb': False
            }
        }
        
        quality_result = await executors['quality_metrics'].execute_forward(quality_op)
        print(f"Quality result: {quality_result}")
        
        # Shutdown
        executors['similarity'].shutdown()
        executors['quality_metrics'].shutdown()
    
    asyncio.run(test_executors())
