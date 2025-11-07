#!/usr/bin/env python3
"""
Covina Ingestion Backend (Microservice)
========================================

Separates FastAPI Backend für Dokumenten-Ingestion.
Läuft isoliert vom Main Backend auf eigenem Port.

Features:
- Dokumenten-Upload und Verarbeitung
- Batch-Processing mit Worker Pool
- UDS3 Integration (Vector, Graph, Relational, Document DBs)
- SAGA Transaction Management
- Health Monitoring
- Job Queue Management

Port: 45679 (Main Backend: 45678)
Autor: Covina System
Datum: 11. Oktober 2025
"""

# KRITISCH: sitecustomize MUSS zuerst importiert werden (falls verfügbar)
# Füge das Covina Root Directory zum Path hinzu, damit sitecustomize gefunden wird
import sys
from pathlib import Path

# IMMER den Path setzen (unabhängig davon, ob als Skript oder via uvicorn gestartet)
backend_dir = Path(__file__).parent
covina_root = backend_dir.parent
if str(covina_root) not in sys.path:
    sys.path.insert(0, str(covina_root))

try:
    import sitecustomize  # noqa: F401
except ImportError:
    # sitecustomize ist optional - wird oft für globale Python-Konfiguration verwendet
    pass

import sys
import os
# KRITISCH: Füge Covina Root zum Python Path hinzu für ingestion Module
covina_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if covina_root not in sys.path:
    sys.path.insert(0, covina_root)

import asyncio
import logging
import multiprocessing
import os
import shutil
import tempfile
import threading  # [OK] NEW: For threading.Lock
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import asynccontextmanager  # [OK] NEW: For lifespan
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

# [NEW] Production Hardening Modules (28.10.2025)
from ingestion.exceptions import (
    CovinaException, ErrorCode, ErrorSeverity,
    FileNotFoundException, FileProcessingException,
    DatabaseConnectionException, DatabaseWriteException,
    WorkerCrashException, WorkerOOMException, WorkerTimeoutException,
    MemoryLimitExceededException, CircuitBreakerException,
    wrap_exception
)
from ingestion.worker_pool import initialize_pool_manager, get_pool_manager, shutdown_pool_manager
from ingestion.memory_manager import initialize_memory_manager, get_memory_manager, shutdown_memory_manager
from ingestion.circuit_breaker import get_breaker_manager
from ingestion.prometheus_exporter import get_prometheus_exporter

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

# [OK] Load ENV Configuration BEFORE anything else
from dotenv import load_dotenv
load_dotenv('.env.production')  # Load production config
logger_temp = logging.getLogger("ingestion_backend")
logger_temp.info(f"[TOOL] ENV Loaded: ENABLE_BATCH_EMBEDDINGS={os.getenv('ENABLE_BATCH_EMBEDDINGS')}")

# [OK] NEW: Import Modular Ingestion Architecture
from ingestion.handlers.factory import create_default_factory, HandlerFactory
from ingestion.handlers.base import HandlerContext
from ingestion.scanner import DirectoryScanner, FileClassifier
from ingestion.file_events import FileCategory, FileEventType
logger_temp.info("[OK] Modular ingestion architecture imported successfully")

# Initialize JSON Structured Logging
try:
    from utils.json_logging import setup_json_logging
    from utils.json_logging import get_correlation_id, set_correlation_id
    setup_json_logging(
        service_name="ingestion_backend",
        level=logging.INFO,
        environment=os.getenv("ENVIRONMENT", "development"),
        version="3.4.10"
    )
    logger = logging.getLogger("ingestion_backend")
    logger.info("✅ JSON Structured Logging aktiviert")
    # Minimal sichtbare Konsolen-Ausgabe (frühe Boot-Meldung)
    try:
        print("[BOOT] Ingestion Backend starting on :45679 ...", flush=True)
    except Exception:
        pass
except Exception as e:
    # Fallback to basic config
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("ingestion_backend")
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
    
    # Business Metrics
    documents_processed = metrics_registry.register(
        Counter("documents_processed_total", "Total documents processed", ["status"])
    )
    files_uploaded = metrics_registry.register(
        Counter("files_uploaded_total", "Total files uploaded", ["status"])
    )
    recovery_attempts = metrics_registry.register(
        Counter("recovery_attempts_total", "File recovery attempts", ["result"])
    )
    blocked_files = metrics_registry.register(
        Gauge("blocked_files_current", "Currently blocked files", [])
    )
    
    # Performance Metrics
    processing_latency = metrics_registry.register(
        Histogram("document_processing_seconds", "Document processing time", ["stage"])
    )
    db_operation_latency = metrics_registry.register(
        Histogram("db_operation_seconds", "Database operation time", ["database", "operation"])
    )
    
    # Queue Metrics
    queue_depth = metrics_registry.register(
        Gauge("queue_depth_current", "Current queue depth", ["pool"])
    )
    
    # Active Request Tracking
    active_requests = metrics_registry.register(
        Gauge("active_requests_current", "Current active requests", [])
    )
    
    logger.info("✅ Metrics system initialized (8 metrics registered)")
    METRICS_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ Metrics system not available: {e}")
    METRICS_AVAILABLE = False
    # Create dummy objects to avoid NameError
    documents_processed = None
    files_uploaded = None
    recovery_attempts = None
    blocked_files = None
    processing_latency = None
    db_operation_latency = None
    queue_depth = None
    active_requests = None

# Security (OAuth2/JWT + RBAC)
try:
    from security.auth import Role, Principal, require_roles, get_current_user
    AUTH_AVAILABLE = True
    logger.info("✅ Security module loaded (OAuth2/JWT + RBAC)")
except Exception as e:
    AUTH_AVAILABLE = False
    logger.debug(f"Security module not available (optional): {e}")  # Changed to DEBUG level

# [OK] Initialize Modular Ingestion Architecture
logger.info("[BUILD] Initializing modular ingestion architecture...")
HANDLER_FACTORY = create_default_factory()
handlers_registered = len(HANDLER_FACTORY.registry.snapshot())
logger.info(f"[OK] Handler Factory ready: {handlers_registered} handlers registered")
for category, handler_cls in HANDLER_FACTORY.registry.snapshot().items():
    logger.info(f"   [BOX] {category.value}: {handler_cls.__name__}")

# Feature Flags / Kill-Switches
FLAGS: Dict[str, bool] = {
    # Deaktiviert alle ChromaDB-Schreibzugriffe (Vektoreinfügen) sofort
    "KILL_SWITCH_CHROMADB": False,
}


# [OK] Sentence Transformers für echte Embeddings
EMBEDDING_MODEL = None
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, schnell, Deutsch/Englisch
EMBEDDING_MODEL_LOCK = threading.Lock()  # [OK] Thread-safe model loading

def load_embedding_model():
    """Thread-safe Lazy Loading: Embedding Model nur einmal laden"""
    global EMBEDDING_MODEL
    
    # Fast path: Model already loaded (no lock needed)
    if EMBEDDING_MODEL is not None:
        return EMBEDDING_MODEL
    
    # Slow path: Need to load model (acquire lock)
    with EMBEDDING_MODEL_LOCK:
        # Double-check: Another thread might have loaded it while we waited
        if EMBEDDING_MODEL is not None:
            return EMBEDDING_MODEL
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[SYNC] Loading embedding model: {EMBEDDING_MODEL_NAME}...")
            print(f"\n[SYNC] [MODEL] Loading {EMBEDDING_MODEL_NAME}...\n", flush=True)
            
            EMBEDDING_MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
            
            logger.info(f"[OK] Embedding model loaded: {EMBEDDING_MODEL_NAME} (384-dim)")
            print(f"\n[OK] [MODEL] Loaded successfully! (384-dim)\n", flush=True)
        except ImportError:
            logger.warning("[WARNING] sentence-transformers not installed - using hash-based fallback")
            EMBEDDING_MODEL = "FALLBACK"
        except Exception as e:
            logger.error(f"[ERROR] Failed to load embedding model: {e}")
            print(f"\n[ERROR] [MODEL] Loading failed: {e}\n", flush=True)
            EMBEDDING_MODEL = "FALLBACK"
    
    return EMBEDDING_MODEL

# Reduziere Neo4j Logging
logging.getLogger('neo4j.pool').setLevel(logging.WARNING)
logging.getLogger('neo4j.io').setLevel(logging.WARNING)

# ================================================================
# CHROMADB BATCH INSERT CONFIGURATION
# ================================================================

def should_use_batch_insert() -> bool:
    """
    Check if ChromaDB Batch Insert is enabled via ENV.
    
    Returns:
        bool: True if ENABLE_CHROMA_BATCH_INSERT=true in ENV
    """
    enabled = os.getenv('ENABLE_CHROMA_BATCH_INSERT', 'false').lower() == 'true'
    return enabled


def get_batch_insert_size() -> int:
    """
    Get ChromaDB Batch Insert batch size from ENV.
    
    Returns:
        int: Batch size (default: 100)
    """
    try:
        size = int(os.getenv('CHROMA_BATCH_INSERT_SIZE', '100'))
        return max(1, min(size, 1000))  # Clamp between 1-1000
    except ValueError:
        return 100


logger.info(f"[CONFIG] ChromaDB Batch Insert: {'ENABLED' if should_use_batch_insert() else 'DISABLED'}")
if should_use_batch_insert():
    logger.info(f"[CONFIG] Batch Insert Size: {get_batch_insert_size()}")


# ================================================================
# SAGA TOGGLE (ENV)
# ================================================================

def should_use_saga() -> bool:
    """Check if SAGA processing is enabled via ENV (ENABLE_SAGA=true)."""
    return os.getenv('ENABLE_SAGA', 'false').lower() == 'true'


def should_use_legal_graph_nlp() -> bool:
    """Check if Legal Graph NLP extraction is enabled via ENV (ENABLE_LEGAL_GRAPH_NLP=true)."""
    return os.getenv('ENABLE_LEGAL_GRAPH_NLP', 'false').lower() == 'true'


logger.info(f"[CONFIG] Legal Graph NLP: {'ENABLED' if should_use_legal_graph_nlp() else 'DISABLED'}")


# ================================================================
# ================================================================
# THEMIS FEATURE FLAG / ADAPTER (optional replacement for UDS3)
# ================================================================

USE_THEMIS = os.getenv("USE_THEMIS", "false").lower() == "true"
THEMIS_URL = os.getenv("THEMIS_URL", "http://localhost:8765")
THEMIS_TIMEOUT = int(os.getenv("THEMIS_TIMEOUT", "30"))
THEMIS_MAX_RETRIES = int(os.getenv("THEMIS_MAX_RETRIES", "3"))

THEMIS_AVAILABLE = False
themis_adapter = None
if USE_THEMIS:
    try:
        from database import ThemisAdapter, ThemisConfig
        themis_adapter = ThemisAdapter(
            ThemisConfig(
                url=THEMIS_URL,
                timeout=THEMIS_TIMEOUT,
                max_retries=THEMIS_MAX_RETRIES,
            )
        )
        THEMIS_AVAILABLE = True
        logger.info(f"✅ ThemisAdapter aktiviert (USE_THEMIS=true, URL={THEMIS_URL})")
    except Exception as e:
        logger.error(f"❌ ThemisAdapter Initialisierung fehlgeschlagen: {e}")
        THEMIS_AVAILABLE = False

# ================================================================
# UDS3 PHASE 2: POSTGRESQL + COUCHDB BATCH OPERATIONS
# ================================================================

try:
    from uds3.database.batch_operations import (
        PostgreSQLBatchInserter,
        CouchDBBatchInserter,
        Neo4jBatchCreator,
        should_use_postgres_batch_insert,
        should_use_couchdb_batch_insert,
        should_use_neo4j_batching,
        get_postgres_batch_size,
        get_couchdb_batch_size,
        get_neo4j_batch_size
    )
    BATCH_OPERATIONS_AVAILABLE = True
    if THEMIS_AVAILABLE:
        logger.info("ℹ️ UDS3 Batch Operations übersprungen (Themis aktiv)")
    else:
        logger.info("✅ UDS3 Phase 2 Batch Operations imported")
    if not THEMIS_AVAILABLE:
        logger.info(f"[CONFIG] PostgreSQL Batch Insert: {'ENABLED' if should_use_postgres_batch_insert() else 'DISABLED'}")
        if should_use_postgres_batch_insert():
            logger.info(f"[CONFIG] PostgreSQL Batch Size: {get_postgres_batch_size()}")
        logger.info(f"[CONFIG] CouchDB Batch Insert: {'ENABLED' if should_use_couchdb_batch_insert() else 'DISABLED'}")
        if should_use_couchdb_batch_insert():
            logger.info(f"[CONFIG] CouchDB Batch Size: {get_couchdb_batch_size()}")
        logger.info(f"[CONFIG] Neo4j Batch Insert: {'ENABLED' if should_use_neo4j_batching() else 'DISABLED'}")
        if should_use_neo4j_batching():
            logger.info(f"[CONFIG] Neo4j Batch Size: {get_neo4j_batch_size()}")
    else:
        logger.info("[CONFIG] Batch Insert Settings übersprungen (Themis Modus)")
except ImportError as e:
    BATCH_OPERATIONS_AVAILABLE = False
    logger.warning(f"⚠️ UDS3 Phase 2 Batch Operations not available: {e}")
    logger.warning("   Falling back to single-insert mode for PostgreSQL, CouchDB, and Neo4j")


# ================================================================
# CHROMADB BATCH INSERTER
# ================================================================

class ChromaBatchInserter:
    """
    Context manager for batched ChromaDB inserts.
    
    Usage:
        with ChromaBatchInserter(chromadb_backend, batch_size=100) as inserter:
            for chunk_id, vector, metadata in items:
                inserter.add_vector(chunk_id, vector, metadata)
        # Auto-flush on exit
    """
    
    def __init__(self, chromadb_backend, batch_size: int = 100, auto_flush: bool = True):
        """
        Initialize batch inserter.
        
        Args:
            chromadb_backend: ChromaDB backend instance
            batch_size: Maximum batch size before auto-flush
            auto_flush: Flush remaining items on context exit
        """
        self.backend = chromadb_backend
        self.batch_size = batch_size
        self.auto_flush = auto_flush
        self.batch: List[Tuple[str, List[float], Dict]] = []
        self.total_added = 0
        self.flush_count = 0
    
    def add_vector(self, doc_id: str, vector: List[float], metadata: Dict) -> bool:
        """
        Add vector to batch.
        
        Args:
            doc_id: Document/chunk ID
            vector: Embedding vector
            metadata: Metadata dict
        
        Returns:
            bool: True if added successfully
        """
        self.batch.append((doc_id, vector, metadata))
        
        # Auto-flush when batch is full
        if len(self.batch) >= self.batch_size:
            return self.flush()
        
        return True
    
    def flush(self) -> bool:
        """
        Flush current batch to ChromaDB.
        
        Returns:
            bool: True if successful
        """
        if not self.batch:
            return True
        
        try:
            success = False
            # Prefer batch API when available
            if hasattr(self.backend, 'add_vectors'):
                try:
                    success = self.backend.add_vectors(self.batch)
                except Exception as e:
                    logger.warning(f"[BATCH] add_vectors raised: {e} - falling back to per-item")
                    success = False
            
            if not success:
                # Fallback: add items one-by-one
                added = 0
                for doc_id, vector, metadata in self.batch:
                    try:
                        if hasattr(self.backend, 'add_vector'):
                            ok = self.backend.add_vector(doc_id, vector, metadata)  # Correct order: vector_id, vector, metadata
                        else:
                            ok = False
                        if ok:
                            added += 1
                    except Exception as e:
                        logger.error(f"[BATCH] add_vector failed for {doc_id}: {e}")
                self.total_added += added
                # Mark a flush attempt regardless of partial success to reflect activity
                self.flush_count += 1
                logger.info(f"[BATCH] Fallback flushed {added}/{len(self.batch)} vectors (total: {self.total_added}, flushes: {self.flush_count})")
                self.batch = []
                return added > 0
            else:
                self.total_added += len(self.batch)
                self.flush_count += 1
                logger.debug(f"[BATCH] Flushed {len(self.batch)} vectors (total: {self.total_added}, flushes: {self.flush_count})")
                self.batch = []
                return True
        except Exception as e:
            logger.error(f"[BATCH] Flush failed: {e}")
            self.batch = []
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get batch insert statistics.
        
        Returns:
            Dict with total_added, flush_count, pending_count
        """
        return {
            "total_added": self.total_added,
            "flush_count": self.flush_count,
            "pending_count": len(self.batch)
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with auto-flush."""
        if self.auto_flush and self.batch:
            self.flush()
        return False


# ================================================================
# PYDANTIC MODELS
# ================================================================

class UploadResponse(BaseModel):
    """Upload Response Model"""
    message: str
    job_id: str
    file_count: int
    estimated_processing_time: str

class DirectoryScanResponse(BaseModel):
    """Response for directory upload (instant response)"""
    message: str
    scan_job_id: str
    status: str  # "scanning"
    directory_path: str

class BulkCopyProgress(BaseModel):
    """Progress information for bulk copy operation"""
    percent_complete: float = 0.0
    files_copied: int = 0
    total_files: int = 0
    bytes_copied: int = 0
    total_bytes: int = 0
    copy_rate_mbps: float = 0.0
    eta_seconds: int = 0
    current_file: str = ""
    status: str = "preparing"  # preparing, copying, completed, error

class DirectoryScanStatusResponse(BaseModel):
    """Response for scan status query"""
    scan_job_id: str
    status: str  # scanning, creating_jobs, completed, error
    files_found: int
    bulk_copy_progress: Optional[BulkCopyProgress] = None  # 🆕 NEW!
    upload_jobs_created: int
    upload_job_ids: List[str]
    error: Optional[str] = None
    elapsed_time: float

class JobStatus(BaseModel):
    """Job Status Model"""
    job_id: str
    status: str
    created_at: str
    updated_at: str
    file_count: int
    processed_files: int
    error_message: Optional[str] = None

class JobMetrics(BaseModel):
    """Detaillierte Job-Metriken"""
    job_id: str
    total_files: int
    successful_files: int
    failed_files: int
    processing_time: float
    content_extracted_chars: int
    ai_entities_found: int
    metadata_completeness: float
    classification_stats: Dict[str, int]
    backend_metrics: Dict[str, Any]

class HealthResponse(BaseModel):
    """Health Check Response"""
    status: str
    timestamp: str
    components: Dict[str, str]
    worker_pool: Dict[str, Any]
    hardening: Optional[Dict[str, Any]] = None  # Production Hardening Metrics

# ================================================================
# WEBSOCKET MANAGER
# ================================================================

