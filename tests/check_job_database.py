"""
Quick test: Check if jobs are saved in SQLite database
"""
import sqlite3
from pathlib import Path

db_path = Path("data/ingestion_jobs.db")

if not db_path.exists():
    print("❌ Database file not found!")
    exit(1)

print(f"✅ Database found: {db_path}\n")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check jobs table
cursor.execute("SELECT COUNT(*) FROM jobs")
job_count = cursor.fetchone()[0]
print(f"📊 Total jobs in database: {job_count}")

# Get recent jobs
cursor.execute("""
    SELECT job_id, status, file_count, processed_files, created_at, temp_directory, scan_job_id
    FROM jobs
    ORDER BY created_at DESC
    LIMIT 10
""")

jobs = cursor.fetchall()

if jobs:
    print(f"\n📋 Recent jobs:")
    for job in jobs:
        job_id, status, file_count, processed, created_at, temp_dir, scan_id = job
        print(f"  {job_id[:8]}: {status} ({processed}/{file_count} files)")
        print(f"     Created: {created_at}")
        if temp_dir:
            print(f"     Temp: {temp_dir}")
        if scan_id:
            print(f"     Scan: {scan_id}")
        print()
else:
    print("\n❌ No jobs found in database")

# Check scan_jobs table
cursor.execute("SELECT COUNT(*) FROM scan_jobs")
scan_count = cursor.fetchone()[0]
print(f"📊 Total scan jobs in database: {scan_count}")

conn.close()

print("\n✅ Database check complete!")
