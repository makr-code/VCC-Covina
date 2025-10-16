#!/usr/bin/env python3
"""
Document Reconstruction Engine (Phase 4)
Enhanced Covina Backend v1.0.0 - Multi-Database Distribution System

Dieses Modul implementiert die DocumentReconstructor Klasse für die intelligente
Wiederherstellung kompletter Dokumente aus Multi-Database Distribution.

Features:
- Multi-Database Content Aggregation
- Intelligent Document Reassembly  
- Performance-Optimized Reconstruction
- Cross-Database Reference Resolution
- Content Integrity Validation
- Adaptive Reconstruction Strategies
"""

import asyncio
import logging
import time
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

# UDS3 Framework Imports
from .uds3_multi_db_distributor import UDS3MultiDBDistributor, ProcessorResult, ProcessorType
from .adaptive_multi_db_strategy import AdaptiveMultiDBStrategy, StrategyType

class ReconstructionStrategy(Enum):
    """Document Reconstruction Strategies"""
    FULL_RECONSTRUCTION = "full_reconstruction"
    PARTIAL_RECONSTRUCTION = "partial_reconstruction"
    STREAMING_RECONSTRUCTION = "streaming_reconstruction"
    PRIORITY_CONTENT_FIRST = "priority_content_first"
    METADATA_LIGHTWEIGHT = "metadata_lightweight"