class WebSocketManager:
    """
    WebSocket Connection Manager für Real-Time Job Updates
    
    Features:
    - Connection Pooling (mehrere simultane Clients)
    - Broadcasting (alle Clients erhalten Updates)
    - Auto-Cleanup (disconnected clients werden entfernt)
    - Thread-Safe (asyncio.Lock für concurrent access)
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Neue WebSocket-Verbindung akzeptieren"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            logger.info(f"[OK] WebSocket connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """WebSocket-Verbindung entfernen"""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(f"[ERROR] WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast_job_update(self, job_data: Dict[str, Any]):
        """
        Sende Job-Update an alle verbundenen Clients
        
        Args:
            job_data: Job-Informationen (job_id, status, progress, etc.)
        """
        if not self.active_connections:
            return  # Keine Clients verbunden
        
        disconnected = []
        
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_json(job_data)
                except Exception as e:
                    logger.warning(f"[WARNING] Failed to send to client: {e}")
                    disconnected.append(connection)
        
        # Cleanup disconnected clients
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Sende Nachricht an spezifischen Client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"[ERROR] Failed to send personal message: {e}")

    async def _broadcast_bulk_copy_progress(self):
        """🆕 Broadcast bulk copy progress to all WebSocket clients"""
        if not hasattr(self, 'bulk_copy_progress'):
            return
        
        message = {
            "type": "bulk_copy_progress",
            "scan_job_id": self.scan_job_id,
            "progress": {
                "percent_complete": self.bulk_copy_progress.percent_complete,
                "files_copied": self.bulk_copy_progress.files_copied,
                "bytes_copied": self.bulk_copy_progress.bytes_copied,
                "bytes_gb": round(self.bulk_copy_progress.bytes_copied / (1024**3), 2),
                "copy_rate_mbps": round(self.bulk_copy_progress.copy_rate_mbps, 1),
                "status": self.bulk_copy_progress.status
            }
        }
        
        await self.broadcast(message)

# Global WebSocket Manager Instance
ws_manager = WebSocketManager()

# ================================================================
# DIRECTORY SCAN JOBS (Async Upload)
# ================================================================

class DirectoryScanJob:
    """
    Modular directory scan job using ingestion.handlers architecture.
    
    Workflow:
    1. Scan directory recursively (DirectoryScanner)
    2. Copy files to temp directory (data/uploads/scan_{id}/)
    3. Extract archives (ArchiveIngestionHandler)
    4. Discover all ingestible files (including extracted)
    5. Create smart chunks
    6. Submit jobs to ThreadPool
    
    Features:
    - Modular handler system
    - Archive extraction (ZIP, RAR, 7z, TAR)
    - Timeout protection (network drives)
    - Smart chunking (size-aware)
    - Real-time WebSocket updates
    """
    
    def __init__(
        self,
        scan_job_id: str,
        directory_path: str,
        handler_factory: Optional[HandlerFactory] = None,  # Type hint restored
        chunk_size: int = 50
    ):
        self.scan_job_id = scan_job_id
        self.directory_path = Path(directory_path)
        self.handler_factory = handler_factory or HANDLER_FACTORY
        self.chunk_size = chunk_size
        
        # Create temp directory for file processing
        self.temp_dir = Path("data/uploads") / f"scan_{scan_job_id}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Scanner configuration
        self.scanner = DirectoryScanner(
            root=self.directory_path,
            classifier=FileClassifier(),
            compute_hashes=False  # Skip hashing for performance
        )
        
        # Status tracking
        self.status = "scanning"
        self.files_found = 0
        self.files_extracted = 0  # NEW: Track extracted files
        self.upload_jobs_created = []
        self.error_message = None
        self.start_time = datetime.now()
        self.bulk_copy_progress: Optional[BulkCopyProgress] = None  # 🆕 Track bulk copy progress
    
    async def scan_and_create_jobs(self):
        """Main workflow: copy directory → scan locally → extract → chunk → submit"""
        try:
            logger.info(f"[TARGET] [SCAN {self.scan_job_id}] Starting modular scan: {self.directory_path}")
            
            # Phase 0: Copy entire directory to temp_dir (fast OS-level copy!)
            logger.info(f"📂 [SCAN {self.scan_job_id}] Copying directory to local temp...")
            await self._bulk_copy_directory()
            
            # Phase 1: Directory Scan (now on LOCAL drive - fast!)
            file_events = await self._scan_directory()
            self.files_found = len(file_events)
            logger.info(f"📂 [SCAN {self.scan_job_id}] Found {self.files_found} files")
            
            if not file_events:
                self.status = "completed"
                self.error_message = "No supported files found"
                await self._broadcast_status()
                return
            
            # Phase 2: Copy Files & Extract Archives
            self.status = "extracting"
            await self._broadcast_status()
            
            all_files = await self._copy_and_extract_files(file_events)
            logger.info(
                f"[OK] [SCAN {self.scan_job_id}] "
                f"{len(all_files)} files ready (extracted: {self.files_extracted})"
            )
            
            # Phase 3: Create Jobs
            self.status = "creating_jobs"
            await self._broadcast_status()
            
            await self._create_and_submit_jobs(all_files)
            
            # Phase 4: Complete
            self.status = "completed"
            elapsed = (datetime.now() - self.start_time).total_seconds()
            logger.info(
                f"[PARTY] [SCAN {self.scan_job_id}] Completed: "
                f"{self.files_found} original + {self.files_extracted} extracted = "
                f"{len(all_files)} total files in {elapsed:.1f}s"
            )
            await self._broadcast_status()
            
        except Exception as e:
            logger.error(f"[ERROR] [SCAN {self.scan_job_id}] Error: {e}", exc_info=True)
            self.status = "error"
            self.error_message = str(e)
            await self._broadcast_status()
    
    async def _bulk_copy_directory(self):
        """
        🆕 Copy entire directory to temp_dir with STREAMING PROGRESS UPDATES.
        
        Benefits:
        - Much faster than Python file-by-file copy
        - Handles Network Drives efficiently
        - Real-time progress updates via WebSocket
        - Robust error handling
        - Uses robocopy (Windows) or rsync (Linux)
        """
        from ingestion.bulk_copy_streaming import BulkCopyStreaming, CopyProgress
        
        logger.info(f"[BOX] [SCAN {self.scan_job_id}] Bulk copy: {self.directory_path} → {self.temp_dir}")
        
        # 🆕 Initialize progress tracking
        self.bulk_copy_progress = BulkCopyProgress(status="preparing")
        await self._broadcast_bulk_copy_progress()
        
        async def on_progress(progress: CopyProgress):
            """Callback for progress updates from streaming module"""
            # Update our progress object
            self.bulk_copy_progress.percent_complete = progress.percent_complete
            self.bulk_copy_progress.files_copied = progress.files_copied
            self.bulk_copy_progress.total_files = progress.total_files
            self.bulk_copy_progress.bytes_copied = progress.bytes_copied
            self.bulk_copy_progress.total_bytes = progress.total_bytes
            self.bulk_copy_progress.copy_rate_mbps = progress.copy_rate_mbps
            self.bulk_copy_progress.eta_seconds = progress.eta_seconds
            self.bulk_copy_progress.current_file = progress.current_file
            self.bulk_copy_progress.status = progress.status
            
            # Broadcast to WebSocket clients
            await self._broadcast_bulk_copy_progress()
        
        # 🆕 Use streaming bulk copy with progress callbacks
        copier = BulkCopyStreaming(
            source=self.directory_path,
            destination=self.temp_dir,
            progress_callback=on_progress,
            broadcast_interval=5.0  # Update UI every 5 seconds
        )
        
        timeout_seconds = 1800  # 30 minutes for large network transfers (7+ GB)
        
        try:
            final_progress = await copier.execute(timeout=timeout_seconds)
            
            logger.info(
                f"[OK] [SCAN {self.scan_job_id}] Bulk copy complete: "
                f"{final_progress.files_copied} files, "
                f"{final_progress.bytes_copied / (1024**3):.2f} GB, "
                f"avg rate: {final_progress.copy_rate_mbps:.1f} MB/s"
            )
            
            # Mark progress as completed
            self.bulk_copy_progress.status = "completed"
            await self._broadcast_bulk_copy_progress()
            
            # Re-initialize scanner to point to LOCAL copy
            logger.info(f"[SYNC] [SCAN {self.scan_job_id}] Re-initializing scanner for local copy...")
            self.scanner = DirectoryScanner(
                root=self.temp_dir,  # [OK] Now scans local copy!
                classifier=FileClassifier(),
                compute_hashes=False
            )
            logger.info(f"[OK] [SCAN {self.scan_job_id}] Scanner ready for local directory")
            
        except asyncio.TimeoutError:
            self.bulk_copy_progress.status = "error"
            await self._broadcast_bulk_copy_progress()
            raise TimeoutError(
                f"Directory copy timeout after {timeout_seconds}s "
                f"(source: {self.directory_path})"
            )
        except Exception as e:
            self.bulk_copy_progress.status = "error"
            await self._broadcast_bulk_copy_progress()
            logger.error(f"[ERROR] [SCAN {self.scan_job_id}] Bulk copy error: {e}")
            raise
    async def _scan_directory(self) -> List:
        """Scan directory using DirectoryScanner with timeout protection."""
        # NOW scans LOCAL temp_dir (much faster!)
        scan_path = self.temp_dir  # [OK] Scan local copy, not network drive!
        logger.info(f"[SEARCH] [SCAN {self.scan_job_id}] Scanning LOCAL: {scan_path}")
        
        def scan_sync():
            """Sync wrapper for DirectoryScanner"""
            return self.scanner.scan_once()
        
        # Execute with timeout (network drive protection)
        loop = asyncio.get_running_loop()
        timeout_seconds = 300  # 5 minutes
        
        try:
            events = await asyncio.wait_for(
                loop.run_in_executor(None, scan_sync),
                timeout=timeout_seconds
            )
            logger.info(f"[OK] [SCAN {self.scan_job_id}] Scan complete: {len(events)} events")
            return events
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Directory scan timeout after {timeout_seconds}s "
                f"(network drive issue: {self.directory_path})"
            )
    
    async def _copy_and_extract_files(self, file_events: List) -> List[str]:
        """
        Copy files to temp directory and extract archives.
        
        Returns:
            List of absolute paths to all processable files (including extracted)
        """
        all_files = []
        
        for event in file_events:
            snapshot = event.snapshot
            
            # Skip deleted files
            if event.event_type == FileEventType.DELETED:
                continue
            
            # Copy file to temp directory
            dest_path = self.temp_dir / snapshot.path.name
            try:
                shutil.copy2(snapshot.path, dest_path)
                logger.debug(f"[INFO] Copied: {snapshot.path.name} → {dest_path}")
            except Exception as e:
                logger.error(f"Failed to copy {snapshot.path}: {e}")
                continue
            
            # Handle based on category
            category = snapshot.category
            
            if category == FileCategory.ARCHIVE:
                # Extract archive using ArchiveIngestionHandler
                extracted = await self._extract_archive(dest_path)
                all_files.extend(extracted)
                self.files_extracted += len(extracted)
                logger.info(
                    f"[BOX] [SCAN {self.scan_job_id}] Extracted {len(extracted)} files "
                    f"from {snapshot.path.name}"
                )
            else:
                # Regular file - add directly
                all_files.append(str(dest_path))
        
        return all_files
    
    async def _extract_archive(self, archive_path: Path) -> List[str]:
        """Extract archive using ArchiveIngestionHandler."""
        try:
            # Get handler for archives
            handler = self.handler_factory.create(FileCategory.ARCHIVE)
            
            # Create handler context
            context = HandlerContext(
                file_path=archive_path,
                temp_dir=self.temp_dir
            )
            
            # Execute extraction in thread pool (I/O bound)
            loop = asyncio.get_running_loop()
            extracted_files = await loop.run_in_executor(
                None,
                handler.extract_and_discover_files,
                context
            )
            
            logger.info(f"[OK] Extracted {len(extracted_files)} files from {archive_path.name}")
            return extracted_files
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to extract {archive_path.name}: {e}")
            return []  # Return empty list on error (don't fail entire scan)
    
    async def _create_and_submit_jobs(self, file_paths: List[str]):
        """Create smart chunks and submit to ThreadPool."""
        from ingestion_backend import get_job_manager, io_executor, process_documents_batch
        
        jm = get_job_manager()
        
        # Smart chunking (size-aware)
        file_chunks = self._create_smart_chunks(file_paths)
        
        logger.info(
            f"[BOX] [SCAN {self.scan_job_id}] Created {len(file_chunks)} chunks "
            f"from {len(file_paths)} files"
        )
        
        # Submit each chunk
        for chunk_idx, chunk in enumerate(file_chunks):
            # Create job with temp_directory tracking
            upload_job_id = jm.create_job(
                len(chunk),
                temp_directory=str(self.temp_dir),  # [OK] IMPORTANT!
                scan_job_id=self.scan_job_id
            )
            self.upload_jobs_created.append(upload_job_id)
            
            # Submit to ThreadPool
            def process_chunk_sync(job_id, file_paths_chunk, chunk_idx, temp_dir):
                """Sync wrapper for background processing"""
                # Propagate correlation ID from job metadata into this worker thread
                try:
                    jmeta = jm.job_storage.get_job(job_id)
                    if jmeta and jmeta.get("correlation_id"):
                        set_correlation_id(jmeta.get("correlation_id"))
                except Exception:
                    pass
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    logger.info(f"[START] [THREAD {chunk_idx}] Processing {len(file_paths_chunk)} files")
                    loop.run_until_complete(
                        process_documents_batch(job_id, file_paths_chunk, temp_dir)
                    )
                    logger.info(f"[OK] [THREAD {chunk_idx}] Completed")
                except Exception as e:
                    logger.error(f"[ERROR] [THREAD {chunk_idx}] Error: {e}", exc_info=True)
                finally:
                    loop.close()
            
            # [NEW] Use WorkerPoolManager
            pool_manager = get_pool_manager()
            task_id = f"scan_chunk_{self.scan_job_id}_{chunk_idx}_{int(time.time())}"
            
            pool_manager.submit_io_task(
                process_chunk_sync,
                upload_job_id,
                chunk,
                chunk_idx,
                Path(self.temp_dir),
                task_id=task_id
            )
            
            logger.info(
                f"[BOX] [SCAN {self.scan_job_id}] Job {chunk_idx+1}/{len(file_chunks)}: "
                f"{upload_job_id} ({len(chunk)} files), Task: {task_id}"
            )
    
    def _create_smart_chunks(self, file_paths: List[str]) -> List[List[str]]:
        """Create size-aware chunks respecting limits."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for file_path in file_paths:
            try:
                file_size = os.path.getsize(file_path)
                
                # Check if new chunk needed
                if (len(current_chunk) >= MAX_CHUNK_SIZE_FILES or
                    current_size + file_size > MAX_CHUNK_SIZE_MB * 1024 * 1024):
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = []
                    current_size = 0
                
                current_chunk.append(file_path)
                current_size += file_size
                
            except OSError:
                # Skip files we can't access
                continue
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _broadcast_status(self):
        """Broadcast scan status via WebSocket"""
        try:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            await ws_manager.broadcast_job_update({
                "type": "directory_scan_update",
                "scan_job_id": self.scan_job_id,
                "status": self.status,
                "files_found": self.files_found,
                "files_extracted": self.files_extracted,
                "upload_jobs_created": len(self.upload_jobs_created),
                "upload_job_ids": self.upload_jobs_created,
                "error": self.error_message,
                "elapsed_time": elapsed
            })
        except Exception as e:
            logger.debug(f"Status broadcast failed: {e}")
    
    async def _broadcast_bulk_copy_progress(self):
        """Broadcast bulk copy progress via WebSocket"""
        try:
            if self.bulk_copy_progress:
                await ws_manager.broadcast_job_update({
                    "type": "bulk_copy_progress",
                    "scan_job_id": self.scan_job_id,
                    "progress": self.bulk_copy_progress.model_dump()
                })
        except Exception as e:
            logger.debug(f"Bulk copy progress broadcast failed: {e}")

class ScanJobManager:
    """Manages directory scan jobs"""
    
    def __init__(self):
        self.scan_jobs: Dict[str, DirectoryScanJob] = {}
        self.background_tasks: Dict[str, asyncio.Task] = {}  # [OK] FIX: Track background tasks
        self._lock = asyncio.Lock()
    
    def create_scan_job(self, directory_path: str, chunk_size: int = 50) -> str:
        """Create new directory scan job"""
        scan_job_id = f"scan_{uuid.uuid4().hex[:12]}"
        
        scan_job = DirectoryScanJob(
            scan_job_id=scan_job_id,
            directory_path=directory_path,
            chunk_size=chunk_size
        )
        
        self.scan_jobs[scan_job_id] = scan_job
        logger.info(f"[INFO] [SCAN {scan_job_id}] Created scan job for: {directory_path}")
        return scan_job_id
    
    def get_scan_job(self, scan_job_id: str) -> Optional[DirectoryScanJob]:
        """Get scan job by ID"""
        return self.scan_jobs.get(scan_job_id)
    
    async def start_scan_job(self, scan_job_id: str):
        """Start background scan job (non-blocking!)"""
        scan_job = self.scan_jobs.get(scan_job_id)
        if scan_job:
            logger.info(f"[START] [SCAN {scan_job_id}] Starting background scan...")
            
            # [OK] FIX: Create task and store reference (prevents GC cleanup)
            task = asyncio.create_task(self._run_scan_with_error_handling(scan_job))
            self.background_tasks[scan_job_id] = task
            
            # Cleanup task from dict when done
            task.add_done_callback(lambda t: self.background_tasks.pop(scan_job_id, None))
            
            logger.info(f"[OK] [SCAN {scan_job_id}] Background scan task created")
        else:
            logger.error(f"[ERROR] Scan job not found: {scan_job_id}")
    
    async def _run_scan_with_error_handling(self, scan_job: DirectoryScanJob):
        """Run scan with error handling (called as background task)"""
        try:
            await scan_job.scan_and_create_jobs()
            logger.info(f"[OK] [SCAN {scan_job.scan_job_id}] Scan completed successfully")
        except Exception as e:
            logger.error(f"[ERROR] [SCAN {scan_job.scan_job_id}] Scan failed: {e}", exc_info=True)
            scan_job.status = "error"
            scan_job.error_message = str(e)
    
    def cleanup_old_jobs(self, max_age_seconds: int = 3600):
        """Remove old scan jobs (1 hour default)"""
        now = datetime.now()
        to_remove = [
            job_id for job_id, job in self.scan_jobs.items()
            if (now - job.start_time).total_seconds() > max_age_seconds
        ]
        
        for job_id in to_remove:
            del self.scan_jobs[job_id]
        
        if to_remove:
            logger.info(f"🧹 Cleaned up {len(to_remove)} old scan jobs")
        
        return len(to_remove)


# Global scan job manager
_scan_job_manager = None

def get_scan_job_manager() -> ScanJobManager:
    """Get global scan job manager (singleton)"""
    global _scan_job_manager
    if _scan_job_manager is None:
        _scan_job_manager = ScanJobManager()
    return _scan_job_manager


# ================================================================
# PERFORMANCE CONFIGURATION
# ================================================================

CPU_COUNT = multiprocessing.cpu_count()

# PRODUCTION OPTIMIERUNG (basierend auf Load Test Ergebnisse 12.10.2025):
# Load Test ergab: Throughput-Plateau bei 165 files/s mit 18 Workers
# Empfehlung: Worker Pool verdoppeln für +80-100% Throughput
# Erwartete Performance: 300-400 files/s

# [P0 FIX] Windows ProcessPool Spawn Overhead Protection (21.10.2025)
# Problem: spawn mode creates full Python processes (500MB+ each)
# 36 workers × 500MB = 18 GB RAM overhead → OOM crashes!
# Solution: Reduce CPU workers to 8 (stable, 2-3 GB total)
# Impact: Classification slower but NO CRASHES

# Environment Variables für dynamische Konfiguration
IO_WORKERS = int(os.getenv("WORKERS_IO", min(36, CPU_COUNT * 2)))  # Default: 36 (I/O nicht betroffen)
CPU_WORKERS = int(os.getenv("WORKERS_CPU", min(8, CPU_COUNT)))      # Default: 8 (war 36 - CRITICAL FIX!)

logger.info(f"[START] Worker Pool Configuration: {IO_WORKERS} I/O Workers, {CPU_WORKERS} CPU Workers (Total CPUs: {CPU_COUNT})")
logger.info(f"[SHIELD] ProcessPool Protection: CPU workers limited to {CPU_WORKERS} (prevents spawn overhead)")

# ================================================================
# INGESTION HARDENING LIMITS (v3.5.0)
# ================================================================

# Scan Limits
MAX_FILES_PER_SCAN = int(os.getenv("MAX_FILES_PER_SCAN", 50000))      # Maximale Dateien pro Directory Scan
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 2048))           # Maximale Einzeldateigröße (2 GB)
MAX_TOTAL_SIZE_GB = int(os.getenv("MAX_TOTAL_SIZE_GB", 100))          # Maximale Gesamtgröße pro Scan (100 GB)
SCAN_PROGRESS_INTERVAL = int(os.getenv("SCAN_PROGRESS_INTERVAL", 100)) # Progress Update alle N Dateien

# Chunking Limits
MAX_CHUNK_SIZE_FILES = int(os.getenv("MAX_CHUNK_SIZE_FILES", 50))     # Max Dateien pro Chunk
MAX_CHUNK_SIZE_MB = int(os.getenv("MAX_CHUNK_SIZE_MB", 1024))         # Max MB pro Chunk (1 GB)

# Worker Pool Limits
MAX_ACTIVE_JOBS = int(os.getenv("MAX_ACTIVE_JOBS", 100))              # Maximale gleichzeitige Jobs

# [P1 FIX] Parallel Processing Limit (21.10.2025)
# Problem: Unlimited parallel documents → 10,000 files × 4 DBs = 40,000 connections!
# → PostgreSQL max_connections exceeded, Neo4j service unavailable
# Solution: Limit to 50 concurrent documents (200 DB connections max)
MAX_PARALLEL_DOCUMENTS = int(os.getenv("MAX_PARALLEL_DOCUMENTS", 50))

