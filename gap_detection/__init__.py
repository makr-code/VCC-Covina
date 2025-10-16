# -*- coding: utf-8 -*-
"""
Gap Detection Package Init

Initialisierung des Knowledge Gap Detection Packages mit allen
Haupt-Komponenten und Utilities.

Autor: Covina Team
Lizenz: AGPL-3.0
"""

from .core import GapDetectionEngine
from .database import KnowledgeGapDB
from .vpb_process_mining import VPBProcessMiner
from .nlp_pipeline import GermanLegalNLP
from .scheduler import GapDetectionScheduler
from .monitoring_dashboard import GapMonitoringDashboard

# Version information
__version__ = "1.0.0"
__author__ = "Covina Team"
__license__ = "AGPL-3.0"

# Package exports
__all__ = [
    # Core components
    "GapDetectionEngine",
    "KnowledgeGapDB", 
    "VPBProcessMiner",
    "GermanLegalNLP",
    
    # Scheduling and monitoring
    "GapDetectionScheduler",
    "GapMonitoringDashboard",
    
    # Version info
    "__version__",
    "__author__",
    "__license__"
]

# Package-level configuration
DEFAULT_CONFIG = {
    "database": {
        "path": "./data/knowledge_gaps.db",
        "backup_enabled": True,
        "cleanup_days": 90
    },
    "detection": {
        "default_batch_size": 100,
        "max_file_size_mb": 50,
        "supported_formats": [".xml", ".json", ".md", ".txt", ".pdf"]
    },
    "nlp": {
        "model_name": "dbmdz/bert-base-german-cased",
        "max_sequence_length": 512,
        "confidence_threshold": 0.7
    },
    "scheduler": {
        "default_interval": "daily",
        "max_concurrent_jobs": 3,
        "retry_attempts": 2
    }
}

def get_version() -> str:
    """Get package version"""
    return __version__

def get_default_config() -> dict:
    """Get default package configuration"""
    return DEFAULT_CONFIG.copy()

def create_detection_engine(config: dict = None) -> GapDetectionEngine:
    """
    Create a configured gap detection engine
    
    Args:
        config: Optional configuration dict
        
    Returns:
        Configured GapDetectionEngine instance
    """
    
    if config is None:
        config = get_default_config()
    
    return GapDetectionEngine(config)

def create_scheduler(config: dict = None) -> GapDetectionScheduler:
    """
    Create a configured gap detection scheduler
    
    Args:
        config: Optional configuration dict
        
    Returns:
        Configured GapDetectionScheduler instance
    """
    
    if config is None:
        config = get_default_config()
    
    return GapDetectionScheduler(config)

def create_dashboard() -> GapMonitoringDashboard:
    """
    Create a monitoring dashboard instance
    
    Returns:
        GapMonitoringDashboard instance
    """
    
    return GapMonitoringDashboard()

# Initialize package logging
import logging

# Create package logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add console handler if not already present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)

logger.info(f"Gap Detection Package v{__version__} initialized")

# Package health check
def health_check() -> dict:
    """
    Perform package health check
    
    Returns:
        Dict with health status information
    """
    
    health_status = {
        "package_version": __version__,
        "components": {},
        "dependencies": {},
        "overall_status": "healthy"
    }
    
    try:
        # Check core components
        health_status["components"]["GapDetectionEngine"] = "available"
        health_status["components"]["KnowledgeGapDB"] = "available" 
        health_status["components"]["VPBProcessMiner"] = "available"
        health_status["components"]["GermanLegalNLP"] = "available"
        health_status["components"]["GapDetectionScheduler"] = "available"
        health_status["components"]["GapMonitoringDashboard"] = "available"
        
        # Check key dependencies
        try:
            import sqlite3
            health_status["dependencies"]["sqlite3"] = "available"
        except ImportError:
            health_status["dependencies"]["sqlite3"] = "missing"
            health_status["overall_status"] = "degraded"
        
        try:
            import asyncio
            health_status["dependencies"]["asyncio"] = "available"
        except ImportError:
            health_status["dependencies"]["asyncio"] = "missing" 
            health_status["overall_status"] = "degraded"
        
        try:
            import tkinter
            health_status["dependencies"]["tkinter"] = "available"
        except ImportError:
            health_status["dependencies"]["tkinter"] = "missing"
            health_status["overall_status"] = "degraded"
        
        # Check optional dependencies
        try:
            import transformers
            health_status["dependencies"]["transformers"] = "available"
        except ImportError:
            health_status["dependencies"]["transformers"] = "missing"
        
        try:
            import pm4py
            health_status["dependencies"]["pm4py"] = "available"
        except ImportError:
            health_status["dependencies"]["pm4py"] = "missing"
        
        try:
            import matplotlib
            health_status["dependencies"]["matplotlib"] = "available"
        except ImportError:
            health_status["dependencies"]["matplotlib"] = "missing"
    
    except Exception as e:
        health_status["overall_status"] = "error"
        health_status["error"] = str(e)
    
    return health_status

# Package initialization check
try:
    _health = health_check()
    if _health["overall_status"] == "error":
        logger.error(f"Package initialization error: {_health.get('error')}")
    elif _health["overall_status"] == "degraded":
        logger.warning("Package initialized with missing optional dependencies")
    else:
        logger.info("Package initialization successful")
except Exception as e:
    logger.error(f"Health check failed: {e}")