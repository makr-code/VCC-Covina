#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Pipeline Multi-DB Integration

Erweitert die bestehende UDS3 Ingestion Pipeline um Multi-Database Distribution.
Integriert den UDS3MultiDBDistributor nahtlos in die CoreIngestHandler und 
andere Processor Handler für automatische Verteilung der Processor Results
auf die verfügbaren Datenbanken.

Features        async def _distribute_result_async(self, processor_result):
- Seamless Integration in bestehende UDS3 Pipeline
- Automatic Distribution Hooks für alle Handler
- Adaptive Strategy Integration mit Pipeline Context  
- Error Recovery und Fallback Mechanisms
- Performance Monitoring und Statistics
- Pipeline-Level Distribution Coordination
- Backwards Compatibility mit existing handlers

Autor: Covina Development Team
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Import UDS3 Core Components
try:
    from ingestion_core import (
        JobResult, Job, File, ResultType,
        CoreIngestHandler, CoreTransformHandler, CoreApiExportHandler,
        MetadataAggregationHandler, QualityVerificationHandler,
        FileProcessorHandler, Orchestrator
    )
    from .adaptive_multi_db_strategy import AdaptiveMultiDBStrategy
    UDS3_CORE_AVAILABLE = True
except ImportError:
    logging.debug("UDS3 Core components not fully available - running in standalone mode")
    UDS3_CORE_AVAILABLE = False


class DistributionHookType:
    """Types of distribution hooks for different pipeline stages"""
    PRE_PROCESSING = "pre_processing"        # Before handler execution
    POST_PROCESSING = "post_processing"      # After successful handler execution
    ERROR_HANDLING = "error_handling"        # On handler errors
    PIPELINE_COMPLETE = "pipeline_complete"  # When entire pipeline completes
    BATCH_COMPLETE = "batch_complete"        # When batch of files completes


@dataclass
class PipelineDistributionContext:
    """Context information for pipeline-level distribution decisions"""
    pipeline_id: str
    pipeline_name: str
    file_count: int
    completed_files: int
    current_file_id: str
    current_handler: str
    pipeline_start_time: float
    distribution_stats: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    adaptive_strategy_changes: List[str] = field(default_factory=list)


