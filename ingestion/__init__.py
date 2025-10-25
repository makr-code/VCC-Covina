"""
Covina Ingestion Module

Main ingestion module for document processing, classification, and storage.
Provides handlers, scanners, and services for multi-format document ingestion.

Version: 3.4.10
Status: Production Ready
"""

__version__ = "3.4.10"
__author__ = "Covina Team"
__status__ = "Production"

# Core exports for easy import
__all__ = [
    # Handlers
    "HandlerFactory",
    "HandlerContext", 
    
    # File Processing
    "DirectoryScanner",
    "FileClassifier",
    "FileCategory",
    "FileEventType",
    
    # Services
    "BatchEmbeddings",
    "DocumentClassificationService",
    "JobPersistence",
]

# Optional imports (graceful degradation if modules unavailable)
try:
    from .handlers.factory import HandlerFactory
    from .handlers.base import HandlerContext
    HANDLERS_AVAILABLE = True
except ImportError:
    HandlerFactory = None
    HandlerContext = None
    HANDLERS_AVAILABLE = False

try:
    from .scanner import DirectoryScanner, FileClassifier
    from .file_events import FileCategory, FileEventType
    SCANNER_AVAILABLE = True
except ImportError:
    DirectoryScanner = None
    FileClassifier = None
    FileCategory = None
    FileEventType = None
    SCANNER_AVAILABLE = False

try:
    from .batch_embeddings import BatchEmbeddings
    BATCH_EMBEDDINGS_AVAILABLE = True
except ImportError:
    BatchEmbeddings = None
    BATCH_EMBEDDINGS_AVAILABLE = False

try:
    from .uds3_document_classification_service import DocumentClassificationService
    CLASSIFICATION_AVAILABLE = True
except ImportError:
    DocumentClassificationService = None
    CLASSIFICATION_AVAILABLE = False

try:
    from .job_persistence import JobPersistence
    PERSISTENCE_AVAILABLE = True
except ImportError:
    JobPersistence = None
    PERSISTENCE_AVAILABLE = False