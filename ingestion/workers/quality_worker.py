"""
Quality Metrics Worker

I/O-intensive worker for computing quality metrics on document chunks.
Runs in ThreadPool for efficient I/O operations.

Features:
- Advanced quality scoring (completeness, readability, info density, structural, language)
- Batch processing
- Metadata enrichment
- ChromaDB integration

Author: GitHub Copilot
Date: 2025-11-19
"""

import logging
import threading
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from ingestion.quality_metrics import AdvancedQualityScorer, QualityMetrics

logger = logging.getLogger(__name__)


@dataclass
class QualityTask:
    """Task for quality metrics computation"""
    chunk_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    enrich_chromadb: bool = False


class QualityMetricsWorker:
    """
    Worker for quality metrics computation.
    
    Architecture:
    - Runs in ThreadPool (I/O-intensive: text processing, database updates)
    - Integrates with ChromaDB for metadata enrichment
    - Supports batch processing for efficiency
    """
    
    def __init__(
        self,
        chromadb_client=None,
        num_workers: int = 36
    ):
        """
        Initialize quality metrics worker.
        
        Args:
            chromadb_client: ChromaDB client for metadata enrichment
            num_workers: Number of worker threads (default: 36 for I/O)
        """
        self.chromadb = chromadb_client
        self.num_workers = num_workers
        self.executor = None
        self.scorer = AdvancedQualityScorer()
        self._lock = threading.Lock()
    
    def start(self):
        """Start worker pool"""
        if self.executor is None:
            self.executor = ThreadPoolExecutor(
                max_workers=self.num_workers,
                thread_name_prefix='QualityWorker'
            )
            logger.info(f"Started QualityMetricsWorker with {self.num_workers} threads")
    
    def shutdown(self, wait: bool = True):
        """Shutdown worker pool"""
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None
            logger.info("Shut down QualityMetricsWorker")
    
    def process_task(self, task: QualityTask) -> Dict[str, Any]:
        """
        Process a quality metrics task.
        
        Args:
            task: QualityTask object
        
        Returns:
            Result dictionary with quality metrics
        """
        try:
            # Compute quality metrics
            metrics = self.scorer.compute_quality(task.content, task.metadata)
            
            # Optionally enrich ChromaDB
            if task.enrich_chromadb and self.chromadb:
                self._enrich_chromadb(task.chunk_id, metrics)
            
            return {
                'success': True,
                'chunk_id': task.chunk_id,
                'metrics': metrics.to_dict()
            }
        
        except Exception as e:
            logger.error(f"Error processing quality task for {task.chunk_id}: {e}")
            return {
                'success': False,
                'chunk_id': task.chunk_id,
                'error': str(e)
            }
    
    def _enrich_chromadb(self, chunk_id: str, metrics: QualityMetrics):
        """
        Enrich ChromaDB chunk with quality metrics.
        
        Args:
            chunk_id: Chunk ID in ChromaDB
            metrics: QualityMetrics object
        """
        try:
            # Update metadata in ChromaDB
            # Note: This assumes ChromaDB supports metadata updates
            quality_metadata = {
                'quality_overall': metrics.overall_score,
                'quality_completeness': metrics.completeness_score,
                'quality_readability': metrics.readability_score,
                'quality_info_density': metrics.information_density_score,
                'quality_structural': metrics.structural_quality_score,
                'quality_language': metrics.language_quality_score,
                'word_count': metrics.word_count,
                'sentence_count': metrics.sentence_count,
                'unique_word_ratio': metrics.unique_word_ratio,
                'has_headings': metrics.has_headings,
                'has_lists': metrics.has_lists,
                'has_references': metrics.has_references
            }
            
            # Update ChromaDB (thread-safe)
            with self._lock:
                # Implementation depends on ChromaDB API
                # This is a placeholder for the update operation
                if hasattr(self.chromadb, 'update_metadata'):
                    self.chromadb.update_metadata(chunk_id, quality_metadata)
                else:
                    logger.warning("ChromaDB update_metadata not available")
            
            logger.debug(f"Enriched ChromaDB chunk {chunk_id} with quality metrics")
        
        except Exception as e:
            logger.error(f"Error enriching ChromaDB for {chunk_id}: {e}")
    
    def process_batch(self, tasks: List[QualityTask]) -> List[Dict[str, Any]]:
        """
        Process multiple tasks in parallel.
        
        Args:
            tasks: List of QualityTask objects
        
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
    
    def process_document_chunks(
        self,
        chunks: List[Dict[str, Any]],
        enrich_chromadb: bool = True
    ) -> Dict[str, Any]:
        """
        Process all chunks of a document.
        
        Args:
            chunks: List of chunk dictionaries with 'id', 'content', 'metadata'
            enrich_chromadb: Whether to enrich ChromaDB with metrics
        
        Returns:
            Aggregated statistics and individual results
        """
        # Create tasks
        tasks = [
            QualityTask(
                chunk_id=chunk['id'],
                content=chunk['content'],
                metadata=chunk.get('metadata'),
                enrich_chromadb=enrich_chromadb
            )
            for chunk in chunks
        ]
        
        # Process batch
        results = self.process_batch(tasks)
        
        # Aggregate statistics
        successful_results = [r for r in results if r.get('success')]
        
        if successful_results:
            avg_overall = sum(r['metrics']['overall_score'] for r in successful_results) / len(successful_results)
            avg_completeness = sum(r['metrics']['completeness_score'] for r in successful_results) / len(successful_results)
            avg_readability = sum(r['metrics']['readability_score'] for r in successful_results) / len(successful_results)
            avg_info_density = sum(r['metrics']['information_density_score'] for r in successful_results) / len(successful_results)
            
            total_words = sum(r['metrics']['word_count'] for r in successful_results)
            total_sentences = sum(r['metrics']['sentence_count'] for r in successful_results)
            
            chunks_with_headings = sum(1 for r in successful_results if r['metrics']['has_headings'])
            chunks_with_lists = sum(1 for r in successful_results if r['metrics']['has_lists'])
            chunks_with_references = sum(1 for r in successful_results if r['metrics']['has_references'])
        else:
            avg_overall = 0.0
            avg_completeness = 0.0
            avg_readability = 0.0
            avg_info_density = 0.0
            total_words = 0
            total_sentences = 0
            chunks_with_headings = 0
            chunks_with_lists = 0
            chunks_with_references = 0
        
        return {
            'total_chunks': len(chunks),
            'successful_chunks': len(successful_results),
            'failed_chunks': len(results) - len(successful_results),
            'aggregated_metrics': {
                'avg_overall_score': avg_overall,
                'avg_completeness_score': avg_completeness,
                'avg_readability_score': avg_readability,
                'avg_info_density_score': avg_info_density,
                'total_words': total_words,
                'total_sentences': total_sentences,
                'chunks_with_headings': chunks_with_headings,
                'chunks_with_lists': chunks_with_lists,
                'chunks_with_references': chunks_with_references
            },
            'individual_results': results
        }


# Standalone function for ThreadPool execution
def compute_quality_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standalone function for quality computation in ThreadPool.
    
    Args:
        task_data: Task configuration dictionary
    
    Returns:
        Result dictionary with quality metrics
    """
    from ingestion.quality_metrics import AdvancedQualityScorer
    
    scorer = AdvancedQualityScorer()
    
    try:
        metrics = scorer.compute_quality(
            task_data['content'],
            task_data.get('metadata')
        )
        
        return {
            'success': True,
            'chunk_id': task_data['chunk_id'],
            'metrics': metrics.to_dict()
        }
    
    except Exception as e:
        return {
            'success': False,
            'chunk_id': task_data['chunk_id'],
            'error': str(e)
        }


# Example usage
if __name__ == "__main__":
    # Initialize worker
    worker = QualityMetricsWorker(num_workers=36)
    worker.start()
    
    # Sample chunks
    chunks = [
        {
            'id': 'chunk_001',
            'content': '§ 1 Zweck des Gesetzes\n\n(1) Zweck dieses Gesetzes ist es...',
            'metadata': {
                'entities': {'LOC': ['Deutschland']},
                'keywords': ['Schutz', 'Umwelt']
            }
        },
        {
            'id': 'chunk_002',
            'content': '(2) Soweit es sich um genehmigungsbedürftige Anlagen handelt...',
            'metadata': {}
        }
    ]
    
    # Process document chunks
    result = worker.process_document_chunks(chunks, enrich_chromadb=False)
    
    print(f"Total chunks: {result['total_chunks']}")
    print(f"Successful: {result['successful_chunks']}")
    print(f"Average overall score: {result['aggregated_metrics']['avg_overall_score']:.2f}")
    print(f"Average readability: {result['aggregated_metrics']['avg_readability_score']:.2f}")
    print(f"Chunks with headings: {result['aggregated_metrics']['chunks_with_headings']}")
    
    # Shutdown
    worker.shutdown()