class UDS3PipelineDistributionManager:
    """
    Manages Multi-DB Distribution integration within UDS3 Pipeline
    
    Provides seamless integration between existing UDS3 handlers and 
    the new MultiDBDistributor system without breaking existing functionality.
    """
    
    def __init__(
        self, 
        distributor,  # UDS3MultiDBDistributor - late import to avoid circular
        orchestrator=None,
        config=None
    ):
        self.distributor = distributor
        self.orchestrator = orchestrator
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Pipeline state tracking
        self.active_pipelines[str, PipelineDistributionContext] = {}
        self.distribution_hooks[str, List[Callable]] = {}
        self.handler_processors[str, ProcessorType] = {}
        
        # Performance configuration
        self.enable_async_distribution = self.config.get('enable_async_distribution', True)
        self.distribution_timeout = self.config.get('distribution_timeout_ms', 5000)
        self.batch_distribution_size = self.config.get('batch_distribution_size', 50)
        
        # Integration statistics
        self.integration_stats = {
            'total_handler_calls': 0,
            'distributions_triggered': 0,
            'async_distributions': 0,
            'synchronous_distributions': 0,
            'distribution_errors': 0,
            'pipeline_completions': 0
        }
        
        # Initialize handler mapping
        self._initialize_handler_processor_mapping()
    
    def _initialize_handler_processor_mapping(self):
        """Maps UDS3 Handler types to ProcessorTypes for distribution"""
        
        # Late import to avoid circular dependencies
        try:
            from .uds3_multi_db_distributor import ProcessorType
            self.processor_type_available = True
        except ImportError:
            self.processor_type_available = False
            logging.warning("ProcessorType not available - using string mappings")
        
        if self.processor_type_available:
            self.handler_processors = {
                'core_ingest': ProcessorType.CORE_INGEST_HANDLER,
                'core_transform': ProcessorType.TEXT_PROCESSOR,
                'core_api_export': ProcessorType.CORE_INGEST_HANDLER,
                'metadata_aggregator': ProcessorType.TEXT_PROCESSOR,
                'quality_verifier': ProcessorType.TEXT_PROCESSOR,
                'image_processor': ProcessorType.IMAGE_PROCESSOR,
                'geospatial_processor': ProcessorType.GEOSPATIAL_PROCESSOR,
                'audio_video_processor': ProcessorType.AUDIO_VIDEO_PROCESSOR,
                'office_ingestion': ProcessorType.OFFICE_INGESTION_HANDLER,
                'eml_processor': ProcessorType.EML_PROCESSOR,
                'pdf_processor': ProcessorType.PDF_PROCESSOR,
                'archive_processor': ProcessorType.ARCHIVE_PROCESSOR,
                'web_processor': ProcessorType.WEB_PROCESSOR,
                'text_processor': ProcessorType.TEXT_PROCESSOR
            }
        else:
            # Fallback string mapping
            self.handler_processors = {
                'core_ingest': 'CORE_INGEST_HANDLER',
                'core_transform': 'TEXT_PROCESSOR',
                'core_api_export': 'CORE_INGEST_HANDLER',
                'metadata_aggregator': 'TEXT_PROCESSOR',
                'quality_verifier': 'TEXT_PROCESSOR',
                'image_processor': 'IMAGE_PROCESSOR',
                'geospatial_processor': 'GEOSPATIAL_PROCESSOR',
                'audio_video_processor': 'AUDIO_VIDEO_PROCESSOR',
                'office_ingestion': 'OFFICE_INGESTION_HANDLER',
                'eml_processor': 'EML_PROCESSOR',
                'pdf_processor': 'PDF_PROCESSOR',
                'archive_processor': 'ARCHIVE_PROCESSOR',
                'web_processor': 'WEB_PROCESSOR',
                'text_processor': 'TEXT_PROCESSOR'
            }
    
    def register_distribution_hook(
        self, 
        hook_type, 
        hook_function: Callable
    ):
        """
        Registers a distribution hook for specific pipeline events
        
        Args:
            hook_type: Type of hook (from DistributionHookType)
            hook_function: Function to call when hook is triggered
        """
        
        if hook_type not in self.distribution_hooks:
            self.distribution_hooks[hook_type] = []
        
        self.distribution_hooks[hook_type].append(hook_function)
        
        self.logger.debug(f"Registered distribution hook: {hook_type}")
    
    async def integrate_with_handler(
        self, 
        handler,  # FileProcessorHandler
        enhanced_distribution = True
    ):
        """
        Wraps existing UDS3 handler with distribution functionality
        
        Args:
            handler: Original UDS3 handler to enhance
            enhanced_distribution: Whether to enable enhanced distribution features
            
        Returns:
            Enhanced handler with distribution integration
        """
        
        original_process_file = handler.process_file
        
        async def enhanced_process_file(file_obj, job):
            """Enhanced process_file with distribution integration"""
            
            start_time = time.time()
            
            try:
                # Update integration statistics
                self.integration_stats['total_handler_calls'] += 1
                
                # Execute pre-processing hooks
                await self._execute_hooks(
                    DistributionHookType.PRE_PROCESSING,
                    handler=handler,
                    file_obj=file_obj,
                    job=job
                )
                
                # Execute original handler logic
                result = original_process_file(file_obj, job)
                
                # Handle distribution if result is successful
                if result.result_type == ResultType.SUCCESS and enhanced_distribution:
                    await self._handle_successful_processing(
                        handler, file_obj, job, result, start_time
                    )
                
                # Execute post-processing hooks
                await self._execute_hooks(
                    DistributionHookType.POST_PROCESSING,
                    handler=handler,
                    file_obj=file_obj,
                    job=job,
                    result=result
                )
                
                return result
                
            except Exception as e:
                # Execute error handling hooks
                await self._execute_hooks(
                    DistributionHookType.ERROR_HANDLING,
                    handler=handler,
                    file_obj=file_obj,
                    job=job,
                    error=e
                )
                
                # Return error result
                return JobResult(
                    job_id=job.job_id,
                    result_type=ResultType.ERROR,
                    stage=handler.worker_type,
                    target_id=file_obj.file_id,
                    target_type=job.job_type,
                    error=f"Enhanced handler execution failed: {str(e)}"
                )
        
        # Replace the process_file method
        if asyncio.iscoroutinefunction(original_process_file):
            handler.process_file = enhanced_process_file
        else:
            # Wrap synchronous method to work with async enhancement
            def sync_wrapper(file_obj, job):
                return asyncio.run(enhanced_process_file(file_obj, job))
            handler.process_file = sync_wrapper
        
        self.logger.info(f"✅ Enhanced handler {handler.worker_type} with distribution integration")
        
        return handler
    
    async def _handle_successful_processing(
        self,
        handler,  # FileProcessorHandler
        file_obj,  # File
        job,  # Job
        result,  # JobResult
        start_time
    ):
        """Handles distribution for successful processing results"""
        
        try:
            # Create ProcessorResult from JobResult
            processor_result = self._create_processor_result_from_job_result(
                handler, file_obj, job, result, start_time
            )
            
            # Decide on distribution strategy (async vs sync)
            if self.enable_async_distribution:
                # Async distribution (non-blocking)
                asyncio.create_task(
                    self._distribute_result_async(processor_result)
                )
                self.integration_stats['async_distributions'] += 1
            else:
                # Synchronous distribution (blocking)
                distribution_result = await self.distributor.distribute_processor_result(
                    processor_result
                )
                self._log_distribution_result(distribution_result)
                self.integration_stats['synchronous_distributions'] += 1
            
            self.integration_stats['distributions_triggered'] += 1
            
        except Exception as e:
            self.logger.error(f"Distribution handling failed for {file_obj.file_id}: {e}")
            self.integration_stats['distribution_errors'] += 1
    
    def _create_processor_result_from_job_result(
        self,
        handler,  # FileProcessorHandler
        file_obj,  # File
        job,  # Job
        result,  # JobResult
        start_time
    ):
        """Converts UDS3 JobResult to ProcessorResult for distribution"""
        
        # Determine processor type
        processor_type = self.handler_processors.get(
            handler.worker_type, 
            ProcessorType.UNKNOWN
        )
        
        # Extract result data
        result_data = {}
        if hasattr(result, 'data') and result.data:
            result_data = result.data
        
        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000
        
        # Build metadata from file and job information
        metadata = {
            'file_path': file_obj.file_path if hasattr(file_obj, 'file_path') else '',
            'file_id': file_obj.file_id,
            'job_id': job.job_id,
            'job_type': job.job_type,
            'pipeline_id': getattr(job, 'pipeline_id', ''),
            'worker_type': handler.worker_type,
            'result_type': result.result_type.value if hasattr(result.result_type, 'value') else str(result.result_type),
            'processing_timestamp': datetime.now().isoformat()
        }
        
        # Add file-specific metadata if available
        if hasattr(file_obj, '__dict__'):
            file_metadata = {
                k: v for k, v in file_obj.__dict__.items() 
                if k not in ['file_path', 'file_id'] and not k.startswith('_')
            }
            metadata.update(file_metadata)
        
        # Determine confidence score
        confidence_score = 1.0  # Default high confidence for successful results
        if hasattr(result, 'confidence'):
            confidence_score = result.confidence
        elif result.result_type != ResultType.SUCCESS:
            confidence_score = 0.1  # Low confidence for failed results
        
        return ProcessorResult(
            processor_name=f"{handler.__class__.__name__}",
            processor_type=processor_type,
            document_id=file_obj.file_id,
            result_data=result_data,
            confidence_score=confidence_score,
            execution_time_ms=int(execution_time),
            metadata=metadata,
            error_info=None if result.result_type == ResultType.SUCCESS else {
                'message': getattr(result, 'error', 'Processing failed'),
                'stage': result.stage
            }
        )
    
    async def _distribute_result_async(self, processor_result):
        """Handles asynchronous distribution with timeout protection"""
        
        try:
            # Apply timeout to prevent hanging
            distribution_result = await asyncio.wait_for(
                self.distributor.distribute_processor_result(processor_result),
                timeout=self.distribution_timeout / 1000.0
            )
            
            self._log_distribution_result(distribution_result)
            
        except asyncio.TimeoutError:
            self.logger.warning(
                f"Distribution timeout for {processor_result.document_id} "
                f"after {self.distribution_timeout}ms"
            )
            self.integration_stats['distribution_errors'] += 1
            
        except Exception as e:
            self.logger.error(f"Async distribution failed for {processor_result.document_id}: {e}")
            self.integration_stats['distribution_errors'] += 1
    
    def _log_distribution_result(self, distribution_result):
        """Logs distribution results with appropriate level"""
        
        if distribution_result.success:
            self.logger.debug(
                f"✅ Distribution successful for {distribution_result.document_id}: "
                f"{distribution_result.execution_time_ms:.1f}ms, "
                f"Strategy: {distribution_result.strategy_used}"
            )
        else:
            self.logger.warning(
                f"⚠️ Distribution failed for {distribution_result.document_id}: "
                f"Errors: {distribution_result.errors}"
            )
    
    async def _execute_hooks(self, hook_type, **kwargs):
        """Executes registered hooks for specific events"""
        
        if hook_type not in self.distribution_hooks:
            return
        
        for hook_function in self.distribution_hooks[hook_type]:
            try:
                if asyncio.iscoroutinefunction(hook_function):
                    await hook_function(**kwargs)
                else:
                    hook_function(**kwargs)
                    
            except Exception as e:
                self.logger.error(f"Distribution hook {hook_type} failed: {e}")
    
    def register_pipeline_context(
        self, 
        pipeline_id,
        pipeline_name,
        file_count
    ):
        """Registers a pipeline for distribution tracking"""
        
        self.active_pipelines[pipeline_id] = PipelineDistributionContext(
            pipeline_id=pipeline_id,
            pipeline_name=pipeline_name,
            file_count=file_count,
            completed_files=0,
            current_file_id='',
            current_handler='',
            pipeline_start_time=time.time()
        )
        
        self.logger.info(f"📋 Registered pipeline {pipeline_name} with {file_count} files")
    
    async def notify_pipeline_completion(self, pipeline_id):
        """Handles pipeline completion for distribution coordination"""
        
        if pipeline_id not in self.active_pipelines:
            return
        
        context = self.active_pipelines[pipeline_id]
        
        try:
            # Execute pipeline completion hooks
            await self._execute_hooks(
                DistributionHookType.PIPELINE_COMPLETE,
                pipeline_context=context,
                distributor=self.distributor
            )
            
            # Update statistics
            self.integration_stats['pipeline_completions'] += 1
            
            # Log completion
            pipeline_duration = time.time() - context.pipeline_start_time
            
            self.logger.info(
                f"🏁 Pipeline {context.pipeline_name} completed: "
                f"{context.completed_files}/{context.file_count} files, "
                f"Duration: {pipeline_duration:.1f}s"
            )
            
        finally:
            # Clean up pipeline context
            del self.active_pipelines[pipeline_id]
    
    def get_integration_stats(self):
        """Returns current integration statistics"""
        
        distributor_stats = self.distributor.get_distribution_stats()
        
        return {
            'integration': self.integration_stats,
            'distribution': distributor_stats,
            'active_pipelines': len(self.active_pipelines),
            'registered_hooks': {
                hook_type: len(hooks) 
                for hook_type, hooks in self.distribution_hooks.items()
            }
        }


