"""
Document Similarity Worker

CPU-intensive worker for computing document similarities using embeddings.
Runs in ProcessPool to avoid GIL limitations.

Features:
- Cosine similarity computation
- Similar document search
- Duplicate detection
- Document clustering
- Neo4j relationship creation

Author: GitHub Copilot
Date: 2025-11-19
"""

import logging
import multiprocessing
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

from ingestion.document_similarity import (
    DocumentSimilarityEngine,
    SimilarityResult,
    DocumentCluster
)

logger = logging.getLogger(__name__)


@dataclass
class SimilarityTask:
    """Task for similarity computation"""
    task_type: str  # 'find_similar', 'detect_duplicates', 'cluster'
    document_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    top_k: int = 5
    threshold: float = 0.7
    n_clusters: int = 5
    create_neo4j_relationships: bool = False


class SimilarityWorker:
    """
    Worker for document similarity computations.
    
    Architecture:
    - Runs in ProcessPool (CPU-intensive: embedding operations)
    - Integrates with ChromaDB (embeddings), PostgreSQL (metadata), Neo4j (relationships)
    - Supports batch processing
    """
    
    def __init__(
        self,
        chromadb_client=None,
        postgresql_client=None,
        neo4j_driver=None,
        num_workers: int = None
    ):
        """
        Initialize similarity worker.
        
        Args:
            chromadb_client: ChromaDB client for embeddings
            postgresql_client: PostgreSQL client for metadata
            neo4j_driver: Neo4j driver for relationship storage
            num_workers: Number of worker processes (default: CPU count)
        """
        self.chromadb = chromadb_client
        self.postgresql = postgresql_client
        self.neo4j = neo4j_driver
        
        if num_workers is None:
            num_workers = max(1, multiprocessing.cpu_count() - 1)
        
        self.num_workers = num_workers
        self.executor = None
        self.engine = DocumentSimilarityEngine(chromadb_client, postgresql_client, neo4j_driver)
    
    def start(self):
        """Start worker pool"""
        if self.executor is None:
            self.executor = ProcessPoolExecutor(max_workers=self.num_workers)
            logger.info(f"Started SimilarityWorker with {self.num_workers} processes")
    
    def shutdown(self, wait: bool = True):
        """Shutdown worker pool"""
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None
            logger.info("Shut down SimilarityWorker")
    
    def process_task(self, task: SimilarityTask) -> Dict[str, Any]:
        """
        Process a similarity task.
        
        Args:
            task: SimilarityTask object
        
        Returns:
            Result dictionary with task results
        """
        try:
            if task.task_type == 'find_similar':
                return self._find_similar(task)
            
            elif task.task_type == 'detect_duplicates':
                return self._detect_duplicates(task)
            
            elif task.task_type == 'cluster':
                return self._cluster_documents(task)
            
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
        
        except Exception as e:
            logger.error(f"Error processing similarity task: {e}")
            return {'success': False, 'error': str(e)}
    
    def _find_similar(self, task: SimilarityTask) -> Dict[str, Any]:
        """Find similar documents"""
        if not task.document_id:
            return {'success': False, 'error': 'document_id required'}
        
        # Find similar documents
        similar_docs = self.engine.find_similar_documents(
            task.document_id,
            top_k=task.top_k,
            threshold=task.threshold
        )
        
        # Optionally create Neo4j relationships
        if task.create_neo4j_relationships and self.neo4j:
            count = self.engine.create_similarity_relationships_neo4j(
                task.document_id,
                similar_docs
            )
            logger.info(f"Created {count} similarity relationships in Neo4j")
        
        return {
            'success': True,
            'task_type': 'find_similar',
            'document_id': task.document_id,
            'similar_documents': [s.to_dict() for s in similar_docs],
            'count': len(similar_docs)
        }
    
    def _detect_duplicates(self, task: SimilarityTask) -> Dict[str, Any]:
        """Detect duplicate documents"""
        duplicates = self.engine.detect_duplicates(
            threshold=task.threshold,
            document_ids=task.document_ids
        )
        
        return {
            'success': True,
            'task_type': 'detect_duplicates',
            'duplicates': [
                {
                    'doc_id_1': doc1,
                    'doc_id_2': doc2,
                    'similarity_score': score
                }
                for doc1, doc2, score in duplicates
            ],
            'count': len(duplicates)
        }
    
    def _cluster_documents(self, task: SimilarityTask) -> Dict[str, Any]:
        """Cluster documents"""
        if not task.document_ids:
            return {'success': False, 'error': 'document_ids required'}
        
        clusters = self.engine.cluster_documents(
            task.document_ids,
            n_clusters=task.n_clusters
        )
        
        return {
            'success': True,
            'task_type': 'cluster',
            'clusters': [c.to_dict() for c in clusters],
            'count': len(clusters)
        }
    
    def process_batch(self, tasks: List[SimilarityTask]) -> List[Dict[str, Any]]:
        """
        Process multiple tasks in parallel.
        
        Args:
            tasks: List of SimilarityTask objects
        
        Returns:
            List of result dictionaries
        """
        if not self.executor:
            self.start()
        
        # Submit all tasks
        futures = {
            self.executor.submit(self.process_task, task): i
            for i, task in enumerate(tasks)
        }
        
        # Collect results
        results = [None] * len(tasks)
        for future in as_completed(futures):
            index = futures[future]
            try:
                results[index] = future.result()
            except Exception as e:
                logger.error(f"Task {index} failed: {e}")
                results[index] = {'success': False, 'error': str(e)}
        
        return results


