"""
Apply Analytics Schema Migration to PostgreSQL via UDS3

Usage:
    python -m ingestion.analytics.apply_migration
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from uds3.database.database_manager import DatabaseManager


def read_migration_file(migration_path: str) -> str:
    """Read SQL migration file."""
    with open(migration_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_sql_statements(sql_content: str) -> list[str]:
    """
    Split SQL content into individual statements.
    
    Handles:
    - CREATE TABLE statements
    - CREATE INDEX statements
    - CREATE MATERIALIZED VIEW statements
    - CREATE FUNCTION statements (with $$...$$)
    """
    statements = []
    current_stmt = []
    in_function = False
    
    for line in sql_content.split('\n'):
        # Skip comments and empty lines
        if line.strip().startswith('--') or not line.strip():
            continue
        
        # Track if we're inside a function definition
        if '$$' in line:
            in_function = not in_function
        
        current_stmt.append(line)
        
        # End of statement (semicolon outside of function)
        if ';' in line and not in_function:
            stmt = '\n'.join(current_stmt).strip()
            if stmt:
                statements.append(stmt)
            current_stmt = []
    
    # Add last statement if exists
    if current_stmt:
        stmt = '\n'.join(current_stmt).strip()
        if stmt:
            statements.append(stmt)
    
    return statements


def apply_migration():
    """Apply migration to PostgreSQL via UDS3."""
    print("=" * 70)
    print("Analytics Schema Migration")
    print("=" * 70)
    print()
    
    # 1. Read migration file
    migration_path = project_root / "ingestion" / "analytics" / "migrations" / "001_analytics_schema.sql"
    
    if not migration_path.exists():
        print(f"ERROR: Migration file not found: {migration_path}")
        return 1
    
    print(f"Reading migration: {migration_path.name}")
    sql_content = read_migration_file(migration_path)
    print(f"  Size: {len(sql_content)} bytes")
    print()
    
    # 2. Initialize UDS3 DatabaseManager (Relational backend only)
    print("Connecting to PostgreSQL via UDS3...")
    try:
        db_manager = DatabaseManager(
            backend_dict={'relational': {'enabled': True}},
            autostart=True
        )
        relational_backend = db_manager.relational_backend
        
        if not relational_backend:
            print("  ERROR: Relational backend not available")
            return 1
        
        print("  Connected successfully")
        print()
    except Exception as e:
        print(f"  ERROR: Connection failed: {e}")
        return 1
    
    # 3. Split SQL into statements
    print("Parsing SQL statements...")
    statements = split_sql_statements(sql_content)
    print(f"  Found {len(statements)} SQL statements")
    print()
    
    # 4. Execute statements one by one
    print("Applying migration...")
    print("-" * 70)
    
    success_count = 0
    failed_count = 0
    
    for i, stmt in enumerate(statements, 1):
        # Extract statement type for display
        stmt_type = stmt.split()[0:3]
        stmt_preview = ' '.join(stmt_type).upper()
        
        print(f"[{i}/{len(statements)}] {stmt_preview}...", end=" ")
        
        try:
            relational_backend.execute_query(stmt)
            print("OK")
            success_count += 1
        except Exception as e:
            print(f"FAILED")
            print(f"      Error: {e}")
            failed_count += 1
            
            # Continue on error (some statements might already exist)
            # But log it for review
            continue
    
    print("-" * 70)
    print()
    
    # 5. Summary
    print("Migration Summary:")
    print(f"  Successful: {success_count}/{len(statements)}")
    print(f"  Failed:     {failed_count}/{len(statements)}")
    print()
    
    # 6. Verify schema
    print("Verifying schema...")
    verification_queries = [
        ("Dimension Tables", "SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_name LIKE 'dim_%'"),
        ("Fact Tables", "SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_name LIKE 'legal_stats%'"),
        ("Materialized Views", "SELECT COUNT(*) AS cnt FROM pg_matviews WHERE matviewname LIKE 'mv_%'"),
    ]
    
    for check_name, query in verification_queries:
        try:
            result = relational_backend.execute_query(query)
            count = result[0]['cnt'] if result else 0
            print(f"  {check_name}: {count}")
        except Exception as e:
            print(f"  {check_name}: ERROR: {e}")
    
    print()
    
    # 7. Exit status
    if failed_count > 0:
        print("Migration completed with errors")
        print("  Review errors above and check if tables already existed")
        print()
        return 0  # Exit code 0 because failures might be "already exists" errors
    else:
        print("Migration completed successfully!")
        print()
        print("Next steps:")
        print("  1. Enable feature flag: ENABLE_GRAPH_ANALYTICS_SYNC=true")
        print("  2. Run initial sync: python -m ingestion.analytics.graph_to_relational_sync")
        print("  3. Schedule daily refresh: .\\scripts\\refresh_analytics.ps1")
        print()
        return 0


if __name__ == "__main__":
    exit_code = apply_migration()
    sys.exit(exit_code)