class UDS3EnhancedOrchestrator:
    """
    Enhanced Orchestrator with integrated Multi-DB Distribution
    
    Extends the existing UDS3 Orchestrator with seamless distribution
    capabilities while maintaining full backwards compatibility.
    """
    
    def __init__(
        self,
        queue,
        pool,
        pipelines_dir = "pipelines",
        state_store=None,
        adaptive_strategy = None,
        distribution_config = None
    ):
        super().__init__(queue, pool, pipelines_dir, state_store)
        
        self.adaptive_strategy = adaptive_strategy
        self.distribution_config = distribution_config or {}
        self.distribution_manager = None
        
        # Initialize distribution if adaptive strategy is provided
        if self.adaptive_strategy:
            asyncio.create_task(self._initialize_distribution())
    
    async def _initialize_distribution(self):
        """Initializes the distribution system asynchronously"""
        
        try:
            # Create distributor
            distributor = await create_uds3_distributor(
                adaptive_strategy=self.adaptive_strategy,
                database_manager=None,  # Use default from strategy
                config=self.distribution_config
            )
            
            # Create distribution manager
            self.distribution_manager = UDS3PipelineDistributionManager(
                distributor=distributor,
                orchestrator=self,
                config=self.distribution_config
            )
            
            # Register standard hooks
            await self._register_standard_distribution_hooks()
            
            self.logger.info("✅ UDS3 Enhanced Orchestrator with Multi-DB Distribution initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize distribution system: {e}")
    
    async def _register_standard_distribution_hooks(self):
        """Registers standard distribution hooks for common pipeline events"""
        
        if not self.distribution_manager:
            return
        
        # Pipeline completion hook
        async def on_pipeline_complete(pipeline_context=None, **kwargs):
            if pipeline_context:
                # Trigger batch distribution for any remaining results
                await self.distribution_manager.notify_pipeline_completion(
                    pipeline_context.pipeline_id
                )
        
        self.distribution_manager.register_distribution_hook(
            DistributionHookType.PIPELINE_COMPLETE,
            on_pipeline_complete
        )
        
        # Error handling hook
        def on_processing_error(handler=None, error=None, **kwargs):
            if error:
                self.logger.warning(f"Processing error in {handler.worker_type if handler else 'unknown'}: {error}")
        
        self.distribution_manager.register_distribution_hook(
            DistributionHookType.ERROR_HANDLING,
            on_processing_error
        )
    
    def enhance_handler_with_distribution(
        self, 
        handler,  # FileProcessorHandler
        enhanced_distribution = True
    ):
        """
        Enhances a handler with distribution capabilities
        
        Args:
            handler: Handler to enhance
            enhanced_distribution: Whether to enable enhanced features
            
        Returns:
            Enhanced handler
        """
        
        if self.distribution_manager:
            return asyncio.run(
                self.distribution_manager.integrate_with_handler(
                    handler, enhanced_distribution
                )
            )
        
        # Return original handler if distribution not available
        return handler
    
    def get_distribution_stats(self):
        """Gets current distribution statistics"""
        
        if self.distribution_manager:
            return self.distribution_manager.get_integration_stats()
        
        return None


