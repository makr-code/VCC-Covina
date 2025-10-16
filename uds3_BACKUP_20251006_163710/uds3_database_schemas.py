#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Database Schemas - Extracted from uds3_core.py
====================================================
OPTIMIZED (1. Oktober 2025): Schema Definitions aus uds3_core.py extrahiert

EXTRACTION: Lines 512-841 + 4156-4170 aus uds3_core.py (~350 LOC)
PURPOSE: Reduziere uds3_core.py Komplexität durch Schema-Extraktion

Dieses Modul enthält alle Database Schema-Definitionen:
- _create_vector_schema() - Vector DB (ChromaDB/Pinecone)
- _create_graph_schema() - Graph DB (Neo4j/ArangoDB)
- _create_relational_schema() - Relational DB (SQLite/PostgreSQL)
- _create_file_storage_schema() - File Storage Backend

Pattern: Mixin-Class für saubere Integration in UnifiedDatabaseStrategy
"""

from typing import Dict


class UDS3DatabaseSchemasMixin:
    """
    Mixin für Database Schema-Definitionen
    
    Wird in UnifiedDatabaseStrategy gemischt für modulare Schema-Verwaltung.
    Alle Methoden sind self-contained und returnieren Schema-Dictionaries.
    """
    
    def _create_vector_schema(self) -> Dict:
        """
        Optimiertes Schema für Vector Database
        
        EXTRAHIERT aus uds3_core.py (Lines 512-560)
        
        Returns:
            Dict: Vector Database Schema mit Collections und Search Strategies
        """
        return {
            "collections": {
                "document_chunks": {
                    "embedding_field": "content_vector",
                    "metadata_fields": [
                        "document_id",  # Referenz für Cross-DB Queries
                        "chunk_index",
                        "content_preview",  # Für Suchergebnisse
                        "section_title",
                        "chunk_type",  # 'paragraph', 'heading', 'table', etc.
                        "content_length",
                        "language",
                        "created_at",
                    ],
                    "vector_config": {
                        "dimensions": 1536,
                        "similarity_metric": "cosine",
                        "index_type": "hnsw",  # Hierarchical Navigable Small World
                    },
                },
                "document_summaries": {
                    "embedding_field": "summary_vector",
                    "metadata_fields": [
                        "document_id",
                        "summary_text",
                        "key_topics",
                        "document_type",
                        "confidence_score",
                        "created_at",
                    ],
                },
            },
            "search_strategies": {
                "semantic_search": {
                    "collection": "document_chunks",
                    "k_results": 50,
                    "similarity_threshold": 0.7,
                    "rerank": True,
                },
                "document_discovery": {
                    "collection": "document_summaries",
                    "k_results": 20,
                    "similarity_threshold": 0.75,
                },
            },
        }

    def _create_graph_schema(self) -> Dict:
        """
        Optimiertes Schema für Graph Database
        
        EXTRAHIERT aus uds3_core.py (Lines 561-665)
        
        Returns:
            Dict: Graph Database Schema mit Node Types, Relationships, Traversal Strategies
        """
        return {
            "node_types": {
                "Document": {
                    "primary_key": "id",
                    "indexes": ["file_hash", "rechtsgebiet", "created_at"],
                    "properties": {
                        "essential": ["id", "title", "file_path", "file_hash"],
                        "metadata": ["rechtsgebiet", "behoerde", "document_type"],
                        "computed": [
                            "chunk_count",
                            "relationship_count",
                            "centrality_score",
                        ],
                    },
                },
                "Author": {
                    "primary_key": "normalized_name",
                    "indexes": ["name", "organization"],
                    "properties": {
                        "essential": ["id", "name", "normalized_name"],
                        "metadata": ["organization", "role", "expertise_areas"],
                        "computed": [
                            "document_count",
                            "citation_count",
                            "authority_score",
                        ],
                    },
                },
                "LegalEntity": {
                    "primary_key": "entity_id",
                    "indexes": ["entity_type", "jurisdiction"],
                    "properties": {
                        "essential": ["entity_id", "name", "entity_type"],
                        "metadata": [
                            "jurisdiction",
                            "legal_form",
                            "establishment_date",
                        ],
                        "computed": ["mention_count", "case_involvement"],
                    },
                },
                "Concept": {
                    "primary_key": "concept_id",
                    "indexes": ["domain", "confidence"],
                    "properties": {
                        "essential": ["concept_id", "term", "domain"],
                        "metadata": ["definition", "synonyms", "related_terms"],
                        "computed": ["frequency", "importance_score"],
                    },
                },
            },
            "relationship_types": {
                "CONTAINS": {
                    "from": "Document",
                    "to": "DocumentChunk",
                    "properties": ["chunk_index", "section_type"],
                    "traversal_weight": 1.0,
                },
                "CITES": {
                    "from": "Document",
                    "to": "Document",
                    "properties": ["citation_type", "relevance_score", "context"],
                    "traversal_weight": 0.8,
                },
                "AUTHORED_BY": {
                    "from": "Document",
                    "to": "Author",
                    "properties": ["role", "contribution_type"],
                    "traversal_weight": 0.9,
                },
                "MENTIONS": {
                    "from": "Document",
                    "to": "LegalEntity",
                    "properties": ["mention_count", "context_type", "sentiment"],
                    "traversal_weight": 0.6,
                },
                "RELATES_TO": {
                    "from": "Document",
                    "to": "Concept",
                    "properties": ["relevance_score", "extraction_method"],
                    "traversal_weight": 0.7,
                },
                "SUPERSEDES": {
                    "from": "Document",
                    "to": "Document",
                    "properties": ["supersession_date", "legal_basis"],
                    "traversal_weight": 0.95,
                },
            },
            "traversal_strategies": {
                "citation_network": {
                    "relationships": ["CITES", "SUPERSEDES"],
                    "max_depth": 3,
                    "direction": "both",
                },
                "concept_expansion": {
                    "relationships": ["RELATES_TO", "MENTIONS"],
                    "max_depth": 2,
                    "direction": "outgoing",
                },
            },
        }

    def _create_relational_schema(self) -> Dict:
        """
        Optimiertes Schema für Relational Database
        
        EXTRAHIERT aus uds3_core.py (Lines 666-841)
        
        Returns:
            Dict: Relational Database Schema mit Tables, Indexes, Query Strategies
        """
        return {
            "tables": {
                "documents_metadata": {
                    "primary_key": "document_id",
                    "indexes": [
                        {"columns": ["rechtsgebiet"], "type": "btree"},
                        {"columns": ["behoerde"], "type": "btree"},
                        {"columns": ["document_type"], "type": "btree"},
                        {"columns": ["created_at"], "type": "btree"},
                        {"columns": ["file_hash"], "type": "unique"},
                        {
                            "columns": ["title"],
                            "type": "gin_trgm",
                        },  # PostgreSQL Trigram
                    ],
                    "columns": {
                        "document_id": "VARCHAR(32) PRIMARY KEY",
                        "title": "TEXT NOT NULL",
                        "file_path": "TEXT NOT NULL",
                        "file_hash": "VARCHAR(64) UNIQUE",
                        "file_size": "INTEGER",
                        "rechtsgebiet": "VARCHAR(100)",
                        "behoerde": "VARCHAR(200)",
                        "document_type": "VARCHAR(50)",
                        "language": 'CHAR(2) DEFAULT "de"',
                        "chunk_count": "INTEGER DEFAULT 0",
                        "processing_status": 'VARCHAR(20) DEFAULT "pending"',
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
                "keywords_index": {
                    "primary_key": "id",
                    "indexes": [
                        {"columns": ["keyword"], "type": "gin_trgm"},
                        {"columns": ["document_id"], "type": "btree"},
                        {"columns": ["frequency"], "type": "btree"},
                        {"columns": ["keyword", "document_id"], "type": "unique"},
                    ],
                    "columns": {
                        "id": "SERIAL PRIMARY KEY",
                        "document_id": "VARCHAR(32) REFERENCES documents_metadata(document_id)",
                        "keyword": "VARCHAR(200) NOT NULL",
                        "frequency": "INTEGER NOT NULL",
                        "context_type": "VARCHAR(50)",  # 'title', 'content', 'summary'
                        "extraction_method": "VARCHAR(50)",  # 'tfidf', 'ner', 'manual'
                        "confidence": "DECIMAL(3,2) DEFAULT 1.0",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
                "processing_statistics": {
                    "primary_key": "id",
                    "indexes": [
                        {"columns": ["document_id"], "type": "btree"},
                        {"columns": ["processing_stage"], "type": "btree"},
                        {"columns": ["created_at"], "type": "btree"},
                    ],
                    "columns": {
                        "id": "SERIAL PRIMARY KEY",
                        "document_id": "VARCHAR(32) REFERENCES documents_metadata(document_id)",
                        "processing_stage": "VARCHAR(50) NOT NULL",
                        "duration_ms": "INTEGER",
                        "memory_usage_mb": "INTEGER",
                        "tokens_processed": "INTEGER",
                        "vectors_created": "INTEGER",
                        "relationships_created": "INTEGER",
                        "status": 'VARCHAR(20) DEFAULT "completed"',
                        "error_message": "TEXT",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
                "administrative_identities": {
                    "primary_key": "uuid",
                    "indexes": [
                        {"columns": ["aktenzeichen"], "type": "btree"},
                        {"columns": ["status"], "type": "btree"},
                    ],
                    "columns": {
                        "uuid": "VARCHAR(36) PRIMARY KEY",
                        "aktenzeichen": "VARCHAR(120) UNIQUE",
                        "status": 'VARCHAR(32) DEFAULT "registered"',
                        "source_system": "VARCHAR(100)",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
                "administrative_identity_mappings": {
                    "primary_key": "uuid",
                    "indexes": [
                        {"columns": ["aktenzeichen"], "type": "btree"},
                        {"columns": ["relational_id"], "type": "btree"},
                        {"columns": ["graph_id"], "type": "btree"},
                        {"columns": ["vector_id"], "type": "btree"},
                        {"columns": ["file_storage_id"], "type": "btree"},
                    ],
                    "columns": {
                        "uuid": "VARCHAR(36) PRIMARY KEY REFERENCES administrative_identities(uuid)",
                        "aktenzeichen": "VARCHAR(120)",
                        "relational_id": "VARCHAR(64)",
                        "graph_id": "VARCHAR(64)",
                        "vector_id": "VARCHAR(64)",
                        "file_storage_id": "VARCHAR(64)",
                        "metadata": "JSONB",
                        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
                "administrative_identity_audit": {
                    "primary_key": "audit_id",
                    "indexes": [
                        {"columns": ["uuid"], "type": "btree"},
                        {"columns": ["action"], "type": "btree"},
                    ],
                    "columns": {
                        "audit_id": "VARCHAR(36) PRIMARY KEY",
                        "uuid": "VARCHAR(36) NOT NULL REFERENCES administrative_identities(uuid)",
                        "action": "VARCHAR(64) NOT NULL",
                        "actor": "VARCHAR(100)",
                        "details": "JSONB",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
                "administrative_identity_metrics": {
                    "primary_key": "metric_id",
                    "indexes": [
                        {"columns": ["aktenzeichen"], "type": "btree"},
                        {"columns": ["metric_name"], "type": "btree"},
                        {"columns": ["observed_at"], "type": "btree"},
                    ],
                    "columns": {
                        "metric_id": "VARCHAR(36) PRIMARY KEY",
                        "aktenzeichen": "VARCHAR(120) NOT NULL REFERENCES administrative_identities(aktenzeichen)",
                        "metric_name": "VARCHAR(64) NOT NULL",
                        "metric_value": "DECIMAL(12,4) NOT NULL",
                        "units": "VARCHAR(16)",
                        "metadata": "JSONB",
                        "observed_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
                "administrative_identity_traces": {
                    "primary_key": "trace_id",
                    "indexes": [
                        {"columns": ["aktenzeichen"], "type": "btree"},
                        {"columns": ["stage"], "type": "btree"},
                        {"columns": ["observed_at"], "type": "btree"},
                    ],
                    "columns": {
                        "trace_id": "VARCHAR(36) PRIMARY KEY",
                        "aktenzeichen": "VARCHAR(120) NOT NULL REFERENCES administrative_identities(aktenzeichen)",
                        "stage": "VARCHAR(64) NOT NULL",
                        "status": "VARCHAR(20) NOT NULL",
                        "details": "JSONB",
                        "observed_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
            },
            "query_strategies": {
                "keyword_search": {
                    "table": "keywords_index",
                    "search_type": "fulltext",
                    "ranking": "frequency DESC, confidence DESC",
                },
                "metadata_filtering": {
                    "table": "documents_metadata",
                    "filter_fields": ["rechtsgebiet", "behoerde", "document_type"],
                    "sort_options": ["created_at", "title", "file_size"],
                },
                "identity_lookup": {
                    "table": "administrative_identities",
                    "filter_fields": ["aktenzeichen", "status"],
                    "sort_options": ["created_at", "aktenzeichen"],
                },
            },
        }

    def _create_file_storage_schema(self) -> Dict:
        """
        Erstellt Schema-/Policy-Definition für File Storage Backend
        
        EXTRAHIERT aus uds3_core.py (Lines 4156-4170)
        
        Returns:
            Dict: File Storage Schema mit Policies und Integrity Checks
        """
        return {
            "storage_root": "var/uds3/files",
            "replication": "none",
            "versioning": True,
            "retention_policies": {
                "default": {"min_days": 365, "archive_after_days": 30},
                "legal_hold": {"min_days": 1825, "immutable": True},
            },
            "integrity_checks": {
                "hash_algorithm": "sha256",
                "store_original_hash": True,
                "periodic_rehash_days": 90,
            },
        }


# Export
__all__ = ["UDS3DatabaseSchemasMixin"]
