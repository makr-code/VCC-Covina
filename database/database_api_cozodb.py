#!/usr/bin/env python3
"""
CozoDB Database API Implementation
Hybrid Relational-Graph-Vector Database mit Datalog Query Language
"""

import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from database.database_api_base import VectorDatabaseBackend, GraphDatabaseBackend, RelationalDatabaseBackend

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

logger = logging.getLogger(__name__)

class CozoDBVectorBackend(VectorDatabaseBackend):
    """CozoDB Vector Backend mit HNSW Integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = config
        self.client = None
        # heavy initialization moved to connect() to avoid network/import at instantiation
        self._initialized = False
    
    def _initialize_client(self):
        """Initialisiert CozoDB Client"""
        try:
            # CozoDB Python bindings
            import pycozo  # type: ignore[import-unresolved]
            
            # Konfiguration basierend auf Backend-Typ
            backend_type = self.config.get('backend_type', 'sqlite')
            path = self.config.get('path', './cozodb.db')
            
            if backend_type == 'memory':
                self.client = pycozo.DbInstance('mem', {})
            elif backend_type == 'sqlite':
                self.client = pycozo.DbInstance('sqlite', {'path': path})
            elif backend_type == 'rocksdb':
                self.client = pycozo.DbInstance('rocksdb', {'path': path})
            else:
                raise ValueError(f"Unsupported CozoDB backend: {backend_type}")
            
            # HNSW Index Schema initialisieren
            self._initialize_vector_schema()
            logger.info(f"CozoDB Vector Backend initialisiert ({backend_type})")
            
        except ImportError:
            logger.error("pycozo nicht installiert. Installieren Sie mit: pip install pycozo")
            raise
        except Exception as e:
            logger.error(f"Fehler beim Initialisieren von CozoDB: {e}")
            raise

    def connect(self) -> bool:
        """Initialize the CozoDB client lazily and verify availability."""
        if self._initialized:
            return True
        try:
            self._initialize_client()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"CozoDB connect failed: {e}")
            return False
    
    def _initialize_vector_schema(self):
        """Initialisiert Vector Schema mit HNSW Index"""
        try:
            # Relation für Dokumente mit Vektoren erstellen
            schema_query = """
            :create documents {
                id: String,
                collection: String,
                text: String,
                embedding: <F32; 384>,  # 384-dimensionale Embeddings
                metadata: Json,
                => id
            }
            """
            self.client.run(schema_query)
            
            # HNSW Index für Vektor-Suche erstellen
            index_query = """
            ::hnsw create documents:embedding {
                dim: 384,
                m: 16,
                ef_construction: 200,
                ef: 64,
                filter: collection != null
            }
            """
            self.client.run(index_query)
            
        except Exception as e:
            logger.warning(f"Schema bereits vorhanden oder Fehler: {e}")
    
    def list_collections(self) -> List[str]:
        """Listet alle Collections auf"""
        try:
            query = "?[collection] := *documents{collection}, distinct(collection)"
            result = self.client.run(query)
            return [row[0] for row in result['rows']]
        except Exception as e:
            logger.error(f"Fehler beim Auflisten der Collections: {e}")
            return []
    
    def create_collection(self, collection_name: str, metadata: Optional[Dict] = None) -> bool:
        """Erstellt neue Collection (implizit durch Insert)"""
        try:
            # Collections werden implizit durch Einfügen erstellt
            logger.info(f"Collection '{collection_name}' wird beim ersten Insert erstellt")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Collection {collection_name}: {e}")
            return False
    
    def add_documents(self, collection_name: str, documents: List[Dict[str, Any]], 
                     embeddings: List[List[float]], ids: Optional[List[str]] = None) -> bool:
        """
        Fügt Dokumente mit beliebigen Metadaten (inkl. Relationen, Kontext, Tags) hinzu.
        """
        try:
            if not ids:
                ids = [f"{collection_name}_{i}" for i in range(len(documents))]
            
            # Daten für Bulk Insert vorbereiten
            data_rows = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                row = [
                    ids[i],
                    collection_name,
                    doc.get('text', ''),
                    embedding,
                    json.dumps(doc.get('metadata', {}))
                ]
                data_rows.append(row)
            
            # Bulk Insert mit Datalog
            query = """
            ?[id, collection, text, embedding, metadata] <- $data
            :put documents {id, collection, text, embedding, metadata}
            """
            
            result = self.client.run(query, {'data': data_rows})
            logger.info(f"✅ {len(documents)} Dokumente zu '{collection_name}' hinzugefügt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen von Dokumenten: {e}")
            return False
    
    def similarity_search(self, collection_name: str, query_embedding: List[float], 
                         k: int = 5, filter: Optional[Dict] = None) -> List[Dict]:
        """HNSW-basierte Ähnlichkeitssuche"""
        try:
            # Filter für Collection
            filter_clause = f"collection == '{collection_name}'"
            if filter:
                for key, value in filter.items():
                    filter_clause += f" && metadata->{key} == '{value}'"
            
            # HNSW Suche mit Datalog
            query = f"""
            candidates[id, distance] := ~documents:embedding{{
                query: $query_vector,
                k: {k},
                filter: {filter_clause}
            }}
            
            ?[id, text, metadata, distance] := candidates[id, distance],
                                             *documents{{id, text, metadata}}
            
            :order distance
            :limit {k}
            """
            
            result = self.client.run(query, {'query_vector': query_embedding})
            
            # Ergebnisse formatieren
            results = []
            for row in result['rows']:
                doc_id, text, metadata_json, distance = row
                try:
                    metadata = json.loads(metadata_json) if metadata_json else {}
                except:
                    metadata = {}
                
                results.append({
                    'id': doc_id,
                    'text': text,
                    'metadata': metadata,
                    'distance': distance,
                    'score': 1.0 - distance  # Convert distance to similarity score
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Fehler bei der Ähnlichkeitssuche: {e}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """Löscht alle Dokumente einer Collection"""
        try:
            query = f"""
            ?[id] := *documents{{collection: '{collection_name}', id}}
            :rm documents {{id}}
            """
            self.client.run(query)
            logger.info(f"Collection '{collection_name}' gelöscht")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Collection {collection_name}: {e}")
            return False


class CozoDBGraphBackend(GraphDatabaseBackend):
    """CozoDB Graph Backend mit Datalog Queries"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = config
        self.client = None
        # postpone heavy initialization to connect()
        self._initialized = False

    def connect(self) -> bool:
        """Lazily initialize the CozoDB client for Graph backend."""
        if getattr(self, '_initialized', False):
            return True
        try:
            self._initialize_client()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"CozoDB Graph connect failed: {e}")
            return False
    
    def _initialize_client(self):
        """Initialisiert CozoDB Client (shared mit Vector Backend)"""
        try:
            import pycozo  # type: ignore[import-unresolved]
            
            backend_type = self.config.get('backend_type', 'sqlite')
            path = self.config.get('path', './cozodb.db')
            
            if backend_type == 'memory':
                self.client = pycozo.DbInstance('mem', {})
            elif backend_type == 'sqlite':
                self.client = pycozo.DbInstance('sqlite', {'path': path})
            elif backend_type == 'rocksdb':
                self.client = pycozo.DbInstance('rocksdb', {'path': path})
            
            self._initialize_graph_schema()
            logger.info(f"CozoDB Graph Backend initialisiert ({backend_type})")
            
        except ImportError:
            logger.error("pycozo nicht installiert")
            raise
        except Exception as e:
            logger.error(f"Fehler beim Initialisieren von CozoDB Graph: {e}")
            raise
    
    def _initialize_graph_schema(self):
        """Initialisiert Graph Schema"""
        try:
            # Nodes (Vertices)
            nodes_query = """
            :create nodes {
                id: String,
                label: String,
                properties: Json,
                => id
            }
            """
            self.client.run(nodes_query)
            
            # Edges (Relationships)
            edges_query = """
            :create edges {
                id: String,
                from_id: String,
                to_id: String,
                relationship: String,
                properties: Json,
                => id
            }
            """
            self.client.run(edges_query)
            
        except Exception as e:
            logger.warning(f"Graph Schema bereits vorhanden: {e}")
    
    def create_node(self, node_id: str, label: str, properties: Dict[str, Any]) -> bool:
        """
        Erstellt einen Knoten mit beliebigen Properties (inkl. Metadaten, Relationen etc.)
        """
        node = {
            "id": node_id,
            "label": label,
            "properties": properties,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            query = """
            ?[id, label, properties] <- [[$node_id, $label, $properties]]
            :put nodes {id, label, properties}
            """
            
            result = self.client.run(query, {
                'node_id': node_id,
                'label': label,
                'properties': json.dumps(properties)
            })
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Knotens: {e}")
            return False
    
    def create_relationship(self, from_id: str, to_id: str, relationship: str, 
                          properties: Optional[Dict[str, Any]] = None) -> bool:
        """
        Erstellt eine Kante mit beliebigen Properties (inkl. Relationen, Kontext etc.)
        """
        edge_id = f"edge_{uuid.uuid4().hex}"
        edge = {
            "from": from_id,
            "to": to_id,
            "relationship": relationship,
            "properties": properties or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            query = """
            ?[id, from_id, to_id, relationship, properties] <- [[$edge_id, $from_id, $to_id, $relationship, $properties]]
            :put edges {id, from_id, to_id, relationship, properties}
            """
            
            result = self.client.run(query, {
                'edge_id': edge_id,
                'from_id': from_id,
                'to_id': to_id,
                'relationship': relationship,
                'properties': json.dumps(properties)
            })
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Kante: {e}")
            return False
    
    def find_nodes(self, label: Optional[str] = None, properties: Optional[Dict] = None) -> List[Dict]:
        """Findet Knoten basierend auf Label und Properties"""
        try:
            # Base query
            query_parts = ["?[id, label, properties] := *nodes{id, label, properties}"]
            params = {}
            
            # Filter für Label
            if label:
                query_parts[0] += f", label == '{label}'"
            
            # TODO: Property Filter implementation
            
            query = ", ".join(query_parts)
            result = self.client.run(query, params)
            
            nodes = []
            for row in result['rows']:
                node_id, node_label, props_json = row
                try:
                    properties = json.loads(props_json) if props_json else {}
                except:
                    properties = {}
                
                nodes.append({
                    'id': node_id,
                    'label': node_label,
                    'properties': properties
                })
            
            return nodes
            
        except Exception as e:
            logger.error(f"Fehler beim Suchen von Knoten: {e}")
            return []
    
    def get_neighbors(self, node_id: str, relationship: Optional[str] = None, 
                     direction: str = 'both') -> List[Dict]:
        """Findet Nachbarknoten mit Datalog"""
        try:
            # Datalog Query für Nachbarn
            if direction == 'outgoing':
                query = """
                ?[neighbor_id, relationship, neighbor_label, neighbor_props] := 
                    *edges{from_id, to_id, relationship}, from_id == $node_id,
                    *nodes{id: to_id, label: neighbor_label, properties: neighbor_props},
                    neighbor_id = to_id
                """
            elif direction == 'incoming':
                query = """
                ?[neighbor_id, relationship, neighbor_label, neighbor_props] := 
                    *edges{from_id, to_id, relationship}, to_id == $node_id,
                    *nodes{id: from_id, label: neighbor_label, properties: neighbor_props},
                    neighbor_id = from_id
                """
            else:  # both
                query = """
                outgoing[neighbor_id, relationship, neighbor_label, neighbor_props] := 
                    *edges{from_id, to_id, relationship}, from_id == $node_id,
                    *nodes{id: to_id, label: neighbor_label, properties: neighbor_props},
                    neighbor_id = to_id
                    
                incoming[neighbor_id, relationship, neighbor_label, neighbor_props] := 
                    *edges{from_id, to_id, relationship}, to_id == $node_id,
                    *nodes{id: from_id, label: neighbor_label, properties: neighbor_props},
                    neighbor_id = from_id
                
                ?[neighbor_id, relationship, neighbor_label, neighbor_props] := 
                    outgoing[neighbor_id, relationship, neighbor_label, neighbor_props]
                ?[neighbor_id, relationship, neighbor_label, neighbor_props] := 
                    incoming[neighbor_id, relationship, neighbor_label, neighbor_props]
                """
            
            # Relationship Filter
            if relationship:
                query += f" && relationship == '{relationship}'"
            
            result = self.client.run(query, {'node_id': node_id})
            
            neighbors = []
            for row in result['rows']:
                neighbor_id, rel, label, props_json = row
                try:
                    properties = json.loads(props_json) if props_json else {}
                except:
                    properties = {}
                
                neighbors.append({
                    'id': neighbor_id,
                    'label': label,
                    'properties': properties,
                    'relationship': rel
                })
            
            return neighbors
            
        except Exception as e:
            logger.error(f"Fehler beim Finden von Nachbarn für {node_id}: {e}")
            return []


class CozoDBRelationalBackend(RelationalDatabaseBackend):
    """CozoDB Relational Backend mit SQL-ähnlichen Datalog Queries"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = config
        self.client = None
        # postpone heavy initialization to connect()
        self._initialized = False

    def connect(self) -> bool:
        """Lazily initialize the CozoDB client for Relational backend."""
        if getattr(self, '_initialized', False):
            return True
        try:
            self._initialize_client()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"CozoDB Relational connect failed: {e}")
            return False
    
    def _initialize_client(self):
        """Initialisiert CozoDB Client (shared)"""
        try:
            import pycozo  # type: ignore[import-unresolved]
            
            backend_type = self.config.get('backend_type', 'sqlite')
            path = self.config.get('path', './cozodb.db')
            
            if backend_type == 'memory':
                self.client = pycozo.DbInstance('mem', {})
            elif backend_type == 'sqlite':
                self.client = pycozo.DbInstance('sqlite', {'path': path})
            elif backend_type == 'rocksdb':
                self.client = pycozo.DbInstance('rocksdb', {'path': path})
            
            logger.info(f"CozoDB Relational Backend initialisiert ({backend_type})")
            
        except ImportError:
            logger.error("pycozo nicht installiert")
            raise
        except Exception as e:
            logger.error(f"Fehler beim Initialisieren von CozoDB Relational: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Führt Datalog Query aus"""
        try:
            result = self.client.run(query, params or {})
            
            # Convert to list of dicts
            if 'headers' in result and 'rows' in result:
                headers = result['headers']
                rows = result['rows']
                
                return [
                    dict(zip(headers, row))
                    for row in rows
                ]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Fehler beim Ausführen der Query: {e}")
            return []
    
    def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        """Erstellt Tabelle mit Datalog Schema"""
        try:
            # Schema für CozoDB erstellen
            columns = []
            keys = []
            
            for col_name, col_type in schema.items():
                if col_type.lower() in ['string', 'text']:
                    columns.append(f"{col_name}: String")
                elif col_type.lower() in ['int', 'integer']:
                    columns.append(f"{col_name}: Int")
                elif col_type.lower() in ['float', 'double']:
                    columns.append(f"{col_name}: Float")
                elif col_type.lower() == 'json':
                    columns.append(f"{col_name}: Json")
                else:
                    columns.append(f"{col_name}: String")  # Default
                
                # Erste Spalte als Key verwenden (vereinfacht)
                if not keys:
                    keys.append(col_name)
            
            query = f"""
            :create {table_name} {{
                {', '.join(columns)},
                => {', '.join(keys)}
            }}
            """
            
            self.client.run(query)
            logger.info(f"Tabelle '{table_name}' erstellt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Tabelle {table_name}: {e}")
            return False
    
    def insert_data(self, table_name: str, data: List[Dict[str, Any]]) -> bool:
        """Fügt Daten in Tabelle ein"""
        try:
            if not data:
                return True
            
            # Spalten aus erstem Datensatz ermitteln
            columns = list(data[0].keys())
            
            # Daten für Bulk Insert vorbereiten
            rows = []
            for item in data:
                row = [item.get(col, None) for col in columns]
                rows.append(row)
            
            # Datalog Insert Query
            placeholders = ', '.join(columns)
            query = f"""
            ?[{placeholders}] <- $data
            :put {table_name} {{{placeholders}}}
            """
            
            result = self.client.run(query, {'data': rows})
            logger.info(f"✅ {len(data)} Datensätze in '{table_name}' eingefügt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Einfügen in Tabelle {table_name}: {e}")
            return False

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_cozodb"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...GLVhFWo="  # Gekuerzt fuer Sicherheit
module_organization_key = "322175e77dad3bcc4fcd74531f29359c8f1d4f9bb54fdfd22dc873b10208c0f6"
module_file_key = "3c422cc8d409a9c3f383ab224ba203316f322d4153583f28d0b76b9ce4c1d177"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
