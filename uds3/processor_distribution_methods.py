#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Processor-Specific Distribution Methods

Implementiert spezifische Distribution Strategies für verschiedene UDS3 Processor Types.
Optimiert Content-Type spezifische Routing und Database Storage Strategies basierend
auf den Charakteristika der verschiedenen Processor Results.

Features:
- ImageProcessor: Optimierte Binary Data + Embedding Distribution
- GeospatialProcessor: Koordinaten-basierte Spatial Database Integration
- AudioVideoProcessor: Media Metadata + Transcription Distribution
- OfficeIngestionHandler: Document Structure + Relationship Extraction
- EMLProcessor: Email Thread + Attachment Distribution
- PDFProcessor: Page-basierte Content + Annotation Distribution
- TextProcessor: Natural Language + Semantic Embedding Distribution
- Performance-optimierte Storage Strategies pro Processor Type

Autor: Covina Development Team
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
import base64
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod

# Import base components
try:
    from .uds3_multi_db_distributor import (
        UDS3MultiDBDistributor, ProcessorResult, ProcessorType, 
        DistributionTarget, DistributionPriority, DistributionResult
    )
    from .adaptive_multi_db_strategy import AdaptiveMultiDBStrategy
    from .pipeline_integration import UDS3PipelineDistributionManager
    UDS3_COMPONENTS_AVAILABLE = True
except ImportError:
    logging.warning("UDS3 distribution components not available")
    UDS3_COMPONENTS_AVAILABLE = False

# Standard imports for processing
import hashlib
import mimetypes


@dataclass
class ProcessorDistributionConfig:
    """Configuration for processor-specific distribution strategies"""
    processor_type: ProcessorType
    priority_overrides: Dict[str, DistributionPriority] = field(default_factory=dict)
    storage_optimizations: Dict[str, Any] = field(default_factory=dict)
    fallback_strategies: List[str] = field(default_factory=list)
    content_filters: List[str] = field(default_factory=list)
    performance_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentExtractionResult:
    """Result of content extraction for specific processor types"""
    primary_content: Dict[str, Any]
    metadata_content: Dict[str, Any] = field(default_factory=dict)
    binary_content: Dict[str, bytes] = field(default_factory=dict)
    relationship_content: List[Dict] = field(default_factory=list)
    embedding_content: Dict[str, List[float]] = field(default_factory=dict)
    geospatial_content: Dict[str, Any] = field(default_factory=dict)


