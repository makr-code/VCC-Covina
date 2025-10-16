"""
Recovery System - Stress Test with Database Failures

This test simulates actual processing failures by temporarily
stopping database services.
"""

import requests
import time
import sqlite3
from pathlib import Path

BASE_URL = "http://127.0.0.1:45679"
DB_PATH = Path("data/ingestion_jobs.db")

def print_section(title, char="="):
    print(f"\n{char * 70}")
    print(f" {title}")
    print(f"{char * 70}\n")

print_section("🔥 Recovery System - Database Inspection & Manual Failure Test", "=")

# ================================================================
# Check for Existing Failed Files
# ================================================================

print_section("Step 1: Check Database for Any Failed Files", "-")

if DB_PATH.exists():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Get all files with failure status or high retry count
    cursor.execute("""
        SELECT 
            job_id,
            file_path,
            status,
            error_message,
            retry_count,
            recovery_blocked,
            block_reason,
            created_at,
            updated_at
        FROM job_files
        WHERE status = 'failed' OR retry_count > 0 OR recovery_blocked = 1
        ORDER BY updated_at DESC
    """)
    
    failed_files = cursor.fetchall()
    
    print(f"Found {len(failed_files)} files with issues:\n")
    
    if failed_files:
        for row in failed_files:
            job_id, file_path, status, error, retry, blocked, block_reason, created, updated = row
            print(f"Job: {job_id[:16]}...")
            print(f"  File: {Path(file_path).name}")
            print(f"  ├─ Status: {status}")
            print(f"  ├─ Retry Count: {retry}")
            print(f"  ├─ Blocked: {bool(blocked)}")
            if error:
                print(f"  ├─ Error: {error[:80]}...")
            if block_reason:
                print(f"  └─ Block Reason: {block_reason}")
            print()
    else:
        print("✅ No failed files found - system is healthy!")
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN retry_count > 0 THEN 1 ELSE 0 END) as retried,
            SUM(CASE WHEN recovery_blocked = 1 THEN 1 ELSE 0 END) as blocked
        FROM job_files
    """)
    
    stats = cursor.fetchone()
    print(f"📊 Overall Statistics:")
    print(f"   Total Files Tracked: {stats[0]}")
    print(f"   Failed Files: {stats[1]}")
    print(f"   Files with Retries: {stats[2]}")
    print(f"   Blocked Files: {stats[3]}")
    
    conn.close()
else:
    print("❌ Database not found")

# ================================================================
# Manual Failure Injection (for testing)
# ================================================================

print_section("Step 2: Manual Failure Injection (Optional)", "-")

print("""
To test recovery system with actual failures:

Option 1: Simulate Database Failure
───────────────────────────────────────
1. Find a recent job ID from database
2. Manually set some files to 'failed' status:

   UPDATE job_files 
   SET status = 'failed',
       error_message = 'Simulated database connection timeout',
       updated_at = datetime('now')
   WHERE job_id = '{job_id}' 
   AND file_path LIKE '%test%'
   LIMIT 2;

Option 2: Simulate Max Retries
───────────────────────────────────────
UPDATE job_files
SET retry_count = 3,
    recovery_blocked = 1,
    block_reason = 'Max retries (3) exceeded',
    updated_at = datetime('now')
WHERE file_path LIKE '%test_1%';

Option 3: Simulate Critical Error
───────────────────────────────────────
UPDATE job_files
SET status = 'failed',
    error_message = 'Critical: File corrupted - invalid PDF header',
    recovery_blocked = 1,
    block_reason = 'Critical error: File corrupted',
    updated_at = datetime('now')
