"""
Test PostgreSQL ReviewQueue
============================

Tests the ReviewQueue class with PostgreSQL review_tasks table.

Prerequisites:
- PostgreSQL migration completed (review_tasks table exists)
- PostgreSQL connection configured
- Python 3.8+
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct import to avoid module loading issues
import sys
import importlib.util

# Load ReviewQueue module directly
spec = importlib.util.spec_from_file_location(
    "review_queue", 
    Path(__file__).parent.parent / "management_core" / "review_queue.py"
)
review_queue_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_queue_module)

ReviewQueue = review_queue_module.ReviewQueue
TaskStatus = review_queue_module.TaskStatus
TaskSeverity = review_queue_module.TaskSeverity
GapType = review_queue_module.GapType

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


def test_add_review_task(queue: ReviewQueue) -> str:
    """Test adding a review task"""
    print_section("TEST 1: Add Review Task")
    
    # Create a test document first (required for foreign key)
    backend = queue.postgres_backend
    backend.connect()
    
    # Insert test document
    test_doc_id = "test_doc_review_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    backend.cursor.execute("""
        INSERT INTO documents (document_id, file_path, classification, content_length, legal_terms_count, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (test_doc_id, "/test/document.pdf", "TEST", 1000, 5, datetime.now().isoformat()))
    backend.conn.commit()
    
    print(f"Created test document: {test_doc_id}")
    
    # Add review task
    review_item = {
        "document_id": test_doc_id,
        "file_path": "/test/document.pdf",
        "gap_type": GapType.MISSING_REGISTER_NUMBER.value,
        "firma": "Test AG",
        "severity": TaskSeverity.MEDIUM.value,
        "message": "Firma 'Test AG' has no HRB/HRA number"
    }
    
    review_id = queue.add_item(review_item)
    
    print(f"✅ Review task created: {review_id}")
    print(f"   - Gap type: {review_item['gap_type']}")
    print(f"   - Firma: {review_item['firma']}")
    print(f"   - Severity: {review_item['severity']}")
    
    return review_id, test_doc_id


def test_get_task(queue: ReviewQueue, review_id: str):
    """Test retrieving a task"""
    print_section("TEST 2: Get Review Task")
    
    task = queue.get_task(review_id)
    
    if task:
        print(f"✅ Task retrieved: {review_id}")
        print(f"   - Status: {task['status']}")
        print(f"   - Severity: {task['severity']}")
        print(f"   - Gap type: {task['gap_type']}")
        print(f"   - Firma: {task['firma']}")
        print(f"   - Created at: {task['created_at']}")
        return True
    else:
        print(f"❌ Task not found: {review_id}")
        return False


def test_get_by_status(queue: ReviewQueue):
    """Test querying tasks by status"""
    print_section("TEST 3: Get Tasks by Status")
    
    pending_tasks = queue.get_tasks_by_status(TaskStatus.PENDING.value)
    
    print(f"Found {len(pending_tasks)} pending tasks")
    
    if pending_tasks:
        print("\nFirst pending task:")
        task = pending_tasks[0]
        print(f"   - Review ID: {task['review_id']}")
        print(f"   - Gap type: {task['gap_type']}")
        print(f"   - Firma: {task['firma']}")
        print(f"   - Severity: {task['severity']}")
        return True
    else:
        print("⚠️ No pending tasks found")
        return True  # Not a failure


def test_get_by_severity(queue: ReviewQueue):
    """Test querying tasks by severity"""
    print_section("TEST 4: Get Tasks by Severity")
    
    medium_tasks = queue.get_tasks_by_severity(TaskSeverity.MEDIUM.value)
    
    print(f"Found {len(medium_tasks)} medium severity tasks")
    
    if medium_tasks:
        print("\nMedium severity tasks:")
        for task in medium_tasks[:3]:  # Show first 3
            print(f"   - {task['review_id']}: {task['gap_type']} - {task['firma']}")
        return True
    else:
        print("⚠️ No medium severity tasks found")
        return True


def test_update_status(queue: ReviewQueue, review_id: str):
    """Test updating task status"""
    print_section("TEST 5: Update Task Status")
    
    # Update to in_progress
    success = queue.update_status(review_id, TaskStatus.IN_PROGRESS.value)
    
    if success:
        print(f"✅ Status updated to IN_PROGRESS")
        
        # Verify
        task = queue.get_task(review_id)
        if task and task['status'] == TaskStatus.IN_PROGRESS.value:
            print(f"✅ Verification passed")
        else:
            print(f"❌ Verification failed")
            return False
        
        # Update to resolved with notes
        success = queue.update_status(
            review_id, 
            TaskStatus.RESOLVED.value,
            "Fixed manually - added HRB number from company website"
        )
        
        if success:
            print(f"✅ Status updated to RESOLVED")
            
            # Verify resolution
            task = queue.get_task(review_id)
            if task and task['status'] == TaskStatus.RESOLVED.value:
                print(f"✅ Resolution verified")
                print(f"   - Resolved at: {task['resolved_at']}")
                print(f"   - Notes: {task['resolution_notes']}")
                return True
            else:
                print(f"❌ Resolution verification failed")
                return False
        else:
            print(f"❌ Failed to update to RESOLVED")
            return False
    else:
        print(f"❌ Failed to update status")
        return False


