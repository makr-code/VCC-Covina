"""
Backend Factory - UDS3 Database Backend Initialization
=======================================================

Factory pattern für die Initialisierung von UDS3 Database Backends
analog zu main_backend.py Pattern.

Features:
- Verwendet uds3.database.config für Konfiguration
- Manuelle Backend-Instanziierung (wie in main_backend.py)
- Connection Pooling (PostgreSQL)
- Error Handling & Logging
- Singleton Pattern für Backend-Sharing

Author: VCC-Covina Team
Version: 1.0.0
Date: 2025-10-24
"""

import logging
import sys
import os
from typing import Dict, Any, Optional

# Add UDS3 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uds3'))

from uds3.database.config import (
    database_manager,
    DatabaseType,
    DatabaseBackend,
    get_vector_database,
    get_graph_database,
    get_relational_database
)

logger = logging.getLogger(__name__)


class BackendFactory:
    """Singleton Factory für UDS3 Database Backends."""
    
    _instance = None
    _backends_initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Backend Factory (Singleton)."""
        if not self._backends_initialized:
            self.postgres_backend = None
            self.chromadb_backend = None
            self.neo4j_backend = None
            self.couchdb_backend = None
            
            self._init_backends()
            self._backends_initialized = True
    
    def _init_backends(self):
        """Initialize all UDS3 backends using config.py."""
        logger.info("=" * 80)
        logger.info("🔧 UDS3 Backend Factory - Initialization")
        logger.info("=" * 80)
        
        # PostgreSQL Backend
        self._init_postgresql()
        
        # ChromaDB Backend
        self._init_chromadb()
        
        # Neo4j Backend
        self._init_neo4j()
        
        # CouchDB Backend (optional)
        self._init_couchdb()
        
        logger.info("=" * 80)
        logger.info("✅ Backend Factory Initialization Complete")
        logger.info("=" * 80)
        logger.info(f"   PostgreSQL: {'✅ Connected' if self.postgres_backend else '❌ Not available'}")
        logger.info(f"   ChromaDB:   {'✅ Connected' if self.chromadb_backend else '❌ Not available'}")
        logger.info(f"   Neo4j:      {'✅ Connected' if self.neo4j_backend else '❌ Not available'}")
        logger.info(f"   CouchDB:    {'✅ Connected' if self.couchdb_backend else '❌ Not available'}")
        logger.info("=" * 80)
    
    def _init_postgresql(self):
        """Initialize PostgreSQL backend from config."""
        try:
            db_config = get_relational_database()
            if not db_config or not db_config.enabled:
                logger.warning("⚠️ PostgreSQL disabled in config")
                return
            
            # Use pooled backend (analog zu main_backend.py)
            from uds3.database.database_api_postgresql_pooled import PostgreSQLRelationalBackend
            
            pg_config = {
                'host': db_config.host,
                'port': db_config.port,
                'user': db_config.username,
                'password': db_config.password,
                'database': db_config.database,
                'schema': 'public',
                'pool_min': db_config.settings.get('pool_min', 5),
                'pool_max': db_config.settings.get('pool_max', 20),
            }
            
            self.postgres_backend = PostgreSQLRelationalBackend(pg_config)
            self.postgres_backend.connect()
            
            logger.info("✅ PostgreSQL Backend initialized via UDS3 config")
            logger.info(f"   Host: {pg_config['host']}:{pg_config['port']}")
            logger.info(f"   Database: {pg_config['database']}")
        
        except Exception as e:
            logger.error(f"❌ PostgreSQL initialization failed: {e}")
            self.postgres_backend = None
    
    def _init_chromadb(self):
        """Initialize ChromaDB backend from config."""
        try:
            db_config = get_vector_database()
            if not db_config or not db_config.enabled:
                logger.warning("⚠️ ChromaDB disabled in config")
                return
            
            from uds3.database.database_api_chromadb_remote import ChromaRemoteVectorBackend
            
            chroma_config = {
                "collection": db_config.settings.get('index_name', 'covina_documents'),
                "remote": {
                    "host": db_config.host,
                    "port": db_config.port,
                    "protocol": "http"
                },
                "tenant": "default_tenant",
                "database": "default_database"
            }
            
            self.chromadb_backend = ChromaRemoteVectorBackend(chroma_config)
            self.chromadb_backend.connect()
            
            logger.info("✅ ChromaDB Backend initialized via UDS3 config")
            logger.info(f"   Host: {chroma_config['remote']['host']}:{chroma_config['remote']['port']}")
            logger.info(f"   Collection: {chroma_config['collection']}")
        
        except Exception as e:
            logger.error(f"❌ ChromaDB initialization failed: {e}")
            self.chromadb_backend = None
    
    def _init_neo4j(self):
        """Initialize Neo4j backend from config."""
        try:
            db_config = get_graph_database()
            if not db_config or not db_config.enabled:
                logger.warning("⚠️ Neo4j disabled in config")
                return
            
            from uds3.database.database_api_neo4j import Neo4jGraphBackend
            
            neo4j_config = {
                'uri': db_config.get_connection_string(),
                'user': db_config.username,
                'password': db_config.password
            }
            
            self.neo4j_backend = Neo4jGraphBackend(neo4j_config)
            self.neo4j_backend.connect()
            
            logger.info("✅ Neo4j Backend initialized via UDS3 config")
            logger.info(f"   URI: {neo4j_config['uri']}")
        
        except Exception as e:
            logger.error(f"❌ Neo4j initialization failed: {e}")
            self.neo4j_backend = None
    
    def _init_couchdb(self):
        """Initialize CouchDB backend from config (optional)."""
        try:
            # Find CouchDB in config
            db_config = database_manager.get_database_by_backend(DatabaseBackend.COUCHDB)
            if not db_config or not db_config.enabled:
                logger.debug("CouchDB disabled or not configured")
                return
            
            from uds3.database.database_api_couchdb import CouchDBBackend
            
            couch_config = {
                'host': db_config.host,
                'port': db_config.port,
                'username': db_config.username,
                'password': db_config.password,
                'database': db_config.database,
                'protocol': db_config.settings.get('protocol', 'http')
            }
            
            self.couchdb_backend = CouchDBBackend(couch_config)
            self.couchdb_backend.connect()
            
            logger.info("✅ CouchDB Backend initialized via UDS3 config")
            logger.info(f"   Host: {couch_config['host']}:{couch_config['port']}")
        
        except Exception as e:
            logger.debug(f"CouchDB not initialized: {e}")
            self.couchdb_backend = None
    
    def get_postgres(self):
        """Get PostgreSQL backend."""
        return self.postgres_backend
    
    def get_chromadb(self):
        """Get ChromaDB backend."""
        return self.chromadb_backend
    
    def get_neo4j(self):
        """Get Neo4j backend."""
        return self.neo4j_backend
    
    def get_couchdb(self):
        """Get CouchDB backend."""
        return self.couchdb_backend
    
    def is_postgres_available(self) -> bool:
        """Check if PostgreSQL is available."""
        return self.postgres_backend is not None and hasattr(self.postgres_backend, 'pool') and self.postgres_backend.pool is not None
    
    def is_chromadb_available(self) -> bool:
        """Check if ChromaDB is available."""
        return self.chromadb_backend is not None and self.chromadb_backend.is_available()
    
    def is_neo4j_available(self) -> bool:
        """Check if Neo4j is available."""
        return self.neo4j_backend is not None and self.neo4j_backend.is_available()
    
    def is_couchdb_available(self) -> bool:
        """Check if CouchDB is available."""
        return self.couchdb_backend is not None


# Singleton instance
backend_factory = BackendFactory()


# Convenience functions
def get_postgres_backend():
    """Get PostgreSQL backend (singleton)."""
    return backend_factory.get_postgres()


def get_chromadb_backend():
    """Get ChromaDB backend (singleton)."""
    return backend_factory.get_chromadb()


def get_neo4j_backend():
    """Get Neo4j backend (singleton)."""
    return backend_factory.get_neo4j()


def get_couchdb_backend():
    """Get CouchDB backend (singleton)."""
    return backend_factory.get_couchdb()
