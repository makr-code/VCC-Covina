#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Multi-DB Distribution Performance Testing & Optimization

Umfassende Performance Tests, Benchmarks und Optimierungen für das
UDS3 Multi-Database Distribution System. Validiert die Performance
verschiedener Strategy Configurations, Batch Processing Optimizations
und adaptiver Fallback Mechanisms unter verschiedenen Lastbedingungen.

Features:
- Comprehensive Performance Benchmarks
- Strategy Configuration Testing
- Batch Processing Optimization
- Adaptive Fallback Validation
- Load Testing und Stress Testing
- Performance Regression Detection
- Memory Usage Monitoring
- Database Connection Pool Testing
- Throughput und Latency Analysis
- Performance Reporting und Visualization

Autor: Covina Development Team
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
import time
import uuid
import psutil
import statistics
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import csv
import io

# Import UDS3 components for testing
try:
    from .uds3_multi_db_distributor import (
        UDS3MultiDBDistributor, ProcessorResult, ProcessorType, 
        DistributionResult, create_uds3_distributor
    )
    from .adaptive_multi_db_strategy import (
        AdaptiveMultiDBStrategy, StrategyType, DatabaseAvailability
    )
    from .processor_distribution_methods import (
        UDS3EnhancedMultiDBDistributor, create_enhanced_uds3_distributor
    )
    from .saga_multi_db_integration import (
        SAGAIntegratedMultiDBDistributor, create_saga_integrated_distributor
    )
    from .pipeline_integration import (
        UDS3PipelineDistributionManager, bootstrap_enhanced_orchestrator
    )
    UDS3_TEST_COMPONENTS_AVAILABLE = True
except ImportError:
    logging.warning("UDS3 components not available for performance testing")
    UDS3_TEST_COMPONENTS_AVAILABLE = False

# Standard testing imports
import threading
from collections import defaultdict
import gc


@dataclass
class PerformanceTestConfig:
    """Configuration for performance tests"""
    
    # Test execution parameters
    test_duration_seconds: float = 60.0
    max_concurrent_operations: int = 50
    batch_sizes: List[int] = field(default_factory=lambda: [1, 10, 50, 100])
    
    # Load testing parameters
    ramp_up_duration_seconds: float = 10.0
    target_throughput_ops_per_second: float = 100.0
    stress_test_multiplier: float = 2.0
    
    # Data generation parameters
    document_size_bytes_min: int = 1024      # 1KB
    document_size_bytes_max: int = 1048576   # 1MB
    embedding_dimensions: List[int] = field(default_factory=lambda: [128, 256, 512, 1024])
    
    # Strategy configurations to test
    test_strategies: List[StrategyType] = field(default_factory=lambda: [
        StrategyType.FULL_POLYGLOT,
        StrategyType.TRI_DATABASE,
        StrategyType.DUAL_DATABASE,
        StrategyType.POSTGRESQL_ENHANCED,
        StrategyType.SQLITE_MONOLITH
    ])
    
    # Performance thresholds
    max_acceptable_latency_ms: float = 1000.0
    min_acceptable_throughput_ops_per_second: float = 50.0
    max_acceptable_memory_mb: float = 512.0
    max_acceptable_error_rate: float = 0.01  # 1%
    
    # Monitoring parameters
    memory_sampling_interval_seconds: float = 1.0
    performance_reporting_enabled: bool = True


@dataclass
class PerformanceMetrics:
    """Performance metrics collected during testing"""
    
    # Throughput metrics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    operations_per_second: float = 0.0
    
    # Latency metrics
    latencies_ms: List[float] = field(default_factory=list)
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    
    # Resource usage metrics
    memory_usage_samples_mb: List[float] = field(default_factory=list)
    avg_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Distribution-specific metrics
    distribution_success_rate: float = 0.0
    fallback_usage_rate: float = 0.0
    saga_compensation_rate: float = 0.0
    
    # Error analysis
    error_types: Dict[str, int] = field(default_factory=dict)
    timeout_count: int = 0
    
    # Test metadata
    test_start_time: datetime = field(default_factory=datetime.now)
    test_duration_seconds: float = 0.0
    configuration_tested: str = ""
    
    def calculate_derived_metrics(self):
        """Calculates derived metrics from collected data"""
        
        if self.latencies_ms:
            self.avg_latency_ms = statistics.mean(self.latencies_ms)
            self.p50_latency_ms = statistics.median(self.latencies_ms)
            
            sorted_latencies = sorted(self.latencies_ms)
            n = len(sorted_latencies)
            
            if n > 0:
                self.p95_latency_ms = sorted_latencies[int(0.95 * n)]
                self.p99_latency_ms = sorted_latencies[int(0.99 * n)]
                self.max_latency_ms = max(self.latencies_ms)
        
        if self.memory_usage_samples_mb:
            self.avg_memory_mb = statistics.mean(self.memory_usage_samples_mb)
            self.peak_memory_mb = max(self.memory_usage_samples_mb)
        
        if self.total_operations > 0:
            self.distribution_success_rate = self.successful_operations / self.total_operations
            
        if self.test_duration_seconds > 0:
            self.operations_per_second = self.total_operations / self.test_duration_seconds