class ContentPriority(Enum):
    """Content Reconstruction Priorities"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"

@dataclass
class ReconstructionTarget:
    """Target for document reconstruction"""
    document_id: str
    processor_results: List[str] = field(default_factory=list)
    database_sources: Dict[str, List[str]] = field(default_factory=dict)
    content_types: List[str] = field(default_factory=list)
    priority: ContentPriority = ContentPriority.MEDIUM
    reconstruction_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReconstructedContent:
    """Reconstructed content piece"""
    content_id: str
    content_type: str
    source_database: str
    content_data: Dict[str, Any]
    metadata: Dict[str, Any]
    reconstruction_timestamp: str
    confidence_score: float = 1.0
    integrity_verified: bool = False

@dataclass
class DocumentReconstructionResult:
    """Result of document reconstruction process"""
    document_id: str
    reconstruction_id: str
    success: bool
    reconstructed_content: Dict[str, ReconstructedContent] = field(default_factory=dict)
    missing_content: List[str] = field(default_factory=list)
    reconstruction_time_ms: float = 0.0
    content_completeness: float = 0.0
    integrity_score: float = 0.0
    strategy_used: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class DocumentReconstructor:
    """
    Enhanced Document Reconstruction Engine
    
    Intelligente Wiederherstellung kompletter Dokumente aus Multi-Database Distribution
    mit adaptiven Strategien und Performance-Optimierung.
    """
    
    def __init__(
        self,
        adaptive_strategy: AdaptiveMultiDBStrategy,
        distributor: Optional[UDS3MultiDBDistributor] = None,
        config: Optional[Dict] = None
    ):
        self.adaptive_strategy = adaptive_strategy
        self.distributor = distributor
        self.config = config or {}
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Reconstruction configuration
        self.default_strategy = ReconstructionStrategy.FULL_RECONSTRUCTION
        self.max_concurrent_reconstructions = self.config.get('max_concurrent_reconstructions', 5)
        self.reconstruction_timeout_seconds = self.config.get('reconstruction_timeout_seconds', 30)
        self.content_integrity_check = self.config.get('content_integrity_check', True)
        
        # Performance tracking
        self.reconstruction_stats = {
            'total_reconstructions': 0,
            'successful_reconstructions': 0,
            'failed_reconstructions': 0,
            'average_reconstruction_time_ms': 0.0,
            'average_content_completeness': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Content reconstruction cache
        self.content_cache: Dict[str, ReconstructedContent] = {}
        self.cache_ttl_seconds = self.config.get('cache_ttl_seconds', 300)
        
        # Database source mapping  
        self.database_content_mapping = {
            'postgresql': ['master_registry', 'processor_results', 'document_content', 'metadata_enrichment'],
            'couchdb': ['binary_content', 'attachments', 'large_documents'],
            'chromadb': ['vector_embeddings', 'similarity_data', 'search_indices'],
            'neo4j': ['relationships', 'graph_data', 'entity_connections'],
            'sqlite': ['fallback_content', 'basic_metadata', 'processing_logs']
        }
        
        self.logger.info("DocumentReconstructor initialized with Multi-DB reconstruction capabilities")
    
    async def reconstruct_document(
        self,
        document_id: str,
        reconstruction_strategy: Optional[ReconstructionStrategy] = None,
        target_content_types: Optional[List[str]] = None,
        priority_filter: Optional[ContentPriority] = None
    ) -> DocumentReconstructionResult:
        """
        Main document reconstruction method
        
        Args:
            document_id: ID of document to reconstruct
            reconstruction_strategy: Strategy to use for reconstruction
            target_content_types: Specific content types to reconstruct
            priority_filter: Minimum priority level for content
            
        Returns:
            DocumentReconstructionResult with reconstructed content
        """
        
        start_time = time.time()
        reconstruction_id = str(uuid.uuid4())
        
        self.logger.info(f"Starting document reconstruction for {document_id}")
        
        try:
            self.reconstruction_stats['total_reconstructions'] += 1
            
            # 1. Determine reconstruction strategy
            strategy = reconstruction_strategy or self._determine_optimal_strategy(document_id)
            
            # 2. Identify content sources across databases
            content_sources = await self._identify_content_sources(document_id)
            
            # 3. Create reconstruction plan
            reconstruction_plan = await self._create_reconstruction_plan(
                document_id, content_sources, strategy, target_content_types, priority_filter
            )
            
            # 4. Execute reconstruction across databases
            reconstructed_content = await self._execute_reconstruction(
                reconstruction_id, document_id, reconstruction_plan, strategy
            )
            
            # 5. Validate content integrity
            if self.content_integrity_check:
                await self._validate_content_integrity(reconstructed_content)
            
            # 6. Calculate completeness metrics
            completeness_metrics = self._calculate_completeness_metrics(
                reconstruction_plan, reconstructed_content
            )
            
            reconstruction_time = (time.time() - start_time) * 1000
            
            result = DocumentReconstructionResult(
                document_id=document_id,
                reconstruction_id=reconstruction_id,
                success=len(reconstructed_content) > 0,
                reconstructed_content=reconstructed_content,
                missing_content=completeness_metrics['missing_content'],
                reconstruction_time_ms=reconstruction_time,
                content_completeness=completeness_metrics['completeness_ratio'],
                integrity_score=completeness_metrics['integrity_score'],
                strategy_used=strategy.value
            )
            
            # Update statistics
            if result.success:
                self.reconstruction_stats['successful_reconstructions'] += 1
                
                # Update average metrics
                total_recons = self.reconstruction_stats['total_reconstructions']
                current_avg_time = self.reconstruction_stats['average_reconstruction_time_ms']
                self.reconstruction_stats['average_reconstruction_time_ms'] = (
                    (current_avg_time * (total_recons - 1) + reconstruction_time) / total_recons
                )
                
                current_avg_completeness = self.reconstruction_stats['average_content_completeness']
                self.reconstruction_stats['average_content_completeness'] = (
                    (current_avg_completeness * (total_recons - 1) + result.content_completeness) / total_recons
                )
            else:
                self.reconstruction_stats['failed_reconstructions'] += 1
            
            self.logger.info(
                f"Document reconstruction completed for {document_id}: "
                f"{reconstruction_time:.1f}ms, Completeness: {result.content_completeness:.2%}"
            )
            
            return result
            
        except Exception as e:
            reconstruction_time = (time.time() - start_time) * 1000
            self.reconstruction_stats['failed_reconstructions'] += 1
            
            self.logger.error(f"Document reconstruction failed for {document_id}: {e}")
            
            return DocumentReconstructionResult(
                document_id=document_id,
                reconstruction_id=reconstruction_id,
                success=False,
                reconstruction_time_ms=reconstruction_time,
                strategy_used=strategy.value if 'strategy' in locals() else 'unknown',
                errors=[f"Reconstruction failed: {str(e)}"]
            )
    
    def _determine_optimal_strategy(self, document_id: str) -> ReconstructionStrategy:
        """Determines optimal reconstruction strategy based on current conditions"""
        
        # Get current adaptive strategy state
        current_strategy = self.adaptive_strategy.current_strategy
        available_dbs = self._get_available_databases()
        
        # Strategy selection logic
        if current_strategy == StrategyType.FULL_POLYGLOT and len(available_dbs) >= 4:
            return ReconstructionStrategy.FULL_RECONSTRUCTION
        elif current_strategy == StrategyType.DUAL_STORE_OPTIMIZATION:
            return ReconstructionStrategy.PRIORITY_CONTENT_FIRST
        elif current_strategy == StrategyType.SQLITE_MONOLITH:
            return ReconstructionStrategy.METADATA_LIGHTWEIGHT
        else:
            return ReconstructionStrategy.PARTIAL_RECONSTRUCTION
    
    def _get_available_databases(self) -> Dict[str, bool]:
        """Gets available databases from adaptive strategy"""
        
        if self.adaptive_strategy and self.adaptive_strategy.db_availability:
            return {
                'postgresql': self.adaptive_strategy.db_availability.postgresql,
                'couchdb': self.adaptive_strategy.db_availability.couchdb,
                'chromadb': self.adaptive_strategy.db_availability.chromadb,
                'neo4j': self.adaptive_strategy.db_availability.neo4j,
                'sqlite': self.adaptive_strategy.db_availability.sqlite
            }
        
        # Fallback: assume only SQLite available
        return {
            'postgresql': False,
            'couchdb': False,
            'chromadb': False,
            'neo4j': False,
            'sqlite': True
        }
    
    async def _identify_content_sources(self, document_id: str) -> Dict[str, List[str]]:
        """Identifies content sources across databases for the document"""
        
        content_sources = {}
        available_dbs = self._get_available_databases()
        
        # Check each available database for content
        for db_name, is_available in available_dbs.items():
            if is_available and db_name in self.database_content_mapping:
                # Simulate content discovery - in production this would query actual databases
                potential_content = self.database_content_mapping[db_name]
                
                # Mock content existence check
                found_content = []
                for content_type in potential_content:
                    # Simulate 80% chance of finding each content type
                    import random
                    if random.random() < 0.8:
                        found_content.append(f"{content_type}_{document_id}")
                
                if found_content:
                    content_sources[db_name] = found_content
        
        self.logger.debug(f"Identified content sources for {document_id}: {list(content_sources.keys())}")
        
        return content_sources
    
    async def _create_reconstruction_plan(
        self,
        document_id: str,
        content_sources: Dict[str, List[str]],
        strategy: ReconstructionStrategy,
        target_content_types: Optional[List[str]] = None,
        priority_filter: Optional[ContentPriority] = None
    ) -> Dict[str, List[ReconstructionTarget]]:
        """Creates intelligent reconstruction plan based on strategy and available content"""
        
        reconstruction_plan = {}
        
        # Priority mapping for different content types
        content_priorities = {
            'master_registry': ContentPriority.CRITICAL,
            'processor_results': ContentPriority.HIGH,
            'document_content': ContentPriority.HIGH,
            'binary_content': ContentPriority.MEDIUM,
            'vector_embeddings': ContentPriority.MEDIUM,
            'relationships': ContentPriority.LOW,
            'metadata_enrichment': ContentPriority.LOW,
            'fallback_content': ContentPriority.OPTIONAL
        }
        
        for db_name, content_items in content_sources.items():
            db_targets = []
            
            for content_item in content_items:
                # Extract content type from item name
                content_type = content_item.split('_')[0] if '_' in content_item else content_item
                
                # Apply filters
                if target_content_types and content_type not in target_content_types:
                    continue
                
                content_priority = content_priorities.get(content_type, ContentPriority.MEDIUM)
                if priority_filter and content_priority.value > priority_filter.value:
                    continue
                
                # Create reconstruction target
                target = ReconstructionTarget(
                    document_id=document_id,
                    processor_results=[content_item],
                    database_sources={db_name: [content_item]},
                    content_types=[content_type],
                    priority=content_priority,
                    reconstruction_metadata={
                        'strategy': strategy.value,
                        'source_db': db_name,
                        'estimated_size': 'medium'
                    }
                )
                
                db_targets.append(target)
            
            if db_targets:
                reconstruction_plan[db_name] = db_targets
        
        self.logger.debug(f"Created reconstruction plan for {document_id}: {len(reconstruction_plan)} databases")
        
        return reconstruction_plan
    
    async def _execute_reconstruction(
        self,
        reconstruction_id: str,
        document_id: str,
        reconstruction_plan: Dict[str, List[ReconstructionTarget]],
        strategy: ReconstructionStrategy
    ) -> Dict[str, ReconstructedContent]:
        """Executes reconstruction across multiple databases"""
        
        reconstructed_content = {}
        
        # Determine execution order based on strategy
        execution_order = self._determine_execution_order(reconstruction_plan, strategy)
        
        # Execute reconstruction with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_reconstructions)
        
        async def reconstruct_target(db_name: str, target: ReconstructionTarget):
            async with semaphore:
                return await self._reconstruct_content_from_database(
                    db_name, target, reconstruction_id
                )
        
        # Execute all reconstruction tasks
        tasks = []
        for db_name in execution_order:
            if db_name in reconstruction_plan:
                for target in reconstruction_plan[db_name]:
                    tasks.append(reconstruct_target(db_name, target))
        
        # Wait for all reconstructions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                self.logger.warning(f"Content reconstruction failed: {result}")
                continue
            
            if isinstance(result, ReconstructedContent):
                reconstructed_content[result.content_id] = result
        
        return reconstructed_content
    
    def _determine_execution_order(
        self, 
        reconstruction_plan: Dict[str, List[ReconstructionTarget]], 
        strategy: ReconstructionStrategy
    ) -> List[str]:
        """Determines optimal execution order for database queries"""
        
        # Priority order based on strategy
        if strategy == ReconstructionStrategy.FULL_RECONSTRUCTION:
            # Comprehensive order: critical content first
            return ['postgresql', 'couchdb', 'chromadb', 'neo4j', 'sqlite']
        elif strategy == ReconstructionStrategy.PRIORITY_CONTENT_FIRST:
            # Priority content first
            return ['postgresql', 'sqlite', 'couchdb', 'chromadb', 'neo4j']
        elif strategy == ReconstructionStrategy.METADATA_LIGHTWEIGHT:
            # Lightweight: focus on metadata and basic content
            return ['sqlite', 'postgresql', 'chromadb']
        else:
            # Default order
            return list(reconstruction_plan.keys())
    
    async def _reconstruct_content_from_database(
        self,
        db_name: str,
        target: ReconstructionTarget,
        reconstruction_id: str
    ) -> Optional[ReconstructedContent]:
        """Reconstructs content from specific database"""
        
        try:
            # Check cache first
            cache_key = f"{db_name}_{target.document_id}_{target.content_types[0] if target.content_types else 'unknown'}"
            
            if cache_key in self.content_cache:
                cached_content = self.content_cache[cache_key]
                # Check if cache is still valid
                cache_age = time.time() - datetime.fromisoformat(cached_content.reconstruction_timestamp).timestamp()
                if cache_age < self.cache_ttl_seconds:
                    self.reconstruction_stats['cache_hits'] += 1
                    self.logger.debug(f"Cache hit for {cache_key}")
                    return cached_content
                else:
                    # Remove expired cache entry
                    del self.content_cache[cache_key]
            
            self.reconstruction_stats['cache_misses'] += 1
            
            # Simulate database content retrieval - in production this would use actual database APIs
            await asyncio.sleep(0.05)  # Simulate network/DB latency
            
            # Mock reconstructed content
            content = ReconstructedContent(
                content_id=f"{reconstruction_id}_{db_name}_{target.content_types[0] if target.content_types else 'content'}",
                content_type=target.content_types[0] if target.content_types else 'unknown',
                source_database=db_name,
                content_data={
                    'document_id': target.document_id,
                    'data_size': 'medium',
                    'content_preview': f"Content from {db_name} for {target.document_id}",
                    'metadata': target.reconstruction_metadata,
                    'quality_score': 0.85
                },
                metadata={
                    'retrieval_method': 'direct_query',
                    'source_reliability': 'high',
                    'content_version': '1.0'
                },
                reconstruction_timestamp=datetime.now().isoformat(),
                confidence_score=0.9,
                integrity_verified=False
            )
            
            # Cache the content
            self.content_cache[cache_key] = content
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to reconstruct content from {db_name}: {e}")
            return None
    
    async def _validate_content_integrity(self, reconstructed_content: Dict[str, ReconstructedContent]):
        """Validates integrity of reconstructed content"""
        
        for content_id, content in reconstructed_content.items():
            try:
                # Simulate integrity validation
                await asyncio.sleep(0.01)  # Simulate validation processing
                
                # Mock integrity checks
                has_required_fields = all(
                    field in content.content_data 
                    for field in ['document_id', 'content_preview']
                )
                
                confidence_acceptable = content.confidence_score >= 0.7
                
                content.integrity_verified = has_required_fields and confidence_acceptable
                
                if not content.integrity_verified:
                    self.logger.warning(f"Content integrity validation failed for {content_id}")
                
            except Exception as e:
                self.logger.error(f"Integrity validation error for {content_id}: {e}")
                content.integrity_verified = False
    
    def _calculate_completeness_metrics(
        self,
        reconstruction_plan: Dict[str, List[ReconstructionTarget]],
        reconstructed_content: Dict[str, ReconstructedContent]
    ) -> Dict[str, Any]:
        """Calculates completeness and quality metrics"""
        
        # Count total expected content items
        total_expected = sum(len(targets) for targets in reconstruction_plan.values())
        total_reconstructed = len(reconstructed_content)
        
        # Calculate completeness ratio
        completeness_ratio = total_reconstructed / total_expected if total_expected > 0 else 0.0
        
        # Find missing content
        expected_items = set()
        for targets in reconstruction_plan.values():
            for target in targets:
                for content_type in target.content_types:
                    expected_items.add(f"{target.document_id}_{content_type}")
        
        reconstructed_items = set(content.content_type for content in reconstructed_content.values())
        missing_content = list(expected_items - reconstructed_items)
        
        # Calculate average integrity score
        integrity_scores = [
            content.confidence_score for content in reconstructed_content.values()
            if content.integrity_verified
        ]
        integrity_score = sum(integrity_scores) / len(integrity_scores) if integrity_scores else 0.0
        
        return {
            'completeness_ratio': completeness_ratio,
            'missing_content': missing_content,
            'integrity_score': integrity_score,
            'total_expected': total_expected,
            'total_reconstructed': total_reconstructed
        }
    
    async def reconstruct_multiple_documents(
        self,
        document_ids: List[str],
        reconstruction_strategy: Optional[ReconstructionStrategy] = None
    ) -> List[DocumentReconstructionResult]:
        """Reconstructs multiple documents concurrently"""
        
        self.logger.info(f"Starting batch reconstruction for {len(document_ids)} documents")
        
        # Process in batches to avoid overwhelming the system
        batch_size = self.max_concurrent_reconstructions
        results = []
        
        for i in range(0, len(document_ids), batch_size):
            batch = document_ids[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [
                self.reconstruct_document(doc_id, reconstruction_strategy)
                for doc_id in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle any exceptions in batch results
            for j, batch_result in enumerate(batch_results):
                if isinstance(batch_result, Exception):
                    # Create error result for failed reconstruction
                    error_result = DocumentReconstructionResult(
                        document_id=batch[j],
                        reconstruction_id=str(uuid.uuid4()),
                        success=False,
                        errors=[f"Batch reconstruction failed: {str(batch_result)}"]
                    )
                    results.append(error_result)
                else:
                    results.append(batch_result)
        
        successful = sum(1 for result in results if result.success)
        
        self.logger.info(
            f"Batch reconstruction completed: {successful}/{len(results)} successful"
        )
        
        return results
    
    def get_reconstruction_stats(self) -> Dict[str, Any]:
        """Returns comprehensive reconstruction statistics"""
        
        return {
            **self.reconstruction_stats,
            'cache_entries': len(self.content_cache),
            'cache_hit_ratio': (
                self.reconstruction_stats['cache_hits'] / 
                (self.reconstruction_stats['cache_hits'] + self.reconstruction_stats['cache_misses'])
                if (self.reconstruction_stats['cache_hits'] + self.reconstruction_stats['cache_misses']) > 0
                else 0.0
            ),
            'success_rate': (
                self.reconstruction_stats['successful_reconstructions'] / 
                self.reconstruction_stats['total_reconstructions']
                if self.reconstruction_stats['total_reconstructions'] > 0
                else 0.0
            )
        }
    
    def clear_content_cache(self):
        """Clears the content reconstruction cache"""
        
        self.content_cache.clear()
        self.logger.info("Content reconstruction cache cleared")


# Factory functions for easy integration

async def create_document_reconstructor(
    adaptive_strategy: AdaptiveMultiDBStrategy,
    distributor: Optional[UDS3MultiDBDistributor] = None,
    config: Dict = None
) -> DocumentReconstructor:
    """
    Factory function for DocumentReconstructor
    """
    
    reconstructor = DocumentReconstructor(
        adaptive_strategy=adaptive_strategy,
        distributor=distributor,
        config=config
    )
    
    logging.info("DocumentReconstructor created and ready for document reconstruction")
    
    return reconstructor


def create_reconstruction_target_from_distribution_result(distribution_result) -> ReconstructionTarget:
    """
    Creates ReconstructionTarget from UDS3 distribution result
    
    This function integrates with the existing distribution system by converting
    distribution results to reconstruction targets.
    """
    
    # This is a placeholder - would need actual distribution result structure
    return ReconstructionTarget(
        document_id=getattr(distribution_result, 'document_id', 'unknown'),
        processor_results=getattr(distribution_result, 'distributed_to', {}).keys(),
        database_sources=getattr(distribution_result, 'distributed_to', {}),
        content_types=['reconstructed_content'],
        priority=ContentPriority.MEDIUM,
        reconstruction_metadata={
            'source': 'distribution_result',
            'strategy': getattr(distribution_result, 'strategy_used', 'unknown')
        }
    )


if __name__ == "__main__":
    # Example usage and testing
    async def test_document_reconstructor():
        """Test function for development"""
        
        logging.basicConfig(level=logging.INFO)
        
        # Mock adaptive strategy
        class MockAdaptiveStrategy:
            current_strategy = StrategyType.FULL_POLYGLOT
            db_availability = type('', (), {
                'postgresql': True,
                'couchdb': True,
                'chromadb': True,
                'neo4j': True,
                'sqlite': True
            })()
        
        mock_strategy = MockAdaptiveStrategy()
        
        # Create reconstructor
        reconstructor = await create_document_reconstructor(mock_strategy)
        
        # Test document reconstruction
        test_document_id = "test_doc_12345"
        result = await reconstructor.reconstruct_document(test_document_id)
        
        print(f"Reconstruction Result:")
        print(f"  Success: {result.success}")
        print(f"  Content Items: {len(result.reconstructed_content)}")
        print(f"  Completeness: {result.content_completeness:.2%}")
        print(f"  Time: {result.reconstruction_time_ms:.1f}ms")
        
        # Test batch reconstruction
        batch_results = await reconstructor.reconstruct_multiple_documents([
            "batch_doc_1", "batch_doc_2", "batch_doc_3"
        ])
        
        print(f"\nBatch Reconstruction:")
        print(f"  Total Documents: {len(batch_results)}")
        print(f"  Successful: {sum(1 for r in batch_results if r.success)}")
        
        # Display statistics
        stats = reconstructor.get_reconstruction_stats()
        print(f"\nReconstruction Statistics:")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
    
    # Run test
    asyncio.run(test_document_reconstructor())