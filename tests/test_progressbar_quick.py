"""
Quick Test: Bulk Copy Progress Monitoring
==========================================

Tests the complete progressbar implementation:
1. Upload directory via API
2. Monitor bulk_copy_progress via polling
3. Display progress updates

Author: Covina Development Team
Date: 14. Oktober 2025, 16:30 Uhr
"""

import requests
import time
import json

BACKEND_URL = "http://127.0.0.1:45679"
TEST_DIR = r"C:\Temp\covina_test_progress"

def test_directory_upload():
    """Test directory upload with progress monitoring"""
    
    print("=" * 60)
    print("PROGRESSBAR TEST - Directory Upload")
    print("=" * 60)
    
    # Step 1: Start upload
    print(f"\n📤 Starting directory upload: {TEST_DIR}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/upload/directory",
            data={
                "directory_path": TEST_DIR,
                "chunk_size": 50
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
        
        data = response.json()
        scan_job_id = data["scan_job_id"]
        
        print(f"✅ Upload started successfully!")
        print(f"   Scan Job ID: {scan_job_id}")
        print(f"   Status: {data['status']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 2: Monitor progress
    print(f"\n📊 Monitoring bulk copy progress...")
    print(f"   Polling interval: 2 seconds")
    print(f"   Max duration: 60 seconds\n")
    
    for i in range(1, 31):  # 30 polls × 2s = 60s max
        try:
            response = requests.get(
                f"{BACKEND_URL}/scan/{scan_job_id}",
                timeout=2
            )
            
            if response.status_code != 200:
                print(f"[{i}] ⚠️  Status endpoint error: {response.status_code}")
                time.sleep(2)
                continue
            
            status = response.json()
            progress = status.get("bulk_copy_progress")
            
            if progress:
                # Progress data available!
                percent = progress.get("percent_complete", 0.0)
                files = progress.get("files_copied", 0)
                bytes_gb = progress.get("bytes_copied", 0) / (1024**3)
                rate = progress.get("copy_rate_mbps", 0.0)
                pstatus = progress.get("status", "unknown")
                
                # Color-coded output
                if pstatus == "completed":
                    symbol = "✅"
                elif pstatus == "copying":
                    symbol = "🔄"
                elif pstatus == "error":
                    symbol = "❌"
                else:
                    symbol = "⏳"
                
                print(
                    f"[{i:2d}] {symbol} Progress: {percent:5.1f}% | "
                    f"Files: {files:3d} | "
                    f"Data: {bytes_gb:6.2f} GB | "
                    f"Rate: {rate:6.1f} MB/s | "
                    f"Status: {pstatus}"
                )
                
                # Check if finished
                if pstatus in ["completed", "error"]:
                    print(f"\n🎉 Bulk copy finished! Status: {pstatus}")
                    break
            
            else:
                # No progress data yet
                print(f"[{i:2d}] ⏸️  No progress data yet (scan_status: {status.get('status')})")
            
        except Exception as e:
            print(f"[{i}] ❌ Error: {e}")
        
        time.sleep(2)
    
    # Step 3: Final status
    print(f"\n📋 Final Scan Status:")
    
    try:
        response = requests.get(f"{BACKEND_URL}/scan/{scan_job_id}", timeout=2)
        if response.status_code == 200:
            status = response.json()
            print(f"   Scan Job ID: {status['scan_job_id']}")
            print(f"   Status: {status['status']}")
            print(f"   Files Found: {status.get('files_found', 0)}")
            print(f"   Upload Jobs: {status.get('upload_jobs_created', 0)}")
            print(f"   Elapsed Time: {status.get('elapsed_time', 0):.1f}s")
            
            if status.get('error'):
                print(f"   ❌ Error: {status['error']}")
        else:
            print(f"   ⚠️  Could not retrieve final status")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_directory_upload()