# Enhanced Handler Factory Functions
def create_enhanced_core_handlers(
    distribution_manager = None
):
    """
    Creates enhanced versions of core UDS3 handlers with distribution integration
    
    Args:
        distribution_manager: Distribution manager for integration
        
    Returns:
        Dictionary of enhanced handlers
    """
    
    handlers = {}
    
    # Create standard handlers
    if UDS3_CORE_AVAILABLE:
        standard_handlers = {
            'core_ingest': CoreIngestHandler(),
            'core_transform': CoreTransformHandler(),
            'core_api_export': CoreApiExportHandler(),
            'metadata_aggregator': MetadataAggregationHandler(),
            'quality_verifier': QualityVerificationHandler()
        }
        
        # Enhance with distribution if manager available
        if distribution_manager:
            for name, handler in standard_handlers.items():
                enhanced_handler = asyncio.run(
                    distribution_manager.integrate_with_handler(handler)
                )
                handlers[name] = enhanced_handler
        else:
            handlers.update(standard_handlers)
    
    return handlers


def bootstrap_enhanced_orchestrator(
    caps=None,
    pipelines_dir = "pipelines",
    adaptive_strategy = None,
    distribution_config = None,
    uds3_adapter = None,
    state_store = None
) -> UDS3EnhancedOrchestrator:
    """
    Bootstrap function for enhanced UDS3 orchestrator with distribution
    
    Args:
        caps: Handler capabilities configuration
        pipelines_dir: Directory containing pipeline definitions
        adaptive_strategy: Multi-database adaptive strategy
        distribution_config: Configuration for distribution system
        uds3_adapter: Optional UDS3 adapter
        state_store: Optional state store
        
    Returns:
        Enhanced orchestrator with distribution capabilities
    """
    
    if not UDS3_CORE_AVAILABLE:
        raise ImportError("UDS3 Core components not available")
    
    from ingestion_core import JobQueue, WorkerPool
    
    # Create standard components
    default_caps = {
        'core_ingest': 1,
        'core_transform': 1,
        'core_api_export': 1,
        'metadata_aggregator': 1,
        'quality_verifier': 1,
    }
    
    effective_caps = dict(default_caps)
    if caps:
        effective_caps.update(caps)
    
    # Create queue and worker pool
    queue = JobQueue()
    pool = WorkerPool(queue, caps=effective_caps)
    
    # Create enhanced orchestrator
    orchestrator = UDS3EnhancedOrchestrator(
        queue=queue,
        pool=pool,
        pipelines_dir=pipelines_dir,
        state_store=state_store,
        adaptive_strategy=adaptive_strategy,
        distribution_config=distribution_config
    )
    
    # Set UDS3 adapter if provided
    if uds3_adapter:
        orchestrator.set_uds3_adapter(uds3_adapter)
    
    # Register enhanced handlers
    if orchestrator.distribution_manager:
        enhanced_handlers = create_enhanced_core_handlers(orchestrator.distribution_manager)
        
        for handler_type, handler in enhanced_handlers.items():
            pool.register_enhanced_handler_factory(
                handler.worker_type,
                lambda h=handler: h,
                capabilities=handler.capabilities
            )
    
    logging.info("🚀 Enhanced UDS3 Orchestrator with Multi-DB Distribution bootstrapped")
    
    return orchestrator


if __name__ == "__main__":
    # Example usage and testing
    async def test_pipeline_integration():
        """Test function for pipeline integration"""
        
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
        
        # Test enhanced orchestrator bootstrap
        try:
            orchestrator = bootstrap_enhanced_orchestrator(
                adaptive_strategy=mock_strategy,
                distribution_config={'enable_async_distribution': True}
            )
            
            # Test distribution stats
            stats = orchestrator.get_distribution_stats()
            print(f"Distribution Stats: {stats}")
            
        except ImportError:
            print("UDS3 Core not available - running mock test")
            
            # Create standalone distribution manager
            from .uds3_multi_db_distributor import create_uds3_distributor
            
            distributor = await create_uds3_distributor(mock_strategy)
            distribution_manager = UDS3PipelineDistributionManager(distributor)
            
            # Test pipeline registration
            distribution_manager.register_pipeline_context(
                pipeline_id="test_pipeline_001",
                pipeline_name="Test Pipeline",
                file_count=10
            )
            
            # Test completion
            await distribution_manager.notify_pipeline_completion("test_pipeline_001")
            
            print(f"Integration Stats: {distribution_manager.get_integration_stats()}")
    
    # Run test
    asyncio.run(test_pipeline_integration())
