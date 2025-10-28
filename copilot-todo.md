# Covina Project - Copilot Todo List

**Letzte Aktualisierung:** 28. Oktober 2025  
**Projekt:** Covina Document Management System  
**Status:** Production Hardening Implementation

---

## 🎯 Aktuelle Priorität: Production Hardening (24/7-Fähigkeit)

### Ziel
Transformation des Ingestion Backends von Development zu Production-Grade System mit strukturierter Fehlerbehandlung, Worker Monitoring, Memory Management und Fault Tolerance.

**Rating:** Aktuell 2.5/5 → Ziel 5.0/5 ⭐⭐⭐⭐⭐

---

## ✅ ABGESCHLOSSEN

### Phase 0: Problem-Analyse & Architektur (28.10.2025)
- [x] **Streaming Upload für große Dateien (2 GB+)**
  - Status: ✅ Complete (v2.0.0)
  - File: `tools/ingestion_gui.py`
  - Features: 64KB chunks, dynamic timeouts, 32,768x memory savings
  - Tests: 4 scenarios (10MB → 2GB) passed

- [x] **Backend Stability Fixes**
  - Status: ✅ Fixed
  - Problem: Backends beendeten sich unerwartet
  - Solution: sitecustomize import path korrigiert
  - Debug Tools: 4 PowerShell scripts erstellt

- [x] **Architecture Analysis**
  - Status: ✅ Complete
  - Found: 30+ generic `except Exception` blocks
  - Found: Worker crashes undetected (8→7 processes)
  - Found: No memory limits (OOM risk)
  - Found: No circuit breakers (cascading failure risk)

- [x] **Production Hardening System Design**
  - Status: ✅ Complete (2,500+ lines)
  - Files Created:
    - `ingestion/exceptions.py` (700 lines)
    - `ingestion/worker_pool.py` (500 lines)
    - `ingestion/memory_manager.py` (400 lines)
    - `ingestion/circuit_breaker.py` (400 lines)
    - `docs/PRODUCTION_HARDENING_GUIDE.py` (500 lines)
    - `docs/PRODUCTION_HARDENING_SUMMARY.md` (400 lines)

---

## 🔄 IN PROGRESS

### Phase 1: Core Systems Integration (Stunden 1-2)

- [ ] **1.1 Install Dependencies**
  - Task: `pip install psutil`
  - Purpose: Memory monitoring system requirements
  - File: `requirements.txt`
  - Priority: HIGH

- [ ] **1.2 Import Hardening Modules**
  - File: `backend/ingestion.py` (Lines 40-50)
  - Add imports:
    ```python
    from ingestion.exceptions import *
    from ingestion.worker_pool import initialize_pool_manager, get_pool_manager
    from ingestion.memory_manager import initialize_memory_manager, get_memory_manager
    from ingestion.circuit_breaker import get_breaker_manager
    ```
  - Priority: HIGH

- [ ] **1.3 Initialize Systems in Lifespan**
  - File: `backend/ingestion.py` (@asynccontextmanager lifespan)
  - Tasks:
    - Initialize WorkerPoolManager (36 I/O + 8 CPU workers)
    - Initialize MemoryManager (4GB soft, 6GB hard limits)
    - Create Circuit Breakers (PostgreSQL, ChromaDB, Neo4j)
    - Setup graceful shutdown handlers
  - Reference: `docs/PRODUCTION_HARDENING_GUIDE.py` (Lines 50-150)
  - Priority: HIGH

---

## ⏳ PENDING

### Phase 2: Exception Handling Refactor (Stunden 3-4)

- [ ] **2.1 Replace Generic Exception Handlers**
  - File: `backend/ingestion.py`
  - Locations: 30+ `except Exception` blocks
  - Search Pattern: `except Exception as e:`
  - Replace with:
    - `FileNotFoundException` (file operations)
    - `DatabaseConnectionException` (DB operations)
    - `WorkerCrashException` (worker failures)
    - `MemoryLimitExceededException` (memory issues)
    - etc.
  - Priority: HIGH
  - Effort: 2-3 hours

- [ ] **2.2 Add Exception Context**
  - Add `context={}` dict to all exceptions
  - Include: file_path, file_size_mb, operation, user_id (if available)
  - Ensure DSGVO compliance (no PII in logs)
  - Priority: MEDIUM
  - Effort: 1 hour

- [ ] **2.3 Add Recovery Hints**
  - Add actionable `recovery_hint` to exceptions
  - Examples:
    - "Check file permissions"
    - "Verify database connection"
    - "Restart worker pool"
  - Priority: LOW
  - Effort: 30 minutes

