"""Quick test to verify analytics schema was created."""
from uds3.database.database_manager import DatabaseManager

dm = DatabaseManager({'relational': {'enabled': True}}, autostart=True)
backend = dm.relational_backend

print("Testing analytics schema...")
print()

# Test dimension tables with fetch=True
dim_tables = ['dim_domain', 'dim_concept', 'dim_jurisdiction', 'dim_authority', 'dim_law', 'dim_norm']
print("Testing dimension tables...")
for table in dim_tables:
    try:
        result = backend.execute_query(
            f'SELECT COUNT(*) AS cnt FROM {table}',
            fetch=True  # CRITICAL: Must be True for SELECT queries!
        )
        if result and len(result) > 0:
            count = result[0]['cnt']
            print(f"  {table}: {count} rows")
        else:
            print(f"  {table}: Query returned empty")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")

print()

# Show dim_domain data
print("Sample data from dim_domain:")
try:
    result = backend.execute_query(
        "SELECT id, name, tier FROM dim_domain ORDER BY tier, name LIMIT 10",
        fetch=True
    )
    if result:
        for row in result:
            print(f"  [{row['tier']}] {row['id']}: {row['name']}")
    else:
        print("  No data")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("Schema verification complete!")

