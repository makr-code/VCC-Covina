# Implementation Roadmap - Priority Phases (L5, LR, Production Hardening)

**Erstellt:** 30. Oktober 2025  
**Status:** Ready for Implementation  
**Estimated Duration:** 3-4 Tage (24-32 Stunden)

---

## 📋 Executive Summary

**3 Prioritäre Phasen zur Umsetzung (inkl. Enterprise Features):**

1. **Phase L5: Migration & Backfill** (10-12 Std)
   - 161k Documents mit Legal Domain Nodes verlinken
   - Batch-Processing, Checkpointing, Recovery
   - **Enterprise:** Task Queue (RQ/Celery), Background Workers
   - **Impact:** Legal Knowledge Graph komplett + skalierbare Migration

2. **Phase LR: Reasoning & Config-Driven** (8-10 Std)
   - Multi-Hop Reasoner für komplexe Queries
   - Config-driven Extraction (YAML/JSON)
   - **Enterprise:** DI/Composition Root, pydantic-settings, Hot-Reload
   - **Impact:** Flexible, wartbare, typsichere NLP-Pipeline

3. **Production Hardening** (14-18 Std)
   - Circuit Breakers, Memory Management, Worker Pool
   - **Enterprise:** Middlewares, Observability, Security, API UX
   - **Impact:** 24/7-Fähigkeit, Enterprise-Grade Monitoring & Security

# Implementation Roadmap – Kompakt (L5, LR, Hardening, DevOps)

Erstellt: 30.10.2025  •  Status: Startklar  •  Umfang: 4–5 Tage

## Übersicht (Ziele & Ergebnisse)
- L5 Migration: 161k Dokumente mit Legal-Domain/Concept/Jurisdiction/Authority verlinken → +~608k Kanten; resumierbar, idempotent.
- LR Reasoning & Config: Multi-Hop-Abfragen (<100ms) + konfigurationsgetriebene Extraktion (YAML/JSON) mit Typsicherheit.
- Production Hardening (Core): Ausfallsicherheit (Breakers), Stabilität (Memory, Worker), Basis-Metriken (Prometheus).
- DevOps & Deployment: Docker, Compose, CI-Pipeline, Contract-Tests → reproduzierbare Builds.

## Phase L5 – Migration & Backfill
Ziel: Vollständige Relinking der Bestandsdokumente in Neo4j.
- Deliverables: `ingestion/graph/document_migration.py`, `scripts/migrate_documents_to_legal_graph.py`, Tests (7), Validation-Report.
- Eigenschaften: Batch (1000), Checkpointing, Dry-Run, Rate-Limit; optional Queue (RQ/Celery) für 10× Speedup.
- Erfolg: ≥161k Docs mit Kanten; Laufzeit <4h (ohne Queue) oder <15min (mit Queue); 0 Duplikate (idempotent).

## Phase LR – Reasoning & Config
Ziel: Erklärbare Pfad-Queries und flexible Extraktion über Konfiguration.
- Deliverables: `ingestion/reasoning/multi_hop_reasoner.py`, `ingestion/queries/graph_queries.yaml`.
- Config: `ingestion/config/config_loader.py`, `ingestion/config/extraction_rules.yaml`, `ingestion/config/schemas/extraction_rules.schema.json`.
- Enterprise: DI/Composition Root (`ingestion/di/container.py`), pydantic-settings (`ingestion/config/settings.py`), optional Hot-Reload.
- Erfolg: Multi-Hop <100ms, Config-Validierung grün, 14/14 Tests (Reasoner + Config).

## Production Hardening – Core
Ziel: 24/7-Fähigkeit für Ingestion mit Testdaten stabil absichern.
- Breakers: PG (5/60s), Neo4j (5/60s), ChromaDB (3/30s); Wrapper in `backend/ingestion.py`.
- Memory: Soft/Hard (4/6 GB), Pre-Checks vor großen Tasks, Health-Ausgabe.
- Worker: Pool-Manager (I/O/CPU), Crash-/Timeout-Erkennung, Graceful Shutdown.
- Observability: Basis-Prometheus (/prometheus), /health mit Worker/Memory/Breaker-Stats.
- Erfolg: Keine Crash-Loops; Breakers greifen; Health zeigt stabile Werte; 10/10 Kern-Tests.

