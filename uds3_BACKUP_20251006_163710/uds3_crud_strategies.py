#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 CRUD Strategies - Extracted from uds3_core.py

EXTRACTION: Lines 3194-3394 aus uds3_core.py (~200 LOC)
PURPOSE: Reduziere uds3_core.py Komplexität durch CRUD-Strategie-Extraktion
DATE: 1. Oktober 2025

Enthält:
- _create_crud_strategies(): CRUD-Operationsstrategien für alle DB-Typen
- _create_conflict_resolution_rules(): Konfliktlösungsstrategien
"""

from typing import Dict
from enum import Enum


class OperationType(Enum):
    """Definiert die verfügbaren CRUD-Operationen"""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"  # Upsert-Operation
    ARCHIVE = "archive"  # Soft Delete
    RESTORE = "restore"  # Restore from Archive


class SyncStrategy(Enum):
    """Synchronisationsstrategien zwischen Datenbanken"""

    IMMEDIATE = "immediate"  # Sofortige Synchronisation
    DEFERRED = "deferred"  # Verzögerte Batch-Synchronisation
    EVENTUAL = "eventual"  # Eventual Consistency
    MANUAL = "manual"  # Manuelle Synchronisation


class UDS3CRUDStrategiesMixin:
    """Mixin für CRUD-Strategie-Definitionen"""

    def _create_crud_strategies(self) -> Dict:
        """Definiert CRUD-Strategien für alle Datenbank-Typen"""
        return {
            OperationType.CREATE: {
                "vector": {
                    "primary_operation": "add_embeddings",
                    "validation": ["duplicate_check", "dimension_check"],
                    "rollback_strategy": "delete_by_id",
                    "batch_size": 50,
                },
                "graph": {
                    "primary_operation": "create_nodes_and_edges",
                    "validation": ["node_existence_check", "edge_validity"],
                    "rollback_strategy": "delete_cascade",
                    "batch_size": 100,
                },
                "relational": {
                    "primary_operation": "insert_records",
                    "validation": ["constraint_check", "foreign_key_check"],
                    "rollback_strategy": "transaction_rollback",
                    "batch_size": 200,
                },
            },
            OperationType.READ: {
                "vector": {
                    "operations": [
                        "similarity_search",
                        "get_by_id",
                        "list_collections",
                    ],
                    "optimization": "index_hints",
                    "cache_strategy": "embedding_cache",
                },
                "graph": {
                    "operations": [
                        "cypher_query",
                        "traversal",
                        "get_node",
                        "get_relationships",
                    ],
                    "optimization": "query_planner",
                    "cache_strategy": "result_cache",
                },
                "relational": {
                    "operations": ["sql_query", "get_by_id", "filtered_search"],
                    "optimization": "index_usage",
                    "cache_strategy": "query_cache",
                },
            },
            OperationType.UPDATE: {
                "sync_strategy": SyncStrategy.IMMEDIATE,
                "conflict_resolution": "last_write_wins",
                "validation_required": True,
                "operations": {
                    "vector": {
                        "primary_operation": "update_embeddings",
                        "requires_recompute": True,
                        "affected_indexes": ["similarity_index"],
                        "cascade_updates": ["related_chunks"],
                    },
                    "graph": {
                        "primary_operation": "update_node_properties",
                        "requires_reindex": ["property_indexes"],
                        "cascade_updates": ["connected_nodes"],
                        "relationship_updates": "conditional",
                    },
                    "relational": {
                        "primary_operation": "update_records",
                        "requires_reindex": False,
                        "cascade_updates": ["dependent_tables"],
                        "triggers": ["audit_log", "statistics_update"],
                    },
                },
            },
            OperationType.DELETE: {
                "sync_strategy": SyncStrategy.IMMEDIATE,
                "soft_delete_preferred": True,
                "cascade_strategy": "selective",
                "operations": {
                    "vector": {
                        "primary_operation": "delete_embeddings",
                        "cascade_deletes": ["related_chunks"],
                        "cleanup_required": ["orphaned_vectors"],
                        "index_maintenance": True,
                    },
                    "graph": {
                        "primary_operation": "delete_node_cascade",
                        "relationship_cleanup": "automatic",
                        "orphan_detection": True,
                        "index_cleanup": True,
                    },
                    "relational": {
                        "primary_operation": "soft_delete_records",
                        "foreign_key_handling": "restrict",
                        "audit_trail": True,
                        "statistics_update": True,
                    },
                },
            },
            OperationType.ARCHIVE: {
                "retention_policy": "90_days",
                "compression": True,
                "accessibility": "read_only",
                "operations": {
                    "vector": {
                        "move_to": "archive_collection",
                        "compress_embeddings": True,
                        "maintain_searchability": False,
                    },
                    "graph": {
                        "move_to": "archive_subgraph",
                        "preserve_relationships": True,
                        "mark_inactive": True,
                    },
                    "relational": {
                        "move_to": "archive_tables",
                        "maintain_indexes": False,
                        "compress_data": True,
                    },
                },
                "uds3_audit_log": {
                    "primary_key": "audit_id",
                    "indexes": [
                        {"columns": ["trace_id"], "type": "btree"},
                        {"columns": ["saga_id"], "type": "btree"},
                    ],
                    "columns": {
                        "audit_id": "VARCHAR(36) PRIMARY KEY",
                        "saga_id": "VARCHAR(36) NOT NULL",
                        "trace_id": "VARCHAR(36)",
                        "step_name": "VARCHAR(128)",
                        "event_type": "VARCHAR(64)",
                        "status": "VARCHAR(32)",
                        "duration_ms": "INTEGER",
                        "details": "JSONB",
                        "actor": "VARCHAR(100)",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                },
                "uds3_saga_metrics": {
                    "primary_key": "metric_id",
                    "indexes": [
                        {"columns": ["saga_id"], "type": "btree"},
                        {"columns": ["trace_id"], "type": "btree"},
                        {"columns": ["step_name"], "type": "btree"},
                    ],
                    "columns": {
                        "metric_id": "VARCHAR(36) PRIMARY KEY",
                        "saga_id": "VARCHAR(36) NOT NULL",
                        "trace_id": "VARCHAR(36)",
                        "step_name": "VARCHAR(128)",
                        "status": "VARCHAR(32)",
                        "started_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "finished_at": "TIMESTAMP",
                        "duration_ms": "INTEGER",
                        "error_message": "TEXT",
                        "details": "JSONB",
                    },
                },
            },
        }

    def _create_conflict_resolution_rules(self) -> Dict:
        """Definiert Konfliktlösungsstrategien"""
        return {
            "update_conflicts": {
                "strategy": "timestamp_based",
                "fallback": "manual_resolution",
                "rules": {
                    "vector_embeddings": "recompute_on_conflict",
                    "graph_properties": "merge_non_conflicting",
                    "relational_data": "last_write_wins",
                },
            },
            "cross_db_inconsistency": {
                "detection_method": "periodic_validation",
                "resolution_strategy": "authoritative_source",
                "authority_hierarchy": ["relational", "graph", "vector"],
                "reconciliation_batch_size": 100,
            },
            "concurrent_operations": {
                "locking_strategy": "optimistic_locking",
                "retry_policy": {
                    "max_retries": 3,
                    "backoff_strategy": "exponential",
                    "base_delay_ms": 100,
                },
            },
        }
