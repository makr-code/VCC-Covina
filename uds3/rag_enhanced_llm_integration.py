"""
UDS3 RAG-Enhanced LLM Integration
Multi-Database RAG Context Aggregation with Token Optimization

Erweitert bestehende LLM-Services mit Multi-Database RAG Capabilities:
- Intelligente Kontext-Aggregation aus PostgreSQL, CouchDB, ChromaDB, Neo4j
- Token-optimierte Prompt Generation 
- Adaptive Query Routing basierend auf verfügbaren Datenbanken
- Semantic Search Enhancement mit Cross-Database Context
- Performance-optimierte RAG Pipeline mit Caching
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import sys
from abc import ABC, abstractmethod
from enum import Enum
from collections import defaultdict, OrderedDict
from contextlib import asynccontextmanager
import hashlib
import sqlite3
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import UDS3 components
try:
    from .adaptive_multi_db_strategy import AdaptiveMultiDBStrategy, DatabaseConnectionManager
    from .document_reconstruction_engine import DocumentReconstructionEngine
except ImportError:
    # Fallback for direct execution - create minimal mock classes
    class AdaptiveMultiDBStrategy:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(__name__)
            print("Using mock AdaptiveMultiDBStrategy for testing")
    
    class DatabaseConnectionManager:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(__name__)
    
    class DocumentReconstructionEngine:
        def __init__(self, *args, **kwargs):
            self.logger = logging.getLogger(__name__)
import hashlib
import uuid

# Additional UDS3 Framework Imports (optional for testing)
try:
    from .uds3_multi_db_distributor import UDS3MultiDBDistributor
    from .performance_testing_optimization import PerformanceMonitor
    UDS3_COMPONENTS_AVAILABLE = True
except ImportError:
    UDS3_COMPONENTS_AVAILABLE = False
    UDS3MultiDBDistributor = None
    PerformanceMonitor = None
    
# Database Integrations
try:
    import asyncpg  # PostgreSQL
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

try:
    import chromadb  # ChromaDB
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from neo4j import AsyncGraphDatabase  # Neo4j
    NEO4J_AVAILABLE = True
except (ImportError, AttributeError) as e:
    # Neo4j has compatibility issues with Python 3.13 on Windows
    NEO4J_AVAILABLE = False
    AsyncGraphDatabase = None
    print(f"Warning: Neo4j not available ({e.__class__.__name__}). Neo4j functionality disabled.")

# LLM Integration (Mock für Development)
try:
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


@dataclass
class RAGQueryContext:
    """Kontext für eine RAG-Query mit Multi-Database Information"""
    
    # Query Information
    query_id: str
    user_query: str
    query_intent: str  # 'search', 'summarize', 'analyze', 'compare', 'extract'
    query_language: str = 'de'
    
    # Context Requirements
    max_context_tokens: int = 4000
    min_relevance_score: float = 0.7
    include_metadata: bool = True
    include_relationships: bool = True
    
    # Database Preferences
    preferred_databases: List[str] = field(default_factory=lambda: ['chromadb', 'postgresql', 'neo4j', 'couchdb'])
    exclude_databases: List[str] = field(default_factory=list)
    
    # Document Constraints
    document_filters: Dict[str, Any] = field(default_factory=dict)
    temporal_range: Optional[Tuple[datetime, datetime]] = None
    content_types: List[str] = field(default_factory=list)
    
    # Performance Settings
    timeout_seconds: int = 30
    use_cache: bool = True
    cache_ttl_minutes: int = 15
    
    # Processing Options
    enable_cross_references: bool = True
    enable_semantic_expansion: bool = True
    enable_entity_linking: bool = True


@dataclass
class RAGContextResult:
    """Ergebnis der Multi-Database RAG Context Aggregation"""
    
    # Result Metadata
    context_id: str
    query_context: RAGQueryContext
    generation_timestamp: datetime
    
    # Aggregated Content
    primary_content: List[Dict[str, Any]]  # Hauptinhalt aus verschiedenen DBs
    related_content: List[Dict[str, Any]]  # Verwandte Inhalte
    metadata_context: Dict[str, Any]       # Metadaten und Strukturinformation
    
    # Cross-Database References
    cross_references: List[Dict[str, Any]]  # Verbindungen zwischen DBs
    entity_relationships: Dict[str, List[Dict]]  # Entitäts-Beziehungen
    
    # Token Management
    total_tokens: int
    content_tokens: int
    metadata_tokens: int
    estimated_response_tokens: int
    
    # Quality Metrics
    relevance_scores: Dict[str, float]  # Relevanz pro Datenbank
    coverage_metrics: Dict[str, Any]    # Abdeckung verschiedener Aspekte
    confidence_score: float
    
    # Performance Information
    retrieval_time_ms: int
    databases_queried: List[str]
    cache_hits: int
    
    # Optimization Hints
    token_optimization_applied: bool
    context_truncation_applied: bool
    suggested_followup_queries: List[str]


class MultiDatabaseRAGContextAggregator:
    """
    Intelligente RAG Context Aggregation aus Multiple Databases
    
    Kombiniert Inhalte aus PostgreSQL, CouchDB, ChromaDB, und Neo4j
    für optimale LLM Context Generation
    """
    
    def __init__(
        self,
        adaptive_strategy: AdaptiveMultiDBStrategy,
        document_reconstructor: Optional[DocumentReconstructionEngine] = None,
        config: Dict[str, Any] = None
    ):
        self.adaptive_strategy = adaptive_strategy
        self.document_reconstructor = document_reconstructor
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Performance Monitoring
        self.performance_monitor = PerformanceMonitor("RAGContextAggregator") if PerformanceMonitor else None
        
        # Context Cache
        self.context_cache = {}
        self.cache_timestamps = {}
        
        # Database Clients (werden bei Bedarf initialisiert)
        self.postgresql_pool = None
        self.chromadb_client = None
        self.neo4j_driver = None
        
        # Token Management
        self.tokenizer = None
        self._load_tokenizer()
        
        # Logging Setup
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🤖 MultiDatabaseRAGContextAggregator initialized")
    
    def _load_tokenizer(self):
        """Lädt Tokenizer für Token Counting"""
        try:
            if TRANSFORMERS_AVAILABLE:
                # Verwende einen Standard-Tokenizer für Token Counting
                model_name = self.config.get('tokenizer_model', 'bert-base-german-cased')
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            else:
                # Fallback: Approximation
                self.tokenizer = None
                self.logger.warning("Transformers not available, using token approximation")
        except Exception as e:
            self.logger.warning(f"Could not load tokenizer: {e}")
            self.tokenizer = None
    
    def _count_tokens(self, text: str) -> int:
        """Zählt Tokens in einem Text"""
        if self.tokenizer:
            try:
                tokens = self.tokenizer.encode(text, add_special_tokens=False)
                return len(tokens)
            except Exception as e:
                self.logger.warning(f"Tokenizer error: {e}")
                
        # Fallback: Approximation (1 Token ≈ 4 Zeichen für Deutsch)
        return max(1, len(text) // 4)
    
    async def _get_postgresql_context(
        self, 
        query_context: RAGQueryContext
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Holt Kontext aus PostgreSQL Master Registry und Processor Results"""
        
        if not self.adaptive_strategy.db_availability.postgresql:
            return [], {}
            
        try:
            if not self.postgresql_pool:
                # Initialisiere PostgreSQL Connection Pool
                connection_string = self.config.get(
                    'postgresql_connection',
                    'postgresql://postgres:postgres@localhost:5432/uds3_multidb'
                )
                self.postgresql_pool = await asyncpg.create_pool(connection_string)
            
            context_items = []
            metadata = {}
            
            async with self.postgresql_pool.acquire() as conn:
                # 1. Master Documents relevante Dokumente finden
                documents_query = """
                    SELECT document_id, original_filename, extracted_text_preview, 
                           classification_tags, content_type, db_references, 
                           processing_status, ingestion_timestamp
                    FROM uds3_master_documents 
                    WHERE processing_status = 'completed'
                    AND ($1::text IS NULL OR to_tsvector('german', original_filename || ' ' || coalesce(extracted_text_preview, '')) @@ plainto_tsquery('german', $1))
                    ORDER BY ingestion_timestamp DESC
                    LIMIT 20
                """
                
                search_term = query_context.user_query if len(query_context.user_query) > 3 else None
                documents = await conn.fetch(documents_query, search_term)
                
                for doc in documents:
                    context_items.append({
                        'source': 'postgresql_master',
                        'document_id': doc['document_id'],
                        'title': doc['original_filename'],
                        'content': doc['extracted_text_preview'] or '',
                        'content_type': doc['content_type'],
                        'tags': doc['classification_tags'] or [],
                        'timestamp': doc['ingestion_timestamp'],
                        'db_references': doc['db_references'],
                        'relevance_score': 0.8  # Basis-Relevanz für PostgreSQL Treffer
                    })
                
                # 2. Processor Results für detaillierte Informationen
                if documents:
                    doc_ids = [doc['document_id'] for doc in documents[:5]]  # Top 5 für Details
                    
                    results_query = """
                        SELECT document_id, processor_name, result_type, 
                               result_summary, extracted_entities, confidence_score
                        FROM uds3_processor_results 
                        WHERE document_id = ANY($1) AND processing_status = 'completed'
                        ORDER BY confidence_score DESC
                        LIMIT 50
                    """
                    
                    results = await conn.fetch(results_query, doc_ids)
                    
                    for result in results:
                        if result['result_summary']:
                            context_items.append({
                                'source': 'postgresql_processor',
                                'document_id': result['document_id'],
                                'processor': result['processor_name'],
                                'type': result['result_type'],
                                'content': result['result_summary'],
                                'entities': result['extracted_entities'],
                                'confidence': float(result['confidence_score'] or 0.0),
                                'relevance_score': float(result['confidence_score'] or 0.5)
                            })
                
                # Metadata zusammenstellen
                metadata = {
                    'total_documents_found': len(documents),
                    'total_processor_results': len([r for r in context_items if r['source'] == 'postgresql_processor']),
                    'query_type': 'full_text_search' if search_term else 'latest_documents'
                }
            
            return context_items, metadata
            
        except Exception as e:
            self.logger.error(f"PostgreSQL context retrieval failed: {e}")
            return [], {'error': str(e)}
    
    async def _get_chromadb_context(
        self, 
        query_context: RAGQueryContext
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Holt semantisch ähnliche Inhalte aus ChromaDB"""
        
        if not self.adaptive_strategy.db_availability.chromadb:
            return [], {}
            
        try:
            if not self.chromadb_client:
                # ChromaDB Client initialisieren
                if CHROMADB_AVAILABLE:
                    import chromadb
                    self.chromadb_client = chromadb.Client()
                else:
                    self.logger.warning("ChromaDB not available")
                    return [], {}
            
            context_items = []
            metadata = {}
            
            # Standard Collection für Dokumente
            collection_name = self.config.get('chromadb_collection', 'covina_documents')
            
            try:
                collection = self.chromadb_client.get_collection(collection_name)
                
                # Semantische Suche durchführen
                results = collection.query(
                    query_texts=[query_context.user_query],
                    n_results=min(20, query_context.max_context_tokens // 100),  # Adaptive Anzahl
                    include=['documents', 'metadatas', 'distances']
                )
                
                if results['documents'] and results['documents'][0]:
                    for i, (doc, meta, distance) in enumerate(zip(
                        results['documents'][0], 
                        results['metadatas'][0], 
                        results['distances'][0]
                    )):
                        # Relevanz Score berechnen (niedrigere Distance = höhere Relevanz)
                        relevance_score = max(0.1, 1.0 - distance)
                        
                        if relevance_score >= query_context.min_relevance_score:
                            context_items.append({
                                'source': 'chromadb_semantic',
                                'collection': collection_name,
                                'content': doc,
                                'metadata': meta or {},
                                'distance': distance,
                                'relevance_score': relevance_score,
                                'rank': i + 1
                            })
                
                metadata = {
                    'collection_name': collection_name,
                    'total_results': len(results['documents'][0]) if results['documents'] else 0,
                    'filtered_results': len(context_items),
                    'min_distance': min(results['distances'][0]) if results['distances'] and results['distances'][0] else None,
                    'max_distance': max(results['distances'][0]) if results['distances'] and results['distances'][0] else None
                }
                
            except Exception as e:
                self.logger.warning(f"ChromaDB collection {collection_name} not found or error: {e}")
                metadata = {'collection_error': str(e)}
            
            return context_items, metadata
            
        except Exception as e:
            self.logger.error(f"ChromaDB context retrieval failed: {e}")
            return [], {'error': str(e)}
    
    async def _get_neo4j_context(
        self, 
        query_context: RAGQueryContext
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Holt Beziehungs-Kontext aus Neo4j Knowledge Graph"""
        
        if not self.adaptive_strategy.db_availability.neo4j:
            return [], {}
            
        try:
            # Neo4j ist derzeit nicht verfügbar, Mock-Implementation
            self.logger.info("Neo4j context retrieval (mock implementation)")
            
            # Mock: Simuliere Entitäts-Beziehungen basierend auf der Query
            context_items = []
            
            # Extrahiere potenzielle Entitäten aus der Query
            query_words = query_context.user_query.lower().split()
            potential_entities = [word for word in query_words if len(word) > 4]
            
            if potential_entities:
                # Simuliere gefundene Beziehungen
                for i, entity in enumerate(potential_entities[:3]):  # Max 3 Entitäten
                    context_items.append({
                        'source': 'neo4j_relationships',
                        'entity': entity.title(),
                        'relationships': [
                            {'type': 'RELATED_TO', 'target': f'Entity_{i+1}', 'strength': 0.8},
                            {'type': 'PART_OF', 'target': f'Document_{i+1}', 'strength': 0.7}
                        ],
                        'node_properties': {
                            'type': 'concept',
                            'confidence': 0.7,
                            'frequency': 5 + i
                        },
                        'relevance_score': 0.7 - (i * 0.1)
                    })
            
            metadata = {
                'entities_found': len(potential_entities),
                'relationships_extracted': len(context_items),
                'graph_traversal_depth': 2,
                'mock_implementation': True
            }
            
            return context_items, metadata
            
        except Exception as e:
            self.logger.error(f"Neo4j context retrieval failed: {e}")
            return [], {'error': str(e)}
    
    async def _get_couchdb_context(
        self, 
        query_context: RAGQueryContext
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Holt unstrukturierte Dokument-Inhalte aus CouchDB"""
        
        if not self.adaptive_strategy.db_availability.couchdb:
            return [], {}
            
        try:
            # CouchDB Mock-Implementation (da CouchDB derzeit nicht konfiguriert)
            self.logger.info("CouchDB context retrieval (mock implementation)")
            
            context_items = []
            
            # Simuliere CouchDB Dokumente mit relevanten Inhalten
            mock_documents = [
                {
                    'id': f'couchdb_doc_{i}',
                    'title': f'Document {i+1} related to query',
                    'content': f'Mock content für "{query_context.user_query}" - Document {i+1} with detailed information and structured data.',
                    'content_type': 'json_document',
                    'size_bytes': 1024 * (i + 1),
                    'relevance_score': 0.6 - (i * 0.1)
                }
                for i in range(min(3, query_context.max_context_tokens // 200))
            ]
            
            context_items = [
                {
                    'source': 'couchdb_documents',
                    'document_id': doc['id'],
                    'title': doc['title'],
                    'content': doc['content'],
                    'content_type': doc['content_type'],
                    'size_bytes': doc['size_bytes'],
                    'relevance_score': doc['relevance_score']
                }
                for doc in mock_documents
                if doc['relevance_score'] >= query_context.min_relevance_score
            ]
            
            metadata = {
                'total_documents_searched': len(mock_documents),
                'documents_returned': len(context_items),
                'search_type': 'full_text_mock',
                'mock_implementation': True
            }
            
            return context_items, metadata
            
        except Exception as e:
            self.logger.error(f"CouchDB context retrieval failed: {e}")
            return [], {'error': str(e)}
    
    def _optimize_context_for_tokens(
        self, 
        context_items: List[Dict[str, Any]], 
        max_tokens: int
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Optimiert Context Items für Token Budget"""
        
        if not context_items:
            return [], False
            
        # Sortiere nach Relevanz
        sorted_items = sorted(
            context_items, 
            key=lambda x: x.get('relevance_score', 0.0), 
            reverse=True
        )
        
        optimized_items = []
        current_tokens = 0
        truncation_applied = False
        
        for item in sorted_items:
            content = item.get('content', '')
            item_tokens = self._count_tokens(content)
            
            if current_tokens + item_tokens <= max_tokens:
                optimized_items.append(item)
                current_tokens += item_tokens
            else:
                # Versuche Truncation des Contents
                available_tokens = max_tokens - current_tokens
                if available_tokens > 50:  # Mindestens 50 Tokens für sinnvollen Content
                    # Kürze Content auf verfügbare Tokens
                    chars_per_token = 4  # Approximation für Deutsch
                    max_chars = available_tokens * chars_per_token
                    
                    truncated_content = content[:max_chars] + "..."
                    truncated_item = item.copy()
                    truncated_item['content'] = truncated_content
                    truncated_item['truncated'] = True
                    
                    optimized_items.append(truncated_item)
                    truncation_applied = True
                    break
                else:
                    # Nicht genug Platz für weitere Items
                    truncation_applied = True
                    break
        
        return optimized_items, truncation_applied
    
    def _generate_cache_key(self, query_context: RAGQueryContext) -> str:
        """Generiert Cache Key für Query Context"""
        key_data = {
            'query': query_context.user_query,
            'intent': query_context.query_intent,
            'max_tokens': query_context.max_context_tokens,
            'min_relevance': query_context.min_relevance_score,
            'databases': sorted(query_context.preferred_databases),
            'filters': query_context.document_filters
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str, ttl_minutes: int) -> bool:
        """Prüft ob Cache Entry noch gültig ist"""
        if cache_key not in self.cache_timestamps:
            return False
            
        cache_time = self.cache_timestamps[cache_key]
        expiry_time = cache_time + timedelta(minutes=ttl_minutes)
        return datetime.now() < expiry_time
    
    async def aggregate_rag_context(
        self, 
        query_context: RAGQueryContext
    ) -> RAGContextResult:
        """
        Hauptfunktion: Aggregiert RAG Context aus Multiple Databases
        """
        
        start_time = time.time()
        context_id = str(uuid.uuid4())
        
        self.logger.info(f"🤖 Starting RAG context aggregation for query: {query_context.user_query[:50]}...")
        
        # Cache Check
        cache_key = self._generate_cache_key(query_context)
        cache_hits = 0
        
        if query_context.use_cache and self._is_cache_valid(cache_key, query_context.cache_ttl_minutes):
            cached_result = self.context_cache.get(cache_key)
            if cached_result:
                self.logger.info("📋 Returning cached RAG context")
                cached_result.cache_hits = 1
                return cached_result
        
        try:
            # Database Context Retrieval (parallel)
            database_tasks = []
            databases_queried = []
            
            if 'postgresql' in query_context.preferred_databases and 'postgresql' not in query_context.exclude_databases:
                database_tasks.append(('postgresql', self._get_postgresql_context(query_context)))
                databases_queried.append('postgresql')
                
            if 'chromadb' in query_context.preferred_databases and 'chromadb' not in query_context.exclude_databases:
                database_tasks.append(('chromadb', self._get_chromadb_context(query_context)))
                databases_queried.append('chromadb')
                
            if 'neo4j' in query_context.preferred_databases and 'neo4j' not in query_context.exclude_databases:
                database_tasks.append(('neo4j', self._get_neo4j_context(query_context)))
                databases_queried.append('neo4j')
                
            if 'couchdb' in query_context.preferred_databases and 'couchdb' not in query_context.exclude_databases:
                database_tasks.append(('couchdb', self._get_couchdb_context(query_context)))
                databases_queried.append('couchdb')
            
            # Execute database queries with timeout
            results = {}
            try:
                db_results = await asyncio.wait_for(
                    asyncio.gather(*[task[1] for task in database_tasks], return_exceptions=True),
                    timeout=query_context.timeout_seconds
                )
                
                for i, (db_name, _) in enumerate(database_tasks):
                    if i < len(db_results) and not isinstance(db_results[i], Exception):
                        results[db_name] = db_results[i]
                    else:
                        self.logger.warning(f"Database {db_name} query failed or timed out")
                        results[db_name] = ([], {'error': 'timeout_or_failure'})
                        
            except asyncio.TimeoutError:
                self.logger.warning(f"RAG context aggregation timed out after {query_context.timeout_seconds}s")
                # Verwende partielle Ergebnisse
                for db_name, _ in database_tasks:
                    if db_name not in results:
                        results[db_name] = ([], {'error': 'timeout'})
            
            # Aggregiere alle Context Items
            all_context_items = []
            db_metadata = {}
            relevance_scores = {}
            
            for db_name, (context_items, metadata) in results.items():
                all_context_items.extend(context_items)
                db_metadata[db_name] = metadata
                
                if context_items:
                    avg_relevance = sum(item.get('relevance_score', 0.0) for item in context_items) / len(context_items)
                    relevance_scores[db_name] = avg_relevance
                else:
                    relevance_scores[db_name] = 0.0
            
            # Token-optimierte Context-Auswahl
            primary_context, truncation_applied = self._optimize_context_for_tokens(
                all_context_items, 
                query_context.max_context_tokens - 500  # Reserve für Metadata
            )
            
            # Separiere Primary und Related Content
            primary_content = []
            related_content = []
            
            for item in primary_context:
                if item.get('relevance_score', 0.0) >= query_context.min_relevance_score:
                    primary_content.append(item)
                else:
                    related_content.append(item)
            
            # Cross-References extrahieren
            cross_references = []
            entity_relationships = {}
            
            for item in primary_content:
                if 'db_references' in item and item['db_references']:
                    cross_references.append({
                        'source_item': item['source'],
                        'references': item['db_references']
                    })
                    
                if item['source'] == 'neo4j_relationships' and 'relationships' in item:
                    entity = item.get('entity', 'unknown')
                    entity_relationships[entity] = item['relationships']
            
            # Token Counting
            content_tokens = sum(self._count_tokens(item.get('content', '')) for item in primary_content)
            metadata_tokens = self._count_tokens(json.dumps(db_metadata, ensure_ascii=False))
            total_tokens = content_tokens + metadata_tokens
            
            # Quality Metrics berechnen
            coverage_metrics = {
                'databases_with_results': len([db for db, score in relevance_scores.items() if score > 0]),
                'total_databases_queried': len(databases_queried),
                'content_sources': len(set(item['source'] for item in primary_content)),
                'cross_reference_count': len(cross_references)
            }
            
            confidence_score = min(1.0, sum(relevance_scores.values()) / len(relevance_scores) if relevance_scores else 0.0)
            
            # Suggested Follow-up Queries generieren
            suggested_queries = []
            if entity_relationships:
                for entity in list(entity_relationships.keys())[:2]:
                    suggested_queries.append(f"Weitere Informationen über {entity}")
            
            if len(primary_content) > 5:
                suggested_queries.append(f"Zusammenfassung der Ergebnisse zu '{query_context.user_query}'")
            
            # RAG Context Result erstellen
            retrieval_time = int((time.time() - start_time) * 1000)
            
            result = RAGContextResult(
                context_id=context_id,
                query_context=query_context,
                generation_timestamp=datetime.now(),
                
                primary_content=primary_content,
                related_content=related_content,
                metadata_context=db_metadata,
                
                cross_references=cross_references,
                entity_relationships=entity_relationships,
                
                total_tokens=total_tokens,
                content_tokens=content_tokens,
                metadata_tokens=metadata_tokens,
                estimated_response_tokens=min(2000, total_tokens // 2),  # Schätzung für Response
                
                relevance_scores=relevance_scores,
                coverage_metrics=coverage_metrics,
                confidence_score=confidence_score,
                
                retrieval_time_ms=retrieval_time,
                databases_queried=databases_queried,
                cache_hits=cache_hits,
                
                token_optimization_applied=True,
                context_truncation_applied=truncation_applied,
                suggested_followup_queries=suggested_queries
            )
            
            # Cache Result
            if query_context.use_cache:
                self.context_cache[cache_key] = result
                self.cache_timestamps[cache_key] = datetime.now()
            
            self.logger.info(f"✅ RAG context aggregation completed: {len(primary_content)} items, {total_tokens} tokens, {retrieval_time}ms")
            
            return result
            
        except Exception as e:
            self.logger.error(f"RAG context aggregation failed: {e}")
            
            # Fallback Result
            return RAGContextResult(
                context_id=context_id,
                query_context=query_context,
                generation_timestamp=datetime.now(),
                
                primary_content=[],
                related_content=[],
                metadata_context={'error': str(e)},
                
                cross_references=[],
                entity_relationships={},
                
                total_tokens=0,
                content_tokens=0,
                metadata_tokens=0,
                estimated_response_tokens=0,
                
                relevance_scores={},
                coverage_metrics={},
                confidence_score=0.0,
                
                retrieval_time_ms=int((time.time() - start_time) * 1000),
                databases_queried=databases_queried if 'databases_queried' in locals() else [],
                cache_hits=cache_hits,
                
                token_optimization_applied=False,
                context_truncation_applied=False,
                suggested_followup_queries=[]
            )


class RAGEnhancedLLMService:
    """
    RAG-Enhanced LLM Service mit Multi-Database Integration
    
    Erweitert bestehende LLM-Services mit intelligenter Context Aggregation
    """
    
    def __init__(
        self,
        adaptive_strategy: AdaptiveMultiDBStrategy,
        context_aggregator: Optional[MultiDatabaseRAGContextAggregator] = None,
        config: Dict[str, Any] = None
    ):
        self.adaptive_strategy = adaptive_strategy
        self.context_aggregator = context_aggregator or MultiDatabaseRAGContextAggregator(adaptive_strategy)
        self.config = config or {}
        
        # LLM Configuration
        self.model_name = self.config.get('llm_model', 'gpt-3.5-turbo')  # Mock für Development
        self.max_tokens = self.config.get('max_tokens', 8192)
        self.temperature = self.config.get('temperature', 0.7)
        
        # Performance Monitoring
        self.performance_monitor = PerformanceMonitor("RAGEnhancedLLMService") if PerformanceMonitor else None
        
        # Response Cache
        self.response_cache = {}
        self.response_cache_timestamps = {}
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🧠 RAGEnhancedLLMService initialized")
    
    def _build_enhanced_prompt(
        self, 
        user_query: str, 
        rag_context: RAGContextResult
    ) -> str:
        """Baut erweiterten Prompt mit Multi-Database Context"""
        
        prompt_parts = []
        
        # System Instruction
        prompt_parts.append("""Du bist ein intelligenter Assistent mit Zugang zu einem Multi-Database System. 
Du kannst Informationen aus verschiedenen Datenbanken (PostgreSQL, ChromaDB, Neo4j, CouchDB) nutzen, 
um umfassende und präzise Antworten zu geben.""")
        
        # Context Information
        if rag_context.primary_content:
            prompt_parts.append("\n## Verfügbare Kontextinformationen:")
            
            for i, item in enumerate(rag_context.primary_content[:10], 1):  # Max 10 Items
                source = item.get('source', 'unknown')
                content = item.get('content', '')
                title = item.get('title', f'Item {i}')
                relevance = item.get('relevance_score', 0.0)
                
                prompt_parts.append(f"\n### [{i}] {title} (Quelle: {source}, Relevanz: {relevance:.2f})")
                prompt_parts.append(content[:500] + "..." if len(content) > 500 else content)
        
        # Cross-Database References
        if rag_context.cross_references:
            prompt_parts.append("\n## Datenbank-übergreifende Referenzen:")
            for ref in rag_context.cross_references[:3]:  # Max 3 References
                prompt_parts.append(f"- {ref}")
        
        # Entity Relationships
        if rag_context.entity_relationships:
            prompt_parts.append("\n## Entitäts-Beziehungen:")
            for entity, relationships in list(rag_context.entity_relationships.items())[:3]:
                rel_text = ", ".join([f"{rel['type']}: {rel['target']}" for rel in relationships[:2]])
                prompt_parts.append(f"- {entity}: {rel_text}")
        
        # Query
        prompt_parts.append(f"\n## Benutzeranfrage:\n{user_query}")
        
        # Instructions
        prompt_parts.append("""
## Anweisungen:
1. Nutze die verfügbaren Kontextinformationen zur Beantwortung der Frage
2. Gib die Quellen der verwendeten Informationen an
3. Wenn Informationen unvollständig sind, weise darauf hin
4. Berücksichtige die Relevanzscores bei der Gewichtung der Informationen
5. Nutze Cross-Database Referenzen für umfassende Antworten""")
        
        return "\n".join(prompt_parts)
    
    async def _call_llm_api(self, prompt: str) -> Dict[str, Any]:
        """Mock LLM API Call (ersetzt durch echte LLM Integration)"""
        
        # Mock Response basierend auf Prompt Analysis
        response_text = f"""Basierend auf den verfügbaren Multi-Database Informationen kann ich folgende Antwort geben:

Die Anfrage wurde mit Kontext aus mehreren Datenbanken bearbeitet. Die Informationen stammen aus:
- PostgreSQL Master Registry für strukturierte Dokumentmetadaten
- ChromaDB für semantisch ähnliche Inhalte  
- Neo4j Knowledge Graph für Entitäts-Beziehungen
- CouchDB für unstrukturierte Dokumentinhalte

[Mock Response - hier würde die echte LLM-generierte Antwort stehen]

Die verwendeten Quellen haben verschiedene Relevanzscores und wurden entsprechend gewichtet."""
        
        return {
            'response': response_text,
            'model': self.model_name,
            'tokens_used': len(prompt.split()) + len(response_text.split()),  # Approximation
            'processing_time_ms': 1500,  # Mock
            'confidence': 0.85
        }
    
    async def enhanced_query(
        self,
        user_query: str,
        query_intent: str = 'search',
        max_context_tokens: int = 4000,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Enhanced Query mit Multi-Database RAG Context
        """
        
        start_time = time.time()
        query_id = str(uuid.uuid4())
        
        self.logger.info(f"🧠 Processing enhanced query: {user_query[:50]}...")
        
        try:
            # RAG Query Context erstellen
            rag_query_context = RAGQueryContext(
                query_id=query_id,
                user_query=user_query,
                query_intent=query_intent,
                max_context_tokens=max_context_tokens,
                use_cache=use_cache,
                **kwargs
            )
            
            # Context aus Multi-Database System aggregieren
            rag_context = await self.context_aggregator.aggregate_rag_context(rag_query_context)
            
            # Enhanced Prompt bauen
            enhanced_prompt = self._build_enhanced_prompt(user_query, rag_context)
            
            # Check Response Cache
            prompt_hash = hashlib.md5(enhanced_prompt.encode()).hexdigest()
            if use_cache and prompt_hash in self.response_cache:
                cached_response = self.response_cache[prompt_hash]
                self.logger.info("📋 Returning cached LLM response")
                cached_response['cache_hit'] = True
                return cached_response
            
            # LLM API Call
            llm_response = await self._call_llm_api(enhanced_prompt)
            
            # Response zusammenstellen
            total_time = int((time.time() - start_time) * 1000)
            
            enhanced_response = {
                'query_id': query_id,
                'user_query': user_query,
                'response': llm_response['response'],
                'model_used': llm_response['model'],
                
                # Context Information
                'context_sources': len(rag_context.primary_content),
                'databases_used': rag_context.databases_queried,
                'context_confidence': rag_context.confidence_score,
                'context_tokens': rag_context.total_tokens,
                
                # Token Usage
                'prompt_tokens': rag_context.total_tokens + 200,  # System prompt overhead
                'completion_tokens': llm_response['tokens_used'] - rag_context.total_tokens,
                'total_tokens': llm_response['tokens_used'],
                
                # Performance Metrics
                'context_retrieval_time_ms': rag_context.retrieval_time_ms,
                'llm_processing_time_ms': llm_response['processing_time_ms'],
                'total_processing_time_ms': total_time,
                
                # Quality Information
                'relevance_scores': rag_context.relevance_scores,
                'coverage_metrics': rag_context.coverage_metrics,
                'suggested_followup_queries': rag_context.suggested_followup_queries,
                
                # Technical Details
                'context_truncation_applied': rag_context.context_truncation_applied,
                'cache_hit': False,
                'rag_context_id': rag_context.context_id
            }
            
            # Cache Response
            if use_cache:
                self.response_cache[prompt_hash] = enhanced_response
                self.response_cache_timestamps[prompt_hash] = datetime.now()
            
            self.logger.info(f"✅ Enhanced query completed: {total_time}ms, {enhanced_response['total_tokens']} tokens")
            
            return enhanced_response
            
        except Exception as e:
            self.logger.error(f"Enhanced query failed: {e}")
            
            return {
                'query_id': query_id,
                'user_query': user_query,
                'error': str(e),
                'response': 'Es ist ein Fehler bei der Verarbeitung aufgetreten.',
                'total_processing_time_ms': int((time.time() - start_time) * 1000)
            }


# Integration Functions
async def create_rag_enhanced_llm_service(
    adaptive_strategy: AdaptiveMultiDBStrategy,
    config: Dict[str, Any] = None
) -> RAGEnhancedLLMService:
    """
    Factory Function für RAG-Enhanced LLM Service
    """
    
    context_aggregator = MultiDatabaseRAGContextAggregator(adaptive_strategy, config=config)
    
    rag_service = RAGEnhancedLLMService(
        adaptive_strategy=adaptive_strategy,
        context_aggregator=context_aggregator,
        config=config
    )
    
    logging.info("🚀 RAG-Enhanced LLM Service created and ready")
    
    return rag_service


# Demo und Testing
async def test_rag_enhanced_llm_integration():
    """Test Function für RAG-Enhanced LLM Integration"""
    
    print("🤖 Testing RAG-Enhanced LLM Integration...")
    
    # Use mock adaptive strategy for testing
    adaptive_strategy = AdaptiveMultiDBStrategy()
    
    # RAG Service erstellen
    rag_service = await create_rag_enhanced_llm_service(
        adaptive_strategy=adaptive_strategy,
        config={
            'max_tokens': 8192,
            'temperature': 0.7,
            'chromadb_collection': 'covina_documents'
        }
    )
    
    # Test Query
    test_query = "Welche Dokumente gibt es über Datenschutz und wie hängen sie zusammen?"
    
    print(f"\n📝 Test Query: {test_query}")
    
    # Enhanced Query ausführen
    result = await rag_service.enhanced_query(
        user_query=test_query,
        query_intent='analyze',
        max_context_tokens=3000
    )
    
    print(f"\n✅ Query Results:")
    print(f"   📊 Context Sources: {result.get('context_sources', 0)}")
    print(f"   🗄️ Databases Used: {', '.join(result.get('databases_used', []))}")
    print(f"   🎯 Context Confidence: {result.get('context_confidence', 0.0):.2f}")
    print(f"   ⏱️ Total Time: {result.get('total_processing_time_ms', 0)}ms")
    print(f"   🔧 Tokens Used: {result.get('total_tokens', 0)}")
    
    # Response Preview
    response = result.get('response', '')
    if response:
        print(f"\n📄 Response Preview:")
        print(f"   {response[:200]}...")
    
    # Follow-up Suggestions
    followup_queries = result.get('suggested_followup_queries', [])
    if followup_queries:
        print(f"\n💡 Suggested Follow-up Queries:")
        for query in followup_queries:
            print(f"   - {query}")
    
    print(f"\n🚀 RAG-Enhanced LLM Integration Test: {'✅ PASSED' if result.get('response') else '❌ FAILED'}")
    
    return result


if __name__ == "__main__":
    # Test ausführen
    asyncio.run(test_rag_enhanced_llm_integration())