## DevOps & Deployment
Ziel: Reproduzierbare Deployments und Qualitätsbarrieren.
- Docker/Compose: `deploy/Dockerfile.ingestion`, `deploy/Dockerfile.main`, `deploy/docker-compose.yml`.
- CI: `.github/workflows/ci.yml` – Lint (ruff/mypy) → Tests (pytest+cov) → Contract-Tests → Build.
- Contracts: `tests/contract/test_config_schema.py`, `tests/contract/test_api_contracts.py`.
- Erfolg: CI grün, Images bauen lokal, Compose startet alle Services mit Healthchecks.

## Zeitplan (kompakt)
- Tag 1: L5 Modul + Script + Tests; Dry-Run; Validation.
- Tag 2: LR Reasoner + Queries; Config Loader + Schema; DI + Settings.
- Tag 3: Hardening – Breakers + Memory + Worker; /health + Prometheus.
- Tag 4: Docker/Compose + CI + Contracts; Integrationstests; Doku kurz.

## Akzeptanzkriterien (kurz)
- L5: 161k verlinkt; <4h; idempotent; 7/7 Tests; Validation ok.
- LR: <100ms Pfade; Config aktiv/valide; 14/14 Tests.
- Hardening: Breaker aktiv; Memory <6 GB; Worker gesund; 10/10 Kern-Tests.
- DevOps: CI grün; Images bauen; Compose up; Contracts ok.

Hinweis: Fokus ausschließlich auf Ingestion; Daten sind Testdaten. Umfang bewusst schlank, Ergebnisse messbar.
breaker_manager = get_breaker_manager()
breaker_manager.register_breaker(
    "postgresql",
    failure_threshold=5,
    recovery_timeout=60.0,
    half_open_max_calls=3
)
breaker_manager.register_breaker(
    "chromadb",
    failure_threshold=3,
    recovery_timeout=30.0,
    half_open_max_calls=2
)
breaker_manager.register_breaker(
    "neo4j",
    failure_threshold=5,
    recovery_timeout=60.0,
    half_open_max_calls=3
)

# Wrapper functions
def _insert_postgresql_with_breaker(data: dict) -> bool:
    """PostgreSQL insert with circuit breaker protection"""
    breaker = breaker_manager.get_breaker("postgresql")
    
    def _do_insert():
        return uds3_relational.insert(data)
    
    try:
        return breaker.call(_do_insert)
    except CircuitOpenException as e:
        logger.error(f"PostgreSQL circuit open: {e}")
        raise DatabaseConnectionException(
            "PostgreSQL temporarily unavailable",
            error_code=1300,
            context={"breaker_state": "OPEN"}
        )

def _insert_chromadb_with_breaker(vector: list, metadata: dict, doc_id: str) -> bool:
    """ChromaDB insert with circuit breaker protection"""
    breaker = breaker_manager.get_breaker("chromadb")
    
    def _do_insert():
        return chromadb_client.add_vector(vector, metadata, doc_id)
    
    try:
        return breaker.call(_do_insert)
    except CircuitOpenException as e:
        logger.error(f"ChromaDB circuit open: {e}")
        raise DatabaseConnectionException(
            "ChromaDB temporarily unavailable",
            error_code=1301,
            context={"breaker_state": "OPEN"}
        )

# Replace all database calls with wrapped versions
# OLD: uds3_relational.insert(data)
# NEW: _insert_postgresql_with_breaker(data)
```

**2. Testing (1 Std)**

**File:** `tests/test_circuit_breaker_integration.py` (200+ Zeilen)

```python
def test_postgresql_circuit_breaker():
    """Test PostgreSQL circuit breaker triggers on failures"""
    # Simulate 5 consecutive failures
    # Verify circuit opens
    # Verify CircuitOpenException raised
    ...

def test_circuit_breaker_recovery():
    """Test circuit breaker recovers after timeout"""
    # Open circuit
    # Wait recovery_timeout seconds
    # Verify circuit enters HALF_OPEN
    # Successful call → CLOSED
    ...

def test_circuit_breaker_metrics():
    """Test circuit breaker exposes metrics"""
    # Check breaker_manager.get_stats()
    # Verify failure_count, state, last_failure_time
    ...
```

### Part 2: Memory Management (3-4 Std)

**Already implemented:** `ingestion/memory_manager.py` (400+ Zeilen)  
**Integration needed:** Add memory checks before large operations

#### Implementation Steps

**1. Integrate Memory Manager (2 Std)**

**File:** `backend/ingestion.py` (modify existing)

```python
# Add after imports
from ingestion.memory_manager import initialize_memory_manager, get_memory_manager