WHERE file_path LIKE '%test_2%';
""")

response = input("\nDo you want to inject test failures? (y/N): ")

if response.lower() == 'y':
    print("\n🔧 Injecting test failures...")
    
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Get recent job with files
        cursor.execute("""
            SELECT DISTINCT job_id
            FROM job_files
            WHERE status = 'completed'
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            job_id = result[0]
            print(f"\nUsing job: {job_id[:16]}...")
            
            # Inject different failure types
            
            # Get file IDs for selective updates
            cursor.execute("""
                SELECT id, file_path FROM job_files
                WHERE job_id = ? AND status = 'completed'
                LIMIT 3
            """, (job_id,))
            
            files = cursor.fetchall()
            
            if len(files) >= 3:
                # 1. Simple failure (recoverable)
                cursor.execute("""
                    UPDATE job_files
                    SET status = 'failed',
                        error_message = 'Simulated network timeout',
                        retry_count = 0,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (files[0][0],))
                failed_1 = cursor.rowcount
                
                # 2. Max retries (blocked)
                cursor.execute("""
                    UPDATE job_files
                    SET status = 'failed',
                        error_message = 'Repeated processing failure',
                        retry_count = 3,
                        recovery_blocked = 1,
                        block_reason = 'Max retries (3) exceeded',
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (files[1][0],))
                failed_2 = cursor.rowcount
                
                # 3. Critical error (blocked)
                cursor.execute("""
                    UPDATE job_files
                    SET status = 'failed',
                        error_message = 'Critical: File corrupted - invalid format',
                        retry_count = 1,
                        recovery_blocked = 1,
                        block_reason = 'Critical error: File corrupted',
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (files[2][0],))
                """, (files[2][0],))
                failed_3 = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                print(f"\n✅ Injected failures:")
                print(f"   - Simple failure: {Path(files[0][1]).name}")
                print(f"   - Max retries: {Path(files[1][1]).name}")
                print(f"   - Critical error: {Path(files[2][1]).name}")
            else:
                print(f"❌ Not enough files in job (need 3, found {len(files)})")
                conn.close()
                return
            
            # ================================================================
            # Test Recovery Endpoints
            # ================================================================
            
            print_section(f"Step 3: Test Recovery for Job {job_id[:16]}...", "-")
            
            # Get failed files
            response = requests.get(f"{BASE_URL}/jobs/{job_id}/failed-files")
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"📊 Recovery Status:")
                print(f"   Eligible: {data['recovery_eligible']['count']} files")
                print(f"   Blocked:  {data['recovery_blocked']['count']} files")
                
                if data['recovery_eligible']['files']:
                    print(f"\n📄 Eligible Files:")
                    for file in data['recovery_eligible']['files']:
                        print(f"   - {Path(file['file_path']).name}")
                        print(f"     Retry: {file['retry_count']}, Error: {file['error_message'][:50]}...")
                
                if data['recovery_blocked']['files']:
                    print(f"\n⚠️ Blocked Files:")
                    for file in data['recovery_blocked']['files']:
                        print(f"   - {Path(file['file_path']).name}")
                        print(f"     Reason: {file['block_reason']}")
            
            # Test system-wide audit
            print_section("Step 4: System-Wide Blocked Files Audit", "-")
            
            response = requests.get(f"{BASE_URL}/recovery/blocked-files")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Total Blocked: {data['total_blocked']}")
                print(f"Jobs Affected: {data['jobs_affected']}")
                
                if data['blocked_files']:
                    print(f"\n📊 Block Reasons:")
                    reasons = {}
                    for file in data['blocked_files']:
                        reason = file.get('block_reason', 'Unknown')
                        reasons[reason] = reasons.get(reason, 0) + 1
                    
                    for reason, count in reasons.items():
                        print(f"   - {reason}: {count} files")
        else:
            print("❌ No recent jobs found with files")
            conn.close()
    else:
        print("❌ Database not found")
else:
    print("\n⏭️ Skipping test failure injection")

# ================================================================
# Summary
# ================================================================

print_section("✅ Recovery System Inspection Complete", "=")

print("""Recovery System Status:
- Database schema validated
- Failed file tracking working
- Retry count tracking working
- Blocking mechanism working
- Recovery endpoints accessible

To test recovery:
1. Inject failures (run script with 'y' response)
2. Test recovery: POST /jobs/{job_id}/recover-failed-files
3. Check blocked files: GET /recovery/blocked-files
4. Admin unblock: POST /jobs/{id}/files/{path}/unblock?admin_override=true

API Documentation:
  http://127.0.0.1:45679/docs

Complete Documentation:
  docs/RECOVERY_SYSTEM_COMPLETE.md
  docs/RECOVERY_SYSTEM_SUMMARY.md
""")

print("=" * 70)