@dataclass
class BenchmarkResult:
    """Result of a complete benchmark run"""
    
    benchmark_name: str
    configuration: Dict[str, Any]
    metrics: PerformanceMetrics
    passed_thresholds: bool
    threshold_violations: List[str] = field(default_factory=list)
    additional_data: Dict[str, Any] = field(default_factory=dict)


class PerformanceDataGenerator:
    """Generates synthetic test data for performance testing"""
    
    def __init__(self, config: PerformanceTestConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_processor_result(
        self, 
        processor_type: ProcessorType = ProcessorType.TEXT_PROCESSOR,
        document_size_bytes: Optional[int] = None,
        embedding_dimension: Optional[int] = None
    ) -> ProcessorResult:
        """Generates a synthetic ProcessorResult for testing"""
        
        # Generate document size
        if document_size_bytes is None:
            import random
            document_size_bytes = random.randint(
                self.config.document_size_bytes_min,
                self.config.document_size_bytes_max
            )
        
        # Generate embedding dimension
        if embedding_dimension is None:
            import random
            embedding_dimension = random.choice(self.config.embedding_dimensions)
        
        # Generate synthetic content
        document_id = f"perf_test_{uuid.uuid4().hex[:8]}"
        
        # Generate text content
        text_content = self._generate_text_content(document_size_bytes)
        
        # Generate embedding
        import random
        embedding = [random.uniform(-1.0, 1.0) for _ in range(embedding_dimension)]
        
        # Build result data based on processor type
        result_data = {
            'text_content': text_content,
            'document_size_bytes': document_size_bytes,
            'embedding_dimension': embedding_dimension
        }
        
        if processor_type == ProcessorType.TEXT_PROCESSOR:
            result_data.update({
                'language': 'de',
                'text_statistics': {
                    'word_count': len(text_content.split()),
                    'character_count': len(text_content),
                    'paragraph_count': text_content.count('\n\n') + 1
                },
                'embedding': embedding
            })
        
        elif processor_type == ProcessorType.IMAGE_PROCESSOR:
            result_data.update({
                'dimensions': {'width': 1920, 'height': 1080},
                'format': 'JPEG',
                'visual_embedding': embedding,
                'exif_data': {
                    'camera': 'Test Camera',
                    'capture_time': datetime.now().isoformat()
                }
            })
        
        elif processor_type == ProcessorType.GEOSPATIAL_PROCESSOR:
            result_data.update({
                'coordinates': {
                    'latitude': random.uniform(47.0, 55.0),  # Germany area
                    'longitude': random.uniform(5.0, 15.0)
                },
                'spatial_embedding': embedding,
                'location_metadata': {
                    'accuracy_meters': random.uniform(1.0, 10.0),
                    'coordinate_system': 'WGS84'
                }
            })
        
        return ProcessorResult(
            processor_name=f"{processor_type.value}BenchmarkProcessor",
            processor_type=processor_type,
            document_id=document_id,
            result_data=result_data,
            confidence_score=random.uniform(0.7, 1.0),
            execution_time_ms=random.randint(50, 500),
            metadata={
                'file_path': f'/test/benchmark/{document_id}.txt',
                'mime_type': 'text/plain',
                'test_generated': True,
                'benchmark_timestamp': datetime.now().isoformat()
            }
        )
    
    def _generate_text_content(self, size_bytes: int) -> str:
        """Generates synthetic text content of specified size"""
        
        # Base text template
        template_words = [
            "performance", "test", "document", "content", "analysis", "processing",
            "system", "database", "distribution", "optimization", "benchmark",
            "validation", "testing", "implementation", "strategy", "configuration"
        ]
        
        import random
        
        content = []
        current_size = 0
        
        while current_size < size_bytes:
            # Add a sentence
            sentence_length = random.randint(5, 15)
            sentence_words = [random.choice(template_words) for _ in range(sentence_length)]
            sentence = " ".join(sentence_words) + ". "
            
            content.append(sentence)
            current_size += len(sentence.encode('utf-8'))
            
            # Occasionally add paragraph breaks
            if random.random() < 0.1:
                content.append("\n\n")
                current_size += 2
        
        result = "".join(content)
        
        # Trim to exact size if needed
        if len(result.encode('utf-8')) > size_bytes:
            result = result.encode('utf-8')[:size_bytes].decode('utf-8', errors='ignore')
        
        return result
    
    def generate_processor_batch(
        self, 
        batch_size: int,
        processor_types: Optional[List[ProcessorType]] = None
    ) -> List[ProcessorResult]:
        """Generates a batch of processor results for testing"""
        
        if processor_types is None:
            processor_types = [ProcessorType.TEXT_PROCESSOR]
        
        import random
        
        batch = []
        for _ in range(batch_size):
            processor_type = random.choice(processor_types)
            result = self.generate_processor_result(processor_type)
            batch.append(result)
        
        return batch


class PerformanceMonitor:
    """Monitors system performance during testing"""
    
    def __init__(self, config: PerformanceTestConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.metrics = PerformanceMetrics()
        self._start_time = time.time()
        
        # Resource monitoring
        self.process = psutil.Process()
    
    async def start_monitoring(self):
        """Starts performance monitoring"""
        
        self.monitoring_active = True
        self._start_time = time.time()
        self.metrics = PerformanceMetrics()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("📊 Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stops performance monitoring and calculates final metrics"""
        
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Calculate final metrics
        self.metrics.test_duration_seconds = time.time() - self._start_time
        self.metrics.calculate_derived_metrics()
        
        self.logger.info("🏁 Performance monitoring stopped")
        
        return self.metrics
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        
        try:
            while self.monitoring_active:
                # Sample memory usage
                try:
                    memory_info = self.process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    self.metrics.memory_usage_samples_mb.append(memory_mb)
                    
                    # Sample CPU usage
                    cpu_percent = self.process.cpu_percent()
                    self.metrics.cpu_usage_percent = cpu_percent
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process might have ended or we don't have access
                    pass
                
                await asyncio.sleep(self.config.memory_sampling_interval_seconds)
                
        except asyncio.CancelledError:
            pass
    
    def record_operation(
        self, 
        latency_ms: float, 
        success: bool, 
        error_type: Optional[str] = None
    ):
        """Records a single operation result"""
        
        self.metrics.total_operations += 1
        
        if success:
            self.metrics.successful_operations += 1
        else:
            self.metrics.failed_operations += 1
            
            if error_type:
                self.metrics.error_types[error_type] = self.metrics.error_types.get(error_type, 0) + 1
        
        self.metrics.latencies_ms.append(latency_ms)
    
    def record_timeout(self):
        """Records a timeout occurrence"""
        self.metrics.timeout_count += 1


class DistributorPerformanceTester:
    """Performance tester for UDS3 Multi-DB Distributors"""
    
    def __init__(self, config: PerformanceTestConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_generator = PerformanceDataGenerator(config)
    
    async def benchmark_basic_distributor(
        self, 
        strategy_type: StrategyType = StrategyType.FULL_POLYGLOT
    ) -> BenchmarkResult:
        """Benchmarks basic UDS3MultiDBDistributor"""
        
        self.logger.info(f"🎯 Benchmarking basic distributor with {strategy_type.value} strategy")
        
        # Create mock adaptive strategy
        adaptive_strategy = self._create_mock_adaptive_strategy(strategy_type)
        
        # Create distributor
        distributor = await create_uds3_distributor(
            adaptive_strategy=adaptive_strategy,
            config={'batch_size': 50}
        )
        
        return await self._run_distributor_benchmark(
            distributor=distributor,
            benchmark_name=f"basic_distributor_{strategy_type.value}",
            configuration={'strategy': strategy_type.value, 'distributor_type': 'basic'}
        )
    
    async def benchmark_enhanced_distributor(
        self, 
        strategy_type: StrategyType = StrategyType.FULL_POLYGLOT
    ) -> BenchmarkResult:
        """Benchmarks UDS3EnhancedMultiDBDistributor with processor-specific optimizations"""
        
        self.logger.info(f"🔧 Benchmarking enhanced distributor with {strategy_type.value} strategy")
        
        adaptive_strategy = self._create_mock_adaptive_strategy(strategy_type)
        
        distributor = await create_enhanced_uds3_distributor(
            adaptive_strategy=adaptive_strategy,
            config={'enable_processor_optimization': True, 'batch_size': 50}
        )
        
        return await self._run_distributor_benchmark(
            distributor=distributor,
            benchmark_name=f"enhanced_distributor_{strategy_type.value}",
            configuration={'strategy': strategy_type.value, 'distributor_type': 'enhanced'}
        )
    
    async def benchmark_saga_distributor(
        self, 
        strategy_type: StrategyType = StrategyType.FULL_POLYGLOT
    ) -> BenchmarkResult:
        """Benchmarks SAGAIntegratedMultiDBDistributor with transactional guarantees"""
        
        self.logger.info(f"🔄 Benchmarking SAGA distributor with {strategy_type.value} strategy")
        
        adaptive_strategy = self._create_mock_adaptive_strategy(strategy_type)
        
        distributor = await create_saga_integrated_distributor(
            adaptive_strategy=adaptive_strategy,
            config={
                'enable_saga_transactions': True,
                'saga_config': {
                    'max_concurrent_transactions': 25,
                    'default_transaction_timeout': 30.0
                }
            }
        )
        
        return await self._run_distributor_benchmark(
            distributor=distributor,
            benchmark_name=f"saga_distributor_{strategy_type.value}",
            configuration={'strategy': strategy_type.value, 'distributor_type': 'saga'}
        )
    
    async def _run_distributor_benchmark(
        self,
        distributor: UDS3MultiDBDistributor,
        benchmark_name: str,
        configuration: Dict[str, Any]
    ) -> BenchmarkResult:
        """Runs a comprehensive benchmark on a distributor"""
        
        monitor = PerformanceMonitor(self.config)
        await monitor.start_monitoring()
        
        try:
            # Generate test data
            test_data = self.data_generator.generate_processor_batch(
                batch_size=500,  # Large batch for testing
                processor_types=[
                    ProcessorType.TEXT_PROCESSOR,
                    ProcessorType.IMAGE_PROCESSOR,
                    ProcessorType.GEOSPATIAL_PROCESSOR
                ]
            )
            
            # Run throughput test
            await self._run_throughput_test(distributor, test_data[:100], monitor)
            
            # Run latency test
            await self._run_latency_test(distributor, test_data[100:200], monitor)
            
            # Run batch processing test
            await self._run_batch_test(distributor, test_data[200:400], monitor)
            
            # Run stress test
            await self._run_stress_test(distributor, test_data[400:], monitor)
            
        finally:
            metrics = await monitor.stop_monitoring()
        
        # Check performance thresholds
        passed_thresholds, violations = self._check_performance_thresholds(metrics)
        
        return BenchmarkResult(
            benchmark_name=benchmark_name,
            configuration=configuration,
            metrics=metrics,
            passed_thresholds=passed_thresholds,
            threshold_violations=violations,
            additional_data={
                'distributor_stats': distributor.get_distribution_stats() if hasattr(distributor, 'get_distribution_stats') else {}
            }
        )
    
    async def _run_throughput_test(
        self,
        distributor: UDS3MultiDBDistributor,
        test_data: List[ProcessorResult],
        monitor: PerformanceMonitor
    ):
        """Tests maximum throughput of the distributor"""
        
        self.logger.info("📈 Running throughput test...")
        
        # Process all items as quickly as possible
        tasks = []
        for processor_result in test_data:
            task = asyncio.create_task(self._timed_distribution(distributor, processor_result, monitor))
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_latency_test(
        self,
        distributor: UDS3MultiDBDistributor,
        test_data: List[ProcessorResult],
        monitor: PerformanceMonitor
    ):
        """Tests latency characteristics under normal load"""
        
        self.logger.info("⏱️ Running latency test...")
        
        # Process items one by one to measure individual latencies
        for processor_result in test_data:
            await self._timed_distribution(distributor, processor_result, monitor)
            
            # Small delay between operations to simulate normal load
            await asyncio.sleep(0.01)
    
    async def _run_batch_test(
        self,
        distributor: UDS3MultiDBDistributor,
        test_data: List[ProcessorResult],
        monitor: PerformanceMonitor
    ):
        """Tests batch processing capabilities"""
        
        self.logger.info("📦 Running batch processing test...")
        
        # Test different batch sizes
        for batch_size in self.config.batch_sizes:
            batch_start_idx = 0
            
            while batch_start_idx < len(test_data):
                batch_end_idx = min(batch_start_idx + batch_size, len(test_data))
                batch = test_data[batch_start_idx:batch_end_idx]
                
                # Process batch
                if hasattr(distributor, 'distribute_multiple_results'):
                    # Use batch processing if available
                    start_time = time.time()
                    try:
                        results = await distributor.distribute_multiple_results(batch)
                        latency_ms = (time.time() - start_time) * 1000
                        
                        # Record each result
                        for result in results:
                            monitor.record_operation(
                                latency_ms / len(results),  # Approximate per-item latency
                                result.success,
                                'batch_processing_error' if not result.success else None
                            )
                            
                    except Exception as e:
                        latency_ms = (time.time() - start_time) * 1000
                        for _ in batch:
                            monitor.record_operation(
                                latency_ms / len(batch),
                                False,
                                f'batch_error_{type(e).__name__}'
                            )
                else:
                    # Process individually
                    for processor_result in batch:
                        await self._timed_distribution(distributor, processor_result, monitor)
                
                batch_start_idx = batch_end_idx
    
    async def _run_stress_test(
        self,
        distributor: UDS3MultiDBDistributor,
        test_data: List[ProcessorResult],
        monitor: PerformanceMonitor
    ):
        """Tests distributor under stress conditions"""
        
        self.logger.info("🔥 Running stress test...")
        
        # Create high concurrent load
        max_concurrent = int(self.config.max_concurrent_operations * self.config.stress_test_multiplier)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def stress_operation(processor_result):
            async with semaphore:
                return await self._timed_distribution(distributor, processor_result, monitor)
        
        # Launch all operations concurrently
        tasks = [stress_operation(result) for result in test_data]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _timed_distribution(
        self,
        distributor: UDS3MultiDBDistributor,
        processor_result: ProcessorResult,
        monitor: PerformanceMonitor
    ) -> Optional[DistributionResult]:
        """Times a single distribution operation"""
        
        start_time = time.time()
        
        try:
            result = await distributor.distribute_processor_result(processor_result)
            latency_ms = (time.time() - start_time) * 1000
            
            monitor.record_operation(
                latency_ms,
                result.success,
                'distribution_error' if not result.success else None
            )
            
            return result
            
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            monitor.record_operation(latency_ms, False, 'timeout_error')
            monitor.record_timeout()
            return None
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            monitor.record_operation(latency_ms, False, f'{type(e).__name__}')
            return None
    
    def _create_mock_adaptive_strategy(self, strategy_type: StrategyType) -> AdaptiveMultiDBStrategy:
        """Creates a mock adaptive strategy for testing"""
        
        # Define database availability based on strategy type
        if strategy_type == StrategyType.FULL_POLYGLOT:
            db_availability = DatabaseAvailability(
                postgresql=True, couchdb=True, chromadb=True, neo4j=True, sqlite=True
            )
        elif strategy_type == StrategyType.TRI_DATABASE:
            db_availability = DatabaseAvailability(
                postgresql=True, couchdb=True, chromadb=True, neo4j=False, sqlite=True
            )
        elif strategy_type == StrategyType.DUAL_DATABASE:
            db_availability = DatabaseAvailability(
                postgresql=True, couchdb=True, chromadb=False, neo4j=False, sqlite=True
            )
        elif strategy_type == StrategyType.POSTGRESQL_ENHANCED:
            db_availability = DatabaseAvailability(
                postgresql=True, couchdb=False, chromadb=False, neo4j=False, sqlite=True
            )
        else:  # SQLITE_MONOLITH
            db_availability = DatabaseAvailability(
                postgresql=False, couchdb=False, chromadb=False, neo4j=False, sqlite=True
            )
        
        # Create mock strategy
        class MockAdaptiveStrategy:
            def __init__(self):
                self.current_strategy = strategy_type
                self.db_availability = db_availability
        
        return MockAdaptiveStrategy()
    
    def _check_performance_thresholds(
        self, 
        metrics: PerformanceMetrics
    ) -> Tuple[bool, List[str]]:
        """Checks if performance metrics meet defined thresholds"""
        
        violations = []
        
        # Check latency threshold
        if metrics.p95_latency_ms > self.config.max_acceptable_latency_ms:
            violations.append(
                f"P95 latency ({metrics.p95_latency_ms:.1f}ms) exceeds threshold "
                f"({self.config.max_acceptable_latency_ms}ms)"
            )
        
        # Check throughput threshold
        if metrics.operations_per_second < self.config.min_acceptable_throughput_ops_per_second:
            violations.append(
                f"Throughput ({metrics.operations_per_second:.1f} ops/s) below threshold "
                f"({self.config.min_acceptable_throughput_ops_per_second} ops/s)"
            )
        
        # Check memory threshold
        if metrics.peak_memory_mb > self.config.max_acceptable_memory_mb:
            violations.append(
                f"Peak memory ({metrics.peak_memory_mb:.1f}MB) exceeds threshold "
                f"({self.config.max_acceptable_memory_mb}MB)"
            )
        
        # Check error rate threshold
        error_rate = metrics.failed_operations / max(metrics.total_operations, 1)
        if error_rate > self.config.max_acceptable_error_rate:
            violations.append(
                f"Error rate ({error_rate:.3f}) exceeds threshold "
                f"({self.config.max_acceptable_error_rate:.3f})"
            )
        
        return len(violations) == 0, violations


class PerformanceReportGenerator:
    """Generates comprehensive performance reports"""
    
    def __init__(self, config: PerformanceTestConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_report(
        self, 
        benchmark_results: List[BenchmarkResult],
        output_path: Path = None
    ) -> str:
        """Generates a comprehensive performance report"""
        
        if output_path is None:
            output_path = Path(f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        
        # Generate HTML report
        html_content = self._generate_html_report(benchmark_results)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Generate CSV data
        csv_path = output_path.with_suffix('.csv')
        self._generate_csv_report(benchmark_results, csv_path)
        
        self.logger.info(f"📊 Performance report generated: {output_path}")
        
        return str(output_path)
    
    def _generate_html_report(self, results: List[BenchmarkResult]) -> str:
        """Generates HTML performance report"""
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>UDS3 Multi-DB Distribution Performance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .benchmark { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .passed { border-left: 5px solid #28a745; }
        .failed { border-left: 5px solid #dc3545; }
        .metrics-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        .metrics-table th, .metrics-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .metrics-table th { background-color: #f8f9fa; }
        .violation { color: #dc3545; font-weight: bold; }
        .summary { background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
"""
        
        # Header
        html += f"""
    <div class="header">
        <h1>🚀 UDS3 Multi-DB Distribution Performance Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Benchmarks:</strong> {len(results)}</p>
        <p><strong>Passed Benchmarks:</strong> {sum(1 for r in results if r.passed_thresholds)}</p>
        <p><strong>Failed Benchmarks:</strong> {sum(1 for r in results if not r.passed_thresholds)}</p>
    </div>
"""
        
        # Summary statistics
        if results:
            html += self._generate_summary_section(results)
        
        # Individual benchmark results
        html += "<h2>📈 Benchmark Results</h2>"
        
        for result in results:
            status_class = "passed" if result.passed_thresholds else "failed"
            status_icon = "✅" if result.passed_thresholds else "❌"
            
            html += f"""
    <div class="benchmark {status_class}">
        <h3>{status_icon} {result.benchmark_name}</h3>
        <p><strong>Configuration:</strong> {json.dumps(result.configuration, indent=2)}</p>
"""
            
            # Metrics table
            metrics = result.metrics
            html += """
        <table class="metrics-table">
            <tr><th>Metric</th><th>Value</th></tr>
"""
            
            metrics_data = [
                ("Total Operations", f"{metrics.total_operations:,}"),
                ("Success Rate", f"{metrics.distribution_success_rate:.1%}"),
                ("Throughput (ops/s)", f"{metrics.operations_per_second:.1f}"),
                ("Avg Latency (ms)", f"{metrics.avg_latency_ms:.1f}"),
                ("P95 Latency (ms)", f"{metrics.p95_latency_ms:.1f}"),
                ("P99 Latency (ms)", f"{metrics.p99_latency_ms:.1f}"),
                ("Peak Memory (MB)", f"{metrics.peak_memory_mb:.1f}"),
                ("Test Duration (s)", f"{metrics.test_duration_seconds:.1f}"),
            ]
            
            for metric_name, metric_value in metrics_data:
                html += f"<tr><td>{metric_name}</td><td>{metric_value}</td></tr>"
            
            html += "</table>"
            
            # Threshold violations
            if result.threshold_violations:
                html += "<h4 class='violation'>⚠️ Threshold Violations:</h4><ul>"
                for violation in result.threshold_violations:
                    html += f"<li class='violation'>{violation}</li>"
                html += "</ul>"
            
            html += "</div>"
        
        html += """
</body>
</html>
"""
        
        return html
    
    def _generate_summary_section(self, results: List[BenchmarkResult]) -> str:
        """Generates summary statistics section"""
        
        # Calculate aggregate metrics
        all_throughputs = [r.metrics.operations_per_second for r in results]
        all_latencies = [r.metrics.p95_latency_ms for r in results]
        all_memory = [r.metrics.peak_memory_mb for r in results]
        
        html = f"""
    <div class="summary">
        <h2>📊 Summary Statistics</h2>
        <table class="metrics-table">
            <tr><th>Metric</th><th>Min</th><th>Avg</th><th>Max</th></tr>
            <tr>
                <td>Throughput (ops/s)</td>
                <td>{min(all_throughputs):.1f}</td>
                <td>{statistics.mean(all_throughputs):.1f}</td>
                <td>{max(all_throughputs):.1f}</td>
            </tr>
            <tr>
                <td>P95 Latency (ms)</td>
                <td>{min(all_latencies):.1f}</td>
                <td>{statistics.mean(all_latencies):.1f}</td>
                <td>{max(all_latencies):.1f}</td>
            </tr>
            <tr>
                <td>Peak Memory (MB)</td>
                <td>{min(all_memory):.1f}</td>
                <td>{statistics.mean(all_memory):.1f}</td>
                <td>{max(all_memory):.1f}</td>
            </tr>
        </table>
    </div>
"""
        
        return html
    
    def _generate_csv_report(self, results: List[BenchmarkResult], csv_path: Path):
        """Generates CSV performance data"""
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow([
                'Benchmark Name', 'Strategy', 'Distributor Type', 'Passed Thresholds',
                'Total Operations', 'Success Rate', 'Throughput (ops/s)',
                'Avg Latency (ms)', 'P95 Latency (ms)', 'P99 Latency (ms)',
                'Peak Memory (MB)', 'Test Duration (s)', 'Violations'
            ])
            
            # Data rows
            for result in results:
                writer.writerow([
                    result.benchmark_name,
                    result.configuration.get('strategy', 'unknown'),
                    result.configuration.get('distributor_type', 'unknown'),
                    result.passed_thresholds,
                    result.metrics.total_operations,
                    result.metrics.distribution_success_rate,
                    result.metrics.operations_per_second,
                    result.metrics.avg_latency_ms,
                    result.metrics.p95_latency_ms,
                    result.metrics.p99_latency_ms,
                    result.metrics.peak_memory_mb,
                    result.metrics.test_duration_seconds,
                    '; '.join(result.threshold_violations)
                ])


class UDS3PerformanceTestSuite:
    """Comprehensive performance test suite for UDS3 Multi-DB Distribution"""
    
    def __init__(self, config: PerformanceTestConfig = None):
        self.config = config or PerformanceTestConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tester = DistributorPerformanceTester(self.config)
        self.reporter = PerformanceReportGenerator(self.config)
    
    async def run_comprehensive_tests(self) -> List[BenchmarkResult]:
        """Runs comprehensive performance tests across all configurations"""
        
        self.logger.info("🚀 Starting UDS3 Multi-DB Distribution performance test suite")
        
        results = []
        
        # Test all strategy types with different distributor types
        for strategy_type in self.config.test_strategies:
            self.logger.info(f"Testing strategy: {strategy_type.value}")
            
            try:
                # Test basic distributor
                basic_result = await self.tester.benchmark_basic_distributor(strategy_type)
                results.append(basic_result)
                
                # Test enhanced distributor
                enhanced_result = await self.tester.benchmark_enhanced_distributor(strategy_type)
                results.append(enhanced_result)
                
                # Test SAGA distributor (only for multi-database strategies)
                if strategy_type in [StrategyType.FULL_POLYGLOT, StrategyType.TRI_DATABASE, StrategyType.DUAL_DATABASE]:
                    saga_result = await self.tester.benchmark_saga_distributor(strategy_type)
                    results.append(saga_result)
                
                # Cleanup between tests
                gc.collect()
                await asyncio.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Test failed for strategy {strategy_type.value}: {e}")
                continue
        
        self.logger.info(f"✅ Completed {len(results)} performance benchmarks")
        
        return results
    
    async def run_quick_tests(self) -> List[BenchmarkResult]:
        """Runs a quick subset of performance tests"""
        
        self.logger.info("⚡ Running quick performance tests")
        
        # Reduce test scope for quick testing
        quick_config = PerformanceTestConfig(
            test_duration_seconds=20.0,
            max_concurrent_operations=25,
            batch_sizes=[10, 50]
        )
        quick_tester = DistributorPerformanceTester(quick_config)
        
        results = []
        
        # Test key configurations only
        test_strategies = [StrategyType.FULL_POLYGLOT, StrategyType.SQLITE_MONOLITH]
        
        for strategy_type in test_strategies:
            try:
                # Test enhanced distributor only
                result = await quick_tester.benchmark_enhanced_distributor(strategy_type)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Quick test failed for {strategy_type.value}: {e}")
                continue
        
        self.logger.info(f"✅ Completed {len(results)} quick benchmarks")
        
        return results
    
    def generate_performance_report(
        self, 
        results: List[BenchmarkResult],
        output_directory: Path = None
    ) -> str:
        """Generates comprehensive performance report"""
        
        if output_directory is None:
            output_directory = Path('./performance_reports')
        
        output_directory.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = output_directory / f"uds3_performance_report_{timestamp}.html"
        
        return self.reporter.generate_report(results, report_path)


# Main execution functions
async def run_full_performance_suite():
    """Runs the complete UDS3 performance test suite"""
    
    if not UDS3_TEST_COMPONENTS_AVAILABLE:
        print("❌ UDS3 test components not available")
        return
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure comprehensive testing
    config = PerformanceTestConfig(
        test_duration_seconds=120.0,
        max_concurrent_operations=100,
        target_throughput_ops_per_second=200.0,
        batch_sizes=[1, 10, 50, 100, 200],
        max_acceptable_latency_ms=500.0,
        min_acceptable_throughput_ops_per_second=50.0
    )
    
    suite = UDS3PerformanceTestSuite(config)
    
    # Run comprehensive tests
    results = await suite.run_comprehensive_tests()
    
    # Generate report
    report_path = suite.generate_performance_report(results)
    
    print(f"\n🎉 Performance testing complete!")
    print(f"📊 Report generated: {report_path}")
    print(f"🔍 Benchmarks completed: {len(results)}")
    print(f"✅ Passed benchmarks: {sum(1 for r in results if r.passed_thresholds)}")
    print(f"❌ Failed benchmarks: {sum(1 for r in results if not r.passed_thresholds)}")


async def run_quick_performance_check():
    """Runs a quick performance validation"""
    
    if not UDS3_TEST_COMPONENTS_AVAILABLE:
        print("❌ UDS3 test components not available")
        return
    
    logging.basicConfig(level=logging.INFO)
    
    suite = UDS3PerformanceTestSuite()
    results = await suite.run_quick_tests()
    
    print(f"\n⚡ Quick performance check complete!")
    print(f"🔍 Benchmarks: {len(results)}")
    
    for result in results:
        status = "✅ PASS" if result.passed_thresholds else "❌ FAIL"
        print(f"{status} {result.benchmark_name}: {result.metrics.operations_per_second:.1f} ops/s")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(run_quick_performance_check())
    else:
        asyncio.run(run_full_performance_suite())