logger.info(f"[SHIELD] Ingestion Hardening Enabled:")
logger.info(f"   MAX_FILES_PER_SCAN = {MAX_FILES_PER_SCAN:,}")
logger.info(f"   MAX_FILE_SIZE_MB = {MAX_FILE_SIZE_MB:,} MB")
logger.info(f"   MAX_TOTAL_SIZE_GB = {MAX_TOTAL_SIZE_GB} GB")
logger.info(f"   MAX_CHUNK_SIZE_FILES = {MAX_CHUNK_SIZE_FILES}")
logger.info(f"   MAX_CHUNK_SIZE_MB = {MAX_CHUNK_SIZE_MB} MB")
logger.info(f"   MAX_ACTIVE_JOBS = {MAX_ACTIVE_JOBS}")
logger.info(f"   MAX_PARALLEL_DOCUMENTS = {MAX_PARALLEL_DOCUMENTS} (P1 Protection)")

# Thread Pool für I/O Operations (File Reading, Upload, DB Writes)
io_executor = ThreadPoolExecutor(
    max_workers=IO_WORKERS,
    thread_name_prefix="ingestion_io"
)

# Process Pool für CPU-intensive Operations (AI, Parsing, Embeddings)
cpu_executor = ProcessPoolExecutor(
    max_workers=CPU_WORKERS,
    mp_context=multiprocessing.get_context('spawn')
)

# [P1 FIX] Processing Semaphore (21.10.2025)
# Limits concurrent document processing to prevent DB connection exhaustion
# NOTE: Semaphore MUST be created per event loop (asyncio limitation)
_processing_semaphores = {}  # Dict[event_loop_id, Semaphore]

def get_processing_semaphore() -> asyncio.Semaphore:
    """
    Get or create processing semaphore for current event loop.
    
    Each event loop needs its own semaphore instance to avoid
    "bound to different event loop" errors.
    
    Returns:
        Semaphore instance for current event loop
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - this should not happen in async context
        raise RuntimeError("get_processing_semaphore() called outside async context")
    
    loop_id = id(loop)
    if loop_id not in _processing_semaphores:
        _processing_semaphores[loop_id] = asyncio.Semaphore(MAX_PARALLEL_DOCUMENTS)
    
    return _processing_semaphores[loop_id]

# Worker Pool Metrics Tracking
def update_pool_metrics():
    """Update worker pool queue depth metrics."""
    if not METRICS_AVAILABLE or queue_depth is None:
        return
    
    try:
        # I/O Pool Queue Depth
        io_queue_size = io_executor._work_queue.qsize() if hasattr(io_executor, '_work_queue') else 0
        queue_depth.set(io_queue_size, labels={"pool": "io"})
        
        # CPU Pool Queue Depth (ProcessPoolExecutor uses different internals)
        cpu_queue_size = len(cpu_executor._pending_work_items) if hasattr(cpu_executor, '_pending_work_items') else 0
        queue_depth.set(cpu_queue_size, labels={"pool": "cpu"})
        
    except Exception as e:
        logger.debug(f"Failed to update pool metrics: {e}")

# ================================================================
# JOB MANAGER
# ================================================================

class IngestionJobManager:
    """Job Manager für Ingestion Backend mit Persistent Storage"""
    
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self._jobs_lock = threading.Lock()  # [OK] Thread-safe access
        self.uds3_ready = False
        self.uds3_strategy = None
        
        # [OK] NEW: Persistent Job Storage for Crash Recovery
        from ingestion.job_persistence import PersistentJobStorage
        self.job_storage = PersistentJobStorage(db_path="data/ingestion_jobs.db")
        
        # Performance Metrics
        self.metrics = {
            "total_documents": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_processing_time": 0.0,
        }
        
        # [OK] NEW: Load incomplete jobs from database on startup
        self._load_incomplete_jobs()
        
        # UDS3 Integration Setup
        self._setup_uds3()
    
    def _load_incomplete_jobs(self):
        """Load incomplete jobs from database for crash recovery"""
        try:
            incomplete_jobs = self.job_storage.get_incomplete_jobs()
            
            if incomplete_jobs:
                logger.info(f"[SYNC] Found {len(incomplete_jobs)} incomplete jobs from previous session")
                
                with self._jobs_lock:
                    for job_data in incomplete_jobs:
                        job_id = job_data["job_id"]
                        self.jobs[job_id] = job_data
                        
                        # Mark as recovered (user can restart manually)
                        logger.info(f"   [INFO] Job {job_id}: {job_data['status']} "
                                  f"({job_data['processed_files']}/{job_data['file_count']} files)")
                
                logger.info(f"[OK] Loaded {len(incomplete_jobs)} incomplete jobs into memory")
            else:
                logger.info("[OK] No incomplete jobs found - clean start")
                
        except Exception as e:
            logger.error(f"[ERROR] Failed to load incomplete jobs: {e}")
    
    def _setup_uds3(self):
        """
        Initialisiere UDS3 Framework mit automatischer Backend-Konfiguration.
        
        Separation of Concerns:
        - Ingestion Backend: Definiert welche DB-Typen benötigt werden
        - UDS3 Database Manager: Übernimmt komplette Konfiguration (Credentials, Connections, etc.)
        
        Keine ENV-Variablen nötig - alles zentral in UDS3!
        
        NOTE: Skipped wenn Themis aktiv (THEMIS_AVAILABLE=True)
        """
        # Skip UDS3 setup if Themis is active
        if THEMIS_AVAILABLE:
            logger.info("ℹ️ UDS3 Setup übersprungen (Themis Modus aktiv)")
            self.uds3_ready = False
            self.uds3_strategy = None
            return
        
        try:
            logger.info("=" * 80)
            logger.info("🔧 UDS3 v2.0.0 AUTO-CONFIG (Ingestion)")
            logger.info("=" * 80)
            logger.info("Pattern: Backend-Typen angeben → UDS3 konfiguriert automatisch")
            logger.info("")
            
            from uds3.core.polyglot_manager import UDS3PolyglotManager
            
            # Nur Backend-TYPEN angeben - UDS3 übernimmt Rest!
            backend_config = {
                "relational": {"enabled": True},  # PostgreSQL
                "vector": {"enabled": True},      # ChromaDB
                "graph": {"enabled": True},       # Neo4j
                "file": {"enabled": True}         # CouchDB
            }
            
            self.uds3_strategy = UDS3PolyglotManager(
                backend_config=backend_config,
                enable_rag=False
            )
            logger.info("✅ UDS3 PolyglotManager initialisiert (Auto-Config)")
            
            # Backend-Status ausgeben (DatabaseManager hat bereits alles konfiguriert!)
            self.uds3_ready = True
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ UDS3 AUTO-CONFIG COMPLETE (Ingestion)")
            logger.info("=" * 80)
            
            db_manager = self.uds3_strategy.db_manager
            postgres_backend = db_manager.get_relational_backend()
            chroma_backend = db_manager.get_vector_backend()
            neo4j_backend = db_manager.get_graph_backend()
            file_backend = getattr(db_manager, 'file_backend', None)
            
            logger.info(f"   PostgreSQL: {'✅ Connected' if postgres_backend else '❌ Not available'}")
            logger.info(f"   ChromaDB:   {'✅ Connected' if chroma_backend else '❌ Not available'}")
            logger.info(f"   Neo4j:      {'✅ Connected' if neo4j_backend else '❌ Not available'}")
            logger.info(f"   CouchDB:    {'✅ Connected' if file_backend else '❌ Not available'}")
            logger.info("")
            logger.info("🔌 UDS3 Status: [OK] Ready")
            logger.info("=" * 80)
            
        except Exception as e:
            self.uds3_ready = False
            logger.error("=" * 80)
            logger.error("❌ CRITICAL ERROR: UDS3 Setup Failed (Ingestion)")
            logger.error("=" * 80)
            logger.error(f"Error: {e}")
            logger.error("")
            logger.error("🔍 DEBUG INFO:")
            logger.error(f"   Environment Variables:")
            logger.error(f"      POSTGRES_HOST: {os.getenv('POSTGRES_HOST', 'not set')}")
            logger.error(f"      CHROMA_HOST: {os.getenv('CHROMA_HOST', 'not set')}")
            logger.error(f"      NEO4J_HOST: {os.getenv('NEO4J_HOST', 'not set')}")
            logger.error(f"      COUCHDB_HOST: {os.getenv('COUCHDB_HOST', 'not set')}")
            logger.error("")
            logger.error("💡 TROUBLESHOOTING:")
            logger.error("   1. Check .env.production file exists and is loaded")
            logger.error("   2. Verify all database servers running")
            logger.error("   3. Test network connectivity to 192.168.178.94")
            logger.error("=" * 80)
            import traceback
            logger.error(traceback.format_exc())
            self.uds3_ready = False
    
    # Helper methods for backend access (UDS3 v2.0 compatibility + Themis support)
    def get_relational_backend(self):
        """Get relational (PostgreSQL/Themis) backend"""
        if THEMIS_AVAILABLE and themis_adapter:
            return themis_adapter.get_relational_backend()
        return self.uds3_strategy.db_manager.get_relational_backend() if self.uds3_strategy else None
    
    def get_vector_backend(self):
        """Get vector (ChromaDB/Themis) backend"""
        if THEMIS_AVAILABLE and themis_adapter:
            return themis_adapter.get_vector_backend()
        return self.uds3_strategy.db_manager.get_vector_backend() if self.uds3_strategy else None
    
    def get_graph_backend(self):
        """Get graph (Neo4j/Themis) backend"""
        if THEMIS_AVAILABLE and themis_adapter:
            return themis_adapter.get_graph_backend()
        return self.uds3_strategy.db_manager.get_graph_backend() if self.uds3_strategy else None
    
    def get_document_backend(self):
        """Get document (CouchDB/Themis) backend"""
        if THEMIS_AVAILABLE and themis_adapter:
            return themis_adapter.get_document_backend()
        if not self.uds3_strategy:
            return None
        db_manager = self.uds3_strategy.db_manager
        return getattr(db_manager, 'get_document_backend', lambda: None)()

    
    def create_job(self, file_count: int, temp_directory: str = None, scan_job_id: str = None, correlation_id: str = None) -> str:
        """Erstelle neuen Job mit Persistent Storage"""
        job_id = str(uuid.uuid4())
        # Capture current request correlation_id if not explicitly provided
        try:
            if correlation_id is None:
                correlation_id = get_correlation_id()
        except Exception:
            correlation_id = None
        
        job_data = {
            "job_id": job_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "file_count": file_count,
            "processed_files": 0,
            "error_message": None,
            "metrics": {},
            "temp_directory": temp_directory,
            "scan_job_id": scan_job_id,
            "correlation_id": correlation_id
        }
        
        with self._jobs_lock:  # [OK] Thread-safe
            self.jobs[job_id] = job_data
        
        # [OK] NEW: Save to persistent storage
        self.job_storage.save_job(job_data)
        
        return job_id
    
    def update_job_status(self, job_id: str, status: str, error: str = None):
        """Update Job Status with Persistent Storage"""
        with self._jobs_lock:  # [OK] Thread-safe
            # [OK] FIX: Load job from DB if not in memory (Singleton broken in background threads!)
            if job_id not in self.jobs:
                logger.warning(f"[FIX] Job {job_id} not in memory - loading from DB...")
                job_data = self.job_storage.get_job(job_id)
                if job_data:
                    self.jobs[job_id] = job_data
                    logger.info(f"[OK] Job {job_id} loaded from DB into memory")
                else:
                    logger.error(f"[ERROR] Job {job_id} not found in DB either!")
                    return  # Job doesn't exist - can't update
            
            # Now update the job
            self.jobs[job_id]["status"] = status
            self.jobs[job_id]["updated_at"] = datetime.now().isoformat()
            if error:
                self.jobs[job_id]["error_message"] = error
            
            # [OK] NEW: Save to persistent storage
            self.job_storage.save_job(self.jobs[job_id])
        
        # Broadcast WebSocket Update (outside lock!)
        asyncio.create_task(self._broadcast_job_update(job_id))
    
    def update_job_progress(self, job_id: str, processed: int):
        """Update Job Progress with Persistent Storage"""
        with self._jobs_lock:  # [OK] Thread-safe
            # [OK] FIX: Load job from DB if not in memory (Singleton broken in background threads!)
            if job_id not in self.jobs:
                logger.warning(f"[FIX] Job {job_id} not in memory - loading from DB...")
                job_data = self.job_storage.get_job(job_id)
                if job_data:
                    self.jobs[job_id] = job_data
                    logger.info(f"[OK] Job {job_id} loaded from DB into memory")
                else:
                    logger.error(f"[ERROR] Job {job_id} not found in DB either!")
                    return  # Job doesn't exist - can't update
            
            # Now update the progress
            self.jobs[job_id]["processed_files"] = processed
            self.jobs[job_id]["updated_at"] = datetime.now().isoformat()
            
            # [OK] NEW: Save to persistent storage
            self.job_storage.save_job(self.jobs[job_id])
        
        # Broadcast WebSocket Update (outside lock!)
        asyncio.create_task(self._broadcast_job_update(job_id))
    
    async def _broadcast_job_update(self, job_id: str):
        """Broadcast job update via WebSocket"""
        with self._jobs_lock:  # [OK] Thread-safe read
            # [OK] FIX: Load job from DB if not in memory
            if job_id not in self.jobs:
                job_data = self.job_storage.get_job(job_id)
                if not job_data:
                    return  # Job doesn't exist
            else:
                job_data = self.jobs[job_id].copy()
        
        job_data["type"] = "job_update"
        await ws_manager.broadcast_job_update(job_data)
    
    def set_job_metrics(self, job_id: str, metrics: Dict):
        """Set Job Metrics with Persistent Storage"""
        with self._jobs_lock:  # [OK] Thread-safe
            if job_id in self.jobs:
                self.jobs[job_id]["metrics"] = metrics
                
                # [OK] NEW: Save to persistent storage
                self.job_storage.save_job(self.jobs[job_id])
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get Job by ID (Memory first, Database fallback)"""
        with self._jobs_lock:  # [OK] Thread-safe
            if job_id in self.jobs:
                return self.jobs.get(job_id).copy()
        
        # [OK] NEW: Fallback to database if not in memory
        return self.job_storage.get_job(job_id)
    
    def list_jobs(self, limit: int = 50) -> List[Dict]:
        """List all Jobs (Database as source of truth)"""
        # [OK] NEW: Get jobs from database (persistent)
        return self.job_storage.list_jobs(limit=limit)

# Global Job Manager
_job_manager: Optional[IngestionJobManager] = None

def get_job_manager() -> IngestionJobManager:
    """Get Global Job Manager (Singleton)"""
    global _job_manager
    if _job_manager is None:
        _job_manager = IngestionJobManager()
    return _job_manager

# ================================================================
# DOCUMENT PROCESSING
# ================================================================

def classify_document_sync(
    file_path: str,
    content: str
) -> Dict[str, Any]:
    """
    [OK] CPU-Intensive Document Classification (synchron für Process Pool)
    
    Wird in separatem Process ausgeführt (keine GIL-Probleme!)
    Nur Klassifizierung + Entity Extraction - KEINE Datenbank-Operationen!
    
    Args:
        file_path: Pfad zur Datei
        content: Datei-Inhalt
    
    Returns:
        Classification-Ergebnis
    """
    import hashlib
    from datetime import datetime
    
    try:
        # Generate unique document ID
        document_id = hashlib.sha256(f"{file_path}:{content[:100]}".encode()).hexdigest()[:16]
        timestamp = datetime.now().isoformat()
        
        # 1. Simple Word-Based Classification
        content_lower = content.lower()
        words = content_lower.split()
        legal_terms = ['gesetz', 'recht', 'paragraph', 'artikel', 'vertrag', 'bgb', 'stgb']
        legal_count = sum(1 for word in words if any(term in word for term in legal_terms))
        
        # 2. Entity Estimation (simple heuristic)
        entities_estimate = len(content) // 300 + legal_count
        
        # 3. Classification Logic (PRIORITY ORDER!)
        classification = "DOCUMENT"  # Default
        
        # Priority 1: Vertrag (most specific)
        if 'vertrag' in content_lower:
            classification = "VERTRAG"
        # Priority 2: Legal Document Types
        elif legal_count > 5:
            if 'urteil' in content_lower or 'beschluss' in content_lower:
                classification = "RECHTSPRECHUNG"
            elif 'gesetz' in content_lower:
                classification = "GESETZ"
            else:
                classification = "RECHTSTEXT"
        
        # 4. Quality Score Calculation
        word_count = len(words)
        quality_score = min(1.0, 
            (len(content) / 1000) * 0.3 +  # Length factor
            (legal_count / max(1, word_count)) * 0.5 +  # Legal terms density
            (0.2 if entities_estimate > 5 else 0.0)  # Entities bonus
        )
        
        return {
            "document_id": document_id,
            "classification": classification,
            "legal_terms_count": legal_count,
            "entities_estimate": entities_estimate,
            "quality_score": quality_score,
            "word_count": word_count,
            "char_count": len(content),
            "timestamp": timestamp
        }
        
    except Exception as e:
        return {
            "document_id": None,
            "classification": "ERROR",
            "legal_terms_count": 0,
            "entities_estimate": 0,
            "quality_score": 0.0,
            "word_count": 0,
            "char_count": len(content),
            "error": str(e)
        }


