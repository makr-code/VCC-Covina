#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Multi-Database Distributor

Intelligente Verteilung von UDS3 Processor Results auf die verfügbaren Datenbanken
basierend auf der AdaptiveMultiDBStrategy. Koordiniert die Distribution von
Dokumenteninhalten, Metadaten, Embeddings und Beziehungen auf PostgreSQL,
CouchDB, ChromaDB und Neo4j.

Features:
- Adaptive Strategy-basierte Distribution
- Processor-spezifische Routing Logic
- Multi-DB Transaction Coordination
- Automatic Fallback bei DB-Ausfällen
- Performance-optimierte Batch Processing
- Comprehensive Error Handling und Recovery
- Integration mit UDS3 SAGA Pattern

Autor: Covina Development Team
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
import uuid
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Import UDS3 components
try:
    from .adaptive_multi_db_strategy import AdaptiveMultiDBStrategy, StrategyType, FlexibleMultiDBDistributor
    from .monolithic_fallback_strategies import SQLiteMonolithStrategy
    from .database.database_manager import DatabaseManager
    from .database.database_api_base import DatabaseBackend
    UDS3_AVAILABLE = True
except ImportError:
    logging.debug("UDS3 imports not fully available - running in standalone mode")
    UDS3_AVAILABLE = False

# Standard imports for fallback
import sqlite3
import psycopg2


class ProcessorType(Enum):
    """UDS3 Processor Types für spezifische Distribution Logic"""
    IMAGE_PROCESSOR = "ImageProcessor"
    GEOSPATIAL_PROCESSOR = "GeospatialProcessor"
    AUDIO_VIDEO_PROCESSOR = "AudioVideoProcessor"
    OFFICE_INGESTION_HANDLER = "OfficeIngestionHandler"
    EML_PROCESSOR = "EMLProcessor"
    TEXT_PROCESSOR = "TextProcessor"
    PDF_PROCESSOR = "PDFProcessor"
    ARCHIVE_PROCESSOR = "ArchiveProcessor"
    WEB_PROCESSOR = "WebProcessor"
    CORE_INGEST_HANDLER = "CoreIngestHandler"
    UNKNOWN = "Unknown"


class DistributionPriority(Enum):
    """Priority für Database Distribution"""
    CRITICAL = "critical"      # Must be stored (e.g., master registry)
    HIGH = "high"             # Should be stored (e.g., primary content)
    MEDIUM = "medium"         # Can be stored (e.g., enrichment data)
    LOW = "low"              # Optional storage (e.g., cache data)


@dataclass
class DistributionTarget:
    """Ziel-Database für spezifische Content-Types"""
    database_type: str        # 'postgresql', 'couchdb', 'chromadb', 'neo4j'
    storage_location: str     # table/collection/index name
    priority: DistributionPriority
    content_type: str         # 'metadata', 'content', 'embedding', 'relationship'
    processor_affinity: float = 1.0  # How well suited this processor type is
    fallback_targets: List[str] = field(default_factory=list)


@dataclass
class ProcessorResult:
    """Structured UDS3 Processor Result für Distribution"""
    processor_name: str
    processor_type: ProcessorType
    document_id: str
    result_data: Dict[str, Any]
    confidence_score: float
    execution_time_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_info: Optional[Dict] = None


@dataclass
class DistributionResult:
    """Ergebnis einer Multi-DB Distribution"""
    document_id: str
    processor_name: str
    success: bool
    distributed_to: Dict[str, List[str]]  # database -> list of stored items
    execution_time_ms: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fallback_applied: bool = False
    strategy_used: str = "adaptive"


