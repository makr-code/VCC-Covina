"""
Phase 1 Test - EventBus Architecture
=====================================

Test script für die neuen Core-Module:
- EventBus
- TaskExecutor
- BackendService
- BaseView

Version: 4.0.0 (Frontend Modernization)
Date: 14. Oktober 2025
"""

import logging
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.core import EventBus, EventType, TaskExecutor, Task, CovinaBackendService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_event_bus():
    """Test EventBus basic functionality"""
    print("\n" + "="*70)
    print("TEST 1: EventBus Basic Functionality")
    print("="*70)
    
    bus = EventBus()
    bus.start()
    
    # Test event
    events_received = []
    
    def on_test_event(event):
        events_received.append(event)
        print(f"✅ Event received: {event.event_type.value}")
        print(f"   Data: {event.data}")
    
    # Subscribe
    bus.subscribe(EventType.BACKEND_CONNECTED, on_test_event)
    
    # Emit
    bus.emit(EventType.BACKEND_CONNECTED, {"url": "http://test", "type": "main"})
    
    # Wait for dispatch
    time.sleep(0.5)
    
    # Verify
    assert len(events_received) == 1, "Event not received!"
    assert events_received[0].data["url"] == "http://test"
    
    bus.stop()
    
    print("✅ EventBus test PASSED")
    return True


def test_task_executor():
    """Test TaskExecutor with priority queue"""
    print("\n" + "="*70)
    print("TEST 2: TaskExecutor Priority Queue")
    print("="*70)
    
    executor = TaskExecutor(max_workers=2)
    executor.start()
    
    results = []
    
    def worker_task(task_name, duration):
        print(f"   🔧 Task '{task_name}' started (duration: {duration}s)")
        time.sleep(duration)
        print(f"   ✅ Task '{task_name}' completed")
        return task_name
    
    def on_success(result):
        results.append(result)
    
    # Submit tasks with different priorities
    task1 = Task(
        task_id="low_priority",
        func=worker_task,
        args=("Low Priority", 0.2),
        priority=3,
        callback=on_success
    )
    
    task2 = Task(
        task_id="high_priority",
        func=worker_task,
        args=("High Priority", 0.2),
        priority=9,
        callback=on_success
    )
    
    task3 = Task(
        task_id="medium_priority",
        func=worker_task,
        args=("Medium Priority", 0.2),
        priority=5,
        callback=on_success
    )
    
    # Submit in order: low, high, medium
    executor.submit(task1)
    executor.submit(task2)
    executor.submit(task3)
    
    # Wait for completion
    time.sleep(1.5)
    
    # Verify
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    
    executor.stop()
    
    print(f"✅ TaskExecutor test PASSED")
    print(f"   Results order: {results}")
    return True


def test_backend_service():
    """Test BackendService with EventBus integration"""
    print("\n" + "="*70)
    print("TEST 3: BackendService Integration")
    print("="*70)
    
    event_bus = EventBus()
    event_bus.start()
    
    task_executor = TaskExecutor(max_workers=3)
    task_executor.start()
    
    service = CovinaBackendService(
        base_url="http://127.0.0.1:45678",
        ingestion_base_url="http://127.0.0.1:45679",
        event_bus=event_bus,
        task_executor=task_executor
    )
    
    # Track events
    events_received = []
    
    def on_backend_event(event):
        events_received.append(event.event_type.value)
        print(f"   📡 Event: {event.event_type.value}")
        if event.data:
            for key, value in list(event.data.items())[:3]:  # First 3 items
                print(f"      {key}: {value}")
    
    # Subscribe to all backend events
    event_bus.subscribe(EventType.BACKEND_CONNECTED, on_backend_event)
    event_bus.subscribe(EventType.BACKEND_DISCONNECTED, on_backend_event)
    event_bus.subscribe(EventType.BACKEND_ERROR, on_backend_event)
    event_bus.subscribe(EventType.JOB_STATUS_CHANGED, on_backend_event)
    
    # Start service (triggers health check)
    service.start()
    
    print("\n   Waiting for health check... (10s)")
    time.sleep(12)
    
    # Stop service
    service.stop()
    event_bus.stop()
    task_executor.stop()
    
    print(f"\n✅ BackendService test COMPLETED")
    print(f"   Events received: {len(events_received)}")
    print(f"   Event types: {set(events_received)}")
    return True


def test_all():
    """Run all tests"""
    print("\n" + "="*70)
    print("COVINA FRONTEND v4.0.0 - PHASE 1 TESTS")
    print("EventBus Architecture Validation")
    print("="*70)
    
    tests = [
        ("EventBus", test_event_bus),
        ("TaskExecutor", test_task_executor),
        ("BackendService", test_backend_service),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "✅ PASSED" if result else "❌ FAILED"))
        except Exception as e:
            results.append((test_name, f"❌ ERROR: {e}"))
            logger.error(f"Test '{test_name}' failed with error: {e}", exc_info=True)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, result in results:
        print(f"{test_name:20s} {result}")
    
    passed = sum(1 for _, r in results if "PASSED" in r)
    total = len(results)
    
    print("\n" + "="*70)
    print(f"RESULT: {passed}/{total} tests passed")
    print("="*70)
    
    return passed == total


if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
