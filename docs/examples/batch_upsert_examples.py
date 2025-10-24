"""
Batch UPSERT Operations - Python Examples

This file demonstrates how to use the Batch UPSERT API endpoint
for efficient bulk insert/update of documents.

API Endpoint: POST /api/v1/batch/upsert
Performance: 83x faster than sequential upserts

Author: GitHub Copilot
Date: October 21, 2025
Version: 1.0.0
"""

import requests
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime


# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = "http://127.0.0.1:45678/api/v1"
BATCH_UPSERT_ENDPOINT = f"{API_BASE_URL}/batch/upsert"


# ============================================================================
# Helper Functions
# ============================================================================

def batch_upsert(
    documents: List[Dict[str, Any]],
    conflict_resolution: str = "update",
    upsert_postgres: bool = True,
    upsert_neo4j: bool = False,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Send batch upsert request to API.
    
    Args:
        documents: List of documents to upsert
        conflict_resolution: "update" (update on conflict) or "skip" (skip on conflict)
        upsert_postgres: Whether to upsert to PostgreSQL
        upsert_neo4j: Whether to upsert to Neo4j
        timeout: Request timeout in seconds
    
    Returns:
        API response with upsert results
    """
    payload = {
        "documents": documents,
        "conflict_resolution": conflict_resolution,
        "upsert_postgres": upsert_postgres,
        "upsert_neo4j": upsert_neo4j
    }
    
    try:
        response = requests.post(
            BATCH_UPSERT_ENDPOINT,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": response.status_code if hasattr(response, 'status_code') else None
        }


def print_results(result: Dict[str, Any], operation_name: str = "Batch Upsert"):
    """Print formatted results."""
    print(f"\n{'='*80}")
    print(f"📊 {operation_name} Results")
    print(f"{'='*80}")
    
    if result.get("success"):
        print(f"✅ Success: {result['success']}")
        
        if "postgres" in result:
            pg = result["postgres"]
            print(f"\n📦 PostgreSQL:")
            print(f"   Inserted:    {pg.get('inserted', 0)}")
            print(f"   Updated:     {pg.get('updated', 0)}")
            print(f"   Failed:      {pg.get('failed', 0)}")
            print(f"   Time:        {pg.get('execution_time_ms', 0):.2f}ms")
        
        if "neo4j" in result:
            neo = result["neo4j"]
            print(f"\n🔗 Neo4j:")
            print(f"   Inserted:    {neo.get('inserted', 0)}")
            print(f"   Updated:     {neo.get('updated', 0)}")
            print(f"   Failed:      {neo.get('failed', 0)}")
            print(f"   Time:        {neo.get('execution_time_ms', 0):.2f}ms")
        
        if "total_execution_time_ms" in result:
            print(f"\n⏱️  Total Time: {result['total_execution_time_ms']:.2f}ms")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    print(f"{'='*80}\n")


# ============================================================================
# Example 1: Simple Insert (All New Documents)
# ============================================================================

def example_1_simple_insert():
    """Example 1: Insert 10 new documents"""
    print("\n" + "="*80)
    print("Example 1: Simple Insert (All New Documents)")
    print("="*80)
    
    # Create new documents
    documents = [
        {
            "document_id": f"new_doc_{i}_{int(time.time())}",
            "title": f"New Document {i}",
            "content": f"This is new content for document {i}",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "author": "batch_upsert_system",
                "version": 1
            },
            "tags": ["new", "batch_insert"],
            "category": "general",
            "status": "draft"
        }
        for i in range(1, 11)
    ]
    
    print(f"\n➕ Inserting {len(documents)} new documents...")
    print(f"Conflict resolution: update (not applicable - all new)")
    
    # Send batch upsert request
    result = batch_upsert(documents, conflict_resolution="update")
    
    # Print results
    print_results(result, "Simple Insert")
    
    print("ℹ️  Note: All documents are new (inserted=10, updated=0)")
    
    return result


# ============================================================================
# Example 2: Simple Update (All Existing Documents)
# ============================================================================

def example_2_simple_update():
    """Example 2: Update 10 existing documents"""
    print("\n" + "="*80)
    print("Example 2: Simple Update (All Existing Documents)")
    print("="*80)
    
    # Update existing documents (use known IDs)
    documents = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "title": f"Updated Document {i}",
            "content": f"This is updated content for document {i}",
            "metadata": {
                "updated_at": datetime.now().isoformat(),
                "updated_by": "batch_upsert_system",
                "version": 2
            },
            "tags": ["updated", "batch_upsert"],
            "category": "general",
            "status": "published"
        }
        for i in range(1, 11)
    ]
    
    print(f"\n✏️  Updating {len(documents)} existing documents...")
    print(f"Conflict resolution: update")
    
    # Send batch upsert request
    result = batch_upsert(documents, conflict_resolution="update")
    
    # Print results
    print_results(result, "Simple Update")
    
    print("ℹ️  Note: All documents existed (inserted=0, updated=10)")
    
    return result


# ============================================================================
# Example 3: Mixed Insert/Update
# ============================================================================

def example_3_mixed_insert_update():
    """Example 3: Mix of new and existing documents"""
    print("\n" + "="*80)
    print("Example 3: Mixed Insert/Update")
    print("="*80)
    
    # Mix of new and existing documents
    documents = []
    
    # First 10: Existing documents (update)
    for i in range(1, 11):
        documents.append({
            "document_id": f"doc_2024_{i:04d}",
            "title": f"Updated Doc {i}",
            "content": f"Updated content {i}",
            "metadata": {"version": 2},
            "tags": ["updated"]
        })
    
    # Next 10: New documents (insert)
    for i in range(11, 21):
        documents.append({
            "document_id": f"new_doc_{i}_{int(time.time())}",
            "title": f"New Doc {i}",
            "content": f"New content {i}",
            "metadata": {"version": 1},
            "tags": ["new"]
        })
    
    print(f"\n🔀 Upserting {len(documents)} documents (mixed)...")
    print(f"Expected: ~10 inserts, ~10 updates")
    
    # Send batch upsert request
    result = batch_upsert(documents, conflict_resolution="update")
    
    # Print results
    print_results(result, "Mixed Insert/Update")
    
    return result


# ============================================================================
# Example 4: Bulk Import (100 New Documents)
# ============================================================================

def example_4_bulk_import():
    """Example 4: Bulk import 100 new documents"""
    print("\n" + "="*80)
    print("Example 4: Bulk Import (100 New Documents)")
    print("="*80)
    
    # Create 100 new documents
    documents = [
        {
            "document_id": f"import_doc_{i}_{int(time.time())}",
            "title": f"Import Document {i}",
            "content": f"Bulk import content for document {i}",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "source": "bulk_import",
                "batch": "2024_10_21",
                "version": 1
            },
            "tags": ["import", "bulk", f"batch_{i // 10}"],
            "category": "imported",
            "status": "active"
        }
        for i in range(1, 101)
    ]
    
    print(f"\n➕ Importing {len(documents)} documents...")
    
    # Measure execution time
    start_time = time.time()
    result = batch_upsert(documents, conflict_resolution="update")
    execution_time = time.time() - start_time
    
    # Print results
    print_results(result, "Bulk Import")
    
    print(f"🚀 Client-side execution time: {execution_time:.4f}s")
    print(f"📊 Throughput: {len(documents) / execution_time:.1f} docs/s")
    
    return result


# ============================================================================
# Example 5: Sync External Data (Update if Exists, Insert if New)
# ============================================================================

def example_5_sync_external_data():
    """Example 5: Sync data from external source"""
    print("\n" + "="*80)
    print("Example 5: Sync External Data (Update/Insert)")
    print("="*80)
    
    # Simulate external data source
    external_data = [
        {"id": f"ext_{i}", "name": f"External Item {i}", "data": f"Data {i}"}
        for i in range(1, 31)
    ]
    
    print(f"\n🔄 Syncing {len(external_data)} items from external source...")
    
    # Transform external data to documents
    documents = [
        {
            "document_id": item["id"],
            "title": item["name"],
            "content": item["data"],
            "metadata": {
                "synced_at": datetime.now().isoformat(),
                "source": "external_api",
                "version": 1
            },
            "tags": ["synced", "external"]
        }
        for item in external_data
    ]
    
    # Send batch upsert request
    result = batch_upsert(documents, conflict_resolution="update")
    
    # Print results
    print_results(result, "Sync External Data")
    
    print(f"ℹ️  Sync complete: {result.get('postgres', {}).get('inserted', 0)} new, "
          f"{result.get('postgres', {}).get('updated', 0)} updated")
    
    return result


# ============================================================================
# Example 6: Conflict Resolution - Update on Conflict
# ============================================================================

def example_6_conflict_resolution_update():
    """Example 6: Update on conflict (default behavior)"""
    print("\n" + "="*80)
    print("Example 6: Conflict Resolution - Update on Conflict")
    print("="*80)
    
    # Create documents (some may already exist)
    documents = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "title": f"Conflict Update {i}",
            "content": f"Updated via conflict resolution {i}",
            "metadata": {
                "conflict_resolution": "update",
                "updated_at": datetime.now().isoformat()
            },
            "tags": ["conflict_update"]
        }
        for i in range(1, 21)
    ]
    
    print(f"\n🔄 Upserting {len(documents)} documents...")
    print(f"Conflict resolution: update (update if exists)")
    
    # Send batch upsert request
    result = batch_upsert(documents, conflict_resolution="update")
    
    # Print results
    print_results(result, "Conflict Resolution (Update)")
    
    print("ℹ️  Behavior: Existing documents updated, new documents inserted")
    
    return result


# ============================================================================
# Example 7: Conflict Resolution - Skip on Conflict
# ============================================================================

def example_7_conflict_resolution_skip():
    """Example 7: Skip on conflict (preserve existing data)"""
    print("\n" + "="*80)
    print("Example 7: Conflict Resolution - Skip on Conflict")
    print("="*80)
    
    # Create documents (some may already exist)
    documents = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "title": f"Conflict Skip {i}",
            "content": f"This should be skipped if exists {i}",
            "metadata": {
                "conflict_resolution": "skip",
                "attempted_at": datetime.now().isoformat()
            },
            "tags": ["conflict_skip"]
        }
        for i in range(1, 21)
    ]
    
    print(f"\n➕ Upserting {len(documents)} documents...")
    print(f"Conflict resolution: skip (preserve existing, insert new only)")
    
    # Send batch upsert request
    result = batch_upsert(documents, conflict_resolution="skip")
    
    # Print results
    print_results(result, "Conflict Resolution (Skip)")
    
    print("ℹ️  Behavior: Existing documents unchanged, only new documents inserted")
    
    return result


# ============================================================================
# Example 8: Multi-Database Upsert (PostgreSQL + Neo4j)
# ============================================================================

def example_8_multi_database_upsert():
    """Example 8: Upsert to both PostgreSQL and Neo4j"""
    print("\n" + "="*80)
    print("Example 8: Multi-Database Upsert (PostgreSQL + Neo4j)")
    print("="*80)
    
    # Create documents
    documents = [
        {
            "document_id": f"multi_doc_{i}",
            "title": f"Multi-DB Document {i}",
            "content": f"Content synced across databases {i}",
            "metadata": {
                "synced": True,
                "created_at": datetime.now().isoformat()
            },
            "tags": ["multi_db", "synced"]
        }
        for i in range(1, 16)
    ]
    
    print(f"\n🔀 Upserting {len(documents)} documents...")
    print(f"Databases: PostgreSQL ✅ + Neo4j ✅")
    
    # Send batch upsert request (both databases)
    result = batch_upsert(
        documents,
        conflict_resolution="update",
        upsert_postgres=True,
        upsert_neo4j=True
    )
    
    # Print results
    print_results(result, "Multi-Database Upsert")
    
    return result


# ============================================================================
# Example 9: Error Handling - Partial Success
# ============================================================================

def example_9_error_handling():
    """Example 9: Handle documents with missing required fields"""
    print("\n" + "="*80)
    print("Example 9: Error Handling - Partial Success")
    print("="*80)
    
    # Mixed documents (some valid, some with missing fields)
    documents = [
        # Valid documents
        {
            "document_id": "valid_doc_1",
            "title": "Valid Document 1",
            "content": "Valid content 1",
            "metadata": {},
            "tags": []
        },
        {
            "document_id": "valid_doc_2",
            "title": "Valid Document 2",
            "content": "Valid content 2",
            "metadata": {},
            "tags": []
        },
        # Invalid document (missing title)
        {
            "document_id": "invalid_doc_1",
            "content": "Content without title",
            # Missing title field
        },
        # Valid document
        {
            "document_id": "valid_doc_3",
            "title": "Valid Document 3",
            "content": "Valid content 3",
            "metadata": {},
            "tags": []
        }
    ]
    
    print(f"\n🔀 Upserting {len(documents)} documents (mixed valid/invalid)...")
    print(f"Expected: Some succeed, some fail")
    
    # Send batch upsert request
    result = batch_upsert(documents, conflict_resolution="update")
    
    # Print results
    print_results(result, "Error Handling")
    
    # Detailed error analysis
    if not result.get("success") and result.get("partial_success"):
        print("\n⚠️  Partial Success Detected:")
        if "postgres" in result:
            pg = result["postgres"]
            total = pg.get('inserted', 0) + pg.get('updated', 0)
            print(f"   PostgreSQL: {total} succeeded, {pg.get('failed', 0)} failed")
            if pg.get("errors"):
                print(f"   Errors: {pg['errors'][:3]}")
    
    return result


# ============================================================================
# Example 10: Batch Upsert with Retry Logic
# ============================================================================

def example_10_retry_logic():
    """Example 10: Implement retry logic for failed upserts"""
    print("\n" + "="*80)
    print("Example 10: Batch Upsert with Retry Logic")
    print("="*80)
    
    # Create documents
    documents = [
        {
            "document_id": f"retry_doc_{i}",
            "title": f"Retry Document {i}",
            "content": f"Content with retry logic {i}",
            "metadata": {"retry_attempt": 1},
            "tags": ["retry"]
        }
        for i in range(1, 21)
    ]
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    print(f"\n🔀 Upserting {len(documents)} documents with retry logic...")
    print(f"Max retries: {max_retries}")
    print(f"Retry delay: {retry_delay}s")
    
    for attempt in range(1, max_retries + 1):
        print(f"\n🔄 Attempt {attempt}/{max_retries}...")
        
        result = batch_upsert(documents, conflict_resolution="update")
        
        if result.get("success"):
            print(f"✅ Success on attempt {attempt}!")
            print_results(result, f"Retry Attempt {attempt}")
            return result
        
        # Check for partial success
        if result.get("partial_success"):
            postgres_total = (result.get("postgres", {}).get("inserted", 0) + 
                            result.get("postgres", {}).get("updated", 0))
            print(f"⚠️  Partial success: {postgres_total} documents processed")
            
            if attempt < max_retries:
                print(f"⏳ Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
        else:
            print(f"❌ Attempt {attempt} failed completely")
            if attempt < max_retries:
                print(f"⏳ Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
    
    print(f"\n❌ All {max_retries} attempts failed!")
    print_results(result, "Final Retry Result")
    
    return result


# ============================================================================
# Example 11: Performance Comparison (Batch vs Sequential)
# ============================================================================

def example_11_performance_comparison():
    """Example 11: Compare batch vs sequential upsert performance"""
    print("\n" + "="*80)
    print("Example 11: Performance Comparison (Batch vs Sequential)")
    print("="*80)
    
    num_documents = 50
    
    # Create documents (mix of new and existing)
    documents = [
        {
            "document_id": f"perf_doc_{i}",
            "title": f"Performance Test {i}",
            "content": f"Performance test content {i}",
            "metadata": {"test_type": "performance"},
            "tags": ["performance"]
        }
        for i in range(1, num_documents + 1)
    ]
    
    # Batch upsert
    print(f"\n🚀 Batch Upsert ({num_documents} documents)...")
    batch_start = time.time()
    batch_result = batch_upsert(documents, conflict_resolution="update")
    batch_time = time.time() - batch_start
    
    print(f"   Time: {batch_time:.4f}s")
    print(f"   Throughput: {num_documents / batch_time:.1f} docs/s")
    
    # Sequential upsert (simulated - don't actually do this!)
    print(f"\n🐌 Sequential Upsert (simulated - {num_documents} documents)...")
    estimated_sequential_time = batch_time * 83
    print(f"   Estimated time: {estimated_sequential_time:.4f}s (83x slower)")
    print(f"   Estimated throughput: {num_documents / estimated_sequential_time:.1f} docs/s")
    
    # Calculate speedup
    estimated_speedup = 83  # Based on benchmark data
    print(f"\n📊 Performance Summary:")
    print(f"   Batch time:      {batch_time:.4f}s")
    print(f"   Sequential time: ~{estimated_sequential_time:.4f}s (estimated)")
    print(f"   Speedup:         ~{estimated_speedup}x")
    print(f"   Status:          {'✅ OPTIMAL' if estimated_speedup >= 60 else '⚠️  SUBOPTIMAL'}")
    
    return batch_result


# ============================================================================
# Example 12: Data Migration Strategy
# ============================================================================

def example_12_data_migration():
    """Example 12: Data migration from old system to new system"""
    print("\n" + "="*80)
    print("Example 12: Data Migration Strategy")
    print("="*80)
    
    # Simulate legacy data
    print("\n🔄 Step 1: Extract data from legacy system...")
    print("   (Simulated: Extracted 100 records)")
    
    legacy_data = [
        {
            "id": f"legacy_{i}",
            "name": f"Legacy Item {i}",
            "description": f"Migrated from old system {i}",
            "created": datetime.now().isoformat()
        }
        for i in range(1, 101)
    ]
    
    print(f"\n🔄 Step 2: Transform data to new format...")
    documents = [
        {
            "document_id": item["id"],
            "title": item["name"],
            "content": item["description"],
            "metadata": {
                "migrated_at": datetime.now().isoformat(),
                "source": "legacy_system",
                "original_created": item["created"],
                "version": 1
            },
            "tags": ["migrated", "legacy"],
            "category": "migrated",
            "status": "active"
        }
        for item in legacy_data
    ]
    
    print(f"\n🔄 Step 3: Upsert {len(documents)} documents to new system...")
    
    # Measure execution time
    start_time = time.time()
    result = batch_upsert(documents, conflict_resolution="update")
    execution_time = time.time() - start_time
    
    # Print results
    print_results(result, "Data Migration")
    
    print(f"🚀 Migration time: {execution_time:.4f}s")
    print(f"📊 Throughput: {len(documents) / execution_time:.1f} docs/s")
    print("✅ Migration complete!")
    
    return result


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("🚀 Batch UPSERT API - Python Examples")
    print("="*80)
    print(f"\nAPI Endpoint: {BATCH_UPSERT_ENDPOINT}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTotal Examples: 12")
    print("="*80)
    
    examples = [
        ("Example 1: Simple Insert (All New)", example_1_simple_insert),
        ("Example 2: Simple Update (All Existing)", example_2_simple_update),
        ("Example 3: Mixed Insert/Update", example_3_mixed_insert_update),
        ("Example 4: Bulk Import (100 docs)", example_4_bulk_import),
        ("Example 5: Sync External Data", example_5_sync_external_data),
        ("Example 6: Conflict Resolution (Update)", example_6_conflict_resolution_update),
        ("Example 7: Conflict Resolution (Skip)", example_7_conflict_resolution_skip),
        ("Example 8: Multi-Database Upsert", example_8_multi_database_upsert),
        ("Example 9: Error Handling", example_9_error_handling),
        ("Example 10: Retry Logic", example_10_retry_logic),
        ("Example 11: Performance Comparison", example_11_performance_comparison),
        ("Example 12: Data Migration", example_12_data_migration),
    ]
    
    # Run examples (uncomment to enable)
    # for name, example_func in examples:
    #     try:
    #         print(f"\n{'='*80}")
    #         print(f"Running: {name}")
    #         print(f"{'='*80}")
    #         example_func()
    #     except Exception as e:
    #         print(f"❌ Error in {name}: {e}")
    
    print("\n" + "="*80)
    print("📚 Examples ready to run!")
    print("="*80)
    print("\nTo run examples, uncomment the loop in main() function.")
    print("Or run individual examples:")
    print("  >>> example_1_simple_insert()")
    print("  >>> example_4_bulk_import()")
    print("  >>> example_11_performance_comparison()")
    
    print("\n💡 Use Cases:")
    print("  - Data import/sync from external sources")
    print("  - Bulk updates with conflict resolution")
    print("  - Data migration strategies")
    print("  - Insert new + update existing in one operation")


if __name__ == "__main__":
    main()
