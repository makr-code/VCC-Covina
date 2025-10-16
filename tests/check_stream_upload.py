"""
Quick check: Verify streaming upload worked
"""
from database.database_manager import DatabaseManager

def main():
    dm = DatabaseManager()
    
    # Get relational DB stats
    relational = dm.get_relational_db()
    if relational:
        stats = relational.get_database_statistics()
        total = stats.get('total_documents', 0)
        print(f"✅ PostgreSQL Total Documents: {total}")
    else:
        print("❌ Relational DB not available")
    
    dm.close()

if __name__ == "__main__":
    main()
