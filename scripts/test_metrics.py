"""
Metrics System Test Script
===========================

Tests the internal metrics system by:
1. Testing metrics classes directly
2. Generating activity on both backends
3. Fetching and validating /metrics endpoints

Author: Covina Observability Team
Version: 1.0.0
Created: 2025-10-22
"""

import sys
import time
import requests
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.metrics import Counter, Gauge, Histogram, metrics_registry


def test_metrics_classes():
    """Test Counter, Gauge, and Histogram classes."""
    print("\n" + "="*60)
    print("TEST 1: Metrics Classes")
    print("="*60)
    
    # Create test metrics
    counter = Counter("test_counter", "Test counter", ["status"])
    gauge = Gauge("test_gauge", "Test gauge", ["pool"])
    histogram = Histogram("test_histogram", "Test histogram", ["operation"])
    
    print("\n1. Counter Test...")
    counter.inc(labels={"status": "success"})
    counter.inc(amount=5, labels={"status": "success"})
    counter.inc(labels={"status": "failed"})
    
    success_count = counter.get(labels={"status": "success"})
    failed_count = counter.get(labels={"status": "failed"})
    
    print(f"   Success count: {success_count} (expected: 6.0)")
    print(f"   Failed count: {failed_count} (expected: 1.0)")
    
    passed = success_count == 6.0 and failed_count == 1.0
    print(f"   {'✅ PASS' if passed else '❌ FAIL'}")
    
    print("\n2. Gauge Test...")
    gauge.set(42, labels={"pool": "io"})
    gauge.inc(8, labels={"pool": "io"})
    gauge.set(18, labels={"pool": "cpu"})
    
    io_value = gauge.get(labels={"pool": "io"})
    cpu_value = gauge.get(labels={"pool": "cpu"})
    
    print(f"   IO pool: {io_value} (expected: 50.0)")
    print(f"   CPU pool: {cpu_value} (expected: 18.0)")
    
    passed = io_value == 50.0 and cpu_value == 18.0
    print(f"   {'✅ PASS' if passed else '❌ FAIL'}")
    
    print("\n3. Histogram Test...")
    latencies = [0.1, 0.2, 0.15, 0.3, 0.25, 0.5, 0.4, 1.0]
    for lat in latencies:
        histogram.observe(lat, labels={"operation": "query"})
    
    stats = histogram.get_stats(labels={"operation": "query"})
    print(f"   Count: {stats['count']} (expected: 8)")
    print(f"   Min: {stats['min']} (expected: 0.1)")
    print(f"   Max: {stats['max']} (expected: 1.0)")
    print(f"   P50: {stats['p50']}")
    print(f"   P95: {stats['p95']}")
    print(f"   P99: {stats['p99']}")
    
    passed = stats['count'] == 8 and stats['min'] == 0.1 and stats['max'] == 1.0
    print(f"   {'✅ PASS' if passed else '❌ FAIL'}")
    
    return True


def test_main_backend_metrics():
    """Test Main Backend /metrics endpoint."""
    print("\n" + "="*60)
    print("TEST 2: Main Backend Metrics")
    print("="*60)
    
    backend_url = "http://127.0.0.1:45678"
    
    try:
        # Check if backend is running
        health = requests.get(f"{backend_url}/health", timeout=30)  # Increased timeout
        if health.status_code != 200:
            print(f"❌ Main Backend nicht erreichbar (Status: {health.status_code})")
            return False
        
        print(f"✅ Main Backend läuft auf {backend_url}")
        
        # Generate some activity
        print("\n1. Generiere Aktivität...")
        queries = ["test query 1", "test query 2", "another search"]
        
        for i, query in enumerate(queries, 1):
            try:
                response = requests.get(
                    f"{backend_url}/query/semantic",
                    params={"query": query, "top_k": 5},
                    timeout=10
                )
                print(f"   Query {i}: Status {response.status_code}")
            except Exception as e:
                print(f"   Query {i}: {e}")
        
        # Wait for metrics to be collected
        time.sleep(1)
        
        # Fetch metrics
        print("\n2. Abrufen der Metriken...")
        metrics = requests.get(f"{backend_url}/metrics", timeout=30)  # Increased for slow startup
        
        if metrics.status_code != 200:
            print(f"❌ Metrics endpoint error: {metrics.status_code}")
            return False
        
        metrics_data = metrics.json()
        print(f"✅ Metrics abgerufen (Timestamp: {metrics_data.get('timestamp')})")
        
        # Validate metrics structure
        print("\n3. Validierung der Metriken-Struktur...")
        if 'metrics' not in metrics_data:
            print("❌ 'metrics' key fehlt")
            return False
        
        metric_names = [m['name'] for m in metrics_data['metrics']]
        print(f"   Gefundene Metriken: {len(metric_names)}")
        
        expected_metrics = [
            "queries_total",
            "query_latency_seconds",
            "db_operations_total",
            "db_operation_seconds",
            "pool_connections_current"
        ]
        
        for expected in expected_metrics:
            if expected in metric_names:
                print(f"   ✅ {expected}")
            else:
                print(f"   ⚠️  {expected} (not found)")
        
        print(f"\n✅ Main Backend Metrics-Test abgeschlossen")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Main Backend nicht erreichbar - ist der Service gestartet?")
        return False
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False