### Phase 3: Worker Pool Integration (Stunden 5-6)

- [ ] **3.1 Replace Direct Executor Calls**
  - File: `backend/ingestion.py`
  - Search: `io_executor.submit(`
  - Replace: `pool_manager.submit_io_task(`
  - Add `task_id` parameter for tracking
  - Locations: ~15-20 calls
  - Priority: HIGH
  - Effort: 1.5 hours

- [ ] **3.2 Replace CPU Executor Calls**
  - File: `backend/ingestion.py`
  - Search: `cpu_executor.submit(`
  - Replace: `pool_manager.submit_cpu_task(`
  - Add `task_id` parameter for tracking
  - Locations: ~5-10 calls
  - Priority: HIGH
  - Effort: 1 hour

- [ ] **3.3 Add Task ID Generation**
  - Create `_generate_task_id()` helper
  - Format: `{operation}_{timestamp}_{uuid4()}`
  - Use in all task submissions
  - Priority: MEDIUM
  - Effort: 30 minutes

- [ ] **3.4 Test Worker Health Monitoring**
  - Verify heartbeat tracking (30s intervals)
  - Verify crash detection (5min timeout)
  - Verify task timeout detection (10min)
  - Test graceful shutdown (30s wait)
  - Priority: HIGH
  - Effort: 1 hour

### Phase 4: Database Protection (Stunden 7-8)

- [ ] **4.1 Wrap PostgreSQL Operations**
  - File: `backend/ingestion.py`
  - Create: `_insert_postgresql_with_breaker()` wrapper
  - Breaker config: failure_threshold=5, recovery_timeout=60s
  - Wrap all `uds3_relational.insert()` calls
  - Priority: HIGH
  - Effort: 1 hour

- [ ] **4.2 Wrap ChromaDB Operations**
  - File: `backend/ingestion.py`
  - Create: `_insert_chromadb_with_breaker()` wrapper
  - Breaker config: failure_threshold=3, recovery_timeout=30s
  - Wrap all `chromadb_client.add_vector()` calls
  - Priority: HIGH
  - Effort: 1 hour

- [ ] **4.3 Wrap Neo4j Operations**
  - File: `backend/ingestion.py`
  - Create: `_insert_neo4j_with_breaker()` wrapper
  - Breaker config: failure_threshold=5, recovery_timeout=60s
  - Wrap all Neo4j graph operations
  - Priority: MEDIUM
  - Effort: 1 hour

- [ ] **4.4 Add Memory Checks Before Large Operations**
  - Add `memory_manager.check_can_allocate(size_mb)` before:
    - File upload processing
    - Large embeddings generation
    - Batch operations
  - Reject if insufficient memory
  - Priority: MEDIUM
  - Effort: 30 minutes

### Phase 5: Monitoring & Observability (Stunde 9)

- [ ] **5.1 Update /health Endpoint**
  - File: `backend/ingestion.py`
  - Add metrics:
    - Worker pool stats (idle/busy/crashed)
    - Memory stats (current/peak/limits)
    - Circuit breaker stats (states/failures)
    - Task stats (submitted/completed/failed)
  - Reference: `docs/PRODUCTION_HARDENING_GUIDE.py` (Lines 400-450)
  - Priority: MEDIUM
  - Effort: 1 hour

- [ ] **5.2 Create /metrics Endpoint**
  - File: `backend/ingestion.py`
  - Format: Prometheus-compatible
  - Expose:
    - worker_pool_* metrics
    - memory_* metrics
    - circuit_breaker_* metrics
    - task_* metrics
  - Reference: `docs/PRODUCTION_HARDENING_GUIDE.py` (Lines 450-500)
  - Priority: LOW
  - Effort: 1 hour

- [ ] **5.3 Add Structured Logging**
  - Ensure all exceptions use `.to_dict()` for JSON logging
  - Add correlation IDs to all log entries
  - Test log aggregation (ELK/Splunk compatible)
  - Priority: LOW
  - Effort: 30 minutes

### Phase 6: Testing & Validation (Stunden 10-12)

- [ ] **6.1 Load Testing**
  - Test: 1000+ concurrent requests
  - Verify: Worker pool handles load
  - Verify: Memory stays within limits
  - Verify: No worker crashes
  - Tool: `tests/load_test_upload_simple.py` (modify)
  - Priority: HIGH
  - Effort: 1 hour