# Initialize in lifespan
memory_manager = initialize_memory_manager(
    soft_limit_mb=4096,  # 4 GB
    hard_limit_mb=6144,  # 6 GB
    check_interval=30.0,  # 30 seconds
    enable_leak_detection=True
)

# Add memory checks before large operations
async def process_file_upload(file: UploadFile, ...):
    """Process uploaded file with memory safety"""
    
    # Check memory before processing
    file_size_mb = file.size / (1024 * 1024)
    
    if not memory_manager.check_can_allocate(file_size_mb):
        raise MemoryLimitExceededException(
            f"Cannot allocate {file_size_mb:.1f} MB",
            error_code=1500,
            context={
                "current_mb": memory_manager.get_current_usage_mb(),
                "soft_limit_mb": 4096,
                "hard_limit_mb": 6144
            }
        )
    
    # Proceed with processing
    ...

# Add memory monitoring to /health endpoint
@app.get("/health")
async def health():
    memory_stats = memory_manager.get_stats()
    return {
        "status": "healthy",
        "memory": {
            "current_mb": memory_stats["current_mb"],
            "soft_limit_mb": memory_stats["soft_limit_mb"],
            "hard_limit_mb": memory_stats["hard_limit_mb"],
            "usage_percent": memory_stats["usage_percent"]
        }
    }
```

**2. Testing (1 Std)**

**File:** `tests/test_memory_management.py` (200+ Zeilen)

```python
def test_memory_check_before_upload():
    """Test memory check rejects oversized files"""
    # Create fake file > soft limit
    # Verify MemoryLimitExceededException raised
    ...

def test_memory_monitoring():
    """Test memory stats exposed in /health"""
    # Call /health endpoint
    # Verify memory stats present
    ...

def test_memory_leak_detection():
    """Test memory leak detection triggers"""
    # Simulate gradual memory growth
    # Verify leak detection warning logged
    ...
```

### Part 3: Worker Pool Manager (4-6 Std)

**Already implemented:** `ingestion/worker_pool.py` (500+ Zeilen)  
**Integration needed:** Replace direct executor calls with managed pool

#### Implementation Steps

**1. Replace Executor Calls (3 Std)**

**File:** `backend/ingestion.py` (modify existing, ~20 locations)

```python
# OLD (Direct Executor)
future = io_executor.submit(
    process_file,
    file_path,
    ...
)

