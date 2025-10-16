#!/usr/bin/env python3
"""
ArangoDB Graph Database Backend
"""

import logging
import uuid
from typing import Dict, List, Optional
from database.database_api_base import GraphDatabaseBackend
# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None
from datetime import datetime, timezone

try:
    from arango import ArangoClient  # type: ignore[import-unresolved]
    ARANGO_AVAILABLE = True
except ImportError:
    ARANGO_AVAILABLE = False

logger = logging.getLogger(__name__)

class ArangoDBGraphBackend(GraphDatabaseBackend):
    """ArangoDB Graph Database"""
    
    def __init__(self, config: Dict):
        if not ARANGO_AVAILABLE:
            logger.warning("ArangoDB library not available at import time; connect() will fail if used")

        self.config = config
        self.host = config.get('host', 'http://localhost:8529')
        self.username = config.get('username', 'root')
        self.password = config.get('password', '')
        self.database_name = config.get('database', '_system')
        self.graph_name = config.get('graph_name', 'default_graph')
        self.vertex_collection = config.get('vertex_collection', 'vertices')
        self.edge_collection = config.get('edge_collection', 'edges')

        self.client = None
        self.db = None
        self.graph = None
        # postpone client initialization to connect()
        self._initialized = False

        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for ArangoDB: {exc}")
            self.strategy = None

        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"ArangoDB Backend initialisiert mit Strategie {strategy_version}")
        
    def connect(self) -> bool:
        if self._initialized:
            return True
        if not ARANGO_AVAILABLE:
            logger.error("ArangoDB client library not installed")
            return False
        try:
            self.client = ArangoClient(hosts=self.host)
            self.db = self.client.db(
                name=self.database_name,
                username=self.username,
                password=self.password
            )

            # Test connection
            self.db.version()

            # Collections und Graph erstellen falls nicht vorhanden
            self._setup_collections()

            self._initialized = True
            logging.info(f"ArangoDB verbunden: {self.host}")
            return True

        except Exception as e:
            logging.error(f"ArangoDB Verbindung fehlgeschlagen: {e}")
            return False
    
    def _setup_collections(self):
        """Collections und Graph einrichten"""
        try:
            # Vertex Collection
            if not self.db.has_collection(self.vertex_collection):
                self.db.create_collection(self.vertex_collection)
                logging.info(f"ArangoDB Vertex Collection erstellt: {self.vertex_collection}")
            
            # Edge Collection
            if not self.db.has_collection(self.edge_collection):
                self.db.create_collection(self.edge_collection, edge=True)
                logging.info(f"ArangoDB Edge Collection erstellt: {self.edge_collection}")
            
            # Graph
            if not self.db.has_graph(self.graph_name):
                edge_definition = {
                    'edge_collection': self.edge_collection,
                    'from_vertex_collections': [self.vertex_collection],
                    'to_vertex_collections': [self.vertex_collection]
                }
                
                self.db.create_graph(
                    name=self.graph_name,
                    edge_definitions=[edge_definition]
                )
                logging.info(f"ArangoDB Graph erstellt: {self.graph_name}")
            
            self.graph = self.db.graph(self.graph_name)
            
        except Exception as e:
            logging.error(f"ArangoDB Setup fehlgeschlagen: {e}")
    
    def disconnect(self):
        self.client = None
        self.db = None
        self.graph = None
    
    def is_available(self) -> bool:
        try:
            if self.db:
                self.db.version()
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        return "ArangoDB"
    
    def create_node(self, node_type: str, properties: Dict) -> str:
        """
        Erstellt einen Knoten mit beliebigen Properties (inkl. Metadaten, Relationen etc.)
        """
        db = self._get_graph_db()
        node = {
            "_key": properties.get("chunk_id") or properties.get("id") or str(uuid.uuid4()),
            "type": node_type,
            "properties": properties,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            db.collection("nodes").insert(node)
            return node["_key"]
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Knotens: {e}")
            return None
    
    def create_edge(self, from_id: str, to_id: str, edge_type: str, properties: Dict = None) -> str:
        """
        Erstellt eine Kante mit beliebigen Properties (inkl. Relationen, Kontext etc.)
        """
        db = self._get_graph_db()
        edge = {
            "_from": f"nodes/{from_id}",
            "_to": f"nodes/{to_id}",
            "type": edge_type,
            "properties": properties or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            db.collection("edges").insert(edge)
            return edge["_from"] + "->" + edge["_to"]
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Kante: {e}")
            return None
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        try:
            if not self.db:
                return None
            
            vertex_collection = self.db.collection(self.vertex_collection)
            
            # Key oder ID verwenden
            if '/' in node_id:
                document = vertex_collection.get(node_id.split('/')[-1])
            else:
                document = vertex_collection.get(node_id)
            
            if document:
                return {
                    'id': document['_id'],
                    'type': document.get('node_type', 'Unknown'),
                    'properties': {k: v for k, v in document.items() 
                                 if not k.startswith('_') and k != 'node_type'}
                }
            return None
            
        except Exception as e:
            logging.error(f"ArangoDB Node abrufen fehlgeschlagen: {e}")
            return None
    
    def find_nodes(self, node_type: str, filters: Dict = None) -> List[Dict]:
        try:
            if not self.db:
                return []
            
            # AQL Query erstellen
            bind_vars = {'node_type': node_type}
            where_conditions = ['doc.node_type == @node_type']
            
            if filters:
                for key, value in filters.items():
                    var_name = f'filter_{key}'
                    where_conditions.append(f'doc.{key} == @{var_name}')
                    bind_vars[var_name] = value
            
            query = f"""
                FOR doc IN {self.vertex_collection}
                FILTER {' AND '.join(where_conditions)}
                RETURN doc
            """
            
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            
            results = []
            for document in cursor:
                results.append({
                    'id': document['_id'],
                    'type': document.get('node_type', 'Unknown'),
                    'properties': {k: v for k, v in document.items() 
                                 if not k.startswith('_') and k != 'node_type'}
                })
            
            return results
            
        except Exception as e:
            logging.error(f"ArangoDB Nodes suchen fehlgeschlagen: {e}")
            return []
    
    def get_relationships(self, node_id: str, direction: str = "both") -> List[Dict]:
        try:
            if not self.db:
                return []
            
            bind_vars = {'node_id': node_id}
            
            if direction == "outgoing":
                query = f"""
                    FOR edge IN {self.edge_collection}
                    FILTER edge._from == @node_id
                    LET target = DOCUMENT(edge._to)
                    RETURN {{
                        edge_id: edge._id,
                        edge_type: edge.edge_type,
                        edge_properties: UNSET(edge, ['_id', '_key', '_from', '_to', '_rev', 'edge_type']),
                        target_id: target._id,
                        target_type: target.node_type,
                        target_properties: UNSET(target, ['_id', '_key', '_rev', 'node_type'])
                    }}
                """
            elif direction == "incoming":
                query = f"""
                    FOR edge IN {self.edge_collection}
                    FILTER edge._to == @node_id
                    LET target = DOCUMENT(edge._from)
                    RETURN {{
                        edge_id: edge._id,
                        edge_type: edge.edge_type,
                        edge_properties: UNSET(edge, ['_id', '_key', '_from', '_to', '_rev', 'edge_type']),
                        target_id: target._id,
                        target_type: target.node_type,
                        target_properties: UNSET(target, ['_id', '_key', '_rev', 'node_type'])
                    }}
                """
            else:  # both
                query = f"""
                    FOR edge IN {self.edge_collection}
                    FILTER edge._from == @node_id OR edge._to == @node_id
                    LET target = edge._from == @node_id ? DOCUMENT(edge._to) : DOCUMENT(edge._from)
                    RETURN {{
                        edge_id: edge._id,
                        edge_type: edge.edge_type,
                        edge_properties: UNSET(edge, ['_id', '_key', '_from', '_to', '_rev', 'edge_type']),
                        target_id: target._id,
                        target_type: target.node_type,
                        target_properties: UNSET(target, ['_id', '_key', '_rev', 'node_type'])
                    }}
                """
            
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            return list(cursor)
            
        except Exception as e:
            logging.error(f"ArangoDB Relationships abrufen fehlgeschlagen: {e}")
            return []
    
    def run_aql(self, query: str, bind_vars: Dict = None) -> List[Dict]:
        """Führe eine custom AQL Query aus"""
        try:
            if not self.db:
                return []
            
            cursor = self.db.aql.execute(query, bind_vars=bind_vars or {})
            return list(cursor)
            
        except Exception as e:
            logging.error(f"ArangoDB AQL Query fehlgeschlagen: {e}")
            return []
    
    def get_node_count(self) -> int:
        """Anzahl aller Nodes"""
        try:
            query = f"RETURN LENGTH({self.vertex_collection})"
            results = self.run_aql(query)
            if results:
                return results[0]
            return 0
            
        except Exception as e:
            logging.error(f"ArangoDB Node Count fehlgeschlagen: {e}")
            return 0
    
    def get_relationship_count(self) -> int:
        """Anzahl aller Relationships"""
        try:
            query = f"RETURN LENGTH({self.edge_collection})"
            results = self.run_aql(query)
            if results:
                return results[0]
            return 0
            
        except Exception as e:
            logging.error(f"ArangoDB Relationship Count fehlgeschlagen: {e}")
            return 0
    
    def delete_node(self, node_id: str) -> bool:
        """Lösche Node und alle verbundenen Edges"""
        try:
            if not self.graph:
                return False
            
            vertex_collection = self.graph.vertex_collection(self.vertex_collection)
            
            # Key aus ID extrahieren
            if '/' in node_id:
                key = node_id.split('/')[-1]
            else:
                key = node_id
            
            vertex_collection.delete(key)
            return True
            
        except Exception as e:
            logging.error(f"ArangoDB Node löschen fehlgeschlagen: {e}")
            return False
    
    def delete_relationship(self, edge_id: str) -> bool:
        """Lösche Relationship"""
        try:
            if not self.graph:
                return False
            
            edge_collection = self.graph.edge_collection(self.edge_collection)
            
            # Key aus ID extrahieren
            if '/' in edge_id:
                key = edge_id.split('/')[-1]
            else:
                key = edge_id
            
            edge_collection.delete(key)
            return True
            
        except Exception as e:
            logging.error(f"ArangoDB Relationship löschen fehlgeschlagen: {e}")
            return False
    
    def create_document_with_strategy(self, file_path: str, content: str, **metadata) -> str:
        """Erstelle Document-Node mit der neuen Unified Strategy"""
        try:
            # Generiere ID und Properties mit Strategy
            document_id = self.strategy.generate_document_id(file_path, content[:200])
            properties = self.strategy.create_document_properties(
                file_path=file_path,
                content_preview=content[:200],
                **metadata
            )
            
            # Erstelle Node in ArangoDB
            return self.create_node("Document", properties)
            
        except Exception as e:
            logger.error(f"Document mit Strategy erstellen fehlgeschlagen: {e}")
            return None
    
    def create_chunk_with_strategy(self, document_id: str, chunk_index: int, 
                                  content: str, **metadata) -> str:
        """Erstelle DocumentChunk-Node mit der neuen Unified Strategy"""
        try:
            # Generiere Chunk ID und Properties
            chunk_id = self.strategy.generate_chunk_id(document_id, chunk_index)
            properties = self.strategy.create_chunk_properties(
                document_id=document_id,
                chunk_index=chunk_index,
                content=content,
                **metadata
            )
            
            # Erstelle Node in ArangoDB
            return self.create_node("DocumentChunk", properties)
            
        except Exception as e:
            logger.error(f"Chunk mit Strategy erstellen fehlgeschlagen: {e}")
            return None
    
    def create_relationship_with_strategy(self, from_node_id: str, to_node_id: str, 
                                         relationship_type: str, **metadata) -> str:
        """Erstelle Relationship mit der neuen Unified Strategy"""
        try:
            # Erstelle Relationship Properties
            rel_props = self.strategy.create_relationship_properties(
                relationship_type=relationship_type,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                **metadata
            )
            
            # Erstelle Edge in ArangoDB
            return self.create_edge(from_node_id, to_node_id, relationship_type, rel_props)
            
        except Exception as e:
            logger.error(f"Relationship mit Strategy erstellen fehlgeschlagen: {e}")
            return None


def get_backend_class():
    """Factory-Funktion für ArangoDB Backend"""
    return ArangoDBGraphBackend

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_arangodb"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...zNDpu0s="  # Gekuerzt fuer Sicherheit
module_organization_key = "9ccf2bffcc3cc77e5613cd6d66c73e1e47da2d6f0d25d1c31e6f1050fd6b8b92"
module_file_key = "e17a3ca1c72d3c23b70f69932087754ef6e6b58865cc94a579f8faab62f85461"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
