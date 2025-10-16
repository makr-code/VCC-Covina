# Frontend Architecture Quick Reference

**Version:** 4.0.0 (Frontend Modernization)  
**Date:** 14. Oktober 2025  
**Status:** Phase 1 Complete ✅

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     CovinaApp                           │
│  ┌───────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ EventBus  │  │ TaskExecutor │  │ BackendService  │ │
│  └─────┬─────┘  └──────┬───────┘  └────────┬────────┘ │
│        │               │                    │          │
│        └───────────────┴────────────────────┘          │
│                        │                               │
│         ┌──────────────┴──────────────┐               │
│         │                               │               │
│    ┌────▼────┐                    ┌────▼────┐         │
│    │  View1  │ ... (9 Views) ...  │  View10 │         │
│    │(BaseView│                    │(BaseView│         │
│    └─────────┘                    └─────────┘         │
└─────────────────────────────────────────────────────────┘
```

**Event Flow:**
```
BackendService → EventBus → View.event_handler() → View.update_data()
```

---

## 📦 Core Modules

### EventBus

**Import:**
```python
from frontend.core import EventBus, EventType, Event
```

**Basic Usage:**
```python
# Create and start
bus = EventBus()
bus.start()

# Subscribe
def on_event(event: Event):
    print(f"Received: {event.event_type.value}")
    print(f"Data: {event.data}")

bus.subscribe(EventType.BACKEND_CONNECTED, on_event)

# Emit (async)
bus.emit(EventType.BACKEND_CONNECTED, {"url": "http://localhost"})

# Emit (sync - careful with blocking!)
bus.emit_sync(EventType.BACKEND_CONNECTED, {"url": "http://localhost"})

# Cleanup
bus.stop()
```

**Available Event Types:**
```python
# Backend Events
EventType.BACKEND_CONNECTED
EventType.BACKEND_DISCONNECTED
EventType.BACKEND_ERROR

# Job Events
EventType.JOB_CREATED
EventType.JOB_STATUS_CHANGED
EventType.JOB_PROGRESS_UPDATE
EventType.JOB_COMPLETED
EventType.JOB_FAILED

# Recovery Events (NEW v3.4.8)
EventType.RECOVERY_STARTED
EventType.RECOVERY_COMPLETE
EventType.RECOVERY_FAILED
EventType.RECOVERY_FILE_BLOCKED
EventType.RECOVERY_FILE_UNBLOCKED

# ... see event_bus.py for all 30+ types
```

---

### TaskExecutor

**Import:**
```python
from frontend.core import TaskExecutor, Task
```

**Basic Usage:**
```python
# Create and start
executor = TaskExecutor(max_workers=5)
executor.start()

# Define task
def my_task(x, y):
    return x + y

def on_success(result):
    print(f"Result: {result}")

def on_error(error):
    print(f"Error: {error}")

# Submit task
task = Task(
    task_id="unique_id",
    func=my_task,
    args=(5, 3),
    priority=8,  # 1-10, higher = more important
    callback=on_success,
    error_callback=on_error
)

task_id = executor.submit(task)

# Cancel task (if still pending)
executor.cancel(task_id)

# Cleanup
executor.stop()
```

**Priority Levels:**
- `1-3`: Low priority (background tasks)
- `4-6`: Normal priority (default)
- `7-9`: High priority (user-initiated)
- `10`: Critical (use sparingly)

---

### BackendService

**Import:**
```python
from frontend.core import CovinaBackendService
```

**Basic Setup:**
```python
# Dependencies
event_bus = EventBus()
task_executor = TaskExecutor(max_workers=3)

# Create service
service = CovinaBackendService(
    base_url="http://127.0.0.1:45678",
    ingestion_base_url="http://127.0.0.1:45679",
    event_bus=event_bus,
    task_executor=task_executor
)

# Start (triggers health check + job polling)
service.start()

# ... use service ...

# Stop
service.stop()
```

**API Methods:**

**Job Management:**
```python
# List jobs (emits JOB_STATUS_CHANGED)
service.list_jobs(limit=100)

# Get job details (emits JOB_PROGRESS_UPDATE)
service.get_job_details(job_id="abc123")
```

**Recovery API (v3.4.8):**
```python
# Get failed files (emits RECOVERY_STARTED)
service.get_failed_files(job_id="abc123", max_retries=3)

# Recover failed files (emits RECOVERY_COMPLETE/FAILED)
service.recover_failed_files(job_id="abc123")

# Unblock file (emits RECOVERY_FILE_UNBLOCKED)
service.unblock_file(job_id="abc123", file_path="path/to/file.txt", admin_override=True)

# Get all blocked files (emits RECOVERY_STARTED)
service.get_all_blocked_files()
```

**Event Subscription:**
```python
def on_backend_connected(event: Event):
    backend_type = event.data.get('type')  # 'main' or 'ingestion'
    url = event.data.get('url')
    print(f"{backend_type} backend connected: {url}")

event_bus.subscribe(EventType.BACKEND_CONNECTED, on_backend_connected)
```

---

### BaseView

**Import:**
```python
from frontend.views import BaseView
```

**View Template:**
```python
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from frontend.core import EventBus, EventType, Event
from frontend.views import BaseView

class MyView(BaseView):
    """
    Example view demonstrating BaseView usage
    """
    
    def build_ui(self):
        """Pure UI construction"""
        # Header
        self.title_label = ttk.Label(
            self, 
            text="My View", 
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(pady=10)
        
        # Content
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Status
        self.status_label = ttk.Label(self, text="Status: Waiting...")
        self.status_label.pack(pady=5)
        
        # Button
        self.refresh_button = ttk.Button(
            self, 
            text="Refresh", 
            command=self._fetch_data
        )
        self.refresh_button.pack(pady=10)
    
    def update_data(self, data: Dict[str, Any]):
        """Pure business logic"""
        # Store data
        self.data = data
        
        # Update status
        status = data.get('status', 'Unknown')
        self.status_label.config(text=f"Status: {status}")
        
        # Update content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        items = data.get('items', [])
        if items:
            for item in items:
                label = ttk.Label(
                    self.content_frame, 
                    text=f"• {item}"
                )
                label.pack(anchor=tk.W)
        else:
            no_data_label = ttk.Label(
                self.content_frame, 
                text="No data available"
            )
            no_data_label.pack()
    
    def on_activate(self):
        """Subscribe to events when view becomes visible"""
        self.event_bus.subscribe(
            EventType.BACKEND_CONNECTED, 
            self._on_backend_connected
        )
        self.event_bus.subscribe(
            EventType.JOB_STATUS_CHANGED, 
            self._on_job_status_changed
        )
        
        # Fetch initial data
        self._fetch_data()
    
    def on_deactivate(self):
        """Unsubscribe when view becomes hidden"""
        self.event_bus.unsubscribe(
            EventType.BACKEND_CONNECTED, 
            self._on_backend_connected
        )
        self.event_bus.unsubscribe(
            EventType.JOB_STATUS_CHANGED, 
            self._on_job_status_changed
        )
    
    # Event Handlers (private methods)
    
    def _on_backend_connected(self, event: Event):
        """Handle backend connected event"""
        self.safe_update_data({"status": "Connected"})
    
    def _on_job_status_changed(self, event: Event):
        """Handle job status changed event"""
        jobs = event.data.get('jobs', [])
        job_names = [j.get('job_id', 'Unknown') for j in jobs]
        self.safe_update_data({
            "status": f"{len(jobs)} jobs active",
            "items": job_names[:10]  # First 10
        })
    
    def _fetch_data(self):
        """Fetch data from backend"""
        # This would typically call backend_service methods
        # which emit events that trigger update_data()
        pass
```

**Usage in Main App:**
```python
# Create view
my_view = MyView(parent=notebook, event_bus=event_bus)

# Add to notebook
notebook.add(my_view, text="My View")

# Lifecycle management
notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

def _on_tab_changed(self, event):
    selected_tab = notebook.select()
    selected_view = notebook.nametowidget(selected_tab)
    
    # Deactivate all views
    for view in all_views:
        view.set_active(False)
    
    # Activate selected view
    if isinstance(selected_view, BaseView):
        selected_view.set_active(True)
```

---

## 🎨 Best Practices

### DO ✅

**Separation of Concerns:**
```python
# Good: Separate UI and logic
def build_ui(self):
    self.label = ttk.Label(self, text="")
    self.label.pack()

def update_data(self, data):
    self.label.config(text=data['message'])
```

**Thread-Safe Updates:**
```python
# Good: Use safe_update_data from background thread
def _on_event(self, event):
    self.safe_update_data(event.data)
```

**Event Subscription:**
```python
# Good: Subscribe in on_activate, unsubscribe in on_deactivate
def on_activate(self):
    self.event_bus.subscribe(EventType.JOB_CREATED, self._on_job_created)

def on_deactivate(self):
    self.event_bus.unsubscribe(EventType.JOB_CREATED, self._on_job_created)
```

### DON'T ❌

**Mixed Concerns:**
```python
# Bad: Mixed UI and logic
def build_ui(self):
    self.label = ttk.Label(self, text="Loading...")
    self.label.pack()
    
    # BAD: Fetching data in build_ui()
    response = requests.get("http://...")
    self.label.config(text=response.json()['data'])
```

**Direct Thread Updates:**
```python
# Bad: Direct update from background thread
def _on_event(self, event):
    self.label.config(text=event.data['message'])  # NOT THREAD-SAFE!
```

**Memory Leaks:**
```python
# Bad: Forgetting to unsubscribe
def on_activate(self):
    self.event_bus.subscribe(EventType.JOB_CREATED, self._on_job_created)

# Missing on_deactivate() → Memory leak!
```

---

## 🧪 Testing

**Test Template:**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.core import EventBus, EventType

def test_my_feature():
    # Setup
    bus = EventBus()
    bus.start()
    
    events_received = []
    
    def on_test_event(event):
        events_received.append(event)
    
    # Subscribe
    bus.subscribe(EventType.BACKEND_CONNECTED, on_test_event)
    
    # Act
    bus.emit(EventType.BACKEND_CONNECTED, {"url": "http://test"})
    
    # Wait for async dispatch
    import time
    time.sleep(0.5)
    
    # Assert
    assert len(events_received) == 1
    assert events_received[0].data["url"] == "http://test"
    
    # Cleanup
    bus.stop()
    
    print("✅ Test passed!")

if __name__ == "__main__":
    test_my_feature()
```

---

## 📚 Further Reading

**Documentation:**
- `docs/frontend/PHASE1_EVENTBUS_ARCHITECTURE_COMPLETE.md` - Complete Phase 1 documentation
- `frontend/views/base_view.py` - BaseView docstrings with examples
- `tests/test_phase1_eventbus_architecture.py` - Test examples

**Source Code:**
- `frontend/core/event_bus.py` - EventBus implementation
- `frontend/core/task_executor.py` - TaskExecutor implementation
- `frontend/core/backend_service.py` - BackendService implementation

---

**Last Updated:** 14. Oktober 2025, 09:15 Uhr  
**Version:** 4.0.0 (Frontend Modernization - Phase 1 Complete)