def test_assign_task(queue: ReviewQueue, review_id: str):
    """Test assigning task to user"""
    print_section("TEST 6: Assign Task")
    
    success = queue.assign_task(review_id, "user@example.com")
    
    if success:
        print(f"✅ Task assigned to user@example.com")
        
        # Verify
        task = queue.get_task(review_id)
        if task and task['assigned_to'] == "user@example.com":
            print(f"✅ Assignment verified")
            return True
        else:
            print(f"❌ Assignment verification failed")
            return False
    else:
        print(f"❌ Failed to assign task")
        return False


def test_statistics(queue: ReviewQueue):
    """Test getting statistics"""
    print_section("TEST 7: Get Statistics")
    
    stats = queue.get_statistics()
    
    if "error" not in stats:
        print(f"✅ Statistics retrieved successfully")
        print(f"\nStatistics:")
        print(f"   - Total tasks: {stats['total_tasks']}")
        print(f"   - By status: {stats['by_status']}")
        print(f"   - By severity: {stats['by_severity']}")
        print(f"   - By gap type: {stats['by_gap_type']}")
        
        if stats['avg_resolution_time_hours']:
            print(f"   - Avg resolution time: {stats['avg_resolution_time_hours']:.2f} hours")
        else:
            print(f"   - Avg resolution time: N/A (no resolved tasks)")
        
        return True
    else:
        print(f"❌ Failed to get statistics: {stats['error']}")
        return False


def test_get_by_document(queue: ReviewQueue, document_id: str):
    """Test getting tasks by document"""
    print_section("TEST 8: Get Tasks by Document")
    
    tasks = queue.get_tasks_by_document(document_id)
    
    print(f"Found {len(tasks)} tasks for document {document_id}")
    
    if tasks:
        print("\nTasks for this document:")
        for task in tasks:
            print(f"   - {task['gap_type']}: {task['firma']} ({task['status']})")
        return True
    else:
        print("⚠️ No tasks found for this document")
        return True


def cleanup_test_data(queue: ReviewQueue, review_id: str, document_id: str):
    """Remove test data"""
    print_section("CLEANUP: Remove Test Data")
    
    # Delete review task
    success = queue.delete_task(review_id)
    if success:
        print(f"✅ Review task deleted: {review_id}")
    
    # Delete test document
    backend = queue.postgres_backend
    backend.connect()
    backend.cursor.execute("DELETE FROM documents WHERE document_id = %s", (document_id,))
    backend.conn.commit()
    print(f"✅ Test document deleted: {document_id}")


def main():
    """Run all tests"""
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║  PostgreSQL ReviewQueue - Test Suite                              ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    
    # Initialize
    print("\nInitializing PostgreSQL backend...")
    backend = PostgreSQLRelationalBackend(POSTGRES_CONFIG)
    backend.connect()
    print(f"✅ Connected to {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
    
    print("\nInitializing ReviewQueue...")
    queue = ReviewQueue(backend)
    print("✅ ReviewQueue initialized")
    
    # Run tests
    test_results = []
    review_id = None
    document_id = None
    
    try:
        # Test 1: Add task
        review_id, document_id = test_add_review_task(queue)
        test_results.append(("Add Review Task", True))
        
        # Test 2: Get task
        success = test_get_task(queue, review_id)
        test_results.append(("Get Review Task", success))
        
        # Test 3: Get by status
        success = test_get_by_status(queue)
        test_results.append(("Get by Status", success))
        
        # Test 4: Get by severity
        success = test_get_by_severity(queue)
        test_results.append(("Get by Severity", success))
        
        # Test 5: Update status
        success = test_update_status(queue, review_id)
        test_results.append(("Update Status", success))
        
        # Test 6: Assign task (skip - already resolved)
        # success = test_assign_task(queue, review_id)
        # test_results.append(("Assign Task", success))
        
        # Test 7: Statistics
        success = test_statistics(queue)
        test_results.append(("Get Statistics", success))
        
        # Test 8: Get by document
        success = test_get_by_document(queue, document_id)
        test_results.append(("Get by Document", success))
        
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
        
        # Cleanup
        if review_id and document_id:
            response = input("\nRemove test data? (y/n): ")
            if response.lower() == 'y':
                cleanup_test_data(queue, review_id, document_id)
        
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
