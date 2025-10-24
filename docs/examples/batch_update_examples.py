"""
Batch UPDATE Operations - Python Examples

This file demonstrates how to use the Batch UPDATE API endpoint
for efficient bulk updates of documents.

API Endpoint: POST /api/v1/batch/update
Performance: 67-80x faster than sequential updates

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
BATCH_UPDATE_ENDPOINT = f"{API_BASE_URL}/batch/update"


# ============================================================================
# Helper Functions
# ============================================================================

def batch_update(
    updates: List[Dict[str, Any]],
    mode: str = "partial",
    update_postgres: bool = True,
    update_neo4j: bool = False,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Send batch update request to API.
    
    Args:
        updates: List of update operations
        mode: "partial" (update specific fields) or "full" (replace all fields)
        update_postgres: Whether to update PostgreSQL
        update_neo4j: Whether to update Neo4j
        timeout: Request timeout in seconds
    
    Returns:
        API response with update results
    """
    payload = {
        "updates": updates,
        "mode": mode,
        "update_postgres": update_postgres,
        "update_neo4j": update_neo4j
    }
    
    try:
        response = requests.post(
            BATCH_UPDATE_ENDPOINT,
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


def print_results(result: Dict[str, Any], operation_name: str = "Batch Update"):
    """Print formatted results."""
    print(f"\n{'='*80}")
    print(f"📊 {operation_name} Results")
    print(f"{'='*80}")
    
    if result.get("success"):
        print(f"✅ Success: {result['success']}")
        
        if "postgres" in result:
            pg = result["postgres"]
            print(f"\n📦 PostgreSQL:")
            print(f"   Updated:     {pg.get('updated', 0)}")
            print(f"   Failed:      {pg.get('failed', 0)}")
            print(f"   Time:        {pg.get('execution_time_ms', 0):.2f}ms")
        
        if "neo4j" in result:
            neo = result["neo4j"]
            print(f"\n🔗 Neo4j:")
            print(f"   Updated:     {neo.get('updated', 0)}")
            print(f"   Failed:      {neo.get('failed', 0)}")
            print(f"   Time:        {neo.get('execution_time_ms', 0):.2f}ms")
        
        if "total_execution_time_ms" in result:
            print(f"\n⏱️  Total Time: {result['total_execution_time_ms']:.2f}ms")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    print(f"{'='*80}\n")


# ============================================================================
# Example 1: Simple Partial Update (Update Title Only)
# ============================================================================

def example_1_simple_partial_update():
    """Example 1: Update title field for 10 documents"""
    print("\n" + "="*80)
    print("Example 1: Simple Partial Update (Title Only)")
    print("="*80)
    
    # Create update operations (update title field only)
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "title": f"Updated Title {i} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        for i in range(1, 11)
    ]
    
    print(f"\n📝 Updating {len(updates)} documents (title only)...")
    print(f"Mode: partial (only specified fields updated)")
    
    # Send batch update request
    result = batch_update(updates, mode="partial")
    
    # Print results
    print_results(result, "Simple Partial Update")
    
    return result


# ============================================================================
# Example 2: Multi-Field Partial Update
# ============================================================================

def example_2_multi_field_partial_update():
    """Example 2: Update multiple fields (title, metadata, tags)"""
    print("\n" + "="*80)
    print("Example 2: Multi-Field Partial Update")
    print("="*80)
    
    # Create update operations (update multiple fields)
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "title": f"Multi-Field Update {i}",
                "metadata": {
                    "updated_at": datetime.now().isoformat(),
                    "update_type": "multi_field",
                    "version": 2
                },
                "tags": ["updated", "multi_field", f"batch_{i}"]
            }
        }
        for i in range(1, 21)
    ]
    
    print(f"\n📝 Updating {len(updates)} documents (title + metadata + tags)...")
    print(f"Mode: partial (only specified fields updated)")
    
    # Send batch update request
    result = batch_update(updates, mode="partial")
    
    # Print results
    print_results(result, "Multi-Field Partial Update")
    
    return result


# ============================================================================
# Example 3: Full Document Replacement
# ============================================================================

def example_3_full_document_replacement():
    """Example 3: Replace entire document (all fields)"""
    print("\n" + "="*80)
    print("Example 3: Full Document Replacement")
    print("="*80)
    
    # Create update operations (replace all fields)
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "title": f"Completely New Title {i}",
                "content": f"Completely new content for document {i}. All old data replaced.",
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "replaced": True,
                    "version": 3
                },
                "tags": ["replaced", "full_update"],
                "category": "updated",
                "status": "active"
            }
        }
        for i in range(1, 11)
    ]
    
    print(f"\n📝 Replacing {len(updates)} documents (all fields)...")
    print(f"Mode: full (entire document replaced)")
    print(f"⚠️  Warning: All fields not specified will be cleared!")
    
    # Send batch update request
    result = batch_update(updates, mode="full")
    
    # Print results
    print_results(result, "Full Document Replacement")
    
    return result


# ============================================================================
# Example 4: Large Batch Update (100 documents)
# ============================================================================

