"""Check classification values in PostgreSQL."""
from database.database_manager import DatabaseManager

dm = DatabaseManager({"relational": {"enabled": True}}, autostart=True)
backend = dm.relational_backend

result = backend.execute_query(
    "SELECT classification, COUNT(*) as cnt FROM documents WHERE classification IS NOT NULL GROUP BY classification ORDER BY cnt DESC LIMIT 20",
    fetch=True
)

print("\nClassification Distribution (Top 20):")
print("=" * 50)
for r in result:
    print(f"{r['classification']:35s}: {r['cnt']:>7,d}")
print("=" * 50)

# Check total
total_result = backend.execute_query(
    "SELECT COUNT(*) as total FROM documents WHERE classification IS NOT NULL",
    fetch=True
)
print(f"\nTotal with classification: {total_result[0]['total']:,}")