async def process_document_with_uds3(
    file_path: str, 
    content: str, 
    job_manager: IngestionJobManager
) -> Dict[str, Any]:
    """
    [OK] UDS3 Document Processing mit Process Pool für CPU-intensive Tasks
    
    Architektur:
    1. Process Pool: Klassifizierung + Entity Extraction (CPU-intensiv, keine GIL!)
    2. Direct Database Writes: PostgreSQL + CouchDB + ChromaDB + Neo4j (I/O-bound, async)
    
    Returns:
        Verarbeitungs-Metriken
    """
    if not job_manager.uds3_strategy:
        raise RuntimeError("UDS3 Strategy not available")
    
    # [OK] STEP 1: CPU-intensive Classification im Process Pool
    loop = asyncio.get_event_loop()
    
    try:
        # Execute classification in Process Pool (separate process, no GIL!)
        classification_result = await loop.run_in_executor(
            cpu_executor,
            classify_document_sync,
            file_path,
            content
        )
        
        # Extract results
        document_id = classification_result.get("document_id")
        classification = classification_result.get("classification", "DOCUMENT")
        legal_count = classification_result.get("legal_terms_count", 0)
        entities_estimate = classification_result.get("entities_estimate", 0)
        quality_score = classification_result.get("quality_score", 0.0)
        timestamp = classification_result.get("timestamp")
        word_count = classification_result.get("word_count", 0)
        
        # [OK] STEP 2: Multi-Database Writes (UDS3 Polyglot Persistence)
        db_results = {}
        
        # 1. PostgreSQL (Relational Master Data) - PRIORITY 1
        postgres_batch = getattr(job_manager, 'postgres_batch', None)
        
        if postgres_batch:
            # BATCH MODE: Add to buffer (auto-flush at batch_size)
            try:
                await asyncio.to_thread(
                    postgres_batch.add,
                    document_id=document_id,
                    file_path=file_path,
                    classification=classification,
                    content_length=len(content),
                    legal_count=legal_count,
                    created_at=timestamp,
                    quality_score=quality_score
                )
                db_results["relational"] = "batch_queued"
                logger.debug(f"[BATCH] PostgreSQL queued: {document_id}")
            except Exception as e:
                logger.error(f"[ERROR] PostgreSQL batch add failed: {e}")
                db_results["relational"] = f"error: {str(e)[:50]}"
        elif job_manager.uds3_strategy.db_manager.get_relational_backend():
            # SINGLE MODE: Fallback to direct insert (with Circuit Breaker)
            try:
                # [NEW] Wrap with Circuit Breaker
                breaker_mgr = get_breaker_manager()
                postgres_breaker = breaker_mgr.get_or_create("postgresql")
                
                relational_backend = job_manager.uds3_strategy.db_manager.get_relational_backend()
                
                def _insert_postgresql():
                    """PostgreSQL insert wrapped for circuit breaker"""
                    return relational_backend.insert_document(
                        document_id,
                        file_path,
                        classification,
                        len(content),
                        legal_count,
                        timestamp,
                        quality_score
                    )
                
                # Execute with circuit breaker protection
                await asyncio.to_thread(
                    postgres_breaker.call,
                    _insert_postgresql
                )
                
                db_results["relational"] = "success"
                logger.info(f"[OK] PostgreSQL: {document_id}")
            
            except CircuitBreakerException as e:
                # Circuit open - PostgreSQL unavailable
                error = DatabaseConnectionException(
                    database_type="postgresql",
                    operation="insert_document",
                    context={
                        "document_id": document_id,
                        "file_path": file_path,
                        "circuit_state": str(e)
                    },
                    recovery_hint="PostgreSQL circuit breaker is OPEN. Database may be down or overloaded. Wait for auto-recovery."
                )
                logger.error(error.to_dict())
                db_results["relational"] = "circuit_open"
            
            except Exception as e:
                logger.error(f"[ERROR] PostgreSQL insert failed: {e}")
                db_results["relational"] = f"error: {str(e)[:50]}"
        
        # 2. CouchDB (Full Document Storage) - PRIORITY 2
        couchdb_batch = getattr(job_manager, 'couchdb_batch', None)
        
        if couchdb_batch:
            # BATCH MODE: Add to buffer (auto-flush at batch_size)
            try:
                doc_data = {
                    "file_path": file_path,
                    "content": content,  # Full content!
                    "classification": classification,
                    "legal_terms_count": legal_count,
                    "quality_score": quality_score,
                    "timestamp": timestamp,
                    "word_count": word_count
                }
                await asyncio.to_thread(
                    couchdb_batch.add,
                    doc=doc_data,
                    doc_id=document_id
                )
                db_results["document"] = "batch_queued"
                logger.debug(f"[BATCH] CouchDB queued: {document_id}")
            except Exception as e:
                logger.error(f"[ERROR] CouchDB batch add failed: {e}")
                db_results["document"] = f"error: {str(e)[:50]}"
        elif job_manager.get_document_backend():
            # SINGLE MODE: Fallback to direct insert
            try:
                doc_data = {
                    "file_path": file_path,
                    "content": content,  # Full content!
                    "classification": classification,
                    "legal_terms_count": legal_count,
                    "quality_score": quality_score,
                    "timestamp": timestamp,
                    "word_count": word_count
                }
                await asyncio.to_thread(
                    job_manager.get_document_backend().create_document,
                    doc_data,
                    document_id  # doc_id parameter
                )
                db_results["document"] = "success"
                logger.info(f"[OK] CouchDB: {document_id}")
            except Exception as e:
                logger.error(f"[ERROR] CouchDB insert failed: {e}")
                db_results["document"] = f"error: {str(e)[:50]}"
        
        # 3. ChromaDB (Vector Embeddings) - PRIORITY 3
        if FLAGS.get("KILL_SWITCH_CHROMADB", False):
            logger.warning("[KILL] ChromaDB Kill-Switch aktiv – überspringe Vektoreinfügen")
            db_results["vector"] = "skipped (kill-switch)"
        elif job_manager.get_vector_backend():
            try:
                # Chunk content for better semantic search
                chunks = [content[i:i+500] for i in range(0, len(content), 500)][:10]  # Max 10 chunks
                chunk_count = 0
                
                # [OK] CHECK: Batch Embeddings aktiviert?
                from ingestion.batch_embeddings import (
                    should_use_batch_embeddings,
                    create_batch_generator,
                    get_batch_size,
                    get_use_gpu
                )
                # ChromaDB Batch Insert functions defined at module level (Lines 113-145)
                
                # Decision logging for diagnostics
                logger.info(f"[DEBUG] Embedding mode decision: enable_batch={should_use_batch_embeddings()} chunks={len(chunks)}")
                
                if should_use_batch_embeddings() and len(chunks) > 1:
                    # ═══════════════════════════════════════════════════════════
                    # BATCH MODE: Alle Chunks auf einmal verarbeiten
                    # ═══════════════════════════════════════════════════════════
                    logger.info(f"[START] Batch Embeddings aktiviert (batch_size={get_batch_size()}, chunks={len(chunks)})")
                    
                    try:
                        # Create Batch Generator
                        generator = create_batch_generator(
                            model_name=EMBEDDING_MODEL_NAME,
                            batch_size=get_batch_size(),
                            use_gpu=get_use_gpu()
                        )
                        
                        # Generate ALL embeddings (Batch)
                        logger.debug(f"[SYNC] Generating {len(chunks)} embeddings in batch...")
                        embeddings = generator.generate_embeddings_batch(chunks, normalize=True)
                        logger.debug(f"[OK] Batch generated: {len(embeddings)} embeddings")
                        
                        # ═══════════════════════════════════════════════════════════
                        # ChromaDB Insert: BATCH vs SINGLE Mode
                        # ═══════════════════════════════════════════════════════════
                        if should_use_batch_insert():
                            # BATCH INSERT MODE (Expected: +700% performance!)
                            logger.info(f"[START] ChromaDB Batch Insert aktiviert (batch_size={get_batch_insert_size()})")
                            
                            # Synchronous batch insert in thread pool
                            def batch_insert_sync():
                                chunk_count_local = 0
                                
                                # Create Batch Inserter; we will flush explicitly to ensure stats reflect writes
                                with ChromaBatchInserter(
                                    chromadb_backend=job_manager.get_vector_backend(),
                                    batch_size=get_batch_insert_size(),
                                    auto_flush=False
                                ) as batch_inserter:
                                    
                                    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                                        chunk_id = f"{document_id}_chunk_{idx}"
                                        metadata = {
                                            "file_path": file_path,
                                            "classification": classification,
                                            "chunk_index": idx,
                                            "document_id": document_id,
                                            "embedding_model": EMBEDDING_MODEL_NAME,
                                            "batch_processed": True,
                                            "batch_insert": True
                                        }
                                        
                                        # Add to buffer (auto-flush at batch_size)
                                        batch_inserter.add_vector(chunk_id, vector, metadata)
                                        chunk_count_local += 1

                                    # Ensure remaining vectors are flushed before reading stats
                                    batch_inserter.flush()
                                    stats = batch_inserter.get_stats()
                                    return chunk_count_local, stats
                            
                            # Run batch insert in thread pool (non-blocking)
                            chunk_count, stats = await asyncio.to_thread(batch_insert_sync)
                            
                            logger.info(f"[OK] ChromaDB Batch Insert: {document_id} ({chunk_count} chunks)")
                            logger.info(f"[CHART] Batch Statistics: {stats}")
                        
                        else:
                            # SINGLE INSERT MODE (Legacy - individual API calls)
                            logger.info(f"[DEBUG] Using Single Insert Mode (chunks={len(chunks)})")
                            
                            # [NEW] Get Circuit Breaker
                            breaker_mgr = get_breaker_manager()
                            chromadb_breaker = breaker_mgr.get_or_create("chromadb")
                            
                            for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                                chunk_id = f"{document_id}_chunk_{idx}"
                                metadata = {
                                    "file_path": file_path,
                                    "classification": classification,
                                    "chunk_index": idx,
                                    "document_id": document_id,
                                    "embedding_model": EMBEDDING_MODEL_NAME,
                                    "batch_processed": True,
                                    "batch_insert": False
                                }
                                
                                # [NEW] ChromaDB API: add_vector() with Circuit Breaker
                                def _add_vector():
                                    return job_manager.get_vector_backend().add_vector(
                                        chunk_id,  # vector_id (first parameter)
                                        vector,     # vector embedding (second parameter)
                                        metadata   # metadata dict (third parameter)
                                    )
                                
                                try:
                                    success = await asyncio.to_thread(
                                        chromadb_breaker.call,
                                        _add_vector
                                    )
                                    
                                    if success:
                                        chunk_count += 1
                                
                                except CircuitBreakerException:
                                    # Circuit open - skip this chunk
                                    logger.warning(f"[CIRCUIT] ChromaDB circuit open - skipping chunk {idx}")
                                    continue
                        
                        logger.info(f"[OK] ChromaDB Batch: {document_id} ({chunk_count} chunks)")
                        
                    except Exception as batch_error:
                        logger.error(f"[ERROR] Batch Embeddings failed: {batch_error}, fallback to single")
                        # Fallback zu Single Processing (siehe unten)
                        raise batch_error
                
                else:
                    # ═══════════════════════════════════════════════════════════
                    # SINGLE MODE: Chunks einzeln verarbeiten (Legacy/Fallback)
                    # ═══════════════════════════════════════════════════════════
                    logger.info(f"[SYNC] Single Embeddings Mode (chunks={len(chunks)})")
                    
                    # [OK] Load embedding model (lazy loading)
                    embedding_model = load_embedding_model()
                    
                    for idx, chunk in enumerate(chunks):
                        chunk_id = f"{document_id}_chunk_{idx}"
                        
                        # [OK] REAL EMBEDDINGS: sentence-transformers statt Hash
                        if embedding_model != "FALLBACK":
                            # Echte semantische Embeddings (384-dim)
                            embedding = embedding_model.encode(chunk, convert_to_numpy=True)
                            vector = embedding.tolist()
                            logger.debug(f"[OK] Real embedding generated: {len(vector)}-dim")
                        else:
                            # Fallback: Hash-based vector (nur wenn sentence-transformers nicht verfügbar)
                            import hashlib
                            # MD5 used for vector generation only (not security), usedforsecurity=False
                            chunk_hash = hashlib.md5(chunk.encode(), usedforsecurity=False).hexdigest()  # nosec B324
                            vector = [float(int(chunk_hash[i:i+2], 16)) / 255.0 for i in range(0, 32, 1)]
                            vector = vector[:384] + [0.0] * (384 - len(vector))
                            logger.debug(f"[WARNING] Fallback hash-based vector: {len(vector)}-dim")
                        
                        metadata = {
                            "file_path": file_path,
                            "classification": classification,
                            "chunk_index": idx,
                            "document_id": document_id,
                            "embedding_model": EMBEDDING_MODEL_NAME if embedding_model != "FALLBACK" else "hash-fallback",
                            "batch_processed": False
                        }
                        
                        # [NEW] ChromaDB API: add_vector() with Circuit Breaker
                        breaker_mgr = get_breaker_manager()
                        chromadb_breaker = breaker_mgr.get_or_create("chromadb")
                        
                        def _add_vector():
                            """ChromaDB add_vector wrapped for circuit breaker"""
                            return job_manager.get_vector_backend().add_vector(
                                chunk_id,  # vector_id (first parameter)
                                vector,     # vector embedding (second parameter)
                                metadata   # metadata dict (third parameter)
                            )
                        
                        try:
                            success = await asyncio.to_thread(
                                chromadb_breaker.call,
                                _add_vector
                            )
                            
                            if success:
                                chunk_count += 1
                        
                        except CircuitBreakerException:
                            # Circuit open - skip this chunk, continue processing
                            logger.warning(f"[CIRCUIT] ChromaDB circuit open - skipping chunk {idx}")
                            continue
                    
                    logger.info(f"[OK] ChromaDB Single: {document_id} ({chunk_count} chunks)")
                
                db_results["vector"] = f"success ({chunk_count} chunks)"
                logger.info(f"[OK] ChromaDB: {document_id} ({chunk_count} chunks)")
            
            except ConnectionError as e:
                # ChromaDB connection failed
                error = DatabaseConnectionException(
                    database_type="chromadb",
                    operation="add_vector",
                    context={
                        "document_id": document_id,
                        "file_path": file_path,
                        "chunks_count": len(chunks),
                        "error": str(e)
                    },
                    recovery_hint="Verify ChromaDB server is running on configured port. Check CHROMA_HOST/CHROMA_PORT in .env"
                )
                logger.error(error.to_dict())
                db_results["vector"] = f"error: connection failed"
            
            except Exception as e:
                # Wrap unexpected ChromaDB errors
                error = DatabaseWriteException(
                    database_type="chromadb",
                    operation="add_vector",
                    context={
                        "document_id": document_id,
                        "file_path": file_path,
                        "chunks_count": len(chunks),
                        "error": str(e)
                    },
                    recovery_hint="Check ChromaDB logs for details. Document processing will continue without vectors."
                )
                logger.error(error.to_dict())
                db_results["vector"] = f"error: {str(e)[:50]}"
        
        # 4. Neo4j (Graph Relationships) - PRIORITY 4
        if job_manager.get_graph_backend():
            try:
                # UDS3RelationsCore hat driver - nutze session für Cypher
                relations_core = job_manager.get_graph_backend()
                
                # Neo4j Backend speichert Driver in _driver (private attribute)
                neo4j_driver = getattr(relations_core, '_driver', None) or getattr(relations_core, 'driver', None)
                
                if neo4j_driver:
                    # Check if Neo4j Batch Mode is enabled
                    neo4j_batch = getattr(job_manager, 'neo4j_batch', None)
                    
                    if neo4j_batch:
                        # BATCH MODE: Add node to batch (deferred creation)
                        # Note: Neo4j batch uses UNWIND, so we add node data to batch
                        # The batch creator expects relationships, but for nodes we can use
                        # a custom method or accumulate node creation queries
                        
                        # For now, create node immediately and use batch for relationships
                        # This is because Neo4jBatchCreator is designed for relationships
                        # Node creation is typically less frequent and less of a bottleneck
                        
                        # Create Document Node in Neo4j via driver.session()
                        create_node_query = """
                        MERGE (d:Document {id: $doc_id})
                        SET d.file_path = $file_path,
                            d.classification = $classification,
                            d.legal_terms_count = $legal_terms_count,
                            d.quality_score = $quality_score,
                            d.created_at = $timestamp
                        RETURN d.id as id
                        """
                        
                        params = {
                            "doc_id": document_id,
                            "file_path": file_path,
                            "classification": classification,
                            "legal_terms_count": legal_count,
                            "quality_score": quality_score,
                            "timestamp": timestamp
                        }
                        
                        # [NEW] Execute via driver.session() with Circuit Breaker
                        breaker_mgr = get_breaker_manager()
                        neo4j_breaker = breaker_mgr.get_or_create("neo4j")
                        
                        def execute_cypher():
                            with neo4j_driver.session() as session:
                                result = session.run(create_node_query, params)
                                return result.single()
                        
                        result = await asyncio.to_thread(
                            neo4j_breaker.call,
                            execute_cypher
                        )
                        
                        db_results["graph"] = "success (batch mode)"
                        logger.info(f"[OK] Neo4j Batch: {document_id} (node created, relationships batched)")
                    else:
                        # SINGLE MODE: Direct insert (original behavior) with Circuit Breaker
                        create_node_query = """
                        MERGE (d:Document {id: $doc_id})
                        SET d.file_path = $file_path,
                            d.classification = $classification,
                            d.legal_terms_count = $legal_terms_count,
                            d.quality_score = $quality_score,
                            d.created_at = $timestamp
                        RETURN d.id as id
                        """
                        
                        params = {
                            "doc_id": document_id,
                            "file_path": file_path,
                            "classification": classification,
                            "legal_terms_count": legal_count,
                            "quality_score": quality_score,
                            "timestamp": timestamp
                        }
                        
                        # [NEW] Execute via driver.session() with Circuit Breaker
                        breaker_mgr = get_breaker_manager()
                        neo4j_breaker = breaker_mgr.get_or_create("neo4j")
                        
                        def execute_cypher():
                            with neo4j_driver.session() as session:
                                result = session.run(create_node_query, params)
                                return result.single()
                        
                        result = await asyncio.to_thread(
                            neo4j_breaker.call,
                            execute_cypher
                        )
                        
                        db_results["graph"] = "success"
                        logger.info(f"[OK] Neo4j Single: {document_id}")
                else:
                    db_results["graph"] = "skipped (driver not available)"
                    logger.warning("[WARNING] Neo4j driver not available")
            
            except CircuitBreakerException as e:
                # Circuit open - Neo4j unavailable
                error = DatabaseConnectionException(
                    database_type="neo4j",
                    operation="create_node",
                    context={
                        "document_id": document_id,
                        "file_path": file_path,
                        "circuit_state": str(e)
                    },
                    recovery_hint="Neo4j circuit breaker is OPEN. Database may be down or overloaded. Wait for auto-recovery."
                )
                logger.error(error.to_dict())
                db_results["graph"] = "circuit_open"
            
            except ConnectionError as e:
                # Neo4j connection failed
                error = DatabaseConnectionException(
                    database_type="neo4j",
                    operation="create_node",
                    context={
                        "document_id": document_id,
                        "file_path": file_path,
                        "error": str(e)
                    },
                    recovery_hint="Verify Neo4j server is running. Check NEO4J_URI in .env. Test with: cypher-shell"
                )
                logger.error(error.to_dict())
                db_results["graph"] = "error: connection failed"
            
            except Exception as e:
                # Wrap unexpected Neo4j errors
                error = DatabaseWriteException(
                    database_type="neo4j",
                    operation="create_node",
                    context={
                        "document_id": document_id,
                        "file_path": file_path,
                        "error": str(e)
                    },
                    recovery_hint="Check Neo4j logs and Cypher syntax. Document processing will continue without graph data."
                )
                logger.error(error.to_dict())
                db_results["graph"] = f"error: {str(e)[:50]}"
        
        # ═══════════════════════════════════════════════════════════
        # LEGAL GRAPH NLP: Extract legal entities and persist to graph
        # ═══════════════════════════════════════════════════════════
        legal_nlp_results = {}
        if should_use_legal_graph_nlp():
            try:
                from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
                from ingestion.graph.entity_graph_writer import EntityGraphWriter
                from collections import Counter
                
                # Extract legal entities (Tier 1 - Regex)
                extractor = LegalEntityExtractor()
                entities = extractor.extract(content)
                
                # Persist to Neo4j via UDS3
                writer = EntityGraphWriter()  # Uses UDS3Gateway internally
                
                # Process extracted entities
                entity_stats = Counter()
                for entity in entities:
                    if entity.kind == "norm":
                        # Upsert LegalNorm node
                        norm_id = entity.value.lower().replace(" ", "_")
                        writer.upsert_legal_norm(
                            norm_id=norm_id,
                            norm_text=entity.value,
                            law_abbreviation=entity.meta.get("law"),
                            paragraph=entity.meta.get("paragraph"),
                        )
                        # Link document to norm
                        writer.link_cites_norm(
                            document_id=document_id,
                            norm_id=norm_id,
                            count=1,
                            context=entity.meta.get("context_window"),
                        )
                        entity_stats["norms"] += 1
                    
                    elif entity.kind == "aktenzeichen":
                        # Upsert LegalConcept node (Az. as concept)
                        concept_id = f"az_{entity.value.lower().replace(' ', '_')}"
                        writer.upsert_legal_concept(
                            concept_id=concept_id,
                            name=f"Aktenzeichen: {entity.value}",
                            tier=1,
                            context_window=entity.meta.get("context_window"),
                        )
                        writer.link_mentions_concept(
                            document_id=document_id,
                            concept_id=concept_id,
                            count=1,
                        )
                        entity_stats["aktenzeichen"] += 1
                    
                    elif entity.kind == "ecli":
                        # Upsert LegalConcept node (ECLI as concept)
                        concept_id = entity.value.lower()
                        writer.upsert_legal_concept(
                            concept_id=concept_id,
                            name=f"ECLI: {entity.value}",
                            tier=1,
                            context_window=entity.meta.get("context_window"),
                        )
                        writer.link_mentions_concept(
                            document_id=document_id,
                            concept_id=concept_id,
                            count=1,
                        )
                        entity_stats["ecli"] += 1
                
                legal_nlp_results = {
                    "entities_extracted": len(entities),
                    "entities_by_kind": dict(entity_stats),
                    "extraction_tier": 1,  # Regex
                }
                logger.info(f"[LEGAL_NLP] Extracted {len(entities)} entities from {document_id}: {dict(entity_stats)}")
            
            except Exception as e:
                logger.error(f"[LEGAL_NLP] Extraction failed for {document_id}: {e}")
                legal_nlp_results = {
                    "error": str(e)[:100],
                    "entities_extracted": 0,
                }
        else:
            legal_nlp_results = {"status": "disabled"}
        
        # ═══════════════════════════════════════════════════════════
        # METRICS: Record document processing success
        # ═══════════════════════════════════════════════════════════
        if METRICS_AVAILABLE and documents_processed:
            documents_processed.inc(labels={"status": "success"})
            logger.debug("[METRICS] Document processed successfully")
        
        return {
            "content_extracted_chars": len(content),
            "ai_entities_found": entities_estimate,
            "metadata_completeness": quality_score,
            "classification": classification,
            "legal_terms_count": legal_count,
            "quality_score": quality_score,
            "database_writes": db_results,
            "legal_nlp": legal_nlp_results,  # NEW: Legal NLP results
            "document_id": document_id,
            "processing_mode": "UDS3_FULL_POLYGLOT"  # All 4 databases!
        }
    
    except FileNotFoundError as e:
        # File disappeared during processing
        error = FileNotFoundException(
            file_path=file_path,
            context={
                "operation": "process_document_with_uds3",
                "error": str(e)
            },
            recovery_hint="File was deleted or moved during processing. Check if file still exists."
        )
        logger.error(error.to_dict())
        
        if METRICS_AVAILABLE and documents_processed:
            documents_processed.inc(labels={"status": "failed"})
        
        return {
            "content_extracted_chars": len(content),
            "ai_entities_found": 0,
            "metadata_completeness": 0.0,
            "classification": "ERROR",
            "error": str(error),
            "processing_mode": "UDS3_FAILED"
        }
    
    except MemoryError as e:
        # Out of memory during processing
        error = MemoryLimitExceededException(
            operation="process_document_with_uds3",
            current_mb=0,  # Would need memory_manager integration
            limit_mb=0,
            context={
                "file_path": file_path,
                "content_size": len(content),
                "error": str(e)
            },
            recovery_hint="Document too large. Consider splitting into smaller chunks or increasing memory limits."
        )
        logger.error(error.to_dict())
        
        if METRICS_AVAILABLE and documents_processed:
            documents_processed.inc(labels={"status": "failed"})
        
        return {
            "content_extracted_chars": len(content),
            "ai_entities_found": 0,
            "metadata_completeness": 0.0,
            "classification": "ERROR",
            "error": str(error),
            "processing_mode": "UDS3_FAILED"
        }
    
    except Exception as e:
        # [SAFETY NET] Catch-all for unexpected errors
        error = wrap_exception(
            e,
            context={
                "operation": "process_document_with_uds3",
                "file_path": file_path,
                "content_size": len(content)
            },
            recovery_hint="Check logs for detailed error trace. Document may require manual investigation."
        )
        logger.error(error.to_dict())
        import traceback
        traceback.print_exc()
        
        # ═══════════════════════════════════════════════════════════
        # METRICS: Record document processing failure
        # ═══════════════════════════════════════════════════════════
        if METRICS_AVAILABLE and documents_processed:
            documents_processed.inc(labels={"status": "failed"})
            logger.debug("[METRICS] Document processing failed")
        
        return {
            "content_extracted_chars": len(content),
            "ai_entities_found": 0,
            "metadata_completeness": 0.0,
            "classification": "ERROR",
            "error": str(error),
            "processing_mode": "UDS3_FAILED"
        }

