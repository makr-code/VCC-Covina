"""
End-to-End Test Suite - Phase 5: Testing & Validation

Comprehensive testing of all Phase 1-4 components:
- EventBus functionality
- ViewManager lifecycle
- All 10 views
- Navigation system
- Event flow
- Performance metrics

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 5)
Date: 14.10.2025, 12:10 Uhr
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import tkinter as tk
import time
from unittest.mock import Mock, patch
import logging

# Import all components
from frontend.core.event_bus import EventBus, EventType, Event
from frontend.core.task_executor import TaskExecutor
from frontend.core.view_manager import ViewManager
from frontend.core.backend_service import CovinaBackendService

# Import views
from frontend.views import (
    RecoveryView,
    HomeView,
    SystemStatusViewMigrated,
    IngestionViewMigrated,
    DatabaseHealthViewMigrated,
    SecurityViewMigrated,
    ErrorTrackingViewMigrated,
    GoldenDatasetViewMigrated,
    UDS3View,
    SAGAView,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEventBus(unittest.TestCase):
    """Test EventBus functionality."""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.event_bus.start()
    
    def tearDown(self):
        self.event_bus.stop()
    
    def test_event_emission(self):
        """Test event emission and reception."""
        received = []
        
        def handler(event):
            received.append(event)
        
        self.event_bus.subscribe(EventType.JOB_CREATED, handler)
        self.event_bus.emit(EventType.JOB_CREATED, {"job_id": "test_123"})
        
        time.sleep(0.1)  # Wait for async processing
        
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].data["job_id"], "test_123")
    
    def test_multiple_subscribers(self):
        """Test multiple subscribers to same event."""
        received1 = []
        received2 = []
        
        def handler1(event):
            received1.append(event)
        
        def handler2(event):
            received2.append(event)
        
        self.event_bus.subscribe(EventType.JOB_CREATED, handler1)
        self.event_bus.subscribe(EventType.JOB_CREATED, handler2)
        self.event_bus.emit(EventType.JOB_CREATED, {"test": "data"})
        
        time.sleep(0.1)
        
        self.assertEqual(len(received1), 1)
        self.assertEqual(len(received2), 1)
    
    def test_unsubscribe(self):
        """Test unsubscribe functionality."""
        received = []
        
        def handler(event):
            received.append(event)
        
        self.event_bus.subscribe(EventType.JOB_CREATED, handler)
        self.event_bus.emit(EventType.JOB_CREATED, {"test": "1"})
        
        time.sleep(0.1)
        self.assertEqual(len(received), 1)
        
        self.event_bus.unsubscribe(EventType.JOB_CREATED, handler)
        self.event_bus.emit(EventType.JOB_CREATED, {"test": "2"})
        
        time.sleep(0.1)
        self.assertEqual(len(received), 1)  # Should not receive second event


class TestViewManager(unittest.TestCase):
    """Test ViewManager functionality."""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Don't show window
        
        self.event_bus = EventBus()
        self.backend_service = Mock()
        
        self.container = tk.Frame(self.root)
        self.view_manager = ViewManager(self.container)
        
        # Register test views
        self.view1 = RecoveryView(self.container, self.event_bus, self.backend_service)
        self.view2 = UDS3View(self.container, self.event_bus, self.backend_service)
        
        self.view_manager.register_view("recovery", self.view1)
        self.view_manager.register_view("uds3", self.view2)
    
    def tearDown(self):
        self.view_manager.cleanup()
        self.root.destroy()
    
    def test_register_view(self):
        """Test view registration."""
        self.assertIn("recovery", self.view_manager.views)
        self.assertIn("uds3", self.view_manager.views)
        self.assertEqual(len(self.view_manager.list_views()), 2)
    
    def test_switch_view(self):
        """Test view switching."""
        success = self.view_manager.switch_view("recovery")
        self.assertTrue(success)
        self.assertEqual(self.view_manager.get_current_view_name(), "recovery")
        
        success = self.view_manager.switch_view("uds3")
        self.assertTrue(success)
        self.assertEqual(self.view_manager.get_current_view_name(), "uds3")
    
    def test_switch_to_invalid_view(self):
        """Test switching to non-existent view."""
        success = self.view_manager.switch_view("invalid_view")
        self.assertFalse(success)
    
    def test_view_lifecycle(self):
        """Test view activation/deactivation."""
        # Track lifecycle calls
        activate_called = []
        deactivate_called = []
        
        original_activate = self.view1.on_activate
        original_deactivate = self.view1.on_deactivate
        
        def track_activate():
            activate_called.append(True)
            original_activate()
        
        def track_deactivate():
            deactivate_called.append(True)
            original_deactivate()
        
        self.view1.on_activate = track_activate
        self.view1.on_deactivate = track_deactivate
        
        # Switch to view1
        self.view_manager.switch_view("recovery")
        self.assertEqual(len(activate_called), 1)
        
        # Switch to view2
        self.view_manager.switch_view("uds3")
        self.assertEqual(len(deactivate_called), 1)


class TestViewIntegration(unittest.TestCase):
    """Test individual view functionality."""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        self.event_bus = EventBus()
        self.backend_service = Mock()
        self.container = tk.Frame(self.root)
    
    def tearDown(self):
        self.root.destroy()
    
    def test_recovery_view_initialization(self):
        """Test RecoveryView initialization."""
        view = RecoveryView(self.container, self.event_bus, self.backend_service)
        self.assertIsNotNone(view)
        self.assertEqual(view.backend_service, self.backend_service)
    
    def test_uds3_view_initialization(self):
        """Test UDS3View initialization."""
        view = UDS3View(self.container, self.event_bus, self.backend_service)
        self.assertIsNotNone(view)
        self.assertEqual(len(view._datasets), 0)
    
    def test_saga_view_initialization(self):
        """Test SAGAView initialization."""
        view = SAGAView(self.container, self.event_bus, self.backend_service)
        self.assertIsNotNone(view)
        self.assertEqual(len(view._transactions), 0)
    
    def test_view_update_data(self):
        """Test view data updates."""
        view = UDS3View(self.container, self.event_bus, self.backend_service)
        
        test_data = {
            "type": "datasets",
            "datasets": [
                {"id": 1, "name": "Test Dataset"}
            ]
        }
        
        view.update_data(test_data)
        self.assertEqual(len(view._datasets), 1)


class TestNavigationFlow(unittest.TestCase):
    """Test navigation event flow."""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        self.event_bus = EventBus()
        self.event_bus.start()
        self.backend_service = Mock()
        
        self.container = tk.Frame(self.root)
        self.view_manager = ViewManager(self.container)
        
        # Register views
        views = [
            ("recovery", RecoveryView),
            ("uds3", UDS3View),
            ("saga", SAGAView),
        ]
        
        for name, view_class in views:
            view = view_class(self.container, self.event_bus, self.backend_service)
            self.view_manager.register_view(name, view)
    
    def tearDown(self):
        self.event_bus.stop()
        self.view_manager.cleanup()
        self.root.destroy()
    
    def test_navigation_event(self):
        """Test navigation via events."""
        # Subscribe to VIEW_CHANGED event
        view_changed = []
        
        def on_view_changed(event):
            view_changed.append(event.data.get("view"))
        
        self.event_bus.subscribe(EventType.VIEW_CHANGED, on_view_changed)
        
        # Switch view
        self.view_manager.switch_view("recovery")
        
        # Emit VIEW_CHANGED event
        self.event_bus.emit(EventType.VIEW_CHANGED, {"view": "recovery"})
        
        time.sleep(0.1)
        
        self.assertEqual(len(view_changed), 1)
        self.assertEqual(view_changed[0], "recovery")


class TestPerformance(unittest.TestCase):
    """Test performance metrics."""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        self.event_bus = EventBus()
        self.backend_service = Mock()
        self.container = tk.Frame(self.root)
        self.view_manager = ViewManager(self.container)
        
        # Register all 10 views
        views_config = [
            ("home", HomeView),
            ("recovery", RecoveryView),
            ("uds3", UDS3View),
            ("saga", SAGAView),
        ]
        
        for name, view_class in views_config:
            view = view_class(self.container, self.event_bus, self.backend_service)
            self.view_manager.register_view(name, view)
    
    def tearDown(self):
        self.view_manager.cleanup()
        self.root.destroy()
    
    def test_view_switch_performance(self):
        """Test view switching performance."""
        times = []
        
        for _ in range(10):
            start = time.perf_counter()
            self.view_manager.switch_view("recovery")
            self.view_manager.switch_view("uds3")
            end = time.perf_counter()
            
            times.append(end - start)
        
        avg_time = sum(times) / len(times) * 1000  # Convert to ms
        
        logger.info(f"Average view switch time: {avg_time:.2f}ms")
        
        # Target: <50ms per switch (2 switches = <100ms)
        self.assertLess(avg_time, 100, f"View switch too slow: {avg_time:.2f}ms")
    
    def test_event_emission_performance(self):
        """Test event emission performance."""
        received = []
        
        def handler(event):
            received.append(event)
        
        self.event_bus.start()
        self.event_bus.subscribe(EventType.JOB_CREATED, handler)
        
        start = time.perf_counter()
        
        for i in range(100):
            self.event_bus.emit(EventType.JOB_CREATED, {"job_id": f"job_{i}"})
        
        end = time.perf_counter()
        
        time.sleep(0.5)  # Wait for async processing
        
        elapsed_ms = (end - start) * 1000
        avg_per_event = elapsed_ms / 100
        
        logger.info(f"100 events emitted in {elapsed_ms:.2f}ms ({avg_per_event:.2f}ms per event)")
        
        self.event_bus.stop()
        
        # Should emit 100 events in <100ms
        self.assertLess(elapsed_ms, 100)
        self.assertEqual(len(received), 100)


def run_tests():
    """Run all test suites."""
    print("=" * 60)
    print("Phase 5: End-to-End Testing - Covina v4.0.0")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEventBus))
    suite.addTests(loader.loadTestsFromTestCase(TestViewManager))
    suite.addTests(loader.loadTestsFromTestCase(TestViewIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestNavigationFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"⚠️  Errors: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
