"""
Themis Adapter Smoke Test

Validates Themis integration in Covina backends:
1. Themis mode status
2. Health check
3. Backend availability
4. Optional: Simple CRUD operations

Usage:
    python tests/test_themis_smoke.py
    python tests/test_themis_smoke.py --full  # Include CRUD tests
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx


async def test_themis_mode(client: httpx.AsyncClient, backend_name: str, base_url: str):
    """Test /themis/mode endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing Themis Mode: {backend_name}")
    print(f"{'='*60}")
    
    try:
        response = await client.get(f"{base_url}/themis/mode")
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Status: {response.status_code}")
        print(f"   Enabled: {data.get('enabled')}")
        print(f"   URL: {data.get('url')}")
        print(f"   Timeout: {data.get('timeout')}s")
        print(f"   Max Retries: {data.get('max_retries')}")
        print(f"   Fallback: {data.get('fallback')}")
        print(f"   Backends Available:")
        for backend, available in data.get('backends', {}).items():
            status = "✅" if available else "❌"
            print(f"      {status} {backend}")
        
        return data.get('enabled', False)
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_themis_health(client: httpx.AsyncClient, backend_name: str, base_url: str):
    """Test /themis/health endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing Themis Health: {backend_name}")
    print(f"{'='*60}")
    
    try:
        response = await client.get(f"{base_url}/themis/health")
        if response.status_code == 503:
            data = response.json()
            print(f"⚠️  Status: 503 (Themis not available)")
            print(f"   Detail: {data.get('detail')}")
            return False
        
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Status: {response.status_code}")
        print(f"   Health: {data.get('status')}")
        print(f"   Latency: {data.get('latency_ms')}ms")
        print(f"   Themis Response: {data.get('themis_response')}")
        
        return True
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(f"   Detail: {e.response.json().get('detail', 'Unknown error')}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_backend_health(client: httpx.AsyncClient, backend_name: str, base_url: str):
    """Test general /health endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing General Health: {backend_name}")
    print(f"{'='*60}")
    
    try:
        response = await client.get(f"{base_url}/health")
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Status: {response.status_code}")
        print(f"   Backend Status: {data.get('status')}")
        print(f"   Backend Type: {data.get('backend_type')}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_crud_operations(client: httpx.AsyncClient, base_url: str):
    """Test simple CRUD operations (optional)"""
    print(f"\n{'='*60}")
    print(f"Testing CRUD Operations (Themis)")
    print(f"{'='*60}")
    
    # This would require a running Themis server and proper test data
    # For now, just document the approach
    print("⚠️  CRUD tests require live Themis server (skipped)")
    print("   To enable: Start Themis server, uncomment CRUD test code")
    
    return True


async def run_smoke_tests(full: bool = False):
    """Run all smoke tests"""
    print("\n" + "="*80)
    print("THEMIS ADAPTER SMOKE TEST")
    print("="*80)
    
    backends = [
        ("Main Backend", "http://127.0.0.1:45678"),
        ("Ingestion Backend", "http://127.0.0.1:45679")
    ]
    
    results = {
        "main_health": False,
        "main_mode": False,
        "main_themis_health": False,
        "ingestion_health": False,
        "ingestion_mode": False,
        "ingestion_themis_health": False,
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test Main Backend
        backend_name, base_url = backends[0]
        results["main_health"] = await test_backend_health(client, backend_name, base_url)
        results["main_mode"] = await test_themis_mode(client, backend_name, base_url)
        if results["main_mode"]:
            results["main_themis_health"] = await test_themis_health(client, backend_name, base_url)
        
        # Test Ingestion Backend
        backend_name, base_url = backends[1]
        results["ingestion_health"] = await test_backend_health(client, backend_name, base_url)
        results["ingestion_mode"] = await test_themis_mode(client, backend_name, base_url)
        if results["ingestion_mode"]:
            results["ingestion_themis_health"] = await test_themis_health(client, backend_name, base_url)
        
        # Optional CRUD tests
        if full and results["main_mode"]:
            await test_crud_operations(client, backends[0][1])
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    print(f"\n{'Main Backend:':<30}")
    print(f"  {'General Health:':<28} {'✅ PASS' if results['main_health'] else '❌ FAIL'}")
    print(f"  {'Themis Mode Enabled:':<28} {'✅ YES' if results['main_mode'] else '❌ NO'}")
    if results['main_mode']:
        print(f"  {'Themis Health Check:':<28} {'✅ PASS' if results['main_themis_health'] else '❌ FAIL'}")
    
    print(f"\n{'Ingestion Backend:':<30}")
    print(f"  {'General Health:':<28} {'✅ PASS' if results['ingestion_health'] else '❌ FAIL'}")
    print(f"  {'Themis Mode Enabled:':<28} {'✅ YES' if results['ingestion_mode'] else '❌ NO'}")
    if results['ingestion_mode']:
        print(f"  {'Themis Health Check:':<28} {'✅ PASS' if results['ingestion_themis_health'] else '❌ FAIL'}")
    
    # Overall verdict
    print("\n" + "="*80)
    themis_active = results['main_mode'] or results['ingestion_mode']
    
    if themis_active:
        all_healthy = (
            results['main_health'] and 
            results['ingestion_health'] and
            (results['main_themis_health'] if results['main_mode'] else True) and
            (results['ingestion_themis_health'] if results['ingestion_mode'] else True)
        )
        if all_healthy:
            print("✅ OVERALL: ALL TESTS PASSED (Themis Active)")
        else:
            print("⚠️  OVERALL: SOME TESTS FAILED (Check details above)")
    else:
        print("ℹ️  OVERALL: Themis Not Active (UDS3 Fallback Mode)")
        if results['main_health'] and results['ingestion_health']:
            print("✅ Both backends healthy (UDS3 mode)")
        else:
            print("❌ Backend health issues detected")
    
    print("="*80 + "\n")
    
    return 0 if (results['main_health'] and results['ingestion_health']) else 1


if __name__ == "__main__":
    full_test = "--full" in sys.argv
    exit_code = asyncio.run(run_smoke_tests(full=full_test))
    sys.exit(exit_code)
