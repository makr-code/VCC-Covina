"""Benchmark: PostgreSQL Connection Pooling Performance

Vergleicht Performance zwischen:
- Single Connection (Original Implementation)
- Connection Pool (Neue Implementation)

Metriken:
- Latency (ms): Insert, Query, Delete Operations
- Throughput (ops/s): Concurrent Operations
- Connection Overhead: Create vs Reuse

Expected Improvements:
- Latency: -58% (Connection-Reuse statt Create)
- Throughput: +50-80% (Pool statt Blocking)
- Concurrent: +100-200% (Thread-safe Pool)
"""

import time
import statistics
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# Add UDS3 to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'uds3'))

# Test Configuration
CONFIG = {
    'host': '192.168.178.94',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres',
}

# Benchmark Configuration
NUM_OPERATIONS = 100
NUM_CONCURRENT = 20
NUM_WORKERS = 10


class BenchmarkRunner:
    """Benchmark Runner für Connection Pool Performance"""
    
    def __init__(self):
        self.results = {}
    
    def measure_latency(self, operation_func, name: str, num_runs: int = 100) -> Dict[str, float]:
        """
        Misst Latency einer Operation.
        
        Returns:
            Dict mit p50, p95, p99, min, max, mean (in ms)
        """
        latencies = []
        
        for i in range(num_runs):
            start = time.perf_counter()
            operation_func(i)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms
        
        latencies.sort()
        
        return {
            'operation': name,
            'runs': num_runs,
            'p50': latencies[len(latencies) // 2],
            'p95': latencies[int(len(latencies) * 0.95)],
            'p99': latencies[int(len(latencies) * 0.99)],
            'min': min(latencies),
            'max': max(latencies),
            'mean': statistics.mean(latencies),
            'stdev': statistics.stdev(latencies) if len(latencies) > 1 else 0,
        }
    
    def measure_throughput(self, operation_func, name: str, num_ops: int, num_workers: int) -> Dict[str, float]:
        """
        Misst Throughput bei konkurrenten Operations.
        
        Returns:
            Dict mit ops_per_sec, total_time, success_rate
        """
        start = time.perf_counter()
        results = []
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(operation_func, i)
                for i in range(num_ops)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        end = time.perf_counter()
        total_time = end - start
        
        successes = [r for r in results if r.get('success', False)]
        
        return {
            'operation': name,
            'num_operations': num_ops,
            'num_workers': num_workers,
            'total_time_sec': total_time,
            'ops_per_sec': num_ops / total_time,
            'success_count': len(successes),
            'success_rate': len(successes) / num_ops,
        }
    
    def benchmark_single_connection(self):
        """Benchmark: Single Connection (Original)"""
        # Import from UDS3
        from database.database_api_postgresql import PostgreSQLRelationalBackend
        
        print("\n" + "="*80)
        print("BENCHMARK: Single Connection (Original Implementation)")
        print("="*80)
        
        backend = PostgreSQLRelationalBackend(CONFIG)
        backend.connect()
        
        try:
            # Latency Test: Insert
            def insert_op(i):
                doc_id = f'bench_single_insert_{i:04d}'
                backend.insert_document(
                    document_id=doc_id,
                    file_path=f'/bench/single/{doc_id}.pdf',
                    classification='benchmark',
                    content_length=1000,
                    legal_terms_count=5,
                )
            
            insert_latency = self.measure_latency(insert_op, 'insert', NUM_OPERATIONS)
            self.results['single_insert_latency'] = insert_latency
            
            print(f"\n📊 INSERT Latency:")
            print(f"   P50: {insert_latency['p50']:.2f}ms")
            print(f"   P95: {insert_latency['p95']:.2f}ms")
            print(f"   P99: {insert_latency['p99']:.2f}ms")
            print(f"   Mean: {insert_latency['mean']:.2f}ms ± {insert_latency['stdev']:.2f}ms")
            
            # Latency Test: Query
            def query_op(i):
                doc_id = f'bench_single_insert_{i:04d}'
                backend.get_document(doc_id)
            
            query_latency = self.measure_latency(query_op, 'query', NUM_OPERATIONS)
            self.results['single_query_latency'] = query_latency
            
            print(f"\n📊 QUERY Latency:")
            print(f"   P50: {query_latency['p50']:.2f}ms")
            print(f"   P95: {query_latency['p95']:.2f}ms")
            print(f"   P99: {query_latency['p99']:.2f}ms")
            print(f"   Mean: {query_latency['mean']:.2f}ms ± {query_latency['stdev']:.2f}ms")
            
            # Throughput Test: Concurrent Inserts
            def concurrent_insert_op(i):
                doc_id = f'bench_single_concurrent_{i:04d}'
                result = backend.insert_document(
                    document_id=doc_id,
                    file_path=f'/bench/single/{doc_id}.pdf',
                    classification='benchmark',
                    content_length=1000,
                    legal_terms_count=5,
                )
                return result
            
            throughput = self.measure_throughput(
                concurrent_insert_op, 'concurrent_insert', 
                NUM_CONCURRENT, NUM_WORKERS
            )
            self.results['single_throughput'] = throughput
            
            print(f"\n📊 CONCURRENT INSERT Throughput:")
            print(f"   Operations: {throughput['num_operations']}")
            print(f"   Workers: {throughput['num_workers']}")
            print(f"   Total Time: {throughput['total_time_sec']:.2f}s")
            print(f"   Throughput: {throughput['ops_per_sec']:.1f} ops/s")
            print(f"   Success Rate: {throughput['success_rate']:.1%}")
            
            # Cleanup
            print(f"\n🧹 Cleanup...")
            for i in range(NUM_OPERATIONS):
                backend.delete_document(f'bench_single_insert_{i:04d}')
            for i in range(NUM_CONCURRENT):
                backend.delete_document(f'bench_single_concurrent_{i:04d}')
            
        finally:
            backend.disconnect()
    
    def benchmark_connection_pool(self):
        """Benchmark: Connection Pool (New)"""
        # Import from UDS3
        from database.database_api_postgresql_pooled import PostgreSQLRelationalBackend
        
        print("\n" + "="*80)
        print("BENCHMARK: Connection Pool (New Implementation)")
        print("="*80)
        
        config_pooled = {
            **CONFIG,
            'min_connections': 5,
            'max_connections': 20,
        }
        
        backend = PostgreSQLRelationalBackend(config_pooled)
        backend.connect()
        
        try:
            # Latency Test: Insert
            def insert_op(i):
                doc_id = f'bench_pooled_insert_{i:04d}'
                backend.insert_document(
                    document_id=doc_id,
                    file_path=f'/bench/pooled/{doc_id}.pdf',
                    classification='benchmark',
                    content_length=1000,
                    legal_terms_count=5,
                )
            
            insert_latency = self.measure_latency(insert_op, 'insert', NUM_OPERATIONS)
            self.results['pooled_insert_latency'] = insert_latency
            
            print(f"\n📊 INSERT Latency:")
            print(f"   P50: {insert_latency['p50']:.2f}ms")
            print(f"   P95: {insert_latency['p95']:.2f}ms")
            print(f"   P99: {insert_latency['p99']:.2f}ms")
            print(f"   Mean: {insert_latency['mean']:.2f}ms ± {insert_latency['stdev']:.2f}ms")
            
            # Latency Test: Query
            def query_op(i):
                doc_id = f'bench_pooled_insert_{i:04d}'
                backend.get_document(doc_id)
            
            query_latency = self.measure_latency(query_op, 'query', NUM_OPERATIONS)
            self.results['pooled_query_latency'] = query_latency
            
            print(f"\n📊 QUERY Latency:")
            print(f"   P50: {query_latency['p50']:.2f}ms")
            print(f"   P95: {query_latency['p95']:.2f}ms")
            print(f"   P99: {query_latency['p99']:.2f}ms")
            print(f"   Mean: {query_latency['mean']:.2f}ms ± {query_latency['stdev']:.2f}ms")
            
            # Throughput Test: Concurrent Inserts
            def concurrent_insert_op(i):
                doc_id = f'bench_pooled_concurrent_{i:04d}'
                result = backend.insert_document(
                    document_id=doc_id,
                    file_path=f'/bench/pooled/{doc_id}.pdf',
                    classification='benchmark',
                    content_length=1000,
                    legal_terms_count=5,
                )
                return result
            
            throughput = self.measure_throughput(
                concurrent_insert_op, 'concurrent_insert', 
                NUM_CONCURRENT, NUM_WORKERS
            )
            self.results['pooled_throughput'] = throughput
            
            print(f"\n📊 CONCURRENT INSERT Throughput:")
            print(f"   Operations: {throughput['num_operations']}")
            print(f"   Workers: {throughput['num_workers']}")
            print(f"   Total Time: {throughput['total_time_sec']:.2f}s")
            print(f"   Throughput: {throughput['ops_per_sec']:.1f} ops/s")
            print(f"   Success Rate: {throughput['success_rate']:.1%}")
            
            # Pool Statistics
            pool_stats = backend.get_pool_stats()
            print(f"\n📊 Connection Pool Statistics:")
            print(f"   Created: {pool_stats['total_created']}")
            print(f"   Reused: {pool_stats['total_reused']}")
            print(f"   Errors: {pool_stats['total_errors']}")
            print(f"   Reuse Rate: {pool_stats['reuse_rate']:.1%}")
            
            # Cleanup
            print(f"\n🧹 Cleanup...")
            for i in range(NUM_OPERATIONS):
                backend.delete_document(f'bench_pooled_insert_{i:04d}')
            for i in range(NUM_CONCURRENT):
                backend.delete_document(f'bench_pooled_concurrent_{i:04d}')
            
        finally:
            backend.disconnect()
    
    def print_comparison(self):
        """Vergleicht Ergebnisse und zeigt Improvements"""
        print("\n" + "="*80)
        print("COMPARISON: Single Connection vs Connection Pool")
        print("="*80)
        
        # Insert Latency Comparison
        single_insert = self.results['single_insert_latency']
        pooled_insert = self.results['pooled_insert_latency']
        
        insert_improvement = (
            (single_insert['mean'] - pooled_insert['mean']) / single_insert['mean']
        ) * 100
        
        print(f"\n📊 INSERT Latency (Mean):")
        print(f"   Single Connection: {single_insert['mean']:.2f}ms")
        print(f"   Connection Pool:   {pooled_insert['mean']:.2f}ms")
        print(f"   Improvement:       {insert_improvement:+.1f}% {'✅' if insert_improvement > 0 else '❌'}")
        
        # Query Latency Comparison
        single_query = self.results['single_query_latency']
        pooled_query = self.results['pooled_query_latency']
        
        query_improvement = (
            (single_query['mean'] - pooled_query['mean']) / single_query['mean']
        ) * 100
        
        print(f"\n📊 QUERY Latency (Mean):")
        print(f"   Single Connection: {single_query['mean']:.2f}ms")
        print(f"   Connection Pool:   {pooled_query['mean']:.2f}ms")
        print(f"   Improvement:       {query_improvement:+.1f}% {'✅' if query_improvement > 0 else '❌'}")
        
        # Throughput Comparison
        single_tput = self.results['single_throughput']
        pooled_tput = self.results['pooled_throughput']
        
        tput_improvement = (
            (pooled_tput['ops_per_sec'] - single_tput['ops_per_sec']) / single_tput['ops_per_sec']
        ) * 100
        
        print(f"\n📊 CONCURRENT INSERT Throughput:")
        print(f"   Single Connection: {single_tput['ops_per_sec']:.1f} ops/s")
        print(f"   Connection Pool:   {pooled_tput['ops_per_sec']:.1f} ops/s")
        print(f"   Improvement:       {tput_improvement:+.1f}% {'✅' if tput_improvement > 0 else '❌'}")
        
        # Overall Assessment
        print(f"\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        total_improvement = (insert_improvement + query_improvement + tput_improvement) / 3
        
        print(f"\n✅ Average Improvement: {total_improvement:+.1f}%")
        
        if insert_improvement >= 50:
            print(f"   🎯 INSERT Latency: EXCELLENT ({insert_improvement:+.1f}%)")
        elif insert_improvement >= 30:
            print(f"   ✅ INSERT Latency: GOOD ({insert_improvement:+.1f}%)")
        elif insert_improvement >= 10:
            print(f"   ⚠️  INSERT Latency: MODERATE ({insert_improvement:+.1f}%)")
        else:
            print(f"   ❌ INSERT Latency: LOW ({insert_improvement:+.1f}%)")
        
        if query_improvement >= 50:
            print(f"   🎯 QUERY Latency: EXCELLENT ({query_improvement:+.1f}%)")
        elif query_improvement >= 30:
            print(f"   ✅ QUERY Latency: GOOD ({query_improvement:+.1f}%)")
        elif query_improvement >= 10:
            print(f"   ⚠️  QUERY Latency: MODERATE ({query_improvement:+.1f}%)")
        else:
            print(f"   ❌ QUERY Latency: LOW ({query_improvement:+.1f}%)")
        
        if tput_improvement >= 80:
            print(f"   🎯 Throughput: EXCELLENT ({tput_improvement:+.1f}%)")
        elif tput_improvement >= 50:
            print(f"   ✅ Throughput: GOOD ({tput_improvement:+.1f}%)")
        elif tput_improvement >= 20:
            print(f"   ⚠️  Throughput: MODERATE ({tput_improvement:+.1f}%)")
        else:
            print(f"   ❌ Throughput: LOW ({tput_improvement:+.1f}%)")
        
        print(f"\n" + "="*80)
        
        if total_improvement >= 50:
            print(f"✅ RATING: 5.0/5 - EXCELLENT PERFORMANCE IMPROVEMENT!")
        elif total_improvement >= 30:
            print(f"✅ RATING: 4.5/5 - GOOD PERFORMANCE IMPROVEMENT")
        elif total_improvement >= 10:
            print(f"⚠️  RATING: 4.0/5 - MODERATE PERFORMANCE IMPROVEMENT")
        else:
            print(f"❌ RATING: 3.5/5 - LIMITED PERFORMANCE IMPROVEMENT")
        
        print(f"="*80 + "\n")


def main():
    """Run benchmark"""
    print("\n" + "="*80)
    print("PostgreSQL Connection Pooling Benchmark")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"   Operations: {NUM_OPERATIONS}")
    print(f"   Concurrent: {NUM_CONCURRENT}")
    print(f"   Workers: {NUM_WORKERS}")
    print(f"   Database: {CONFIG['host']}:{CONFIG['port']}/{CONFIG['database']}")
    
    runner = BenchmarkRunner()
    
    # Run benchmarks
    try:
        runner.benchmark_single_connection()
        runner.benchmark_connection_pool()
        runner.print_comparison()
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
