"""
Database Migration: Add Recovery Tracking Columns

Adds new columns to job_files table:
- retry_count
- last_retry_at
- recovery_blocked
- block_reason
"""

import sqlite3
from pathlib import Path

db_path = Path("data/ingestion_jobs.db")

if not db_path.exists():
    print("❌ Database not found - will be created on next backend start")
    exit(0)

print("=" * 70)
print(" 🔄 Database Migration: Recovery Tracking")
print("=" * 70)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check current schema
cursor.execute("PRAGMA table_info(job_files)")
columns = [col[1] for col in cursor.fetchall()]

print(f"\nCurrent columns: {columns}")

# Add new columns if they don't exist
new_columns = [
    ("retry_count", "INTEGER DEFAULT 0"),
    ("last_retry_at", "TEXT"),
    ("recovery_blocked", "BOOLEAN DEFAULT 0"),
    ("block_reason", "TEXT")
]

added = []
skipped = []

for col_name, col_type in new_columns:
    if col_name not in columns:
        try:
            cursor.execute(f"ALTER TABLE job_files ADD COLUMN {col_name} {col_type}")
            added.append(col_name)
            print(f"✅ Added column: {col_name}")
        except Exception as e:
            print(f"❌ Failed to add {col_name}: {e}")
    else:
        skipped.append(col_name)
        print(f"⏭️  Column exists: {col_name}")

conn.commit()

# Verify new schema
cursor.execute("PRAGMA table_info(job_files)")
columns_after = cursor.fetchall()

print("\n" + "=" * 70)
print(" 📊 Updated Schema: job_files")
print("=" * 70)

for col in columns_after:
    print(f"  {col[1]:20} {col[2]:15} (NULL: {col[3] == 0})")

conn.close()

print("\n" + "=" * 70)
print(" ✅ Migration Complete")
print("=" * 70)
print(f"Columns added: {len(added)}")
print(f"Columns skipped: {len(skipped)}")
print("\nRecovery tracking is now enabled!")
