#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adaptive Multi-Database Strategy für UDS3 Covina Backend

Implementiert eine flexible Multi-Database Strategie die sich automatisch an verfügbare 
Database-Backends anpasst. Unterstützt administrative Flexibilität für unvorhersehbare
Deployment-Szenarien in Verwaltungsumgebungen.

Features:
- Runtime DB Discovery mit Health Checks
- 5 Fallback-Strategien (full_polyglot bis sqlite_monolith)  
- Automatic Strategy Selection basierend auf verfügbaren DBs
- Compensation Logic für fehlende Database Capabilities
- Zero-Configuration Startup mit optimaler Performance
- Graduelle Migration Paths zwischen Strategien

Autor: Covina Development Team
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
import socket
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# UDS3 Integration
try:
    from .database.database_manager import DatabaseManager
    from .database.config import DatabaseType, DatabaseBackend, DatabaseConnection
    from .database.database_api_base import DatabaseBackend as BaseBackend
except ImportError:
    # Fallback für standalone testing
    logging.debug("UDS3 database imports not available - running in standalone mode")

# Standard Library fallbacks
import sqlite3

try:
    import psycopg2
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except (ImportError, AttributeError) as e:
    # Handle Python 3.13 compatibility issue with neo4j
    NEO4J_AVAILABLE = False
    GraphDatabase = None
    print(f"Neo4j not available: {e}")


class StrategyType(Enum):
    """Verfügbare Multi-DB Strategien nach Komplexität"""
    FULL_POLYGLOT = "full_polyglot"          # 4 DBs: PostgreSQL + CouchDB + ChromaDB + Neo4j  
    TRI_DATABASE = "tri_database"             # 3 DBs: Intelligente 3-DB Kompensation
    DUAL_DATABASE = "dual_database"           # 2 DBs: Hybrid Approach mit Compensation  
    POSTGRESQL_ENHANCED = "postgresql_enhanced"  # PostgreSQL + SQLite Enhanced
    SQLITE_MONOLITH = "sqlite_monolith"      # SQLite-only für minimal environments


@dataclass
class DatabaseAvailability:
    """Database Availability Status mit Connection Details"""
    postgresql: bool = False
    couchdb: bool = False  
    chromadb: bool = False
    neo4j: bool = False
    sqlite: bool = True  # Always available
    redis: bool = False  # Optional performance layer
    
    # Connection details für successful connections
    connection_details: Dict[str, Dict] = field(default_factory=dict)
    health_scores: Dict[str, float] = field(default_factory=dict)
    last_check: float = field(default_factory=time.time)


@dataclass
class FlexibleDistributionResult:
    """Result der flexiblen Document Distribution"""
    document_id: str
    strategy_used: StrategyType
    db_distribution: Dict[str, List[str]]
    compensation_applied: Dict[str, str]
    performance_rating: int
    execution_time_ms: float
    warnings: List[str] = field(default_factory=list)