class ProcessorDistributionStrategy(ABC):
    """
    Abstract base class for processor-specific distribution strategies
    """
    
    def __init__(
        self, 
        distributor: UDS3MultiDBDistributor,
        config: ProcessorDistributionConfig
    ):
        self.distributor = distributor
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Processor-specific performance metrics
        self.performance_metrics = {
            'total_processed': 0,
            'successful_distributions': 0,
            'content_extractions': 0,
            'optimization_hits': 0,
            'fallback_used': 0,
            'avg_processing_time_ms': 0.0
        }
    
    @abstractmethod
    def extract_content(self, processor_result: ProcessorResult) -> ContentExtractionResult:
        """
        Extracts and categorizes content from processor result
        
        Args:
            processor_result: Original processor result
            
        Returns:
            Structured content extraction result
        """
        pass
    
    @abstractmethod
    def optimize_distribution_targets(
        self, 
        content: ContentExtractionResult,
        available_databases: Dict[str, bool]
    ) -> Dict[str, List[DistributionTarget]]:
        """
        Optimizes distribution targets based on content characteristics
        
        Args:
            content: Extracted content
            available_databases: Available database systems
            
        Returns:
            Optimized distribution plan
        """
        pass
    
    async def distribute_processor_result(
        self, 
        processor_result: ProcessorResult
    ) -> DistributionResult:
        """
        Main distribution method with processor-specific optimizations
        """
        
        start_time = time.time()
        
        try:
            self.performance_metrics['total_processed'] += 1
            
            # Step 1: Extract content with processor-specific logic
            content = self.extract_content(processor_result)
            self.performance_metrics['content_extractions'] += 1
            
            # Step 2: Get available databases
            available_dbs = await self._get_available_databases()
            
            # Step 3: Optimize distribution targets
            optimized_targets = self.optimize_distribution_targets(content, available_dbs)
            
            # Step 4: Apply processor-specific modifications
            modified_result = self._apply_processor_modifications(processor_result, content)
            
            # Step 5: Execute base distribution (bypass processor-specific to avoid recursion)
            distribution_result = await self.distributor._distribute_to_base_strategy(modified_result, optimized_targets)
            
            # Step 6: Post-process and update metrics
            await self._post_process_distribution(distribution_result, content)
            
            if distribution_result.success:
                self.performance_metrics['successful_distributions'] += 1
            
            if distribution_result.fallback_applied:
                self.performance_metrics['fallback_used'] += 1
            
            # Update average processing time
            processing_time = (time.time() - start_time) * 1000
            self._update_average_processing_time(processing_time)
            
            return distribution_result
            
        except Exception as e:
            self.logger.error(f"Processor-specific distribution failed: {e}")
            
            processing_time = (time.time() - start_time) * 1000
            
            return DistributionResult(
                document_id=processor_result.document_id,
                processor_name=processor_result.processor_name,
                success=False,
                distributed_to={},
                execution_time_ms=processing_time,
                errors=[f"Processor distribution strategy failed: {str(e)}"],
                strategy_used=f"{self.config.processor_type.value}_specific"
            )
    
    async def _get_available_databases(self) -> Dict[str, bool]:
        """Gets available databases from distributor's adaptive strategy"""
        
        if hasattr(self.distributor, 'adaptive_strategy') and self.distributor.adaptive_strategy:
            strategy = self.distributor.adaptive_strategy
            if hasattr(strategy, 'db_availability'):
                return {
                    'postgresql': strategy.db_availability.postgresql,
                    'couchdb': strategy.db_availability.couchdb,
                    'chromadb': strategy.db_availability.chromadb,
                    'neo4j': strategy.db_availability.neo4j,
                    'sqlite': strategy.db_availability.sqlite
                }
        
        # Fallback
        return {'postgresql': True, 'couchdb': True, 'chromadb': True, 'neo4j': True, 'sqlite': True}
    
    def _apply_processor_modifications(
        self, 
        processor_result: ProcessorResult, 
        content: ContentExtractionResult
    ) -> ProcessorResult:
        """Applies processor-specific modifications to result data"""
        
        # Create modified copy
        modified_data = dict(processor_result.result_data)
        
        # Add extracted content
        modified_data.update({
            'extracted_primary_content': content.primary_content,
            'extracted_metadata': content.metadata_content,
            'extracted_relationships': content.relationship_content,
            'processor_optimization_applied': True,
            'optimization_timestamp': datetime.now().isoformat()
        })
        
        # Add binary content references (not the data itself)
        if content.binary_content:
            modified_data['binary_content_refs'] = {
                key: {
                    'size_bytes': len(data),
                    'hash': hashlib.sha256(data).hexdigest()[:16],
                    'type': 'binary_reference'
                }
                for key, data in content.binary_content.items()
            }
        
        # Add embeddings metadata
        if content.embedding_content:
            modified_data['embedding_metadata'] = {
                key: {
                    'dimension': len(vector),
                    'type': 'embedding_vector',
                    'norm': sum(x*x for x in vector) ** 0.5
                }
                for key, vector in content.embedding_content.items()
            }
        
        # Create modified processor result
        return ProcessorResult(
            processor_name=processor_result.processor_name,
            processor_type=processor_result.processor_type,
            document_id=processor_result.document_id,
            result_data=modified_data,
            confidence_score=processor_result.confidence_score,
            execution_time_ms=processor_result.execution_time_ms,
            metadata=processor_result.metadata,
            error_info=processor_result.error_info
        )
    
    async def _post_process_distribution(
        self, 
        distribution_result: DistributionResult,
        content: ContentExtractionResult
    ):
        """Post-processes distribution result with processor-specific logic"""
        
        # Log processor-specific metrics
        self.logger.debug(
            f"Processor distribution completed: "
            f"Primary content: {len(content.primary_content)} items, "
            f"Binary content: {len(content.binary_content)} items, "
            f"Relationships: {len(content.relationship_content)} items"
        )
        
        # Processor-specific cleanup or follow-up actions can be implemented here
    
    def _update_average_processing_time(self, new_time_ms: float):
        """Updates running average of processing time"""
        
        current_avg = self.performance_metrics['avg_processing_time_ms']
        total_processed = self.performance_metrics['total_processed']
        
        if total_processed <= 1:
            self.performance_metrics['avg_processing_time_ms'] = new_time_ms
        else:
            # Running average calculation
            self.performance_metrics['avg_processing_time_ms'] = (
                (current_avg * (total_processed - 1) + new_time_ms) / total_processed
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Returns current performance metrics for this processor strategy"""
        
        total = self.performance_metrics['total_processed']
        
        return {
            **self.performance_metrics,
            'success_rate': (
                self.performance_metrics['successful_distributions'] / total 
                if total > 0 else 0.0
            ),
            'fallback_rate': (
                self.performance_metrics['fallback_used'] / total 
                if total > 0 else 0.0
            ),
            'processor_type': self.config.processor_type.value
        }


class ImageProcessorDistributionStrategy(ProcessorDistributionStrategy):
    """
    Distribution strategy optimized for Image Processing results
    
    Specializes in:
    - Binary image data distribution
    - Visual embedding optimization
    - Thumbnail generation and storage
    - EXIF metadata extraction
    - Image relationship detection
    """
    
    def extract_content(self, processor_result: ProcessorResult) -> ContentExtractionResult:
        """Extracts image-specific content from processor result"""
        
        result_data = processor_result.result_data
        
        # Extract primary image content
        primary_content = {
            'image_dimensions': result_data.get('dimensions', {}),
            'color_profile': result_data.get('color_profile', ''),
            'image_format': result_data.get('format', ''),
            'compression_info': result_data.get('compression', {}),
            'quality_score': result_data.get('quality_score', 0.0)
        }
        
        # Extract metadata content
        metadata_content = {
            'exif_data': result_data.get('exif_data', {}),
            'camera_info': result_data.get('camera_info', {}),
            'location_data': result_data.get('location_data', {}),
            'capture_timestamp': result_data.get('capture_timestamp', ''),
            'processing_metadata': {
                'extraction_method': 'ImageProcessorStrategy',
                'processed_at': datetime.now().isoformat()
            }
        }
        
        # Extract binary content
        binary_content = {}
        if 'image_data' in result_data:
            binary_content['original_image'] = result_data['image_data']
        if 'thumbnail_data' in result_data:
            binary_content['thumbnail'] = result_data['thumbnail_data']
        if 'preview_data' in result_data:
            binary_content['preview'] = result_data['preview_data']
        
        # Extract embedding content
        embedding_content = {}
        if 'visual_embedding' in result_data:
            embedding_content['visual_features'] = result_data['visual_embedding']
        if 'color_histogram' in result_data:
            embedding_content['color_features'] = result_data['color_histogram']
        
        # Extract relationship content
        relationship_content = []
        if 'similar_images' in result_data:
            for similar_image in result_data['similar_images']:
                relationship_content.append({
                    'relationship_type': 'visual_similarity',
                    'target_document': similar_image.get('document_id', ''),
                    'confidence': similar_image.get('similarity_score', 0.0),
                    'relationship_metadata': {
                        'similarity_method': 'visual_embedding',
                        'features_compared': similar_image.get('features', [])
                    }
                })
        
        return ContentExtractionResult(
            primary_content=primary_content,
            metadata_content=metadata_content,
            binary_content=binary_content,
            relationship_content=relationship_content,
            embedding_content=embedding_content
        )
    
    def optimize_distribution_targets(
        self, 
        content: ContentExtractionResult,
        available_databases: Dict[str, bool]
    ) -> Dict[str, List[DistributionTarget]]:
        """Optimizes distribution for image content"""
        
        targets = {}
        
        # Binary content -> CouchDB for large image data
        if content.binary_content and available_databases.get('couchdb', False):
            targets['image_binary_data'] = [
                DistributionTarget(
                    database_type='couchdb',
                    storage_location='image_binaries',
                    priority=DistributionPriority.HIGH,
                    content_type='binary',
                    processor_affinity=1.0,
                    fallback_targets=['postgresql']
                )
            ]
        
        # Visual embeddings -> ChromaDB for similarity search
        if content.embedding_content and available_databases.get('chromadb', False):
            targets['visual_embeddings'] = [
                DistributionTarget(
                    database_type='chromadb',
                    storage_location='visual_embeddings',
                    priority=DistributionPriority.HIGH,
                    content_type='embedding',
                    processor_affinity=1.0,
                    fallback_targets=['postgresql']
                )
            ]
        
        # Image metadata -> PostgreSQL for structured queries
        if content.metadata_content and available_databases.get('postgresql', False):
            targets['image_metadata'] = [
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='image_metadata',
                    priority=DistributionPriority.HIGH,
                    content_type='metadata',
                    processor_affinity=0.9,
                    fallback_targets=['sqlite']
                )
            ]
        
        # Visual relationships -> Neo4j for graph queries
        if content.relationship_content and available_databases.get('neo4j', False):
            targets['visual_relationships'] = [
                DistributionTarget(
                    database_type='neo4j',
                    storage_location='VisualDocument',
                    priority=DistributionPriority.MEDIUM,
                    content_type='relationship',
                    processor_affinity=0.9,
                    fallback_targets=['postgresql']
                )
            ]
        
        return targets


class GeospatialProcessorDistributionStrategy(ProcessorDistributionStrategy):
    """
    Distribution strategy optimized for Geospatial Processing results
    
    Specializes in:
    - Coordinate data validation and storage
    - Spatial relationship detection
    - Geographic metadata extraction
    - Spatial indexing optimization
    - Multi-coordinate system support
    """
    
    def extract_content(self, processor_result: ProcessorResult) -> ContentExtractionResult:
        """Extracts geospatial-specific content from processor result"""
        
        result_data = processor_result.result_data
        
        # Extract primary geospatial content
        primary_content = {
            'coordinates': result_data.get('coordinates', {}),
            'coordinate_system': result_data.get('coordinate_system', 'WGS84'),
            'accuracy_meters': result_data.get('accuracy_meters', 0.0),
            'elevation_meters': result_data.get('elevation_meters'),
            'geometric_type': result_data.get('geometric_type', 'POINT')
        }
        
        # Extract metadata content
        metadata_content = {
            'location_name': result_data.get('location_name', ''),
            'administrative_areas': result_data.get('administrative_areas', []),
            'geographic_context': result_data.get('geographic_context', {}),
            'data_source': result_data.get('data_source', ''),
            'extraction_method': 'GeospatialProcessorStrategy',
            'processed_at': datetime.now().isoformat()
        }
        
        # Extract geospatial-specific content
        geospatial_content = {
            'latitude': result_data.get('coordinates', {}).get('latitude'),
            'longitude': result_data.get('coordinates', {}).get('longitude'),
            'bounding_box': result_data.get('bounding_box', {}),
            'spatial_precision': result_data.get('spatial_precision', 'unknown'),
            'spatial_metadata': result_data.get('spatial_metadata', {})
        }
        
        # Extract spatial relationships
        relationship_content = []
        if 'nearby_locations' in result_data:
            for location in result_data['nearby_locations']:
                relationship_content.append({
                    'relationship_type': 'spatial_proximity',
                    'target_document': location.get('document_id', ''),
                    'confidence': 1.0,
                    'relationship_metadata': {
                        'distance_meters': location.get('distance_meters', 0),
                        'direction': location.get('direction', ''),
                        'spatial_relationship': location.get('relationship_type', 'nearby')
                    }
                })
        
        # Extract spatial embeddings if available
        embedding_content = {}
        if 'spatial_embedding' in result_data:
            embedding_content['spatial_features'] = result_data['spatial_embedding']
        
        return ContentExtractionResult(
            primary_content=primary_content,
            metadata_content=metadata_content,
            geospatial_content=geospatial_content,
            relationship_content=relationship_content,
            embedding_content=embedding_content
        )
    
    def optimize_distribution_targets(
        self, 
        content: ContentExtractionResult,
        available_databases: Dict[str, bool]
    ) -> Dict[str, List[DistributionTarget]]:
        """Optimizes distribution for geospatial content"""
        
        targets = {}
        
        # Spatial data -> Neo4j for spatial queries and relationships
        if content.geospatial_content and available_databases.get('neo4j', False):
            targets['spatial_data'] = [
                DistributionTarget(
                    database_type='neo4j',
                    storage_location='SpatialDocument',
                    priority=DistributionPriority.HIGH,
                    content_type='spatial',
                    processor_affinity=1.0,
                    fallback_targets=['postgresql']
                )
            ]
        
        # Coordinate data -> PostgreSQL with PostGIS for spatial indexing
        if content.geospatial_content and available_databases.get('postgresql', False):
            targets['coordinate_data'] = [
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='spatial_coordinates',
                    priority=DistributionPriority.HIGH,
                    content_type='spatial',
                    processor_affinity=0.9,
                    fallback_targets=['sqlite']
                )
            ]
        
        # Geographic metadata -> CouchDB for flexible geographic data
        if content.metadata_content and available_databases.get('couchdb', False):
            targets['geographic_metadata'] = [
                DistributionTarget(
                    database_type='couchdb',
                    storage_location='geographic_metadata',
                    priority=DistributionPriority.MEDIUM,
                    content_type='metadata',
                    processor_affinity=0.8,
                    fallback_targets=['postgresql']
                )
            ]
        
        return targets


class TextProcessorDistributionStrategy(ProcessorDistributionStrategy):
    """
    Distribution strategy optimized for Text Processing results
    
    Specializes in:
    - Text content normalization
    - Semantic embedding optimization
    - Language detection and metadata
    - Text relationship extraction
    - Natural language processing results
    """
    
    def extract_content(self, processor_result: ProcessorResult) -> ContentExtractionResult:
        """Extracts text-specific content from processor result"""
        
        result_data = processor_result.result_data
        
        # Extract primary text content
        primary_content = {
            'extracted_text': result_data.get('text_content', ''),
            'text_length': len(result_data.get('text_content', '')),
            'language': result_data.get('language', 'unknown'),
            'encoding': result_data.get('encoding', 'utf-8'),
            'text_quality_score': result_data.get('text_quality_score', 0.0)
        }
        
        # Extract metadata content
        metadata_content = {
            'language_detection': result_data.get('language_detection', {}),
            'text_statistics': result_data.get('text_statistics', {}),
            'nlp_metadata': result_data.get('nlp_metadata', {}),
            'extraction_confidence': result_data.get('extraction_confidence', 0.0),
            'processing_metadata': {
                'extraction_method': 'TextProcessorStrategy',
                'processed_at': datetime.now().isoformat(),
                'text_processing_version': '1.0.0'
            }
        }
        
        # Extract text embeddings
        embedding_content = {}
        if 'text_embedding' in result_data:
            embedding_content['semantic_embedding'] = result_data['text_embedding']
        if 'sentence_embeddings' in result_data:
            embedding_content['sentence_vectors'] = result_data['sentence_embeddings']
        
        # Extract text relationships
        relationship_content = []
        if 'text_similarities' in result_data:
            for similarity in result_data['text_similarities']:
                relationship_content.append({
                    'relationship_type': 'semantic_similarity',
                    'target_document': similarity.get('document_id', ''),
                    'confidence': similarity.get('similarity_score', 0.0),
                    'relationship_metadata': {
                        'similarity_method': 'semantic_embedding',
                        'text_overlap': similarity.get('text_overlap', 0.0),
                        'semantic_distance': similarity.get('semantic_distance', 1.0)
                    }
                })
        
        return ContentExtractionResult(
            primary_content=primary_content,
            metadata_content=metadata_content,
            relationship_content=relationship_content,
            embedding_content=embedding_content
        )
    
    def optimize_distribution_targets(
        self, 
        content: ContentExtractionResult,
        available_databases: Dict[str, bool]
    ) -> Dict[str, List[DistributionTarget]]:
        """Optimizes distribution for text content"""
        
        targets = {}
        
        # Text content -> CouchDB for full-text search
        if content.primary_content and available_databases.get('couchdb', False):
            targets['text_content'] = [
                DistributionTarget(
                    database_type='couchdb',
                    storage_location='text_documents',
                    priority=DistributionPriority.HIGH,
                    content_type='content',
                    processor_affinity=0.9,
                    fallback_targets=['postgresql']
                )
            ]
        
        # Semantic embeddings -> ChromaDB for similarity search
        if content.embedding_content and available_databases.get('chromadb', False):
            targets['semantic_embeddings'] = [
                DistributionTarget(
                    database_type='chromadb',
                    storage_location='text_embeddings',
                    priority=DistributionPriority.HIGH,
                    content_type='embedding',
                    processor_affinity=1.0,
                    fallback_targets=['postgresql']
                )
            ]
        
        # Text metadata -> PostgreSQL for structured queries
        if content.metadata_content and available_databases.get('postgresql', False):
            targets['text_metadata'] = [
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='text_metadata',
                    priority=DistributionPriority.MEDIUM,
                    content_type='metadata',
                    processor_affinity=0.8,
                    fallback_targets=['sqlite']
                )
            ]
        
        return targets


class ProcessorDistributionFactory:
    """
    Factory for creating processor-specific distribution strategies
    """
    
    def __init__(self, distributor: UDS3MultiDBDistributor):
        self.distributor = distributor
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Registry of available strategies
        self.strategy_registry = {
            ProcessorType.IMAGE_PROCESSOR: ImageProcessorDistributionStrategy,
            ProcessorType.GEOSPATIAL_PROCESSOR: GeospatialProcessorDistributionStrategy,
            ProcessorType.TEXT_PROCESSOR: TextProcessorDistributionStrategy,
            # Add more strategies as needed
        }
        
        # Cache of instantiated strategies
        self.strategy_cache: Dict[ProcessorType, ProcessorDistributionStrategy] = {}
    
    def get_distribution_strategy(
        self, 
        processor_type: ProcessorType,
        config: Optional[ProcessorDistributionConfig] = None
    ) -> ProcessorDistributionStrategy:
        """
        Gets or creates a distribution strategy for the specified processor type
        
        Args:
            processor_type: Type of processor
            config: Optional configuration for the strategy
            
        Returns:
            Appropriate distribution strategy instance
        """
        
        # Check cache first
        if processor_type in self.strategy_cache:
            return self.strategy_cache[processor_type]
        
        # Create default config if not provided
        if config is None:
            config = ProcessorDistributionConfig(processor_type=processor_type)
        
        # Get strategy class
        strategy_class = self.strategy_registry.get(processor_type)
        
        if strategy_class is None:
            # Fallback to base strategy for unknown processor types
            self.logger.warning(f"No specific strategy for {processor_type.value}, using base strategy")
            strategy = ProcessorDistributionStrategy(self.distributor, config)
        else:
            # Create specific strategy
            strategy = strategy_class(self.distributor, config)
        
        # Cache the strategy
        self.strategy_cache[processor_type] = strategy
        
        self.logger.debug(f"Created distribution strategy for {processor_type.value}")
        
        return strategy
    
    def get_all_performance_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Gets performance metrics for all cached strategies"""
        
        return {
            processor_type.value: strategy.get_performance_metrics()
            for processor_type, strategy in self.strategy_cache.items()
        }
    
    def clear_strategy_cache(self):
        """Clears the strategy cache"""
        self.strategy_cache.clear()
        self.logger.info("Strategy cache cleared")


class UDS3EnhancedMultiDBDistributor(UDS3MultiDBDistributor):
    """
    Enhanced Multi-DB Distributor with processor-specific strategies
    
    Extends the base UDS3MultiDBDistributor with processor-specific
    optimization strategies for improved performance and storage efficiency.
    """
    
    def __init__(
        self, 
        adaptive_strategy: AdaptiveMultiDBStrategy,
        database_manager = None,
        config: Dict = None
    ):
        super().__init__(adaptive_strategy, database_manager, config)
        
        # Initialize processor-specific distribution
        self.distribution_factory = ProcessorDistributionFactory(self)
        self.enable_processor_optimization = config.get('enable_processor_optimization', True) if config else True
        
        self.logger.info("🔧 Enhanced Multi-DB Distributor with processor-specific strategies initialized")
    
    async def distribute_processor_result(
        self, 
        processor_result: ProcessorResult
    ) -> DistributionResult:
        """
        Enhanced distribution with processor-specific optimizations
        """
        
        if not self.enable_processor_optimization:
            # Fall back to base implementation
            return await super().distribute_processor_result(processor_result)
        
        try:
            # Get processor-specific strategy
            strategy = self.distribution_factory.get_distribution_strategy(
                processor_result.processor_type
            )
            
            # Use processor-specific distribution
            return await strategy.distribute_processor_result(processor_result)
            
        except Exception as e:
            self.logger.warning(f"Processor-specific distribution failed, falling back to base: {e}")
            
            # Fallback to base implementation
            return await super().distribute_processor_result(processor_result)
    
    def get_enhanced_distribution_stats(self) -> Dict[str, Any]:
        """Gets enhanced distribution statistics including processor-specific metrics"""
        
        base_stats = self.get_distribution_stats()
        processor_metrics = self.distribution_factory.get_all_performance_metrics()
        
        return {
            'base_distribution': base_stats,
            'processor_specific': processor_metrics,
            'optimization_enabled': self.enable_processor_optimization,
            'cached_strategies': len(self.distribution_factory.strategy_cache)
        }


# Convenience function for creating enhanced distributor
async def create_enhanced_uds3_distributor(
    adaptive_strategy: AdaptiveMultiDBStrategy,
    database_manager = None,
    config: Dict = None
) -> UDS3EnhancedMultiDBDistributor:
    """
    Creates an enhanced UDS3 Multi-DB Distributor with processor-specific strategies
    """
    
    enhanced_config = config or {}
    enhanced_config.setdefault('enable_processor_optimization', True)
    
    distributor = UDS3EnhancedMultiDBDistributor(
        adaptive_strategy=adaptive_strategy,
        database_manager=database_manager,
        config=enhanced_config
    )
    
    logging.info("🚀 Enhanced UDS3 Multi-DB Distributor with processor strategies created")
    
    return distributor


if __name__ == "__main__":
    # Example usage and testing
    async def test_processor_strategies():
        """Test processor-specific distribution strategies"""
        
        logging.basicConfig(level=logging.INFO)
        
        # Mock adaptive strategy
        class MockAdaptiveStrategy:
            current_strategy = 'full_polyglot'
            db_availability = type('', (), {
                'postgresql': True,
                'couchdb': True,
                'chromadb': True,
                'neo4j': True,
                'sqlite': True
            })()
        
        mock_strategy = MockAdaptiveStrategy()
        
        # Create enhanced distributor
        distributor = await create_enhanced_uds3_distributor(mock_strategy)
        
        # Test image processor result
        image_result = ProcessorResult(
            processor_name="ImageProcessor",
            processor_type=ProcessorType.IMAGE_PROCESSOR,
            document_id="test_image_001",
            result_data={
                'dimensions': {'width': 1920, 'height': 1080},
                'format': 'JPEG',
                'exif_data': {'camera': 'Canon EOS R5'},
                'visual_embedding': [0.1, 0.2, 0.3, 0.4, 0.5],
                'similar_images': [
                    {'document_id': 'img_002', 'similarity_score': 0.85}
                ]
            },
            confidence_score=0.92,
            execution_time_ms=1500,
            metadata={'file_path': '/test/image.jpg'}
        )
        
        # Test distribution
        result = await distributor.distribute_processor_result(image_result)
        print(f"Image Distribution Result: {result.success}")
        
        # Test geospatial processor result
        geo_result = ProcessorResult(
            processor_name="GeospatialProcessor",
            processor_type=ProcessorType.GEOSPATIAL_PROCESSOR,
            document_id="test_geo_001",
            result_data={
                'coordinates': {'latitude': 52.5200, 'longitude': 13.4050},
                'coordinate_system': 'WGS84',
                'location_name': 'Berlin, Germany',
                'accuracy_meters': 5.0,
                'nearby_locations': [
                    {'document_id': 'geo_002', 'distance_meters': 150}
                ]
            },
            confidence_score=0.98,
            execution_time_ms=800,
            metadata={'file_path': '/test/document.pdf'}
        )
        
        # Test distribution
        geo_dist_result = await distributor.distribute_processor_result(geo_result)
        print(f"Geospatial Distribution Result: {geo_dist_result.success}")
        
        # Get enhanced statistics
        stats = distributor.get_enhanced_distribution_stats()
        print(f"Enhanced Distribution Stats: {json.dumps(stats, indent=2)}")
    
    # Run test
    asyncio.run(test_processor_strategies())