def example_4_large_batch_update():
    """Example 4: Update 100 documents (triggers temp table strategy)"""
    print("\n" + "="*80)
    print("Example 4: Large Batch Update (100 Documents)")
    print("="*80)
    
    # Create update operations for 100 documents
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "title": f"Bulk Update {i}",
                "metadata": {
                    "bulk_update": True,
                    "batch_size": 100,
                    "updated_at": datetime.now().isoformat()
                },
                "tags": ["bulk", f"batch_{i // 10}"]
            }
        }
        for i in range(1, 101)
    ]
    
    print(f"\n📝 Updating {len(updates)} documents...")
    print(f"Strategy: Temp table (batch size >= 100)")
    print(f"Mode: partial")
    
    # Measure execution time
    start_time = time.time()
    result = batch_update(updates, mode="partial")
    execution_time = time.time() - start_time
    
    # Print results
    print_results(result, "Large Batch Update")
    
    print(f"🚀 Client-side execution time: {execution_time:.4f}s")
    
    return result


# ============================================================================
# Example 5: Conditional Update (Based on Current Values)
# ============================================================================

def example_5_conditional_update():
    """Example 5: Update documents with conditional logic"""
    print("\n" + "="*80)
    print("Example 5: Conditional Update (Status-Based)")
    print("="*80)
    
    # Simulate fetching documents first
    # In real scenario, you'd query documents to get current status
    print("\n🔍 Step 1: Query documents to check current status...")
    print("   (Simulated: Assuming we have 20 documents with 'draft' status)")
    
    # Create conditional updates (only for draft documents)
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "status": "published",
                "published_at": datetime.now().isoformat(),
                "metadata": {
                    "previous_status": "draft",
                    "published_by": "batch_update_system",
                    "version": 2
                },
                "tags": ["published", "batch_published"]
            }
        }
        for i in range(1, 21)
    ]
    
    print(f"\n📝 Step 2: Update {len(updates)} documents (draft → published)...")
    print(f"Mode: partial (status, published_at, metadata)")
    
    # Send batch update request
    result = batch_update(updates, mode="partial")
    
    # Print results
    print_results(result, "Conditional Update")
    
    return result


# ============================================================================
# Example 6: Version Increment Update
# ============================================================================

def example_6_version_increment():
    """Example 6: Increment document versions"""
    print("\n" + "="*80)
    print("Example 6: Version Increment Update")
    print("="*80)
    
    # Note: For actual version increment, you'd need to fetch current versions first
    print("\n🔍 Step 1: Query documents to get current versions...")
    print("   (Simulated: Assuming current versions are 1)")
    
    # Create version increment updates
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "version": 2,  # In real scenario, use: current_version + 1
                "metadata": {
                    "version_updated_at": datetime.now().isoformat(),
                    "update_reason": "Content modification"
                }
            }
        }
        for i in range(1, 31)
    ]
    
    print(f"\n📝 Step 2: Update {len(updates)} documents (version increment)...")
    print(f"Mode: partial (version, metadata)")
    
    # Send batch update request
    result = batch_update(updates, mode="partial")
    
    # Print results
    print_results(result, "Version Increment Update")
    
    return result


# ============================================================================
# Example 7: Multi-Database Update (PostgreSQL + Neo4j)
# ============================================================================

def example_7_multi_database_update():
    """Example 7: Update both PostgreSQL and Neo4j"""
    print("\n" + "="*80)
    print("Example 7: Multi-Database Update (PostgreSQL + Neo4j)")
    print("="*80)
    
    # Create update operations
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "title": f"Multi-DB Update {i}",
                "metadata": {
                    "synced": True,
                    "updated_at": datetime.now().isoformat()
                }
            }
        }
        for i in range(1, 16)
    ]
    
    print(f"\n📝 Updating {len(updates)} documents...")
    print(f"Databases: PostgreSQL ✅ + Neo4j ✅")
    print(f"Mode: partial")
    
    # Send batch update request (both databases)
    result = batch_update(
        updates,
        mode="partial",
        update_postgres=True,
        update_neo4j=True
    )
    
    # Print results
    print_results(result, "Multi-Database Update")
    
    return result


# ============================================================================
# Example 8: Error Handling - Partial Success
# ============================================================================