class AdaptiveMultiDBStrategy:
    """
    Adaptive Multi-Database Strategy die sich dynamisch an verfügbare DBs anpasst
    
    Core-Features:
    - Runtime DB Discovery mit Connection Health Checks
    - Intelligente Strategy Selection basierend auf verfügbaren Backends  
    - Automatic Compensation Logic für fehlende DB Capabilities
    - Performance-optimierte Configuration für jede Strategy
    - Administrative Flexibilität für unvorhersehbare Environments
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Core State
        self.db_availability = DatabaseAvailability()
        self.current_strategy: Optional[StrategyType] = None
        self.fallback_strategies = self._initialize_fallback_strategies()
        self.compensation_handlers = {}
        
        # Performance Tracking
        self.strategy_performance = {}
        self.discovery_cache_ttl = self.config.get('discovery_cache_ttl', 300)  # 5 minutes
        
        # UDS3 Integration
        self.database_manager = None
        self._initialize_uds3_integration()
        
    def _initialize_uds3_integration(self):
        """Initialisiere Integration mit UDS3 DatabaseManager"""
        try:
            # Use existing UDS3 DatabaseManager if available
            if 'DatabaseManager' in globals():
                self.database_manager = DatabaseManager()
                self.logger.info("✅ UDS3 DatabaseManager Integration aktiviert")
            else:
                self.logger.info("ℹ️ UDS3 DatabaseManager nicht verfügbar - Standalone Mode")
        except Exception as e:
            self.logger.warning(f"UDS3 Integration fehlgeschlagen: {e}")
    
    async def initialize_adaptive_setup(self) -> StrategyType:
        """
        Hauptfunktion: Dynamische DB-Erkennung und optimale Strategy-Auswahl
        
        Returns:
            StrategyType: Die optimal ausgewählte Strategie für verfügbare DBs
        """
        self.logger.info("🚀 Initialisiere Adaptive Multi-DB Setup...")
        
        try:
            # 1. Runtime DB Discovery
            discovery_start = time.time()
            await self._discover_available_databases()
            discovery_time = (time.time() - discovery_start) * 1000
            
            # 2. Strategy Selection basierend auf Verfügbarkeit  
            self.current_strategy = self._select_optimal_strategy()
            
            # 3. Configuration Adaptation für gewählte Strategy
            await self._adapt_configuration()
            
            # 4. Performance Validation
            performance_rating = await self._validate_strategy_performance()
            
            self.logger.info(
                f"✅ Adaptive Setup Complete: {self.current_strategy.value} "
                f"(Discovery: {discovery_time:.1f}ms, Performance: {performance_rating}/10)"
            )
            
            return self.current_strategy
            
        except Exception as e:
            self.logger.error(f"❌ Adaptive Setup fehlgeschlagen: {e}")
            # Fallback to minimal strategy
            self.current_strategy = StrategyType.SQLITE_MONOLITH
            await self._adapt_configuration()
            return self.current_strategy
    
    async def _discover_available_databases(self):
        """
        Runtime Discovery aller verfügbaren Database Backends mit Health Checks
        """
        self.logger.info("🔍 Starting DB Discovery...")
        
        # Check if we have cached results within TTL
        if (time.time() - self.db_availability.last_check) < self.discovery_cache_ttl:
            self.logger.debug("Using cached DB availability results")
            return
        
        # Parallel Discovery Tasks für Performance
        discovery_tasks = [
            self._check_postgresql_availability(),
            self._check_couchdb_availability(), 
            self._check_chromadb_availability(),
            self._check_neo4j_availability(),
            self._check_redis_availability()
        ]
        
        # Execute all discovery tasks concurrently
        results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
        
        # Update availability basierend auf Discovery Results
        db_names = ['postgresql', 'couchdb', 'chromadb', 'neo4j', 'redis']
        for i, result in enumerate(results):
            db_name = db_names[i]
            if isinstance(result, tuple) and len(result) == 2:
                # Success: (True, connection_details)
                available, details = result
                setattr(self.db_availability, db_name, available)
                if available and details:
                    self.db_availability.connection_details[db_name] = details
                    self.db_availability.health_scores[db_name] = details.get('health_score', 1.0)
            elif isinstance(result, bool):
                # Simple boolean result  
                setattr(self.db_availability, db_name, result)
            else:
                # Exception or failure
                setattr(self.db_availability, db_name, False)
                if isinstance(result, Exception):
                    self.logger.warning(f"DB Discovery failed for {db_name}: {result}")
        
        # Update cache timestamp
        self.db_availability.last_check = time.time()
        
        # Log discovery results
        available_dbs = [db for db in db_names if getattr(self.db_availability, db)]
        available_dbs.append('sqlite')  # SQLite always available
        
        self.logger.info(f"📊 DB Discovery Complete: {len(available_dbs)} databases available")
        self.logger.debug(f"Available DBs: {available_dbs}")
        for db, health in self.db_availability.health_scores.items():
            self.logger.debug(f"  {db}: Health Score {health:.2f}")
    
    async def _check_postgresql_availability(self) -> Tuple[bool, Optional[Dict]]:
        """Check PostgreSQL availability mit Connection Health Check"""
        try:
            # Default connection parameters
            host = self.config.get('postgresql_host', 'localhost')
            port = self.config.get('postgresql_port', 5432)
            database = self.config.get('postgresql_database', 'postgres')
            user = self.config.get('postgresql_user', 'postgres') 
            password = self.config.get('postgresql_password', '')
            
            # Connection test
            start_time = time.time()
            conn = psycopg2.connect(
                host=host, port=port, database=database, 
                user=user, password=password,
                connect_timeout=5
            )
            
            # Health check query
            cursor = conn.cursor()
            cursor.execute("SELECT version(), current_database(), current_timestamp;")
            result = cursor.fetchone()
            
            # Check for useful extensions
            cursor.execute("SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'pg_vector', 'pg_trgm');")
            extensions = [row[0] for row in cursor.fetchall()]
            
            connection_time = (time.time() - start_time) * 1000
            health_score = min(1.0, 1000.0 / connection_time)  # Better performance = higher score
            
            cursor.close()
            conn.close()
            
            details = {
                'host': host,
                'port': port, 
                'database': database,
                'version': result[0] if result else 'unknown',
                'extensions': extensions,
                'connection_time_ms': connection_time,
                'health_score': health_score
            }
            
            return True, details
            
        except Exception as e:
            self.logger.debug(f"PostgreSQL not available: {e}")
            return False, None
    
    async def _check_couchdb_availability(self) -> Tuple[bool, Optional[Dict]]:
        """Check CouchDB availability mit HTTP Health Check"""
        try:
            host = self.config.get('couchdb_host', 'localhost')
            port = self.config.get('couchdb_port', 5984)
            url = f"http://{host}:{port}/"
            
            start_time = time.time()
            response = requests.get(url + "_up", timeout=5)
            
            if response.status_code == 200:
                # Get server info
                info_response = requests.get(url, timeout=3)
                server_info = info_response.json() if info_response.status_code == 200 else {}
                
                connection_time = (time.time() - start_time) * 1000
                health_score = min(1.0, 1000.0 / connection_time)
                
                details = {
                    'host': host,
                    'port': port,
                    'url': url,
                    'version': server_info.get('version', 'unknown'),
                    'vendor': server_info.get('vendor', {}),
                    'connection_time_ms': connection_time,
                    'health_score': health_score
                }
                
                return True, details
            else:
                return False, None
                
        except Exception as e:
            self.logger.debug(f"CouchDB not available: {e}")
            return False, None
    
    async def _check_chromadb_availability(self) -> Tuple[bool, Optional[Dict]]:
        """Check ChromaDB availability mit HTTP API Check"""
        try:
            host = self.config.get('chromadb_host', 'localhost')
            port = self.config.get('chromadb_port', 8000)
            url = f"http://{host}:{port}"
            
            start_time = time.time()
            # ChromaDB API heartbeat
            response = requests.get(url + "/api/v1/heartbeat", timeout=5)
            
            if response.status_code == 200:
                # Get version info
                try:
                    version_response = requests.get(url + "/api/v1/version", timeout=3)
                    version_info = version_response.json() if version_response.status_code == 200 else {}
                except:
                    version_info = {}
                
                connection_time = (time.time() - start_time) * 1000
                health_score = min(1.0, 1000.0 / connection_time)
                
                details = {
                    'host': host,
                    'port': port,
                    'url': url,
                    'version': version_info.get('version', 'unknown'),
                    'connection_time_ms': connection_time,
                    'health_score': health_score
                }
                
                return True, details
            else:
                return False, None
                
        except Exception as e:
            self.logger.debug(f"ChromaDB not available: {e}")
            return False, None
    
    async def _check_neo4j_availability(self) -> Tuple[bool, Optional[Dict]]:
        """Check Neo4j availability mit Bolt Protocol Check"""
        try:
            if not NEO4J_AVAILABLE or GraphDatabase is None:
                raise Exception("Neo4j driver not available")
                
            uri = self.config.get('neo4j_uri', 'bolt://localhost:7687')
            username = self.config.get('neo4j_username', 'neo4j')
            password = self.config.get('neo4j_password', 'neo4j')
            
            start_time = time.time()
            driver = GraphDatabase.driver(uri, auth=(username, password))
            
            # Health check query
            with driver.session() as session:
                result = session.run("CALL dbms.components() YIELD name, versions, edition")
                components = list(result)
            
            connection_time = (time.time() - start_time) * 1000
            health_score = min(1.0, 1000.0 / connection_time)
            
            driver.close()
            
            details = {
                'uri': uri,
                'username': username,
                'components': components,
                'connection_time_ms': connection_time,
                'health_score': health_score
            }
            
            return True, details
            
        except Exception as e:
            self.logger.debug(f"Neo4j not available: {e}")
            return False, None
    
    async def _check_redis_availability(self) -> Tuple[bool, Optional[Dict]]:
        """Check Redis availability (optional performance layer)"""
        try:
            host = self.config.get('redis_host', 'localhost')
            port = self.config.get('redis_port', 6379)
            
            # Simple socket check for Redis
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                connection_time = (time.time() - start_time) * 1000
                health_score = min(1.0, 1000.0 / connection_time)
                
                details = {
                    'host': host,
                    'port': port,
                    'connection_time_ms': connection_time,
                    'health_score': health_score
                }
                
                return True, details
            else:
                return False, None
                
        except Exception as e:
            self.logger.debug(f"Redis not available: {e}")
            return False, None
    
    def _select_optimal_strategy(self) -> StrategyType:
        """
        Intelligente Strategy Selection basierend auf verfügbaren DBs
        
        Returns:
            StrategyType: Optimal ausgewählte Strategie
        """
        
        # Count available primary databases (exclude Redis as it's optional)
        available_dbs = []
        if self.db_availability.postgresql:
            available_dbs.append('postgresql')
        if self.db_availability.couchdb:
            available_dbs.append('couchdb')  
        if self.db_availability.chromadb:
            available_dbs.append('chromadb')
        if self.db_availability.neo4j:
            available_dbs.append('neo4j')
        
        db_count = len(available_dbs)
        
        self.logger.info(f"🧠 Strategy Selection: {db_count} primary DBs available: {available_dbs}")
        
        # Strategy Selection Logic
        if db_count >= 4:
            strategy = StrategyType.FULL_POLYGLOT
            self.logger.info("🏆 Selected FULL_POLYGLOT: All 4 databases available")
            
        elif db_count == 3:
            strategy = StrategyType.TRI_DATABASE
            missing_db = set(['postgresql', 'couchdb', 'chromadb', 'neo4j']) - set(available_dbs)
            self.logger.info(f"🥈 Selected TRI_DATABASE: Missing {list(missing_db)}")
            
        elif db_count == 2:
            strategy = StrategyType.DUAL_DATABASE
            self.logger.info(f"🥉 Selected DUAL_DATABASE: Available {available_dbs}")
            
        elif self.db_availability.postgresql:
            strategy = StrategyType.POSTGRESQL_ENHANCED
            self.logger.info("👍 Selected POSTGRESQL_ENHANCED: PostgreSQL + SQLite")
            
        else:
            strategy = StrategyType.SQLITE_MONOLITH
            self.logger.info("💪 Selected SQLITE_MONOLITH: Minimal viable deployment")
        
        # Consider performance scores in selection
        if hasattr(self, 'db_availability') and self.db_availability.health_scores:
            avg_health = sum(self.db_availability.health_scores.values()) / len(self.db_availability.health_scores)
            self.logger.debug(f"Average DB health score: {avg_health:.2f}")
            
            # Downgrade strategy if health scores are too low
            if avg_health < 0.3 and strategy != StrategyType.SQLITE_MONOLITH:
                self.logger.warning("⚠️ Low health scores detected - considering fallback")
        
        return strategy
    
    async def _adapt_configuration(self):
        """
        Configuration Adaptation für die gewählte Strategy
        """
        if not self.current_strategy:
            raise ValueError("No strategy selected - call initialize_adaptive_setup() first")
        
        strategy_config = self.fallback_strategies[self.current_strategy]
        
        self.logger.info(f"⚙️ Adapting configuration for {self.current_strategy.value}")
        self.logger.debug(f"Strategy config: {strategy_config['description']}")
        
        # Initialize compensation handlers if needed
        if 'compensation_logic' in strategy_config:
            await self._initialize_compensation_handlers(strategy_config['compensation_logic'])
        
        # Log performance expectations
        performance_rating = strategy_config.get('performance_rating', 5)
        self.logger.info(f"📊 Expected performance rating: {performance_rating}/10")
        
        if 'limitations' in strategy_config:
            for limitation in strategy_config['limitations']:
                self.logger.warning(f"⚠️ Limitation: {limitation}")
    
    async def _validate_strategy_performance(self) -> int:
        """
        Validate performance der gewählten Strategy
        
        Returns:
            int: Performance rating 1-10
        """
        if not self.current_strategy:
            return 1
        
        strategy_config = self.fallback_strategies[self.current_strategy]
        expected_rating = strategy_config.get('performance_rating', 5)
        
        # TODO: Add real performance validation tests
        # For now, return expected rating
        return expected_rating
    
    async def _initialize_compensation_handlers(self, compensation_logic: Dict):
        """Initialize compensation handlers für fehlende DB capabilities"""
        self.compensation_handlers = compensation_logic
        self.logger.debug(f"Initialized {len(compensation_logic)} compensation handlers")
    
    def _initialize_fallback_strategies(self) -> Dict[StrategyType, Dict]:
        """
        Comprehensive Fallback Strategies für verschiedene DB-Kombinationen
        
        Returns:
            Dict: Vollständige Strategy-Definitionen für alle Deployment-Szenarien
        """
        return {
            # OPTIMAL: Alle 4 DBs verfügbar - Full Polyglot Architecture
            StrategyType.FULL_POLYGLOT: {
                "description": "Vollständige Multi-DB Strategie mit allen 4 Datenbanken",
                "databases": {
                    "postgresql": {
                        "role": "master_registry", 
                        "capabilities": ["structured_metadata", "cross_references", "audit_trail"],
                        "tables": ["uds3_master_documents", "uds3_processor_results", "uds3_cross_references"]
                    },
                    "couchdb": {
                        "role": "document_store",
                        "capabilities": ["complex_documents", "event_store", "processing_history"], 
                        "collections": ["processed_documents", "event_log", "processor_workflows"]
                    },
                    "chromadb": {
                        "role": "vector_engine",
                        "capabilities": ["vector_embeddings", "semantic_search", "similarity_matching"],
                        "collections": ["document_embeddings", "content_vectors", "similarity_cache"]
                    },
                    "neo4j": {
                        "role": "relationship_engine", 
                        "capabilities": ["graph_relationships", "spatial_relations", "document_networks"],
                        "node_types": ["Document", "Processor", "Relationship", "Spatial"]
                    }
                },
                "performance_rating": 10,
                "limitations": [],
                "compensation_logic": {}
            },
            
            # FALLBACK 1: 3 DBs verfügbar - Intelligente Kompensation
            StrategyType.TRI_DATABASE: {
                "description": "3-Database Setup mit intelligenter Kompensation für fehlende DB",
                "compensation_strategies": {
                    "no_neo4j": {
                        "postgresql": {
                            "role": "master_registry_plus",
                            "capabilities": ["structured_metadata", "cross_references", "relationships_table"],
                            "additional_tables": ["uds3_document_relationships", "uds3_spatial_data"]
                        },
                        "couchdb": {
                            "role": "document_store_plus", 
                            "capabilities": ["complex_documents", "event_store", "spatial_metadata"],
                            "additional_docs": ["spatial_documents", "relationship_cache"]
                        },
                        "chromadb": {
                            "role": "vector_engine_plus",
                            "capabilities": ["vector_embeddings", "semantic_search", "relationship_vectors"],
                            "additional_collections": ["relationship_embeddings", "spatial_vectors"]
                        }
                    },
                    "no_chromadb": {
                        "postgresql": {
                            "role": "master_registry_plus",
                            "capabilities": ["structured_metadata", "cross_references", "full_text_search", "simple_vectors"],
                            "extensions_required": ["pg_trgm", "pg_vector"],
                            "additional_tables": ["uds3_document_vectors", "uds3_fulltext_index"]
                        },
                        "couchdb": {
                            "role": "document_store_plus",
                            "capabilities": ["complex_documents", "event_store", "text_content", "search_indexes"],
                            "additional_docs": ["search_cache", "content_index"]
                        },
                        "neo4j": {
                            "role": "relationship_engine_plus", 
                            "capabilities": ["graph_relationships", "spatial_relations", "content_similarity"],
                            "additional_properties": ["content_hash", "similarity_scores"]
                        }
                    },
                    "no_couchdb": {
                        "postgresql": {
                            "role": "master_registry_plus",
                            "capabilities": ["structured_metadata", "cross_references", "jsonb_documents", "event_log"],
                            "additional_tables": ["uds3_document_content", "uds3_event_store"]
                        },
                        "chromadb": {
                            "role": "vector_engine_plus",
                            "capabilities": ["vector_embeddings", "semantic_search", "document_content"],
                            "additional_collections": ["document_cache", "processing_history"]
                        },
                        "neo4j": {
                            "role": "relationship_engine_plus",
                            "capabilities": ["graph_relationships", "spatial_relations", "processing_workflows"],
                            "additional_nodes": ["ProcessingStep", "DocumentVersion"]
                        }
                    },
                    "no_postgresql": {
                        "sqlite": {
                            "role": "master_registry_fallback",
                            "capabilities": ["structured_metadata", "cross_references", "local_cache"],
                            "tables": ["uds3_master_documents", "uds3_processor_results", "uds3_cache"]
                        },
                        "couchdb": {
                            "role": "document_store_plus",
                            "capabilities": ["complex_documents", "event_store", "metadata_backup"],
                            "additional_docs": ["metadata_mirror", "registry_backup"]
                        },
                        "chromadb": {
                            "role": "vector_engine",
                            "capabilities": ["vector_embeddings", "semantic_search", "content_storage"]
                        },
                        "neo4j": {
                            "role": "relationship_engine_plus",
                            "capabilities": ["graph_relationships", "spatial_relations", "metadata_graph"],
                            "additional_nodes": ["Metadata", "Registry"]
                        }
                    }
                },
                "performance_rating": 8,
                "limitations": ["Reduced redundancy", "Single point of failure per capability"],
                "compensation_logic": {
                    "missing_vector_search": "postgresql_pg_vector_fallback",
                    "missing_graph_traversal": "postgresql_recursive_cte", 
                    "missing_document_store": "postgresql_jsonb_storage",
                    "missing_relational_layer": "sqlite_local_fallback"
                }
            },
            
            # FALLBACK 2: 2 DBs verfügbar - Hybrid Approach
            StrategyType.DUAL_DATABASE: {
                "description": "2-Database Hybrid Setup mit maximaler Funktionalitäts-Kompensation",
                "combinations": {
                    "postgresql_chromadb": {
                        "postgresql": {
                            "role": "master_plus_documents",
                            "capabilities": ["structured_metadata", "cross_references", "relationships", "spatial_data", "event_log"],
                            "extensions_required": ["postgis", "pg_trgm"],
                            "tables": ["uds3_master_documents", "uds3_relationships", "uds3_spatial", "uds3_events"]
                        },
                        "chromadb": {
                            "role": "vector_plus_content",
                            "capabilities": ["vector_embeddings", "semantic_search", "document_content", "processing_history"],
                            "collections": ["document_vectors", "content_cache", "search_index", "history"]
                        }
                    },
                    "postgresql_neo4j": {
                        "postgresql": {
                            "role": "master_plus_documents",
                            "capabilities": ["structured_metadata", "document_content", "embeddings_table", "event_log"],
                            "extensions_required": ["pg_vector", "pg_trgm"],
                            "tables": ["uds3_master_documents", "uds3_content", "uds3_vectors", "uds3_events"]
                        },
                        "neo4j": {
                            "role": "relationship_plus_spatial",
                            "capabilities": ["graph_relationships", "spatial_relations", "content_networks", "processing_flows"],
                            "additional_properties": ["document_content", "processing_metadata"]
                        }
                    },
                    "postgresql_couchdb": {
                        "postgresql": {
                            "role": "master_plus_vectors",
                            "capabilities": ["structured_metadata", "relationships", "simple_vectors", "spatial_basic"],
                            "extensions_required": ["pg_vector", "postgis"],
                            "tables": ["uds3_master_documents", "uds3_relationships", "uds3_vectors"]
                        },
                        "couchdb": {
                            "role": "documents_plus_search",
                            "capabilities": ["complex_documents", "event_store", "processing_history", "spatial_data"],
                            "views": ["spatial_index", "search_index", "relationship_views"]
                        }
                    },
                    "sqlite_chromadb": {
                        "sqlite": {
                            "role": "master_plus_relations",
                            "capabilities": ["structured_metadata", "relationships", "spatial_basic", "cache_layer"],
                            "extensions_required": ["rtree", "fts5"],
                            "tables": ["uds3_master_documents", "uds3_relationships", "uds3_spatial_basic", "uds3_cache"]
                        },
                        "chromadb": {
                            "role": "vector_plus_content_plus",
                            "capabilities": ["vector_embeddings", "semantic_search", "document_content", "processing_history", "metadata_cache"],
                            "collections": ["document_vectors", "content_full", "metadata_backup", "search_cache"]
                        }
                    }
                },
                "performance_rating": 6,
                "limitations": ["Significant capability overlap", "Performance bottlenecks", "Complex compensation logic"],
                "compensation_logic": {
                    "missing_specialized_storage": "postgresql_jsonb_universal",
                    "missing_graph_capabilities": "manual_relationship_tracking",
                    "missing_vector_search": "postgresql_pg_vector_required",
                    "missing_spatial_features": "postgis_or_basic_calculations"
                }
            },
            
            # FALLBACK 3: PostgreSQL Enhanced (PostgreSQL + SQLite)
            StrategyType.POSTGRESQL_ENHANCED: {
                "description": "PostgreSQL-zentrierte Lösung mit SQLite Performance Layer",
                "databases": {
                    "postgresql": {
                        "role": "primary_engine",
                        "capabilities": [
                            "master_registry", "structured_metadata", "cross_references", 
                            "document_content", "vector_embeddings", "relationships",
                            "spatial_data_postgis", "processing_history", "event_store"
                        ],
                        "extensions_required": ["postgis", "pg_vector", "pg_trgm"],
                        "tables": [
                            "uds3_master_documents", "uds3_processor_results", "uds3_cross_references",
                            "uds3_document_content", "uds3_relationships", "uds3_spatial_data", 
                            "uds3_vector_embeddings", "uds3_processing_history", "uds3_event_store"
                        ]
                    },
                    "sqlite": {
                        "role": "performance_layer",
                        "capabilities": ["cache_layer", "session_data", "temp_processing", "performance_indexes", "quick_search"],
                        "extensions_required": ["fts5", "rtree", "json1"],
                        "tables": ["cache_documents", "session_cache", "temp_results", "search_index", "performance_stats"]
                    }
                },
                "performance_rating": 7,
                "limitations": ["Single primary database dependency", "Complex PostgreSQL schema", "Extension requirements"],
                "compensation_logic": {
                    "vector_search": "pg_vector_native",
                    "graph_relationships": "recursive_cte_queries",
                    "document_storage": "jsonb_columns",
                    "spatial_operations": "postgis_full_feature",
                    "performance_boost": "sqlite_caching_layer"
                }
            },
            
            # FALLBACK 4: SQLite Monolith (Minimum viable)
            StrategyType.SQLITE_MONOLITH: {
                "description": "SQLite-only Lösung für minimale Deployment-Environments",
                "databases": {
                    "sqlite": {
                        "role": "universal_backend",
                        "capabilities": [
                            "master_documents", "structured_metadata", "cross_references",
                            "document_content", "simple_embeddings", "relationships", 
                            "spatial_basic", "processing_history", "event_log",
                            "cache_tables", "search_indexes"
                        ],
                        "extensions_required": ["fts5", "rtree", "json1"],
                        "tables": [
                            "uds3_master_documents", "uds3_processor_results", "uds3_cross_references",
                            "uds3_document_content", "uds3_relationships", "uds3_spatial_basic",
                            "uds3_simple_vectors", "uds3_processing_history", "uds3_event_log",
                            "uds3_cache_layer", "uds3_fts_index"
                        ],
                        "custom_functions": [
                            "cosine_similarity_approx", "spatial_distance_basic", 
                            "json_extract_enhanced", "search_rank_bm25"
                        ]
                    }
                },
                "performance_rating": 4,
                "limitations": [
                    "Keine echte Vector Search (nur Approximate LSH)",
                    "Begrenzte Concurrent Performance", 
                    "Einfache Spatial Operations (kein PostGIS)",
                    "Keine Graph Traversal (nur Relationship Tables)",
                    "File-size Limits für große Deployments"
                ],
                "compensation_logic": {
                    "vector_similarity": "lsh_approximate_matching",
                    "spatial_operations": "basic_distance_calculations", 
                    "graph_traversal": "iterative_relationship_queries",
                    "concurrent_access": "wal_mode_optimization",
                    "performance": "aggressive_indexing_strategy"
                }
            }
        }


class FlexibleMultiDBDistributor:
    """
    Flexible Document Distribution die sich an verfügbare DBs anpasst
    
    Koordiniert die Verteilung von UDS3 Processing Results auf verfügbare
    Database Backends basierend auf der gewählten AdaptiveMultiDBStrategy.
    """
    
    def __init__(self, adaptive_strategy: AdaptiveMultiDBStrategy):
        self.strategy = adaptive_strategy
        self.logger = logging.getLogger(self.__class__.__name__)
        self.distribution_cache = {}
        
    async def distribute_document_flexibly(
        self, 
        document_id: str,
        processor_results: List[Dict],  # UDS3 JobResults
        metadata: Dict = None
    ) -> FlexibleDistributionResult:
        """
        Hauptfunktion: Flexible Document Distribution basierend auf verfügbaren DBs
        
        Args:
            document_id: Unique Document Identifier
            processor_results: Liste der UDS3 Processor Results
            metadata: Optional additional metadata
            
        Returns:
            FlexibleDistributionResult: Detailliertes Ergebnis der Distribution
        """
        
        start_time = time.time()
        
        if not self.strategy.current_strategy:
            raise ValueError("AdaptiveMultiDBStrategy must be initialized first")
        
        self.logger.info(f"📤 Starting flexible distribution for {document_id} using {self.strategy.current_strategy.value}")
        
        try:
            # 1. Strategy Configuration laden
            strategy_config = self.strategy.fallback_strategies[self.strategy.current_strategy]
            
            # 2. Distribution Plan erstellen basierend auf Strategy
            distribution_plan = await self._create_adaptive_distribution_plan(
                processor_results, strategy_config, metadata or {}
            )
            
            # 3. Compensation Logic anwenden für fehlende DBs
            compensation_results = await self._apply_compensation_logic(
                distribution_plan, processor_results
            )
            
            # 4. Flexible Execution der Distribution
            execution_results = await self._execute_flexible_distribution(
                document_id, distribution_plan, compensation_results
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            result = FlexibleDistributionResult(
                document_id=document_id,
                strategy_used=self.strategy.current_strategy,
                db_distribution=execution_results,
                compensation_applied=compensation_results,
                performance_rating=strategy_config.get('performance_rating', 5),
                execution_time_ms=execution_time
            )
            
            self.logger.info(
                f"✅ Distribution complete for {document_id}: "
                f"{execution_time:.1f}ms, Rating: {result.performance_rating}/10"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Distribution failed for {document_id}: {e}")
            
            # Emergency fallback result
            return FlexibleDistributionResult(
                document_id=document_id,
                strategy_used=StrategyType.SQLITE_MONOLITH,
                db_distribution={"sqlite": ["emergency_fallback"]},
                compensation_applied={"emergency": "full_sqlite_fallback"},
                performance_rating=1,
                execution_time_ms=(time.time() - start_time) * 1000,
                warnings=[f"Emergency fallback due to: {str(e)}"]
            )
    
    async def _create_adaptive_distribution_plan(
        self, 
        processor_results: List[Dict], 
        strategy_config: Dict,
        metadata: Dict
    ) -> Dict[str, List[str]]:
        """
        Erstellt adaptiven Distribution Plan basierend auf Strategy Config
        """
        
        distribution_plan = {}
        
        # Different logic based on strategy type
        if self.strategy.current_strategy == StrategyType.FULL_POLYGLOT:
            # Full distribution across all 4 DBs
            distribution_plan = await self._plan_full_polyglot_distribution(processor_results, metadata)
            
        elif self.strategy.current_strategy == StrategyType.TRI_DATABASE:
            # 3-DB distribution with compensation  
            distribution_plan = await self._plan_tri_database_distribution(processor_results, strategy_config)
            
        elif self.strategy.current_strategy == StrategyType.DUAL_DATABASE:
            # 2-DB hybrid distribution
            distribution_plan = await self._plan_dual_database_distribution(processor_results, strategy_config)
            
        elif self.strategy.current_strategy == StrategyType.POSTGRESQL_ENHANCED:
            # PostgreSQL-centric distribution  
            distribution_plan = await self._plan_postgresql_enhanced_distribution(processor_results)
            
        elif self.strategy.current_strategy == StrategyType.SQLITE_MONOLITH:
            # SQLite-only distribution
            distribution_plan = await self._plan_sqlite_monolith_distribution(processor_results)
        
        self.logger.debug(f"Distribution plan: {distribution_plan}")
        return distribution_plan
    
    async def _plan_full_polyglot_distribution(self, processor_results: List[Dict], metadata: Dict) -> Dict[str, List[str]]:
        """Plan distribution for full polyglot setup"""
        return {
            "postgresql": ["master_registry", "structured_metadata", "cross_references"], 
            "couchdb": ["complex_documents", "event_store", "processing_history"],
            "chromadb": ["vector_embeddings", "semantic_search", "similarity_cache"],
            "neo4j": ["graph_relationships", "spatial_relations", "document_networks"]
        }
    
    async def _plan_tri_database_distribution(self, processor_results: List[Dict], strategy_config: Dict) -> Dict[str, List[str]]:
        """Plan distribution for 3-database setup with compensation"""
        
        # Determine which DB is missing and select appropriate compensation strategy
        available_dbs = []
        if self.strategy.db_availability.postgresql: available_dbs.append('postgresql')
        if self.strategy.db_availability.couchdb: available_dbs.append('couchdb')
        if self.strategy.db_availability.chromadb: available_dbs.append('chromadb')
        if self.strategy.db_availability.neo4j: available_dbs.append('neo4j')
        
        missing_db = set(['postgresql', 'couchdb', 'chromadb', 'neo4j']) - set(available_dbs)
        
        if 'neo4j' in missing_db:
            compensation_strategy = strategy_config['compensation_strategies']['no_neo4j']
        elif 'chromadb' in missing_db:
            compensation_strategy = strategy_config['compensation_strategies']['no_chromadb']
        elif 'couchdb' in missing_db:
            compensation_strategy = strategy_config['compensation_strategies']['no_couchdb']
        elif 'postgresql' in missing_db:
            compensation_strategy = strategy_config['compensation_strategies']['no_postgresql']
        else:
            # Fallback to first available strategy
            compensation_strategy = list(strategy_config['compensation_strategies'].values())[0]
        
        # Build distribution plan from compensation strategy
        distribution_plan = {}
        for db_name, db_config in compensation_strategy.items():
            if hasattr(self.strategy.db_availability, db_name) and getattr(self.strategy.db_availability, db_name):
                distribution_plan[db_name] = db_config['capabilities']
        
        return distribution_plan
    
    async def _plan_dual_database_distribution(self, processor_results: List[Dict], strategy_config: Dict) -> Dict[str, List[str]]:
        """Plan distribution for 2-database hybrid setup"""
        
        # Identify available DB combination
        available_dbs = []
        if self.strategy.db_availability.postgresql: available_dbs.append('postgresql')
        if self.strategy.db_availability.couchdb: available_dbs.append('couchdb')
        if self.strategy.db_availability.chromadb: available_dbs.append('chromadb')  
        if self.strategy.db_availability.neo4j: available_dbs.append('neo4j')
        
        # Select best combination strategy
        if 'postgresql' in available_dbs and 'chromadb' in available_dbs:
            combination = strategy_config['combinations']['postgresql_chromadb']
        elif 'postgresql' in available_dbs and 'neo4j' in available_dbs:
            combination = strategy_config['combinations']['postgresql_neo4j']
        elif 'postgresql' in available_dbs and 'couchdb' in available_dbs:
            combination = strategy_config['combinations']['postgresql_couchdb']
        elif 'chromadb' in available_dbs:  # sqlite_chromadb fallback
            combination = strategy_config['combinations']['sqlite_chromadb']
        else:
            # Emergency fallback
            combination = {"sqlite": {"capabilities": ["emergency_storage"]}}
        
        # Build distribution plan
        distribution_plan = {}
        for db_name, db_config in combination.items():
            distribution_plan[db_name] = db_config['capabilities']
        
        return distribution_plan
    
    async def _plan_postgresql_enhanced_distribution(self, processor_results: List[Dict]) -> Dict[str, List[str]]:
        """Plan distribution for PostgreSQL enhanced setup"""
        return {
            "postgresql": [
                "master_registry", "structured_metadata", "cross_references",
                "document_content", "vector_embeddings", "relationships",
                "spatial_data_postgis", "processing_history", "event_store"
            ],
            "sqlite": [
                "cache_layer", "session_data", "temp_processing", 
                "performance_indexes", "quick_search"
            ]
        }
    
    async def _plan_sqlite_monolith_distribution(self, processor_results: List[Dict]) -> Dict[str, List[str]]:
        """Plan distribution for SQLite monolith setup"""
        return {
            "sqlite": [
                "master_documents", "structured_metadata", "cross_references",
                "document_content", "simple_embeddings", "relationships",
                "spatial_basic", "processing_history", "event_log", 
                "cache_tables", "search_indexes"
            ]
        }
    
    async def _apply_compensation_logic(
        self,
        distribution_plan: Dict[str, List[str]], 
        processor_results: List[Dict]
    ) -> Dict[str, str]:
        """
        Wendet Compensation Logic für fehlende DB Capabilities an
        """
        
        compensation_applied = {}
        strategy_config = self.strategy.fallback_strategies[self.strategy.current_strategy]
        compensation_logic = strategy_config.get('compensation_logic', {})
        
        for missing_capability, compensation_method in compensation_logic.items():
            self.logger.debug(f"Applying compensation: {missing_capability} -> {compensation_method}")
            compensation_applied[missing_capability] = compensation_method
        
        return compensation_applied
    
    async def _execute_flexible_distribution(
        self,
        document_id: str,
        distribution_plan: Dict[str, List[str]],
        compensation_results: Dict[str, str]
    ) -> Dict[str, List[str]]:
        """
        Führt die flexible Distribution aus (Placeholder für echte DB Operations)
        """
        
        execution_results = {}
        
        for db_name, capabilities in distribution_plan.items():
            try:
                # TODO: Implement actual database operations here
                # For now, simulate successful distribution
                
                self.logger.debug(f"Distributing to {db_name}: {capabilities}")
                
                # Simulate processing time based on capability count
                processing_time = len(capabilities) * 0.01  
                await asyncio.sleep(processing_time)
                
                execution_results[db_name] = capabilities
                
            except Exception as e:
                self.logger.error(f"Distribution to {db_name} failed: {e}")
                execution_results[db_name] = [f"failed: {str(e)}"]
        
        return execution_results


# Convenience functions for easy integration
async def initialize_adaptive_multi_db(config: Dict = None) -> Tuple[AdaptiveMultiDBStrategy, FlexibleMultiDBDistributor]:
    """
    Convenience function: Initialize complete Adaptive Multi-DB System
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Tuple of (AdaptiveMultiDBStrategy, FlexibleMultiDBDistributor)
    """
    
    # Initialize adaptive strategy
    strategy = AdaptiveMultiDBStrategy(config)
    selected_strategy = await strategy.initialize_adaptive_setup()
    
    # Initialize flexible distributor  
    distributor = FlexibleMultiDBDistributor(strategy)
    
    logging.info(f"🚀 Adaptive Multi-DB System initialized with {selected_strategy.value}")
    
    return strategy, distributor


if __name__ == "__main__":
    # Example usage and testing
    async def test_adaptive_strategy():
        """Test function for development"""
        
        logging.basicConfig(level=logging.INFO)
        
        # Test configuration
        test_config = {
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'couchdb_host': 'localhost', 
            'couchdb_port': 5984,
            'chromadb_host': 'localhost',
            'chromadb_port': 8000,
            'neo4j_uri': 'bolt://localhost:7687'
        }
        
        # Initialize system
        strategy, distributor = await initialize_adaptive_multi_db(test_config)
        
        # Test document distribution
        test_processor_results = [
            {"processor": "ImageProcessor", "content": "test image data"},
            {"processor": "TextProcessor", "content": "test text content"}
        ]
        
        result = await distributor.distribute_document_flexibly(
            document_id="test_doc_001",
            processor_results=test_processor_results
        )
        
        print(f"Distribution Result: {result}")
    
    # Run test if executed directly
    asyncio.run(test_adaptive_strategy())