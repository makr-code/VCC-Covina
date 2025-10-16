"""
Large File Performance Test

Tests upload performance with 100 MB file using different chunk sizes.

Author: Covina Development Team
Created: 15. Oktober 2025
"""

import subprocess
import time
import sys
from pathlib import Path

TEST_FILE = "C:/Temp/test_100mb.bin"

TESTS = [
    # Chunked HTTP tests
    {"name": "Chunked HTTP (256KB)", "cmd": ["python", "scripts/client_chunked_upload.py", TEST_FILE, "--chunk-size", "256KB"]},
    {"name": "Chunked HTTP (1MB)", "cmd": ["python", "scripts/client_chunked_upload.py", TEST_FILE, "--chunk-size", "1MB"]},
    {"name": "Chunked HTTP (5MB)", "cmd": ["python", "scripts/client_chunked_upload.py", TEST_FILE, "--chunk-size", "5MB"]},
    
    # WebSocket tests
    {"name": "WebSocket (64KB)", "cmd": ["python", "scripts/client_websocket_upload.py", TEST_FILE, "--chunk-size", "64KB"]},
    {"name": "WebSocket (256KB)", "cmd": ["python", "scripts/client_websocket_upload.py", TEST_FILE, "--chunk-size", "256KB"]},
    {"name": "WebSocket (1MB)", "cmd": ["python", "scripts/client_websocket_upload.py", TEST_FILE, "--chunk-size", "1MB"]},
]

def run_test(test):
    """Run single test"""
    print(f"\n{'='*70}")
    print(f"  {test['name']}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            test['cmd'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            # Extract throughput from output
            throughput = 100 / duration  # MB/s
            return {
                "name": test['name'],
                "status": "SUCCESS",
                "duration": duration,
                "throughput": throughput
            }
        else:
            print(f"❌ FAILED")
            print(result.stderr[:500])
            return {
                "name": test['name'],
                "status": "FAILED",
                "duration": duration
            }
    
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT (>120s)")
        return {"name": test['name'], "status": "TIMEOUT", "duration": 120.0}
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {"name": test['name'], "status": "ERROR", "error": str(e)}

def main():
    """Run all tests"""
    if not Path(TEST_FILE).exists():
        print(f"❌ Test file not found: {TEST_FILE}")
        return 1
    
    file_size = Path(TEST_FILE).stat().st_size / 1024 / 1024
    
    print("\n" + "="*70)
    print("  LARGE FILE PERFORMANCE TEST")
    print("="*70)
    print(f"Test File: {Path(TEST_FILE).name}")
    print(f"File Size: {file_size:.2f} MB")
    print(f"Tests: {len(TESTS)}")
    print("="*70)
    
    results = []
    for test in TESTS:
        result = run_test(test)
        results.append(result)
        time.sleep(3)  # Wait between tests
    
    # Print summary
    print("\n" + "="*70)
    print("  PERFORMANCE SUMMARY")
    print("="*70)
    print(f"{'Method':<30} {'Status':<10} {'Duration':<12} {'Throughput'}")
    print("-"*70)
    
    for result in results:
        status_emoji = {"SUCCESS": "✅", "FAILED": "❌", "TIMEOUT": "⏱️"}.get(result['status'], "❓")
        
        if result['status'] == 'SUCCESS':
            print(f"{result['name']:<30} {status_emoji} {result['status']:<8} {result['duration']:>8.2f}s    {result['throughput']:>6.2f} MB/s")
        else:
            print(f"{result['name']:<30} {status_emoji} {result['status']:<8} {result['duration']:>8.2f}s")
    
    # Find fastest
    successful = [r for r in results if r['status'] == 'SUCCESS']
    if successful:
        fastest = min(successful, key=lambda r: r['duration'])
        print(f"\n🏆 Fastest: {fastest['name']} ({fastest['duration']:.2f}s, {fastest['throughput']:.2f} MB/s)")
    
    print("="*70 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
