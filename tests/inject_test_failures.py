"""
Simple Recovery Test - Direct SQL Injection

Injects test failures directly into database for recovery testing.
"""

import sqlite3
import requests
from pathlib import Path

DB_PATH = Path("data/ingestion_jobs.db")
BASE_URL = "http://127.0.0.1:45679"

print("=" * 70)
print(" Recovery System - Test Failure Injection")
print("=" * 70)

# Get recent job
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

cursor.execute("""
    SELECT id, job_id, file_path FROM job_files
    WHERE status = 'completed'
    ORDER BY updated_at DESC
    LIMIT 3
""")

files = cursor.fetchall()

if len(files) >= 3:
    job_id = files[0][1]
    print(f"\nUsing job: {job_id[:16]}...")
    print(f"Injecting 3 types of failures:\n")
    
    # 1. Simple failure
    cursor.execute("""
        UPDATE job_files
        SET status = 'failed',
            error_message = 'Simulated network timeout',
            retry_count = 0,
            updated_at = datetime('now')
        WHERE id = ?
    """, (files[0][0],))
    print(f"1. Simple Failure: {Path(files[0][2]).name}")
    
    # 2. Max retries
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
    print(f"2. Max Retries: {Path(files[1][2]).name}")
    
    # 3. Critical error
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
    print(f"3. Critical Error: {Path(files[2][2]).name}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 70)
    print(" Testing Recovery Endpoints")
    print("=" * 70)
    
    # Test failed files endpoint
    print(f"\n1. GET /jobs/{job_id}/failed-files")
    response = requests.get(f"{BASE_URL}/jobs/{job_id[:16]}/failed-files")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Eligible: {data['recovery_eligible']['count']}")
        print(f"   Blocked: {data['recovery_blocked']['count']}")
    
    # Test system-wide audit
    print(f"\n2. GET /recovery/blocked-files")
    response = requests.get(f"{BASE_URL}/recovery/blocked-files")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Total Blocked: {data['total_blocked']}")
        print(f"   Jobs Affected: {data['jobs_affected']}")
    
    print("\n" + "=" * 70)
    print(" Test Complete!")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. View failed files: http://127.0.0.1:45679/docs")
    print(f"2. Test recovery: POST /jobs/{job_id[:16]}/recover-failed-files")
    print(f"3. Check database: python tests\\check_job_database_detailed.py")
    
else:
    print("Not enough files found in database")
    conn.close()
