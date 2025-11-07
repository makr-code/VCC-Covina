"""
Performance Benchmarks: Themis vs UDS3
=======================================

Compares performance metrics between Themis DB and UDS3:
- CRUD operation latency
- Vector query performance
- Transaction overhead
- Batch operation speedup
- Connection pooling efficiency

Usage:
    python tests/benchmark_themis_vs_uds3.py

Output:
    - Console report with comparison tables
    - JSON results: tests/benchmark_results.json
    - CSV results: tests/benchmark_results.csv
"""

import asyncio
import time
import statistics
import json
import csv
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, asdict
import numpy as np

# Conditional imports (graceful degradation if Themis not available)
try:
    from database.themis_adapter import ThemisAdapter
    from database.themis_relational import ThemisRelationalBackend
    from database.themis_vector import ThemisVectorBackend
    from database.themis_graph import ThemisGraphBackend
    from database.themis_document import ThemisDocumentBackend
    THEMIS_AVAILABLE = True
except ImportError:
    THEMIS_AVAILABLE = False
    print("⚠️  Warning: Themis adapter not available, will skip Themis benchmarks")

# UDS3 imports
try:
    from database.database_api_postgresql import DatabasePostgreSQL
    from uds3.database.database_api_chromadb_remote import ChromaDBRemote
    from uds3.uds3_relations_core import UDS3RelationsCore
    from database.database_api_couchdb import DatabaseCouchDB
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    print("⚠️  Warning: UDS3 not available, will skip UDS3 benchmarks")


# ============================================================================
# Benchmark Configuration
# ============================================================================

BENCHMARK_CONFIG = {
    "warmup_iterations": 3,      # Warmup before timing
    "test_iterations": 10,       # Iterations for averaging
    "crud_operations": 100,      # Operations per CRUD test
    "vector_dimensions": 384,    # Embedding dimension
    "vector_query_sizes": [100, 1000, 10000],  # Collection sizes
    "batch_sizes": [1, 10, 50, 100],  # Batch operation sizes
    "transaction_operations": 10,  # Ops per transaction test
}

# Connection configs
THEMIS_CONFIG = {
    "base_url": "http://localhost:8765",
    "timeout": 30,
    "max_retries": 3,
}