async def process_document_with_saga(
    file_path: str,
    content: str,
    job_manager: IngestionJobManager
) -> Dict[str, Any]:
    """
    [OK] SAGA-based UDS3 Document Processing with Automatic Rollback
    
    Uses SAGA Pattern to ensure transactional consistency across all 4 databases.
    If ANY database write fails, ALL previous writes are automatically rolled back.
    
    Architecture:
    1. Process Pool: Classification + Entity Extraction (CPU-intensive)
    2. SAGA Orchestrator: Coordinated Database Writes with Compensation
    3. Automatic Rollback: All-or-nothing guarantee
    
    Returns:
        Processing metrics with SAGA transaction status
    """
    if not job_manager.uds3_strategy:
        raise RuntimeError("UDS3 Strategy not available")
    
    # [OK] STEP 1: CPU-intensive Classification in Process Pool
    loop = asyncio.get_event_loop()
    
    try:
        # Execute classification in Process Pool (separate process, no GIL!)
        classification_result = await loop.run_in_executor(
            cpu_executor,
            classify_document_sync,
            file_path,
            content
        )
        
        # Extract results
        document_id = classification_result.get("document_id")
        classification = classification_result.get("classification", "DOCUMENT")
        legal_count = classification_result.get("legal_terms_count", 0)
        entities_estimate = classification_result.get("entities_estimate", 0)
        quality_score = classification_result.get("quality_score", 0.0)
        timestamp = classification_result.get("timestamp")
        word_count = classification_result.get("word_count", 0)
        
        # [OK] STEP 2: Use Production SAGA Orchestrator
        # Clean OOP implementation with PostgreSQL state backend
        from saga.saga_orchestrator_production import SagaOrchestrator
        
        # Get all available backends (via unified getters - Themis or UDS3)
        relational_backend = job_manager.get_relational_backend()
        vector_backend = job_manager.get_vector_backend()
        graph_backend = job_manager.get_graph_backend()
        document_backend = job_manager.get_document_backend()
        
        db_backends = {
            'relational': relational_backend,
            'document': document_backend,
            'vector': vector_backend,
            'graph': graph_backend
        }
        
        # Filter out None backends
        db_backends = {k: v for k, v in db_backends.items() if v is not None}
        
        # Create SAGA Orchestrator with PostgreSQL state backend
        orchestrator = SagaOrchestrator(
            backends=db_backends,
            relational_backend=relational_backend
        )
        
        # [OK] STEP 3: Create SAGA with UDS3's native format
        saga_id = f"ingest_{document_id}"
        
        # Build SAGA steps list
        steps = []
        
        # Step 1: PostgreSQL
        if 'relational' in db_backends:
            steps.append({
                'step_id': f'{saga_id}_pg',
                'backend': 'relational',
                'operation': 'insert',
                'payload': {
                    'document_id': document_id,
                    'file_path': file_path,
                    'classification': classification,
                    'content_length': len(content),
                    'legal_terms_count': legal_count,
                    'timestamp': timestamp,
                    'quality_score': quality_score
                },
                'compensation': 'delete',
                'idempotency_key': f'pg_{document_id}'
            })
        
        # Step 2: CouchDB
        if 'document' in db_backends:
            steps.append({
                'step_id': f'{saga_id}_couch',
                'backend': 'document',
                'operation': 'insert',  # [OK] FIXED: insert instead of create
                'payload': {
                    '_id': document_id,
                    'file_path': file_path,
                    'content': content,
                    'classification': classification,
                    'legal_terms_count': legal_count,
                    'quality_score': quality_score,
                    'timestamp': timestamp,
                    'word_count': word_count
                },
                'compensation': 'delete',
                'idempotency_key': f'couch_{document_id}'
            })
        
        # Step 3: ChromaDB (simplified - store document_id for rollback)
        if 'vector' in db_backends:
            chunks = [content[i:i+500] for i in range(0, len(content), 500)][:10]
            steps.append({
                'step_id': f'{saga_id}_chroma',
                'backend': 'vector',
                'operation': 'insert',  # [OK] FIXED: insert instead of add_batch
                'payload': {
                    'document_id': document_id,
                    'chunks': chunks,
                    'metadata': {
                        'file_path': file_path,
                        'classification': classification,
                        'quality_score': quality_score
                    }
                },
                'compensation': 'delete',
                'idempotency_key': f'chroma_{document_id}'
            })
        
        # Step 4: Neo4j
        if 'graph' in db_backends:
            steps.append({
                'step_id': f'{saga_id}_neo4j',
                'backend': 'graph',
                'operation': 'insert',  # [OK] FIXED: insert instead of create_node
                'payload': {
                    'source_id': document_id,
                    'target_id': 'DOCUMENT_ROOT',  # Link to root node
                    'relation_type': 'IS_DOCUMENT',
                    'properties': {
                        'file_path': file_path,
                        'classification': classification,
                        'legal_terms_count': legal_count,
                        'quality_score': quality_score
                    }
                },
                'compensation': 'delete',
                'idempotency_key': f'neo4j_{document_id}'
            })
        
        # Create SAGA context
        context = {
            'document_id': document_id,
            'file_path': file_path,
            'classification': classification
        }
        
        # [OK] STEP 3: Create SAGA Transaction (Production)
        print(f"\n[SYNC] [SAGA] Creating transaction: {saga_id} ({len(steps)} steps)\n", flush=True)
        logger.info(f"[SYNC] Creating SAGA transaction: {saga_id} ({len(steps)} steps)")
        
        # Convert steps to dict format for production SAGA
        saga_steps_data = []
        for step in steps:
            saga_steps_data.append({
                'step_id': step['step_id'],
                'backend_name': step['backend'],
                'operation': step['operation'],
                'payload': step['payload'],
                'compensation': step['compensation'],
                'idempotency_key': step.get('idempotency_key')
            })
        
        orchestrator.create_saga(saga_id, context, saga_steps_data)
        
        # [OK] STEP 4: Execute SAGA Transaction
        print(f"[START] [SAGA] Executing transaction {saga_id}...\n", flush=True)
        logger.info(f"[SYNC] Executing SAGA transaction {saga_id} ({len(steps)} steps)")
        
        result = await asyncio.to_thread(
            orchestrator.execute_saga,
            saga_id,
            max_retries=2
        )
        
        if result.get('success'):
            print(f"[OK] [SAGA] Transaction completed: {saga_id}\n", flush=True)
            logger.info(f"[OK] SAGA transaction completed: {saga_id}")
            
            return {
                "content_extracted_chars": len(content),
                "ai_entities_found": entities_estimate,
                "metadata_completeness": quality_score,
                "classification": classification,
                "legal_terms_count": legal_count,
                "quality_score": quality_score,
                "document_id": document_id,
                "processing_mode": "SAGA_FULL_POLYGLOT",
                "saga_status": "completed",
                "databases_written": len(steps)
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"[ERROR] [SAGA] Transaction FAILED and rolled back: {saga_id} - {error_msg}\n", flush=True)
            logger.error(f"[ERROR] SAGA transaction failed and rolled back: {saga_id} - {error_msg}")
            
            return {
                "content_extracted_chars": len(content),
                "ai_entities_found": entities_estimate,
                "metadata_completeness": 0.0,
                "classification": classification,
                "error": f"SAGA transaction failed: {error_msg}",
                "processing_mode": "SAGA_FAILED_ROLLBACK",
                "saga_status": "compensated"
            }
        
    except Exception as e:
        logger.error(f"[ERROR] SAGA processing failed for {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "content_extracted_chars": len(content),
            "ai_entities_found": 0,
            "metadata_completeness": 0.0,
            "classification": "ERROR",
            "error": str(e),
            "processing_mode": "SAGA_ERROR"
        }

async def process_single_document(
    file_path: str,
    job_manager: IngestionJobManager,
    job_id: str = None,  # [OK] NEW: Job ID for file tracking
    use_saga: bool = None  # If None, decide via ENV (ENABLE_SAGA)
) -> Dict[str, Any]:
    """
    Verarbeite einzelnes Dokument mit File-Level Tracking
    
    Args:
        file_path: Pfad zur Datei
        job_manager: Job Manager Instanz
        job_id: Job ID für File-Level Tracking in DB
    use_saga: Wenn True, nutze SAGA Pattern; wenn None, via ENV (ENABLE_SAGA)
    
    Returns:
        Verarbeitungs-Metriken
    """
    # [P1 FIX] Semaphore for Connection Pool Protection (21.10.2025)
    # Get semaphore for current event loop (fixes "bound to different event loop" error)
    semaphore = get_processing_semaphore()
    
    async with semaphore:
        # Original processing logic wrapped in semaphore
        try:
            # [OK] NEW: Track file start in database
            if job_id:
                job_manager.job_storage.save_job_file(job_id, file_path, status="processing")
            
            # Lese Datei (in Thread Pool) with explicit file handle management
            loop = asyncio.get_event_loop()
            
            def read_file():
                # [FIX] Explicitly use context manager to ensure file handle is closed
                # Problem: Path.read_text() doesn't guarantee immediate file descriptor release
                # → "Too many open files" error under high concurrency
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                        return f.read()
            
            content = await loop.run_in_executor(io_executor, read_file)
            
            # Decide SAGA usage
            if use_saga is None:
                use_saga = should_use_saga()

            # [OK] Choose processing mode: SAGA (transactional) vs Direct (best-effort)
            if use_saga:
                # SAGA Mode: Transactional consistency with automatic rollback
                metrics = await process_document_with_saga(file_path, content, job_manager)
            else:
                # Direct Mode: Best-effort writes (legacy, faster but no rollback)
                metrics = await process_document_with_uds3(file_path, content, job_manager)
            
            # [OK] NEW: Track file completion in database
            if job_id:
                if metrics.get("error"):
                    job_manager.job_storage.update_job_file_status(
                        job_id, file_path, status="failed", error=metrics["error"]
                    )
                else:
                    job_manager.job_storage.update_job_file_status(
                        job_id, file_path, status="completed"
                    )
            
            logger.info(f"[OK] Processed: {Path(file_path).name} (mode: {metrics.get('processing_mode')})")
            return metrics
            
        except Exception as e:
            logger.error(f"[ERROR] Error processing {file_path}: {e}")
            
            # [OK] NEW: Track file error in database
            if job_id:
                job_manager.job_storage.update_job_file_status(
                    job_id, file_path, status="failed", error=str(e)
                )
            
            return {
                "content_extracted_chars": 0,
                "ai_entities_found": 0,
                "metadata_completeness": 0.0,
                "classification": "ERROR",
                "error": str(e)
            }

