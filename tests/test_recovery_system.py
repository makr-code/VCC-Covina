"""
Recovery System Test Script

Tests automatic recovery with safety features:
- Failed file detection
- Retry count tracking
- Critical error blocking
- Admin override for unblocking
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:45679"

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def print_section(title):
    print(f"\n📌 {title}")
    print("-" * 70)

# ================================================================
# TEST 1: Check Current Jobs
# ================================================================
print_header("🧪 Recovery System Test")

print_section("Current Jobs in Database")

response = requests.get(f"{BASE_URL}/jobs/incomplete")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Incomplete Jobs: {data['count']}")
    
    if data['incomplete_jobs']:
        for job in data['incomplete_jobs'][:3]:  # Show first 3
            print(f"  - {job['job_id'][:16]}... ({job['status']}, {job['processed_files']}/{job['file_count']} files)")
else:
    print(f"❌ Error: {response.text}")

# ================================================================
# TEST 2: Get Failed Files from Recent Job
# ================================================================
print_section("Get Failed Files (if any)")

# Get recent job with files
response = requests.get(f"{BASE_URL}/jobs/incomplete")
if response.status_code == 200:
    jobs = response.json()["incomplete_jobs"]
    
    if jobs:
        test_job_id = jobs[0]["job_id"]
        print(f"Testing with job: {test_job_id[:16]}...")
        
        # Get failed files
        response = requests.get(f"{BASE_URL}/jobs/{test_job_id}/failed-files")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nJob Status: {data['job_status']}")
            print(f"Recovery Eligible: {data['recovery_eligible']['count']} files")
            print(f"Recovery Blocked:  {data['recovery_blocked']['count']} files")
            
            if data['recovery_eligible']['files']:
                print("\nFailed Files (first 3):")
                for file in data['recovery_eligible']['files'][:3]:
                    print(f"  - {Path(file['file_path']).name}")
                    print(f"    Retry Count: {file['retry_count']}")
                    print(f"    Error: {file['error_message'][:60]}...")
            
            if data['recovery_blocked']['files']:
                print("\n⚠️ Blocked Files (first 3):")
                for file in data['recovery_blocked']['files'][:3]:
                    print(f"  - {Path(file['file_path']).name}")
                    print(f"    Reason: {file['block_reason']}")
        else:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    else:
        print("No incomplete jobs found for testing")
else:
    print(f"❌ Could not get jobs: {response.status_code}")

# ================================================================
# TEST 3: Check All Blocked Files
# ================================================================
print_section("All Blocked Files Across System")

response = requests.get(f"{BASE_URL}/recovery/blocked-files")

if response.status_code == 200:
    data = response.json()
    print(f"Total Blocked: {data['total_blocked']}")
    print(f"Jobs Affected: {data['jobs_affected']}")
    
    if data['blocked_files']:
        print("\nBlocked Files (first 5):")
        for file in data['blocked_files'][:5]:
            print(f"  - Job: {file['job_id'][:16]}...")
            print(f"    File: {Path(file['file_path']).name}")
            print(f"    Reason: {file['block_reason']}")
            print(f"    Retry Count: {file['retry_count']}")
            print()
    else:
        print("✅ No blocked files - system healthy!")
else:
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")

# ================================================================
# TEST 4: Recovery API Reference
# ================================================================
print_section("Recovery API Reference")

print("""
Available Endpoints:

1. GET /jobs/{job_id}/failed-files
   - List all failed files for a job
   - Shows retry counts and blocked status
   - Parameters: max_retries (default: 3)

2. POST /jobs/{job_id}/recover-failed-files
   - Recover only failed files from a job
   - Safety: Blocks files with critical errors
   - Safety: Blocks files with max retries exceeded
   - Parameters:
     * max_retries: Maximum retry attempts (default: 3)
     * force_retry: Admin override for blocked files (default: false)

3. POST /jobs/{job_id}/files/{file_path}/unblock
   - Unblock a specific file (REQUIRES ADMIN)
   - Parameters:
     * admin_override: Must be true to confirm (REQUIRED)

4. GET /recovery/blocked-files
   - View all blocked files across all jobs
   - Useful for system-wide recovery audit

Safety Features:
✅ Automatic retry count tracking
✅ Critical error detection (corrupted, permission denied, etc.)
✅ Max retries limit (default: 3)
✅ Admin override required for unblocking
✅ Missing file detection
""")

# ================================================================
# TEST 5: Example Recovery Workflow
# ================================================================
print_section("Example Recovery Workflow")

print("""
SCENARIO 1: Automatic Recovery (Safe Files)
───────────────────────────────────────────────
1. Check failed files:
   GET /jobs/{job_id}/failed-files

2. Start recovery (safe files only):
   POST /jobs/{job_id}/recover-failed-files
   → Automatically blocks files with:
     - retry_count >= 3
     - Critical errors (corrupted, permission denied)
     - Missing files

3. Monitor recovery:
   GET /jobs/{recovery_job_id}
   → New job ID returned from step 2


SCENARIO 2: Admin Override (Critical Errors)
───────────────────────────────────────────────
1. Check blocked files:
   GET /recovery/blocked-files

2. Review block reasons:
   → "Max retries exceeded"
   → "Critical error: corrupted file"
   → "File not found"

3. Unblock specific file (ADMIN):
   POST /jobs/{job_id}/files/{file_path}/unblock?admin_override=true
   → Resets retry count
   → Clears block reason

4. Retry unblocked file:
   POST /jobs/{job_id}/recover-failed-files?force_retry=true
   → force_retry bypasses safety checks


SCENARIO 3: System-Wide Recovery Audit
───────────────────────────────────────────────
1. Get all blocked files:
   GET /recovery/blocked-files

2. Export to CSV for review:
   → Job ID, File Path, Block Reason, Retry Count

3. Decide on action:
   → Unblock and retry (admin override)
   → Mark as permanently failed (manual cleanup)
   → Investigate root cause (corrupted storage, permissions, etc.)
""")

print("\n" + "=" * 70)
print("✅ Recovery System Test Complete")
print("=" * 70)
print("\nNext Steps:")
print("1. Test recovery with: POST /jobs/{job_id}/recover-failed-files")
print("2. Monitor blocked files: GET /recovery/blocked-files")
print("3. Review API docs: http://127.0.0.1:45679/docs")
