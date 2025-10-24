#!/usr/bin/env python3
"""
Rate Limiting Test Script
Tests slowapi rate limiting on Covina backends.
"""

import requests
import time
from datetime import datetime

MAIN_BACKEND = "http://127.0.0.1:45678"
INGESTION_BACKEND = "http://127.0.0.1:45679"

def test_rate_limit(url: str, max_requests: int, expected_limit: int, test_name: str):
    """
    Test rate limiting by sending max_requests and expecting rejection after expected_limit.
    """
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"URL: {url}")
    print(f"Expected Limit: {expected_limit}/minute")
    print(f"{'='*70}\n")
    
    success_count = 0
    rate_limited_count = 0
    
    start_time = time.time()
    
    for i in range(1, max_requests + 1):
        try:
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                success_count += 1
                print(f"[{i:2d}] ✅ OK (200)")
            elif response.status_code == 429:
                rate_limited_count += 1
                retry_after = response.headers.get('Retry-After', 'N/A')
                print(f"[{i:2d}] 🛑 RATE LIMITED (429) - Retry-After: {retry_after}s")
                
                if rate_limited_count == 1:
                    print(f"\n⚠️  Rate limit triggered after {success_count} requests")
                    print(f"   Expected: {expected_limit}, Actual: {success_count}")
                    
                    if success_count <= expected_limit + 2:  # Allow 2 requests tolerance
                        print(f"   ✅ Rate limiting working correctly!\n")
                    else:
                        print(f"   ❌ Rate limit higher than expected!\n")
                    
                    break
            else:
                print(f"[{i:2d}] ⚠️  Unexpected status: {response.status_code}")
        
        except requests.exceptions.Timeout:
            print(f"[{i:2d}] ⏱️  Timeout")
        except Exception as e:
            print(f"[{i:2d}] ❌ Error: {e}")
        
        time.sleep(0.1)  # Small delay to avoid overwhelming
    
    elapsed = time.time() - start_time
    
    print(f"\n📊 Summary:")
    print(f"   Successful: {success_count}")
    print(f"   Rate Limited: {rate_limited_count}")
    print(f"   Duration: {elapsed:.1f}s")
    
    return success_count, rate_limited_count

def main():
    print(f"\n🔒 RATE LIMITING TEST")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test 1: Main Backend - Semantic Search (50/minute limit)
    test_rate_limit(
        url=f"{MAIN_BACKEND}/query/semantic?query=test&limit=5",
        max_requests=60,
        expected_limit=50,
        test_name="Main Backend - Semantic Search (50/min)"
    )
    
    # Wait 5 seconds before next test
    print("\n⏳ Waiting 5 seconds before next test...")
    time.sleep(5)
    
    # Test 2: Ingestion Backend - Job Listing (30/minute limit)
    test_rate_limit(
        url=f"{INGESTION_BACKEND}/jobs?limit=10",
        max_requests=40,
        expected_limit=30,
        test_name="Ingestion Backend - Job Listing (30/min)"
    )
    
    print(f"\n{'='*70}")
    print("✅ Rate limiting tests completed!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
