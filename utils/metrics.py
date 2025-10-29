"""
Internal Metrics System (Without Prometheus)
============================================

Lightweight metrics collection using thread-safe counters, gauges, and histograms.
No external dependencies required.

Features:
- Thread-safe operations
- Counter (incrementing values)
- Gauge (current value, can go up/down)
- Histogram (latency tracking with percentiles)
- JSON export via /metrics endpoint

Usage:
    from utils.metrics import metrics_registry, Counter, Gauge, Histogram
    
    # Create metrics
    docs_processed = Counter("documents_processed_total", "Total documents", ["status"])
    queue_depth = Gauge("queue_depth", "Queue depth", ["pool"])
    latency = Histogram("processing_seconds", "Processing time")
    
    # Update metrics
    docs_processed.inc(labels={"status": "success"})
    queue_depth.set(42, labels={"pool": "io"})
    latency.observe(1.23)
    
    # Export
    metrics_json = metrics_registry.export_json()

Author: Covina Observability Team
Version: 1.0.0
Created: 2025-10-22
"""

import threading
import time
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json


class Counter:
    """Thread-safe counter that only increments."""
    
    def __init__(self, name: str, description: str, labels: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def inc(self, amount: float = 1.0, labels: Dict[str, str] = None) -> None:
        """Increment counter by amount."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._values[label_values] += amount
    
    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current counter value."""
        label_values = self._get_label_values(labels)
        with self._lock:
            return self._values[label_values]
    
    def _get_label_values(self, labels: Dict[str, str] = None) -> tuple:
        """Convert label dict to tuple for dict key."""
        if not self.label_names:
            return ()
        labels = labels or {}
        return tuple(labels.get(name, "") for name in self.label_names)
    
    def export(self) -> Dict[str, Any]:
        """Export counter data."""
        with self._lock:
            samples = []
            for label_values, value in self._values.items():
                label_dict = dict(zip(self.label_names, label_values)) if self.label_names else {}
                samples.append({"labels": label_dict, "value": value})
            
            return {
                "name": self.name,
                "type": "counter",
                "description": self.description,
                "samples": samples
            }


class Gauge:
    """Thread-safe gauge that can go up and down."""
    
    def __init__(self, name: str, description: str, labels: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def set(self, value: float, labels: Dict[str, str] = None) -> None:
        """Set gauge to value."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._values[label_values] = value
    
    def inc(self, amount: float = 1.0, labels: Dict[str, str] = None) -> None:
        """Increment gauge."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._values[label_values] += amount
    
    def dec(self, amount: float = 1.0, labels: Dict[str, str] = None) -> None:
        """Decrement gauge."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._values[label_values] -= amount
    
    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current gauge value."""
        label_values = self._get_label_values(labels)
        with self._lock:
            return self._values[label_values]
    
    def _get_label_values(self, labels: Dict[str, str] = None) -> tuple:
        """Convert label dict to tuple for dict key."""
        if not self.label_names:
            return ()
        labels = labels or {}
        return tuple(labels.get(name, "") for name in self.label_names)
    
    def export(self) -> Dict[str, Any]:
        """Export gauge data."""
        with self._lock:
            samples = []
            for label_values, value in self._values.items():
                label_dict = dict(zip(self.label_names, label_values)) if self.label_names else {}
                samples.append({"labels": label_dict, "value": value})
            
            return {
                "name": self.name,
                "type": "gauge",
                "description": self.description,
                "samples": samples
            }


class Histogram:
    """Thread-safe histogram for latency tracking."""
    
    def __init__(self, name: str, description: str, labels: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._observations: Dict[tuple, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def observe(self, value: float, labels: Dict[str, str] = None) -> None:
        """Record an observation."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._observations[label_values].append(value)
    
    def get_stats(self, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get statistics (count, sum, min, max, p50, p95, p99)."""
        label_values = self._get_label_values(labels)
        with self._lock:
            observations = self._observations[label_values]
            if not observations:
                return {
                    "count": 0,
                    "sum": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0
                }
            
            sorted_obs = sorted(observations)
            count = len(sorted_obs)
            
            return {
                "count": count,
                "sum": sum(sorted_obs),
                "min": sorted_obs[0],
                "max": sorted_obs[-1],
                "p50": self._percentile(sorted_obs, 50),
                "p95": self._percentile(sorted_obs, 95),
                "p99": self._percentile(sorted_obs, 99)
            }
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0
        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def _get_label_values(self, labels: Dict[str, str] = None) -> tuple:
        """Convert label dict to tuple for dict key."""
        if not self.label_names:
            return ()
        labels = labels or {}
        return tuple(labels.get(name, "") for name in self.label_names)
    
    def export(self) -> Dict[str, Any]:
        """Export histogram data."""
        with self._lock:
            samples = []
            for label_values in self._observations.keys():
                label_dict = dict(zip(self.label_names, label_values)) if self.label_names else {}
                stats = self.get_stats(label_dict if self.label_names else None)
                samples.append({
                    "labels": label_dict,
                    "stats": stats
                })
            
            return {
                "name": self.name,
                "type": "histogram",
                "description": self.description,
                "samples": samples
            }


class MetricsRegistry:
    """Global registry for all metrics."""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register(self, metric: Any) -> Any:
        """Register a metric."""
        with self._lock:
            if metric.name in self._metrics:
                return self._metrics[metric.name]  # Return existing
            self._metrics[metric.name] = metric
            return metric
    
    def get(self, name: str) -> Optional[Any]:
        """Get metric by name."""
        with self._lock:
            return self._metrics.get(name)
    
    def export_json(self) -> str:
        """Export all metrics as JSON."""
        with self._lock:
            data = {
                "timestamp": time.time(),
                "metrics": [metric.export() for metric in self._metrics.values()]
            }
            return json.dumps(data, indent=2)
    
    def export_dict(self) -> Dict[str, Any]:
        """Export all metrics as dict."""
        with self._lock:
            return {
                "timestamp": time.time(),
                "metrics": [metric.export() for metric in self._metrics.values()]
            }


def _format_labels(labels: Dict[str, str]) -> str:
    if not labels:
        return ""
    parts = [f"{k}={json.dumps(v)}" for k, v in labels.items()]
    return "{" + ",".join(parts) + "}"


def export_prometheus_text(registry: MetricsRegistry = None) -> str:
    """Export metrics in a Prometheus-like text format.

    Note: Histogram is exported as _count and _sum only (no buckets).
    """
    reg = registry or metrics_registry
    data = reg.export_dict()
    lines = []
    for m in data.get("metrics", []):
        name = m.get("name")
        mtype = m.get("type")
        # HELP / TYPE headers (optional)
        lines.append(f"# TYPE {name} {mtype}")
        # Samples
        samples = m.get("samples", [])
        if mtype in ("counter", "gauge"):
            for s in samples:
                labels = s.get("labels") or {}
                value = s.get("value", 0)
                lines.append(f"{name}{_format_labels(labels)} {value}")
        elif mtype == "histogram":
            # Export as summary-like: _count and _sum
            for s in samples:
                labels = s.get("labels") or {}
                stats = s.get("stats") or {}
                count = stats.get("count", 0)
                _sum = stats.get("sum", 0.0)
                lines.append(f"{name}_count{_format_labels(labels)} {count}")
                lines.append(f"{name}_sum{_format_labels(labels)} {_sum}")
    return "\n".join(lines) + "\n"


# Global registry instance
metrics_registry = MetricsRegistry()


# Example usage
if __name__ == "__main__":
    print("Metrics System Test")
    print("=" * 60)
    
    # Create metrics
    docs_processed = metrics_registry.register(
        Counter("documents_processed_total", "Total documents processed", ["status"])
    )
    queue_depth = metrics_registry.register(
        Gauge("queue_depth", "Current queue depth", ["pool"])
    )
    latency = metrics_registry.register(
        Histogram("processing_seconds", "Document processing time", ["operation"])
    )
    
    # Simulate some activity
    print("\nSimulating metrics collection...")
    
    # Process some documents
    for i in range(10):
        docs_processed.inc(labels={"status": "success"})
    for i in range(2):
        docs_processed.inc(labels={"status": "failed"})
    
    # Update queue depth
    queue_depth.set(42, labels={"pool": "io"})
    queue_depth.set(18, labels={"pool": "cpu"})
    
    # Record latencies
    latencies = [0.123, 0.456, 0.234, 0.567, 0.345, 1.234, 0.678, 0.890]
    for lat in latencies:
        latency.observe(lat, labels={"operation": "classify"})
    
    # Export metrics
    print("\nExported Metrics (JSON):")
    print("-" * 60)
    print(metrics_registry.export_json())
    
    print("\nMetrics test complete!")
