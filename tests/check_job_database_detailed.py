"""
Enhanced Database Inspection: Job + File Level Tracking

Shows detailed view of job and file-level metadata for audit logging
"""
import sqlite3
from pathlib import Path
from datetime import datetime

db_path = Path("data/ingestion_jobs.db")

if not db_path.exists():
    print("❌ Database file not found!")
    exit(1)

print("=" * 70)
print(" 📊 Covina Ingestion Database Inspector")
print("=" * 70)
print(f"Database: {db_path}\n")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# ================================================================
# JOB-LEVEL STATISTICS
# ================================================================
print("\n📦 JOB-LEVEL OVERVIEW:")
print("-" * 70)

cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
    FROM jobs
""")
job_stats = cursor.fetchone()
print(f"  Total Jobs:     {job_stats[0]}")
print(f"  ├─ Pending:     {job_stats[1]}")
print(f"  ├─ Processing:  {job_stats[2]}")
print(f"  ├─ Completed:   {job_stats[3]}")
print(f"  └─ Failed:      {job_stats[4]}")

# ================================================================
# FILE-LEVEL STATISTICS
# ================================================================
print("\n📄 FILE-LEVEL OVERVIEW:")
print("-" * 70)

cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
    FROM job_files
""")
file_stats = cursor.fetchone()
print(f"  Total Files:    {file_stats[0]}")
print(f"  ├─ Pending:     {file_stats[1]}")
print(f"  ├─ Processing:  {file_stats[2]}")
print(f"  ├─ Completed:   {file_stats[3]}")
print(f"  └─ Failed:      {file_stats[4]}")

# ================================================================
# RECENT JOBS WITH FILE COUNTS
# ================================================================
print("\n📋 RECENT JOBS (with File Details):")
print("-" * 70)

cursor.execute("""
    SELECT 
        j.job_id,
        j.status,
        j.file_count,
        j.processed_files,
        j.created_at,
        j.temp_directory,
        j.scan_job_id,
        (SELECT COUNT(*) FROM job_files jf WHERE jf.job_id = j.job_id) as tracked_files,
        (SELECT COUNT(*) FROM job_files jf WHERE jf.job_id = j.job_id AND jf.status = 'completed') as completed_files,
        (SELECT COUNT(*) FROM job_files jf WHERE jf.job_id = j.job_id AND jf.status = 'failed') as failed_files
    FROM jobs j
    ORDER BY j.created_at DESC
    LIMIT 10
""")

jobs = cursor.fetchall()

if jobs:
    for job in jobs:
        job_id, status, file_count, processed, created_at, temp_dir, scan_id, tracked, completed, failed = job
        
        print(f"\n  Job: {job_id[:16]}...")
        print(f"  ├─ Status:      {status}")
        print(f"  ├─ Created:     {created_at}")
        print(f"  ├─ Files:       {processed}/{file_count} processed")
        print(f"  ├─ Tracked:     {tracked} files in DB")
        print(f"  │  ├─ Completed: {completed}")
        print(f"  │  └─ Failed:    {failed}")
        if temp_dir:
            print(f"  ├─ Temp Dir:    {temp_dir}")
        if scan_id:
            print(f"  └─ Scan Job:    {scan_id}")
else:
    print("  ❌ No jobs found")

# ================================================================
# FAILED FILES (for debugging)
# ================================================================
print("\n❌ FAILED FILES (Recent):")
print("-" * 70)

cursor.execute("""
    SELECT 
        jf.job_id,
        jf.file_path,
        jf.error_message,
        jf.updated_at
    FROM job_files jf
    WHERE jf.status = 'failed'
    ORDER BY jf.updated_at DESC
    LIMIT 10
""")

failed_files = cursor.fetchall()

if failed_files:
    for job_id, file_path, error, updated in failed_files:
        print(f"\n  Job: {job_id[:16]}...")
        print(f"  ├─ File:  {Path(file_path).name}")
        print(f"  ├─ Error: {error[:60]}...")
        print(f"  └─ Time:  {updated}")
else:
    print("  ✅ No failed files")

# ================================================================
# PROCESSING TIME ANALYSIS
# ================================================================
print("\n⏱️  PROCESSING TIME ANALYSIS:")
print("-" * 70)

cursor.execute("""
    SELECT 
        jf.file_path,
        jf.created_at,
        jf.updated_at,
        CAST((julianday(jf.updated_at) - julianday(jf.created_at)) * 86400 AS INTEGER) as duration_seconds
    FROM job_files jf
    WHERE jf.status = 'completed'
    ORDER BY duration_seconds DESC
    LIMIT 5
""")

slow_files = cursor.fetchall()

if slow_files:
    print("  Slowest Files:")
    for file_path, created, updated, duration in slow_files:
        print(f"  ├─ {Path(file_path).name}: {duration}s")
    
    # Average processing time
    cursor.execute("""
        SELECT 
            AVG(CAST((julianday(updated_at) - julianday(created_at)) * 86400 AS REAL)) as avg_seconds,
            MIN(CAST((julianday(updated_at) - julianday(created_at)) * 86400 AS REAL)) as min_seconds,
            MAX(CAST((julianday(updated_at) - julianday(created_at)) * 86400 AS REAL)) as max_seconds
        FROM job_files
        WHERE status = 'completed'
    """)
    avg, min_time, max_time = cursor.fetchone()
    
    print(f"\n  Average: {avg:.2f}s")
    print(f"  Min:     {min_time:.2f}s")
    print(f"  Max:     {max_time:.2f}s")
else:
    print("  ❌ No completed files for analysis")

conn.close()

print("\n" + "=" * 70)
print("✅ Database inspection complete!")
print("=" * 70)