- [ ] **6.2 Chaos Testing**
  - Test: Inject database failures
  - Verify: Circuit breakers open
  - Verify: Graceful degradation
  - Verify: Auto-recovery works
  - Tool: Create `tests/test_chaos.py`
  - Priority: HIGH
  - Effort: 1.5 hours

- [ ] **6.3 Memory Leak Testing**
  - Test: 24-hour continuous run
  - Verify: Memory stays stable
  - Verify: No gradual growth
  - Verify: Leak detection triggers if needed
  - Tool: Create `tests/test_memory_leak.py`
  - Priority: MEDIUM
  - Effort: 1 hour (+ 24h runtime)

- [ ] **6.4 Recovery Testing**
  - Test: Backend restart scenarios
  - Verify: Graceful shutdown waits for tasks
  - Verify: No data loss
  - Verify: Clean recovery on startup
  - Tool: PowerShell scripts
  - Priority: MEDIUM
  - Effort: 1 hour

---

## 🚀 FUTURE ENHANCEMENTS

### Performance Optimizations

- [ ] **GPU-Accelerated Embeddings**
  - Library: sentence-transformers with CUDA
  - Expected: +300-500% embedding speed
  - Priority: LOW
  - Effort: 4 hours

- [ ] **Redis Caching Layer**
  - Cache: Frequently accessed queries
  - Expected: +50-100% query speed
  - Priority: LOW
  - Effort: 8 hours

- [ ] **Horizontal Scaling**
  - Multiple backend instances
  - Load balancer (NGINX)
  - Expected: Linear scaling
  - Priority: LOW
  - Effort: 2-3 days

### Monitoring & Alerting

- [ ] **Prometheus Integration**
  - Scrape /metrics endpoint
  - Create dashboards
  - Priority: LOW
  - Effort: 4 hours

- [ ] **Grafana Dashboards**
  - Worker pool dashboard
  - Memory dashboard
  - Circuit breaker dashboard
  - Priority: LOW
  - Effort: 4 hours

- [ ] **Alerting Rules**
  - Worker crash alerts
  - Memory limit alerts
  - Circuit breaker open alerts
  - Priority: LOW
  - Effort: 2 hours

### Documentation

- [ ] **API Documentation Update**
  - Document new error codes
  - Document new endpoints (/metrics)
  - Document recovery procedures
  - Priority: MEDIUM
  - Effort: 2 hours

- [ ] **Runbook Creation**
  - Worker crash recovery
  - Memory leak investigation
  - Circuit breaker manual reset
  - Priority: MEDIUM
  - Effort: 3 hours

- [ ] **Architecture Diagram Update**
  - Add worker pool manager
  - Add circuit breakers
  - Add memory manager
  - Priority: LOW
  - Effort: 1 hour

---

## 📊 Progress Tracking

### Overall Status

| Phase | Tasks | Completed | In Progress | Pending | Progress |
|-------|-------|-----------|-------------|---------|----------|
| **Phase 0: Analysis** | 4 | 4 | 0 | 0 | ✅ 100% |
| **Phase 1: Core** | 3 | 0 | 3 | 0 | 🔄 0% |
| **Phase 2: Exceptions** | 3 | 0 | 0 | 3 | ⏳ 0% |
| **Phase 3: Workers** | 4 | 0 | 0 | 4 | ⏳ 0% |
| **Phase 4: Database** | 4 | 0 | 0 | 4 | ⏳ 0% |
| **Phase 5: Monitoring** | 3 | 0 | 0 | 3 | ⏳ 0% |
| **Phase 6: Testing** | 4 | 0 | 0 | 4 | ⏳ 0% |
| **TOTAL** | **25** | **4** | **3** | **18** | **16%** |

### Time Estimate

- **Completed:** 8 hours (Analysis + Design)
- **Remaining:** 12 hours (Implementation + Testing)
- **Total Project:** 20 hours

### Success Criteria

- [ ] All 30+ generic exceptions replaced with typed exceptions
- [ ] Worker crashes detected within 30 seconds
- [ ] Memory usage stays below 6 GB hard limit
- [ ] Circuit breakers prevent cascading failures
- [ ] Graceful shutdown waits for tasks (30s timeout)
- [ ] /health endpoint returns comprehensive metrics
- [ ] Load test: 1000+ concurrent requests handled
- [ ] Chaos test: Database failures don't crash backend
- [ ] 24-hour stability test: No memory leaks detected
- [ ] **System Rating:** 5.0/5 ⭐⭐⭐⭐⭐

