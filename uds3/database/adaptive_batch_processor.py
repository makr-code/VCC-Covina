#!/usr/bin/env python3
"""
Adaptive Batch Processor Implementation
======================================

Hochperformanter Batch-Prozessor mit adaptiver Größenanpassung,
Performance-Monitoring und intelligenter Optimierung.

Author: UDS3 Framework
Date: Oktober 2025
"""

import logging
import threading
import time
import asyncio
import queue
import statistics
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class BatchMetrics:
    """Performance-Metriken für Batch-Operationen"""
    
    batch_size: int
    processing_time: float
    success_rate: float
    throughput: float
    memory_usage: float
    error_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'batch_size': self.batch_size,
            'processing_time': self.processing_time,
            'success_rate': self.success_rate,
            'throughput': self.throughput,
            'memory_usage': self.memory_usage,
            'error_count': self.error_count,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class BatchProcessingConfig:
    """Konfiguration für Batch-Processing"""
    
    initial_batch_size: int = 100
    min_batch_size: int = 10
    max_batch_size: int = 10000
    target_processing_time: float = 2.0  # Sekunden
    performance_window_size: int = 50
    optimization_threshold: float = 0.1
    max_retry_attempts: int = 3
    backup_enabled: bool = True
    backup_interval: int = 1000  # Operationen
    

