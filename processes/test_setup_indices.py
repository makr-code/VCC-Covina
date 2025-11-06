"""
Test Neo4j Temporal & Process Indices Setup

Activates constraints and indices for:
- Temporal Canon (Year, Month, Day, Date)
- Process entities (Process, Step, Role, OrgUnit, System, Control, LegalRef, InfoObject)
"""
import os
import sys


def main():
    """Test index setup with UDS3 Neo4j adapter."""
    # Add parent directory to path for imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    from processes.graph.setup_indices import setup_all_indices
    from uds3.database.database_api_neo4j import Neo4jGraphBackend
    
    # Get Neo4j connection details
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://192.168.178.94:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j")
    
    print("=" * 80)
    print("Neo4j Temporal & Process Indices Setup")
    print("=" * 80)
    print(f"\nNeo4j URI: {neo4j_uri}")
    print(f"User: {neo4j_user}")
    print("\nConnecting to Neo4j...\n")
    
    # Initialize adapter
    config = {
        'uri': neo4j_uri,
        'user': neo4j_user,
        'password': neo4j_password,
    }
    adapter = Neo4jGraphBackend(config)
    
    try:
        adapter.connect()
        print("✅ Connected to Neo4j\n")
        
        # Setup all indices
        print("Creating constraints and indices...\n")
        result = setup_all_indices(adapter)
        
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"\nTemporal Canon: {result['temporal']} queries executed")
        print(f"Process Entities: {result['process']} queries executed")
        print(f"Total: {result['total']} queries executed")
        print("\n✅ All constraints and indices created successfully!")
        print("\nDetails:")
        print("  - Temporal constraints: date_iso_unique, year_y_unique, month_ym_unique, day_ymd_unique")
        print("  - Temporal indices: month_y_m, day_y_m_d, date_year, date_month, date_day")
        print("  - Process constraints: process_id_unique, step_id_unique, role_id_unique, ...")
        print("  - Process indices: process_key, step_type, role_name, ...")
        print("  - Fulltext indices: process_search, step_search, role_search, org_unit_search")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        adapter.disconnect()
        print("\n✅ Neo4j connection closed")


if __name__ == "__main__":
    main()