# Standalone function for ProcessPool execution
def compute_similarity_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standalone function for similarity computation in ProcessPool.
    
    This function can be pickled and sent to worker processes.
    
    Args:
        task_data: Task configuration dictionary
    
    Returns:
        Result dictionary
    """
    # Initialize engine in worker process
    # Note: Database clients need to be recreated in worker process
    from ingestion.document_similarity import DocumentSimilarityEngine
    
    engine = DocumentSimilarityEngine()
    
    task_type = task_data['task_type']
    
    if task_type == 'find_similar':
        similar_docs = engine.find_similar_documents(
            task_data['document_id'],
            top_k=task_data.get('top_k', 5),
            threshold=task_data.get('threshold', 0.7)
        )
        
        return {
            'success': True,
            'task_type': 'find_similar',
            'document_id': task_data['document_id'],
            'similar_documents': [s.to_dict() for s in similar_docs],
            'count': len(similar_docs)
        }
    
    elif task_type == 'detect_duplicates':
        duplicates = engine.detect_duplicates(
            threshold=task_data.get('threshold', 0.95),
            document_ids=task_data.get('document_ids')
        )
        
        return {
            'success': True,
            'task_type': 'detect_duplicates',
            'duplicates': [
                {
                    'doc_id_1': doc1,
                    'doc_id_2': doc2,
                    'similarity_score': score
                }
                for doc1, doc2, score in duplicates
            ],
            'count': len(duplicates)
        }
    
    elif task_type == 'cluster':
        clusters = engine.cluster_documents(
            task_data['document_ids'],
            n_clusters=task_data.get('n_clusters', 5)
        )
        
        return {
            'success': True,
            'task_type': 'cluster',
            'clusters': [c.to_dict() for c in clusters],
            'count': len(clusters)
        }
    
    else:
        return {'success': False, 'error': f"Unknown task type: {task_type}"}


# Example usage
if __name__ == "__main__":
    # Initialize worker
    worker = SimilarityWorker(num_workers=4)
    worker.start()
    
    # Create tasks
    tasks = [
        SimilarityTask(
            task_type='find_similar',
            document_id='doc_123',
            top_k=5,
            create_neo4j_relationships=True
        ),
        SimilarityTask(
            task_type='detect_duplicates',
            threshold=0.95
        )
    ]
    
    # Process batch
    results = worker.process_batch(tasks)
    
    for result in results:
        print(f"Task: {result.get('task_type')}")
        print(f"Success: {result.get('success')}")
        print(f"Count: {result.get('count')}")
        print()
    
    # Shutdown
    worker.shutdown()