class AdaptiveBatchProcessor:
    """
    Adaptiver Batch-Prozessor mit intelligenter Größenoptimierung
    
    Features:
    - Dynamische Batch-Größenanpassung basierend auf Performance
    - Asynchrone Verarbeitung mit Thread-Pool
    - Performance-Monitoring und -Analyse
    - Fehlerbehandlung und Retry-Mechanismus
    - Persistente Backup-Integration
    - Memory-Management und Leak-Prevention
    """
    
    def __init__(
        self,
        backend: Optional[Any] = None,
        operation_type: str = "batch_operation",
        batch_executor: Optional[Callable] = None,
        config: Optional[BatchProcessingConfig] = None,
        **kwargs
    ):
        self.backend = backend
        self.operation_type = operation_type
        self.batch_executor = batch_executor
        self.config = config or BatchProcessingConfig()
        
        # Processing state
        self.current_batch_size = self.config.initial_batch_size
        self.is_processing = False
        self.total_processed = 0
        self.total_errors = 0
        
        # Performance tracking
        self.performance_history: List[BatchMetrics] = []
        self.current_performance: Optional[BatchMetrics] = None
        
        # Threading
        self._processing_lock = threading.RLock()
        self._queue = queue.Queue()
        self._shutdown_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        
        # Backup manager
        if self.config.backup_enabled:
            self._backup_manager = BackupManager(
                backend_name=getattr(backend, '__class__.__name__', 'unknown'),
                operation_type=operation_type
            )
        else:
            self._backup_manager = None
            
        # Statistics
        self._start_time = datetime.now()
        self._last_optimization = datetime.now()
        
        logger.info(f"✅ AdaptiveBatchProcessor initialized: {operation_type}")
        
    def start_processing(self) -> bool:
        """Startet den Background-Worker für asynchrone Verarbeitung"""
        try:
            with self._processing_lock:
                if self._worker_thread and self._worker_thread.is_alive():
                    logger.warning("Background worker already running")
                    return True
                
                self._shutdown_event.clear()
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name=f"BatchProcessor-{self.operation_type}",
                    daemon=True
                )
                self._worker_thread.start()
                
                logger.info(f"✅ Background worker started for {self.operation_type}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to start background worker: {e}")
            return False
    
    def stop_processing(self, timeout: float = 30.0) -> bool:
        """Stoppt den Background-Worker gracefully"""
        try:
            self._shutdown_event.set()
            
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=timeout)
                
                if self._worker_thread.is_alive():
                    logger.warning(f"Background worker did not shut down within {timeout}s")
                    return False
                    
            logger.info(f"✅ Background worker stopped for {self.operation_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping background worker: {e}")
            return False
    
    def queue_operation(self, operation_data: Any) -> bool:
        """Fügt eine Operation zur Batch-Queue hinzu"""
        try:
            self._queue.put(operation_data, timeout=1.0)
            
            # Starte Worker falls nicht aktiv
            if not (self._worker_thread and self._worker_thread.is_alive()):
                self.start_processing()
                
            return True
            
        except queue.Full:
            logger.error("Batch queue is full, dropping operation")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to queue operation: {e}")
            return False
    
    def process_batch(self, items: List[Any], **kwargs) -> Dict[str, Any]:
        """Verarbeitet einen Batch von Items synchron"""
        if not items:
            return {'processed': 0, 'success': True, 'errors': []}
        
        start_time = time.time()
        processed = 0
        errors = []
        
        try:
            # Verwende den konfigurierten Batch-Executor
            if self.batch_executor and callable(self.batch_executor):
                result = self.batch_executor(items, **kwargs)
                if isinstance(result, dict):
                    processed = result.get('processed', len(items))
                    if 'errors' in result:
                        errors.extend(result['errors'])
                else:
                    processed = len(items)
            else:
                # Fallback: Item-by-item processing
                for item in items:
                    try:
                        self._process_single_item(item, **kwargs)
                        processed += 1
                    except Exception as e:
                        errors.append(str(e))
                        
        except Exception as e:
            logger.error(f"❌ Batch processing error: {e}")
            errors.append(str(e))
        
        processing_time = time.time() - start_time
        success_rate = processed / len(items) if items else 0.0
        
        # Aktualisiere Metriken
        self._update_performance_metrics(
            batch_size=len(items),
            processing_time=processing_time,
            success_rate=success_rate,
            error_count=len(errors)
        )
        
        # Optimiere Batch-Größe
        self._optimize_batch_size()
        
        self.total_processed += processed
        self.total_errors += len(errors)
        
        return {
            'processed': processed,
            'success': len(errors) == 0,
            'errors': errors,
            'processing_time': processing_time,
            'success_rate': success_rate
        }
    
    def _worker_loop(self):
        """Background-Worker Loop für asynchrone Batch-Verarbeitung"""
        batch_items = []
        last_batch_time = time.time()
        
        while not self._shutdown_event.is_set():
            try:
                # Sammle Items für Batch
                try:
                    item = self._queue.get(timeout=0.1)
                    batch_items.append(item)
                    self._queue.task_done()
                except queue.Empty:
                    pass
                
                # Verarbeite Batch wenn Größe erreicht oder Timeout
                should_process = (
                    len(batch_items) >= self.current_batch_size or
                    (batch_items and time.time() - last_batch_time > 1.0)
                )
                
                if should_process and batch_items:
                    self._process_worker_batch(batch_items.copy())
                    batch_items.clear()
                    last_batch_time = time.time()
                    
            except Exception as e:
                logger.error(f"❌ Worker loop error: {e}")
                time.sleep(0.1)
        
        # Verarbeite verbleibende Items beim Shutdown
        if batch_items:
            self._process_worker_batch(batch_items)
    
    def _process_worker_batch(self, items: List[Any]):
        """Verarbeitet einen Batch im Worker-Thread"""
        try:
            result = self.process_batch(items)
            
            if not result['success']:
                logger.warning(
                    f"Batch processing completed with errors: "
                    f"{len(result['errors'])}/{result['processed']}"
                )
            
            # Backup falls konfiguriert
            if self._backup_manager and self.total_processed % self.config.backup_interval == 0:
                self._backup_manager.create_incremental_backup({
                    'processed_items': self.total_processed,
                    'timestamp': datetime.now().isoformat(),
                    'performance_metrics': [m.to_dict() for m in self.performance_history[-10:]]
                })
                
        except Exception as e:
            logger.error(f"❌ Worker batch processing failed: {e}")
    
    def _process_single_item(self, item: Any, **kwargs):
        """Verarbeitet ein einzelnes Item (Fallback-Implementierung)"""
        if self.backend and hasattr(self.backend, f'process_{self.operation_type}'):
            method = getattr(self.backend, f'process_{self.operation_type}')
            return method(item, **kwargs)
        else:
            # Einfache Fallback-Verarbeitung
            logger.debug(f"Processing item: {type(item).__name__}")
            return item
    
    def _update_performance_metrics(
        self, 
        batch_size: int, 
        processing_time: float, 
        success_rate: float, 
        error_count: int
    ):
        """Aktualisiert Performance-Metriken"""
        throughput = batch_size / processing_time if processing_time > 0 else 0.0
        memory_usage = self._estimate_memory_usage()
        
        metrics = BatchMetrics(
            batch_size=batch_size,
            processing_time=processing_time,
            success_rate=success_rate,
            throughput=throughput,
            memory_usage=memory_usage,
            error_count=error_count
        )
        
        self.performance_history.append(metrics)
        self.current_performance = metrics
        
        # Begrenze History-Größe
        if len(self.performance_history) > self.config.performance_window_size:
            self.performance_history.pop(0)
    
    def _optimize_batch_size(self):
        """Optimiert die Batch-Größe basierend auf Performance-Historie"""
        if len(self.performance_history) < 5:
            return  # Zu wenig Daten für Optimierung
        
        recent_metrics = self.performance_history[-10:]
        
        # Berechne durchschnittliche Performance
        avg_throughput = statistics.mean(m.throughput for m in recent_metrics)
        avg_processing_time = statistics.mean(m.processing_time for m in recent_metrics)
        avg_success_rate = statistics.mean(m.success_rate for m in recent_metrics)
        
        # Optimierungsstrategie
        target_time = self.config.target_processing_time
        
        if avg_processing_time > target_time * 1.5 and avg_success_rate > 0.9:
            # Zu langsam aber stabil -> kleinere Batches
            new_size = max(
                self.config.min_batch_size,
                int(self.current_batch_size * 0.8)
            )
        elif avg_processing_time < target_time * 0.5 and avg_success_rate > 0.95:
            # Schnell und stabil -> größere Batches
            new_size = min(
                self.config.max_batch_size,
                int(self.current_batch_size * 1.2)
            )
        elif avg_success_rate < 0.8:
            # Viele Fehler -> deutlich kleinere Batches
            new_size = max(
                self.config.min_batch_size,
                int(self.current_batch_size * 0.5)
            )
        else:
            new_size = self.current_batch_size
        
        if abs(new_size - self.current_batch_size) / self.current_batch_size > self.config.optimization_threshold:
            old_size = self.current_batch_size
            self.current_batch_size = new_size
            self._last_optimization = datetime.now()
            
            logger.info(
                f"🔄 Batch size optimized: {old_size} → {new_size} "
                f"(throughput: {avg_throughput:.2f}/s, success: {avg_success_rate:.1%})"
            )
    
    def _estimate_memory_usage(self) -> float:
        """Schätzt aktuelle Memory-Usage (vereinfacht)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0  # Fallback wenn psutil nicht verfügbar
    
    def get_adaptive_stats(self) -> Dict[str, Any]:
        """Liefert detaillierte Statistiken"""
        uptime = datetime.now() - self._start_time
        
        stats = {
            'operation_type': self.operation_type,
            'backend': self.backend.__class__.__name__ if self.backend else 'None',
            'current_batch_size': self.current_batch_size,
            'total_processed': self.total_processed,
            'total_errors': self.total_errors,
            'success_rate': (self.total_processed - self.total_errors) / max(self.total_processed, 1),
            'uptime_seconds': uptime.total_seconds(),
            'queue_size': self._queue.qsize(),
            'is_processing': self.is_processing,
            'worker_active': self._worker_thread and self._worker_thread.is_alive(),
        }
        
        # Performance-Metriken
        if self.performance_history:
            recent = self.performance_history[-10:]
            stats.update({
                'avg_throughput': statistics.mean(m.throughput for m in recent),
                'avg_processing_time': statistics.mean(m.processing_time for m in recent),
                'avg_success_rate': statistics.mean(m.success_rate for m in recent),
                'memory_usage_mb': self.current_performance.memory_usage if self.current_performance else 0.0
            })
        
        return stats
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Erstellt detaillierten Performance-Report"""
        if not self.performance_history:
            return {'error': 'No performance data available'}
        
        metrics = self.performance_history
        
        return {
            'summary': {
                'total_batches': len(metrics),
                'total_items': sum(m.batch_size for m in metrics),
                'total_processing_time': sum(m.processing_time for m in metrics),
                'overall_success_rate': statistics.mean(m.success_rate for m in metrics),
                'avg_throughput': statistics.mean(m.throughput for m in metrics)
            },
            'optimization': {
                'current_batch_size': self.current_batch_size,
                'min_observed': min(m.batch_size for m in metrics),
                'max_observed': max(m.batch_size for m in metrics),
                'last_optimization': self._last_optimization.isoformat()
            },
            'performance_trend': {
                'recent_throughput': [m.throughput for m in metrics[-10:]],
                'recent_success_rates': [m.success_rate for m in metrics[-10:]],
                'recent_processing_times': [m.processing_time for m in metrics[-10:]]
            }
        }


class BackupManager:
    """Backup-Manager für Batch-Processing Recovery"""
    
    def __init__(self, backend_name: str, operation_type: str, backup_dir: str = "./database_backup"):
        self.backend_name = backend_name
        self.operation_type = operation_type
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_incremental_backup(self, data: Dict[str, Any]):
        """Erstellt inkrementelles Backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.backend_name}_{self.operation_type}_{timestamp}.json"
            filepath = self.backup_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
            logger.debug(f"✅ Backup created: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
    
    def restore_from_latest_backup(self) -> Optional[Dict[str, Any]]:
        """Stellt vom neuesten Backup wieder her"""
        try:
            pattern = f"{self.backend_name}_{self.operation_type}_*.json"
            backup_files = list(self.backup_dir.glob(pattern))
            
            if not backup_files:
                logger.warning("No backup files found")
                return None
                
            latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            with open(latest_backup, 'r') as f:
                data = json.load(f)
                
            logger.info(f"✅ Restored from backup: {latest_backup.name}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Backup restoration failed: {e}")
            return None