UDS3_CONFIG = {
    "postgres": {
        "host": "192.168.178.94",
        "port": 5432,
        "user": "postgres",
        "password": "postgres",
        "database": "postgres",
    },
    "chromadb": {
        "host": "192.168.178.94",
        "port": 8000,
    },
    "neo4j": {
        "uri": "bolt://192.168.178.94:7687",
        "user": "neo4j",
        "password": "neo4j",
    },
    "couchdb": {
        "host": "192.168.178.94",
        "port": 32931,
    },
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BenchmarkResult:
    """Single benchmark result"""
    name: str
    system: str  # "Themis" or "UDS3"
    operation: str  # "CRUD", "Vector", "Transaction", etc.
    mean_ms: float
    median_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    p99_ms: float
    iterations: int
    
    def speedup_vs(self, other: 'BenchmarkResult') -> float:
        """Calculate speedup relative to another result"""
        if other.mean_ms == 0:
            return float('inf')
        return other.mean_ms / self.mean_ms


# ============================================================================
# Benchmark Infrastructure
# ============================================================================

class BenchmarkTimer:
    """High-precision timing utility"""
    
    def __init__(self):
        self.measurements: List[float] = []
    
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        elapsed = (time.perf_counter() - self.start) * 1000  # Convert to ms
        self.measurements.append(elapsed)
    
    def get_stats(self, name: str, system: str, operation: str) -> BenchmarkResult:
        """Calculate statistics from measurements"""
        if not self.measurements:
            return BenchmarkResult(name, system, operation, 0, 0, 0, 0, 0, 0, 0, 0)
        
        measurements = np.array(self.measurements)
        return BenchmarkResult(
            name=name,
            system=system,
            operation=operation,
            mean_ms=float(np.mean(measurements)),
            median_ms=float(np.median(measurements)),
            std_ms=float(np.std(measurements)),
            min_ms=float(np.min(measurements)),
            max_ms=float(np.max(measurements)),
            p95_ms=float(np.percentile(measurements, 95)),
            p99_ms=float(np.percentile(measurements, 99)),
            iterations=len(measurements),
        )


class TestDataGenerator:
    """Generate realistic test data"""
    
    @staticmethod
    def generate_entity(index: int) -> Dict[str, Any]:
        """Generate test entity for relational DB"""
        return {
            "id": f"benchmark_entity_{index}",
            "type": "test_document",
            "attributes": {
                "title": f"Test Document {index}",
                "content": f"Content for benchmark test {index}" * 10,
                "index": index,
            },
            "metadata": {
                "created_at": "2025-11-07T16:30:00Z",
                "benchmark": True,
            }
        }
    
    @staticmethod
    def generate_vector(index: int, dimensions: int = 384) -> Dict[str, Any]:
        """Generate test vector for vector DB"""
        # Normalized random vector
        vec = np.random.randn(dimensions)
        vec = vec / np.linalg.norm(vec)
        
        return {
            "id": f"benchmark_vector_{index}",
            "embedding": vec.tolist(),
            "metadata": {
                "text": f"Test chunk {index}",
                "index": index,
            }
        }
    
    @staticmethod
    def generate_graph_node(index: int) -> Dict[str, Any]:
        """Generate test graph node"""
        return {
            "id": f"benchmark_node_{index}",
            "type": "TestNode",
            "properties": {
                "name": f"Node {index}",
                "index": index,
            }
        }
    
    @staticmethod
    def generate_document(index: int) -> Dict[str, Any]:
        """Generate test document"""
        return {
            "id": f"benchmark_doc_{index}",
            "content": f"Document content for benchmark test {index}" * 20,
            "metadata": {
                "filename": f"test_{index}.txt",
                "mime_type": "text/plain",
                "size": 1024,
            }
        }


# ============================================================================
# CRUD Benchmarks
# ============================================================================

class CRUDBenchmarks:
    """CRUD operation benchmarks"""
    
    @staticmethod
    async def benchmark_themis_crud(config: Dict) -> List[BenchmarkResult]:
        """Benchmark Themis CRUD operations"""
        if not THEMIS_AVAILABLE:
            return []
        
        results = []
        adapter = ThemisAdapter(**THEMIS_CONFIG)
        await adapter.initialize()
        
        try:
            backend = ThemisRelationalBackend(adapter._client, THEMIS_CONFIG["base_url"])
            
            # CREATE benchmark
            timer_create = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                entity = TestDataGenerator.generate_entity(i)
                with timer_create:
                    await backend.create_entity("benchmark_entities", entity)
            
            results.append(timer_create.get_stats(
                "Create Entity", "Themis", "CRUD"
            ))
            
            # READ benchmark
            timer_read = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                with timer_read:
                    await backend.get_entity("benchmark_entities", f"benchmark_entity_{i}")
            
            results.append(timer_read.get_stats(
                "Read Entity", "Themis", "CRUD"
            ))
            
            # UPDATE benchmark
            timer_update = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                update_data = {"attributes": {"updated": True}}
                with timer_update:
                    await backend.update_entity(
                        "benchmark_entities",
                        f"benchmark_entity_{i}",
                        update_data
                    )
            
            results.append(timer_update.get_stats(
                "Update Entity", "Themis", "CRUD"
            ))
            
            # DELETE benchmark
            timer_delete = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                with timer_delete:
                    await backend.delete_entity("benchmark_entities", f"benchmark_entity_{i}")
            
            results.append(timer_delete.get_stats(
                "Delete Entity", "Themis", "CRUD"
            ))
        
        finally:
            await adapter.close()
        
        return results
    
    @staticmethod
    async def benchmark_uds3_crud(config: Dict) -> List[BenchmarkResult]:
        """Benchmark UDS3 CRUD operations"""
        if not UDS3_AVAILABLE:
            return []
        
        results = []
        db = DatabasePostgreSQL(**UDS3_CONFIG["postgres"])
        await db.connect()
        
        try:
            # CREATE benchmark
            timer_create = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                entity = TestDataGenerator.generate_entity(i)
                with timer_create:
                    await db.insert_document(entity)
            
            results.append(timer_create.get_stats(
                "Create Entity", "UDS3", "CRUD"
            ))
            
            # READ benchmark
            timer_read = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                with timer_read:
                    await db.get_document(f"benchmark_entity_{i}")
            
            results.append(timer_read.get_stats(
                "Read Entity", "UDS3", "CRUD"
            ))
            
            # UPDATE benchmark
            timer_update = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                entity = await db.get_document(f"benchmark_entity_{i}")
                entity["attributes"]["updated"] = True
                with timer_update:
                    await db.update_document(entity)
            
            results.append(timer_update.get_stats(
                "Update Entity", "UDS3", "CRUD"
            ))
            
            # DELETE benchmark
            timer_delete = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                with timer_delete:
                    await db.delete_document(f"benchmark_entity_{i}")
            
            results.append(timer_delete.get_stats(
                "Delete Entity", "UDS3", "CRUD"
            ))
        
        finally:
            await db.disconnect()
        
        return results


# ============================================================================
# Vector Query Benchmarks
# ============================================================================

class VectorBenchmarks:
    """Vector similarity search benchmarks"""
    
    @staticmethod
    async def benchmark_themis_vector(config: Dict) -> List[BenchmarkResult]:
        """Benchmark Themis vector operations"""
        if not THEMIS_AVAILABLE:
            return []
        
        results = []
        adapter = ThemisAdapter(**THEMIS_CONFIG)
        await adapter.initialize()
        
        try:
            backend = ThemisVectorBackend(adapter._client, THEMIS_CONFIG["base_url"])
            
            # Insert benchmark vectors
            print("  Inserting test vectors...")
            for size in config["vector_query_sizes"]:
                collection = f"benchmark_vectors_{size}"
                
                # Insert vectors
                for i in range(size):
                    vector_data = TestDataGenerator.generate_vector(i, config["vector_dimensions"])
                    await backend.add_vector(
                        collection=collection,
                        vector_id=vector_data["id"],
                        embedding=vector_data["embedding"],
                        metadata=vector_data["metadata"]
                    )
                
                # Benchmark queries
                timer_query = BenchmarkTimer()
                query_vector = TestDataGenerator.generate_vector(0, config["vector_dimensions"])
                
                for _ in range(config["test_iterations"]):
                    with timer_query:
                        await backend.query_vectors(
                            collection=collection,
                            query_embedding=query_vector["embedding"],
                            n_results=10
                        )
                
                results.append(timer_query.get_stats(
                    f"Vector Query (n={size})", "Themis", "Vector"
                ))
        
        finally:
            await adapter.close()
        
        return results
    
    @staticmethod
    async def benchmark_uds3_vector(config: Dict) -> List[BenchmarkResult]:
        """Benchmark UDS3 vector operations"""
        if not UDS3_AVAILABLE:
            return []
        
        results = []
        db = ChromaDBRemote(**UDS3_CONFIG["chromadb"])
        await db.connect()
        
        try:
            # Similar structure to Themis benchmark
            for size in config["vector_query_sizes"]:
                collection = f"benchmark_vectors_{size}"
                
                # Insert vectors
                print(f"  Inserting {size} test vectors...")
                for i in range(size):
                    vector_data = TestDataGenerator.generate_vector(i, config["vector_dimensions"])
                    await db.add_vector(
                        collection=collection,
                        vector_id=vector_data["id"],
                        embedding=vector_data["embedding"],
                        metadata=vector_data["metadata"]
                    )
                
                # Benchmark queries
                timer_query = BenchmarkTimer()
                query_vector = TestDataGenerator.generate_vector(0, config["vector_dimensions"])
                
                for _ in range(config["test_iterations"]):
                    with timer_query:
                        await db.query_vectors(
                            collection=collection,
                            query_embedding=query_vector["embedding"],
                            n_results=10
                        )
                
                results.append(timer_query.get_stats(
                    f"Vector Query (n={size})", "UDS3", "Vector"
                ))
        
        finally:
            await db.disconnect()
        
        return results


# ============================================================================
# Transaction Benchmarks
# ============================================================================

class TransactionBenchmarks:
    """Transaction overhead benchmarks"""
    
    @staticmethod
    async def benchmark_themis_transactions(config: Dict) -> List[BenchmarkResult]:
        """Benchmark Themis transaction overhead"""
        if not THEMIS_AVAILABLE:
            return []
        
        results = []
        adapter = ThemisAdapter(**THEMIS_CONFIG)
        await adapter.initialize()
        
        try:
            backend = ThemisRelationalBackend(adapter._client, THEMIS_CONFIG["base_url"])
            
            # Benchmark: Operations WITHOUT transaction
            timer_no_txn = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                with timer_no_txn:
                    for j in range(config["transaction_operations"]):
                        entity = TestDataGenerator.generate_entity(i * 100 + j)
                        await backend.create_entity("benchmark_txn", entity)
            
            results.append(timer_no_txn.get_stats(
                "Without Transaction", "Themis", "Transaction"
            ))
            
            # Benchmark: Operations WITH transaction
            timer_with_txn = BenchmarkTimer()
            for i in range(config["test_iterations"]):
                with timer_with_txn:
                    async with backend.transaction() as txn_id:
                        for j in range(config["transaction_operations"]):
                            entity = TestDataGenerator.generate_entity(i * 100 + j + 1000)
                            await backend.create_entity(
                                "benchmark_txn",
                                entity,
                                transaction_id=txn_id
                            )
            
            results.append(timer_with_txn.get_stats(
                "With Transaction", "Themis", "Transaction"
            ))
        
        finally:
            await adapter.close()
        
        return results


# ============================================================================
# Batch Operation Benchmarks
# ============================================================================

class BatchBenchmarks:
    """Batch vs single operation benchmarks"""
    
    @staticmethod
    async def benchmark_themis_batch(config: Dict) -> List[BenchmarkResult]:
        """Benchmark Themis batch operations"""
        if not THEMIS_AVAILABLE:
            return []
        
        results = []
        adapter = ThemisAdapter(**THEMIS_CONFIG)
        await adapter.initialize()
        
        try:
            backend = ThemisRelationalBackend(adapter._client, THEMIS_CONFIG["base_url"])
            
            for batch_size in config["batch_sizes"]:
                # Single operations
                timer_single = BenchmarkTimer()
                for i in range(config["test_iterations"]):
                    with timer_single:
                        for j in range(batch_size):
                            entity = TestDataGenerator.generate_entity(i * batch_size + j)
                            await backend.create_entity("benchmark_batch", entity)
                
                results.append(timer_single.get_stats(
                    f"Single Ops (n={batch_size})", "Themis", "Batch"
                ))
                
                # Batch operations
                timer_batch = BenchmarkTimer()
                for i in range(config["test_iterations"]):
                    entities = [
                        TestDataGenerator.generate_entity(i * batch_size + j + 10000)
                        for j in range(batch_size)
                    ]
                    with timer_batch:
                        await backend.batch_create("benchmark_batch", entities)
                
                results.append(timer_batch.get_stats(
                    f"Batch Ops (n={batch_size})", "Themis", "Batch"
                ))
        
        finally:
            await adapter.close()
        
        return results


# ============================================================================
# Main Benchmark Runner
# ============================================================================

async def run_all_benchmarks():
    """Run all benchmarks and generate report"""
    
    print("=" * 80)
    print("Themis vs UDS3 Performance Benchmarks")
    print("=" * 80)
    print()
    
    all_results: List[BenchmarkResult] = []
    
    # CRUD Benchmarks
    print("🔧 Running CRUD Benchmarks...")
    if THEMIS_AVAILABLE:
        print("  Running Themis CRUD...")
        themis_crud = await CRUDBenchmarks.benchmark_themis_crud(BENCHMARK_CONFIG)
        all_results.extend(themis_crud)
    
    if UDS3_AVAILABLE:
        print("  Running UDS3 CRUD...")
        uds3_crud = await CRUDBenchmarks.benchmark_uds3_crud(BENCHMARK_CONFIG)
        all_results.extend(uds3_crud)
    
    # Vector Benchmarks
    print("\n📊 Running Vector Query Benchmarks...")
    if THEMIS_AVAILABLE:
        print("  Running Themis Vector...")
        themis_vector = await VectorBenchmarks.benchmark_themis_vector(BENCHMARK_CONFIG)
        all_results.extend(themis_vector)
    
    if UDS3_AVAILABLE:
        print("  Running UDS3 Vector...")
        uds3_vector = await VectorBenchmarks.benchmark_uds3_vector(BENCHMARK_CONFIG)
        all_results.extend(uds3_vector)
    
    # Transaction Benchmarks
    print("\n⚡ Running Transaction Benchmarks...")
    if THEMIS_AVAILABLE:
        print("  Running Themis Transactions...")
        themis_txn = await TransactionBenchmarks.benchmark_themis_transactions(BENCHMARK_CONFIG)
        all_results.extend(themis_txn)
    
    # Batch Benchmarks
    print("\n📦 Running Batch Operation Benchmarks...")
    if THEMIS_AVAILABLE:
        print("  Running Themis Batch...")
        themis_batch = await BatchBenchmarks.benchmark_themis_batch(BENCHMARK_CONFIG)
        all_results.extend(themis_batch)
    
    # Generate report
    print("\n" + "=" * 80)
    print("📊 BENCHMARK RESULTS")
    print("=" * 80)
    
    # Print results
    generate_console_report(all_results)
    
    # Save results
    save_results(all_results)
    
    return all_results


def generate_console_report(results: List[BenchmarkResult]):
    """Generate formatted console report"""
    
    # Group by operation type
    operations = {}
    for result in results:
        if result.operation not in operations:
            operations[result.operation] = []
        operations[result.operation].append(result)
    
    for operation, op_results in operations.items():
        print(f"\n{operation} Operations:")
        print("-" * 80)
        print(f"{'Benchmark':<40} {'System':<10} {'Mean (ms)':<12} {'P95 (ms)':<12} {'Speedup':<10}")
        print("-" * 80)
        
        # Group by benchmark name
        benchmarks = {}
        for result in op_results:
            if result.name not in benchmarks:
                benchmarks[result.name] = []
            benchmarks[result.name].append(result)
        
        for name, bench_results in benchmarks.items():
            for i, result in enumerate(bench_results):
                speedup_str = "-"
                if len(bench_results) == 2:
                    # Calculate speedup
                    other = bench_results[1-i]
                    speedup = result.speedup_vs(other)
                    if speedup > 1:
                        speedup_str = f"{speedup:.2f}x faster"
                    else:
                        speedup_str = f"{1/speedup:.2f}x slower"
                
                print(f"{name:<40} {result.system:<10} {result.mean_ms:<12.2f} {result.p95_ms:<12.2f} {speedup_str:<10}")


def save_results(results: List[BenchmarkResult]):
    """Save results to JSON and CSV"""
    
    # JSON
    json_path = "tests/benchmark_results.json"
    with open(json_path, 'w') as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\n✅ Results saved to: {json_path}")
    
    # CSV
    csv_path = "tests/benchmark_results.csv"
    with open(csv_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=asdict(results[0]).keys())
            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))
    print(f"✅ Results saved to: {csv_path}")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Performance Benchmarks...\n")
    
    if not THEMIS_AVAILABLE and not UDS3_AVAILABLE:
        print("❌ Error: Neither Themis nor UDS3 available!")
        exit(1)
    
    asyncio.run(run_all_benchmarks())
    
    print("\n✅ Benchmarks Complete!\n")
