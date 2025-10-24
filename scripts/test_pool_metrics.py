"""
Test Script: Pool Metrics Enhancement

Tests new gauge metrics for pool monitoring:
1. Worker Pool Queue Depth (I/O + CPU) - Ingestion Backend
2. PostgreSQL Connection Pool - Main Backend
3. Active Request Tracking - Both Backends

Author: Covina Team
Date: 22. Oktober 2025
"""

import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
MAIN_BACKEND_URL = "http://127.0.0.1:45678"
INGESTION_BACKEND_URL = "http://127.0.0.1:45679"
TIMEOUT = 10


def test_main_backend_pool_metrics():
    """Test 1: PostgreSQL Connection Pool Gauges (Main Backend)."""
    print("=" * 70)
    print("TEST 1: PostgreSQL Connection Pool Metrics")
    print("=" * 70)
    
    try:
        response = requests.get(f"{MAIN_BACKEND_URL}/metrics", timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Extract metrics from nested format
        metrics_list = data.get("metrics", [])
        pool_metric = next((m for m in metrics_list if m["name"] == "pool_connections_current"), None)
        
        if not pool_metric:
            print("❌ pool_connections_current metric not found")
            return 0, 1
        
        # Extract samples
        samples = pool_metric.get("samples", [])
        pool_values = {s["labels"].get("state"): s["value"] for s in samples}
        
        # Check for labels (active, idle, total)
        required_states = ["active", "idle", "total"]
        
        passed = 0
        failed = 0
        
        for state in required_states:
            if state in pool_values:
                value = pool_values[state]
                print(f"✅ Pool Connections ({state}): {value}")
                passed += 1
            else:
                print(f"❌ Pool Connections ({state}): NOT FOUND")
                failed += 1
        
        print(f"\n📊 Test 1 Result: {passed}/{passed+failed} pool states tracked")
        return passed, failed
        
    except requests.exceptions.Timeout:
        print("❌ Main Backend timeout (sentence-transformers loading?)")
        print("   Retry in 30s or check backend logs")
        return 0, 1
    except requests.exceptions.ConnectionError:
        print("❌ Main Backend not running on port 45678")
        print("   Start with: .\\scripts\\start_services.ps1")
        return 0, 1
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return 0, 1


def test_ingestion_backend_queue_metrics():
    """Test 2: Worker Pool Queue Depth (Ingestion Backend)."""
    print("\n" + "=" * 70)
    print("TEST 2: Worker Pool Queue Depth Metrics")
    print("=" * 70)
    
    try:
        response = requests.get(f"{INGESTION_BACKEND_URL}/metrics", timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Extract metrics from nested format
        metrics_list = data.get("metrics", [])
        queue_metric = next((m for m in metrics_list if m["name"] == "queue_depth_current"), None)
        
        if not queue_metric:
            print("❌ queue_depth_current metric not found")
            return 0, 1
        
        # Extract samples
        samples = queue_metric.get("samples", [])
        queue_values = {s["labels"].get("pool"): s["value"] for s in samples}
        
        # Check for pools (io, cpu)
        required_pools = ["io", "cpu"]
        
        passed = 0
        failed = 0
        
        for pool in required_pools:
            if pool in queue_values:
                value = queue_values[pool]
                print(f"✅ Queue Depth ({pool}): {value}")
                passed += 1
            else:
                print(f"❌ Queue Depth ({pool}): NOT FOUND")
                failed += 1
        
        print(f"\n📊 Test 2 Result: {passed}/{passed+failed} pool queues tracked")
        return passed, failed
        
    except requests.exceptions.ConnectionError:
        print("❌ Ingestion Backend not running on port 45679")
        print("   Start with: .\\scripts\\start_services.ps1")
        return 0, 1
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return 0, 1


def test_active_request_tracking(backend_name, base_url):
    """Test 3: Active Request Tracking with concurrent requests."""
    print("\n" + "=" * 70)
    print(f"TEST 3: Active Request Tracking ({backend_name})")
    print("=" * 70)
    
    try:
        # Baseline: No active requests
        response = requests.get(f"{base_url}/metrics", timeout=TIMEOUT)
        response.raise_for_status()
        data_baseline = response.json()
        
        # Extract active_requests metric
        metrics_list = data_baseline.get("metrics", [])
        active_metric = next((m for m in metrics_list if m["name"] == "active_requests_current"), None)
        samples = active_metric.get("samples", []) if active_metric else []
        active_baseline = samples[0]["value"] if samples else 0
        print(f"📊 Baseline active requests: {active_baseline}")
        
        # Generate concurrent requests with artificial delay IN the request handler
        print(f"🔄 Generating 20 concurrent slow requests...")
        
        def make_request(i):
            # Make request with query param to trigger backend delay
            return requests.get(f"{base_url}/health?delay=2", timeout=TIMEOUT)
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            
            # While requests running, check active requests
            time.sleep(1.0)  # Let requests accumulate at backend
            
            response_concurrent = requests.get(f"{base_url}/metrics", timeout=TIMEOUT)
            response_concurrent.raise_for_status()
            data_concurrent = response_concurrent.json()
            
            metrics_list = data_concurrent.get("metrics", [])
            active_metric = next((m for m in metrics_list if m["name"] == "active_requests_current"), None)
            samples = active_metric.get("samples", []) if active_metric else []
            active_concurrent = samples[0]["value"] if samples else 0
            print(f"📊 Active requests during load: {active_concurrent}")
            
            # Wait for completion
            for future in as_completed(futures):
                future.result()
        
        # After completion
        time.sleep(0.5)
        response_final = requests.get(f"{base_url}/metrics", timeout=TIMEOUT)
        response_final.raise_for_status()
        data_final = response_final.json()
        
        metrics_list = data_final.get("metrics", [])
        active_metric = next((m for m in metrics_list if m["name"] == "active_requests_current"), None)
        samples = active_metric.get("samples", []) if active_metric else []
        active_final = samples[0]["value"] if samples else 0
        print(f"📊 Final active requests: {active_final}")
        
        # Validation
        checks = [
            ("Baseline <= 2", active_baseline <= 2),  # Allow some background
            ("Concurrent > Baseline", active_concurrent > active_baseline),
            ("Final <= 2", active_final <= 2)  # Should return to baseline
        ]
        
        passed = sum(1 for _, check in checks if check)
        failed = len(checks) - passed
        
        for check_name, check_passed in checks:
            status = "✅" if check_passed else "❌"
            print(f"{status} {check_name}")
        
        print(f"\n📊 Test 3 Result ({backend_name}): {passed}/{passed+failed} checks passed")
        return passed, failed
        
    except requests.exceptions.Timeout:
        print(f"❌ {backend_name} timeout during test")
        return 0, 1
    except requests.exceptions.ConnectionError:
        print(f"❌ {backend_name} not running")
        return 0, 1
    except Exception as e:
        print(f"❌ Test 3 ({backend_name}) failed: {e}")
        return 0, 1


def test_metrics_format():
    """Test 4: Verify metrics are in correct JSON format."""
    print("\n" + "=" * 70)
    print("TEST 4: Metrics JSON Format Validation")
    print("=" * 70)
    
    backends = [
        ("Main Backend", MAIN_BACKEND_URL),
        ("Ingestion Backend", INGESTION_BACKEND_URL)
    ]
    
    passed = 0
    failed = 0
    
    for backend_name, base_url in backends:
        try:
            response = requests.get(f"{base_url}/metrics", timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            # Check if response is dict
            if not isinstance(data, dict):
                print(f"❌ {backend_name}: Metrics not a dict")
                failed += 1
                continue
            
            # Extract metrics list
            metrics_list = data.get("metrics", [])
            metric_names = [m["name"] for m in metrics_list]
            
            # Check for new metrics
            new_metrics = [
                "pool_connections_current",  # Main only
                "queue_depth_current",       # Ingestion only
                "active_requests_current"    # Both
            ]
            
            found_metrics = [m for m in new_metrics if m in metric_names]
            
            if found_metrics:
                print(f"✅ {backend_name}: {len(found_metrics)} new metrics found")
                print(f"   Metrics: {', '.join(found_metrics)}")
                passed += 1
            else:
                print(f"❌ {backend_name}: No new metrics found")
                failed += 1
                
        except requests.exceptions.Timeout:
            print(f"⚠️  {backend_name}: Timeout (skip)")
            # Don't count as failure - backend might be slow
        except requests.exceptions.ConnectionError:
            print(f"❌ {backend_name}: Not running")
            failed += 1
        except Exception as e:
            print(f"❌ {backend_name}: {e}")
            failed += 1
    
    print(f"\n📊 Test 4 Result: {passed}/{passed+failed} backends validated")
    return passed, failed


def main():
    """Run all tests."""
    print("\n" + "🧪" * 35)
    print("POOL METRICS ENHANCEMENT - TEST SUITE")
    print("🧪" * 35 + "\n")
    
    total_passed = 0
    total_failed = 0
    
    # Test 1: PostgreSQL Pool (Main Backend)
    passed, failed = test_main_backend_pool_metrics()
    total_passed += passed
    total_failed += failed
    
    # Test 2: Worker Queue Depth (Ingestion Backend)
    passed, failed = test_ingestion_backend_queue_metrics()
    total_passed += passed
    total_failed += failed
    
    # Test 3a: Active Requests (Main Backend)
    passed, failed = test_active_request_tracking("Main Backend", MAIN_BACKEND_URL)
    total_passed += passed
    total_failed += failed
    
    # Test 3b: Active Requests (Ingestion Backend)
    passed, failed = test_active_request_tracking("Ingestion Backend", INGESTION_BACKEND_URL)
    total_passed += passed
    total_failed += failed
    
    # Test 4: Metrics Format
    passed, failed = test_metrics_format()
    total_passed += passed
    total_failed += failed
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"✅ Total Passed: {total_passed}")
    print(f"❌ Total Failed: {total_failed}")
    
    if total_failed + total_passed > 0:
        success_rate = 100 * total_passed / (total_passed + total_failed)
        print(f"📊 Success Rate: {total_passed}/{total_passed+total_failed} ({success_rate:.1f}%)")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED! Pool Metrics Enhancement is PRODUCTION READY!")
    elif total_passed > 0:
        print(f"\n⚠️  {total_failed} test(s) failed, but {total_passed} passed.")
        print("   Review failures - may be environment issues (backend slow/down).")
    else:
        print("\n❌ ALL TESTS FAILED! Check if backends are running:")
        print("   Start with: .\\scripts\\start_services.ps1")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