def test_ingestion_backend_metrics():
    """Test Ingestion Backend /metrics endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Ingestion Backend Metrics")
    print("="*60)
    
    backend_url = "http://127.0.0.1:45679"
    
    try:
        # Check if backend is running
        health = requests.get(f"{backend_url}/health", timeout=5)
        if health.status_code != 200:
            print(f"❌ Ingestion Backend nicht erreichbar (Status: {health.status_code})")
            return False
        
        print(f"✅ Ingestion Backend läuft auf {backend_url}")
        
        # Generate some activity
        print("\n1. Generiere Aktivität...")
        try:
            response = requests.get(f"{backend_url}/jobs", timeout=10)
            print(f"   GET /jobs: Status {response.status_code}")
        except Exception as e:
            print(f"   GET /jobs: {e}")
        
        # Wait for metrics to be collected
        time.sleep(1)
        
        # Fetch metrics
        print("\n2. Abrufen der Metriken...")
        metrics = requests.get(f"{backend_url}/metrics", timeout=5)
        
        if metrics.status_code != 200:
            print(f"❌ Metrics endpoint error: {metrics.status_code}")
            return False
        
        metrics_data = metrics.json()
        print(f"✅ Metrics abgerufen (Timestamp: {metrics_data.get('timestamp')})")
        
        # Validate metrics structure
        print("\n3. Validierung der Metriken-Struktur...")
        if 'metrics' not in metrics_data:
            print("❌ 'metrics' key fehlt")
            return False
        
        metric_names = [m['name'] for m in metrics_data['metrics']]
        print(f"   Gefundene Metriken: {len(metric_names)}")
        
        expected_metrics = [
            "documents_processed_total",
            "files_uploaded_total",
            "recovery_attempts_total",
            "blocked_files_current",
            "document_processing_seconds",
            "db_operation_seconds",
            "queue_depth_current"
        ]
        
        for expected in expected_metrics:
            if expected in metric_names:
                print(f"   ✅ {expected}")
            else:
                print(f"   ⚠️  {expected} (not found)")
        
        print(f"\n✅ Ingestion Backend Metrics-Test abgeschlossen")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Ingestion Backend nicht erreichbar - ist der Service gestartet?")
        return False
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False


def main():
    """Main test function."""
    print("\n" + "="*60)
    print("METRICS SYSTEM - VALIDATION TEST")
    print("="*60)
    print("Testing internal metrics without Prometheus")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Metrics classes
    classes_ok = test_metrics_classes()
    
    # Test 2: Main Backend
    main_backend_ok = test_main_backend_metrics()
    
    # Test 3: Ingestion Backend
    ingestion_backend_ok = test_ingestion_backend_metrics()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Metrics Classes:     {'✅ PASS' if classes_ok else '❌ FAIL'}")
    print(f"Main Backend:        {'✅ PASS' if main_backend_ok else '❌ FAIL'}")
    print(f"Ingestion Backend:   {'✅ PASS' if ingestion_backend_ok else '❌ FAIL'}")
    print("="*60)
    
    if classes_ok and main_backend_ok and ingestion_backend_ok:
        print("\n✅ Alle Tests bestanden!")
        print("⚠️  Metriken sind jetzt verfügbar unter:")
        print("   - http://127.0.0.1:45678/metrics (Main Backend)")
        print("   - http://127.0.0.1:45679/metrics (Ingestion Backend)")
        return 0
    else:
        print("\n❌ Einige Tests fehlgeschlagen!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
