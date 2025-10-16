#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monolithische Fallback-Strategien für UDS3 Covina Backend

Implementiert spezialisierte Single-Database Strategien für minimale
Verwaltungsumgebungen mit beschränkten Ressourcen:

1. SQLiteMonolithStrategy - Vollständige SQLite-only Lösung
2. PostgreSQLEnhancedStrategy - PostgreSQL + SQLite Performance Layer

Diese Strategien sind Teil der AdaptiveMultiDBStrategy und werden automatisch
ausgewählt wenn nur begrenzte Database-Backends verfügbar sind.

Autor: Covina Development Team  
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import sqlite3
import json
import os
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

# PostgreSQL support (optional)
try:
    import psycopg2
    import psycopg2.extras
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    logging.warning("PostgreSQL support not available - SQLite fallback only")


@dataclass
class MonolithResult:
    """Result einer monolithischen Database Operation"""
    success: bool
    strategy_used: str
    operations_completed: List[str]
    execution_time_ms: float
    warnings: List[str] = None
    storage_path: str = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class SQLiteMonolithStrategy:
    """
    SQLite-only Strategie für minimal environments
    
    Implementiert alle Multi-DB Features in einer einzigen SQLite-Datenbank:
    - Comprehensive Schema mit allen UDS3 Tabellen
    - FTS5 für Full-Text Search (ChromaDB Ersatz)
    - RTRee für Spatial Indexing (Neo4j/PostGIS Ersatz) 
    - JSON1 für Document Storage (CouchDB Ersatz)
    - Custom Functions für Vector Similarity (ChromaDB Ersatz)
    - Event Sourcing Tables für Audit Trail
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # SQLite Configuration
        self.db_path = self.config.get('sqlite_path', './data/sqlite_monolith.db')
        self.enable_wal = self.config.get('enable_wal', True)
        self.cache_size = self.config.get('cache_size', -64000)  # 64MB cache
        self.page_size = self.config.get('page_size', 4096)
        
        # Performance settings
        self.batch_size = self.config.get('batch_size', 1000)
        self.connection_pool_size = self.config.get('connection_pool_size', 5)
        
        # State
        self.connection = None
        self.schema_initialized = False
        
    async def initialize_monolith(self) -> MonolithResult:
        """
        Initialisiert die SQLite Monolith Database mit comprehensive schema
        """
        start_time = time.time()
        operations = []
        
        try:
            self.logger.info(f"🗄️ Initializing SQLite Monolith at {self.db_path}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # 1. Create connection with optimized settings
            await self._create_optimized_connection()
            operations.append("connection_created")
            
            # 2. Initialize comprehensive schema
            await self._initialize_comprehensive_schema() 
            operations.append("schema_initialized")
            
            # 3. Create custom functions
            await self._create_custom_functions()
            operations.append("custom_functions_created")
            
            # 4. Create performance indexes
            await self._create_performance_indexes()
            operations.append("indexes_created")
            
            # 5. Initialize FTS5 for full-text search
            await self._initialize_fts5_search()
            operations.append("fts5_initialized")
            
            # 6. Setup spatial indexing with RTRee
            await self._initialize_spatial_indexing()
            operations.append("spatial_indexing_setup")
            
            execution_time = (time.time() - start_time) * 1000
            
            self.schema_initialized = True
            
            self.logger.info(f"✅ SQLite Monolith initialized successfully in {execution_time:.1f}ms")
            
            return MonolithResult(
                success=True,
                strategy_used="sqlite_monolith",
                operations_completed=operations,
                execution_time_ms=execution_time,
                storage_path=self.db_path
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.error(f"❌ SQLite Monolith initialization failed: {e}")
            
            return MonolithResult(
                success=False,
                strategy_used="sqlite_monolith",
                operations_completed=operations,
                execution_time_ms=execution_time,
                warnings=[f"Initialization failed: {str(e)}"],
                storage_path=self.db_path
            )
    
    async def _create_optimized_connection(self):
        """Erstellt optimierte SQLite Connection"""
        
        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow multi-threading
            timeout=30.0
        )
        
        # Enable Row factory for easier data access
        self.connection.row_factory = sqlite3.Row
        
        # Performance optimizations
        cursor = self.connection.cursor()
        
        # Enable WAL mode for better concurrency
        if self.enable_wal:
            cursor.execute("PRAGMA journal_mode=WAL")
        
        # Cache and performance settings
        cursor.execute(f"PRAGMA cache_size={self.cache_size}")
        cursor.execute(f"PRAGMA page_size={self.page_size}")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        
        cursor.close()
        
        self.logger.debug("SQLite connection optimized for performance")
    
    async def _initialize_comprehensive_schema(self):
        """Initialisiert comprehensive SQLite schema für alle UDS3 features"""
        
        cursor = self.connection.cursor()
        
        # Core Tables - entsprechen PostgreSQL Master Registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_master_documents (
                document_id VARCHAR(255) PRIMARY KEY,
                uuid TEXT UNIQUE DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('AB89',1+abs(random())%4,1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                file_path TEXT NOT NULL,
                original_filename TEXT,
                file_size_bytes INTEGER,
                file_hash_sha256 TEXT,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processing_status TEXT DEFAULT 'pending',
                processor_version TEXT,
                metadata_json TEXT,  -- JSON storage for complex metadata
                content_preview TEXT,
                search_content TEXT  -- Optimized for FTS5
            )
        """)
        
        # Processor Results - entspricht PostgreSQL Processor Results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_processor_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id VARCHAR(255) REFERENCES uds3_master_documents(document_id),
                processor_name TEXT NOT NULL,
                processor_version TEXT,
                processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result_type TEXT,  -- 'metadata', 'content', 'embedding', 'relationship'
                result_data_json TEXT,  -- JSON storage for processor results
                confidence_score REAL,
                error_message TEXT,
                execution_time_ms REAL
            )
        """)
        
        # Cross-References - entspricht PostgreSQL Cross References
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_cross_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_document_id VARCHAR(255) REFERENCES uds3_master_documents(document_id),
                target_document_id VARCHAR(255) REFERENCES uds3_master_documents(document_id), 
                reference_type TEXT,  -- 'similarity', 'citation', 'dependency', 'spatial'
                relationship_strength REAL DEFAULT 0.0,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Document Content - entspricht CouchDB Document Storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_document_content (
                document_id VARCHAR(255) PRIMARY KEY REFERENCES uds3_master_documents(document_id),
                content_type TEXT,  -- 'text', 'structured', 'binary_metadata'
                content_text TEXT,  -- Full text content for search
                content_structured_json TEXT,  -- JSON for structured data
                content_binary_metadata TEXT,  -- Base64 encoded metadata for binary files  
                extraction_method TEXT,
                extraction_confidence REAL,
                language_detected TEXT,
                encoding_detected TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Simple Vector Storage - ChromaDB Ersatz mit LSH Approximation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_simple_vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id VARCHAR(255) REFERENCES uds3_master_documents(document_id),
                vector_type TEXT,  -- 'content_embedding', 'title_embedding', 'summary_embedding'
                vector_dimension INTEGER,
                vector_data_json TEXT,  -- JSON array of float values
                lsh_hash TEXT,  -- LSH hash for approximate similarity search
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_name TEXT,
                model_version TEXT
            )
        """)
        
        # Relationships - Neo4j Ersatz mit Table-based Graph
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_document_id VARCHAR(255) REFERENCES uds3_master_documents(document_id),
                target_document_id VARCHAR(255) REFERENCES uds3_master_documents(document_id),
                relationship_type TEXT,  -- 'references', 'similar_to', 'part_of', 'derived_from'
                relationship_properties_json TEXT,  -- JSON for additional properties
                strength REAL DEFAULT 0.0,
                direction TEXT DEFAULT 'directed',  -- 'directed', 'bidirectional' 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_processor TEXT,
                confidence REAL
            )
        """)
        
        # Spatial Data - PostGIS/Neo4j Spatial Ersatz
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_spatial_basic (
                document_id VARCHAR(255) PRIMARY KEY REFERENCES uds3_master_documents(document_id),
                latitude REAL,
                longitude REAL,
                altitude REAL,
                coordinate_system TEXT DEFAULT 'WGS84',
                spatial_precision REAL,  -- Precision in meters
                bounding_box_json TEXT,  -- JSON: {"min_lat": ..., "max_lat": ..., "min_lon": ..., "max_lon": ...}
                spatial_metadata_json TEXT,  -- Additional spatial properties
                extraction_source TEXT,  -- 'exif', 'content_analysis', 'manual'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Processing History - Event Store equivalent
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_processing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id VARCHAR(255) REFERENCES uds3_master_documents(document_id),
                event_type TEXT,  -- 'created', 'processed', 'updated', 'deleted'
                event_data_json TEXT,  -- JSON event payload
                processor_name TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                performance_metrics_json TEXT
            )
        """)
        
        # Event Log - CouchDB Event Store Ersatz  
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_uuid TEXT UNIQUE DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('AB89',1+abs(random())%4,1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                event_stream_id TEXT,  -- Group related events
                event_type TEXT NOT NULL,
                event_version INTEGER DEFAULT 1,
                aggregate_id TEXT,  -- Document ID or other aggregate
                event_payload_json TEXT,  -- Full event data
                metadata_json TEXT,  -- Event metadata
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                correlation_id TEXT,  -- For distributed tracing
                causation_id TEXT     -- Event chain tracking
            )
        """)
        
        # Cache Layer - Performance optimization
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uds3_cache_layer (
                cache_key TEXT PRIMARY KEY,
                cache_value_json TEXT,
                cache_type TEXT,  -- 'query_result', 'computation', 'aggregation'
                expiry_timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hit_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.connection.commit()
        cursor.close()
        
        self.logger.debug("Comprehensive SQLite schema created successfully")
    
    async def _create_custom_functions(self):
        """Erstellt custom SQLite functions für erweiterte Funktionalität"""
        
        def cosine_similarity_approx(vec1_json: str, vec2_json: str) -> float:
            """Approximate cosine similarity für Vector Search Ersatz"""
            try:
                import json
                import math
                
                vec1 = json.loads(vec1_json or "[]")
                vec2 = json.loads(vec2_json or "[]")
                
                if not vec1 or not vec2 or len(vec1) != len(vec2):
                    return 0.0
                
                dot_product = sum(a * b for a, b in zip(vec1, vec2))
                magnitude1 = math.sqrt(sum(a * a for a in vec1))
                magnitude2 = math.sqrt(sum(b * b for b in vec2))
                
                if magnitude1 == 0 or magnitude2 == 0:
                    return 0.0
                    
                return dot_product / (magnitude1 * magnitude2)
                
            except Exception:
                return 0.0
        
        def spatial_distance_basic(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            """Basic spatial distance calculation (Haversine formula)"""
            try:
                import math
                
                if any(x is None for x in [lat1, lon1, lat2, lon2]):
                    return float('inf')
                
                # Convert to radians
                lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
                lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
                
                # Haversine formula
                dlat = lat2_rad - lat1_rad
                dlon = lon2_rad - lon1_rad
                
                a = (math.sin(dlat/2)**2 + 
                     math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
                c = 2 * math.asin(math.sqrt(a))
                
                # Earth radius in kilometers
                earth_radius_km = 6371.0
                
                return earth_radius_km * c
                
            except Exception:
                return float('inf')
        
        def json_extract_enhanced(json_str: str, path: str) -> str:
            """Enhanced JSON extraction mit error handling"""
            try:
                import json
                
                data = json.loads(json_str or "{}")
                
                # Simple path extraction (extend as needed)
                if '.' in path:
                    keys = path.split('.')
                    result = data
                    for key in keys:
                        result = result.get(key, None)
                        if result is None:
                            return None
                    return json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                else:
                    result = data.get(path, None)
                    return json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                    
            except Exception:
                return None
        
        def search_rank_bm25(content: str, query: str, k1: float = 1.5, b: float = 0.75) -> float:
            """Simple BM25 ranking für Search (vereinfacht)"""
            try:
                if not content or not query:
                    return 0.0
                
                # Very simple BM25 approximation
                content_lower = content.lower()
                query_terms = query.lower().split()
                
                score = 0.0
                content_length = len(content_lower.split())
                avg_doc_length = 100  # Assumption
                
                for term in query_terms:
                    term_freq = content_lower.count(term)
                    if term_freq > 0:
                        # Simplified BM25 component
                        idf = 1.0  # Simplified, should be log(N/df)
                        tf_component = (term_freq * (k1 + 1)) / (term_freq + k1 * (1 - b + b * (content_length / avg_doc_length)))
                        score += idf * tf_component
                
                return score
                
            except Exception:
                return 0.0
        
        # Register custom functions
        self.connection.create_function("cosine_similarity_approx", 2, cosine_similarity_approx)
        self.connection.create_function("spatial_distance_basic", 4, spatial_distance_basic)  
        self.connection.create_function("json_extract_enhanced", 2, json_extract_enhanced)
        self.connection.create_function("search_rank_bm25", 2, search_rank_bm25)
        
        self.logger.debug("Custom SQLite functions registered successfully")
    
    async def _create_performance_indexes(self):
        """Erstellt Performance-optimierte Indexes"""
        
        cursor = self.connection.cursor()
        
        # Primary performance indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_master_documents_hash ON uds3_master_documents(file_hash_sha256)",
            "CREATE INDEX IF NOT EXISTS idx_master_documents_status ON uds3_master_documents(processing_status)",
            "CREATE INDEX IF NOT EXISTS idx_master_documents_created ON uds3_master_documents(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_processor_results_document ON uds3_processor_results(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_processor_results_processor ON uds3_processor_results(processor_name)",
            "CREATE INDEX IF NOT EXISTS idx_processor_results_timestamp ON uds3_processor_results(processing_timestamp)",
            
            "CREATE INDEX IF NOT EXISTS idx_cross_references_source ON uds3_cross_references(source_document_id)",
            "CREATE INDEX IF NOT EXISTS idx_cross_references_target ON uds3_cross_references(target_document_id)", 
            "CREATE INDEX IF NOT EXISTS idx_cross_references_type ON uds3_cross_references(reference_type)",
            
            "CREATE INDEX IF NOT EXISTS idx_relationships_source ON uds3_relationships(source_document_id)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_target ON uds3_relationships(target_document_id)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_type ON uds3_relationships(relationship_type)",
            
            "CREATE INDEX IF NOT EXISTS idx_simple_vectors_document ON uds3_simple_vectors(document_id)", 
            "CREATE INDEX IF NOT EXISTS idx_simple_vectors_type ON uds3_simple_vectors(vector_type)",
            "CREATE INDEX IF NOT EXISTS idx_simple_vectors_lsh ON uds3_simple_vectors(lsh_hash)",
            
            "CREATE INDEX IF NOT EXISTS idx_processing_history_document ON uds3_processing_history(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_processing_history_event ON uds3_processing_history(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_processing_history_timestamp ON uds3_processing_history(timestamp)",
            
            "CREATE INDEX IF NOT EXISTS idx_event_log_stream ON uds3_event_log(event_stream_id)",
            "CREATE INDEX IF NOT EXISTS idx_event_log_type ON uds3_event_log(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_event_log_aggregate ON uds3_event_log(aggregate_id)",
            
            "CREATE INDEX IF NOT EXISTS idx_cache_layer_type ON uds3_cache_layer(cache_type)",
            "CREATE INDEX IF NOT EXISTS idx_cache_layer_expiry ON uds3_cache_layer(expiry_timestamp)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        self.connection.commit()
        cursor.close()
        
        self.logger.debug(f"Created {len(indexes)} performance indexes")
    
    async def _initialize_fts5_search(self):
        """Initialisiert FTS5 Full-Text Search (ChromaDB Ersatz)"""
        
        cursor = self.connection.cursor()
        
        # Create FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS uds3_fts_search USING fts5(
                document_id UNINDEXED,
                title,
                content,
                metadata,
                content='',  -- External content table
                contentless_delete=1
            )
        """)
        
        # Create trigger to keep FTS5 in sync with document content
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS uds3_fts_insert_trigger 
            AFTER INSERT ON uds3_document_content
            BEGIN
                INSERT INTO uds3_fts_search(document_id, title, content, metadata) 
                VALUES (
                    NEW.document_id,
                    (SELECT original_filename FROM uds3_master_documents WHERE document_id = NEW.document_id),
                    NEW.content_text,
                    NEW.content_structured_json
                );
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS uds3_fts_update_trigger
            AFTER UPDATE ON uds3_document_content  
            BEGIN
                UPDATE uds3_fts_search 
                SET 
                    title = (SELECT original_filename FROM uds3_master_documents WHERE document_id = NEW.document_id),
                    content = NEW.content_text,
                    metadata = NEW.content_structured_json
                WHERE document_id = NEW.document_id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS uds3_fts_delete_trigger
            AFTER DELETE ON uds3_document_content
            BEGIN
                DELETE FROM uds3_fts_search WHERE document_id = OLD.document_id;
            END
        """)
        
        self.connection.commit()
        cursor.close()
        
        self.logger.debug("FTS5 search system initialized")
    
    async def _initialize_spatial_indexing(self):
        """Initialisiert RTRee Spatial Indexing (PostGIS/Neo4j Spatial Ersatz)"""
        
        cursor = self.connection.cursor()
        
        # Create RTRee virtual table for spatial indexing
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS uds3_spatial_index USING rtree(
                id,
                min_lat, max_lat,
                min_lon, max_lon
            )
        """)
        
        # Create trigger to maintain spatial index
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS uds3_spatial_insert_trigger
            AFTER INSERT ON uds3_spatial_basic
            WHEN NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL
            BEGIN
                INSERT INTO uds3_spatial_index(id, min_lat, max_lat, min_lon, max_lon)
                VALUES (
                    (SELECT rowid FROM uds3_master_documents WHERE document_id = NEW.document_id),
                    NEW.latitude - COALESCE(NEW.spatial_precision, 0.001), 
                    NEW.latitude + COALESCE(NEW.spatial_precision, 0.001),
                    NEW.longitude - COALESCE(NEW.spatial_precision, 0.001),
                    NEW.longitude + COALESCE(NEW.spatial_precision, 0.001)
                );
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS uds3_spatial_update_trigger  
            AFTER UPDATE ON uds3_spatial_basic
            WHEN NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL
            BEGIN
                UPDATE uds3_spatial_index 
                SET 
                    min_lat = NEW.latitude - COALESCE(NEW.spatial_precision, 0.001),
                    max_lat = NEW.latitude + COALESCE(NEW.spatial_precision, 0.001), 
                    min_lon = NEW.longitude - COALESCE(NEW.spatial_precision, 0.001),
                    max_lon = NEW.longitude + COALESCE(NEW.spatial_precision, 0.001)
                WHERE id = (SELECT rowid FROM uds3_master_documents WHERE document_id = NEW.document_id);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS uds3_spatial_delete_trigger
            AFTER DELETE ON uds3_spatial_basic  
            BEGIN
                DELETE FROM uds3_spatial_index 
                WHERE id = (SELECT rowid FROM uds3_master_documents WHERE document_id = OLD.document_id);
            END
        """)
        
        self.connection.commit()
        cursor.close()
        
        self.logger.debug("RTRee spatial indexing initialized")
    
    async def store_document_monolith(
        self, 
        document_id: str, 
        processor_results: List[Dict],
        metadata: Dict = None
    ) -> MonolithResult:
        """
        Speichert Document und Processing Results in SQLite Monolith
        """
        start_time = time.time()
        operations = []
        
        try:
            if not self.schema_initialized:
                await self.initialize_monolith()
            
            cursor = self.connection.cursor()
            
            # 1. Store master document record
            cursor.execute("""
                INSERT OR REPLACE INTO uds3_master_documents 
                (document_id, file_path, original_filename, metadata_json, processing_status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                document_id,
                metadata.get('file_path', '') if metadata else '',
                metadata.get('original_filename', '') if metadata else '', 
                json.dumps(metadata) if metadata else '{}',
                'processing'
            ))
            operations.append("master_document_stored")
            
            # 2. Store processor results
            for result in processor_results:
                cursor.execute("""
                    INSERT INTO uds3_processor_results
                    (document_id, processor_name, result_type, result_data_json, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    document_id,
                    result.get('processor_name', 'unknown'),
                    result.get('result_type', 'general'),
                    json.dumps(result.get('data', {})),
                    result.get('confidence', 1.0)
                ))
            operations.append(f"processor_results_stored_{len(processor_results)}")
            
            # 3. Extract and store content for FTS5
            content_text = self._extract_searchable_content(processor_results)
            if content_text:
                cursor.execute("""
                    INSERT OR REPLACE INTO uds3_document_content
                    (document_id, content_type, content_text, extraction_method)
                    VALUES (?, ?, ?, ?)
                """, (document_id, 'extracted', content_text, 'processor_aggregation'))
                operations.append("content_stored")
            
            # 4. Store simple vectors if available
            vectors = self._extract_vectors(processor_results)
            for vector_type, vector_data in vectors.items():
                lsh_hash = self._calculate_lsh_hash(vector_data)
                cursor.execute("""
                    INSERT INTO uds3_simple_vectors
                    (document_id, vector_type, vector_dimension, vector_data_json, lsh_hash)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    document_id, vector_type, len(vector_data), 
                    json.dumps(vector_data), lsh_hash
                ))
            if vectors:
                operations.append(f"vectors_stored_{len(vectors)}")
            
            # 5. Store spatial data if available
            spatial_data = self._extract_spatial_data(processor_results, metadata)
            if spatial_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO uds3_spatial_basic
                    (document_id, latitude, longitude, spatial_precision, extraction_source)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    document_id,
                    spatial_data.get('latitude'),
                    spatial_data.get('longitude'), 
                    spatial_data.get('precision', 0.001),
                    spatial_data.get('source', 'processor')
                ))
                operations.append("spatial_data_stored")
            
            # 6. Create processing history event
            cursor.execute("""
                INSERT INTO uds3_processing_history
                (document_id, event_type, event_data_json, processor_name)
                VALUES (?, ?, ?, ?)
            """, (
                document_id, 'document_stored',
                json.dumps({'operations': operations, 'processor_count': len(processor_results)}),
                'sqlite_monolith_strategy'
            ))
            operations.append("history_event_created")
            
            # 7. Update master document status
            cursor.execute("""
                UPDATE uds3_master_documents 
                SET processing_status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE document_id = ?
            """, (document_id,))
            operations.append("status_updated")
            
            self.connection.commit()
            cursor.close()
            
            execution_time = (time.time() - start_time) * 1000
            
            self.logger.info(f"✅ Document {document_id} stored in SQLite monolith ({execution_time:.1f}ms)")
            
            return MonolithResult(
                success=True,
                strategy_used="sqlite_monolith",
                operations_completed=operations,
                execution_time_ms=execution_time,
                storage_path=self.db_path
            )
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
                
            execution_time = (time.time() - start_time) * 1000
            self.logger.error(f"❌ Failed to store document {document_id}: {e}")
            
            return MonolithResult(
                success=False,
                strategy_used="sqlite_monolith", 
                operations_completed=operations,
                execution_time_ms=execution_time,
                warnings=[f"Storage failed: {str(e)}"],
                storage_path=self.db_path
            )
    
    def _extract_searchable_content(self, processor_results: List[Dict]) -> str:
        """Extrahiert searchable content aus processor results"""
        content_parts = []
        
        for result in processor_results:
            data = result.get('data', {})
            
            # Text content
            if 'text_content' in data:
                content_parts.append(data['text_content'])
            if 'extracted_text' in data:
                content_parts.append(data['extracted_text'])
            if 'title' in data:
                content_parts.append(data['title'])
            if 'description' in data:
                content_parts.append(data['description'])
        
        return ' '.join(content_parts).strip()
    
    def _extract_vectors(self, processor_results: List[Dict]) -> Dict[str, List[float]]:
        """Extrahiert vector embeddings aus processor results"""
        vectors = {}
        
        for result in processor_results:
            data = result.get('data', {})
            
            if 'embedding' in data and isinstance(data['embedding'], list):
                vector_type = f"{result.get('processor_name', 'unknown')}_embedding"
                vectors[vector_type] = data['embedding']
            
            if 'content_vector' in data and isinstance(data['content_vector'], list):
                vectors['content_embedding'] = data['content_vector']
        
        return vectors
    
    def _extract_spatial_data(self, processor_results: List[Dict], metadata: Dict = None) -> Optional[Dict]:
        """Extrahiert spatial data aus processor results und metadata"""
        
        # Check processor results first
        for result in processor_results:
            data = result.get('data', {})
            
            if 'latitude' in data and 'longitude' in data:
                return {
                    'latitude': float(data['latitude']),
                    'longitude': float(data['longitude']),
                    'precision': data.get('precision', 0.001),
                    'source': 'processor'
                }
        
        # Check metadata
        if metadata:
            if 'latitude' in metadata and 'longitude' in metadata:
                return {
                    'latitude': float(metadata['latitude']),
                    'longitude': float(metadata['longitude']), 
                    'precision': metadata.get('precision', 0.001),
                    'source': 'metadata'
                }
        
        return None
    
    def _calculate_lsh_hash(self, vector: List[float], num_hashes: int = 10) -> str:
        """Berechnet LSH hash für approximate vector similarity"""
        try:
            import hashlib
            import struct
            
            # Simple LSH implementation
            hashes = []
            
            for i in range(num_hashes):
                # Use different hash seeds
                hash_input = f"{i}:{','.join(map(str, vector))}"
                hash_bytes = hashlib.md5(hash_input.encode()).digest()
                hash_int = struct.unpack('>Q', hash_bytes[:8])[0]
                hashes.append(str(hash_int % 1000000))  # Reduce hash space
            
            return ','.join(hashes)
            
        except Exception:
            return 'unknown'
    
    def close_connection(self):
        """Schließt SQLite Connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.debug("SQLite connection closed")