class UDS3MultiDBDistributor:
    """
    Multi-Database Distributor für intelligente UDS3 Content Distribution
    
    Koordiniert die Verteilung von UDS3 Processor Results auf verfügbare
    Datenbanken basierend auf der AdaptiveMultiDBStrategy und Processor-
    spezifischen Content-Charakteristika.
    """
    
    def __init__(
        self, 
        adaptive_strategy: AdaptiveMultiDBStrategy,
        database_manager: Optional[DatabaseManager] = None,
        config: Dict = None
    ):
        self.adaptive_strategy = adaptive_strategy
        self.database_manager = database_manager
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Distribution Configuration
        self.distribution_targets = self._initialize_distribution_targets()
        self.processor_routing = self._initialize_processor_routing()
        
        # Performance Configuration
        self.batch_size = self.config.get('batch_size', 100)
        self.max_concurrent_distributions = self.config.get('max_concurrent', 5)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        
        # State Tracking
        self.active_distributions = {}
        self.distribution_stats = {
            'total_processed': 0,
            'successful_distributions': 0,
            'failed_distributions': 0,
            'fallback_used': 0
        }
        
        # Database Connections Cache
        self._db_connections = {}
        self._connection_health = {}
        
    def _initialize_distribution_targets(self) -> Dict[str, List[DistributionTarget]]:
        """
        Initialisiert Distribution Targets für verschiedene Content-Types
        
        Returns:
            Dict mapping content types to list of potential storage targets
        """
        
        targets = {
            # Master Registry - Always goes to PostgreSQL
            'master_registry': [
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='uds3_master_documents',
                    priority=DistributionPriority.CRITICAL,
                    content_type='metadata',
                    processor_affinity=1.0,
                    fallback_targets=['sqlite']
                )
            ],
            
            # Processor Results - PostgreSQL + distribution tracking
            'processor_results': [
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='uds3_processor_results',
                    priority=DistributionPriority.CRITICAL,
                    content_type='metadata',
                    processor_affinity=1.0,
                    fallback_targets=['sqlite']
                )
            ],
            
            # Document Content - CouchDB primary, PostgreSQL backup
            'document_content': [
                DistributionTarget(
                    database_type='couchdb',
                    storage_location='processed_documents',
                    priority=DistributionPriority.HIGH,
                    content_type='content',
                    processor_affinity=1.0,
                    fallback_targets=['postgresql']
                ),
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='uds3_document_content',
                    priority=DistributionPriority.MEDIUM,
                    content_type='content',
                    processor_affinity=0.7,
                    fallback_targets=['sqlite']
                )
            ],
            
            # Vector Embeddings - ChromaDB primary, PostgreSQL with pg_vector backup
            'vector_embeddings': [
                DistributionTarget(
                    database_type='chromadb',
                    storage_location='document_embeddings',
                    priority=DistributionPriority.HIGH,
                    content_type='embedding',
                    processor_affinity=1.0,
                    fallback_targets=['postgresql']
                ),
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='uds3_vector_embeddings',
                    priority=DistributionPriority.MEDIUM,
                    content_type='embedding',
                    processor_affinity=0.6,
                    fallback_targets=['sqlite']
                )
            ],
            
            # Relationships - Neo4j primary, PostgreSQL table backup
            'relationships': [
                DistributionTarget(
                    database_type='neo4j',
                    storage_location='Document',
                    priority=DistributionPriority.HIGH,
                    content_type='relationship',
                    processor_affinity=1.0,
                    fallback_targets=['postgresql']
                ),
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='uds3_cross_references',
                    priority=DistributionPriority.HIGH,
                    content_type='relationship',
                    processor_affinity=0.8,
                    fallback_targets=['sqlite']
                )
            ],
            
            # Geospatial Data - Neo4j with spatial, PostgreSQL with PostGIS
            'geospatial_data': [
                DistributionTarget(
                    database_type='neo4j',
                    storage_location='SpatialDocument',
                    priority=DistributionPriority.HIGH,
                    content_type='spatial',
                    processor_affinity=0.9,
                    fallback_targets=['postgresql']
                ),
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='uds3_spatial_data',
                    priority=DistributionPriority.HIGH,
                    content_type='spatial',
                    processor_affinity=0.9,
                    fallback_targets=['sqlite']
                )
            ],
            
            # Metadata Enrichment - CouchDB for flexible storage
            'metadata_enrichment': [
                DistributionTarget(
                    database_type='couchdb',
                    storage_location='metadata_enrichment',
                    priority=DistributionPriority.MEDIUM,
                    content_type='metadata',
                    processor_affinity=0.9,
                    fallback_targets=['postgresql']
                ),
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='uds3_enrichment_data',
                    priority=DistributionPriority.MEDIUM,
                    content_type='metadata',
                    processor_affinity=0.7,
                    fallback_targets=['sqlite']
                )
            ],
            
            # Event Sourcing - CouchDB for immutable events
            'event_store': [
                DistributionTarget(
                    database_type='couchdb',
                    storage_location='document_events',
                    priority=DistributionPriority.HIGH,
                    content_type='event',
                    processor_affinity=1.0,
                    fallback_targets=['postgresql']
                ),
                DistributionTarget(
                    database_type='postgresql',
                    storage_location='uds3_event_log',
                    priority=DistributionPriority.MEDIUM,
                    content_type='event',
                    processor_affinity=0.6,
                    fallback_targets=['sqlite']
                )
            ]
        }
        
        return targets
    
    def _initialize_processor_routing(self) -> Dict[ProcessorType, Dict[str, List[str]]]:
        """
        Initialisiert Processor-spezifische Routing Rules
        
        Returns:
            Dict mapping processor types to their preferred distribution targets
        """
        
        routing = {
            ProcessorType.IMAGE_PROCESSOR: {
                'primary_targets': ['master_registry', 'processor_results', 'document_content', 'vector_embeddings'],
                'secondary_targets': ['metadata_enrichment', 'event_store'],
                'content_types': ['image_metadata', 'thumbnails', 'visual_embeddings', 'exif_data']
            },
            
            ProcessorType.GEOSPATIAL_PROCESSOR: {
                'primary_targets': ['master_registry', 'processor_results', 'geospatial_data', 'relationships'],
                'secondary_targets': ['metadata_enrichment', 'event_store'],
                'content_types': ['coordinates', 'spatial_metadata', 'location_relationships', 'geo_embeddings']
            },
            
            ProcessorType.AUDIO_VIDEO_PROCESSOR: {
                'primary_targets': ['master_registry', 'processor_results', 'document_content', 'vector_embeddings'],
                'secondary_targets': ['metadata_enrichment', 'event_store'],
                'content_types': ['media_metadata', 'transcripts', 'audio_features', 'video_thumbnails']
            },
            
            ProcessorType.OFFICE_INGESTION_HANDLER: {
                'primary_targets': ['master_registry', 'processor_results', 'document_content', 'relationships'],
                'secondary_targets': ['vector_embeddings', 'metadata_enrichment', 'event_store'],
                'content_types': ['document_structure', 'text_content', 'document_relationships', 'office_metadata']
            },
            
            ProcessorType.EML_PROCESSOR: {
                'primary_targets': ['master_registry', 'processor_results', 'document_content', 'relationships'],
                'secondary_targets': ['vector_embeddings', 'metadata_enrichment', 'event_store'],
                'content_types': ['email_headers', 'email_content', 'attachments', 'email_thread_relationships']
            },
            
            ProcessorType.TEXT_PROCESSOR: {
                'primary_targets': ['master_registry', 'processor_results', 'document_content', 'vector_embeddings'],
                'secondary_targets': ['relationships', 'metadata_enrichment', 'event_store'],
                'content_types': ['extracted_text', 'text_embeddings', 'text_relationships', 'language_metadata']
            },
            
            ProcessorType.PDF_PROCESSOR: {
                'primary_targets': ['master_registry', 'processor_results', 'document_content', 'relationships'],
                'secondary_targets': ['vector_embeddings', 'metadata_enrichment', 'event_store'],
                'content_types': ['pdf_structure', 'extracted_content', 'pdf_metadata', 'page_relationships']
            },
            
            ProcessorType.CORE_INGEST_HANDLER: {
                'primary_targets': ['master_registry', 'processor_results', 'event_store'],
                'secondary_targets': ['metadata_enrichment'],
                'content_types': ['ingestion_metadata', 'pipeline_events', 'processing_status', 'file_metadata']
            }
        }
        
        return routing
    
    async def distribute_processor_result(
        self, 
        processor_result: ProcessorResult
    ) -> DistributionResult:
        """
        Hauptfunktion: Verteilt ein Processor Result intelligent auf verfügbare Datenbanken
        
        Args:
            processor_result: Structured processor result to distribute
            
        Returns:
            DistributionResult: Detailed result of the distribution process
        """
        
        start_time = time.time()
        distribution_id = str(uuid.uuid4())
        
        self.logger.info(
            f"📤 Starting distribution for {processor_result.document_id} "
            f"from {processor_result.processor_name}"
        )
        
        try:
            # 1. Determine distribution strategy based on current adaptive strategy
            current_strategy = self.adaptive_strategy.current_strategy
            available_dbs = await self._get_available_databases()
            
            # 2. Get processor-specific routing configuration
            routing_config = self._get_processor_routing(processor_result.processor_type)
            
            # 3. Determine target databases and storage locations
            distribution_plan = await self._create_distribution_plan(
                processor_result, routing_config, available_dbs, current_strategy
            )
            
            # 4. Execute distribution across target databases
            distribution_results = await self._execute_distribution(
                distribution_id, processor_result, distribution_plan
            )
            
            # 5. Update cross-references and master registry
            await self._update_master_registry(processor_result, distribution_results)
            
            # 6. Update distribution statistics
            await self._update_distribution_stats(distribution_results)
            
            execution_time = (time.time() - start_time) * 1000
            
            result = DistributionResult(
                document_id=processor_result.document_id,
                processor_name=processor_result.processor_name,
                success=any(dist_result.get('success', False) for dist_result in distribution_results.values()),
                distributed_to={db: list(result.get('stored_items', [])) for db, result in distribution_results.items()},
                execution_time_ms=execution_time,
                errors=[error for result in distribution_results.values() for error in result.get('errors', [])],
                warnings=[warning for result in distribution_results.values() for warning in result.get('warnings', [])],
                fallback_applied=any(result.get('fallback_used', False) for result in distribution_results.values()),
                strategy_used=current_strategy.value if current_strategy else 'unknown'
            )
            
            self.logger.info(
                f"✅ Distribution completed for {processor_result.document_id}: "
                f"{execution_time:.1f}ms, Success: {result.success}"
            )
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            self.logger.error(f"❌ Distribution failed for {processor_result.document_id}: {e}")
            
            return DistributionResult(
                document_id=processor_result.document_id,
                processor_name=processor_result.processor_name,
                success=False,
                distributed_to={},
                execution_time_ms=execution_time,
                errors=[f"Distribution failed: {str(e)}"],
                strategy_used='error_fallback'
            )
    
    async def _get_available_databases(self) -> Dict[str, bool]:
        """Ermittelt verfügbare Datenbanken aus AdaptiveStrategy"""
        
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
    
    def _get_processor_routing(self, processor_type: ProcessorType) -> Dict[str, List[str]]:
        """Holt Routing Configuration für spezifischen Processor Type"""
        
        return self.processor_routing.get(processor_type, {
            'primary_targets': ['master_registry', 'processor_results'],
            'secondary_targets': ['event_store'],
            'content_types': ['generic_content']
        })
    
    async def _create_distribution_plan(
        self,
        processor_result: ProcessorResult,
        routing_config: Dict[str, List[str]],
        available_dbs: Dict[str, bool],
        current_strategy: StrategyType
    ) -> Dict[str, List[DistributionTarget]]:
        """
        Erstellt intelligenten Distribution Plan basierend auf verfügbaren DBs und Strategy
        """
        
        distribution_plan = {}
        
        # Determine which content types to distribute based on processor result
        content_types_to_distribute = self._analyze_processor_result_content(processor_result)
        
        # For each content type, find appropriate targets
        for content_type in content_types_to_distribute:
            if content_type in self.distribution_targets:
                suitable_targets = []
                
                for target in self.distribution_targets[content_type]:
                    # Check if target database is available
                    if available_dbs.get(target.database_type, False):
                        suitable_targets.append(target)
                    else:
                        # Check fallback targets
                        for fallback_db in target.fallback_targets:
                            if available_dbs.get(fallback_db, False):
                                fallback_target = DistributionTarget(
                                    database_type=fallback_db,
                                    storage_location=f"fallback_{target.storage_location}",
                                    priority=target.priority,
                                    content_type=target.content_type,
                                    processor_affinity=target.processor_affinity * 0.7,  # Reduced affinity for fallback
                                    fallback_targets=[]
                                )
                                suitable_targets.append(fallback_target)
                                break
                
                if suitable_targets:
                    distribution_plan[content_type] = suitable_targets
        
        # Always include master registry and processor results (critical)
        for critical_content in ['master_registry', 'processor_results']:
            if critical_content not in distribution_plan:
                # Emergency fallback to SQLite
                distribution_plan[critical_content] = [
                    DistributionTarget(
                        database_type='sqlite',
                        storage_location=f'emergency_{critical_content}',
                        priority=DistributionPriority.CRITICAL,
                        content_type='metadata',
                        processor_affinity=0.5
                    )
                ]
        
        return distribution_plan
    
    def _analyze_processor_result_content(self, processor_result: ProcessorResult) -> List[str]:
        """Analysiert Processor Result und bestimmt welche Content-Types vorhanden sind"""
        
        content_types = ['master_registry', 'processor_results']  # Always present
        
        result_data = processor_result.result_data
        
        # Check for specific content types based on processor type and data
        if processor_result.processor_type == ProcessorType.IMAGE_PROCESSOR:
            content_types.extend(['document_content', 'metadata_enrichment'])
            if 'embedding' in result_data or 'visual_features' in result_data:
                content_types.append('vector_embeddings')
        
        elif processor_result.processor_type == ProcessorType.GEOSPATIAL_PROCESSOR:
            content_types.extend(['geospatial_data', 'relationships'])
            if 'coordinates' in result_data or 'spatial_data' in result_data:
                content_types.append('geospatial_data')
        
        elif processor_result.processor_type in [ProcessorType.TEXT_PROCESSOR, ProcessorType.PDF_PROCESSOR]:
            content_types.extend(['document_content'])
            if 'embedding' in result_data or 'text_vector' in result_data:
                content_types.append('vector_embeddings')
            if 'relationships' in result_data or 'citations' in result_data:
                content_types.append('relationships')
        
        elif processor_result.processor_type in [ProcessorType.OFFICE_INGESTION_HANDLER, ProcessorType.EML_PROCESSOR]:
            content_types.extend(['document_content', 'relationships'])
            if 'metadata' in result_data:
                content_types.append('metadata_enrichment')
        
        # Always include event store for audit trail
        content_types.append('event_store')
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(content_types))
    
    async def _execute_distribution(
        self,
        distribution_id: str,
        processor_result: ProcessorResult,
        distribution_plan: Dict[str, List[DistributionTarget]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Führt die eigentliche Distribution auf die Ziel-Datenbanken aus
        """
        
        distribution_results = {}
        
        # Group targets by database type for efficient execution
        db_operations = {}
        for content_type, targets in distribution_plan.items():
            for target in targets:
                db_type = target.database_type
                if db_type not in db_operations:
                    db_operations[db_type] = []
                db_operations[db_type].append({
                    'content_type': content_type,
                    'target': target,
                    'data': self._extract_content_for_target(processor_result, content_type, target)
                })
        
        # Execute operations for each database type
        for db_type, operations in db_operations.items():
            try:
                result = await self._execute_database_operations(db_type, operations, processor_result)
                distribution_results[db_type] = result
                
            except Exception as e:
                self.logger.error(f"Failed to execute {db_type} operations: {e}")
                distribution_results[db_type] = {
                    'success': False,
                    'errors': [f"{db_type} operations failed: {str(e)}"],
                    'stored_items': [],
                    'fallback_used': False
                }
        
        return distribution_results
    
    def _extract_content_for_target(
        self,
        processor_result: ProcessorResult,
        content_type: str,
        target: DistributionTarget
    ) -> Dict[str, Any]:
        """Extrahiert relevante Daten aus ProcessorResult für spezifischen Target"""
        
        base_data = {
            'document_id': processor_result.document_id,
            'processor_name': processor_result.processor_name,
            'processor_type': processor_result.processor_type.value,
            'confidence_score': processor_result.confidence_score,
            'execution_time_ms': processor_result.execution_time_ms,
            'metadata': processor_result.metadata,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add content-type specific data
        if content_type == 'master_registry':
            base_data.update({
                'file_path': processor_result.metadata.get('file_path', ''),
                'original_filename': processor_result.metadata.get('original_filename', ''),
                'file_size_bytes': processor_result.metadata.get('file_size_bytes', 0),
                'mime_type': processor_result.metadata.get('mime_type', ''),
                'document_category': self._determine_document_category(processor_result),
                'processing_status': 'processing'
            })
        
        elif content_type == 'processor_results':
            base_data.update({
                'result_type': self._determine_result_type(processor_result),
                'result_data': processor_result.result_data,
                'processor_status': 'completed' if not processor_result.error_info else 'failed',
                'error_message': processor_result.error_info.get('message') if processor_result.error_info else None
            })
        
        elif content_type == 'document_content':
            base_data.update({
                'content_text': processor_result.result_data.get('text_content', ''),
                'content_structured': processor_result.result_data.get('structured_data', {}),
                'extraction_method': processor_result.processor_name,
                'content_type': target.content_type
            })
        
        elif content_type == 'vector_embeddings':
            embeddings = processor_result.result_data.get('embedding') or processor_result.result_data.get('vector')
            if embeddings:
                base_data.update({
                    'vector_data': embeddings,
                    'vector_dimension': len(embeddings) if isinstance(embeddings, list) else 0,
                    'embedding_model': processor_result.metadata.get('model_name', 'unknown'),
                    'vector_type': f"{processor_result.processor_type.value}_embedding"
                })
        
        elif content_type == 'relationships':
            relationships = processor_result.result_data.get('relationships', [])
            base_data.update({
                'relationships': relationships,
                'relationship_count': len(relationships),
                'detection_method': processor_result.processor_name
            })
        
        elif content_type == 'geospatial_data':
            spatial_data = processor_result.result_data.get('spatial_data', {})
            base_data.update({
                'latitude': spatial_data.get('latitude'),
                'longitude': spatial_data.get('longitude'),
                'spatial_metadata': spatial_data,
                'coordinate_system': spatial_data.get('crs', 'WGS84')
            })
        
        return base_data
    
    def _determine_document_category(self, processor_result: ProcessorResult) -> str:
        """Bestimmt Document Category basierend auf Processor Type"""
        
        category_mapping = {
            ProcessorType.IMAGE_PROCESSOR: 'image',
            ProcessorType.GEOSPATIAL_PROCESSOR: 'geospatial',
            ProcessorType.AUDIO_VIDEO_PROCESSOR: 'media',
            ProcessorType.OFFICE_INGESTION_HANDLER: 'document',
            ProcessorType.EML_PROCESSOR: 'email',
            ProcessorType.TEXT_PROCESSOR: 'document',
            ProcessorType.PDF_PROCESSOR: 'document',
            ProcessorType.ARCHIVE_PROCESSOR: 'archive',
            ProcessorType.WEB_PROCESSOR: 'web'
        }
        
        return category_mapping.get(processor_result.processor_type, 'unknown')
    
    def _determine_result_type(self, processor_result: ProcessorResult) -> str:
        """Bestimmt Result Type für Processor Results Tabelle"""
        
        if processor_result.error_info:
            return 'error_result'
        
        result_data = processor_result.result_data
        
        if 'embedding' in result_data or 'vector' in result_data:
            return 'embedding_generation'
        elif 'relationships' in result_data:
            return 'relationship_detection'
        elif 'spatial_data' in result_data or 'coordinates' in result_data:
            return 'spatial_analysis'
        elif 'text_content' in result_data:
            return 'content_extraction'
        else:
            return 'metadata_extraction'
    
    async def _execute_database_operations(
        self,
        db_type: str,
        operations: List[Dict],
        processor_result: ProcessorResult
    ) -> Dict[str, Any]:
        """
        Führt Database-spezifische Operations aus
        
        This is a placeholder implementation. In production, this would
        use actual database connections and APIs.
        """
        
        try:
            stored_items = []
            warnings = []
            
            self.logger.debug(f"Executing {len(operations)} operations for {db_type}")
            
            # Simulate database operations
            for operation in operations:
                content_type = operation['content_type']
                target = operation['target']
                data = operation['data']
                
                # Simulate storage operation
                storage_id = f"{db_type}_{target.storage_location}_{processor_result.document_id}_{int(time.time())}"
                stored_items.append(f"{target.storage_location}:{storage_id}")
                
                # Add slight delay to simulate real database operations
                await asyncio.sleep(0.01)
            
            # Update statistics
            self.distribution_stats['successful_distributions'] += len(operations)
            
            return {
                'success': True,
                'stored_items': stored_items,
                'operations_count': len(operations),
                'warnings': warnings,
                'fallback_used': False,
                'execution_time_ms': len(operations) * 10  # Simulate execution time
            }
            
        except Exception as e:
            self.distribution_stats['failed_distributions'] += len(operations)
            
            return {
                'success': False,
                'stored_items': [],
                'errors': [f"Database operation failed: {str(e)}"],
                'fallback_used': False,
                'execution_time_ms': 0
            }
    
    async def _distribute_to_base_strategy(
        self,
        processor_result: ProcessorResult,
        optimized_targets: Dict[str, List] = None
    ) -> DistributionResult:
        """
        Base distribution method that bypasses processor-specific strategies
        to avoid recursion. Used by ProcessorDistributionStrategy classes.
        """
        
        start_time = time.time()
        
        try:
            # Get available databases
            available_dbs = await self._get_available_databases()
            
            # Use optimized targets if provided, otherwise create basic plan
            if optimized_targets:
                distribution_plan = optimized_targets
            else:
                distribution_plan = {
                    'basic_content': [
                        DistributionTarget(
                            database_type='sqlite',
                            storage_location='basic_results',
                            priority=DistributionPriority.HIGH,
                            content_type='processor_result',
                            processor_affinity=1.0,
                            fallback_targets=[]
                        )
                    ]
                }
            
            # Execute distribution without processor-specific routing
            distribution_results = await self._execute_base_distribution(
                processor_result, distribution_plan, available_dbs
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            return DistributionResult(
                document_id=processor_result.document_id,
                processor_name=processor_result.processor_name,
                success=any(result.get('success', False) for result in distribution_results.values()),
                distributed_to={db: result.get('stored_items', []) for db, result in distribution_results.items()},
                execution_time_ms=execution_time,
                errors=[error for result in distribution_results.values() for error in result.get('errors', [])],
                fallback_applied=any(result.get('fallback_used', False) for result in distribution_results.values()),
                strategy_used='base_distribution'
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            return DistributionResult(
                document_id=processor_result.document_id,
                processor_name=processor_result.processor_name,
                success=False,
                distributed_to={},
                execution_time_ms=execution_time,
                errors=[f"Base distribution failed: {str(e)}"],
                strategy_used='base_error_fallback'
            )
    
    async def _execute_base_distribution(
        self,
        processor_result: ProcessorResult,
        distribution_plan: Dict[str, List],
        available_dbs: Dict[str, bool]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Executes basic distribution without processor-specific logic
        """
        
        results = {}
        
        for content_type, targets in distribution_plan.items():
            for target in targets:
                db_type = target.database_type if hasattr(target, 'database_type') else target.get('database_type', 'sqlite')
                
                if available_dbs.get(db_type, False):
                    # Prepare basic operations
                    operations = [{
                        'content_type': content_type,
                        'target': target,
                        'data': {
                            'document_id': processor_result.document_id,
                            'processor_name': processor_result.processor_name,
                            'result_data': processor_result.result_data,
                            'metadata': processor_result.metadata
                        }
                    }]
                    
                    # Execute operations
                    results[db_type] = await self._execute_database_operations(
                        db_type, operations, processor_result
                    )
        
        # If no distributions succeeded, fallback to SQLite
        if not any(result.get('success', False) for result in results.values()):
            fallback_operations = [{
                'content_type': 'fallback_content',
                'target': {'storage_location': 'fallback_storage'},
                'data': {
                    'document_id': processor_result.document_id,
                    'processor_name': processor_result.processor_name,
                    'result_data': processor_result.result_data
                }
            }]
            
            results['sqlite'] = await self._execute_database_operations(
                'sqlite', fallback_operations, processor_result
            )
            results['sqlite']['fallback_used'] = True
        
        return results
    
    async def _update_master_registry(
        self,
        processor_result: ProcessorResult,
        distribution_results: Dict[str, Dict[str, Any]]
    ):
        """
        Aktualisiert Master Registry mit Distribution References
        
        This would update the PostgreSQL master registry with references
        to data stored in other databases.
        """
        
        # Build cross-database references
        db_refs = {}
        for db_type, result in distribution_results.items():
            if result.get('success', False):
                db_refs[f"{db_type}_refs"] = {
                    'stored_items': result.get('stored_items', []),
                    'timestamp': datetime.now().isoformat(),
                    'operations_count': result.get('operations_count', 0)
                }
        
        self.logger.debug(f"Updated master registry for {processor_result.document_id} with {len(db_refs)} DB references")
    
    async def _update_distribution_stats(self, distribution_results: Dict[str, Dict[str, Any]]):
        """Aktualisiert Distribution Statistics"""
        
        self.distribution_stats['total_processed'] += 1
        
        successful_dbs = sum(1 for result in distribution_results.values() if result.get('success', False))
        if successful_dbs > 0:
            self.distribution_stats['successful_distributions'] += 1
        else:
            self.distribution_stats['failed_distributions'] += 1
        
        fallback_used = any(result.get('fallback_used', False) for result in distribution_results.values())
        if fallback_used:
            self.distribution_stats['fallback_used'] += 1
    
    def get_distribution_stats(self) -> Dict[str, Any]:
        """Holt aktuelle Distribution Statistics"""
        
        total = self.distribution_stats['total_processed']
        
        return {
            **self.distribution_stats,
            'success_rate': (self.distribution_stats['successful_distributions'] / total) if total > 0 else 0,
            'fallback_rate': (self.distribution_stats['fallback_used'] / total) if total > 0 else 0
        }
    
    async def distribute_multiple_results(
        self,
        processor_results: List[ProcessorResult]
    ) -> List[DistributionResult]:
        """
        Batch Distribution für mehrere Processor Results
        """
        
        self.logger.info(f"🔄 Starting batch distribution for {len(processor_results)} results")
        
        # Process in batches to avoid overwhelming the system
        results = []
        
        for i in range(0, len(processor_results), self.batch_size):
            batch = processor_results[i:i + self.batch_size]
            
            # Process batch concurrently with limited concurrency
            semaphore = asyncio.Semaphore(self.max_concurrent_distributions)
            
            async def process_with_semaphore(processor_result):
                async with semaphore:
                    return await self.distribute_processor_result(processor_result)
            
            batch_results = await asyncio.gather(
                *[process_with_semaphore(result) for result in batch],
                return_exceptions=True
            )
            
            # Handle any exceptions in batch results
            for j, batch_result in enumerate(batch_results):
                if isinstance(batch_result, Exception):
                    # Create error result for failed distribution
                    error_result = DistributionResult(
                        document_id=batch[j].document_id,
                        processor_name=batch[j].processor_name,
                        success=False,
                        distributed_to={},
                        execution_time_ms=0,
                        errors=[f"Batch processing failed: {str(batch_result)}"]
                    )
                    results.append(error_result)
                else:
                    results.append(batch_result)
        
        successful = sum(1 for result in results if result.success)
        
        self.logger.info(
            f"✅ Batch distribution completed: {successful}/{len(results)} successful"
        )
        
        return results


# Convenience functions for integration
async def create_uds3_distributor(
    adaptive_strategy: AdaptiveMultiDBStrategy,
    database_manager: Optional[DatabaseManager] = None,
    config: Dict = None
) -> UDS3MultiDBDistributor:
    """
    Factory function für UDS3MultiDBDistributor
    """
    
    distributor = UDS3MultiDBDistributor(
        adaptive_strategy=adaptive_strategy,
        database_manager=database_manager,
        config=config
    )
    
    logging.info("🔗 UDS3MultiDBDistributor created and ready for distribution")
    
    return distributor


def create_processor_result_from_uds3_job(job_result) -> ProcessorResult:
    """
    Konvertiert UDS3 JobResult zu ProcessorResult für Distribution
    
    This function would integrate with the existing UDS3 pipeline
    by converting JobResult objects to our structured ProcessorResult format.
    """
    
    # This is a placeholder - would need actual UDS3 JobResult structure
    return ProcessorResult(
        processor_name=getattr(job_result, 'processor_name', 'unknown'),
        processor_type=ProcessorType.UNKNOWN,
        document_id=getattr(job_result, 'document_id', 'unknown'),
        result_data=getattr(job_result, 'data', {}),
        confidence_score=getattr(job_result, 'confidence', 0.5),
        execution_time_ms=getattr(job_result, 'execution_time_ms', 0),
        metadata=getattr(job_result, 'metadata', {}),
        error_info=getattr(job_result, 'error_info', None)
    )


if __name__ == "__main__":
    # Example usage and testing
    async def test_uds3_distributor():
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
        
        # Create distributor
        distributor = await create_uds3_distributor(mock_strategy)
        
        # Test processor result
        test_result = ProcessorResult(
            processor_name="ImageProcessor",
            processor_type=ProcessorType.IMAGE_PROCESSOR,
            document_id="test_doc_001",
            result_data={
                'text_content': 'Test image content',
                'embedding': [0.1, 0.2, 0.3, 0.4, 0.5],
                'metadata': {'width': 1920, 'height': 1080}
            },
            confidence_score=0.85,
            execution_time_ms=1250,
            metadata={'file_path': '/test/image.jpg', 'mime_type': 'image/jpeg'}
        )
        
        # Test distribution
        result = await distributor.distribute_processor_result(test_result)
        
        print(f"Distribution Result: {result}")
        print(f"Distribution Stats: {distributor.get_distribution_stats()}")
    
    # Run test
    asyncio.run(test_uds3_distributor())