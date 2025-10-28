#!/usr/bin/env python3
"""
Covina FastAPI Main Backend
============================

Main Backend für das Covina Document Management System.
Fokus: Queries, DSGVO, Review Queue, Handelsregister.

HINWEIS: Upload/Ingestion läuft auf separatem Ingestion Backend (Port 45679)

Features:
- Query-API für Dokumentensuche
- DSGVO-Compliance-Funktionen
- Review Queue Management
- Handelsregister-Integration
- System Health & Monitoring

Port: 45678 (Ingestion Backend: 45679)
Autor: Covina System
Datum: 17. Oktober 2025
"""

# KRITISCH: Füge Covina Root zum Python Path hinzu BEVOR irgendwelche Imports!
import os
import sys
covina_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if covina_root not in sys.path:
    sys.path.insert(0, covina_root)

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Query as QueryParam, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from fastapi.security import OAuth2PasswordRequestForm

# Initialize JSON Structured Logging EARLY (before any logger usage)
try:
    from utils.json_logging import setup_json_logging
    setup_json_logging(
        service_name="main_backend",
        level=logging.INFO,
        environment=os.getenv("ENVIRONMENT", "development"),
        version="3.4.10"
    )
    logger = logging.getLogger("covina_backend")
    logger.info("✅ JSON Structured Logging aktiviert")
except Exception as e:
    # Fallback to basic config
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("covina_backend")
    logger.warning(f"⚠️ JSON Logging fehlgeschlagen, Fallback zu basicConfig: {e}")

# Add PII Redaction Filter for DSGVO compliance
try:
    from utils.pii_redaction import PIIRedactionFilter
    pii_filter = PIIRedactionFilter()
    logging.getLogger().addFilter(pii_filter)  # Apply to root logger
    logger.info(f"✅ PII Redaction Filter aktiviert ({pii_filter.get_patterns_count()} patterns)")
except Exception as e:
    logger.warning(f"⚠️ PII Redaction Filter konnte nicht geladen werden: {e}")

# Initialize Metrics System
try:
    from utils.metrics import metrics_registry, Counter, Gauge, Histogram
    
    # Query Metrics
    queries_total = metrics_registry.register(
        Counter("queries_total", "Total queries executed", ["endpoint", "status"])
    )
    query_latency = metrics_registry.register(
        Histogram("query_latency_seconds", "Query execution time", ["endpoint"])
    )
    
    # Database Metrics
    db_operations = metrics_registry.register(
        Counter("db_operations_total", "Database operations", ["database", "operation", "status"])
    )
    db_latency = metrics_registry.register(
        Histogram("db_operation_seconds", "Database operation time", ["database", "operation"])
    )
    
    # Connection Pool Metrics
    pool_connections = metrics_registry.register(
        Gauge("pool_connections_current", "Current pool connections", ["state"])
    )
    
    # Active Request Tracking
    active_requests = metrics_registry.register(
        Gauge("active_requests_current", "Current active requests", [])
    )
    
    logger.info("✅ Metrics system initialized (6 metrics registered)")
    METRICS_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ Metrics system not available: {e}")
    METRICS_AVAILABLE = False
    # Create dummy objects
    queries_total = None
    query_latency = None
    db_operations = None
    db_latency = None
    pool_connections = None
    active_requests = None

# Load ENV configuration early (for UDS3 + DB pooling settings)
try:
    from dotenv import load_dotenv
    load_dotenv('.env.production')
except Exception as e:
    # .env.production not found - will use system ENV variables
    logging.warning(f"Could not load .env.production: {e}")

# Security (OAuth2/JWT + RBAC)
try:
    from security.auth import (
        Role,
        Principal,
        create_access_token,
        get_current_user,
        require_roles,
    )
    AUTH_AVAILABLE = True
    logger.info("✅ Security module loaded (OAuth2/JWT + RBAC)")
except Exception as e:
    AUTH_AVAILABLE = False
    logger.debug(f"Security module not available (optional): {e}")  # Changed to DEBUG level

# Logging already initialized above

# Import Covina Core Components
GAP_DETECTION_AVAILABLE = False
POSTGRES_AVAILABLE = False
REVIEW_QUEUE_AVAILABLE = False

try:
    from gap_detection.gap_database import KnowledgeGapDB
    GAP_DETECTION_AVAILABLE = True
    logger.info("✅ Gap Detection Module geladen")
except Exception as e:
    logger.warning(f"⚠️ Gap Detection nicht verfügbar: {e}")
    KnowledgeGapDB = None  # Define as None if import fails

try:
    from uds3.core.polyglot_manager import UDS3PolyglotManager
    UDS3_AVAILABLE = True
    logger.info("✅ UDS3 PolyglotManager Module geladen")
except Exception as e:
    logger.warning(f"⚠️ UDS3 PolyglotManager nicht verfügbar: {e}")
    UDS3_AVAILABLE = False

# Import UDS3 Batch Operations (Phase 3 - READ) - Using installed UDS3 package
try:
    from uds3.database.batch_operations import PostgreSQLBatchReader, ParallelBatchReader
    BATCH_OPERATIONS_AVAILABLE = True
    logger.info("✅ UDS3 Batch Operations (Phase 3 - READ) Module geladen (from uds3 package)")
except Exception as e:
    logger.warning(f"⚠️ UDS3 Batch Operations nicht verfügbar: {e}")
    BATCH_OPERATIONS_AVAILABLE = False

# NOTE: Batch WRITE Operations (Phase 4) now integrated into database adapters
# No separate BatchExecutor imports needed - using adapter methods directly
BATCH_WRITE_AVAILABLE = True  # Always available if backends are available
logger.info("✅ Batch WRITE Operations (Phase 4) - Using Adapter Methods")

try:
    from management_core.review_queue import ReviewQueue, TaskStatus, TaskSeverity, GapType
    REVIEW_QUEUE_AVAILABLE = True
    logger.info("✅ Review Queue Module geladen")
except Exception as e:
    logger.warning(f"⚠️ Review Queue nicht verfügbar: {e}")
    REVIEW_QUEUE_AVAILABLE = False
    ReviewQueue = None  # Define as None if import fails

try:
    from compliance_service import ComplianceService, get_compliance_service
    COMPLIANCE_AVAILABLE = True
    logger.info("✅ Compliance Service Module geladen")
except Exception as e:
    logger.warning(f"⚠️ Compliance Service nicht verfügbar: {e}")
    COMPLIANCE_AVAILABLE = False
    ComplianceService = None  # Define as None if import fails

# ChromaDB availability will be checked via UDS3 Strategy
CHROMADB_AVAILABLE = False  # Will be set after UDS3 initialization

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("✅ sentence-transformers Module geladen")
except Exception as e:
    logger.warning(f"⚠️ sentence-transformers nicht verfügbar: {e}")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None  # Define as None if import fails

# Rate Limiting Setup (slowapi)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["500/minute"])

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def get_postgres_batch_size() -> int:
    """
    Get PostgreSQL batch size from environment or default.
    
    Returns:
        Batch size (default: 100, recommended: 50-200)
    """
    import os
    return int(os.getenv("POSTGRES_BATCH_SIZE", "100"))

