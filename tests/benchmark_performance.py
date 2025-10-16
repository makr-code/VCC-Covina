"""
Performance Benchmarks - Phase 5: Testing & Validation

Measure performance metrics:
- Application startup time
- View switching time
- Memory usage
- Event emission latency
- Component initialization

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 5)
Date: 14.10.2025, 12:15 Uhr
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import tkinter as tk
import tracemalloc
import psutil
from typing import List, Dict
import logging

from frontend.core.event_bus import EventBus, EventType
from frontend.core.task_executor import TaskExecutor
from frontend.core.view_manager import ViewManager
from frontend.core.backend_service import CovinaBackendService

from frontend.widgets.top_toolbar import TopToolbar
from frontend.widgets.sidebar_left import SidebarLeft
from frontend.widgets.sidebar_right import SidebarRight
from frontend.widgets.ai_terminal import AITerminal
from frontend.widgets.status_bar import EnhancedStatusBar

from frontend.views import (
    RecoveryView,
    HomeView,
    UDS3View,
    SAGAView,
)

logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Performance benchmarking suite."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.process = psutil.Process()
    
    def measure_time(self, name: str, func, iterations: int = 1):
        """Measure execution time."""
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            result = func()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        self.results[name] = {
            "avg_ms": round(avg_time, 2),
            "min_ms": round(min_time, 2),
            "max_ms": round(max_time, 2),
            "iterations": iterations
        }
        
        return result
    
    def measure_memory(self, name: str, func):
        """Measure memory usage."""
        tracemalloc.start()
        
        # Get baseline
        baseline = tracemalloc.get_traced_memory()[0]
        
        # Run function
        result = func()
        
        # Get peak memory
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_used = (peak - baseline) / (1024 * 1024)  # Convert to MB
        
        self.results[name]["memory_mb"] = round(memory_used, 2)
        
        return result
    
    def get_system_metrics(self):
        """Get current system metrics."""
        return {
            "cpu_percent": self.process.cpu_percent(),
            "memory_mb": self.process.memory_info().rss / (1024 * 1024),
            "threads": self.process.num_threads()
        }
    
    def print_results(self):
        """Print benchmark results."""
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)
        print()
        
        # Targets
        print("🎯 TARGETS:")
        print("  - Startup time: <500ms")
        print("  - View switch: <50ms")
        print("  - Memory usage: <200 MB")
        print("  - Event latency: <10ms")
        print()
        
        # Results
        print("📊 MEASURED:")
        for name, metrics in self.results.items():
            print(f"\n{name}:")
            for key, value in metrics.items():
                if key == "iterations":
                    print(f"  {key}: {value}")
                elif "ms" in key:
                    print(f"  {key}: {value}ms")
                elif "mb" in key.lower():
                    print(f"  {key}: {value} MB")
                else:
                    print(f"  {key}: {value}")
        
        # System metrics
        print("\n💻 SYSTEM METRICS:")
        metrics = self.get_system_metrics()
        print(f"  CPU: {metrics['cpu_percent']}%")
        print(f"  Memory: {metrics['memory_mb']:.2f} MB")
        print(f"  Threads: {metrics['threads']}")
        
        print("\n" + "=" * 60)
        
        # Validation
        print("\n✅ VALIDATION:")
        self._validate_results()
        
        print("=" * 60)
    
    def _validate_results(self):
        """Validate results against targets."""
        passed = 0
        failed = 0
        
        # Startup time
        if "Application Startup" in self.results:
            startup = self.results["Application Startup"]["avg_ms"]
            if startup < 500:
                print(f"  ✅ Startup time: {startup}ms < 500ms")
                passed += 1
            else:
                print(f"  ❌ Startup time: {startup}ms > 500ms")
                failed += 1
        
        # View switch
        if "View Switch (Single)" in self.results:
            switch = self.results["View Switch (Single)"]["avg_ms"]
            if switch < 50:
                print(f"  ✅ View switch: {switch}ms < 50ms")
                passed += 1
            else:
                print(f"  ❌ View switch: {switch}ms > 50ms")
                failed += 1
        
        # Memory
        metrics = self.get_system_metrics()
        if metrics["memory_mb"] < 200:
            print(f"  ✅ Memory usage: {metrics['memory_mb']:.2f} MB < 200 MB")
            passed += 1
        else:
            print(f"  ❌ Memory usage: {metrics['memory_mb']:.2f} MB > 200 MB")
            failed += 1
        
        # Event latency
        if "Event Emission (Single)" in self.results:
            event = self.results["Event Emission (Single)"]["avg_ms"]
            if event < 10:
                print(f"  ✅ Event latency: {event}ms < 10ms")
                passed += 1
            else:
                print(f"  ❌ Event latency: {event}ms > 10ms")
                failed += 1
        
        print(f"\nTotal: {passed} passed, {failed} failed")


def benchmark_application_startup():
    """Benchmark full application startup."""
    print("Benchmarking application startup...")
    
    bench = PerformanceBenchmark()
    
    def startup():
        root = tk.Tk()
        root.withdraw()
        
        # Phase 1: Core
        event_bus = EventBus()
        task_executor = TaskExecutor()
        backend_service = CovinaBackendService(event_bus, task_executor)
        
        # Phase 2: UI Components
        container = tk.Frame(root)
        toolbar = TopToolbar(container, event_bus)
        sidebar_left = SidebarLeft(container, event_bus)
        sidebar_right = SidebarRight(container, event_bus, backend_service)
        terminal = AITerminal(container, event_bus)
        status_bar = EnhancedStatusBar(container, event_bus)
        
        # Phase 3: Views
        view_manager = ViewManager(container)
        
        views = [
            ("recovery", RecoveryView),
            ("uds3", UDS3View),
            ("saga", SAGAView),
        ]
        
        for name, view_class in views:
            view = view_class(container, event_bus, backend_service)
            view_manager.register_view(name, view)
        
        # Phase 4: Switch to home
        view_manager.switch_view("recovery")
        
        # Cleanup (no shutdown method needed)
        root.destroy()
        
        return True
    
    bench.measure_time("Application Startup", startup, iterations=5)
    
    return bench


def benchmark_view_switching():
    """Benchmark view switching performance."""
    print("Benchmarking view switching...")
    
    bench = PerformanceBenchmark()
    
    # Setup
    root = tk.Tk()
    root.withdraw()
    
    event_bus = EventBus()
    backend_service = CovinaBackendService(event_bus, TaskExecutor())
    
    container = tk.Frame(root)
    view_manager = ViewManager(container)
    
    views = [
        ("recovery", RecoveryView),
        ("uds3", UDS3View),
        ("saga", SAGAView),
    ]
    
    for name, view_class in views:
        view = view_class(container, event_bus, backend_service)
        view_manager.register_view(name, view)
    
    # Benchmark single switch
    def single_switch():
        view_manager.switch_view("recovery")
        return True
    
    bench.measure_time("View Switch (Single)", single_switch, iterations=20)
    
    # Benchmark double switch (deactivate + activate)
    def double_switch():
        view_manager.switch_view("recovery")
        view_manager.switch_view("uds3")
        return True
    
    bench.measure_time("View Switch (Double)", double_switch, iterations=20)
    
    # Cleanup
    root.destroy()
    
    return bench


def benchmark_event_system():
    """Benchmark event system performance."""
    print("Benchmarking event system...")
    
    bench = PerformanceBenchmark()
    
    event_bus = EventBus()
    event_bus.start()
    
    # Subscribe handler
    received = []
    def handler(event):
        received.append(event)
    
    event_bus.subscribe(EventType.JOB_CREATED, handler)
    
    # Benchmark single emission
    def single_emission():
        event_bus.emit(EventType.JOB_CREATED, {"job_id": "test"})
        time.sleep(0.01)  # Wait for async
        return True
    
    bench.measure_time("Event Emission (Single)", single_emission, iterations=20)
    
    # Benchmark batch emission
    def batch_emission():
        for i in range(10):
            event_bus.emit(EventType.JOB_CREATED, {"job_id": f"job_{i}"})
        time.sleep(0.05)  # Wait for async
        return True
    
    bench.measure_time("Event Emission (10x)", batch_emission, iterations=10)
    
    event_bus.stop()
    
    return bench


def benchmark_component_initialization():
    """Benchmark component initialization."""
    print("Benchmarking component initialization...")
    
    bench = PerformanceBenchmark()
    
    root = tk.Tk()
    root.withdraw()
    
    event_bus = EventBus()
    backend_service = CovinaBackendService(event_bus, TaskExecutor())
    container = tk.Frame(root)
    
    # Benchmark UI components
    def init_toolbar():
        toolbar = TopToolbar(container, event_bus)
        return toolbar
    
    def init_sidebar_left():
        sidebar = SidebarLeft(container, event_bus)
        return sidebar
    
    def init_sidebar_right():
        sidebar = SidebarRight(container, event_bus, backend_service)
        return sidebar
    
    def init_terminal():
        terminal = AITerminal(container, event_bus)
        return terminal
    
    def init_status_bar():
        status_bar = EnhancedStatusBar(container, event_bus)
        return status_bar
    
    bench.measure_time("TopToolbar Init", init_toolbar, iterations=10)
    bench.measure_time("SidebarLeft Init", init_sidebar_left, iterations=10)
    bench.measure_time("SidebarRight Init", init_sidebar_right, iterations=10)
    bench.measure_time("AITerminal Init", init_terminal, iterations=10)
    bench.measure_time("StatusBar Init", init_status_bar, iterations=10)
    
    # Benchmark views
    def init_recovery_view():
        view = RecoveryView(container, event_bus, backend_service)
        return view
    
    def init_uds3_view():
        view = UDS3View(container, event_bus, backend_service)
        return view
    
    def init_saga_view():
        view = SAGAView(container, event_bus, backend_service)
        return view
    
    bench.measure_time("RecoveryView Init", init_recovery_view, iterations=10)
    bench.measure_time("UDS3View Init", init_uds3_view, iterations=10)
    bench.measure_time("SAGAView Init", init_saga_view, iterations=10)
    
    root.destroy()
    
    return bench


def run_benchmarks():
    """Run all benchmarks."""
    print("=" * 60)
    print("PERFORMANCE BENCHMARKS - Covina v4.0.0")
    print("=" * 60)
    print()
    
    # Run benchmarks
    results = {}
    
    # Startup
    bench1 = benchmark_application_startup()
    results.update(bench1.results)
    
    # View switching
    bench2 = benchmark_view_switching()
    results.update(bench2.results)
    
    # Event system
    bench3 = benchmark_event_system()
    results.update(bench3.results)
    
    # Component init
    bench4 = benchmark_component_initialization()
    results.update(bench4.results)
    
    # Create combined benchmark for final report
    final_bench = PerformanceBenchmark()
    final_bench.results = results
    final_bench.print_results()


if __name__ == "__main__":
    run_benchmarks()