async def process_documents_batch(
    job_id: str,
    file_paths: List[str],
    temp_dir: Optional[Path]
):
    """
    Background Task für Batch-Verarbeitung
    
    Args:
        job_id: Job ID
        file_paths: Liste von Dateipfaden
        temp_dir: Temporäres Verzeichnis (wird nach Processing gelöscht)
    """
    print(f"\n\n[BOX][BOX][BOX] [BATCH] ENTERED! job_id={job_id}, files={len(file_paths)}\n\n", flush=True)
    
    jm = get_job_manager()
    # Set correlation_id from job context for all logs in this background task
    try:
        job_meta = jm.job_storage.get_job(job_id)
        job_corr = (job_meta or {}).get("correlation_id")
        if job_corr:
            set_correlation_id(job_corr)
    except Exception:
        pass
    
    print(f"[OK] [BATCH] Got job_manager: {jm}\n", flush=True)
    
    try:
        print(f"[SYNC] [BATCH] Starting processing...\n", flush=True)
        logger.info(f"[SYNC] Starting batch processing: Job {job_id}, {len(file_paths)} files")
        
        print(f"[MEMO] [BATCH] Updating job status to 'processing'...\n", flush=True)
        jm.update_job_status(job_id, "processing")
        
        print(f"[OK] [BATCH] Job status updated!\n", flush=True)
        
        # ================================================================
        # PHASE 2: Initialize Batch Inserters (if enabled)
        # ================================================================
        postgres_batch = None
        couchdb_batch = None
        neo4j_batch = None
        
        if BATCH_OPERATIONS_AVAILABLE and should_use_postgres_batch_insert():
            relational_backend = jm.get_relational_backend()
            if relational_backend:
                try:
                    postgres_batch = PostgreSQLBatchInserter(
                        postgresql_backend=relational_backend,
                        batch_size=get_postgres_batch_size()
                    )
                    logger.info("=" * 80)
                    logger.info(f"✅ PostgreSQL Batch Inserter initialized for Job {job_id}")
                    logger.info(f"   Batch Size: {get_postgres_batch_size()}")
                    logger.info(f"   Auto-Flush: Enabled at batch_size")
                    logger.info("=" * 80)
                except Exception as e:
                    logger.warning(f"⚠️ PostgreSQL Batch Inserter initialization failed: {e}")
                    logger.warning("   Falling back to single-insert mode")
        
        if BATCH_OPERATIONS_AVAILABLE and should_use_couchdb_batch_insert():
            # Use unified getter (Themis or UDS3)
            if jm.get_document_backend():
                try:
                    couchdb_batch = CouchDBBatchInserter(
                        couchdb_backend=jm.get_document_backend(),
                        batch_size=get_couchdb_batch_size()
                    )
                    logger.info("=" * 80)
                    logger.info(f"✅ CouchDB Batch Inserter initialized for Job {job_id}")
                    logger.info(f"   Batch Size: {get_couchdb_batch_size()}")
                    logger.info(f"   Auto-Flush: Enabled at batch_size")
                    logger.info("=" * 80)
                except Exception as e:
                    logger.warning(f"⚠️ CouchDB Batch Inserter initialization failed: {e}")
                    logger.warning("   Falling back to single-insert mode")
        
        if BATCH_OPERATIONS_AVAILABLE and should_use_neo4j_batching():
            if jm.get_graph_backend():
                try:
                    neo4j_batch = Neo4jBatchCreator(
                        neo4j_backend=jm.get_graph_backend(),
                        batch_size=get_neo4j_batch_size()
                    )
                    logger.info("=" * 80)
                    logger.info(f"✅ Neo4j Batch Creator initialized for Job {job_id}")
                    logger.info(f"   Batch Size: {get_neo4j_batch_size()}")
                    logger.info(f"   Auto-Flush: Enabled at batch_size")
                    logger.info(f"   Mode: UNWIND with APOC fallback")
                    logger.info("=" * 80)
                except Exception as e:
                    logger.warning(f"⚠️ Neo4j Batch Creator initialization failed: {e}")
                    logger.warning("   Falling back to single-insert mode")
        
        # Store batch inserters in job_manager for access in process_document_with_uds3
        jm.postgres_batch = postgres_batch
        jm.couchdb_batch = couchdb_batch
        jm.neo4j_batch = neo4j_batch
        
        start_time = datetime.now()
        
        # [P1 FIX] Batch Chunking Protection (21.10.2025)
        # Problem: Processing 10,000 files creates 10,000 coroutines + 40,000 DB connections
        # → Memory exhaustion (10+ GB) + Connection pool overflow
        # Solution: Process files in chunks of 100, free memory between chunks
        BATCH_CHUNK_SIZE = int(os.getenv("BATCH_CHUNK_SIZE", 100))
        
        total_files = len(file_paths)
        if total_files > BATCH_CHUNK_SIZE:
            logger.info("=" * 80)
            logger.info(f"[P1] Batch Chunking ENABLED for Job {job_id}")
            logger.info(f"   Total Files: {total_files}")
            logger.info(f"   Chunk Size: {BATCH_CHUNK_SIZE}")
            logger.info(f"   Total Chunks: {(total_files + BATCH_CHUNK_SIZE - 1) // BATCH_CHUNK_SIZE}")
            logger.info("   Protection: Memory + Connection Pool Overflow")
            logger.info("=" * 80)
        
        print(f"[MEMO] [BATCH] Processing {total_files} files in chunks of {BATCH_CHUNK_SIZE}...\n", flush=True)
        
        # Process files in chunks to prevent memory exhaustion
        results = []
        for chunk_idx, i in enumerate(range(0, total_files, BATCH_CHUNK_SIZE), start=1):
            chunk = file_paths[i:i+BATCH_CHUNK_SIZE]
            chunk_size = len(chunk)
            
            logger.info(f"[CHUNK {chunk_idx}] Processing files {i+1}-{i+chunk_size} of {total_files}...")
            print(f"[CHUNK {chunk_idx}] Creating {chunk_size} tasks...\n", flush=True)
            
            # Create tasks for this chunk only
            chunk_tasks = [
                process_single_document(fp, jm, job_id=job_id)
                for fp in chunk
            ]
            
            print(f"[SYNC] [CHUNK {chunk_idx}] Running asyncio.gather()...\n", flush=True)
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
            
            results.extend(chunk_results)
            
            print(f"[OK] [CHUNK {chunk_idx}] Completed! {len(chunk_results)} results\n", flush=True)
            logger.info(f"[CHUNK {chunk_idx}] Completed: {chunk_size} files processed")
            
            # Brief pause between chunks to allow memory cleanup
            if i + BATCH_CHUNK_SIZE < total_files:
                await asyncio.sleep(0.1)
        
        print(f"[OK] [BATCH] All chunks completed! Total results: {len(results)}\n", flush=True)
        
        # Aggregiere Metriken und logge Exceptions
        successful = 0
        failed = 0
        
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                # Exception during processing
                failed += 1
                logger.error(f"[ERROR] File {idx} ({file_paths[idx]}) raised Exception: {result}")
                logger.error(f"[ERROR] Exception type: {type(result).__name__}")
                import traceback
                logger.error(f"[ERROR] Traceback:\n{''.join(traceback.format_exception(type(result), result, result.__traceback__))}")
            elif result.get('error') is not None:
                # Processing returned error
                failed += 1
                logger.error(f"[ERROR] File {idx} ({file_paths[idx]}) returned error: {result.get('error')}")
                logger.error(f"[ERROR] Full result: {result}")
            else:
                # Success
                successful += 1
                logger.debug(f"[OK] File {idx} ({file_paths[idx]}) processed successfully")
        
        print(f"[CHART] [BATCH] Successful: {successful}, Failed: {failed}\n", flush=True)
        
        # [OK] FIXED: Update processed_files counter!
        print(f"[MEMO] [BATCH] Updating job progress: {successful}/{len(file_paths)} files\n", flush=True)
        jm.update_job_progress(job_id, successful)
        print(f"[OK] [BATCH] Job progress updated!\n", flush=True)
        
        total_metrics = {
            "total_files": len(file_paths),
            "successful_files": successful,
            "failed_files": failed,
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "content_extracted_chars": sum(
                r.get('content_extracted_chars', 0) 
                for r in results 
                if not isinstance(r, Exception)
            ),
            "ai_entities_found": sum(
                r.get('ai_entities_found', 0) 
                for r in results 
                if not isinstance(r, Exception)
            ),
        }
        
        jm.set_job_metrics(job_id, total_metrics)
        
        # ================================================================
        # PHASE 2: Flush Batch Inserters & Log Statistics
        # ================================================================
        
        # PostgreSQL Batch Flush
        if postgres_batch:
            try:
                logger.info("=" * 80)
                logger.info(f"[FLUSH] PostgreSQL Batch - Job {job_id}")
                logger.info("=" * 80)
                
                postgres_batch.flush()
                stats = postgres_batch.get_stats()
                
                logger.info(f"[STATS] PostgreSQL Batch Insert Statistics:")
                logger.info(f"   Total Batches:           {stats['total_batches']}")
                logger.info(f"   Total Documents:         {stats['total_documents']}")
                logger.info(f"   Successful Batches:      {stats['successful_batches']}")
                logger.info(f"   Failed Batches:          {stats.get('failed_batches', 0)}")
                logger.info(f"   Fallback Single Inserts: {stats['total_fallbacks']}")
                if stats['total_batches'] > 0:
                    logger.info(f"   Success Rate:            {stats['successful_batches']/stats['total_batches']*100:.1f}%")
                else:
                    logger.info(f"   Success Rate:            N/A")
                logger.info("=" * 80)
                
            except Exception as e:
                logger.error(f"[ERROR] PostgreSQL batch flush failed: {e}")
                logger.error(f"   Some documents may not be persisted!")
        
        # CouchDB Batch Flush
        if couchdb_batch:
            try:
                logger.info("=" * 80)
                logger.info(f"[FLUSH] CouchDB Batch - Job {job_id}")
                logger.info("=" * 80)
                
                couchdb_batch.flush()
                stats = couchdb_batch.get_stats()
                
                logger.info(f"[STATS] CouchDB Batch Insert Statistics:")
                logger.info(f"   Total Batches:           {stats['total_batches']}")
                logger.info(f"   Total Documents:         {stats['total_documents']}")
                logger.info(f"   Successful Batches:      {stats['successful_batches']}")
                logger.info(f"   Failed Batches:          {stats.get('failed_batches', 0)}")
                logger.info(f"   Fallback Single Inserts: {stats['total_fallbacks']}")
                logger.info(f"   Conflicts Handled:       {stats.get('total_conflicts', 0)}")
                if stats['total_batches'] > 0:
                    logger.info(f"   Success Rate:            {stats['successful_batches']/stats['total_batches']*100:.1f}%")
                else:
                    logger.info(f"   Success Rate:            N/A")
                logger.info("=" * 80)
                
            except Exception as e:
                logger.error(f"[ERROR] CouchDB batch flush failed: {e}")
                logger.error(f"   Some documents may not be persisted!")
        
        # Neo4j Batch Flush
        if neo4j_batch:
            try:
                logger.info("=" * 80)
                logger.info(f"[FLUSH] Neo4j Batch - Job {job_id}")
                logger.info("=" * 80)
                
                neo4j_batch.flush()
                stats = neo4j_batch.get_stats()
                
                logger.info(f"[STATS] Neo4j Batch Create Statistics:")
                logger.info(f"   Total Batches:           {stats['total_batches']}")
                logger.info(f"   Total Relationships:     {stats['total_created']}")
                logger.info(f"   Fallback Single Creates: {stats['total_fallbacks']}")
                logger.info(f"   Pending in Buffer:       {stats['pending']}")
                if stats['total_batches'] > 0:
                    avg_per_batch = stats['total_created'] / stats['total_batches']
                    logger.info(f"   Avg per Batch:           {avg_per_batch:.1f}")
                logger.info("=" * 80)
                
            except Exception as e:
                logger.error(f"[ERROR] Neo4j batch flush failed: {e}")
                logger.error(f"   Some relationships may not be persisted!")
        
        jm.update_job_status(job_id, "completed")
        
        logger.info(f"[OK] Batch completed: {successful}/{len(file_paths)} files in {total_metrics['processing_time']:.2f}s")
        
        # [OK] FIX: Only cleanup temp directory on SUCCESS
        # This allows recovery from partial failures
        if temp_dir and temp_dir.exists():
            logger.info(f"🗑️ Cleaning up temp directory after successful processing: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        logger.error(f"[ERROR] Batch processing failed: {e}")
        jm.update_job_status(job_id, "failed", str(e))
        
        # [OK] FIX: Keep temp directory on failure for crash recovery!
        if temp_dir and temp_dir.exists():
            logger.error(f"[ERROR] Processing failed, temp files kept for recovery: {temp_dir}")
            logger.error(f"   To recover: Re-submit files from {temp_dir}")

# ================================================================
# LIFESPAN CONTEXT (FastAPI Startup/Shutdown)
# ================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI startup and shutdown.
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    
    NEW (28.10.2025): Production Hardening Integration
    - WorkerPoolManager for health monitoring
    - MemoryManager for leak detection and limits
    - CircuitBreakers for database fault tolerance
    """
    # STARTUP
    # Set a synthetic correlation ID for startup logs (outside any request context)
    try:
        set_correlation_id("startup:ingestion")
    except Exception:
        pass
    logger.info("=" * 60)
    logger.info("[START] Covina Ingestion Backend Starting")
    logger.info("=" * 60)
    
    # [NEW] Initialize Production Hardening Systems
    logger.info("[HARDENING] Initializing production systems...")
    
    # 1. Worker Pool Manager (health monitoring, crash detection)
    # Note: WorkerPoolManager creates its own executors
    pool_manager = initialize_pool_manager(
        io_workers=IO_WORKERS,
        cpu_workers=CPU_WORKERS,
        health_check_interval=30,  # Check every 30s
        worker_timeout=300,        # 5min worker timeout
        task_timeout=600,          # 10min task timeout
        enable_auto_recovery=False # Manual recovery for safety
    )
    logger.info(f"✅ WorkerPoolManager initialized ({IO_WORKERS} I/O + {CPU_WORKERS} CPU workers)")
    
    # 2. Memory Manager (limits, GC, leak detection)
    memory_manager = initialize_memory_manager(
        soft_limit_mb=4096,       # 4 GB warning limit
        hard_limit_mb=6144,       # 6 GB hard limit
        gc_threshold_mb=3072,     # Auto-GC at 3 GB
        check_interval=30,        # Monitor every 30s
        leak_threshold_mb=512,    # 512 MB growth = leak
        leak_detection_window=300 # 5 minutes (in seconds)
    )
    logger.info(f"✅ MemoryManager initialized (soft: 4GB, hard: 6GB)")
    
    # 3. Circuit Breakers (database fault tolerance)
    breaker_mgr = get_breaker_manager()
    
    # PostgreSQL Circuit Breaker
    postgres_breaker = breaker_mgr.get_or_create(
        "postgresql",
        failure_threshold=5,      # Open after 5 failures
        recovery_timeout=60,      # Try recovery after 60s
        success_threshold=2       # Close after 2 successes
    )
    logger.info("✅ PostgreSQL circuit breaker created")
    
    # ChromaDB Circuit Breaker (more sensitive - embedding service)
    chromadb_breaker = breaker_mgr.get_or_create(
        "chromadb",
        failure_threshold=3,      # Open after 3 failures
        recovery_timeout=30,      # Try recovery after 30s
        success_threshold=2       # Close after 2 successes
    )
    logger.info("✅ ChromaDB circuit breaker created")
    
    # Neo4j Circuit Breaker
    neo4j_breaker = breaker_mgr.get_or_create(
        "neo4j",
        failure_threshold=5,      # Open after 5 failures
        recovery_timeout=60,      # Try recovery after 60s
        success_threshold=2       # Close after 2 successes
    )
    logger.info("✅ Neo4j circuit breaker created")
    
    logger.info("[HARDENING] Production systems initialized ✅")
    
    # Initialize Job Manager (triggers UDS3 setup)
    jm = get_job_manager()
    
    # [OK] Preload Embedding Model (avoid race condition in ProcessPool)
    logger.info("[SYNC] Preloading embedding model...")
    model = load_embedding_model()
    if model and model != "FALLBACK":
        logger.info(f"[OK] Embedding model preloaded: {EMBEDDING_MODEL_NAME}")
    else:
        logger.warning("[WARNING]  Embedding model preload failed - using fallback")
    
    logger.info(f"⚡ Worker Pool: {IO_WORKERS} I/O + {CPU_WORKERS} CPU workers ({CPU_COUNT} total CPUs)")
    logger.info(f"🔌 UDS3 Status: {'[OK] Ready' if jm.uds3_ready else '[ERROR] Not Ready'}")
    logger.info("=" * 60)
    
    # [OK] Auto-Resume pending jobs (NEW - v3.4.9)
    # Start in background task to avoid blocking startup
    asyncio.create_task(auto_resume_pending_jobs(jm))
    logger.info("[SYNC] Auto-resume started in background")
    
    yield  # Application runs here
    
    # SHUTDOWN
    logger.info("[STOP] Covina Ingestion Backend Shutting Down")
    
    # [NEW] Graceful shutdown of production systems
    logger.info("[HARDENING] Shutting down production systems...")
    
    # 0. Cleanup Themis Adapter (if active)
    if THEMIS_AVAILABLE and themis_adapter:
        try:
            await themis_adapter.close()
            logger.info("✅ Themis Adapter geschlossen")
        except Exception as e:
            logger.error(f"❌ Themis Adapter Cleanup Fehler: {e}")
    
    # 1. Stop accepting new tasks
    logger.info("[SHUTDOWN] Stopping new task submissions...")
    
    # 2. Shutdown Worker Pool Manager (waits for tasks, max 30s)
    # Note: WorkerPoolManager handles its own executor shutdown
    shutdown_pool_manager(timeout=30)
    logger.info("✅ WorkerPoolManager shutdown complete (includes executors)")
    
    # 3. Shutdown Memory Manager
    shutdown_memory_manager()
    logger.info("✅ MemoryManager shutdown complete")
    
    # 4. Shutdown original executors (if they still exist and weren't replaced)
    if io_executor is not None:
        try:
            io_executor.shutdown(wait=False)
            logger.info("✅ Original io_executor shutdown")
        except:
            pass
    
    if cpu_executor is not None:
        try:
            cpu_executor.shutdown(wait=False)
            logger.info("✅ Original cpu_executor shutdown")
        except:
            pass
    
    logger.info("[OK] Clean shutdown completed")

# ================================================================
# FASTAPI APPLICATION
# ================================================================

# Rate Limiting Setup (slowapi)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="Covina Ingestion Backend",
    description="Microservice for document ingestion and processing",
    version="1.0.0",
    lifespan=lifespan  # [OK] NEW: Use lifespan instead of on_event
)

# Register Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------
# Phase A - Feature Flag: Neuer Ingestion-Router
# ------------------------------------------------
import os

INGEST_NEW_ROUTER = os.environ.get("INGEST_NEW_ROUTER", "false").lower() in {"1","true","yes","y","on"}

if INGEST_NEW_ROUTER:
    try:
        from ingestionV2.api_v2 import build_v2_router
        app.include_router(build_v2_router())
        logger.info("✅ Neuer Ingestion-Router (v2) aktiviert und eingebunden")
    except Exception as e:
        logger.error(f"❌ Neuer Ingestion-Router konnte nicht aktiviert werden: {e}")
else:
    logger.info("ℹ️ Neuer Ingestion-Router deaktiviert (INGEST_NEW_ROUTER=false)")

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

# ================================================================
# API ENDPOINTS
# ================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check(delay: int = 0):
    """Health Check - Lightweight version (supports ?delay=N for testing active request tracking)"""
    import asyncio
    
    # Optional artificial delay for testing concurrent request tracking
    if delay > 0:
        await asyncio.sleep(min(delay, 5))  # Cap at 5s for safety
    
    # FIXED (17.10.2025, 00:05 Uhr): Removed get_job_manager() call
    # Reason: Triggers UDS3 initialization on first request, causes DB timeout crashes
    
    # Collect Production Hardening Metrics
    hardening_metrics = {}
    
    try:
        # Worker Pool Metrics
        pool_manager = get_pool_manager()
        if pool_manager:
            io_metrics = pool_manager.get_io_metrics()
            cpu_metrics = pool_manager.get_cpu_metrics()
            
            hardening_metrics["worker_pool"] = {
                "io_workers": {
                    "total": pool_manager.io_workers,
                    "active": io_metrics.active_workers,
                    "tasks_completed": io_metrics.tasks_completed,
                    "tasks_failed": io_metrics.tasks_failed,
                    "success_rate": round(io_metrics.success_rate * 100, 1) if io_metrics.success_rate else 0,
                },
                "cpu_workers": {
                    "total": pool_manager.cpu_workers,
                    "active": cpu_metrics.active_workers,
                    "tasks_completed": cpu_metrics.tasks_completed,
                    "tasks_failed": cpu_metrics.tasks_failed,
                    "success_rate": round(cpu_metrics.success_rate * 100, 1) if cpu_metrics.success_rate else 0,
                },
                "health_checks_enabled": True,
                "heartbeat_interval": 30,
                "worker_timeout": 300,
            }
    except Exception as e:
        hardening_metrics["worker_pool"] = {"error": str(e), "status": "not_initialized"}
    
    try:
        # Memory Manager Metrics
        memory_manager = get_memory_manager()
        if memory_manager:
            snapshot = memory_manager.get_current_snapshot()
            
            hardening_metrics["memory"] = {
                "current_mb": round(snapshot.current_mb, 1),
                "soft_limit_mb": memory_manager.soft_limit_mb,
                "hard_limit_mb": memory_manager.hard_limit_mb,
                "usage_percent": round((snapshot.current_mb / memory_manager.hard_limit_mb) * 100, 1),
                "gc_threshold_mb": memory_manager.gc_threshold_mb,
                "leak_detection": {
                    "enabled": True,
                    "window_seconds": memory_manager.leak_detection_window,
                    "threshold_mb": memory_manager.leak_threshold_mb,
                },
                "status": "healthy" if snapshot.current_mb < memory_manager.soft_limit_mb else "warning",
            }
    except Exception as e:
        hardening_metrics["memory"] = {"error": str(e), "status": "not_initialized"}
    
    try:
        # Circuit Breaker Metrics
        breaker_mgr = get_breaker_manager()
        if breaker_mgr:
            circuit_status = {}
            for service_name in ["postgresql", "chromadb", "neo4j"]:
                breaker = breaker_mgr.get_or_create(service_name, failure_threshold=5)
                metrics = breaker.get_metrics()
                
                circuit_status[service_name] = {
                    "state": breaker.state.value,
                    "failure_count": metrics.get("failure_count", 0),
                    "success_count": metrics.get("success_count", 0),
                    "total_calls": metrics.get("total_calls", 0),
                    "last_failure": metrics.get("last_failure_time"),
                    "next_retry": metrics.get("next_retry_time"),
                }
            
            hardening_metrics["circuit_breakers"] = {
                "services": circuit_status,
                "total_services": len(circuit_status),
                "open_circuits": sum(1 for s in circuit_status.values() if s["state"] == "OPEN"),
            }
    except Exception as e:
        hardening_metrics["circuit_breakers"] = {"error": str(e), "status": "not_initialized"}
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        components={
            "uds3": "[INFO] lazy-init (not checked)",
            "vector_db": "[INFO] lazy-init (not checked)",
            "graph_db": "[INFO] lazy-init (not checked)",
            "relational_db": "[INFO] lazy-init (not checked)",
            "document_db": "[INFO] lazy-init (not checked)",
        },
        worker_pool={
            "io_workers": IO_WORKERS,
            "cpu_workers": CPU_WORKERS,
            "total_cpus": CPU_COUNT
        },
        hardening=hardening_metrics if hardening_metrics else None
    )

@app.get("/live")
async def liveness_probe():
    """Einfache Liveness-Probe (keine externen Abhängigkeiten)."""
    return {"status": "alive"}

@app.get("/themis/mode", summary="Themis Adapter Mode", tags=["Themis"])
async def themis_mode():
    """
    Returns Themis adapter configuration status.
    
    Indicates whether Themis is active and backend access details.
    """
    return {
        "enabled": THEMIS_AVAILABLE,
        "url": THEMIS_URL if THEMIS_AVAILABLE else None,
        "timeout": THEMIS_TIMEOUT if THEMIS_AVAILABLE else None,
        "max_retries": THEMIS_MAX_RETRIES if THEMIS_AVAILABLE else None,
        "fallback": "UDS3" if not THEMIS_AVAILABLE else None,
        "backends": {
            "relational": get_job_manager().get_relational_backend() is not None if get_job_manager() else False,
            "vector": get_job_manager().get_vector_backend() is not None if get_job_manager() else False,
            "graph": get_job_manager().get_graph_backend() is not None if get_job_manager() else False,
            "document": get_job_manager().get_document_backend() is not None if get_job_manager() else False
        }
    }

@app.get("/themis/health", summary="Themis Health Check", tags=["Themis"])
async def themis_health():
    """
    Performs health check against Themis adapter.
    
    Pings Themis API and returns latency + status.
    """
    if not THEMIS_AVAILABLE or not themis_adapter:
        raise HTTPException(
            status_code=503,
            detail="Themis not available (USE_THEMIS=false or initialization failed)"
        )
    
    import time
    start = time.perf_counter()
    try:
        health_status = await themis_adapter.health()
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "themis_response": health_status
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        raise HTTPException(
            status_code=503,
            detail=f"Themis health check failed: {str(e)}",
            headers={"X-Latency-Ms": str(round(latency_ms, 2))}
        )

@app.get("/metrics")
async def metrics_endpoint():
    """
    Metrics Endpoint - Exposes internal metrics in JSON format.
    
    Provides business and performance metrics without Prometheus dependency.
    Compatible with custom monitoring solutions and dashboards.
    """
    if not METRICS_AVAILABLE:
        return {
            "status": "metrics_disabled",
            "message": "Metrics system not initialized"
        }
    
    # Update pool metrics before export
    update_pool_metrics()
    
    return metrics_registry.export_dict()

@app.get("/prometheus", response_class=PlainTextResponse)
async def prometheus_endpoint():
    """
    Prometheus Metrics Endpoint - Exposes production hardening metrics.
    
    Returns metrics in Prometheus exposition format for scraping by
    Prometheus server or compatible monitoring tools.
    
    Metrics exposed:
    - Worker pool: tasks, success rates, active workers
    - Memory: usage, limits, GC stats, leak detection
    - Circuit breakers: states, calls, failures per service
    
    Example:
        curl http://127.0.0.1:45679/prometheus
    """
    try:
        # Collect hardening metrics (same as /health endpoint)
        hardening_metrics = {}
        
        # Worker Pool Metrics
        try:
            pool_manager = get_pool_manager()
            if pool_manager:
                io_metrics = pool_manager.get_io_metrics()
                cpu_metrics = pool_manager.get_cpu_metrics()
                
                hardening_metrics["worker_pool"] = {
                    "io_workers": {
                        "total": pool_manager.io_workers,
                        "active": io_metrics.active_workers,
                        "tasks_completed": io_metrics.tasks_completed,
                        "tasks_failed": io_metrics.tasks_failed,
                        "success_rate": round(io_metrics.success_rate * 100, 1) if io_metrics.success_rate else 0,
                    },
                    "cpu_workers": {
                        "total": pool_manager.cpu_workers,
                        "active": cpu_metrics.active_workers,
                        "tasks_completed": cpu_metrics.tasks_completed,
                        "tasks_failed": cpu_metrics.tasks_failed,
                        "success_rate": round(cpu_metrics.success_rate * 100, 1) if cpu_metrics.success_rate else 0,
                    },
                    "health_checks_enabled": True,
                    "heartbeat_interval": 30,
                    "worker_timeout": 300,
                }
        except Exception as e:
            hardening_metrics["worker_pool"] = {"error": str(e), "status": "not_initialized"}
        
        # Memory Metrics
        try:
            memory_manager = get_memory_manager()
            if memory_manager:
                snapshot = memory_manager.get_current_snapshot()
                
                hardening_metrics["memory"] = {
                    "current_mb": round(snapshot.current_mb, 1),
                    "soft_limit_mb": memory_manager.soft_limit_mb,
                    "hard_limit_mb": memory_manager.hard_limit_mb,
                    "usage_percent": round((snapshot.current_mb / memory_manager.hard_limit_mb) * 100, 1),
                    "gc_threshold_mb": memory_manager.gc_threshold_mb,
                    "leak_detection": {
                        "enabled": True,
                        "window_seconds": memory_manager.leak_detection_window,
                        "threshold_mb": memory_manager.leak_threshold_mb,
                    },
                    "status": "healthy" if snapshot.current_mb < memory_manager.soft_limit_mb else "warning",
                }
        except Exception as e:
            hardening_metrics["memory"] = {"error": str(e), "status": "not_initialized"}
        
        # Circuit Breaker Metrics
        try:
            breaker_mgr = get_breaker_manager()
            if breaker_mgr:
                circuit_status = {}
                for service_name in ["postgresql", "chromadb", "neo4j"]:
                    breaker = breaker_mgr.get_or_create(service_name, failure_threshold=5)
                    metrics = breaker.get_metrics()
                    
                    circuit_status[service_name] = {
                        "state": breaker.state.value,
                        "failure_count": metrics.get("failure_count", 0),
                        "success_count": metrics.get("success_count", 0),
                        "total_calls": metrics.get("total_calls", 0),
                        "last_failure": metrics.get("last_failure_time"),
                        "next_retry": metrics.get("next_retry_time"),
                    }
                
                hardening_metrics["circuit_breakers"] = {
                    "services": circuit_status,
                    "total_services": len(circuit_status),
                    "open_circuits": sum(1 for s in circuit_status.values() if s["state"] == "OPEN"),
                }
        except Exception as e:
            hardening_metrics["circuit_breakers"] = {"error": str(e), "status": "not_initialized"}
        
        # Export to Prometheus format
        prometheus_exporter = get_prometheus_exporter(namespace="covina_ingestion")
        prometheus_text = prometheus_exporter.export_metrics(hardening_metrics)
        
        return prometheus_text
        
    except Exception as e:
        logger.error(f"[PROMETHEUS] Export failed: {e}", exc_info=True)
        return f"# Error exporting metrics: {e}\n"

@app.get("/ready")
async def readiness_probe():
    """Readiness-Probe: konservativ 'ready', da Upload-Service modular ist.
    In Produktionsumgebungen kann hier optional auf konkrete Abhängigkeiten
    (z. B. Filesystem-Zugriff, Worker-Initialisierung) geprüft werden.
    """
    return {"ready": True, "notes": "basic readiness (no hard dependencies checked)"}

# ------------------------------------------------
# Capabilities: Supported file types for upload
# ------------------------------------------------
@app.get("/capabilities/supported-filetypes")
async def get_supported_filetypes():
    """Return supported file extensions per category and as a flat list.

    Data source:
    - ingestion.scanner suffix sets (TEXT/OFFICE/IMAGE/GEO/CODE/ARCHIVE)
    - filtered by categories that have a registered handler
    """
    try:
        # Import suffix sets locally to avoid hard dependency at module import time
        from ingestion.scanner import (
            _TEXT_SUFFIXES,
            _OFFICE_SUFFIXES,
            _IMAGE_SUFFIXES,
            _GEO_SUFFIXES,
            _CODE_SUFFIXES,
            _ARCHIVE_SUFFIXES,
        )

        categories_map = {
            FileCategory.TEXT.value: sorted(_TEXT_SUFFIXES),
            FileCategory.OFFICE.value: sorted(_OFFICE_SUFFIXES),
            FileCategory.IMAGE.value: sorted(_IMAGE_SUFFIXES),
            FileCategory.GEO.value: sorted(_GEO_SUFFIXES),
            FileCategory.CODE.value: sorted(_CODE_SUFFIXES),
            FileCategory.ARCHIVE.value: sorted(_ARCHIVE_SUFFIXES),
        }

        # Only include categories that actually have a handler registered
        registered = {cat.value for cat in HANDLER_FACTORY.registry.snapshot().keys()}
        filtered = {k: v for k, v in categories_map.items() if k in registered}

        all_ext = sorted({ext for exts in filtered.values() for ext in exts})

        return {
            "categories": filtered,
            "all_extensions": all_ext,
            "registered_categories": sorted(registered),
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[CAPABILITIES] failed to enumerate supported filetypes: {e}")
        # Fallback: minimal safe default
        fallback = [
            ".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls",
            ".csv", ".json", ".xml", ".html", ".md", ".rtf",
        ]
        return {
            "categories": {"text": fallback},
            "all_extensions": sorted(set(fallback)),
            "registered_categories": [],
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }

# Admin: Flags/Kill-Switches
class FlagUpdate(BaseModel):
    value: bool = Field(..., description="Neuer Flag-Wert (true/false)")

@app.get("/admin/flags")
async def list_flags(
    _principal: "Principal" = Depends(require_roles([Role.admin])) if AUTH_AVAILABLE else None,
):
    return {"flags": FLAGS}

@app.post("/admin/flags/{name}")
async def set_flag(
    name: str,
    update: FlagUpdate,
    _principal: "Principal" = Depends(require_roles([Role.admin])) if AUTH_AVAILABLE else None,
):
    if name not in FLAGS:
        raise HTTPException(status_code=404, detail=f"Unbekanntes Flag: {name}")
    FLAGS[name] = bool(update.value)
    if name == "KILL_SWITCH_CHROMADB":
        if FLAGS[name]:
            logger.warning("🛑 KILL-SWITCH aktiviert: ChromaDB-Writes werden ab sofort blockiert")
        else:
            logger.info("✅ KILL-SWITCH aufgehoben: ChromaDB-Writes wieder erlaubt")
    return {"flag": name, "value": FLAGS[name]}

@app.post("/upload/files", response_model=UploadResponse)
@limiter.limit("10/minute")  # Max 10 uploads pro Minute pro IP
async def upload_files(
    request: Request,  # Required by slowapi
    files: List[UploadFile] = File(...),
    _principal: "Principal" = Depends(require_roles([Role.user, Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """Upload und verarbeite mehrere Dateien"""
    if not files:
        raise HTTPException(status_code=400, detail="Keine Dateien hochgeladen")
    
    jm = get_job_manager()
    
    # [OK] FIX: Persistent temp directory for crash recovery
    # Use job_id in path for easy identification
    temp_base = Path("data/uploads")
    temp_base.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory first (for job metadata)
    import time
    timestamp = int(time.time())
    temp_job_id = str(uuid.uuid4())[:8]  # Short ID for directory name
    temp_dir = temp_base / f"job_{temp_job_id}_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # [OK] NEW: Create job with temp_directory tracking
    job_id = jm.create_job(len(files), temp_directory=str(temp_dir))
    
    file_paths = []
    
    try:
        # [OK] FIX: Stream files to disk without loading into RAM
        for file in files:
            file_path = temp_dir / file.filename
            
            # Stream file content directly to disk (chunk by chunk)
            # This prevents loading entire file into memory!
            with open(file_path, "wb") as f:
                # Read in 64KB chunks to minimize memory usage
                while chunk := await file.read(65536):  # 64KB chunks
                    f.write(chunk)
            
            file_paths.append(str(file_path))
            logger.info(f"[INBOX] Streamed to disk: {file.filename} → {file_path}")
        
        logger.info(f"[OK] All {len(files)} files streamed to: {temp_dir}")
        
        # Background processing starten via ThreadPoolExecutor with new event loop
        def run_batch_in_new_loop():
            """Run batch processing in new event loop (thread-safe!)"""
            logger.info(f"[START] [BACKGROUND THREAD] Starting batch job {job_id} in new event loop")
            # Propagate correlation ID from job meta for this thread's context
            try:
                jmeta = jm.job_storage.get_job(job_id)
                if jmeta and jmeta.get("correlation_id"):
                    set_correlation_id(jmeta.get("correlation_id"))
            except Exception:
                pass
            
            # Create NEW event loop for this thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            
            try:
                # Run batch in new loop
                new_loop.run_until_complete(process_documents_batch(job_id, file_paths, temp_dir))
                logger.info(f"[OK] [BACKGROUND THREAD] Batch job {job_id} completed")
                
                # [P0 FIX] CRITICAL: Wait for ALL pending tasks before closing loop!
                # Problem: Child tasks (WebSocket, DB writes) still running when loop closes
                # → RuntimeError: Event loop is closed
                # Solution: Wait for all pending tasks to complete
                pending = asyncio.all_tasks(new_loop)
                if pending:
                    logger.info(f"⏳ [BACKGROUND THREAD] Waiting for {len(pending)} pending tasks...")
                    new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    logger.info(f"[OK] [BACKGROUND THREAD] All {len(pending)} tasks completed!")
                
            except Exception as e:
                logger.error(f"[ERROR] [BACKGROUND THREAD] Batch job {job_id} failed: {e}", exc_info=True)
            finally:
                new_loop.close()
        
        # [NEW] Use WorkerPoolManager instead of direct executor
        pool_manager = get_pool_manager()
        task_id = f"upload_batch_{job_id}_{int(time.time())}"
        
        pool_manager.submit_io_task(
            run_batch_in_new_loop,
            task_id=task_id
        )
        
        logger.info(f"[OUTBOX] Upload successful: Job {job_id}, {len(files)} files, Task: {task_id}")
        
        return UploadResponse(
            message=f"Upload erfolgreich. {len(files)} Dateien werden verarbeitet.",
            job_id=job_id,
            file_count=len(files),
            estimated_processing_time=f"{len(files) * 2}s"
        )
    
    except FileNotFoundError as e:
        # File disappeared during upload
        error = FileNotFoundException(
            file_path=str(e),
            context={
                "operation": "upload_files",
                "job_id": job_id,
                "temp_dir": str(temp_dir),
                "files_count": len(files)
            },
            recovery_hint="Verify file still exists and has not been moved/deleted during upload"
        )
        logger.error(error.to_dict())
        jm.update_job_status(job_id, "failed", str(error))
        raise HTTPException(status_code=404, detail=str(error))
    
    except PermissionError as e:
        # Permission denied on temp directory or file
        error = FileProcessingException(
            message=f"Permission denied: {e}",
            file_path=str(temp_dir),
            context={
                "operation": "upload_files",
                "job_id": job_id,
                "temp_dir": str(temp_dir),
                "error": str(e)
            },
            recovery_hint="Check file/directory permissions. Backend needs write access to data/uploads/"
        )
        logger.error(error.to_dict())
        jm.update_job_status(job_id, "failed", str(error))
        raise HTTPException(status_code=403, detail=str(error))
    
    except OSError as e:
        # Disk full, I/O error, etc.
        error = FileProcessingException(
            message=f"I/O error during upload: {e}",
            file_path=str(temp_dir),
            context={
                "operation": "upload_files",
                "job_id": job_id,
                "temp_dir": str(temp_dir),
                "files_count": len(files),
                "error": str(e)
            },
            recovery_hint="Check disk space and filesystem health. Files kept at: " + str(temp_dir)
        )
        logger.error(error.to_dict())
        jm.update_job_status(job_id, "failed", str(error))
        raise HTTPException(status_code=507, detail=str(error))  # 507 = Insufficient Storage
    
    except Exception as e:
        # [SAFETY NET] Catch-all for unexpected errors (wrapped with context)
        error = wrap_exception(
            e,
            context={
                "operation": "upload_files",
                "job_id": job_id,
                "temp_dir": str(temp_dir),
                "files_count": len(files)
            },
            recovery_hint=f"Files kept for recovery at: {temp_dir}"
        )
        logger.error(error.to_dict())
        jm.update_job_status(job_id, "failed", str(error))
        raise HTTPException(status_code=500, detail=str(error))

@app.post("/upload/directory", response_model=DirectoryScanResponse)
@limiter.limit("5/minute")  # Max 5 directory scans pro Minute pro IP
async def upload_directory(
    request: Request,  # Required by slowapi
    directory_path: str = Form(...),
    chunk_size: int = Form(50),
    _principal: "Principal" = Depends(require_roles([Role.user, Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Start directory upload (async with instant response)
    
    Returns scan_job_id immediately (<50ms), scan runs in background.
    Use /scan/{scan_job_id} to check status or listen to WebSocket for updates.
    
    Args:
        directory_path: Path to directory
        chunk_size: Number of files per upload job (default: 50)
    
    Returns:
        DirectoryScanResponse with scan_job_id (instant!)
    """
    logger.info(f"📂 [API] Directory upload request: {directory_path}")
    
    # URL-Dekodierung
    decoded_path = unquote(directory_path)
    
    # Sanitize common Windows/drag&drop wrappers (quotes/braces) and trim whitespace
    sanitized_path = decoded_path.strip().strip('"').strip("'")
    if sanitized_path.startswith("{") and sanitized_path.endswith("}"):
        sanitized_path = sanitized_path[1:-1]
    
    # Normalize path (handles backslashes, trailing slashes, etc.)
    normalized_path = os.path.normpath(sanitized_path)
    if normalized_path != decoded_path:
        logger.info(f"[SCAN] Normalized directory path: '{decoded_path}' -> '{normalized_path}'")
    
    # Validation
    if not os.path.exists(normalized_path):
        raise HTTPException(status_code=404, detail=f"Directory not found: {normalized_path}")
    
    if not os.path.isdir(normalized_path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {normalized_path}")
    
    # Create scan job (instant!)
    sjm = get_scan_job_manager()
    scan_job_id = sjm.create_scan_job(normalized_path, chunk_size)
    scan_job = sjm.get_scan_job(scan_job_id)
    
    # [OK] Start background scan in separate asyncio event loop (thread-safe!)
    def run_scan_in_new_loop():
        """Run scan in new event loop (completely independent from FastAPI)"""
        print(f"\n\n[START][START][START] [BACKGROUND THREAD] Starting scan job {scan_job_id} in new event loop\n\n", flush=True)
        logger.info(f"[START] [BACKGROUND THREAD] Starting scan job {scan_job_id} in new event loop")
        
        # Create NEW event loop for this thread
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        
        print(f"\n\n[OK] [BACKGROUND THREAD] Event loop created, running scan...\n\n", flush=True)
        print(f"\n\n[SEARCH] [DEBUG] About to call run_until_complete()...\n\n", flush=True)
        print(f"\n\n[SEARCH] [DEBUG] scan_job object: {scan_job}\n\n", flush=True)
        print(f"\n\n[SEARCH] [DEBUG] scan_job type: {type(scan_job)}\n\n", flush=True)
        
        try:
            # Run scan in new loop - KEEPS RUNNING for all child tasks!
            print(f"\n\n[BLUE] [DEBUG] Calling scan_and_create_jobs()...\n\n", flush=True)
            coro = scan_job.scan_and_create_jobs()
            print(f"\n\n[BLUE] [DEBUG] Coroutine created: {coro}\n\n", flush=True)
            print(f"\n\n[BLUE] [DEBUG] Coroutine type: {type(coro)}\n\n", flush=True)
            
            new_loop.run_until_complete(coro)
            
            print(f"\n\n[OK] [DEBUG] run_until_complete() returned!\n\n", flush=True)
            print(f"\n\n⏳ [BACKGROUND THREAD] Scan completed - waiting for ALL processing tasks...\n\n", flush=True)
            logger.info(f"⏳ [BACKGROUND THREAD] Scan completed - waiting for ALL processing tasks...")
            
            # [OK] CRITICAL: Wait for ALL pending tasks before closing loop!
            pending = asyncio.all_tasks(new_loop)
            if pending:
                print(f"\n\n⏳ [BACKGROUND THREAD] Waiting for {len(pending)} pending tasks...\n\n", flush=True)
                logger.info(f"⏳ [BACKGROUND THREAD] Waiting for {len(pending)} pending tasks...")
                new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                print(f"\n\n[OK] [BACKGROUND THREAD] All {len(pending)} tasks completed!\n\n", flush=True)
                logger.info(f"[OK] [BACKGROUND THREAD] All tasks completed!")
            
            print(f"\n\n[OK][OK][OK] [BACKGROUND THREAD] Scan job {scan_job_id} fully completed\n\n", flush=True)
            logger.info(f"[OK] [BACKGROUND THREAD] Scan job {scan_job_id} fully completed")
        except Exception as e:
            print(f"\n\n[ERROR] [BACKGROUND THREAD] ERROR: {e}\n\n", flush=True)
            logger.error(f"[ERROR] [BACKGROUND THREAD] Scan job {scan_job_id} failed: {e}", exc_info=True)
            
            # [OK] FIX: Update scan job status so GUI shows error!
            try:
                scan_job.status = "failed"
                scan_job.error_message = str(e)
                # Broadcast error to GUI
                new_loop.run_until_complete(scan_job._broadcast_status())
                logger.info(f"[OK] [BACKGROUND THREAD] Error status broadcast to GUI")
            except Exception as broadcast_error:
                logger.debug(f"Failed to broadcast error status: {broadcast_error}")
        finally:
            new_loop.close()
            print(f"\n\n🔒 [BACKGROUND THREAD] Event loop closed\n\n", flush=True)
    
    # [NEW] Use WorkerPoolManager instead of direct executor
    print(f"\n\n[TARGET] [API] Submitting scan job {scan_job_id} to pool_manager...\n\n", flush=True)
    logger.info(f"[TARGET] [API] Submitting scan job {scan_job_id} to pool_manager...")
    
    pool_manager = get_pool_manager()
    task_id = f"directory_scan_{scan_job_id}_{int(time.time())}"
    
    pool_manager.submit_io_task(
        run_scan_in_new_loop,
        task_id=task_id
    )
    
    print(f"\n\n[OK] [API] Scan job {scan_job_id} submitted successfully (Task: {task_id})\n\n", flush=True)
    
    logger.info(f"[OK] [API] Directory scan started: {scan_job_id} (response time: <50ms)")
    
    # [OK] INSTANT RESPONSE (<50ms)
    return DirectoryScanResponse(
        message="Directory scan started in background",
        scan_job_id=scan_job_id,
        status="scanning",
        directory_path=normalized_path
    )


@app.get("/scan/{scan_job_id}", response_model=DirectoryScanStatusResponse)
async def get_scan_status(scan_job_id: str):
    """
    Get directory scan status
    
    Args:
        scan_job_id: Scan job ID from /upload/directory
    
    Returns:
        DirectoryScanStatusResponse with current status
    """
    sjm = get_scan_job_manager()
    scan_job = sjm.get_scan_job(scan_job_id)
    
    if not scan_job:
        raise HTTPException(status_code=404, detail=f"Scan job not found: {scan_job_id}")
    
    elapsed = (datetime.now() - scan_job.start_time).total_seconds()
    
    return DirectoryScanStatusResponse(
        scan_job_id=scan_job_id,
        status=scan_job.status,
        files_found=scan_job.files_found,
        upload_jobs_created=len(scan_job.upload_jobs_created),
        upload_job_ids=scan_job.upload_jobs_created,
        error=scan_job.error_message,
        elapsed_time=elapsed,
        bulk_copy_progress=getattr(scan_job, 'bulk_copy_progress', None)  # 🆕 NEW!
    )


@app.get("/jobs", response_model=List[JobStatus])
@limiter.limit("30/minute")  # Max 30 job listings pro Minute pro IP
async def list_jobs(request: Request, limit: int = 50):  # Required by slowapi
    """Liste alle Jobs"""
    jobs = get_job_manager().list_jobs(limit)
    return [JobStatus(**job) for job in jobs]

@app.get("/jobs/{job_id}", response_model=JobStatus)
@limiter.limit("60/minute")  # Max 60 job queries pro Minute pro IP
async def get_job(request: Request, job_id: str):  # Required by slowapi
    """Hole Job-Details (Alias für /jobs/{job_id}/status)"""
    job = get_job_manager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return JobStatus(**job)

@app.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Hole Job-Status"""
    job = get_job_manager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return JobStatus(**job)

@app.get("/jobs/{job_id}/metrics", response_model=JobMetrics)
async def get_job_metrics(job_id: str):
    """Hole Job-Metriken"""
    job = get_job_manager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job noch nicht abgeschlossen")
    
    metrics = job.get("metrics", {})
    
    return JobMetrics(
        job_id=job_id,
        total_files=metrics.get("total_files", job["file_count"]),
        successful_files=metrics.get("successful_files", 0),
        failed_files=metrics.get("failed_files", 0),
        processing_time=metrics.get("processing_time", 0.0),
        content_extracted_chars=metrics.get("content_extracted_chars", 0),
        ai_entities_found=metrics.get("ai_entities_found", 0),
        metadata_completeness=0.0,
        classification_stats={},
        backend_metrics={}
    )

@app.get("/jobs/{job_id}/files")
async def get_job_files(job_id: str):
    """
    Get detailed file-level tracking for a job
    
    Returns list of all files in job with individual status:
    - pending: Not yet processed
    - processing: Currently being processed
    - completed: Successfully processed
    - failed: Processing failed (with error message)
    
    Use this for:
    - Detailed audit logs
    - Debugging specific file failures
    - Partial recovery (re-process only failed files)
    """
    jm = get_job_manager()
    
    # Check if job exists
    job = jm.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    # Get file-level tracking
    files = jm.job_storage.get_job_files(job_id)
    
    # Aggregate statistics
    stats = {
        "total": len(files),
        "pending": sum(1 for f in files if f["status"] == "pending"),
        "processing": sum(1 for f in files if f["status"] == "processing"),
        "completed": sum(1 for f in files if f["status"] == "completed"),
        "failed": sum(1 for f in files if f["status"] == "failed")
    }
    
    return {
        "job_id": job_id,
        "job_status": job["status"],
        "file_statistics": stats,
        "files": files
    }

# ================================================================
# RECOVERY ENDPOINTS
# ================================================================

@app.get("/jobs/incomplete")
async def get_incomplete_jobs():
    """
    Get all incomplete jobs for manual recovery
    
    Returns jobs with status 'pending' or 'processing' that may need recovery
    """
    jm = get_job_manager()
    incomplete = jm.job_storage.get_incomplete_jobs()
    
    return {
        "incomplete_jobs": incomplete,
        "count": len(incomplete),
        "message": "Use /jobs/{job_id}/recover to restart a specific job"
    }

@app.post("/jobs/{job_id}/recover")
async def recover_job(job_id: str):
    """
    Recover an incomplete job from crash
    
    Steps:
    1. Load job metadata from database
    2. Check if temp files exist
    3. Re-submit files for processing
    
    Returns:
        Recovery status and new job ID if successful
    """
    jm = get_job_manager()
    
    # Get job from database
    job = jm.job_storage.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found in database")
    
    if job["status"] in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job already {job['status']}, no recovery needed"
        )
    
    # Check if temp directory exists
    temp_directory = job.get("temp_directory")
    
    if not temp_directory:
        raise HTTPException(
            status_code=400,
            detail="No temp directory found for this job - cannot recover"
        )
    
    temp_path = Path(temp_directory)
    
    if not temp_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Temp directory not found: {temp_directory}"
        )
    
    # Get list of files in temp directory
    file_paths = [str(f) for f in temp_path.glob("*") if f.is_file()]
    
    if not file_paths:
        raise HTTPException(
            status_code=400,
            detail=f"No files found in temp directory: {temp_directory}"
        )
    
    logger.info(f"[SYNC] Recovering job {job_id}: {len(file_paths)} files in {temp_directory}")
    
    # Create new job for recovery
    new_job_id = jm.create_job(len(file_paths), temp_directory=temp_directory)
    
    # Submit for processing
    def run_recovery_in_new_loop():
        """Background recovery processing"""
        logger.info(f"[START] [RECOVERY] Starting job {new_job_id} in new event loop")
        
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        
        try:
            new_loop.run_until_complete(process_documents_batch(new_job_id, file_paths, temp_path))
            logger.info(f"[OK] [RECOVERY] Job {new_job_id} completed")
        except Exception as e:
            logger.error(f"[ERROR] [RECOVERY] Job {new_job_id} failed: {e}", exc_info=True)
        finally:
            new_loop.close()
    
    # [NEW] Use WorkerPoolManager
    pool_manager = get_pool_manager()
    task_id = f"recovery_{new_job_id}_{int(time.time())}"
    
    pool_manager.submit_io_task(
        run_recovery_in_new_loop,
        task_id=task_id
    )
    
    # Update old job status
    jm.update_job_status(job_id, "recovered", f"Recovered as job {new_job_id}")
    
    return {
        "message": "Job recovery started",
        "old_job_id": job_id,
        "new_job_id": new_job_id,
        "files_count": len(file_paths),
        "temp_directory": temp_directory
    }


@app.get("/jobs/{job_id}/failed-files")
async def get_failed_files(job_id: str, max_retries: int = 3):
    """
    Get all failed files that are eligible for recovery
    
    Args:
        job_id: Job ID to check
        max_retries: Maximum retry count filter (default: 3)
    
    Returns:
        List of failed files with retry counts
    """
    jm = get_job_manager()
    
    # Check if job exists
    job = jm.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get failed files
    failed_files = jm.job_storage.get_failed_files(job_id, max_retries=max_retries)
    
    # Get blocked files
    blocked_files = jm.job_storage.get_blocked_files(job_id)
    
    return {
        "job_id": job_id,
        "job_status": job["status"],
        "recovery_eligible": {
            "count": len(failed_files),
            "files": failed_files
        },
        "recovery_blocked": {
            "count": len(blocked_files),
            "files": blocked_files,
            "note": "Requires admin override to unblock"
        },
        "max_retries": max_retries
    }


@app.post("/jobs/{job_id}/recover-failed-files")
async def recover_failed_files(
    job_id: str,
    max_retries: int = 3,
    force_retry: bool = False,
    _principal: "Principal" = Depends(require_roles([Role.user, Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Recover only failed files from a job
    
    Args:
        job_id: Job ID
        max_retries: Maximum retry count before blocking (default: 3)
        force_retry: Force retry even if retry count >= max_retries (requires admin)
    
    Safety Features:
    - Files with retry_count >= max_retries are automatically blocked
    - Critical errors (e.g., corrupted files) can be manually blocked
    - Admin override required to unblock critical errors
    
    Returns:
        Recovery status and new job ID
    """
    jm = get_job_manager()
    
    # Get job from database
    job = jm.job_storage.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found in database")
    
    # Get failed files
    failed_files = jm.job_storage.get_failed_files(job_id, max_retries=max_retries)
    
    if not failed_files:
        return {
            "message": "No failed files eligible for recovery",
            "job_id": job_id,
            "failed_count": 0,
            "note": "All files either completed or blocked from recovery"
        }
    
    logger.info(f"[SYNC] Recovering {len(failed_files)} failed files from job {job_id}")
    
    # Check if files exist
    file_paths = []
    blocked_files = []
    
    for file_info in failed_files:
        file_path = Path(file_info["file_path"])
        
        if not file_path.exists():
            logger.warning(f"[WARNING] File not found: {file_path}")
            jm.job_storage.block_file_recovery(
                job_id, 
                str(file_path), 
                "File not found - deleted or moved"
            )
            blocked_files.append(str(file_path))
            continue
        
        # Check retry count
        if file_info["retry_count"] >= max_retries and not force_retry:
            logger.warning(f"[WARNING] Max retries reached: {file_path}")
            jm.job_storage.block_file_recovery(
                job_id,
                str(file_path),
                f"Max retries ({max_retries}) exceeded"
            )
            blocked_files.append(str(file_path))
            continue
        
        # Check for critical errors that should block recovery
        error_msg = file_info.get("error_message", "").lower()
        critical_keywords = ["corrupted", "malformed", "invalid format", "permission denied"]
        
        if any(keyword in error_msg for keyword in critical_keywords) and not force_retry:
            logger.warning(f"[WARNING] Critical error detected: {file_path}")
            jm.job_storage.block_file_recovery(
                job_id,
                str(file_path),
                f"Critical error: {file_info.get('error_message', 'Unknown')}"
            )
            blocked_files.append(str(file_path))
            continue
        
        file_paths.append(str(file_path))
    
    if not file_paths:
        return {
            "message": "No files eligible for recovery after safety checks",
            "job_id": job_id,
            "failed_count": len(failed_files),
            "blocked_count": len(blocked_files),
            "blocked_files": blocked_files,
            "note": "All files blocked due to missing files, max retries, or critical errors"
        }
    
    # Create new job for recovery
    temp_dir = job.get("temp_directory") or "data/uploads/recovery"
    new_job_id = jm.create_job(len(file_paths), temp_directory=temp_dir, scan_job_id=job_id)
    
    # Reset file status for retry
    for file_path in file_paths:
        jm.job_storage.reset_file_status(job_id, file_path, new_status="pending")
        jm.job_storage.increment_retry_count(job_id, file_path)
    
    # Submit for processing
    def run_recovery_in_new_loop():
        """Background recovery processing"""
        logger.info(f"[START] [RECOVERY] Starting failed files recovery {new_job_id}")
        
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        
        try:
            new_loop.run_until_complete(
                process_documents_batch(new_job_id, file_paths, Path(file_paths[0]).parent)
            )
            logger.info(f"[OK] [RECOVERY] Job {new_job_id} completed")
        except Exception as e:
            logger.error(f"[ERROR] [RECOVERY] Job {new_job_id} failed: {e}", exc_info=True)
        finally:
            new_loop.close()
    
    # [NEW] Use WorkerPoolManager
    pool_manager = get_pool_manager()
    task_id = f"failed_recovery_{new_job_id}_{int(time.time())}"
    
    pool_manager.submit_io_task(
        run_recovery_in_new_loop,
        task_id=task_id
    )
    
    return {
        "message": "Failed files recovery started",
        "original_job_id": job_id,
        "recovery_job_id": new_job_id,
        "files_to_recover": len(file_paths),
        "blocked_files": len(blocked_files),
        "blocked_file_list": blocked_files if blocked_files else None,
        "max_retries": max_retries
    }


@app.post("/jobs/{job_id}/files/{file_path:path}/unblock")
async def unblock_file_recovery(
    job_id: str,
    file_path: str,
    admin_override: bool = False,
    _principal: "Principal" = Depends(require_roles([Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Unblock a file from recovery (requires admin override)
    
    Args:
        job_id: Job ID
        file_path: File path (URL-encoded)
        admin_override: Admin confirmation (must be true)
    
    Security:
        Requires explicit admin_override=true to prevent accidental unblocking
    
    Returns:
        Unblock status
    """
    jm = get_job_manager()
    
    if not admin_override:
        raise HTTPException(
            status_code=403,
            detail="Admin override required. Set admin_override=true to confirm."
        )
    
    # Get job
    job = jm.job_storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Unblock file
    success = jm.job_storage.unblock_file_recovery(job_id, file_path, admin_override=True)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to unblock file")
    
    logger.info(f"[OK] [ADMIN] Unblocked file: {file_path} (job: {job_id})")
    
    return {
        "message": "File unblocked successfully",
        "job_id": job_id,
        "file_path": file_path,
        "action": "unblocked",
        "note": "File is now eligible for recovery. Use /jobs/{job_id}/recover-failed-files to retry."
    }


@app.get("/recovery/blocked-files")
async def get_all_blocked_files(
    _principal: "Principal" = Depends(require_roles([Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Get all recovery-blocked files across all jobs
    
    Returns:
        List of all blocked files with details
    """
    jm = get_job_manager()
    
    blocked_files = jm.job_storage.get_blocked_files()
    
    # Group by job_id
    by_job = {}
    for file in blocked_files:
        job_id = file["job_id"]
        if job_id not in by_job:
            by_job[job_id] = []
        by_job[job_id].append(file)
    
    return {
        "total_blocked": len(blocked_files),
        "jobs_affected": len(by_job),
        "blocked_by_job": by_job,
        "blocked_files": blocked_files
    }

# ================================================================
# WEBSOCKET ENDPOINT
# ================================================================

@app.websocket("/ws/jobs")
async def websocket_jobs_endpoint(websocket: WebSocket):
    """
    WebSocket Endpoint für Real-Time Job Updates
    
    Connection: ws://127.0.0.1:45679/ws/jobs
    
    Messages Format:
    {
        "type": "job_update",
        "job_id": "uuid",
        "status": "processing|completed|failed",
        "file_count": 10,
        "processed_files": 5,
        "updated_at": "2025-10-11T16:40:00"
    }
    """
    await ws_manager.connect(websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "WebSocket verbunden - Real-Time Job Updates aktiv",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                
                # Echo back (ping-pong for connection health)
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"[ERROR] WebSocket error: {e}")
                break
    
    finally:
        await ws_manager.disconnect(websocket)

# ================================================================
# AUTO-RESUME MECHANISM (v3.4.9)
# ================================================================

async def auto_resume_pending_jobs(jm):
    """
    Auto-resume pending jobs on startup
    
    Strategy:
    1. Find pending jobs with 0 processed files
    2. Check if files exist in database (job_files table)
    3. Re-submit files for processing
    
    This handles crash recovery where jobs were created but never started.
    """
    try:
        # Get pending jobs
        pending_jobs = [
            j for j in jm.jobs.values() 
            if j["status"] == "pending" and j["processed_files"] == 0
        ]
        
        if not pending_jobs:
            logger.info("[OK] No pending jobs - clean start")
            return
        
        logger.info(f"[SYNC] Found {len(pending_jobs)} pending jobs - starting auto-resume...")
        
        resumed_count = 0
        failed_count = 0
        ghost_count = 0
        
        for job in pending_jobs:
            job_id = job["job_id"]
            file_count = job["file_count"]
            
            try:
                # Get files from database
                files = jm.job_storage.get_job_files(job_id)
                
                if not files:
                    logger.warning(f"👻 Ghost Job {job_id}: No files in database - marking as failed")
                    jm.update_job_status(job_id, status="failed", error="Ghost job: No files uploaded")
                    ghost_count += 1
                    failed_count += 1
                    continue
                
                # Filter files that are not completed
                pending_files = [
                    f for f in files 
                    if f.get("status") not in ["completed", "success"]
                ]
                
                if not pending_files:
                    logger.info(f"[OK] Job {job_id}: All files already completed - marking job as completed")
                    jm.update_job_status(job_id, status="completed")
                    resumed_count += 1
                    continue
                
                # Extract file paths
                file_paths = [f["file_path"] for f in pending_files]
                
                logger.info(f"   [START] Auto-resuming job {job_id}: {len(file_paths)}/{file_count} files to process")
                
                # Update job status to processing
                jm.update_job_status(job_id, status="processing")
                
                # Submit for background processing
                def run_resume_in_new_loop():
                    """Background resume processing"""
                    # Use synthetic correlation id for auto-resume per job
                    try:
                        set_correlation_id(f"auto-resume:{job_id}")
                    except Exception:
                        pass
                    logger.info(f"[START] [AUTO-RESUME] Starting job {job_id} in new event loop")
                    
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    try:
                        new_loop.run_until_complete(process_documents_batch(job_id, file_paths, Path(".")))
                        logger.info(f"[OK] [AUTO-RESUME] Job {job_id} completed")
                    except Exception as e:
                        logger.error(f"[ERROR] [AUTO-RESUME] Job {job_id} failed: {e}", exc_info=True)
                    finally:
                        new_loop.close()
                
                # [NEW] Use WorkerPoolManager
                pool_manager = get_pool_manager()
                task_id = f"auto_resume_{job_id}_{int(time.time())}"
                
                pool_manager.submit_io_task(
                    run_resume_in_new_loop,
                    task_id=task_id
                )
                
                resumed_count += 1
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to auto-resume job {job_id}: {e}")
                failed_count += 1
        
        logger.info("=" * 60)
        logger.info(f"[CHART] Auto-Resume Summary:")
        logger.info(f"   [OK] Resumed:     {resumed_count}")
        logger.info(f"   👻 Ghost jobs:  {ghost_count}")
        logger.info(f"   [ERROR] Failed:      {failed_count - ghost_count}")
        logger.info(f"   [INFO] Total:       {len(pending_jobs)}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"[ERROR] Auto-resume failed: {e}", exc_info=True)

# ================================================================
# CHUNKED UPLOAD ENDPOINTS (NEW - v3.5.0)
# ================================================================

from ingestion.upload_chunked import (
    ChunkedUploadStartRequest,
    ChunkedUploadStartResponse,
    ChunkUploadResponse,
    ChunkedUploadStatusResponse,
    ChunkedUploadFinalizeResponse,
    get_chunked_upload_handler
)

from ingestion.upload_websocket import (
    get_websocket_upload_handler
)

@app.post("/upload/chunked/start", response_model=ChunkedUploadStartResponse)
async def start_chunked_upload(
    request: ChunkedUploadStartRequest,
    _principal: "Principal" = Depends(require_roles([Role.user, Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Start chunked file upload session
    
    Returns upload_id and chunk configuration.
    Client should then upload chunks via POST /upload/chunked/{upload_id}/chunk/{chunk_index}
    """
    handler = get_chunked_upload_handler()
    return await handler.start_upload(request)


@app.post("/upload/chunked/{upload_id}/chunk/{chunk_index}", response_model=ChunkUploadResponse)
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    chunk: UploadFile = File(...),
    _principal: "Principal" = Depends(require_roles([Role.user, Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Upload single chunk
    
    Args:
        upload_id: Upload session ID (from start_chunked_upload)
        chunk_index: Chunk index (0-based)
        chunk: Binary chunk data
    
    Returns:
        Progress information
    """
    handler = get_chunked_upload_handler()
    return await handler.upload_chunk(upload_id, chunk_index, chunk)


@app.get("/upload/chunked/{upload_id}/status", response_model=ChunkedUploadStatusResponse)
async def get_chunked_upload_status(
    upload_id: str,
    _principal: "Principal" = Depends(require_roles([Role.user, Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Get upload session status
    
    Returns:
        Current upload progress and metadata
    """
    handler = get_chunked_upload_handler()
    return await handler.get_upload_status(upload_id)


@app.post("/upload/chunked/{upload_id}/finalize", response_model=ChunkedUploadFinalizeResponse)
async def finalize_chunked_upload(
    upload_id: str,
    _principal: "Principal" = Depends(require_roles([Role.user, Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Finalize upload: merge chunks, create processing job
    
    Call this after all chunks uploaded.
    Server will merge chunks and start document processing.
    
    Returns:
        Finalization status with job_id
    """
    handler = get_chunked_upload_handler()
    jm = get_job_manager()
    return await handler.finalize_upload(upload_id, job_manager=jm)


@app.delete("/upload/chunked/{upload_id}")
async def cancel_chunked_upload(
    upload_id: str,
    _principal: "Principal" = Depends(require_roles([Role.user, Role.manager, Role.admin])) if AUTH_AVAILABLE else None,
):
    """
    Cancel upload session
    
    Deletes all chunks and session metadata.
    """
    handler = get_chunked_upload_handler()
    await handler.cancel_upload(upload_id)
    return {"status": "cancelled", "upload_id": upload_id}

# ================================================================
# WEBSOCKET UPLOAD ENDPOINT
# ================================================================

@app.websocket("/ws/upload")
async def websocket_upload_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for bidirectional file uploads
    
    Features:
    - Real-time binary streaming
    - Server-side pause/resume/cancel control
    - Reconnection with resume from last chunk
    - Multiple files over single connection
    - Heartbeat keep-alive
    
    Protocol:
    - JSON control messages (text frames)
    - Binary chunks (binary frames)
    
    See ingestion/upload_websocket.py for full protocol documentation.
    """
    # Get client IP
    client_ip = websocket.client.host if websocket.client else "unknown"
    
    # Get handler and job manager
    handler = get_websocket_upload_handler()
    jm = get_job_manager()
    
    # Handle connection
    await handler.handle_connection(websocket, client_ip, job_manager=jm)

# ================================================================
# MAIN
# ================================================================
# MAIN
# ================================================================
# MAIN ENTRY POINT
# ================================================================

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments  
    parser = argparse.ArgumentParser(description="Covina Ingestion Backend")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=45679, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Log level")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Covina Ingestion Backend")
    logger.info("=" * 60)
    logger.info(f"  Host: {args.host}")
    logger.info(f"  Port: {args.port}")
    logger.info(f"  Log-Level: {args.log_level.upper()}")
    logger.info(f"  Worker Pool: {IO_WORKERS} I/O + {CPU_WORKERS} CPU")
    logger.info("=" * 60)
    
    # Start uvicorn server with explicit config to avoid module loading issues
    # (ingestion package exists, so "ingestion:app" string would load wrong module)
    import uvicorn
    config = uvicorn.Config(
        app=app,  # Pass app object directly
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        access_log=True
    )
    server = uvicorn.Server(config)
    import asyncio
    asyncio.run(server.serve())