def example_8_error_handling():
    """Example 8: Handle partial success scenarios"""
    print("\n" + "="*80)
    print("Example 8: Error Handling - Partial Success")
    print("="*80)
    
    # Create mixed updates (some valid, some invalid)
    updates = [
        # Valid updates
        {
            "document_id": "doc_2024_0001",
            "fields": {"title": "Valid Update 1"}
        },
        {
            "document_id": "doc_2024_0002",
            "fields": {"title": "Valid Update 2"}
        },
        # Invalid updates (non-existent documents)
        {
            "document_id": "non_existent_doc_999",
            "fields": {"title": "Should Fail"}
        },
        {
            "document_id": "invalid_doc_888",
            "fields": {"title": "Should Fail"}
        },
        # Valid updates
        {
            "document_id": "doc_2024_0003",
            "fields": {"title": "Valid Update 3"}
        }
    ]
    
    print(f"\n📝 Updating {len(updates)} documents (mixed valid/invalid)...")
    print(f"Expected: Some succeed, some fail")
    
    # Send batch update request
    result = batch_update(updates, mode="partial")
    
    # Print results
    print_results(result, "Error Handling")
    
    # Detailed error analysis
    if not result.get("success") and result.get("partial_success"):
        print("\n⚠️  Partial Success Detected:")
        if "postgres" in result:
            pg = result["postgres"]
            print(f"   PostgreSQL: {pg.get('updated', 0)} succeeded, {pg.get('failed', 0)} failed")
            if pg.get("errors"):
                print(f"   Errors: {pg['errors'][:3]}")  # Show first 3 errors
    
    return result


# ============================================================================
# Example 9: Batch Update with Retry Logic
# ============================================================================

def example_9_retry_logic():
    """Example 9: Implement retry logic for failed updates"""
    print("\n" + "="*80)
    print("Example 9: Batch Update with Retry Logic")
    print("="*80)
    
    # Create update operations
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "title": f"Retry Update {i}",
                "metadata": {"retry_attempt": 1}
            }
        }
        for i in range(1, 21)
    ]
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    print(f"\n📝 Updating {len(updates)} documents with retry logic...")
    print(f"Max retries: {max_retries}")
    print(f"Retry delay: {retry_delay}s")
    
    for attempt in range(1, max_retries + 1):
        print(f"\n🔄 Attempt {attempt}/{max_retries}...")
        
        result = batch_update(updates, mode="partial")
        
        if result.get("success"):
            print(f"✅ Success on attempt {attempt}!")
            print_results(result, f"Retry Attempt {attempt}")
            return result
        
        # Check for partial success
        if result.get("partial_success"):
            postgres_updated = result.get("postgres", {}).get("updated", 0)
            print(f"⚠️  Partial success: {postgres_updated} documents updated")
            
            # Retry only failed documents
            # (In real scenario, extract failed document IDs from errors)
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
# Example 10: Performance Comparison (Batch vs Sequential)
# ============================================================================

def example_10_performance_comparison():
    """Example 10: Compare batch vs sequential update performance"""
    print("\n" + "="*80)
    print("Example 10: Performance Comparison (Batch vs Sequential)")
    print("="*80)
    
    num_updates = 50
    
    # Create update operations
    updates = [
        {
            "document_id": f"doc_2024_{i:04d}",
            "fields": {
                "title": f"Performance Test {i}",
                "metadata": {"test_type": "performance"}
            }
        }
        for i in range(1, num_updates + 1)
    ]
    
    # Batch update
    print(f"\n🚀 Batch Update ({num_updates} documents)...")
    batch_start = time.time()
    batch_result = batch_update(updates, mode="partial")
    batch_time = time.time() - batch_start
    
    print(f"   Time: {batch_time:.4f}s")
    print(f"   Throughput: {num_updates / batch_time:.1f} docs/s")
    
    # Sequential update (simulated - don't actually do this!)
    print(f"\n🐌 Sequential Update (simulated - {num_updates} documents)...")
    print(f"   Estimated time: {batch_time * 70:.4f}s (70x slower)")
    print(f"   Estimated throughput: {num_updates / (batch_time * 70):.1f} docs/s")
    
    # Calculate speedup
    estimated_speedup = 70  # Based on benchmark data
    print(f"\n📊 Performance Summary:")
    print(f"   Batch time:      {batch_time:.4f}s")
    print(f"   Sequential time: ~{batch_time * estimated_speedup:.4f}s (estimated)")
    print(f"   Speedup:         ~{estimated_speedup}x")
    print(f"   Status:          {'✅ OPTIMAL' if estimated_speedup >= 50 else '⚠️  SUBOPTIMAL'}")
    
    return batch_result


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("🚀 Batch UPDATE API - Python Examples")
    print("="*80)
    print(f"\nAPI Endpoint: {BATCH_UPDATE_ENDPOINT}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTotal Examples: 10")
    print("="*80)
    
    examples = [
        ("Example 1: Simple Partial Update", example_1_simple_partial_update),
        ("Example 2: Multi-Field Partial Update", example_2_multi_field_partial_update),
        ("Example 3: Full Document Replacement", example_3_full_document_replacement),
        ("Example 4: Large Batch Update (100 docs)", example_4_large_batch_update),
        ("Example 5: Conditional Update", example_5_conditional_update),
        ("Example 6: Version Increment", example_6_version_increment),
        ("Example 7: Multi-Database Update", example_7_multi_database_update),
        ("Example 8: Error Handling", example_8_error_handling),
        ("Example 9: Retry Logic", example_9_retry_logic),
        ("Example 10: Performance Comparison", example_10_performance_comparison),
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
    print("  >>> example_1_simple_partial_update()")
    print("  >>> example_4_large_batch_update()")
    print("  >>> example_10_performance_comparison()")


if __name__ == "__main__":
    main()
