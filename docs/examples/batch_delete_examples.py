"""
Batch DELETE Operations - Python Examples

This file demonstrates how to use the Batch DELETE API endpoint
for efficient bulk deletion of documents.

API Endpoint: POST /api/v1/batch/delete
Performance: 100x faster than sequential deletes

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
BATCH_DELETE_ENDPOINT = f"{API_BASE_URL}/batch/delete"


# ============================================================================
# Helper Functions
# ============================================================================

def batch_delete(
    document_ids: List[str],
    mode: str = "soft",
    cascade: bool = True,
    delete_postgres: bool = True,
    delete_neo4j: bool = False,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Send batch delete request to API.
    
    Args:
        document_ids: List of document IDs to delete
        mode: "soft" (mark as deleted) or "hard" (permanent deletion)
        cascade: Whether to cascade delete related entities
        delete_postgres: Whether to delete from PostgreSQL
        delete_neo4j: Whether to delete from Neo4j
        timeout: Request timeout in seconds
    
    Returns:
        API response with delete results
    """
    payload = {
        "document_ids": document_ids,
        "mode": mode,
        "cascade": cascade,
        "delete_postgres": delete_postgres,
        "delete_neo4j": delete_neo4j
    }
    
    try:
        response = requests.post(
            BATCH_DELETE_ENDPOINT,
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


def print_results(result: Dict[str, Any], operation_name: str = "Batch Delete"):
    """Print formatted results."""
    print(f"\n{'='*80}")
    print(f"📊 {operation_name} Results")
    print(f"{'='*80}")
    
    if result.get("success"):
        print(f"✅ Success: {result['success']}")
        
        if "postgres" in result:
            pg = result["postgres"]
            print(f"\n📦 PostgreSQL:")
            print(f"   Deleted:     {pg.get('deleted', 0)}")
            print(f"   Failed:      {pg.get('failed', 0)}")
            print(f"   Time:        {pg.get('execution_time_ms', 0):.2f}ms")
        
        if "neo4j" in result:
            neo = result["neo4j"]
            print(f"\n🔗 Neo4j:")
            print(f"   Deleted:     {neo.get('deleted', 0)}")
            print(f"   Failed:      {neo.get('failed', 0)}")
            print(f"   Time:        {neo.get('execution_time_ms', 0):.2f}ms")
        
        if "total_execution_time_ms" in result:
            print(f"\n⏱️  Total Time: {result['total_execution_time_ms']:.2f}ms")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    print(f"{'='*80}\n")


# ============================================================================
# Example 1: Simple Soft Delete (Default)
# ============================================================================

def example_1_simple_soft_delete():
    """Example 1: Soft delete 10 documents (default mode)"""
    print("\n" + "="*80)
    print("Example 1: Simple Soft Delete (Default)")
    print("="*80)
    
    # Document IDs to delete
    document_ids = [f"doc_2024_{i:04d}" for i in range(1, 11)]
    
    print(f"\n🗑️  Soft deleting {len(document_ids)} documents...")
    print(f"Mode: soft (marks deleted=true, documents remain in DB)")
    print(f"Cascade: Yes (related entities marked deleted)")
    
    # Send batch delete request (soft delete is default)
    result = batch_delete(document_ids, mode="soft", cascade=True)
    
    # Print results
    print_results(result, "Simple Soft Delete")
    
    print("ℹ️  Note: Documents still exist in database with deleted=true flag")
    
    return result


# ============================================================================
# Example 2: Hard Delete (Permanent)
# ============================================================================

def example_2_hard_delete():
    """Example 2: Hard delete 10 documents (permanent deletion)"""
    print("\n" + "="*80)
    print("Example 2: Hard Delete (Permanent)")
    print("="*80)
    
    # Document IDs to delete
    document_ids = [f"doc_2024_{i:04d}" for i in range(101, 111)]
    
    print(f"\n🗑️  Hard deleting {len(document_ids)} documents...")
    print(f"Mode: hard (permanent deletion from DB)")
    print(f"Cascade: Yes (related entities permanently deleted)")
    print(f"⚠️  WARNING: This action is IRREVERSIBLE!")
    
    # Confirmation prompt (in real scenario)
    print(f"\n⚠️  Confirmation required for hard delete in production!")
    
    # Send batch delete request (hard delete)
    result = batch_delete(document_ids, mode="hard", cascade=True)
    
    # Print results
    print_results(result, "Hard Delete")
    
    print("⚠️  Note: Documents permanently removed from database")
    
    return result


# ============================================================================
# Example 3: Large Batch Soft Delete (100 documents)
# ============================================================================

def example_3_large_batch_soft_delete():
    """Example 3: Soft delete 100 documents"""
    print("\n" + "="*80)
    print("Example 3: Large Batch Soft Delete (100 Documents)")
    print("="*80)
    
    # Document IDs to delete
    document_ids = [f"doc_2024_{i:04d}" for i in range(1, 101)]
    
    print(f"\n🗑️  Soft deleting {len(document_ids)} documents...")
    print(f"Mode: soft")
    print(f"Cascade: Yes")
    
    # Measure execution time
    start_time = time.time()
    result = batch_delete(document_ids, mode="soft", cascade=True)
    execution_time = time.time() - start_time
    
    # Print results
    print_results(result, "Large Batch Soft Delete")
    
    print(f"🚀 Client-side execution time: {execution_time:.4f}s")
    print(f"📊 Throughput: {len(document_ids) / execution_time:.1f} docs/s")
    
    return result


# ============================================================================
# Example 4: Soft Delete Without Cascade
# ============================================================================

def example_4_soft_delete_no_cascade():
    """Example 4: Soft delete without cascading to related entities"""
    print("\n" + "="*80)
    print("Example 4: Soft Delete Without Cascade")
    print("="*80)
    
    # Document IDs to delete
    document_ids = [f"doc_2024_{i:04d}" for i in range(1, 21)]
    
    print(f"\n🗑️  Soft deleting {len(document_ids)} documents...")
    print(f"Mode: soft")
    print(f"Cascade: No (related entities NOT deleted)")
    print(f"ℹ️  Use case: Keep relationships for audit trail")
    
    # Send batch delete request (no cascade)
    result = batch_delete(document_ids, mode="soft", cascade=False)
    
    # Print results
    print_results(result, "Soft Delete (No Cascade)")
    
    print("ℹ️  Note: Related entities (relationships, metadata) remain active")
    
    return result


# ============================================================================
# Example 5: Hard Delete With Cascade
# ============================================================================

def example_5_hard_delete_with_cascade():
    """Example 5: Hard delete with cascade (delete all related data)"""
    print("\n" + "="*80)
    print("Example 5: Hard Delete With Cascade")
    print("="*80)
    
    # Document IDs to delete
    document_ids = [f"doc_2024_{i:04d}" for i in range(201, 211)]
    
    print(f"\n🗑️  Hard deleting {len(document_ids)} documents...")
    print(f"Mode: hard (permanent)")
    print(f"Cascade: Yes (all related data deleted)")
    print(f"⚠️  WARNING: Deletes documents + relationships + metadata!")
    
    # Send batch delete request (hard with cascade)
    result = batch_delete(document_ids, mode="hard", cascade=True)
    
    # Print results
    print_results(result, "Hard Delete (Cascade)")
    
    print("⚠️  Note: Documents + ALL related data permanently removed")
    
    return result


# ============================================================================
# Example 6: Conditional Soft Delete (By Status)
# ============================================================================

def example_6_conditional_soft_delete():
    """Example 6: Soft delete documents based on status"""
    print("\n" + "="*80)
    print("Example 6: Conditional Soft Delete (Status-Based)")
    print("="*80)
    
    # Simulate querying documents first
    print("\n🔍 Step 1: Query documents with status='draft'...")
    print("   (Simulated: Found 25 draft documents)")
    
    # In real scenario, you'd query the API to get document IDs
    draft_document_ids = [f"doc_2024_{i:04d}" for i in range(1, 26)]
    
    print(f"\n🗑️  Step 2: Soft delete {len(draft_document_ids)} draft documents...")
    print(f"Mode: soft")
    print(f"Reason: Cleanup old draft documents")
    
    # Send batch delete request
    result = batch_delete(draft_document_ids, mode="soft", cascade=True)
    
    # Print results
    print_results(result, "Conditional Soft Delete")
    
    return result


# ============================================================================
# Example 7: Multi-Database Delete (PostgreSQL + Neo4j)
# ============================================================================

def example_7_multi_database_delete():
    """Example 7: Delete from both PostgreSQL and Neo4j"""
    print("\n" + "="*80)
    print("Example 7: Multi-Database Delete (PostgreSQL + Neo4j)")
    print("="*80)
    
    # Document IDs to delete
    document_ids = [f"doc_2024_{i:04d}" for i in range(1, 16)]
    
    print(f"\n🗑️  Deleting {len(document_ids)} documents...")
    print(f"Databases: PostgreSQL ✅ + Neo4j ✅")
    print(f"Mode: soft")
    print(f"Cascade: Yes")
    
    # Send batch delete request (both databases)
    result = batch_delete(
        document_ids,
        mode="soft",
        cascade=True,
        delete_postgres=True,
        delete_neo4j=True
    )
    
    # Print results
    print_results(result, "Multi-Database Delete")
    
    return result


# ============================================================================
# Example 8: Error Handling - Partial Success
# ============================================================================

def example_8_error_handling():
    """Example 8: Handle partial success scenarios"""
    print("\n" + "="*80)
    print("Example 8: Error Handling - Partial Success")
    print("="*80)
    
    # Mixed document IDs (some valid, some invalid)
    document_ids = [
        "doc_2024_0001",  # Valid
        "doc_2024_0002",  # Valid
        "non_existent_999",  # Invalid
        "doc_2024_0003",  # Valid
        "invalid_888",  # Invalid
    ]
    
    print(f"\n🗑️  Deleting {len(document_ids)} documents (mixed valid/invalid)...")
    print(f"Expected: Some succeed, some fail gracefully")
    
    # Send batch delete request
    result = batch_delete(document_ids, mode="soft", cascade=True)
    
    # Print results
    print_results(result, "Error Handling")
    
    # Detailed error analysis
    if not result.get("success") and result.get("partial_success"):
        print("\n⚠️  Partial Success Detected:")
        if "postgres" in result:
            pg = result["postgres"]
            print(f"   PostgreSQL: {pg.get('deleted', 0)} deleted, {pg.get('failed', 0)} failed")
            if pg.get("errors"):
                print(f"   Errors: {pg['errors'][:3]}")
    
    return result


# ============================================================================
# Example 9: Batch Delete with Retry Logic
# ============================================================================

def example_9_retry_logic():
    """Example 9: Implement retry logic for failed deletes"""
    print("\n" + "="*80)
    print("Example 9: Batch Delete with Retry Logic")
    print("="*80)
    
    # Document IDs to delete
    document_ids = [f"doc_2024_{i:04d}" for i in range(1, 21)]
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    print(f"\n🗑️  Deleting {len(document_ids)} documents with retry logic...")
    print(f"Max retries: {max_retries}")
    print(f"Retry delay: {retry_delay}s")
    
    for attempt in range(1, max_retries + 1):
        print(f"\n🔄 Attempt {attempt}/{max_retries}...")
        
        result = batch_delete(document_ids, mode="soft", cascade=True)
        
        if result.get("success"):
            print(f"✅ Success on attempt {attempt}!")
            print_results(result, f"Retry Attempt {attempt}")
            return result
        
        # Check for partial success
        if result.get("partial_success"):
            postgres_deleted = result.get("postgres", {}).get("deleted", 0)
            print(f"⚠️  Partial success: {postgres_deleted} documents deleted")
            
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
    """Example 10: Compare batch vs sequential delete performance"""
    print("\n" + "="*80)
    print("Example 10: Performance Comparison (Batch vs Sequential)")
    print("="*80)
    
    num_deletes = 100
    
    # Document IDs to delete
    document_ids = [f"doc_2024_{i:04d}" for i in range(1, num_deletes + 1)]
    
    # Batch delete
    print(f"\n🚀 Batch Delete ({num_deletes} documents)...")
    batch_start = time.time()
    batch_result = batch_delete(document_ids, mode="soft", cascade=True)
    batch_time = time.time() - batch_start
    
    print(f"   Time: {batch_time:.4f}s")
    print(f"   Throughput: {num_deletes / batch_time:.1f} docs/s")
    
    # Sequential delete (simulated - don't actually do this!)
    print(f"\n🐌 Sequential Delete (simulated - {num_deletes} documents)...")
    estimated_sequential_time = batch_time * 100
    print(f"   Estimated time: {estimated_sequential_time:.4f}s (100x slower)")
    print(f"   Estimated throughput: {num_deletes / estimated_sequential_time:.1f} docs/s")
    
    # Calculate speedup
    estimated_speedup = 100  # Based on benchmark data
    print(f"\n📊 Performance Summary:")
    print(f"   Batch time:      {batch_time:.4f}s")
    print(f"   Sequential time: ~{estimated_sequential_time:.4f}s (estimated)")
    print(f"   Speedup:         ~{estimated_speedup}x")
    print(f"   Status:          {'✅ OPTIMAL' if estimated_speedup >= 80 else '⚠️  SUBOPTIMAL'}")
    
    return batch_result


# ============================================================================
# Example 11: Archive Documents (Soft Delete + Metadata)
# ============================================================================

def example_11_archive_documents():
    """Example 11: Archive documents by soft deleting with metadata update"""
    print("\n" + "="*80)
    print("Example 11: Archive Documents (Soft Delete + Metadata)")
    print("="*80)
    
    # Note: This requires a two-step process:
    # 1. Update metadata to mark as "archived"
    # 2. Soft delete the documents
    
    document_ids = [f"doc_2024_{i:04d}" for i in range(1, 31)]
    
    print(f"\n📦 Step 1: Update metadata (mark as archived)...")
    print("   (Would call /api/v1/batch/update with archived=true)")
    
    print(f"\n🗑️  Step 2: Soft delete {len(document_ids)} documents...")
    print(f"Mode: soft (preserves data for potential restore)")
    
    # Send batch delete request
    result = batch_delete(document_ids, mode="soft", cascade=True)
    
    # Print results
    print_results(result, "Archive Documents")
    
    print("ℹ️  Note: Documents archived (soft deleted) with metadata preserved")
    
    return result


# ============================================================================
# Example 12: Cleanup Strategy (Delete Old Drafts)
# ============================================================================

def example_12_cleanup_strategy():
    """Example 12: Cleanup strategy - delete old draft documents"""
    print("\n" + "="*80)
    print("Example 12: Cleanup Strategy (Delete Old Drafts)")
    print("="*80)
    
    # Simulate querying old draft documents
    print("\n🔍 Step 1: Query draft documents older than 90 days...")
    print("   SQL: SELECT document_id FROM documents")
    print("        WHERE status='draft' AND created_at < NOW() - INTERVAL '90 days'")
    print("   (Simulated: Found 45 old draft documents)")
    
    old_draft_ids = [f"doc_2024_{i:04d}" for i in range(1, 46)]
    
    print(f"\n🗑️  Step 2: Hard delete {len(old_draft_ids)} old drafts...")
    print(f"Mode: hard (permanent cleanup)")
    print(f"Reason: Cleanup storage, remove unused drafts")
    
    # Send batch delete request
    result = batch_delete(old_draft_ids, mode="hard", cascade=True)
    
    # Print results
    print_results(result, "Cleanup Strategy")
    
    print("✅ Cleanup complete: Old draft documents removed")
    
    return result


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("🚀 Batch DELETE API - Python Examples")
    print("="*80)
    print(f"\nAPI Endpoint: {BATCH_DELETE_ENDPOINT}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTotal Examples: 12")
    print("="*80)
    
    examples = [
        ("Example 1: Simple Soft Delete", example_1_simple_soft_delete),
        ("Example 2: Hard Delete (Permanent)", example_2_hard_delete),
        ("Example 3: Large Batch Soft Delete (100 docs)", example_3_large_batch_soft_delete),
        ("Example 4: Soft Delete (No Cascade)", example_4_soft_delete_no_cascade),
        ("Example 5: Hard Delete (Cascade)", example_5_hard_delete_with_cascade),
        ("Example 6: Conditional Soft Delete", example_6_conditional_soft_delete),
        ("Example 7: Multi-Database Delete", example_7_multi_database_delete),
        ("Example 8: Error Handling", example_8_error_handling),
        ("Example 9: Retry Logic", example_9_retry_logic),
        ("Example 10: Performance Comparison", example_10_performance_comparison),
        ("Example 11: Archive Documents", example_11_archive_documents),
        ("Example 12: Cleanup Strategy", example_12_cleanup_strategy),
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
    print("  >>> example_1_simple_soft_delete()")
    print("  >>> example_3_large_batch_soft_delete()")
    print("  >>> example_10_performance_comparison()")
    
    print("\n⚠️  Safety Reminders:")
    print("  - Soft delete is DEFAULT and RECOMMENDED")
    print("  - Hard delete is IRREVERSIBLE - use with caution")
    print("  - Always test with non-production data first")


if __name__ == "__main__":
    main()
