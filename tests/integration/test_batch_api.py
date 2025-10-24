"""
Test Script for Covina Batch API Endpoints
Tests the Phase 3 Batch Operations integration.

Usage:
    1. Start Covina Main Backend: python main_backend.py
    2. Run this test: python test_batch_api.py
"""

import requests
import time
import json

BASE_URL = "http://127.0.0.1:45678"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def test_batch_status():
    """Test 1: Get Batch Operations Status"""
    print_section("TEST 1: Batch Operations Status")
    
    response = requests.get(f"{BASE_URL}/api/v1/batch/status", timeout=30)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Phase: {data['phase']}")
        print(f"✅ Status: {data['status']}")
        
        print("\n📊 Endpoints:")
        for endpoint, info in data['endpoints'].items():
            status = "✅" if info['available'] else "❌"
            print(f"   {status} {endpoint}")
            print(f"      Performance: {info['performance']}")
            print(f"      Batch Size: {info['recommended_batch_size']}")
        
        print("\n🔌 Backends:")
        for backend, available in data['backends'].items():
            status = "✅" if available else "❌"
            print(f"   {status} {backend}")
        
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_batch_get():
    """Test 2: Batch GET Documents"""
    print_section("TEST 2: Batch GET Documents")
    
    # First, get some real document IDs
    print("📋 Getting sample document IDs...")
    query_response = requests.post(
        f"{BASE_URL}/query/documents",
        json={
            "query_text": "vertrag",
            "limit": 5
        }
    )
    
    if query_response.status_code != 200:
        print("⚠️  Skipping: No documents found")
        return False
    
    documents = query_response.json().get('documents', [])
    if not documents:
        print("⚠️  Skipping: No documents returned")
        return False
    
    doc_ids = [doc['document_id'] for doc in documents[:3]]
    print(f"✅ Found {len(doc_ids)} document IDs: {doc_ids}")
    
    # Test Batch GET
    print("\n🚀 Testing Batch GET...")
    payload = {
        "document_ids": doc_ids,
        "fields": ["document_id", "classification", "file_path"],
        "include_metadata": True
    }
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/api/v1/batch/get",
        json=payload
    )
    elapsed_ms = (time.time() - start_time) * 1000
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success: {data['success']}")
        print(f"✅ Found: {data['found']} documents")
        print(f"✅ Not Found: {data['not_found']} documents")
        print(f"⏱️  Execution Time: {data['execution_time_ms']:.2f}ms (server)")
        print(f"⏱️  Total Time: {elapsed_ms:.2f}ms (including network)")
        print(f"📝 Performance Note: {data['performance_note']}")
        
        print("\n📄 Sample Document:")
        if data['documents']:
            print(json.dumps(data['documents'][0], indent=2))
        
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_batch_exists():
    """Test 3: Batch EXISTS Check"""
    print_section("TEST 3: Batch EXISTS Check")
    
    # Mix of real and fake IDs
    test_ids = [
        "b1ee0dbb70091a73",  # Real ID from production test
        "fake_id_1",
        "fake_id_2",
        "a1234567890abcde"   # Possibly real
    ]
    
    print(f"📋 Testing with {len(test_ids)} IDs (mix of real/fake)")
    
    payload = {
        "document_ids": test_ids
    }
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/api/v1/batch/exists",
        json=payload
    )
    elapsed_ms = (time.time() - start_time) * 1000
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success: {data['success']}")
        print(f"✅ Total: {data['total']} IDs")
        print(f"✅ Found: {data['found']} IDs")
        print(f"❌ Missing: {data['missing']} IDs")
        print(f"⏱️  Execution Time: {data['execution_time_ms']:.2f}ms (server)")
        print(f"⏱️  Total Time: {elapsed_ms:.2f}ms (including network)")
        print(f"📝 Performance Note: {data['performance_note']}")
        
        print("\n📊 Existence Results:")
        for doc_id, exists in data['exists'].items():
            status = "✅" if exists else "❌"
            print(f"   {status} {doc_id}: {exists}")
        
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_batch_search():
    """Test 4: Batch Semantic Search"""
    print_section("TEST 4: Batch Semantic Search")
    
    queries = [
        "Vertrag Lieferung",
        "Rechnung Buchhaltung",
        "DSGVO Datenschutz"
    ]
    
    print(f"📋 Testing with {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")
    
    payload = {
        "queries": queries,
        "top_k": 3,
        "similarity_threshold": 0.5
    }
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/api/v1/batch/search",
        json=payload
    )
    elapsed_ms = (time.time() - start_time) * 1000
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success: {data['success']}")
        print(f"✅ Total Queries: {data['total_queries']}")
        print(f"✅ Total Results: {data['total_results']}")
        print(f"⏱️  Execution Time: {data['execution_time_ms']:.2f}ms (server)")
        print(f"⏱️  Total Time: {elapsed_ms:.2f}ms (including network)")
        print(f"📝 Performance Note: {data['performance_note']}")
        
        print("\n📊 Search Results:")
        for result in data['results']:
            print(f"\n   Query: \"{result['query']}\"")
            print(f"   Matches: {result['count']}")
            if result['count'] > 0 and result['matches']:
                print(f"   Top Result: {result['matches'][0].get('document_id', 'N/A')}")
        
        return True
    elif response.status_code == 503:
        print(f"⚠️  Service Unavailable: {response.json()['detail']}")
        print("💡 ChromaDB or Embedding Model may not be available")
        return False
    else:
        print(f"❌ Failed: {response.text}")
        return False


def main():
    """Run all tests"""
    print("=" * 80)
    print(" COVINA BATCH API TEST SUITE")
    print(" Phase 3: Batch READ Operations")
    print("=" * 80)
    print(f"\n🎯 Target: {BASE_URL}")
    print("⏱️  Testing started...")
    
    # Check if backend is running
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=2)
        if health_response.status_code != 200:
            print("\n❌ FAILED: Backend not responding")
            print("💡 Start backend: python main_backend.py")
            return
    except requests.exceptions.RequestException as e:
        print(f"\n❌ FAILED: Cannot connect to backend")
        print(f"   Error: {e}")
        print("💡 Start backend: python main_backend.py")
        return
    
    print("✅ Backend is running\n")
    
    # Run tests
    results = []
    
    results.append(("Batch Status", test_batch_status()))
    time.sleep(0.5)
    
    results.append(("Batch GET", test_batch_get()))
    time.sleep(0.5)
    
    results.append(("Batch EXISTS", test_batch_exists()))
    time.sleep(0.5)
    
    results.append(("Batch SEARCH", test_batch_search()))
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed\n")
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {status}: {test_name}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Batch Operations (Phase 3) integration successful")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        print("💡 Check backend logs for details")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
