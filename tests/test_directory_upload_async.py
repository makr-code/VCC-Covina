#!/usr/bin/env python3
"""
Directory Upload Async Test

Tests the new async directory upload with instant response.
"""

import time
import sys
import requests


def test_directory_upload_async(directory_path: str):
    """Test async directory upload"""
    
    print("\n" + "="*60)
    print("🧪 ASYNC DIRECTORY UPLOAD TEST")
    print("="*60)
    
    backend_url = "http://127.0.0.1:45679"
    
    # Test 1: Upload directory (instant response expected!)
    print(f"\n📂 Uploading directory: {directory_path}")
    print("   Expected: <50ms response with scan_job_id")
    
    start = time.time()
    try:
        response = requests.post(
            f"{backend_url}/upload/directory",
            data={'directory_path': directory_path, 'chunk_size': 50},
            timeout=5.0  # Should be instant!
        )
        elapsed_ms = (time.time() - start) * 1000
        
        print(f"   ✅ Response Time: {elapsed_ms:.1f}ms")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: 200 OK")
            print(f"   📋 Response:")
            print(f"      - scan_job_id: {result.get('scan_job_id')}")
            print(f"      - status: {result.get('status')}")
            print(f"      - directory_path: {result.get('directory_path')}")
            print(f"      - message: {result.get('message')}")
            
            scan_job_id = result.get('scan_job_id')
            
            # Test 2: Poll scan status
            print(f"\n📊 Polling scan status: {scan_job_id}")
            print("   Polling every 2s until complete...")
            
            poll_start = time.time()
            poll_count = 0
            last_files = 0
            
            while True:
                poll_count += 1
                
                try:
                    status_response = requests.get(
                        f"{backend_url}/scan/{scan_job_id}",
                        timeout=5.0
                    )
                    
                    if status_response.status_code == 200:
                        status = status_response.json()
                        
                        scan_status = status.get('status')
                        files_found = status.get('files_found', 0)
                        upload_jobs = status.get('upload_jobs_created', 0)
                        elapsed = status.get('elapsed_time', 0)
                        error = status.get('error')
                        
                        # Show progress
                        if files_found != last_files or poll_count == 1:
                            print(f"   [{poll_count}] Status: {scan_status}, Files: {files_found}, Jobs: {upload_jobs}, Elapsed: {elapsed:.1f}s")
                            last_files = files_found
                        
                        # Check if done
                        if scan_status == "completed":
                            print(f"\n   ✅ Scan COMPLETED!")
                            print(f"      - Files found: {files_found}")
                            print(f"      - Upload jobs: {upload_jobs}")
                            print(f"      - Job IDs: {status.get('upload_job_ids', [])[:3]}...")  # First 3
                            print(f"      - Total time: {elapsed:.1f}s")
                            print(f"      - Poll requests: {poll_count}")
                            break
                        
                        elif scan_status == "error":
                            print(f"\n   ❌ Scan ERROR: {error}")
                            break
                        
                        # Wait before next poll
                        time.sleep(2)
                    
                    else:
                        print(f"   ❌ Status check failed: {status_response.status_code}")
                        break
                
                except Exception as e:
                    print(f"   ❌ Status poll error: {e}")
                    break
                
                # Safety: Max 60 polls (2 minutes)
                if poll_count >= 60:
                    print(f"   ⚠️ Timeout: Scan took >2 minutes")
                    break
        
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    except requests.exceptions.Timeout:
        elapsed_ms = (time.time() - start) * 1000
        print(f"   ❌ TIMEOUT after {elapsed_ms:.1f}ms (should be <50ms!)")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60 + "\n")


def test_backend_health():
    """Test backend health"""
    print("\n🏥 Testing Backend Health...")
    
    try:
        response = requests.get("http://127.0.0.1:45679/health", timeout=2.0)
        if response.status_code == 200:
            print("   ✅ Ingestion Backend: HEALTHY")
            return True
        else:
            print(f"   ❌ Backend unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Backend not reachable: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_directory_upload_async.py <directory_path>")
        print("\nExample:")
        print("  python test_directory_upload_async.py C:/test/small_dir")
        print("  python test_directory_upload_async.py C:/test/large_dir")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    
    # Check backend first
    if not test_backend_health():
        print("\n❌ Backend not available. Start with:")
        print("   python ingestion_backend.py")
        sys.exit(1)
    
    # Run test
    test_directory_upload_async(directory_path)