# NEW (Managed Pool)
task_id = f"process_file_{timestamp}_{uuid4()}"
future = pool_manager.submit_io_task(
    func=process_file,
    args=(file_path,),
    kwargs={...},
    task_id=task_id,
    timeout=600.0  # 10 minutes
)
```

**Search & Replace Locations:**
- `io_executor.submit(` → ~15 occurrences
- `cpu_executor.submit(` → ~5 occurrences

**2. Add Health Monitoring (1 Std)**

```python
@app.get("/workers/health")
async def workers_health():
    """Worker pool health status"""
    pool_stats = pool_manager.get_stats()
    return {
        "io_workers": {
            "total": pool_stats["io_workers"]["total"],
            "idle": pool_stats["io_workers"]["idle"],
            "busy": pool_stats["io_workers"]["busy"],
            "crashed": pool_stats["io_workers"]["crashed"]
        },
        "cpu_workers": {
            "total": pool_stats["cpu_workers"]["total"],
            "idle": pool_stats["cpu_workers"]["idle"],
            "busy": pool_stats["cpu_workers"]["busy"],
            "crashed": pool_stats["cpu_workers"]["crashed"]
        },
        "tasks": {
            "submitted": pool_stats["tasks"]["submitted"],
            "completed": pool_stats["tasks"]["completed"],
            "failed": pool_stats["tasks"]["failed"]
        }
    }
```

**3. Testing (2 Std)**

**File:** `tests/test_worker_pool_integration.py` (300+ Zeilen)

```python
def test_worker_crash_detection():
    """Test worker crash detected within 5 minutes"""
    # Simulate worker crash (force exit)
    # Wait 5 minutes
    # Verify crash detected in pool stats
    ...

def test_task_timeout_detection():
    """Test task timeout triggers after 10 minutes"""
    # Submit long-running task (11 minutes)
    # Verify timeout detected
    # Verify task marked as failed
    ...

def test_graceful_shutdown():
    """Test graceful shutdown waits for tasks"""
    # Submit tasks
    # Trigger shutdown
    # Verify waits up to 30 seconds
    # Verify tasks completed before exit
    ...

def test_heartbeat_tracking():
    """Test worker heartbeats tracked"""
    # Check pool_manager._worker_heartbeats
    # Verify updated every 30 seconds
    ...
```

### Acceptance Criteria

**Production Hardening - Circuit Breakers:**
- [ ] 3 Circuit Breakers registered (PostgreSQL, ChromaDB, Neo4j)
- [ ] All database operations wrapped with breakers
- [ ] Tests: 3/3 PASS (trigger, recovery, metrics)
- [ ] /health endpoint shows breaker states

**Production Hardening - Memory Management:**
- [ ] Memory Manager initialized (4GB soft / 6GB hard)
- [ ] Memory checks before file uploads
- [ ] Memory stats in /health endpoint
- [ ] Tests: 3/3 PASS (check, monitoring, leak detection)

**Production Hardening - Worker Pool:**
- [ ] All executor calls replaced with pool_manager (20+ locations)
- [ ] Worker crash detection (<5 min)
- [ ] Task timeout detection (10 min)
- [ ] Graceful shutdown (30s wait)
- [ ] /workers/health endpoint
- [ ] Tests: 4/4 PASS (crash, timeout, shutdown, heartbeat)

---

## 🏢 Phase 4: DevOps & Deployment (4-6 Std)

### Ziel
Reproduzierbare Deployments, CI/CD Pipelines, Contract Tests.

### Part 1: Dockerization (2 Std)

**File:** `deploy/Dockerfile.ingestion` (100 Zeilen)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ingestion/ ./ingestion/
COPY backend/ ./backend/
COPY config.py ./
COPY .env.production ./

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:45679/health || exit 1

# Run backend
CMD ["python", "-m", "uvicorn", "backend.ingestion:app", "--host", "0.0.0.0", "--port", "45679"]
```

**File:** `deploy/docker-compose.yml` (150 Zeilen)

```yaml
version: '3.8'

services:
  ingestion-backend:
    build:
      context: ..
      dockerfile: deploy/Dockerfile.ingestion
    container_name: covina-ingestion
    ports:
      - "45679:45679"
    environment:
      - POSTGRES_HOST=postgres
      - CHROMA_HOST=chromadb
      - NEO4J_URI=bolt://neo4j:7687
      - COUCHDB_HOST=couchdb
      - WORKERS_IO=36
      - WORKERS_CPU=36
    volumes:
      - ../data:/app/data
      - ../logs:/app/logs
    depends_on:
      - postgres
      - chromadb
      - neo4j
      - couchdb
    networks:
      - covina-network
    restart: unless-stopped
  
  main-backend:
    build:
      context: ..
      dockerfile: deploy/Dockerfile.main
    container_name: covina-main
    ports:
      - "45678:45678"
    environment:
      - POSTGRES_HOST=postgres
      - CHROMA_HOST=chromadb
      - NEO4J_URI=bolt://neo4j:7687
    depends_on:
      - postgres
      - chromadb
      - neo4j
    networks:
      - covina-network
    restart: unless-stopped

networks:
  covina-network:
    driver: bridge
```

### Part 2: CI/CD Pipeline (2 Std)

**File:** `.github/workflows/ci.yml` (200 Zeilen)

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop, 'feature/**']
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install ruff mypy pytest
          pip install -r requirements.txt
      
      - name: Run ruff
        run: ruff check ingestion/ backend/ tests/
      
      - name: Run mypy
        run: mypy ingestion/ backend/ --ignore-missing-imports
  
  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/neo4j
        options: >-
          --health-cmd "cypher-shell 'RETURN 1'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov
          pip install -r requirements.txt
      
      - name: Run tests
        env:
          POSTGRES_HOST: localhost
          NEO4J_URI: bolt://localhost:7687
        run: |
          pytest tests/ -v --cov=ingestion --cov=backend --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
  
  contract-test:
    name: Contract Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest jsonschema pyyaml
          pip install -r requirements.txt
      
      - name: Validate Config Schemas
        run: |
          python tests/contract/test_config_schema.py
      
      - name: Validate API Contracts
        run: |
          pytest tests/contract/test_api_contracts.py -v
  
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [lint, test, contract-test]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build image
        run: |
          docker build -f deploy/Dockerfile.ingestion -t covina-ingestion:latest .
          docker build -f deploy/Dockerfile.main -t covina-main:latest .
      
      - name: Save images
        run: |
          docker save covina-ingestion:latest | gzip > covina-ingestion.tar.gz
          docker save covina-main:latest | gzip > covina-main.tar.gz
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: docker-images
          path: |
            covina-ingestion.tar.gz
            covina-main.tar.gz
```

### Part 3: Contract Tests (1-2 Std)

**File:** `tests/contract/test_config_schema.py` (100 Zeilen)

```python
"""
Contract Tests: Config Schema Validation

Ensures all config files conform to JSON schemas.
"""

import json
import yaml
from pathlib import Path
from jsonschema import validate, ValidationError
import pytest

def test_extraction_rules_schema():
    """Validate extraction_rules.yaml against schema"""
    schema_path = Path("ingestion/config/schemas/extraction_rules.schema.json")
    config_path = Path("ingestion/config/extraction_rules.yaml")
    
    with open(schema_path) as f:
        schema = json.load(f)
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Should not raise
    validate(instance=config, schema=schema)

def test_concept_synonyms_schema():
    """Validate concept_synonyms.json format"""
    config_path = Path("ingestion/config/concept_synonyms.json")
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Basic structure validation
    assert isinstance(config, dict)
    for key, values in config.items():
        assert isinstance(key, str)
        assert isinstance(values, list)
        for value in values:
            assert isinstance(value, str)

def test_all_pattern_configs_valid():
    """Validate all pattern/*.yaml files"""
    schema_path = Path("ingestion/config/schemas/extraction_rules.schema.json")
    pattern_dir = Path("ingestion/config/patterns")
    
    with open(schema_path) as f:
        schema = json.load(f)
    
    for yaml_file in pattern_dir.glob("*.yaml"):
        with open(yaml_file) as f:
            config = yaml.safe_load(f)
        
        validate(instance=config, schema=schema)
        print(f"✅ {yaml_file.name} is valid")
```

**File:** `tests/contract/test_api_contracts.py` (150 Zeilen)

```python
"""
Contract Tests: API Response Schemas

Ensures API endpoints return expected response structures.
"""

from fastapi.testclient import TestClient
from backend.main import app
import pytest

client = TestClient(app)

def test_legal_graph_health_contract():
    """Verify /legal-graph/health response structure"""
    response = client.get("/legal-graph/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Contract: Must have these fields
    assert "status" in data
    assert "neo4j_available" in data
    assert "node_count" in data
    assert "relationship_count" in data
    
    # Contract: Types
    assert isinstance(data["status"], str)
    assert isinstance(data["neo4j_available"], bool)
    assert isinstance(data["node_count"], int)

def test_legal_analytics_laws_per_domain_contract():
    """Verify /legal-analytics/laws-per-domain response structure"""
    response = client.get("/legal-analytics/laws-per-domain")
    
    assert response.status_code == 200
    data = response.json()
    
    # Contract: Pagination
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    
    # Contract: Item structure
    for item in data["items"]:
        assert "domain_id" in item
        assert "domain_name" in item
        assert "law_count" in item
        assert isinstance(item["law_count"], int)

def test_ingestion_health_contract():
    """Verify /health endpoint (ingestion backend)"""
    # Note: This would use a separate client for port 45679
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Contract: Core metrics
    assert "status" in data
    assert "uptime_seconds" in data
    assert "databases" in data
    
    # Contract: Database health
    for db_name in ["postgresql", "chromadb", "neo4j", "couchdb"]:
        assert db_name in data["databases"]
        assert "available" in data["databases"][db_name]
```

### Acceptance Criteria

- [ ] Dockerfile für beide Backends erstellt
- [ ] docker-compose.yml funktioniert (all services up)
- [ ] CI Pipeline erstellt (.github/workflows/ci.yml)
- [ ] Contract Tests implementiert (config + API schemas)
- [ ] Pipeline runs: Lint → Test → Contract → Build
- [ ] Docker images tagged & ready for deployment

---

## 📊 Updated Implementation Timeline

### Day 1: Phase L5 Migration (10 Std)

**Morning (4 Std):**
- ✅ Implement DocumentMigrator class
- ✅ Implement migration script

**Afternoon (4 Std):**
- ✅ Implement task queue (RQ/Celery) - Optional
- ✅ Create test cases
- ✅ Run tests (fix bugs)

**Evening (2 Std):**
- ✅ Dry-run migration (validate logic)
- ✅ Create validation script

### Day 2: Phase LR Reasoning (10 Std)

**Morning (4 Std):**
- ✅ Implement MultiHopReasoner
- ✅ Create query templates (YAML)
- ✅ Implement query caching

**Afternoon (4 Std):**
- ✅ Implement DI Container (ingestion/di/container.py)
- ✅ Implement pydantic-settings (ingestion/config/settings.py)
- ✅ Update Reasoner to use DI

**Evening (2 Std):**
- ✅ Implement config loader
- ✅ Create JSON schema
- ✅ Create sample configs

### Day 3-4: Production Hardening (16 Std)

**Day 3 Morning (4 Std):**
- ✅ Integrate Circuit Breakers (3 databases)
- ✅ Integrate Memory Manager

**Day 3 Afternoon (4 Std):**
- ✅ Add Middlewares (CORS, GZip, Rate Limit, Request ID)
- ✅ Implement Prometheus instrumentierung

**Day 4 Morning (4 Std):**
- ✅ Replace executor calls with pool_manager
- ✅ Add JWT middleware integration
- ✅ Implement API versioning (/v1)

**Day 4 Afternoon (4 Std):**
- ✅ Implement request size limits & timeouts
- ✅ Add retry logic with backoff
- ✅ Enhanced OpenAPI docs

### Day 5: DevOps & Testing (8 Std)

**Morning (4 Std):**
- ✅ Create Dockerfiles
- ✅ Create docker-compose.yml
- ✅ CI Pipeline (.github/workflows/ci.yml)

**Afternoon (4 Std):**
- ✅ Contract Tests (config schemas + API)
- ✅ Integration testing (all services)
- ✅ Documentation updates

**Total:** 44 Stunden (5.5 Tage)

---

## ✅ Success Criteria (Updated)

### Phase L5
- [ ] 161k documents successfully linked
- [ ] Migration time: <4 hours (or <15 min with task queue)
- [ ] Checkpointing works (can resume)
- [ ] Validation: 100% documents have relations
- [ ] Tests: 7/7 PASS
- [ ] **Enterprise:** Task queue optional, progress tracking

### Phase LR
- [ ] Multi-hop queries work (<100ms)
- [ ] Config-driven extraction active
- [ ] Hot-reload optional (ENV flag)
- [ ] Tests: 14/14 PASS (7 reasoner + 7 config)
- [ ] **Enterprise:** DI Container, pydantic-settings, type-safe configs

### Production Hardening
- [ ] Circuit breakers prevent cascading failures
- [ ] Memory stays <6 GB (hard limit)
- [ ] Worker crashes detected <5 min
- [ ] Graceful shutdown works (30s)
- [ ] Tests: 10/10 PASS (3 breaker + 3 memory + 4 workers)
- [ ] **Enterprise:** Middlewares, Prometheus, JWT, API v1, Retries

### DevOps & Deployment
- [ ] Docker images build successfully
- [ ] docker-compose brings up all services
- [ ] CI Pipeline runs (Lint → Test → Contract → Build)
- [ ] Contract tests validate schemas
- [ ] Healthchecks work in containers
- [ ] Documentation complete

---

## 📞 Next Steps

**Immediate (jetzt):**
1. Review dieser Roadmap
2. Entscheidung: Welche Phase zuerst? (Empfehlung: L5 → LR → Hardening → DevOps)
3. Git Branch erstellen: `git checkout -b feature/priority-phases`

**Phase L5 Start:**
```bash
# Create module structure
mkdir -p ingestion/graph
mkdir -p ingestion/migration
mkdir -p scripts
mkdir -p tests/graph
mkdir -p data/migration

# Create skeleton files
touch ingestion/graph/document_migration.py
touch ingestion/migration/task_queue.py
touch scripts/migrate_documents_to_legal_graph.py
touch scripts/migrate_documents_to_legal_graph_distributed.py
touch tests/graph/test_document_migration.py
touch tests/validate_migration.py
```

**Bereit für Implementation?** 🚀

---

**Erstellt:** 30. Oktober 2025  
**Updated:** 30. Oktober 2025 (Enterprise Features integriert)  
**Status:** Ready for Implementation  
**Estimated Completion:** 5-6 Tage (44 Stunden)
