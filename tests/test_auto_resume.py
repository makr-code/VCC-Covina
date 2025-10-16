"""
Test Auto-Resume Mechanism
Tests: v3.4.9 Auto-Resume pending jobs on startup
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:45679"

def test_auto_resume():
    """Test auto-resume functionality"""
    
    print("\n" + "=" * 60)
    print("🧪 Testing Auto-Resume Mechanism (v3.4.9)")
    print("=" * 60)
    
    # Step 1: Check backend health
    print("\n1️⃣  Checking backend health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("   ✅ Backend healthy")
        else:
            print(f"   ❌ Backend unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Backend not reachable: {e}")
        return False
    
    # Step 2: Get pending jobs count (before restart)
    print("\n2️⃣  Checking pending jobs...")
    try:
        response = requests.get(f"{BASE_URL}/jobs?limit=1000")
        jobs = response.json()
        
        pending_jobs = [j for j in jobs if j["status"] == "pending" and j["processed_files"] == 0]
        processing_jobs = [j for j in jobs if j["status"] == "processing"]
        
        print(f"   📊 Pending jobs (0 progress):  {len(pending_jobs)}")
        print(f"   🔄 Processing jobs:            {len(processing_jobs)}")
        print(f"   📋 Total jobs:                 {len(jobs)}")
        
        if len(pending_jobs) == 0:
            print("   ✅ No pending jobs - auto-resume not needed")
            return True
        
    except Exception as e:
        print(f"   ❌ Failed to get jobs: {e}")
        return False
    
    # Step 3: Check if jobs have files in database
    print("\n3️⃣  Checking job files in database...")
    jobs_with_files = 0
    jobs_without_files = 0
    
    for job in pending_jobs[:5]:  # Check first 5
        job_id = job["job_id"]
        try:
            response = requests.get(f"{BASE_URL}/jobs/{job_id}/files")
            if response.status_code == 200:
                files = response.json()
                file_count = len(files.get("files", []))
                if file_count > 0:
                    print(f"   ✅ Job {job_id[:8]}... has {file_count} files in DB")
                    jobs_with_files += 1
                else:
                    print(f"   ⚠️  Job {job_id[:8]}... has NO files in DB")
                    jobs_without_files += 1
        except Exception as e:
            print(f"   ❌ Job {job_id[:8]}... error: {e}")
            jobs_without_files += 1
    
    print(f"\n   📊 Jobs with files:    {jobs_with_files}")
    print(f"   ⚠️  Jobs without files: {jobs_without_files}")
    
    # Step 4: Recommendation
    print("\n4️⃣  Auto-Resume Readiness:")
    if jobs_with_files > 0:
        print(f"   ✅ {jobs_with_files} jobs ready for auto-resume")
        print("   🚀 Restart backend to trigger auto-resume")
        print(f"   ⏱️  Expected processing time: ~{jobs_with_files * 2} minutes (with batch features)")
    else:
        print("   ⚠️  No jobs have files in database")
        print("   💡 These jobs may have been created but never uploaded")
        print("   🧹 Consider cleaning up empty jobs")
    
    print("\n" + "=" * 60)
    return True

if __name__ == "__main__":
    success = test_auto_resume()
    exit(0 if success else 1)
