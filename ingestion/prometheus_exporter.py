"""
Prometheus Exporter for Production Hardening Metrics

Exposes production hardening metrics (worker pool, memory, circuit breakers)
in Prometheus format for monitoring and alerting.

Author: Covina System
Date: 28. Oktober 2025
Version: 1.0.0
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """
    Prometheus Metrics Exporter for Production Hardening
    
    Converts production hardening metrics into Prometheus exposition format.
    Supports gauges, counters, and metadata labels.
    
    Features:
    - Worker pool metrics (tasks, success rates, active workers)
    - Memory metrics (usage, limits, GC stats)
    - Circuit breaker metrics (states, calls, failures)
    - Auto-generated HELP and TYPE comments
    - Label support for dimensional metrics
    
    Usage:
        exporter = PrometheusMetrics()
        prometheus_text = exporter.export_metrics(hardening_metrics)
    """
    
    def __init__(self, namespace: str = "covina"):
        """
        Initialize Prometheus exporter
        
        Args:
            namespace: Metric namespace prefix (default: "covina")
        """
        self.namespace = namespace
        self.metrics: list[str] = []
    
    def _sanitize_label_value(self, value: str) -> str:
        """Sanitize label value for Prometheus format"""
        return str(value).replace('"', '\\"').replace('\n', '\\n')
    
    def _add_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None,
                   help_text: str = "", metric_type: str = "gauge"):
        """
        Add a metric to the export buffer
        
        Args:
            name: Metric name (will be prefixed with namespace)
            value: Metric value
            labels: Optional metric labels
            help_text: Metric description
            metric_type: Metric type (gauge, counter, histogram, summary)
        """
        full_name = f"{self.namespace}_{name}"
        
        # Add HELP comment (only once per metric name)
        if help_text and not any(f"# HELP {full_name}" in m for m in self.metrics):
            self.metrics.append(f"# HELP {full_name} {help_text}")
            self.metrics.append(f"# TYPE {full_name} {metric_type}")
        
        # Format labels
        if labels:
            label_str = ",".join([f'{k}="{self._sanitize_label_value(v)}"' for k, v in labels.items()])
            metric_line = f'{full_name}{{{label_str}}} {value}'
        else:
            metric_line = f'{full_name} {value}'
        
        self.metrics.append(metric_line)
    
    def export_worker_pool_metrics(self, worker_pool_data: Dict[str, Any]):
        """Export worker pool metrics"""
        if "error" in worker_pool_data:
            logger.warning(f"Worker pool metrics not available: {worker_pool_data['error']}")
            return
        
        # I/O Workers
        io_workers = worker_pool_data.get("io_workers", {})
        self._add_metric(
            "worker_pool_workers_total",
            io_workers.get("total", 0),
            labels={"type": "io"},
            help_text="Total number of worker threads/processes",
            metric_type="gauge"
        )
        self._add_metric(
            "worker_pool_workers_active",
            io_workers.get("active", 0),
            labels={"type": "io"},
            help_text="Currently active workers",
            metric_type="gauge"
        )
        self._add_metric(
            "worker_pool_tasks_completed_total",
            io_workers.get("tasks_completed", 0),
            labels={"type": "io"},
            help_text="Total tasks completed",
            metric_type="counter"
        )
        self._add_metric(
            "worker_pool_tasks_failed_total",
            io_workers.get("tasks_failed", 0),
            labels={"type": "io"},
            help_text="Total tasks failed",
            metric_type="counter"
        )
        self._add_metric(
            "worker_pool_success_rate",
            io_workers.get("success_rate", 0) / 100.0,  # 0.0-1.0
            labels={"type": "io"},
            help_text="Task success rate (0.0-1.0)",
            metric_type="gauge"
        )
        
        # CPU Workers
        cpu_workers = worker_pool_data.get("cpu_workers", {})
        self._add_metric(
            "worker_pool_workers_total",
            cpu_workers.get("total", 0),
            labels={"type": "cpu"},
            metric_type="gauge"
        )
        self._add_metric(
            "worker_pool_workers_active",
            cpu_workers.get("active", 0),
            labels={"type": "cpu"},
            metric_type="gauge"
        )
        self._add_metric(
            "worker_pool_tasks_completed_total",
            cpu_workers.get("tasks_completed", 0),
            labels={"type": "cpu"},
            metric_type="counter"
        )
        self._add_metric(
            "worker_pool_tasks_failed_total",
            cpu_workers.get("tasks_failed", 0),
            labels={"type": "cpu"},
            metric_type="counter"
        )
        self._add_metric(
            "worker_pool_success_rate",
            cpu_workers.get("success_rate", 0) / 100.0,
            labels={"type": "cpu"},
            metric_type="gauge"
        )
        
        # Health Check Config
        self._add_metric(
            "worker_pool_heartbeat_interval_seconds",
            worker_pool_data.get("heartbeat_interval", 0),
            help_text="Worker heartbeat interval in seconds",
            metric_type="gauge"
        )
        self._add_metric(
            "worker_pool_timeout_seconds",
            worker_pool_data.get("worker_timeout", 0),
            help_text="Worker timeout threshold in seconds",
            metric_type="gauge"
        )
    
    def export_memory_metrics(self, memory_data: Dict[str, Any]):
        """Export memory metrics"""
        if "error" in memory_data:
            logger.warning(f"Memory metrics not available: {memory_data['error']}")
            return
        
        # Current Usage
        self._add_metric(
            "memory_usage_bytes",
            memory_data.get("current_mb", 0) * 1024 * 1024,  # Convert to bytes
            help_text="Current memory usage in bytes",
            metric_type="gauge"
        )
        
        # Limits
        self._add_metric(
            "memory_limit_soft_bytes",
            memory_data.get("soft_limit_mb", 0) * 1024 * 1024,
            help_text="Soft memory limit (warning threshold) in bytes",
            metric_type="gauge"
        )
        self._add_metric(
            "memory_limit_hard_bytes",
            memory_data.get("hard_limit_mb", 0) * 1024 * 1024,
            help_text="Hard memory limit (rejection threshold) in bytes",
            metric_type="gauge"
        )
        
        # Usage Percentage
        self._add_metric(
            "memory_usage_percent",
            memory_data.get("usage_percent", 0) / 100.0,  # 0.0-1.0
            help_text="Memory usage as percentage of hard limit (0.0-1.0)",
            metric_type="gauge"
        )
        
        # GC Threshold
        self._add_metric(
            "memory_gc_threshold_bytes",
            memory_data.get("gc_threshold_mb", 0) * 1024 * 1024,
            help_text="Auto-GC trigger threshold in bytes",
            metric_type="gauge"
        )
        
        # Leak Detection Config
        leak_detection = memory_data.get("leak_detection", {})
        self._add_metric(
            "memory_leak_detection_window_seconds",
            leak_detection.get("window_seconds", 0),
            help_text="Memory leak detection window in seconds",
            metric_type="gauge"
        )
        self._add_metric(
            "memory_leak_detection_threshold_bytes",
            leak_detection.get("threshold_mb", 0) * 1024 * 1024,
            help_text="Memory leak detection threshold in bytes",
            metric_type="gauge"
        )
        
        # Status (0 = healthy, 1 = warning, 2 = critical)
        status_map = {"healthy": 0, "warning": 1, "critical": 2}
        status_value = status_map.get(memory_data.get("status", "healthy"), 0)
        self._add_metric(
            "memory_status",
            status_value,
            help_text="Memory status (0=healthy, 1=warning, 2=critical)",
            metric_type="gauge"
        )
    
    def export_circuit_breaker_metrics(self, circuit_data: Dict[str, Any]):
        """Export circuit breaker metrics"""
        if "error" in circuit_data:
            logger.warning(f"Circuit breaker metrics not available: {circuit_data['error']}")
            return
        
        services = circuit_data.get("services", {})
        
        for service_name, service_data in services.items():
            labels = {"service": service_name}
            
            # State (0 = CLOSED, 1 = OPEN, 2 = HALF_OPEN)
            state_map = {"closed": 0, "open": 1, "half_open": 2}
            state_value = state_map.get(service_data.get("state", "closed").lower(), 0)
            self._add_metric(
                "circuit_breaker_state",
                state_value,
                labels=labels,
                help_text="Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
                metric_type="gauge"
            )
            
            # Call Counts
            self._add_metric(
                "circuit_breaker_failures_total",
                service_data.get("failure_count", 0),
                labels=labels,
                help_text="Total circuit breaker failures",
                metric_type="counter"
            )
            self._add_metric(
                "circuit_breaker_successes_total",
                service_data.get("success_count", 0),
                labels=labels,
                help_text="Total circuit breaker successes",
                metric_type="counter"
            )
            self._add_metric(
                "circuit_breaker_calls_total",
                service_data.get("total_calls", 0),
                labels=labels,
                help_text="Total circuit breaker calls",
                metric_type="counter"
            )
        
        # Aggregated Metrics
        self._add_metric(
            "circuit_breaker_services_total",
            circuit_data.get("total_services", 0),
            help_text="Total number of circuit breakers",
            metric_type="gauge"
        )
        self._add_metric(
            "circuit_breaker_open_circuits",
            circuit_data.get("open_circuits", 0),
            help_text="Number of currently open circuits",
            metric_type="gauge"
        )
    
    def export_metrics(self, hardening_data: Dict[str, Any]) -> str:
        """
        Export all production hardening metrics in Prometheus format
        
        Args:
            hardening_data: Hardening metrics from health endpoint
            
        Returns:
            Prometheus exposition format text
        """
        self.metrics = []
        
        # Add timestamp
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        
        # Export each category
        if "worker_pool" in hardening_data:
            self.export_worker_pool_metrics(hardening_data["worker_pool"])
        
        if "memory" in hardening_data:
            self.export_memory_metrics(hardening_data["memory"])
        
        if "circuit_breakers" in hardening_data:
            self.export_circuit_breaker_metrics(hardening_data["circuit_breakers"])
        
        # Add metadata
        self.metrics.insert(0, f"# Generated at {datetime.now().isoformat()}")
        self.metrics.insert(1, f"# Timestamp (ms): {timestamp_ms}")
        self.metrics.insert(2, "")
        
        return "\n".join(self.metrics) + "\n"


# Global exporter instance
_prometheus_exporter: Optional[PrometheusMetrics] = None


def get_prometheus_exporter(namespace: str = "covina") -> PrometheusMetrics:
    """
    Get or create global Prometheus exporter instance
    
    Args:
        namespace: Metric namespace prefix
        
    Returns:
        PrometheusMetrics instance
    """
    global _prometheus_exporter
    
    if _prometheus_exporter is None:
        _prometheus_exporter = PrometheusMetrics(namespace=namespace)
        logger.info(f"✅ Prometheus exporter initialized (namespace: {namespace})")
    
    return _prometheus_exporter