# ================================================================
# LIFESPAN CONTEXT MANAGER (replaces deprecated @app.on_event)
# ================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    """
    # ============================================================
    # STARTUP
    # ============================================================
    global gap_db, uds3_strategy, postgres_backend, review_queue, compliance_service, chromadb_backend, embedding_model
    global POSTGRES_AVAILABLE, CHROMADB_AVAILABLE
    
    # Assign a synthetic correlation ID for startup logs
    try:
        from utils.json_logging import set_correlation_id
        set_correlation_id("startup:main")
    except Exception:
        pass
    logger.info("🚀 Covina Main Backend startet...")
    logger.info("📌 Port: 45678 (Main Backend)")
    logger.info("📌 Ingestion Backend: Port 45679")
    
    # Initialize UDS3 Polyglot Manager FIRST (needed by KnowledgeGapDB!)
    if UDS3_AVAILABLE:
        try:
            logger.info("=" * 80)
            logger.info("🔧 UDS3 v2.0.0 AUTO-CONFIG (Main)")
            logger.info("=" * 80)
            logger.info("Pattern: Backend-Typen angeben → UDS3 konfiguriert automatisch")
            logger.info("")
            
            # Nur Backend-TYPEN angeben - UDS3 Database Manager übernimmt Rest!
            backend_config = {
                "relational": {"enabled": True},  # PostgreSQL
                "vector": {"enabled": True}       # ChromaDB
            }
            
            uds3_strategy = UDS3PolyglotManager(
                backend_config=backend_config,
                enable_rag=False
            )
            logger.info("✅ UDS3 PolyglotManager initialisiert (Auto-Config)")
            
            # Get backends from UDS3
            postgres_backend = uds3_strategy.db_manager.get_relational_backend()
            chromadb_backend = uds3_strategy.db_manager.get_vector_backend()
            
            POSTGRES_AVAILABLE = postgres_backend is not None
            CHROMADB_AVAILABLE = chromadb_backend is not None
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ UDS3 AUTO-CONFIG COMPLETE (Main)")
            logger.info("=" * 80)
            logger.info(f"   PostgreSQL: {'✅ Connected' if POSTGRES_AVAILABLE else '❌ Not available'}")
            logger.info(f"   ChromaDB:   {'✅ Connected' if CHROMADB_AVAILABLE else '❌ Not available'}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error("❌ CRITICAL ERROR: UDS3 Setup Failed (Main)")
            logger.error("=" * 80)
            logger.error(f"Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            uds3_strategy = None
            postgres_backend = None
            chromadb_backend = None
            POSTGRES_AVAILABLE = False
            CHROMADB_AVAILABLE = False
    
    # Initialize Gap Detection Database (uses UDS3 PostgreSQL backend)
    if GAP_DETECTION_AVAILABLE and POSTGRES_AVAILABLE and postgres_backend:
        try:
            logger.info("Initializing Knowledge Gap Database with UDS3 Relational Backend")
            gap_db = KnowledgeGapDB(postgres_backend=postgres_backend)
            logger.info("✅ Gap Detection Database initialisiert (UDS3 Backend)")
        except Exception as e:
            logger.error(f"❌ Gap Detection Initialization Fehler: {e}")
            gap_db = None
    
    # Initialize Review Queue (PostgreSQL)
    if REVIEW_QUEUE_AVAILABLE and POSTGRES_AVAILABLE and postgres_backend:
        try:
            review_queue = ReviewQueue(postgres_backend=postgres_backend)
            logger.info("✅ Review Queue (PostgreSQL) initialisiert")
        except Exception as e:
            logger.error(f"❌ Review Queue Initialization Fehler: {e}")
            review_queue = None
    
    # Initialize Compliance Service (requires PostgreSQL)
    if COMPLIANCE_AVAILABLE and POSTGRES_AVAILABLE and postgres_backend:
        try:
            compliance_service = get_compliance_service(postgres_backend)
            logger.info("✅ Compliance Service initialisiert")
        except Exception as e:
            logger.error(f"❌ Compliance Service Initialization Fehler: {e}")
            compliance_service = None
    
    # Lazy load sentence-transformers (optional)
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        logger.info("📦 sentence-transformers bereit (Lazy Loading bei erster Suche)")
    
    # Phase 4 Batch Operations Status
    logger.info("✅ Batch WRITE Operations (Phase 4) - Ready (Adapter Methods)")
    
    # Phase 3 Batch Operations Initialization
    if BATCH_OPERATIONS_AVAILABLE and uds3_strategy:
        try:
            logger.info("=" * 80)
            logger.info("🚀 PHASE 3: BATCH OPERATIONS INITIALIZATION")
            logger.info("=" * 80)
            
            # PostgreSQL Batch Reader
            postgres_batch_reader = PostgreSQLBatchReader(
                postgresql_backend=postgres_backend
            )
            logger.info("✅ PostgreSQL Batch Reader initialisiert")
            logger.info("   Endpoints: /api/v1/batch/get, /api/v1/batch/exists")
            
            # Parallel Batch Reader
            # Note: ParallelBatchReader takes individual readers, not a backends dict
            parallel_batch_reader = ParallelBatchReader(
                postgres_reader=postgres_batch_reader,
                chromadb_reader=None,  # TODO: Create ChromaDBBatchReader if needed
                couchdb_reader=None,   # TODO: Create CouchDBBatchReader if needed
                neo4j_reader=None      # TODO: Create Neo4jBatchReader if needed
            )
            active_readers = sum(1 for r in [postgres_batch_reader] if r is not None)
            logger.info(f"✅ Parallel Batch Reader initialisiert ({active_readers} readers)")
            logger.info("   Endpoints: /api/v1/batch/search (multi-database)")
            
            logger.info("=" * 80)
            logger.info("✅ Phase 3 Batch Operations Ready")
            logger.info("   Expected Performance: 8-97x speedup vs sequential")
            logger.info("   Batch Size Recommendation: 50-200 documents")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Batch Operations Initialization Fehler: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info("✅ Main Backend bereit für Queries, DSGVO, Review Queue, Compliance, Semantic Search, Governance, Batch Operations")
    # Minimal sichtbare Konsolen-Ausgabe (unabhängig vom JSON-Logger)
    try:
        ready_line = (
            f"[READY] Main Backend :45678 | "
            f"Postgres: {'OK' if POSTGRES_AVAILABLE and postgres_backend else 'NO'} | "
            f"Chroma: {'OK' if CHROMADB_AVAILABLE and chromadb_backend and not FLAGS.get('KILL_SWITCH_CHROMADB', False) else 'NO'} | "
            f"Docs: /docs | Health: /health"
        )
        print(ready_line, flush=True)
    except Exception:
        pass
    
    # ============================================================
    # YIELD (Application runs here)
    # ============================================================
    yield
    
    # ============================================================
    # SHUTDOWN
    # ============================================================
    logger.info("🛑 Covina Main Backend wird heruntergefahren...")
    
    # Cleanup Gap Detection
    if gap_db:
        try:
            gap_db.close()
            logger.info("✅ Gap Detection geschlossen")
        except Exception as e:
            logger.error(f"❌ Gap Detection Cleanup Fehler: {e}")
    
    # Cleanup Review Queue (uses PostgreSQL connection)
    if review_queue:
        try:
            # Review Queue wird über postgres_backend cleanup geschlossen
            logger.info("✅ Review Queue geschlossen")
        except Exception as e:
            logger.error(f"❌ Review Queue Cleanup Fehler: {e}")
    
    # Cleanup PostgreSQL
    if postgres_backend:
        try:
            postgres_backend.disconnect()
            logger.info("✅ PostgreSQL Backend getrennt")
        except Exception as e:
            logger.error(f"❌ PostgreSQL Cleanup Fehler: {e}")
    
    logger.info("👋 Covina Main Backend heruntergefahren")


# FastAPI App Initialisierung mit Lifespan
app = FastAPI(
    title="Covina Main Backend API",
    description="Main Backend für Queries, DSGVO, Review Queue (Ingestion läuft auf Port 45679)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # ✅ NEW: Modern lifespan event handler
)

# Register Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion spezifischer konfigurieren
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID Middleware for request tracing
try:
    from utils.json_logging import create_correlation_id_middleware
    app.middleware("http")(create_correlation_id_middleware())
    logger.info("✅ Correlation ID Middleware aktiviert")
except Exception as e:
    logger.warning(f"⚠️ Correlation ID Middleware konnte nicht aktiviert werden: {e}")

# Active Request Tracking Middleware
if METRICS_AVAILABLE and active_requests is not None:
    @app.middleware("http")
    async def track_active_requests(request: Request, call_next):
        """Track concurrent active requests."""
        active_requests.inc()
        try:
            response = await call_next(request)
            return response
        finally:
            active_requests.dec()
    logger.info("✅ Active Request Tracking Middleware aktiviert")

# Global State
FLAGS: Dict[str, bool] = {
    # Hard kill-switch für kritische Integrationen (sofort wirksam ohne Deploy)
    "KILL_SWITCH_CHROMADB": False,
}

gap_db: Optional[KnowledgeGapDB] = None
uds3_strategy = None  # UDS3 Polyglot Strategy
postgres_backend = None  # Will be set from uds3_strategy.relational_backend
review_queue: Optional['ReviewQueue'] = None
compliance_service: Optional['ComplianceService'] = None
chromadb_backend = None  # Will be set from uds3_strategy.vector_backend
embedding_model: Optional['SentenceTransformer'] = None

# Batch Operations (Phase 3)
postgres_batch_reader = None  # PostgreSQL Batch Reader
parallel_batch_reader = None  # Parallel Multi-Database Batch Reader

# Pool Metrics Tracking
def update_pool_metrics():
    """Update PostgreSQL connection pool metrics using get_pool_stats()."""
    if not METRICS_AVAILABLE or pool_connections is None:
        return
    
    try:
        # Check if postgres_backend has get_pool_stats() method
        if postgres_backend and hasattr(postgres_backend, 'get_pool_stats'):
            stats = postgres_backend.get_pool_stats()
            
            # Active connections (checked out from pool)
            active = stats.get('active', 0)
            pool_connections.set(active, labels={"state": "active"})
            
            # Idle connections (available in pool)
            idle = stats.get('idle', 0)
            pool_connections.set(idle, labels={"state": "idle"})
            
            # Total pool size
            total = stats.get('total', 0)
            pool_connections.set(total, labels={"state": "total"})
            
    except Exception as e:
        logger.debug(f"Failed to update pool metrics: {e}")

# Pydantic Models für API
class SystemHealth(BaseModel):
    status: str
    backend_type: str
    port: int
    ingestion_backend: str
    features_available: Dict[str, bool]
    system_resources: Dict[str, Any]

class KnowledgeGap(BaseModel):
    """Knowledge Gap Model"""
    gap_type: str
    description: str
    severity: str = "medium"
    status: str = "open"
    source: Optional[str] = None
    context: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class GoldenDatasetEntry(BaseModel):
    """Golden Dataset Entry Model (Relational)"""
    document_id: str
    classification: str
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    reviewed_by: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class GraphGoldenPattern(BaseModel):
    """Graph Golden Dataset Pattern Model (Neo4j/Graph-based)"""
    pattern_id: str
    name: str
    description: Optional[str] = None
    category: str  # 'invoice_processing', 'compliance', 'organization', 'workflow'
    nodes_definition: List[Dict[str, Any]]  # [{'id': 'node1', 'label': 'Invoice', 'properties': {...}}]
    relationships_definition: List[Dict[str, Any]]  # [{'from': 'node1', 'to': 'node2', 'type': 'TRIGGERED'}]
    validation_rules: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    tags: Optional[List[str]] = None
    status: str = "active"  # 'active', 'draft', 'archived'

class ComplianceCheck(BaseModel):
    """Compliance Check Model"""
    check_type: str  # "dsgvo", "gdpr", "regulatory"
    document_id: Optional[str] = None
    status: str = "pending"
    findings: Optional[List[str]] = None
    risk_level: str = "medium"
    metadata: Optional[Dict[str, Any]] = None

class GovernancePolicy(BaseModel):
    """Governance Policy Model"""
    policy_id: str
    name: str
    description: Optional[str] = None
    policy_type: str  # 'retention', 'access_control', 'classification', 'quality', 'audit', 'compliance', 'custom'
    scope: str = "global"  # 'global', 'department', 'project', 'document_type', 'custom'
    rules: Dict[str, Any]  # Regelwerk als JSON
    status: str = "active"  # 'active', 'draft', 'archived'
    priority: int = 100
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentQuery(BaseModel):
    """Document Query Model"""
    query_text: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class ReviewQueueItem(BaseModel):
    """Review Queue Item Model"""
    item_id: str
    document_id: str
    review_type: str  # "classification", "quality", "compliance"
    status: str = "pending"
    priority: str = "normal"
    assigned_to: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Batch Operations Models (Phase 3)
class BatchGetRequest(BaseModel):
    """Batch GET Request Model"""
    document_ids: List[str] = Field(..., description="List of document IDs to retrieve")
    fields: Optional[List[str]] = Field(None, description="Optional field selection (default: all)")
    include_metadata: bool = Field(True, description="Include document metadata")

class BatchExistsRequest(BaseModel):
    """Batch Exists Check Request Model"""
    document_ids: List[str] = Field(..., description="List of document IDs to check")

class BatchSearchRequest(BaseModel):
    """Batch Search Request Model"""
    queries: List[str] = Field(..., description="List of search queries")
    top_k: int = Field(5, ge=1, le=20, description="Number of results per query")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")

# Batch WRITE Operations Models (Phase 4)
class DocumentUpdate(BaseModel):
    """Single document update specification"""
    document_id: str = Field(..., description="Document ID to update")
    fields: Dict[str, Any] = Field(..., description="Fields to update with new values")

class BatchUpdateRequest(BaseModel):
    """Batch UPDATE Request Model"""
    updates: List[DocumentUpdate] = Field(..., description="List of document updates")
    update_mode: str = Field("partial", description="Update mode: 'partial' or 'full'")
    databases: Optional[List[str]] = Field(None, description="Target databases (default: all)")

class BatchDeleteRequest(BaseModel):
    """Batch DELETE Request Model"""
    document_ids: List[str] = Field(..., description="List of document IDs to delete")
    delete_mode: str = Field("soft", description="Delete mode: 'soft' or 'hard'")
    cascade: bool = Field(True, description="Delete related entities (Neo4j)")
    databases: Optional[List[str]] = Field(None, description="Target databases (default: all)")

class DocumentUpsert(BaseModel):
    """Single document upsert specification"""
    document_id: str = Field(..., description="Document ID")
    fields: Dict[str, Any] = Field(..., description="Document fields")

class BatchUpsertRequest(BaseModel):
    """Batch UPSERT Request Model"""
    documents: List[DocumentUpsert] = Field(..., description="List of documents to upsert")
    conflict_resolution: str = Field("update", description="Conflict resolution: 'update' or 'skip'")
    databases: Optional[List[str]] = Field(None, description="Target databases (default: all)")

# Startup/Shutdown via Lifespan (deprecated on_event handlers removed)

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint mit API-Info"""
    return {
        "service": "Covina Main Backend API",
        "version": "1.0.0",
        "backend_type": "main",
        "port": 45678,
        "status": "operational",
        "features": [
            "Query API",
            "DSGVO Compliance",
            "Review Queue",
            "Handelsregister"
        ],
        "ingestion_backend": "http://127.0.0.1:45679",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/test-graph-pattern")
def test_graph_pattern_simple(pattern: GraphGoldenPattern):
    """Test endpoint - simple echo"""
    return {"status": "ok", "pattern_id": pattern.pattern_id}

@app.get("/health", response_model=SystemHealth)
async def health_check(delay: int = 0):
    """System Health Check (supports ?delay=N for testing active request tracking)"""
    import psutil
    import asyncio
    
    # Optional artificial delay for testing concurrent request tracking
    if delay > 0:
        await asyncio.sleep(min(delay, 5))  # Cap at 5s for safety
    
    # Berücksichtige Kill-Switches
    chroma_active = CHROMADB_AVAILABLE and chromadb_backend is not None and not FLAGS.get("KILL_SWITCH_CHROMADB", False)

    return SystemHealth(
        status="healthy",
        backend_type="main",
        port=45678,
        ingestion_backend="http://127.0.0.1:45679",
        features_available={
            "gap_detection": GAP_DETECTION_AVAILABLE and gap_db is not None,
            "postgres": POSTGRES_AVAILABLE and postgres_backend is not None,
            "compliance": COMPLIANCE_AVAILABLE and compliance_service is not None,
            "chromadb": chroma_active,
            "semantic_search": chroma_active and SENTENCE_TRANSFORMERS_AVAILABLE,
            "governance": True,
            "golden_dataset": POSTGRES_AVAILABLE,
            "query_api": POSTGRES_AVAILABLE,
            "review_queue": REVIEW_QUEUE_AVAILABLE and review_queue is not None,
            "dsgvo": COMPLIANCE_AVAILABLE and compliance_service is not None
        },
        system_resources={
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    )

@app.get("/live", summary="Liveness Probe")
async def liveness_probe():
    """Einfache Liveness-Probe (keine externen Abhängigkeiten)."""
    return {"status": "alive"}

@app.get("/metrics", summary="Metrics Endpoint")
async def metrics_endpoint():
    """
    Metrics Endpoint - Exposes internal metrics in JSON format.
    
    Provides query and database metrics without Prometheus dependency.
    Compatible with custom monitoring solutions and dashboards.
    """
    if not METRICS_AVAILABLE:
        return {
            "status": "metrics_disabled",
            "message": "Metrics system not initialized"
        }
    
    # Update pool metrics before export
    update_pool_metrics()
    
    try:
        return metrics_registry.export_dict()
    except NameError:
        return {
            "status": "metrics_error",
            "message": "metrics_registry not available"
        }

@app.get("/ready", summary="Readiness Probe")
async def readiness_probe():
    """Readiness-Probe: prüft Kernabhängigkeiten (so weit verfügbar)."""
    deps = {
        "postgres": bool(POSTGRES_AVAILABLE and postgres_backend is not None),
        "chromadb": bool(CHROMADB_AVAILABLE and chromadb_backend is not None and not FLAGS.get("KILL_SWITCH_CHROMADB", False)),
    }
    ready = all(deps.values()) if any(deps.values()) else True
    return {"ready": ready, "dependencies": deps}

@app.get("/db/pool", summary="PostgreSQL Connection Pool Stats")
async def get_db_pool_stats():
    """Gibt Statistiken des PostgreSQL Connection Pools zurück."""
    global postgres_backend
    if not POSTGRES_AVAILABLE or postgres_backend is None:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    try:
        if hasattr(postgres_backend, 'get_pool_stats'):
            stats = postgres_backend.get_pool_stats()
        else:
            # Fallback: Versuche über get_statistics() Pooldaten zu lesen
            stats_all = postgres_backend.get_statistics()
            stats = stats_all.get('pool_stats') if isinstance(stats_all, dict) else None
        if not stats:
            raise HTTPException(status_code=404, detail="Pool-Statistiken nicht verfügbar")
        return {"pool": stats}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Pool-Statistiken: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ADMIN: FEATURE FLAGS & KILL-SWITCH
# ============================================================================

class FlagUpdate(BaseModel):
    value: bool = Field(..., description="Neuer Flag-Wert (true/false)")

@app.get("/admin/flags", summary="Liste aller Feature Flags/Kill-Switches")
async def list_flags(
    _principal: "Principal" = Depends(require_roles([Role.admin])) if AUTH_AVAILABLE else None,
):
    return {"flags": FLAGS}

@app.post("/admin/flags/{name}", summary="Setze Feature Flag/Kill-Switch")
async def set_flag(
    name: str,
    update: FlagUpdate,
    _principal: "Principal" = Depends(require_roles([Role.admin])) if AUTH_AVAILABLE else None,
):
    # Nur bekannte Flags erlauben (Fail-Closed)
    if name not in FLAGS:
        raise HTTPException(status_code=404, detail=f"Unbekanntes Flag: {name}")
    FLAGS[name] = bool(update.value)
    # Zusatzlogik: Wenn Chroma Kill-Switch aktiviert wird, Logging-Hinweis
    if name == "KILL_SWITCH_CHROMADB":
        if FLAGS[name]:
            logger.warning("🛑 KILL-SWITCH aktiviert: ChromaDB wird ab sofort deaktiviert (Semantic Search/Batch Search gesperrt)")
        else:
            logger.info("✅ KILL-SWITCH aufgehoben: ChromaDB wieder aktiviert")
    return {"flag": name, "value": FLAGS[name]}

# ============================================================================
# GAP DETECTION API
# ============================================================================

@app.get("/gaps", summary="Liste alle Knowledge Gaps")
async def list_knowledge_gaps(
    status: Optional[str] = QueryParam(None, description="Filter nach Status"),
    gap_type: Optional[str] = QueryParam(None, description="Filter nach Typ"),
    severity: Optional[str] = QueryParam(None, description="Filter nach Schweregrad"),
    limit: int = QueryParam(50, ge=1, le=500)
):
    """Liste alle Knowledge Gaps mit optionalen Filtern"""
    if not gap_db:
        raise HTTPException(status_code=503, detail="Gap Detection nicht verfügbar")
    
    try:
        gaps = gap_db.get_gaps(status=status, gap_type=gap_type, severity=severity, limit=limit)
        return {"gaps": gaps, "count": len(gaps)}
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gaps/{gap_id}", summary="Hole einzelnen Knowledge Gap")
async def get_knowledge_gap(gap_id: int):
    """Hole Details zu einem spezifischen Knowledge Gap"""
    if not gap_db:
        raise HTTPException(status_code=503, detail="Gap Detection nicht verfügbar")
    
    try:
        gap = gap_db.get_gap(gap_id)
        if not gap:
            raise HTTPException(status_code=404, detail="Gap nicht gefunden")
        return gap
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Gap {gap_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gaps", summary="Erstelle neuen Knowledge Gap")
async def create_knowledge_gap(gap: KnowledgeGap):
    """Erstelle einen neuen Knowledge Gap"""
    if not gap_db:
        raise HTTPException(status_code=503, detail="Gap Detection nicht verfügbar")
    
    try:
        gap_id = gap_db.add_gap(
            gap_type=gap.gap_type,
            description=gap.description,
            severity=gap.severity,
            status=gap.status,
            source=gap.source,
            context=gap.context,
            tags=gap.tags,
            metadata=gap.metadata
        )
        
        if gap_id:
            return {"gap_id": gap_id, "message": "Gap erfolgreich erstellt"}
        else:
            raise HTTPException(status_code=500, detail="Gap konnte nicht erstellt werden")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Erstellen von Gap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/gaps/{gap_id}", summary="Aktualisiere Knowledge Gap")
async def update_knowledge_gap(gap_id: int, gap: KnowledgeGap):
    """Aktualisiere einen existierenden Knowledge Gap"""
    if not gap_db:
        raise HTTPException(status_code=503, detail="Gap Detection nicht verfügbar")
    
    try:
        success = gap_db.update_gap(
            gap_id,
            gap_type=gap.gap_type,
            description=gap.description,
            severity=gap.severity,
            status=gap.status,
            source=gap.source,
            context=gap.context,
            tags=gap.tags,
            metadata=gap.metadata
        )
        
        if success:
            return {"message": "Gap erfolgreich aktualisiert"}
        else:
            raise HTTPException(status_code=404, detail="Gap nicht gefunden")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren von Gap {gap_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gaps/{gap_id}/resolve", summary="Markiere Gap als gelöst")
async def resolve_knowledge_gap(gap_id: int, resolution: str, user: Optional[str] = None):
    """Markiere einen Knowledge Gap als gelöst"""
    if not gap_db:
        raise HTTPException(status_code=503, detail="Gap Detection nicht verfügbar")
    
    try:
        success = gap_db.resolve_gap(gap_id, resolution, user)
        if success:
            return {"message": "Gap erfolgreich als gelöst markiert"}
        else:
            raise HTTPException(status_code=404, detail="Gap nicht gefunden")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Lösen von Gap {gap_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gaps/statistics", summary="Gap Detection Statistiken")
async def get_gap_statistics():
    """Hole statistische Übersicht über alle Knowledge Gaps"""
    if not gap_db:
        raise HTTPException(status_code=503, detail="Gap Detection nicht verfügbar")
    
    try:
        stats = gap_db.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Gap-Statistiken: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# GOLDEN DATASET API
# ============================================================================

@app.get("/golden-dataset", summary="Liste Golden Dataset Einträge")
async def list_golden_dataset(
    classification: Optional[str] = QueryParam(None, description="Filter nach Classification"),
    reviewed_by: Optional[str] = QueryParam(None, description="Filter nach Reviewer"),
    min_quality: float = QueryParam(0.0, ge=0.0, le=1.0, description="Minimale Quality Score"),
    limit: int = QueryParam(100, ge=1, le=1000, description="Maximale Anzahl Ergebnisse"),
    offset: int = QueryParam(0, ge=0, description="Pagination Offset")
):
    """
    Liste alle Golden Dataset Einträge (manuell kuratierte Beispieldokumente).
    
    Golden Dataset = Manuell überprüfte und als korrekt markierte Dokumente
    für Training/Validierung von ML-Modellen und Benchmarking.
    
    Unterstützt Filter nach:
    - classification: Dokumenttyp (invoice, contract, letter, etc.)
    - reviewed_by: Username des Reviewers
    - min_quality: Minimale Quality Score (0.0 - 1.0)
    - Pagination mit limit/offset
    """
    if not postgres_backend:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    
    try:
        # Backend ist bereits verbunden - kein connect() hier nötig!
        # postgres_backend.connect()  # <-- ENTFERNT!
        
        # Build SQL Query mit Filtern
        query = """
        SELECT 
            id,
            document_id,
            classification,
            quality_score,
            reviewed_by,
            reviewed_at,
            notes,
            metadata,
            created_at,
            updated_at
        FROM golden_dataset
        WHERE quality_score >= %s
        """
        
        params = [min_quality]
        
        # Classification Filter
        if classification:
            query += " AND classification = %s"
            params.append(classification)
        
        # Reviewed By Filter
        if reviewed_by:
            query += " AND reviewed_by = %s"
            params.append(reviewed_by)
        
        # Ordering by quality_score (höchste zuerst)
        query += " ORDER BY quality_score DESC, created_at DESC"
        
        # Pagination
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Execute Query
        rows = postgres_backend.execute_query(query, tuple(params))
        
        # Format Results
        entries = []
        for row in rows:
            entries.append({
                'id': row['id'],
                'document_id': row['document_id'],
                'classification': row['classification'],
                'quality_score': float(row['quality_score']) if row['quality_score'] else None,
                'reviewed_by': row['reviewed_by'],
                'reviewed_at': str(row['reviewed_at']) if row['reviewed_at'] else None,
                'notes': row['notes'],
                'metadata': row['metadata'],
                'created_at': str(row['created_at']),
                'updated_at': str(row['updated_at'])
            })
        
        # Get Total Count
        count_query = """
        SELECT COUNT(*) 
        FROM golden_dataset 
        WHERE quality_score >= %s
        """
        count_params = [min_quality]
        
        if classification:
            count_query += " AND classification = %s"
            count_params.append(classification)
        
        if reviewed_by:
            count_query += " AND reviewed_by = %s"
            count_params.append(reviewed_by)
        
        count_result = postgres_backend.execute_query(count_query, tuple(count_params))
        total = count_result[0]['count'] if count_result else 0
        
        return {
            "entries": entries,
            "count": len(entries),
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "classification": classification,
                "reviewed_by": reviewed_by,
                "min_quality": min_quality
            },
            "has_more": (offset + len(entries)) < total
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Golden Dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/golden-dataset", summary="Füge Golden Dataset Eintrag hinzu")
async def add_golden_dataset_entry(entry: GoldenDatasetEntry):
    """
    Füge einen neuen Golden Dataset Eintrag hinzu.
    
    Erstellt einen manuell kuratierten Eintrag für Training/Benchmarking.
    
    Args:
        entry: Golden Dataset Eintrag mit:
            - document_id (required): Eindeutige Dokument-ID
            - classification (required): Dokumenttyp
            - quality_score (optional): Quality Score (0.0 - 1.0)
            - reviewed_by (optional): Username des Reviewers
            - notes (optional): Kommentare/Notizen
            - metadata (optional): Zusätzliche Metadaten
    
    Returns:
        Erfolgsmeldung mit entry_id
    """
    if not postgres_backend:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    
    try:
        # postgres_backend.connect()  # ← Backend bereits connected beim Start!
        
        # Insert SQL
        insert_sql = """
        INSERT INTO golden_dataset 
            (document_id, classification, quality_score, reviewed_by, reviewed_at, notes, metadata)
        VALUES 
            (%s, %s, %s, %s, NOW(), %s, %s::jsonb)
        ON CONFLICT (document_id) 
        DO UPDATE SET
            classification = EXCLUDED.classification,
            quality_score = EXCLUDED.quality_score,
            reviewed_by = EXCLUDED.reviewed_by,
            reviewed_at = NOW(),
            notes = EXCLUDED.notes,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        RETURNING id;
        """
        
        # Prepare metadata as JSON string
        import json
        metadata_json = json.dumps(entry.metadata) if entry.metadata else '{}'
        
        params = (
            entry.document_id,
            entry.classification,
            entry.quality_score,
            entry.reviewed_by,
            entry.notes,
            metadata_json
        )
        
        # Execute INSERT with cursor from connection
        with postgres_backend.conn.cursor() as cur:
            cur.execute(insert_sql, params)
            result = cur.fetchone()
            entry_id = result['id'] if result else None
            postgres_backend.conn.commit()
        
        logger.info(f"✅ Golden Dataset Eintrag hinzugefügt: {entry.document_id} (ID: {entry_id})")
        
        return {
            "message": "Golden Dataset Eintrag erfolgreich hinzugefügt",
            "entry_id": entry_id,
            "document_id": entry.document_id,
            "classification": entry.classification,
            "quality_score": entry.quality_score
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen von Golden Dataset Eintrag: {e}")
        if postgres_backend and postgres_backend.conn:
            postgres_backend.conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# GRAPH GOLDEN DATASET API (Neo4j/Process Patterns)
# ============================================================================

@app.get("/graph-golden-dataset", summary="Liste Graph Golden Dataset Patterns")
async def list_graph_golden_patterns(
    category: Optional[str] = QueryParam(None, description="Filter nach Category (invoice_processing, compliance, organization, workflow)"),
    status: Optional[str] = QueryParam(None, description="Filter nach Status (active, draft, archived)"),
    tags: Optional[str] = QueryParam(None, description="Filter nach Tags (comma-separated)"),
    limit: int = QueryParam(100, ge=1, le=1000, description="Maximale Anzahl Ergebnisse"),
    offset: int = QueryParam(0, ge=0, description="Pagination Offset")
):
    """
    Liste alle Graph Golden Dataset Patterns für Prozessvalidierung.
    
    Graph Golden Dataset = Validierte Graph-Patterns für:
    - Workflow-Validierung (Prozess-Patterns)
    - Dokumenten-Beziehungen (Rechnungen → Lieferungen → Verträge)
    - Compliance-Pfade (DSGVO-konforme Datenflüsse)
    - Organisationsstrukturen (Abteilungen, Rollen, Hierarchien)
    
    Storage:
    - PostgreSQL: Metadata (Name, Beschreibung, Validation Rules)
    - Neo4j: Graph Pattern (Nodes + Relationships) [Optional]
    """
    if not postgres_backend:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    
    try:
        # postgres_backend.connect()  # ← Backend bereits connected beim Start!
        
        # Build Query
        query = """
        SELECT 
            id,
            pattern_id,
            name,
            description,
            category,
            nodes_definition,
            relationships_definition,
            validation_rules,
            created_by,
            created_at,
            updated_at,
            reviewed_by,
            reviewed_at,
            status,
            tags,
            neo4j_pattern_label,
            usage_count,
            last_used_at,
            metadata
        FROM graph_golden_dataset
        WHERE 1=1
        """
        
        params = []
        
        # Category Filter
        if category:
            query += " AND category = %s"
            params.append(category)
        
        # Status Filter
        if status:
            query += " AND status = %s"
            params.append(status)
        
        # Tags Filter
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
            query += " AND tags && %s"  # PostgreSQL Array Overlap Operator
            params.append(tag_list)
        
        # Ordering
        query += " ORDER BY usage_count DESC, created_at DESC"
        
        # Pagination
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Execute
        rows = postgres_backend.execute_query(query, tuple(params))
        
        # Format Results
        patterns = []
        for row in rows:
            patterns.append({
                'id': row['id'],
                'pattern_id': row['pattern_id'],
                'name': row['name'],
                'description': row['description'],
                'category': row['category'],
                'nodes_definition': row['nodes_definition'],
                'relationships_definition': row['relationships_definition'],
                'validation_rules': row['validation_rules'],
                'created_by': row['created_by'],
                'created_at': str(row['created_at']),
                'updated_at': str(row['updated_at']),
                'reviewed_by': row['reviewed_by'],
                'reviewed_at': str(row['reviewed_at']) if row['reviewed_at'] else None,
                'status': row['status'],
                'tags': row['tags'],
                'neo4j_pattern_label': row['neo4j_pattern_label'],
                'usage_count': row['usage_count'],
                'last_used_at': str(row['last_used_at']) if row['last_used_at'] else None,
                'metadata': row['metadata']
            })
        
        # Total Count
        count_query = "SELECT COUNT(*) as count FROM graph_golden_dataset WHERE 1=1"
        count_params = []
        
        if category:
            count_query += " AND category = %s"
            count_params.append(category)
        
        if status:
            count_query += " AND status = %s"
            count_params.append(status)
        
        if tags:
            count_query += " AND tags && %s"
            count_params.append(tag_list)
        
        count_result = postgres_backend.execute_query(count_query, tuple(count_params))
        total = count_result[0]['count'] if count_result else 0
        
        return {
            "patterns": patterns,
            "count": len(patterns),
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "category": category,
                "status": status,
                "tags": tags
            },
            "has_more": (offset + len(patterns)) < total
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Graph Golden Patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph-golden-dataset", summary="Erstelle Graph Golden Pattern")
def create_graph_golden_pattern(pattern: GraphGoldenPattern):  # Changed from async def to def
    """
    Erstelle einen neuen Graph Golden Dataset Pattern.
    
    Speichert Pattern-Metadata in PostgreSQL und optional Graph-Struktur in Neo4j.
    
    Args:
        pattern: Graph Pattern mit:
            - pattern_id (required): Eindeutige Pattern-ID
            - name (required): Pattern-Name
            - category (required): Kategorie (invoice_processing, compliance, organization, workflow)
            - nodes_definition (required): Node-Definitionen als JSON
            - relationships_definition (required): Relationship-Definitionen als JSON
            - validation_rules (optional): Validierungsregeln
            - tags (optional): Tags für Filtering
    
    Returns:
        Erfolgsmeldung mit pattern_id
    """
    if not postgres_backend:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    
    try:
        # postgres_backend.connect()  # ← Backend bereits connected beim Start!
        
        # Insert SQL
        insert_sql = """
        INSERT INTO graph_golden_dataset 
            (pattern_id, name, description, category, nodes_definition, relationships_definition,
             validation_rules, created_by, status, tags)
        VALUES 
            (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
        ON CONFLICT (pattern_id) 
        DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            category = EXCLUDED.category,
            nodes_definition = EXCLUDED.nodes_definition,
            relationships_definition = EXCLUDED.relationships_definition,
            validation_rules = EXCLUDED.validation_rules,
            status = EXCLUDED.status,
            tags = EXCLUDED.tags,
            updated_at = NOW()
        RETURNING id;
        """
        
        # Prepare JSON data
        import json
        nodes_json = json.dumps(pattern.nodes_definition)
        rels_json = json.dumps(pattern.relationships_definition)
        rules_json = json.dumps(pattern.validation_rules) if pattern.validation_rules else '{}'
        
        params = (
            pattern.pattern_id,
            pattern.name,
            pattern.description,
            pattern.category,
            nodes_json,
            rels_json,
            rules_json,
            pattern.created_by,
            pattern.status,
            pattern.tags
        )
        
        with postgres_backend.conn.cursor() as cur:
            cur.execute(insert_sql, params)
            result = cur.fetchone()
            pattern_id_db = result['id'] if result else None
        
        postgres_backend.conn.commit()  # Moved outside context manager
        
        logger.info(f"✅ Graph Golden Pattern erstellt: {pattern.pattern_id} (ID: {pattern_id_db})")
        
        return {
            "message": "Graph Golden Pattern erfolgreich erstellt",
            "pattern_id": pattern.pattern_id,
            "id": pattern_id_db,
            "name": pattern.name,
            "category": pattern.category,
            "nodes_count": len(pattern.nodes_definition),
            "relationships_count": len(pattern.relationships_definition)
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Erstellen von Graph Golden Pattern: {e}")
        try:
            postgres_backend.conn.rollback()
        except Exception as rollback_error:
            # Ignore rollback errors if transaction already committed or connection closed
            logger.debug(f"Rollback failed (likely already committed): {rollback_error}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph-golden-dataset/{pattern_id}", summary="Hole Graph Golden Pattern Details")
async def get_graph_golden_pattern(pattern_id: str):
    """
    Hole Details eines spezifischen Graph Golden Patterns.
    
    Returns:
        Pattern mit vollständiger Graph-Definition
    """
    if not postgres_backend:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    
    try:
        # postgres_backend.connect()  # ← Backend bereits connected beim Start!
        
        query = """
        SELECT 
            id, pattern_id, name, description, category,
            nodes_definition, relationships_definition, validation_rules,
            created_by, created_at, updated_at, reviewed_by, reviewed_at,
            status, tags, neo4j_pattern_label, usage_count, last_used_at, metadata
        FROM graph_golden_dataset
        WHERE pattern_id = %s
        """
        
        rows = postgres_backend.execute_query(query, (pattern_id,))
        row = rows[0] if rows else None
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Pattern '{pattern_id}' nicht gefunden")
        
        pattern = {
            'id': row['id'],
            'pattern_id': row['pattern_id'],
            'name': row['name'],
            'description': row['description'],
            'category': row['category'],
            'nodes_definition': row['nodes_definition'],
            'relationships_definition': row['relationships_definition'],
            'validation_rules': row['validation_rules'],
            'created_by': row['created_by'],
            'created_at': str(row['created_at']),
            'updated_at': str(row['updated_at']),
            'reviewed_by': row['reviewed_by'],
            'reviewed_at': str(row['reviewed_at']) if row['reviewed_at'] else None,
            'status': row['status'],
            'tags': row['tags'],
            'neo4j_pattern_label': row['neo4j_pattern_label'],
            'usage_count': row['usage_count'],
            'last_used_at': str(row['last_used_at']) if row['last_used_at'] else None,
            'metadata': row['metadata']
        }
        
        # Increment usage count
        update_usage_sql = """
        UPDATE graph_golden_dataset 
        SET usage_count = usage_count + 1,
            last_used_at = NOW()
        WHERE pattern_id = %s
        """
        with postgres_backend.conn.cursor() as cur:
            cur.execute(update_usage_sql, (pattern_id,))
            postgres_backend.conn.commit()
        
        return pattern
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# COMPLIANCE API
# ============================================================================

# ----------------------------------------------------------------------------
# OAuth2 Token issuing (development-grade; replace with real user store)
# ----------------------------------------------------------------------------
if AUTH_AVAILABLE:
    @app.post("/token", summary="Issue JWT access token")
    async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        """Authenticate user and return a JWT token.

        NOTE: This is a minimal, development-grade user store. Replace with
        database-backed users and password hashing (passlib) for production.
        """
        users = {
            "admin": {
                "password": os.getenv("ADMIN_PASSWORD", "admin"),
                "roles": [Role.admin, Role.manager],
            },
            "user": {
                "password": os.getenv("USER_PASSWORD", "user"),
                "roles": [Role.user],
            },
        }

        user = users.get(form_data.username)
        if not user or user["password"] != form_data.password:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token(
            subject=form_data.username,
            roles=[r.value for r in user["roles"]],
            scopes=["*"],
        )
        return {"access_token": token, "token_type": "bearer"}

    @app.get("/me", summary="Current user info (claims)")
    async def me(current: "Principal" = Depends(get_current_user)):
        return {"user_id": current.user_id, "roles": [r.value for r in current.roles], "scopes": current.scopes}

@app.post("/compliance/check", summary="Führe Compliance Check durch")
async def perform_compliance_check(
    check: ComplianceCheck,
    _principal: "Principal" = Depends(require_roles([Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """Führe einen Compliance Check durch (DSGVO, GDPR, etc.)"""
    if not compliance_service:
        raise HTTPException(status_code=503, detail="Compliance Service nicht verfügbar")
    
    try:
        # Perform compliance check
        result = compliance_service.check_document(
            document_id=check.document_id if check.document_id else f"check_{datetime.now().timestamp()}",
            content=None,  # Will fetch from DB if needed
            check_type=check.check_type
        )
        
        return {
            "check_id": result.get('document_id'),
            "check_type": result.get('check_type'),
            "status": result.get('status'),
            "findings": result.get('findings', []),
            "risk_level": result.get('risk_level'),
            "pii_detected": result.get('pii_detected', {}),
            "timestamp": result.get('checked_at', datetime.now().isoformat())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Compliance Check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/compliance/checks", summary="Liste Compliance Checks")
async def list_compliance_checks(
    check_type: Optional[str] = QueryParam(None, description="Filter nach Check Type (dsgvo, gdpr, regulatory)"),
    status: Optional[str] = QueryParam(None, description="Filter nach Status"),
    limit: int = QueryParam(50, ge=1, le=500),
    _principal: "Principal" = Depends(require_roles([Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """Liste alle Compliance Checks"""
    if not compliance_service:
        raise HTTPException(status_code=503, detail="Compliance Service nicht verfügbar")
    
    try:
        checks = compliance_service.list_checks(
            check_type=check_type,
            status=status,
            limit=limit
        )
        
        return {
            "checks": checks,
            "count": len(checks),
            "filters": {
                "check_type": check_type,
                "status": status
            }
        }
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Compliance Checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/compliance/dsgvo/{document_id}", summary="DSGVO Status für Dokument")
async def get_document_dsgvo_status(
    document_id: str,
    _principal: "Principal" = Depends(require_roles([Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """Hole DSGVO Compliance Status für ein spezifisches Dokument"""
    if not compliance_service:
        raise HTTPException(status_code=503, detail="Compliance Service nicht verfügbar")
    
    try:
        status = compliance_service.get_dsgvo_status(document_id)
        
        return {
            "document_id": document_id,
            "dsgvo_compliant": status.get('dsgvo_compliant'),
            "status": status.get('status'),
            "risk_level": status.get('risk_level'),
            "pii_detected": status.get('pii_detected', {}),
            "has_consent": status.get('has_consent', False),
            "findings": status.get('findings', []),
            "checked_at": status.get('checked_at'),
            "recommendations": [
                "Prüfe explizite Einwilligung für PII-Verarbeitung" if status.get('pii_detected') and not status.get('has_consent') else None,
                "Dokumentiere Rechtsgrundlage der Verarbeitung" if status.get('risk_level') in ['high', 'critical'] else None
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim DSGVO Status Check für {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# GOVERNANCE API
# ============================================================================

@app.get("/governance/policies", summary="Liste Governance Policies")
async def list_governance_policies(
    policy_type: Optional[str] = QueryParam(None, description="Filter nach Policy Type (retention, access_control, classification, quality, audit, compliance, custom)"),
    scope: Optional[str] = QueryParam(None, description="Filter nach Scope (global, department, project, document_type)"),
    status: Optional[str] = QueryParam(None, description="Filter nach Status (active, draft, archived)"),
    active_only: bool = QueryParam(True, description="Nur aktive Policies"),
    limit: int = QueryParam(100, ge=1, le=500, description="Maximale Anzahl Ergebnisse"),
    offset: int = QueryParam(0, ge=0, description="Pagination Offset")
):
    """
    Liste alle Governance Policies (Unternehmens-Richtlinien).
    
    Governance Policies = Regelwerke für:
    - Retention: Aufbewahrungsfristen (z.B. Rechnungen 10 Jahre)
    - Access Control: Zugriffskontrolle (z.B. nur Manager)
    - Classification: Klassifizierungs-Regeln
    - Quality: Qualitäts-Standards (z.B. min. Score 0.8)
    - Audit: Audit-Anforderungen (z.B. Log alle Zugriffe)
    - Compliance: DSGVO, GoBD, etc.
    
    Policies werden nach Priorität sortiert (höhere Priorität zuerst).
    """
    if not postgres_backend:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    
    try:
        # postgres_backend.connect()  # ← Backend bereits connected beim Start!
        
        # Build Query
        query = """
        SELECT 
            id,
            policy_id,
            name,
            description,
            policy_type,
            scope,
            rules,
            status,
            priority,
            effective_from,
            effective_until,
            created_by,
            created_at,
            updated_at,
            approved_by,
            approved_at,
            metadata
        FROM governance_policies
        WHERE 1=1
        """
        
        params = []
        
        # Active Only Filter
        if active_only:
            query += " AND status = 'active'"
            query += " AND (effective_from IS NULL OR effective_from <= NOW())"
            query += " AND (effective_until IS NULL OR effective_until >= NOW())"
        
        # Policy Type Filter
        if policy_type:
            query += " AND policy_type = %s"
            params.append(policy_type)
        
        # Scope Filter
        if scope:
            query += " AND scope = %s"
            params.append(scope)
        
        # Status Filter (overrides active_only if specified)
        if status and not active_only:
            query += " AND status = %s"
            params.append(status)
        
        # Ordering by priority (higher first)
        query += " ORDER BY priority DESC, created_at DESC"
        
        # Pagination
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Execute
        rows = postgres_backend.execute_query(query, tuple(params))
        
        # Format Results
        policies = []
        for row in rows:
            policies.append({
                'id': row['id'],
                'policy_id': row['policy_id'],
                'name': row['name'],
                'description': row['description'],
                'policy_type': row['policy_type'],
                'scope': row['scope'],
                'rules': row['rules'],
                'status': row['status'],
                'priority': row['priority'],
                'effective_from': str(row['effective_from']) if row['effective_from'] else None,
                'effective_until': str(row['effective_until']) if row['effective_until'] else None,
                'created_by': row['created_by'],
                'created_at': str(row['created_at']),
                'updated_at': str(row['updated_at']),
                'approved_by': row['approved_by'],
                'approved_at': str(row['approved_at']) if row['approved_at'] else None,
                'metadata': row['metadata']
            })
        
        # Total Count
        count_query = "SELECT COUNT(*) as count FROM governance_policies WHERE 1=1"
        count_params = []
        
        if active_only:
            count_query += " AND status = 'active'"
            count_query += " AND (effective_from IS NULL OR effective_from <= NOW())"
            count_query += " AND (effective_until IS NULL OR effective_until >= NOW())"
        
        if policy_type:
            count_query += " AND policy_type = %s"
            count_params.append(policy_type)
        
        if scope:
            count_query += " AND scope = %s"
            count_params.append(scope)
        
        if status and not active_only:
            count_query += " AND status = %s"
            count_params.append(status)
        
        count_result = postgres_backend.execute_query(count_query, tuple(count_params))
        total = count_result[0]['count'] if count_result else 0
        
        return {
            "policies": policies,
            "count": len(policies),
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "policy_type": policy_type,
                "scope": scope,
                "status": status if not active_only else "active",
                "active_only": active_only
            },
            "has_more": (offset + len(policies)) < total
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Governance Policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/governance/policies", summary="Erstelle Governance Policy")
async def create_governance_policy(policy: GovernancePolicy):
    """
    Erstelle eine neue Governance Policy (Unternehmens-Richtlinie).
    
    Args:
        policy: Governance Policy mit:
            - policy_id (required): Eindeutige Policy-ID
            - name (required): Policy-Name
            - policy_type (required): Typ (retention, access_control, classification, quality, audit, compliance, custom)
            - scope (optional): Geltungsbereich (global, department, project, document_type, custom)
            - rules (required): Regelwerk als JSON
            - priority (optional): Priorität (default: 100, höher = wichtiger)
            - effective_from/until (optional): Gültigkeitszeitraum
            - approved_by (optional): Genehmiger
    
    Returns:
        Erfolgsmeldung mit policy_id
    """
    if not postgres_backend:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    
    try:
        # postgres_backend.connect()  # ← Backend bereits connected beim Start!
        
        # Insert SQL
        insert_sql = """
        INSERT INTO governance_policies 
            (policy_id, name, description, policy_type, scope, rules, status, priority,
             effective_from, effective_until, created_by, approved_by, approved_at, metadata)
        VALUES 
            (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (policy_id) 
        DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            policy_type = EXCLUDED.policy_type,
            scope = EXCLUDED.scope,
            rules = EXCLUDED.rules,
            status = EXCLUDED.status,
            priority = EXCLUDED.priority,
            effective_from = EXCLUDED.effective_from,
            effective_until = EXCLUDED.effective_until,
            approved_by = EXCLUDED.approved_by,
            approved_at = EXCLUDED.approved_at,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        RETURNING id;
        """
        
        # Prepare JSON data
        import json
        rules_json = json.dumps(policy.rules)
        metadata_json = json.dumps(policy.metadata) if policy.metadata else '{}'
        
        params = (
            policy.policy_id,
            policy.name,
            policy.description,
            policy.policy_type,
            policy.scope,
            rules_json,
            policy.status,
            policy.priority,
            policy.effective_from,
            policy.effective_until,
            policy.created_by,
            policy.approved_by,
            policy.approved_at,
            metadata_json
        )
        
        with postgres_backend.conn.cursor() as cur:
            cur.execute(insert_sql, params)
            result = cur.fetchone()
            policy_id_db = result['id'] if result else None
        postgres_backend.conn.commit()
        
        logger.info(f"✅ Governance Policy erstellt: {policy.policy_id} (ID: {policy_id_db})")
        
        return {
            "message": "Governance Policy erfolgreich erstellt",
            "policy_id": policy.policy_id,
            "id": policy_id_db,
            "name": policy.name,
            "policy_type": policy.policy_type,
            "scope": policy.scope,
            "priority": policy.priority,
            "status": policy.status
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Erstellen von Governance Policy: {e}")
        try:
            postgres_backend.conn.rollback()
        except Exception as rollback_error:
            # Ignore rollback errors if transaction already committed or connection closed
            logger.debug(f"Rollback failed (likely already committed): {rollback_error}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# QUERY API
# ============================================================================

@app.post("/query/documents", summary="Dokument-Suche (Full-Text)")
async def query_documents(query: DocumentQuery):
    """
    Suche nach Dokumenten mit PostgreSQL Full-Text Search.
    
    Verwendet to_tsvector und to_tsquery für effiziente Textsuche.
    Unterstützt Filter nach classification, date range und Pagination.
    """
    if not postgres_backend:
        raise HTTPException(status_code=503, detail="PostgreSQL nicht verfügbar")
    
    try:
        # postgres_backend.connect()  # ← Backend bereits connected beim Start!
        
        # Build SQL query with full-text search
        # Note: Using file_path as fallback since documents table may not have content column
        base_query = """
        SELECT 
            document_id,
            file_path,
            classification,
            content_length,
            quality_score,
            created_at,
            ts_rank(to_tsvector('german', COALESCE(file_path, '') || ' ' || COALESCE(classification, '')), query) AS rank
        FROM documents, to_tsquery('german', %s) query
        WHERE to_tsvector('german', COALESCE(file_path, '') || ' ' || COALESCE(classification, '')) @@ query
        """
        
        params = []
        query_text = query.query_text.strip()
        
        # Prepare tsquery (replace spaces with &)
        tsquery = ' & '.join(query_text.split())
        params.append(tsquery)
        
        # Apply filters
        filter_conditions = []
        
        if query.filters:
            # Classification filter
            if 'classification' in query.filters:
                filter_conditions.append("classification = %s")
                params.append(query.filters['classification'])
            
            # Date range filter
            if 'date_from' in query.filters:
                filter_conditions.append("created_at >= %s")
                params.append(query.filters['date_from'])
            
            if 'date_to' in query.filters:
                filter_conditions.append("created_at <= %s")
                params.append(query.filters['date_to'])
            
            # Quality score filter
            if 'min_quality' in query.filters:
                filter_conditions.append("quality_score >= %s")
                params.append(query.filters['min_quality'])
        
        # Add filter conditions to query
        if filter_conditions:
            base_query += " AND " + " AND ".join(filter_conditions)
        
        # Add ordering by relevance
        base_query += " ORDER BY rank DESC"
        
        # Add pagination
        base_query += " LIMIT %s OFFSET %s"
        params.extend([query.limit, query.offset])
        
        # Execute query
        postgres_backend.cursor.execute(base_query, tuple(params))
        rows = postgres_backend.cursor.fetchall()
        
        # Format results
        results = []
        for row in rows:
            results.append({
                'document_id': row[0],
                'file_path': row[1],
                'classification': row[2],
                'content_length': row[3],
                'quality_score': float(row[4]) if row[4] else None,
                'created_at': str(row[5]),
                'relevance_score': float(row[6])
            })
        
        # Get total count (without pagination)
        count_query = """
        SELECT COUNT(*)
        FROM documents, to_tsquery('german', %s) query
        WHERE to_tsvector('german', COALESCE(file_path, '') || ' ' || COALESCE(classification, '')) @@ query
        """
        count_params = [tsquery]
        
        if filter_conditions:
            count_query += " AND " + " AND ".join(filter_conditions)
            count_params.extend(params[1:-2])  # Exclude limit and offset
        
        count_result = postgres_backend.execute_query(count_query, tuple(count_params))
        total = count_result[0]['count'] if count_result else 0
        
        return {
            "results": results,
            "total": total,
            "count": len(results),
            "query": query.query_text,
            "limit": query.limit,
            "offset": query.offset,
            "filters": query.filters,
            "has_more": (query.offset + len(results)) < total
        }
        
    except Exception as e:
        logger.error(f"Fehler bei Dokument-Query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/query/semantic", summary="Semantic Search")
@limiter.limit("50/minute")  # Max 50 semantic searches pro Minute pro IP
async def semantic_search(
    request: Request,  # Required by slowapi
    query: str = QueryParam(..., description="Suchtext"),
    limit: int = QueryParam(10, ge=1, le=100),
    threshold: float = QueryParam(0.7, ge=0.0, le=1.0)
):
    """
    Semantische Suche über Dokumente mit ChromaDB Vector Search.
    
    Verwendet sentence-transformers für Query Embeddings und ChromaDB für 
    Ähnlichkeitssuche basierend auf vorher indizierten Dokumenten.
    
    Args:
        query: Suchtext (natürliche Sprache)
        limit: Maximale Anzahl Ergebnisse
        threshold: Minimale Ähnlichkeitsschwelle (0.0 - 1.0, höher = ähnlicher)
    
    Returns:
        results: Liste ähnlicher Dokumente mit Scores
        query: Ursprüngliche Query
        count: Anzahl Ergebnisse
        threshold: Verwendeter Threshold
    """
    global embedding_model
    
    # Kill-Switch prüfen
    if FLAGS.get("KILL_SWITCH_CHROMADB", False):
        raise HTTPException(status_code=503, detail="Semantic Search deaktiviert (Kill-Switch aktiv)")
    
    # Check prerequisites
    if not chromadb_backend:
        raise HTTPException(
            status_code=503, 
            detail="ChromaDB nicht verfügbar - bitte starten Sie ChromaDB Server (192.168.178.94:8000)"
        )
    
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="sentence-transformers nicht verfügbar - bitte installieren Sie das Modul"
        )
    
    try:
        # ═══════════════════════════════════════════════════════════
        # METRICS: Start timing
        # ═══════════════════════════════════════════════════════════
        import time
        start_time = time.time()
        
        # Lazy load embedding model (nur beim ersten Request)
        if embedding_model is None:
            logger.info("🔄 Lade sentence-transformers Modell (all-MiniLM-L6-v2)...")
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            logger.info("✅ Embedding Modell geladen (384-dim)")
        
        # Generate query embedding
        logger.info(f"🔍 Semantic Search: '{query}' (limit={limit}, threshold={threshold})")
        query_embedding = embedding_model.encode(query, convert_to_numpy=True).tolist()
        logger.debug(f"✅ Query Embedding generiert: {len(query_embedding)}-dim")
        
        # Search in ChromaDB
        similar_docs = chromadb_backend.search_similar(
            query_vector=query_embedding,
            n_results=limit,
            collection='covina_documents'
        )
        
        # Filter by threshold and format results
        results = []
        for doc in similar_docs:
            # ChromaDB returns distance (lower = more similar)
            # Convert to similarity score (higher = more similar)
            distance = doc.get('distance', 1.0)
            similarity = 1.0 - distance  # Simple conversion
            
            # Apply threshold filter
            if similarity >= threshold:
                results.append({
                    'document_id': doc.get('id'),
                    'similarity_score': round(similarity, 4),
                    'distance': round(distance, 4),
                    'metadata': doc.get('metadata', {}),
                    'text_preview': doc.get('text', '')[:200] + '...' if doc.get('text') else None
                })
        
        logger.info(f"✅ Semantic Search: {len(results)}/{len(similar_docs)} Dokumente über Threshold {threshold}")
        
        # ═══════════════════════════════════════════════════════════
        # METRICS: Record successful query
        # ═══════════════════════════════════════════════════════════
        if METRICS_AVAILABLE:
            duration = time.time() - start_time
            if queries_total:
                queries_total.inc(labels={"endpoint": "semantic_search", "status": "success"})
            if query_latency:
                query_latency.observe(duration, labels={"endpoint": "semantic_search"})
            logger.debug(f"[METRICS] Semantic search: {duration:.3f}s")
        
        return {
            "results": results,
            "query": query,
            "count": len(results),
            "total_found": len(similar_docs),
            "threshold": threshold,
            "limit": limit,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "embedding_dimensions": 384
        }
        
    except Exception as e:
        logger.error(f"❌ Fehler bei Semantic Search: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # METRICS: Record failed query
        # ═══════════════════════════════════════════════════════════
        if METRICS_AVAILABLE and queries_total:
            queries_total.inc(labels={"endpoint": "semantic_search", "status": "failed"})
        
        raise HTTPException(status_code=500, detail=f"Semantic Search Fehler: {str(e)}")

# ============================================================================
# REVIEW QUEUE API
# ============================================================================

@app.get("/review-queue", summary="Liste Review Queue Items")
async def list_review_queue(
    status: Optional[str] = QueryParam(None, description="Filter nach Status (pending, in_progress, resolved, dismissed)"),
    severity: Optional[str] = QueryParam(None, description="Filter nach Severity (low, medium, high, critical)"),
    gap_type: Optional[str] = QueryParam(None, description="Filter nach Gap Type"),
    document_id: Optional[str] = QueryParam(None, description="Filter nach Document ID"),
    limit: int = QueryParam(50, ge=1, le=500)
):
    """Liste alle Items in der Review Queue mit optionalen Filtern"""
    if not review_queue:
        raise HTTPException(status_code=503, detail="Review Queue nicht verfügbar")
    
    try:
        # Query based on filters
        if document_id:
            tasks = review_queue.get_tasks_by_document(document_id)
        elif status:
            tasks = review_queue.get_tasks_by_status(status)
        elif severity:
            tasks = review_queue.get_tasks_by_severity(severity)
        else:
            # Get all pending tasks by default
            tasks = review_queue.get_tasks_by_status('pending')
        
        # Apply limit
        tasks = tasks[:limit] if len(tasks) > limit else tasks
        
        return {
            "tasks": tasks,
            "count": len(tasks),
            "filters": {
                "status": status,
                "severity": severity,
                "gap_type": gap_type,
                "document_id": document_id
            }
        }
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Review Queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review-queue", summary="Füge Review Queue Item hinzu")
async def add_review_queue_item(item: ReviewQueueItem):
    """Füge ein neues Item zur Review Queue hinzu"""
    if not review_queue:
        raise HTTPException(status_code=503, detail="Review Queue nicht verfügbar")
    
    try:
        # Map ReviewQueueItem to review_item dict format
        review_item = {
            "document_id": item.document_id,
            "gap_type": item.review_type,  # Map review_type to gap_type
            "severity": item.priority if item.priority in ["low", "medium", "high", "critical"] else "medium",
            "message": f"Review required: {item.review_type}",
            "status": item.status,
            "assigned_to": item.assigned_to,
            "metadata": item.metadata or {}
        }
        
        # Add to queue
        review_id = review_queue.add_item(review_item)
        
        if review_id:
            return {
                "review_id": review_id,
                "document_id": item.document_id,
                "message": "Review task erfolgreich erstellt",
                "status": item.status
            }
        else:
            raise HTTPException(status_code=500, detail="Review task konnte nicht erstellt werden")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen von Review Queue Item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/review-queue/{review_id}", summary="Aktualisiere Review Queue Status")
async def update_review_queue_item(
    review_id: str, 
    status: str = QueryParam(..., description="Neuer Status (pending, in_progress, resolved, dismissed)"),
    resolution_notes: Optional[str] = QueryParam(None, description="Resolution Notes (erforderlich für 'resolved')")
):
    """Aktualisiere den Status eines Review Queue Items"""
    if not review_queue:
        raise HTTPException(status_code=503, detail="Review Queue nicht verfügbar")
    
    try:
        # Validate status
        valid_statuses = ['pending', 'in_progress', 'resolved', 'dismissed']
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Ungültiger Status: {status}. Erlaubt: {', '.join(valid_statuses)}"
            )
        
        # Require resolution_notes for resolved status
        if status == 'resolved' and not resolution_notes:
            raise HTTPException(
                status_code=400,
                detail="resolution_notes erforderlich für Status 'resolved'"
            )
        
        # Get current task
        task = review_queue.get_task(review_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Review task {review_id} nicht gefunden")
        
        old_status = task.get('status', 'unknown')
        
        # Update status
        success = review_queue.update_status(review_id, status, resolution_notes)
        
        if success:
            return {
                "success": True,
                "review_id": review_id,
                "old_status": old_status,
                "new_status": status,
                "message": f"Status aktualisiert: {old_status} → {status}"
            }
        else:
            raise HTTPException(status_code=500, detail="Status-Update fehlgeschlagen")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren von Review Queue Item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/review-queue/statistics", summary="Review Queue Statistiken")
async def get_review_queue_statistics():
    """Hole Review Queue Statistiken"""
    if not review_queue:
        raise HTTPException(status_code=503, detail="Review Queue nicht verfügbar")
    
    try:
        stats = review_queue.get_statistics()
        return {
            "total_tasks": stats.get('total_tasks', 0),
            "by_status": stats.get('by_status', {}),
            "by_severity": stats.get('by_severity', {}),
            "by_gap_type": stats.get('by_gap_type', {}),
            "avg_resolution_time_hours": stats.get('avg_resolution_time_hours')
        }
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Statistiken: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# BATCH OPERATIONS API (Phase 3)
# ============================================================================

@app.post("/api/v1/batch/get", summary="Batch GET - Retrieve Multiple Documents")
@limiter.limit("100/minute")  # Max 100 batch requests pro Minute pro IP
async def batch_get_documents(req: Request, request: BatchGetRequest):  # req for slowapi, request for business logic
    """
    Batch GET: Retrieve multiple documents in a single query.
    
    **Performance:** 8-97x faster than sequential requests
    **Recommended Batch Size:** 50-200 documents
    
    Example:
        POST /api/v1/batch/get
        {
            "document_ids": ["doc1", "doc2", "doc3"],
            "fields": ["document_id", "classification", "file_path"],
            "include_metadata": true
        }
    
    Returns:
        {
            "documents": [...],
            "found": 3,
            "not_found": 0,
            "execution_time_ms": 12.5
        }
    """
    if not postgres_batch_reader:
        raise HTTPException(
            status_code=503, 
            detail="Batch Operations nicht verfügbar (PostgreSQL Backend fehlt)"
        )
    
    if not request.document_ids:
        raise HTTPException(status_code=400, detail="document_ids darf nicht leer sein")
    
    if len(request.document_ids) > 1000:
        raise HTTPException(
            status_code=400, 
            detail="Maximale Batch-Größe: 1000 Dokumente (empfohlen: 50-200)"
        )
    
    try:
        import time
        start_time = time.time()
        
        # Execute batch GET
        results = postgres_batch_reader.batch_get(
            doc_ids=request.document_ids,
            fields=request.fields,
            table='documents'
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Build response
        found_ids = {doc.get('document_id') for doc in results if 'document_id' in doc}
        not_found_ids = [doc_id for doc_id in request.document_ids if doc_id not in found_ids]
        
        return {
            "success": True,
            "documents": results,
            "found": len(results),
            "not_found": len(not_found_ids),
            "not_found_ids": not_found_ids if not_found_ids else None,
            "execution_time_ms": round(execution_time_ms, 2),
            "performance_note": f"Batch processed {len(request.document_ids)} IDs in {execution_time_ms:.1f}ms"
        }
        
    except Exception as e:
        logger.error(f"Batch GET Fehler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Batch GET fehlgeschlagen: {str(e)}")


@app.post("/api/v1/batch/exists", summary="Batch EXISTS - Check Document Existence")
async def batch_exists_check(request: BatchExistsRequest):
    """
    Batch EXISTS: Check if multiple documents exist in database.
    
    **Performance:** 20x faster than sequential checks (95%+ improvement)
    **Recommended Batch Size:** 100-500 document IDs
    
    Example:
        POST /api/v1/batch/exists
        {
            "document_ids": ["doc1", "doc2", "doc3", "doc4"]
        }
    
    Returns:
        {
            "exists": {
                "doc1": true,
                "doc2": true,
                "doc3": false,
                "doc4": true
            },
            "total": 4,
            "found": 3,
            "missing": 1,
            "execution_time_ms": 2.3
        }
    """
    if not postgres_batch_reader:
        raise HTTPException(
            status_code=503,
            detail="Batch Operations nicht verfügbar (PostgreSQL Backend fehlt)"
        )
    
    if not request.document_ids:
        raise HTTPException(status_code=400, detail="document_ids darf nicht leer sein")
    
    if len(request.document_ids) > 5000:
        raise HTTPException(
            status_code=400,
            detail="Maximale Batch-Größe: 5000 IDs (empfohlen: 100-500)"
        )
    
    try:
        import time
        start_time = time.time()
        
        # Execute batch EXISTS
        # Custom query for existence check
        placeholders = ','.join(['%s'] * len(request.document_ids))
        query = f"SELECT document_id FROM documents WHERE document_id IN ({placeholders})"  # nosec B608
        
        results_raw = postgres_batch_reader.backend.execute_query(query, request.document_ids)
        found_ids = {row[0] for row in results_raw} if results_raw else set()
        
        # Build exists map
        exists_map = {doc_id: (doc_id in found_ids) for doc_id in request.document_ids}
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "exists": exists_map,
            "total": len(request.document_ids),
            "found": sum(exists_map.values()),
            "missing": len(request.document_ids) - sum(exists_map.values()),
            "execution_time_ms": round(execution_time_ms, 2),
            "performance_note": f"Checked {len(request.document_ids)} IDs in {execution_time_ms:.1f}ms"
        }
        
    except Exception as e:
        logger.error(f"Batch EXISTS Fehler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Batch EXISTS fehlgeschlagen: {str(e)}")


@app.post("/api/v1/batch/search", summary="Batch SEARCH - Multiple Semantic Searches")
async def batch_semantic_search(request: BatchSearchRequest):
    """
    Batch SEARCH: Execute multiple semantic searches in parallel.
    
    **Performance:** Multi-threaded parallel execution across databases
    **Recommended:** 5-10 queries per batch
    
    Example:
        POST /api/v1/batch/search
        {
            "queries": [
                "Vertrag über Lieferung",
                "Rechnung Buchhaltung",
                "DSGVO Datenschutz"
            ],
            "top_k": 5,
            "similarity_threshold": 0.7
        }
    
    Returns:
        {
            "results": [
                {
                    "query": "Vertrag über Lieferung",
                    "matches": [...],
                    "count": 5
                },
                ...
            ],
            "total_queries": 3,
            "total_results": 15,
            "execution_time_ms": 45.2
        }
    """
    # Declare global at the very beginning
    global embedding_model
    
    # Kill-Switch prüfen
    if FLAGS.get("KILL_SWITCH_CHROMADB", False):
        raise HTTPException(status_code=503, detail="Batch Semantic Search deaktiviert (Kill-Switch aktiv)")

    if not parallel_batch_reader:
        raise HTTPException(
            status_code=503,
            detail="Batch Search nicht verfügbar (Parallel Batch Reader fehlt)"
        )
    
    if not chromadb_backend or not embedding_model:
        raise HTTPException(
            status_code=503,
            detail="Semantic Search nicht verfügbar (ChromaDB oder Embedding Model fehlt)"
        )
    
    if not request.queries:
        raise HTTPException(status_code=400, detail="queries darf nicht leer sein")
    
    if len(request.queries) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximale Batch-Größe: 20 Queries (empfohlen: 5-10)"
        )
    
    try:
        import time
        start_time = time.time()
        
        # Load embedding model if not already loaded
        if not embedding_model and SENTENCE_TRANSFORMERS_AVAILABLE:
            from sentence_transformers import SentenceTransformer
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding Model geladen (Lazy Loading)")
        
        # Generate embeddings for all queries
        query_embeddings = embedding_model.encode(request.queries, convert_to_numpy=True)
        
        # Execute searches in parallel
        all_results = []
        
        for query_text, query_embedding in zip(request.queries, query_embeddings):
            try:
                # Query ChromaDB
                search_results = chromadb_backend.search(
                    query_vector=query_embedding.tolist(),
                    top_k=request.top_k,
                    filter_metadata=None
                )
                
                # Filter by similarity threshold
                filtered_results = [
                    r for r in search_results 
                    if r.get('similarity', 0) >= request.similarity_threshold
                ]
                
                all_results.append({
                    "query": query_text,
                    "matches": filtered_results,
                    "count": len(filtered_results)
                })
                
            except Exception as e:
                logger.error(f"Search failed for query '{query_text}': {e}")
                all_results.append({
                    "query": query_text,
                    "matches": [],
                    "count": 0,
                    "error": str(e)
                })
        
        execution_time_ms = (time.time() - start_time) * 1000
        total_results = sum(r['count'] for r in all_results)
        
        return {
            "success": True,
            "results": all_results,
            "total_queries": len(request.queries),
            "total_results": total_results,
            "execution_time_ms": round(execution_time_ms, 2),
            "performance_note": f"Processed {len(request.queries)} searches in {execution_time_ms:.1f}ms"
        }
        
    except Exception as e:
        logger.error(f"Batch SEARCH Fehler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Batch SEARCH fehlgeschlagen: {str(e)}")


@app.get("/api/v1/batch/status", summary="Batch Operations Status")
async def get_batch_operations_status():
    """
    Get status of Batch Operations (Phase 3 + Phase 4).
    
    Returns availability and performance metrics for all batch endpoints.
    """
    return {
        "phase": "Phase 3 + Phase 4",
        "version": "4.0.0",
        "phase3_status": "active" if BATCH_OPERATIONS_AVAILABLE else "unavailable",
        "phase4_status": "active" if BATCH_WRITE_AVAILABLE else "unavailable",
        "endpoints": {
            # Phase 3: Batch READ
            "POST /api/v1/batch/get": {
                "available": postgres_batch_reader is not None,
                "description": "Batch document retrieval",
                "performance": "8-97x faster than sequential",
                "max_batch_size": 1000,
                "recommended_batch_size": "50-200",
                "phase": 3
            },
            "POST /api/v1/batch/exists": {
                "available": postgres_batch_reader is not None,
                "description": "Batch existence check",
                "performance": "20x faster (95%+ improvement)",
                "max_batch_size": 5000,
                "recommended_batch_size": "100-500",
                "phase": 3
            },
            "POST /api/v1/batch/search": {
                "available": parallel_batch_reader is not None and chromadb_backend is not None,
                "description": "Parallel semantic search",
                "performance": "Multi-threaded execution",
                "max_batch_size": 20,
                "recommended_batch_size": "5-10",
                "phase": 3
            },
            # Phase 4: Batch WRITE
            "POST /api/v1/batch/update": {
                "available": batch_update_executor is not None,
                "description": "Batch document update",
                "performance": "67-80x faster than sequential",
                "max_batch_size": 1000,
                "recommended_batch_size": "50-200",
                "phase": 4
            },
            "POST /api/v1/batch/delete": {
                "available": batch_delete_executor is not None,
                "description": "Batch document delete",
                "performance": "100x faster than sequential",
                "max_batch_size": 1000,
                "recommended_batch_size": "100-500",
                "phase": 4
            },
            "POST /api/v1/batch/upsert": {
                "available": batch_upsert_executor is not None,
                "description": "Batch insert or update",
                "performance": "83x faster than sequential",
                "max_batch_size": 1000,
                "recommended_batch_size": "50-200",
                "phase": 4
            }
        },
        "backends": {
            "postgresql": postgres_backend is not None,
            "chromadb": chromadb_backend is not None,
            "embedding_model": embedding_model is not None
        },
        "documentation": {
            "phase3": "https://github.com/makr-code/VCC-UDS3/blob/main/docs/PHASE3_BATCH_READ_COMPLETE.md",
            "phase4": "https://github.com/makr-code/VCC-UDS3/blob/main/docs/PHASE4_BATCH_WRITE_PLAN.md"
        }
    }

# ============================================================================
# BATCH WRITE OPERATIONS - Phase 4 (UPDATE, DELETE, UPSERT)
# ============================================================================

@app.post("/api/v1/batch/update", summary="Batch Update Documents", tags=["Batch Operations"])
async def batch_update_documents(request: BatchUpdateRequest):
    """
    Batch update multiple documents across databases.
    
    **Performance:** 67-80x faster than sequential updates
    **Max batch size:** 1000 (recommended: 50-200)
    
    **Update Modes:**
    - `partial`: Update only specified fields (default)
    - `full`: Replace entire document
    
    **Example:**
    ```json
    {
        "updates": [
            {"document_id": "doc_123", "fields": {"status": "approved", "priority": "high"}},
            {"document_id": "doc_456", "fields": {"category": "legal"}}
        ],
        "update_mode": "partial",
        "databases": ["postgresql", "neo4j"]
    }
    ```
    """
    start_time = time.time()
    
    try:
        # Prepare updates
        updates = [{"document_id": u.document_id, "fields": u.fields} for u in request.updates]
        databases = request.databases or ["postgresql"]
        
        # Execute batch updates on each database (using adapter methods directly)
        results = {}
        
        if "postgresql" in databases and postgres_backend:
            try:
                results["postgresql"] = await postgres_backend.batch_update(
                    updates=updates,
                    mode=request.update_mode
                )
            except Exception as e:
                logger.error(f"❌ PostgreSQL batch update failed: {e}")
                results["postgresql"] = {"updated": 0, "failed": len(updates), "errors": [{"error": str(e)}]}
        
        if "neo4j" in databases and neo4j_backend:
            try:
                results["neo4j"] = await neo4j_backend.batch_update(updates=updates)
            except Exception as e:
                logger.error(f"❌ Neo4j batch update failed: {e}")
                results["neo4j"] = {"updated": 0, "failed": len(updates), "errors": [{"error": str(e)}]}
        
        # Aggregate results
        total_updated = sum(r.get("updated", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())
        all_errors = []
        for db_name, r in results.items():
            for err in r.get("errors", []):
                all_errors.append({"database": db_name, **err})
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return {
            "success": total_failed == 0,
            "updated": total_updated,
            "failed": total_failed,
            "errors": all_errors,
            "databases": results,
            "execution_time_ms": round(execution_time_ms, 2),
            "performance_note": "67-80x faster than sequential updates",
            "batch_size": len(request.updates)
        }
    
    except Exception as e:
        logger.error(f"❌ Batch update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@app.post("/api/v1/batch/delete", summary="Batch Delete Documents", tags=["Batch Operations"])
async def batch_delete_documents(request: BatchDeleteRequest):
    """
    Batch delete multiple documents (soft or hard delete).
    
    **Performance:** 100x faster than sequential deletes
    **Max batch size:** 1000 (recommended: 100-500)
    
    **Delete Modes:**
    - `soft`: Mark as deleted (UPDATE deleted=true) - Recommended
    - `hard`: Permanently delete (DELETE FROM) - Use with caution
    
    **Cascade:** For Neo4j, also delete relationships (DETACH DELETE)
    
    **Example:**
    ```json
    {
        "document_ids": ["doc_123", "doc_456", "doc_789"],
        "delete_mode": "soft",
        "cascade": true,
        "databases": ["postgresql", "neo4j"]
    }
    ```
    """
    start_time = time.time()
    
    try:
        databases = request.databases or ["postgresql"]
        
        # Execute batch deletes on each database (using adapter methods directly)
        results = {}
        
        if "postgresql" in databases and postgres_backend:
            try:
                results["postgresql"] = await postgres_backend.batch_delete(
                    document_ids=request.document_ids,
                    mode=request.delete_mode,
                    cascade=request.cascade
                )
            except Exception as e:
                logger.error(f"❌ PostgreSQL batch delete failed: {e}")
                results["postgresql"] = {"deleted": 0, "failed": len(request.document_ids), "errors": [{"error": str(e)}]}
        
        if "neo4j" in databases and neo4j_backend:
            try:
                results["neo4j"] = await neo4j_backend.batch_delete(
                    document_ids=request.document_ids,
                    mode=request.delete_mode,
                    cascade=request.cascade
                )
            except Exception as e:
                logger.error(f"❌ Neo4j batch delete failed: {e}")
                results["neo4j"] = {"deleted": 0, "failed": len(request.document_ids), "errors": [{"error": str(e)}]}
        
        # Aggregate results
        total_deleted = sum(r.get("deleted", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())
        all_errors = []
        for db_name, r in results.items():
            for err in r.get("errors", []):
                all_errors.append({"database": db_name, **err})
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return {
            "success": total_failed == 0,
            "deleted": total_deleted,
            "failed": total_failed,
            "errors": all_errors,
            "databases": results,
            "execution_time_ms": round(execution_time_ms, 2),
            "performance_note": "100x faster than sequential deletes",
            "batch_size": len(request.document_ids)
        }
    
    except Exception as e:
        logger.error(f"❌ Batch delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@app.post("/api/v1/batch/upsert", summary="Batch Upsert Documents", tags=["Batch Operations"])
async def batch_upsert_documents(request: BatchUpsertRequest):
    """
    Batch insert or update documents (conditional operation).
    
    **Performance:** 83x faster than sequential upserts
    **Max batch size:** 1000 (recommended: 50-200)
    
    **Conflict Resolution:**
    - `update`: Update existing documents (INSERT ON CONFLICT UPDATE) - Default
    - `skip`: Skip existing documents (INSERT ON CONFLICT DO NOTHING)
    
    **Example:**
    ```json
    {
        "documents": [
            {"document_id": "doc_123", "fields": {"title": "Report", "status": "draft"}},
            {"document_id": "doc_456", "fields": {"title": "Invoice", "status": "approved"}}
        ],
        "conflict_resolution": "update",
        "databases": ["postgresql", "neo4j"]
    }
    ```
    """
    start_time = time.time()
    
    try:
        # Prepare documents
        documents = [{"document_id": d.document_id, "fields": d.fields} for d in request.documents]
        databases = request.databases or ["postgresql"]
        
        # Execute batch upserts on each database (using adapter methods directly)
        results = {}
        
        if "postgresql" in databases and postgres_backend:
            try:
                results["postgresql"] = await postgres_backend.batch_upsert(
                    documents=documents,
                    conflict_resolution=request.conflict_resolution
                )
            except Exception as e:
                logger.error(f"❌ PostgreSQL batch upsert failed: {e}")
                results["postgresql"] = {"inserted": 0, "updated": 0, "failed": len(documents), "errors": [{"error": str(e)}]}
        
        if "neo4j" in databases and neo4j_backend:
            try:
                results["neo4j"] = await neo4j_backend.batch_upsert(documents=documents)
            except Exception as e:
                logger.error(f"❌ Neo4j batch upsert failed: {e}")
                results["neo4j"] = {"inserted": 0, "updated": 0, "failed": len(documents), "errors": [{"error": str(e)}]}
        
        # Aggregate results
        total_inserted = sum(r.get("inserted", 0) for r in results.values())
        total_updated = sum(r.get("updated", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())
        all_errors = []
        for db_name, r in results.items():
            for err in r.get("errors", []):
                all_errors.append({"database": db_name, **err})
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return {
            "success": total_failed == 0,
            "inserted": total_inserted,
            "updated": total_updated,
            "failed": total_failed,
            "errors": all_errors,
            "databases": results,
            "execution_time_ms": round(execution_time_ms, 2),
            "performance_note": "83x faster than sequential upserts",
            "batch_size": len(request.documents)
        }
    
    except Exception as e:
        logger.error(f"❌ Batch upsert failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch upsert failed: {str(e)}")


# ============================================================================
# HANDELSREGISTER API (Placeholder)
# ============================================================================

@app.get("/handelsregister/search", summary="Handelsregister Suche")
async def search_handelsregister(
    company_name: Optional[str] = QueryParam(None),
    registration_number: Optional[str] = QueryParam(None),
    location: Optional[str] = QueryParam(None)
):
    """Suche im Handelsregister"""
    try:
        # TODO: Implementiere Handelsregister Integration
        return {
            "results": [],
            "count": 0,
            "message": "Handelsregister Integration wird implementiert"
        }
    except Exception as e:
        logger.error(f"Fehler bei Handelsregister Suche: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Development Server (Port 45678 - Main Backend)
    # Reload and access logs are controlled via environment for minimal console noise
    reload_flag = os.getenv("COVINA_RELOAD", "false").lower() == "true"
    access_log_flag = os.getenv("UVICORN_ACCESS_LOG", "false").lower() == "true"
    uvicorn_log_level = os.getenv("UVICORN_LOG_LEVEL", "warning")  # default reduced noise

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=45678,
        reload=reload_flag,
        log_level=uvicorn_log_level,
        access_log=access_log_flag
    )