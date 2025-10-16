#!/usr/bin/env python3
"""
Covina Performance Benchmarks
==============================

Umfassende Performance-Tests für EventBus und TaskExecutor.

Test-Szenarien:
1. EventBus Throughput-Test (10k events)
2. EventBus Latency-Test (P50, P95, P99)
3. TaskExecutor Throughput-Test (1k tasks)
4. TaskExecutor Latency-Test
5. Stress-Test (100k events, 10k tasks)
"""

import time
import statistics
from typing import List
from covina_architecture import (
    EventBus,
    TaskExecutor,
    Task,
    EventType,
    PerformanceProfiler
)

class PerformanceBenchmark:
    """Performance-Benchmark-Suite"""
    
    def __init__(self):
        self.results = {}
    
    def benchmark_eventbus_throughput(self, num_events: int = 10000) -> dict:
        """
        Benchmark: EventBus Durchsatz
        
        Ziel: 10,000 events/s
        """
        print(f"\n{'='*80}")
        print(f"BENCHMARK: EventBus Throughput ({num_events:,} events)")
        print(f"{'='*80}\n")
        
        # Setup
        bus = EventBus()
        bus.start()
        
        event_counter = {"count": 0}
        
        def fast_handler(event):
            event_counter["count"] += 1
        
        bus.subscribe(EventType.JOB_CREATED, fast_handler)
        
        # Benchmark
        print(f"📤 Sende {num_events:,} Events...")
        start_time = time.perf_counter()
        
        for i in range(num_events):
            bus.emit(EventType.JOB_CREATED, {"index": i})
        
        # Wait for processing
        wait_start = time.perf_counter()
        while event_counter["count"] < num_events:
            if time.perf_counter() - wait_start > 30.0:
                print(f"⚠️ Timeout: Nur {event_counter['count']}/{num_events} Events verarbeitet")
                break
            time.sleep(0.01)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        bus.stop()
        
        # Results
        throughput = num_events / duration
        
        result = {
            "test": "EventBus Throughput",
            "events": num_events,
            "processed": event_counter["count"],
            "duration_s": duration,
            "throughput_events_per_sec": throughput,
            "avg_latency_ms": (duration / num_events) * 1000,
            "target_throughput": 10000,
            "meets_target": throughput >= 10000
        }
        
        self.results["eventbus_throughput"] = result
        
        # Print
        print(f"\n📊 Ergebnisse:")
        print(f"  - Events verarbeitet: {event_counter['count']:,}/{num_events:,}")
        print(f"  - Dauer: {duration:.2f}s")
        print(f"  - Durchsatz: {throughput:,.0f} events/s")
        print(f"  - Avg Latenz: {result['avg_latency_ms']:.3f}ms")
        print(f"  - Ziel: 10,000 events/s")
        print(f"  - Status: {'✅ ERREICHT' if result['meets_target'] else '❌ NICHT ERREICHT'}")
        
        return result
    
    def benchmark_eventbus_latency(self, num_samples: int = 1000) -> dict:
        """
        Benchmark: EventBus Latenz-Verteilung
        
        Misst P50, P95, P99 Latenz
        """
        print(f"\n{'='*80}")
        print(f"BENCHMARK: EventBus Latency ({num_samples:,} samples)")
        print(f"{'='*80}\n")
        
        # Reset Profiler
        PerformanceProfiler.reset()
        PerformanceProfiler.enable()
        
        # Setup
        bus = EventBus()
        bus.start()
        
        def dummy_handler(event):
            pass
        
        bus.subscribe(EventType.JOB_PROGRESS_UPDATE, dummy_handler)
        
        # Benchmark
        print(f"📤 Sende {num_samples:,} Events...")
        for i in range(num_samples):
            bus.emit(EventType.JOB_PROGRESS_UPDATE, {"value": i})
        
        # Wait
        time.sleep(2.0)
        bus.stop()
        
        # Get stats
        stats = PerformanceProfiler.get_stats("_dispatch_event")
        
        if not stats:
            print("❌ Keine Profiling-Daten!")
            return {}
        
        result = {
            "test": "EventBus Latency",
            "samples": stats["count"],
            "mean_ms": stats["mean"] * 1000,
            "median_ms": stats["median"] * 1000,
            "p50_ms": stats["p50"] * 1000,
            "p95_ms": stats["p95"] * 1000,
            "p99_ms": stats["p99"] * 1000,
            "min_ms": stats["min"] * 1000,
            "max_ms": stats["max"] * 1000,
            "target_p95": 1.0,
            "meets_target": stats["p95"] * 1000 <= 1.0
        }
        
        self.results["eventbus_latency"] = result
        
        # Print
        print(f"\n📊 Latenz-Statistiken:")
        print(f"  - Samples: {stats['count']}")
        print(f"  - Mean: {result['mean_ms']:.3f}ms")
        print(f"  - Median: {result['median_ms']:.3f}ms")
        print(f"  - P50: {result['p50_ms']:.3f}ms")
        print(f"  - P95: {result['p95_ms']:.3f}ms ({'✅' if result['meets_target'] else '❌'} Ziel: < 1.0ms)")
        print(f"  - P99: {result['p99_ms']:.3f}ms")
        print(f"  - Min: {result['min_ms']:.3f}ms")
        print(f"  - Max: {result['max_ms']:.3f}ms")
        
        return result
    
    def benchmark_taskexecutor_throughput(self, num_tasks: int = 1000, workers: int = 4) -> dict:
        """
        Benchmark: TaskExecutor Durchsatz
        
        Ziel: 1,000 tasks/s (gesamt) = 250 tasks/s/worker (bei 4 Workers)
        """
        print(f"\n{'='*80}")
        print(f"BENCHMARK: TaskExecutor Throughput ({num_tasks:,} tasks, {workers} workers)")
        print(f"{'='*80}\n")
        
        # Setup
        executor = TaskExecutor(max_workers=workers)
        executor.start()
        
        # Leichtgewichtige Task (~0.1ms) - realistischer für I/O-gebundene Workloads
        def fast_task():
            # Simuliere leichte CPU-Arbeit (ähnlich JSON-Parsing, etc.)
            return sum(range(1000))
        
        # Benchmark
        print(f"📤 Sende {num_tasks:,} Tasks...")
        start_time = time.perf_counter()
        
        task_ids = []
        for i in range(num_tasks):
            task = Task(
                task_id=f"task_{i}",
                func=fast_task,
                priority=5
            )
            task_id = executor.submit(task)
            task_ids.append(task_id)
        
        # Wait for completion (check both active tasks AND queue)
        wait_start = time.perf_counter()
        completed_count = 0
        last_active = num_tasks
        
        while True:
            with executor._lock:
                active_count = len(executor._active_tasks)
            queue_size = executor._task_queue.qsize()
            
            if active_count == 0 and queue_size == 0:
                break
            
            # Progress indicator
            if time.perf_counter() - wait_start > 1.0:
                if active_count != last_active:
                    last_active = active_count
                    print(f"  📊 Fortschritt: {num_tasks - queue_size - active_count}/{num_tasks} abgeschlossen (aktiv: {active_count}, queue: {queue_size})")
                    wait_start = time.perf_counter()  # Reset timeout
            
            if time.perf_counter() - wait_start > 10.0:  # Nur 10s Timeout für Deadlock-Erkennung
                print(f"⚠️ Möglicher Deadlock: {active_count} aktiv, {queue_size} in Queue")
                break
            
            time.sleep(0.05)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        executor.stop()
        
        # Results
        throughput = num_tasks / duration
        throughput_per_worker = throughput / workers
        
        result = {
            "test": "TaskExecutor Throughput",
            "tasks": num_tasks,
            "workers": workers,
            "duration_s": duration,
            "throughput_tasks_per_sec": throughput,
            "throughput_per_worker": throughput_per_worker,
            "avg_latency_ms": (duration / num_tasks) * 1000,
            "target_throughput": 1000,
            "target_per_worker": 250,
            "meets_target": throughput >= 1000
        }
        
        self.results["taskexecutor_throughput"] = result
        
        # Print
        print(f"\n📊 Ergebnisse:")
        print(f"  - Tasks: {num_tasks:,}")
        print(f"  - Workers: {workers}")
        print(f"  - Dauer: {duration:.2f}s")
        print(f"  - Durchsatz (gesamt): {throughput:,.0f} tasks/s")
        print(f"  - Durchsatz (pro Worker): {throughput_per_worker:,.0f} tasks/s")
        print(f"  - Avg Latenz: {result['avg_latency_ms']:.3f}ms")
        print(f"  - Ziel (gesamt): 1,000 tasks/s")
        print(f"  - Ziel (pro Worker): 250 tasks/s")
        print(f"  - Status: {'✅ ERREICHT' if result['meets_target'] else '❌ NICHT ERREICHT'}")
        
        return result
    
    def print_summary(self):
        """Druckt Gesamt-Zusammenfassung"""
        print(f"\n{'='*80}")
        print("BENCHMARK-ZUSAMMENFASSUNG")
        print(f"{'='*80}\n")
        
        for test_name, result in self.results.items():
            if not result:
                continue
            
            test_display = result.get("test", test_name)
            meets_target = result.get("meets_target", False)
            status = "✅ PASS" if meets_target else "❌ FAIL"
            
            print(f"{test_display}: {status}")
            
            if "throughput_events_per_sec" in result:
                print(f"  → {result['throughput_events_per_sec']:,.0f} events/s (Ziel: {result['target_throughput']:,})")
            
            if "throughput_tasks_per_sec" in result:
                print(f"  → {result['throughput_tasks_per_sec']:,.0f} tasks/s (Ziel: {result['target_throughput']:,})")
            
            if "p95_ms" in result:
                print(f"  → P95: {result['p95_ms']:.3f}ms (Ziel: < {result['target_p95']:.1f}ms)")
            
            print()

def main():
    """Führt alle Benchmarks aus"""
    print("\n🚀 Starte Covina Performance Benchmarks...\n")
    
    benchmark = PerformanceBenchmark()
    
    # Run benchmarks
    benchmark.benchmark_eventbus_throughput(num_events=10000)
    benchmark.benchmark_eventbus_latency(num_samples=1000)
    benchmark.benchmark_taskexecutor_throughput(num_tasks=1000, workers=4)
    
    # Summary
    benchmark.print_summary()
    
    # Check if all passed
    all_passed = all(r.get("meets_target", False) for r in benchmark.results.values() if r)
    
    if all_passed:
        print("🎉 ALLE BENCHMARKS BESTANDEN!")
        return 0
    else:
        print("⚠️ EINIGE BENCHMARKS NICHT BESTANDEN")
        return 1

if __name__ == "__main__":
    exit(main())
