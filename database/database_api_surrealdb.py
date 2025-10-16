#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

"""
SurrealDB Multi-Model Database Backend
======================================

Next-Generation Multi-Model Database
- Relational + Graph + Document in einem
- Real-time Queries
- Modern SQL-like SurrealQL
- Built-in Authentication & Permissions
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from database.database_api_base import GraphDatabaseBackend

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

# SurrealDB Import mit Fallback
try:
    from surrealdb import Surreal
    SURREALDB_AVAILABLE = True
except ImportError:
    SURREALDB_AVAILABLE = False

logger = logging.getLogger(__name__)


class SurrealMultiModelBackend(GraphDatabaseBackend):
    """SurrealDB Backend für Multi-Model-Operationen mit UDS3-Integration"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.client = None
        self.connection_url = config.get('connection_url', 'ws://localhost:8000/rpc')
        self.namespace = config.get('namespace', 'veritas')
        self.database = config.get('database', 'covina')
        self.username = config.get('username', 'root')
        self.password = config.get('password', 'root')
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for SurrealDB: {exc}")
            self.strategy = None
        
        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"SurrealDB Multi-Model Backend initialisiert mit Strategie {strategy_version}")
    
    def _backend_connect(self) -> bool:
        """Verbindung zu SurrealDB herstellen"""
        if not SURREALDB_AVAILABLE:
            logger.error("SurrealDB Python client nicht installiert")
            return False
            
        try:
            # SurrealDB-Client erstellen
            self.client = Surreal()
            
            # Verbindung herstellen (synchron)
            self._connect_sync()
            
            logger.info(f"SurrealDB verbunden: {self.get_backend_type()}")
            return True
            
        except Exception as e:
            logger.error(f"SurrealDB Verbindung fehlgeschlagen: {e}")
            return False
    
    def _connect_sync(self):
        """Synchrone Verbindung zu SurrealDB"""
        # Event Loop für async Operationen
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def connect():
            await self.client.connect(self.connection_url)
            await self.client.signin({
                "user": self.username,
                "pass": self.password
            })
            await self.client.use(self.namespace, self.database)
            
            # Test-Query
            result = await self.client.query("SELECT * FROM $version LIMIT 1")
            return result
        
        # Verbindung ausführen
        loop.run_until_complete(connect())
    
    def disconnect(self):
        """Verbindung schließen"""
        if self.client:
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.client.close())
            except:
                pass
            self.client = None
    
    def is_available(self) -> bool:
        """Prüft ob Backend verfügbar ist"""
        try:
            if self.client:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    self.client.query("SELECT 1 as test")
                )
                return bool(result)
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        """Backend-Typ für Logging"""
        return f"SurrealDB Multi-Model"
    
    def _execute_query(self, query: str, params: Dict = None) -> Any:
        """SurrealQL Query ausführen"""
        try:
            loop = asyncio.get_event_loop()
            
            async def run_query():
                if params:
                    return await self.client.query(query, params)
                else:
                    return await self.client.query(query)
            
            result = loop.run_until_complete(run_query())
            return result
            
        except Exception as e:
            logger.error(f"SurrealDB Query fehlgeschlagen: {e}")
            return None
    
    # ==============================
    # DOCUMENT OPERATIONS
    # ==============================
    
    def create_table(self, table_name: str, schema: Dict = None) -> bool:
        """Tabelle/Collection erstellen"""
        try:
            # SurrealDB erstellt Tabellen automatisch bei INSERT
            # Optional: Schema-Definitionen
            if schema:
                schema_queries = []
                for field, field_type in schema.items():
                    surreal_type = self._map_to_surreal_type(field_type)
                    schema_queries.append(f"DEFINE FIELD {field} ON {table_name} TYPE {surreal_type}")
                
                for query in schema_queries:
                    self._execute_query(query)
            
            logger.debug(f"SurrealDB Tabelle vorbereitet: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"SurrealDB Tabelle erstellen fehlgeschlagen: {e}")
            return False
    
    def _map_to_surreal_type(self, generic_type: str) -> str:
        """Mappt generische Typen zu SurrealDB-Typen"""
        type_mapping = {
            'INTEGER': 'int',
            'TEXT': 'string',
            'REAL': 'float',
            'BOOLEAN': 'bool',
            'DATETIME': 'datetime',
            'JSON': 'object',
            'ARRAY': 'array'
        }
        return type_mapping.get(generic_type.upper(), 'string')
    
    def insert_document(self, table_name: str, document: Dict, doc_id: str = None) -> str:
        """Dokument einfügen"""
        try:
            if doc_id:
                query = f"CREATE {table_name}:{doc_id} CONTENT $document"
                params = {"document": document}
            else:
                query = f"CREATE {table_name} CONTENT $document"
                params = {"document": document}
            
            result = self._execute_query(query, params)
            
            if result and result[0] and result[0]['result']:
                created_doc = result[0]['result'][0]
                return created_doc.get('id', '')
            
            return ""
            
        except Exception as e:
            logger.error(f"SurrealDB Dokument einfügen fehlgeschlagen: {e}")
            return ""
    
    def update_document(self, table_name: str, doc_id: str, updates: Dict) -> bool:
        """Dokument aktualisieren"""
        try:
            query = f"UPDATE {table_name}:{doc_id} MERGE $updates"
            params = {"updates": updates}
            
            result = self._execute_query(query, params)
            return result is not None
            
        except Exception as e:
            logger.error(f"SurrealDB Dokument Update fehlgeschlagen: {e}")
            return False
    
    def get_document(self, table_name: str, doc_id: str) -> Optional[Dict]:
        """Dokument abrufen"""
        try:
            query = f"SELECT * FROM {table_name}:{doc_id}"
            result = self._execute_query(query)
            
            if result and result[0] and result[0]['result']:
                return result[0]['result'][0]
            
            return None
            
        except Exception as e:
            logger.error(f"SurrealDB Dokument abrufen fehlgeschlagen: {e}")
            return None
    
    def delete_document(self, table_name: str, doc_id: str) -> bool:
        """Dokument löschen"""
        try:
            query = f"DELETE {table_name}:{doc_id}"
            result = self._execute_query(query)
            return result is not None
            
        except Exception as e:
            logger.error(f"SurrealDB Dokument löschen fehlgeschlagen: {e}")
            return False
    
    # ==============================
    # GRAPH OPERATIONS
    # ==============================
    
    def create_node(self, table_name: str, node_data: Dict, node_id: str = None) -> str:
        """Graph-Node erstellen"""
        return self.insert_document(table_name, node_data, node_id)
    
    def create_relationship(self, from_id: str, to_id: str, 
                          relationship_type: str, properties: Dict = None) -> str:
        """Graph-Relationship erstellen"""
        try:
            if properties is None:
                properties = {}
            
            query = f"RELATE {from_id} -> {relationship_type} -> {to_id} CONTENT $properties"
            params = {"properties": properties}
            
            result = self._execute_query(query, params)
            
            if result and result[0] and result[0]['result']:
                created_rel = result[0]['result'][0]
                return created_rel.get('id', '')
            
            return ""
            
        except Exception as e:
            logger.error(f"SurrealDB Relationship erstellen fehlgeschlagen: {e}")
            return ""
    
    def get_node_relationships(self, node_id: str, direction: str = 'both') -> List[Dict]:
        """Node-Relationships abrufen"""
        try:
            if direction == 'outgoing':
                query = f"SELECT * FROM {node_id}->*"
            elif direction == 'incoming':
                query = f"SELECT * FROM *->{node_id}"
            else:  # both
                query = f"SELECT * FROM {node_id}<->*"
            
            result = self._execute_query(query)
            
            if result and result[0] and result[0]['result']:
                return result[0]['result']
            
            return []
            
        except Exception as e:
            logger.error(f"SurrealDB Node Relationships abrufen fehlgeschlagen: {e}")
            return []
    
    def graph_traversal(self, start_node: str, traversal_pattern: str, 
                       max_depth: int = 3) -> List[Dict]:
        """Graph-Traversal"""
        try:
            # SurrealQL Graph-Traversal
            query = f"""
            SELECT * FROM {start_node}
            {traversal_pattern}
            LIMIT BY DEPTH {max_depth}
            """
            
            result = self._execute_query(query)
            
            if result and result[0] and result[0]['result']:
                return result[0]['result']
            
            return []
            
        except Exception as e:
            logger.error(f"SurrealDB Graph Traversal fehlgeschlagen: {e}")
            return []
    
    # ==============================
    # ADVANCED QUERIES
    # ==============================
    
    def surrealql_query(self, query: str, params: Dict = None) -> List[Dict]:
        """Raw SurrealQL Query"""
        try:
            result = self._execute_query(query, params)
            
            if result and result[0] and result[0]['result']:
                return result[0]['result']
            
            return []
            
        except Exception as e:
            logger.error(f"SurrealDB SurrealQL Query fehlgeschlagen: {e}")
            return []
    
    def fulltext_search(self, table_name: str, search_term: str, 
                       fields: List[str] = None) -> List[Dict]:
        """Volltext-Suche"""
        try:
            if fields:
                field_conditions = []
                for field in fields:
                    field_conditions.append(f"{field} @@ $search_term")
                where_clause = " OR ".join(field_conditions)
            else:
                where_clause = f"text @@ $search_term"
            
            query = f"SELECT * FROM {table_name} WHERE {where_clause}"
            params = {"search_term": search_term}
            
            result = self._execute_query(query, params)
            
            if result and result[0] and result[0]['result']:
                return result[0]['result']
            
            return []
            
        except Exception as e:
            logger.error(f"SurrealDB Volltext-Suche fehlgeschlagen: {e}")
            return []
    
    def aggregate_query(self, table_name: str, aggregations: Dict, 
                       conditions: str = None) -> Dict:
        """Aggregations-Query"""
        try:
            # Aggregations aufbauen
            agg_parts = []
            for field, agg_type in aggregations.items():
                if agg_type.upper() in ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']:
                    agg_parts.append(f"{agg_type.upper()}({field}) AS {field}_{agg_type.lower()}")
            
            select_clause = ", ".join(agg_parts) if agg_parts else "*"
            
            query = f"SELECT {select_clause} FROM {table_name}"
            if conditions:
                query += f" WHERE {conditions}"
            
            result = self._execute_query(query)
            
            if result and result[0] and result[0]['result']:
                return result[0]['result'][0] if result[0]['result'] else {}
            
            return {}
            
        except Exception as e:
            logger.error(f"SurrealDB Aggregation fehlgeschlagen: {e}")
            return {}
    
    def get_table_info(self, table_name: str) -> Dict:
        """Tabellen-Informationen"""
        try:
            # Basis-Info
            count_query = f"SELECT COUNT() FROM {table_name} GROUP ALL"
            count_result = self._execute_query(count_query)
            
            row_count = 0
            if count_result and count_result[0] and count_result[0]['result']:
                row_count = count_result[0]['result'][0].get('count', 0)
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'backend_type': self.get_backend_type(),
                'namespace': self.namespace,
                'database': self.database
            }
            
        except Exception as e:
            logger.error(f"SurrealDB Tabellen-Info fehlgeschlagen: {e}")
            return {}
    
    def export_table(self, table_name: str, format: str = 'json') -> str:
        """Tabelle exportieren"""
        try:
            query = f"SELECT * FROM {table_name}"
            result = self._execute_query(query)
            
            if result and result[0] and result[0]['result']:
                data = result[0]['result']
                
                if format.lower() == 'json':
                    return json.dumps(data, indent=2, default=str)
                else:
                    return str(data)
            
            return ""
            
        except Exception as e:
            logger.error(f"SurrealDB Export fehlgeschlagen: {e}")
            return ""


def get_backend_class():
    """Factory-Funktion für SurrealDB Backend"""
    return SurrealMultiModelBackend if SURREALDB_AVAILABLE else None


"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_surrealdb"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
module_file_key = "66ec027dfd c2g64gg959h9e5459efgff49h99eg17h08gag490gec017d19hg4g"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===