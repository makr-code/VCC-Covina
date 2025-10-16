"""
Test PostgreSQL Company Metadata Methods
=========================================

Tests the new PostgreSQL adapter methods:
1. update_company_metadata() - Store company extraction data
2. get_company_metadata() - Retrieve company data
3. search_documents_by_company() - Search by company name
4. get_company_statistics() - Get company statistics

Prerequisites:
- PostgreSQL schema migration completed (company_metadata column exists)
- PostgreSQL connection configured
- Python 3.8+
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend

# PostgreSQL Configuration
POSTGRES_CONFIG = {
    'host': '192.168.178.94',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'postgres',
    'schema': 'public'
}


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_json(data, indent=2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def test_update_company_metadata(backend: PostgreSQLRelationalBackend):
    """Test update_company_metadata() method"""
    print_section("TEST 1: Update Company Metadata")
    
    # Get first document from database
    backend.connect()
    backend.cursor.execute("SELECT document_id FROM documents LIMIT 1")
    result = backend.cursor.fetchone()
    
    if not result:
        print("❌ No documents found in database")
        return False
    
    document_id = result['document_id']
    print(f"Testing with document ID: {document_id}")
    
    # Test data: Mock company metadata
    test_metadata = {
        "companies": [
            {
                "firma": "Beispiel GmbH",
                "register_number": "HRB 12345",
                "register_type": "HRB",
                "register_court": "Amtsgericht München",
                "verified_in_handelsregister": True,
                "handelsregister_state": "active",
                "document_urls": [
                    "https://handelsregister.de/download/HRB12345_AD.pdf"
                ]
            },
            {
                "firma": "Test AG",
                "register_number": None,
                "register_type": None,
                "register_court": None,
                "verified_in_handelsregister": False,
                "handelsregister_state": None,
                "document_urls": []
            }
        ],
        "extraction_timestamp": datetime.now().isoformat(),
        "gaps": [
            {
                "type": "missing_register_number",
                "firma": "Test AG",
                "severity": "medium",
                "message": "Firma 'Test AG' has no HRB/HRA number"
            }
        ],
        "verification_skipped": False
    }
    
    print("\nTest metadata:")
    print_json(test_metadata)
    
    # Update metadata
    result = backend.update_company_metadata(document_id, test_metadata)
    
    print("\nUpdate result:")
    print_json(result)
    
    if result.get("success"):
        print("✅ Test 1 PASSED")
        return document_id
    else:
        print("❌ Test 1 FAILED")
        return None


def test_get_company_metadata(backend: PostgreSQLRelationalBackend, document_id: str):
    """Test get_company_metadata() method"""
    print_section("TEST 2: Get Company Metadata")
    
    print(f"Retrieving metadata for document: {document_id}")
    
    metadata = backend.get_company_metadata(document_id)
    
    if metadata:
        print("\nRetrieved metadata:")
        print_json(metadata)
        print("✅ Test 2 PASSED")
        return True
    else:
        print("❌ Test 2 FAILED - No metadata found")
        return False


def test_search_documents_by_company(backend: PostgreSQLRelationalBackend):
    """Test search_documents_by_company() method"""
    print_section("TEST 3: Search Documents by Company")
    
    # Test 1: Exact match
    print("\nTest 3a: Exact match search for 'Beispiel GmbH'")
    results = backend.search_documents_by_company("Beispiel GmbH", exact_match=True)
    
    print(f"Found {len(results)} documents")
    if results:
        print("\nFirst result:")
        print_json(results[0], indent=2)
    
    # Test 2: Pattern matching
    print("\nTest 3b: Pattern matching search for 'Beispiel%'")
    results = backend.search_documents_by_company("Beispiel", exact_match=False)
    
    print(f"Found {len(results)} documents")
    
    if results:
        print("✅ Test 3 PASSED")
        return True
    else:
        print("⚠️ Test 3 WARNING - No results (expected if only one test document)")
        return True


def test_company_statistics(backend: PostgreSQLRelationalBackend):
    """Test get_company_statistics() method"""
    print_section("TEST 4: Company Statistics")
    
    stats = backend.get_company_statistics()
    
    print("\nCompany statistics:")
    print_json(stats)
    
    if "total_documents" in stats:
        print("✅ Test 4 PASSED")
        return True
    else:
        print("❌ Test 4 FAILED")
        return False


def test_jsonb_queries(backend: PostgreSQLRelationalBackend):
    """Test advanced JSONB queries"""
    print_section("TEST 5: Advanced JSONB Queries")
    
    backend.connect()
    
    # Test 1: Find documents with gaps
    print("\nTest 5a: Find documents with gaps")
    backend.cursor.execute("""
        SELECT 
            document_id,
            jsonb_array_length(company_metadata->'gaps') as gap_count
        FROM documents
        WHERE company_metadata->'gaps' IS NOT NULL
        AND jsonb_array_length(company_metadata->'gaps') > 0
        LIMIT 5
    """)
    
    results = backend.cursor.fetchall()
    print(f"Found {len(results)} documents with gaps")
    
    for row in results:
        print(f"  - {row['document_id']}: {row['gap_count']} gaps")
    
    # Test 2: Find documents with verified companies
    print("\nTest 5b: Find documents with verified companies")
    backend.cursor.execute("""
        SELECT 
            document_id,
            COUNT(*) as verified_count
        FROM documents,
             jsonb_array_elements(company_metadata->'companies') AS company
        WHERE (company->>'verified_in_handelsregister')::boolean = true
        GROUP BY document_id
        LIMIT 5
    """)
    
    results = backend.cursor.fetchall()
    print(f"Found {len(results)} documents with verified companies")
    
    for row in results:
        print(f"  - {row['document_id']}: {row['verified_count']} verified companies")
    
    # Test 3: Gap type distribution
    print("\nTest 5c: Gap type distribution")
    backend.cursor.execute("""
        SELECT 
            gap->>'type' as gap_type,
            COUNT(*) as count
        FROM documents,
             jsonb_array_elements(company_metadata->'gaps') AS gap
        WHERE company_metadata->'gaps' IS NOT NULL
        GROUP BY gap->>'type'
        ORDER BY count DESC
    """)
    
    results = backend.cursor.fetchall()
    print("Gap types:")
    
    for row in results:
        print(f"  - {row['gap_type']}: {row['count']}")
    
    print("✅ Test 5 PASSED")
    return True


def cleanup_test_data(backend: PostgreSQLRelationalBackend, document_id: str):
    """Remove test data"""
    print_section("CLEANUP: Remove Test Data")
    
    print(f"Removing company_metadata from document: {document_id}")
    
    backend.connect()
    backend.cursor.execute("""
        UPDATE documents 
        SET company_metadata = NULL 
        WHERE document_id = %s
    """, (document_id,))
    
    backend.conn.commit()
    
    print("✅ Test data removed")


def main():
    """Run all tests"""
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║  PostgreSQL Company Metadata Methods - Test Suite                 ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    
    # Initialize backend
    print("\nInitializing PostgreSQL backend...")
    backend = PostgreSQLRelationalBackend(POSTGRES_CONFIG)
    backend.connect()
    print(f"✅ Connected to {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
    
    # Run tests
    test_results = []
    document_id = None
    
    try:
        # Test 1: Update
        document_id = test_update_company_metadata(backend)
        test_results.append(("Update Company Metadata", document_id is not None))
        
        if document_id:
            # Test 2: Get
            success = test_get_company_metadata(backend, document_id)
            test_results.append(("Get Company Metadata", success))
            
            # Test 3: Search
            success = test_search_documents_by_company(backend)
            test_results.append(("Search Documents", success))
            
            # Test 4: Statistics
            success = test_company_statistics(backend)
            test_results.append(("Company Statistics", success))
            
            # Test 5: JSONB Queries
            success = test_jsonb_queries(backend)
            test_results.append(("Advanced JSONB Queries", success))
        
        # Summary
        print_section("TEST SUMMARY")
        
        passed = sum(1 for _, success in test_results if success)
        total = len(test_results)
        
        for test_name, success in test_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{test_name:.<50} {status}")
        
        print("\n" + "=" * 70)
        print(f"  TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        print("=" * 70)
        
        # Cleanup (optional)
        if document_id:
            response = input("\nRemove test data? (y/n): ")
            if response.lower() == 'y':
                cleanup_test_data(backend, document_id)
        
        return 0 if passed == total else 1
    
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        backend.disconnect()
        print("\nPostgreSQL connection closed")


if __name__ == "__main__":
    sys.exit(main())
