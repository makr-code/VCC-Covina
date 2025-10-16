"""
Upload Performance Comparison

Compares Chunked HTTP vs. WebSocket upload performance.

Author: Covina Development Team
Created: 15. Oktober 2025
"""

import subprocess
import time
import sys
from pathlib import Path

# Test file
TEST_FILE = "C:/Temp/test_ws_10mb.bin"

# Test configurations
TESTS = [
    {
        "name": "Chunked HTTP (256KB chunks)",
        "command": ["python", "scripts/client_chunked_upload.py", TEST_FILE, "--chunk-size", "256KB"]
    },
    {
        "name": "WebSocket (64KB chunks)",
        "command": ["python", "scripts/client_websocket_upload.py", TEST_FILE, "--chunk-size", "64KB"]
    },
    {
        "name": "WebSocket (256KB chunks)",
        "command": ["python", "scripts/client_websocket_upload.py", TEST_FILE, "--chunk-size", "256KB"]
    }
]

def run_test(test):
    """Run single upload test"""
    print(f"\n{'='*60}")
    print(f"  {test['name']}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            test['command'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(result.stdout)
            return {
                "name": test['name'],
                "status": "SUCCESS",
                "duration": duration,
                "output": result.stdout
            }
        else:
            print(f"❌ FAILED\n{result.stderr}")
            return {
                "name": test['name'],
                "status": "FAILED",
                "duration": duration,
                "error": result.stderr
            }
    
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT (>60s)")
        return {
            "name": test['name'],
            "status": "TIMEOUT",
            "duration": 60.0
        }
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {
            "name": test['name'],
            "status": "ERROR",
            "error": str(e)
        }

def main():
    """Run all tests and compare results"""
    # Check test file
    if not Path(TEST_FILE).exists():
        print(f"❌ Test file not found: {TEST_FILE}")
        print(f"   Create with: python -c \"import os; data = os.urandom(10*1024*1024); open('{TEST_FILE}', 'wb').write(data)\"")
        return 1
    
    file_size = Path(TEST_FILE).stat().st_size
    
    print("\n" + "="*60)
    print("  UPLOAD PERFORMANCE COMPARISON")
    print("="*60)
    print(f"Test File: {Path(TEST_FILE).name}")
    print(f"File Size: {file_size / 1024 / 1024:.2f} MB")
    print("="*60)
    
    # Run tests
    results = []
    for test in TESTS:
        result = run_test(test)
        results.append(result)
        time.sleep(2)  # Wait between tests
    
    # Print summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    
    for result in results:
        status_emoji = {
            "SUCCESS": "✅",
            "FAILED": "❌",
            "TIMEOUT": "⏱️",
            "ERROR": "❌"
        }.get(result['status'], "❓")
        
        print(f"{status_emoji} {result['name']:40s} {result['duration']:.2f}s")
    
    # Find fastest
    successful = [r for r in results if r['status'] == 'SUCCESS']
    if successful:
        fastest = min(successful, key=lambda r: r['duration'])
        print(f"\n🏆 Fastest: {fastest['name']} ({fastest['duration']:.2f}s)")
    
    print("="*60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