---

## 🔍 Known Issues

### Critical (Blocker)

1. **Worker Crashes Undetected**
   - Impact: 8→7 processes, silent failures
   - Solution: WorkerPoolManager (Phase 3)
   - ETA: 2 hours

2. **No Memory Limits**
   - Impact: OOM crashes (12.9 GB observed)
   - Solution: MemoryManager (Phase 4)
   - ETA: 1 hour

3. **Generic Exception Handling**
   - Impact: Difficult debugging, unclear errors
   - Solution: Exception hierarchy (Phase 2)
   - ETA: 3 hours

### High (Important)

4. **No Circuit Breakers**
   - Impact: Cascading failures possible
   - Solution: Circuit breaker pattern (Phase 4)
   - ETA: 2 hours

5. **No Graceful Shutdown**
   - Impact: Data loss on restart
   - Solution: Graceful shutdown (Phase 3)
   - ETA: 30 minutes

### Medium (Should Fix)

6. **Limited Monitoring**
   - Impact: Reduced visibility
   - Solution: Enhanced /health + /metrics (Phase 5)
   - ETA: 2 hours

---

## 📚 Reference Documentation

### Production Hardening Docs

1. **`docs/PRODUCTION_HARDENING_SUMMARY.md`**
   - Executive summary
   - Problem analysis
   - Expected improvements
   - Production checklist

2. **`docs/PRODUCTION_HARDENING_GUIDE.py`**
   - Complete integration guide
   - 8-step implementation plan
   - Code examples
   - Best practices

### Module Documentation

3. **`ingestion/exceptions.py`**
   - 16 exception classes
   - Error codes (1000-1699 + 9999)
   - Severity levels
   - Context & recovery hints

4. **`ingestion/worker_pool.py`**
   - WorkerPoolManager class
   - Health monitoring
   - Heartbeat tracking
   - Graceful shutdown

5. **`ingestion/memory_manager.py`**
   - MemoryManager class
   - Soft/hard limits
   - GC tuning
   - Leak detection

6. **`ingestion/circuit_breaker.py`**
   - CircuitBreaker class
   - State machine (CLOSED/OPEN/HALF_OPEN)
   - Auto-recovery
   - Metrics collection

---

## 🎯 Next Steps

### Immediate (Today)

1. **Start Phase 1** (Core Systems Integration)
   - Install psutil
   - Add imports to backend/ingestion.py
   - Initialize systems in lifespan
   - Test basic functionality

2. **Create Integration Branch**
   ```bash
   git checkout -b feature/production-hardening
   ```

3. **Run Initial Tests**
   ```bash
   python -m pytest tests/ -v
   ```

### This Week

4. **Complete Phase 2-3** (Exception Handling + Worker Pool)
   - Replace all generic exceptions
   - Integrate WorkerPoolManager
   - Test worker health monitoring

5. **Complete Phase 4** (Database Protection)
   - Add circuit breakers
   - Add memory checks
   - Test fault tolerance

### Next Week

6. **Complete Phase 5-6** (Monitoring + Testing)
   - Update endpoints
   - Run load tests
   - Run chaos tests
   - 24-hour stability test

7. **Production Deployment**
   - Merge feature branch
   - Deploy to production
   - Monitor metrics

---

## 📞 Questions & Decisions Needed

### Technical Decisions

- [ ] **Memory Limits:** Confirm 4 GB soft / 6 GB hard limits appropriate?
- [ ] **Circuit Breaker Thresholds:** Adjust per service? (currently: 5 failures)
- [ ] **Worker Pool Size:** Keep 36 I/O + 8 CPU workers?
- [ ] **Auto-Recovery:** Enable automatic worker restart? (currently: disabled)

### Operational Decisions

- [ ] **Monitoring Stack:** Prometheus + Grafana? Alternative?
- [ ] **Alerting:** PagerDuty? Slack? Email?
- [ ] **Logging:** ELK Stack? Splunk? CloudWatch?
- [ ] **Deployment Strategy:** Blue-Green? Rolling? Canary?

### Testing Decisions

- [ ] **Load Test Target:** 1000 concurrent? Higher?
- [ ] **Chaos Test Scenarios:** Which failures to inject?
- [ ] **Stability Test Duration:** 24h? 48h? 1 week?

---

**Last Updated:** 28. Oktober 2025, 11:30 Uhr  
**Maintained By:** Covina Development Team  
**Review Frequency:** Daily during implementation, weekly after production
