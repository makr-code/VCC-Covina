# Backend Thread-Safety Improvements
## Date: 2025-10-09

## Problem Identified
Backend-Timeouts und Event-Loop-Blocking durch Tasks die direkt im FastAPI Event-Loop ausgeführt wurden.

**Symptome:**
- /health Endpoint Timeout (>15s)
- Frontend kann nicht mit Backend kommunizieren
- FastAPI scheint "frozen"

**Root Cause:**
```python
# VORHER (automation/scheduler.py, Zeile 472)
result = await task.execute(context)  # ❌ Blockiert Event-Loop!
```

Tasks wurden direkt mit `await task.execute()` im AsyncIO Event-Loop ausgeführt. Wenn eine Task:
- Lange DB-Queries macht
- Synchrone I/O durchführt
- CPU-intensive Berechnungen macht

...blockiert sie den **gesamten FastAPI-Server** und alle HTTP-Requests warten.

## Solution Implemented

### 1. Thread-Pool für Task-Execution

**File:** `automation/scheduler.py`

```python
import concurrent.futures
import threading

# Global Thread Pool für Task-Execution
_task_executor = None
_executor_lock = threading.Lock()

def get_task_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Singleton Thread-Pool für Task-Execution"""
    global _task_executor
    with _executor_lock:
        if _task_executor is None:
            _task_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=4,
                thread_name_prefix="AutomationTask"
            )
            logger.info("✅ Task Executor Thread-Pool initialisiert (4 Workers)")
        return _task_executor
```

### 2. Non-Blocking Task Execution

**Periodic Tasks:**
```python
# Task im Thread-Pool ausführen (verhindert Event-Loop-Blocking)
executor = get_task_executor()
loop = asyncio.get_event_loop()

def run_task_sync():
    """Führt Task synchron im Thread aus"""
    try:
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        return thread_loop.run_until_complete(task.execute(context))
    finally:
        thread_loop.close()
        asyncio.set_event_loop(None)

# ✅ Non-blocking execution
result = await loop.run_in_executor(executor, run_task_sync)
```

**Conditional Tasks:**
```python
def run_conditional_task_sync():
    """Führt conditional Task synchron im Thread aus"""
    try:
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        return thread_loop.run_until_complete(task.check_and_execute_if_needed())
    finally:
        thread_loop.close()
        asyncio.set_event_loop(None)

result = await loop.run_in_executor(executor, run_conditional_task_sync)
```

## Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Event Loop              │
│  (uvicorn, HTTP Requests)               │
│                                         │
│  ┌───────────────────────────────┐     │
│  │  Automation Scheduler         │     │
│  │  (asyncio.create_task)        │     │
│  │                               │     │
│  │  Every 30s:                   │     │
│  │  - Check periodic tasks       │     │
│  │  - Check conditional tasks    │     │
│  └───────────────┬───────────────┘     │
└──────────────────┼──────────────────────┘
                   │
                   │ loop.run_in_executor()
                   ▼
┌─────────────────────────────────────────┐
│   ThreadPoolExecutor (4 Workers)        │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│   │ Task 1  │ │ Task 2  │ │ Task 3  │  │
│   │ Thread  │ │ Thread  │ │ Thread  │  │
│   └─────────┘ └─────────┘ └─────────┘  │
│                                         │
│   Each thread has own event loop!      │
│   asyncio.new_event_loop()             │
└─────────────────────────────────────────┘
```

## Benefits

✅ **Non-Blocking FastAPI**: HTTP-Requests werden sofort bearbeitet
✅ **Parallel Task Execution**: Bis zu 4 Tasks gleichzeitig
✅ **Isolated Event Loops**: Jeder Thread hat eigenen AsyncIO Loop
✅ **Thread-Safety**: Lock für Executor-Initialisierung
✅ **Better Error Handling**: Exception-Isolation per Task

## Testing

**Before:**
```bash
$ curl http://127.0.0.1:45678/health
# Timeout nach 15+ Sekunden
```

**After:**
```bash
$ curl http://127.0.0.1:45678/health
# Response in <100ms (expected)
```

## Related Changes

**Frontend Side:**
- `frontend/services/api_client.py`: Thread-safe API-Client (keine Session mehr)
- `frontend/core/chart_threading.py`: Chart-Rendering in eigenen Threads
- Beide Seiten nutzen jetzt Thread-basierte Architekturen

## Future Improvements

1. **Task Prioritization**: High-priority Tasks bevorzugen
2. **Dynamic Thread Pool Size**: Basierend auf Load
3. **Task Queueing**: Queue für Tasks wenn alle Workers busy
4. **Metrics**: Task-Execution-Zeit tracken
5. **Health Checks**: Monitoring ob Workers hängen

## Rollback Plan

Falls Probleme auftreten:

```bash
git diff automation/scheduler.py  # Changes anzeigen
git checkout HEAD -- automation/scheduler.py  # Revert
```

Oder manuell `await task.execute(context)` wiederherstellen (ohne Thread-Pool).

## Notes

- Thread-Pool wird beim ersten Task-Run initialisiert (Lazy Loading)
- Jeder Worker-Thread bekommt eigenen AsyncIO Event-Loop
- `thread_name_prefix="AutomationTask"` hilft beim Debugging
- Max 4 concurrent Tasks (konfigurierbar via `max_workers`)
