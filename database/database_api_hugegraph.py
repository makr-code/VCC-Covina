#!/usr/bin/env python3
"""
Apache HugeGraph Database API Implementation
Enterprise-grade scalable Graph Database mit Gremlin/Cypher Support
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from database.database_api_base import GraphDatabaseBackend
from datetime import datetime

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

logger = logging.getLogger(__name__)

class HugeGraphBackend(GraphDatabaseBackend):
    """Apache HugeGraph Backend mit Gremlin und REST API"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = config
        self.client = None
        self.graph_name = config.get('graph_name', 'hugegraph')
        # postpone client initialization to connect()
        self._initialized = False
    
    def _initialize_client(self):
        """Initialisiert HugeGraph Client"""
        try:
            # HugeGraph Python Client
            from pyhugegraph.client import HugeClient
            
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 8080)
            username = self.config.get('username', 'admin')
            password = self.config.get('password', 'admin')
            
            # REST API URL
            url = f"http://{host}:{port}"
            
            self.client = HugeClient(
                url=url,
                graph=self.graph_name,
                username=username,
                password=password,
                timeout=30
            )
            
            # Schema initialisieren
            self._initialize_schema()
            logger.info(f"HugeGraph Backend verbunden: {url}/{self.graph_name}")
            
        except ImportError:
            logger.error("pyhugegraph nicht installiert. Installieren Sie mit: pip install pyhugegraph")
            raise
        except Exception as e:
            logger.error(f"Fehler beim Verbinden mit HugeGraph: {e}")
            raise

    def connect(self) -> bool:
        """Lazily initialize and connect the HugeGraph client."""
        if self._initialized:
            return True
        try:
            self._initialize_client()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"HugeGraph connect failed: {e}")
            return False
    
    def _initialize_schema(self):
        """Initialisiert HugeGraph Schema für Veritas"""
        try:
            schema = self.client.schema()
            
            # Property Keys definieren
            property_keys = [
                ('id', 'TEXT'),
                ('label', 'TEXT'),
                ('title', 'TEXT'),
                ('content', 'TEXT'),
                ('author', 'TEXT'),
                ('behoerde', 'TEXT'),
                ('verfahrensnummer', 'TEXT'),
                ('aktenzeichen', 'TEXT'),
                ('rechtsgebiet', 'TEXT'),
                ('gemarkung', 'TEXT'),
                ('flur', 'TEXT'),
                ('flurstueck', 'TEXT'),
                ('koordinaten_etrs', 'TEXT'),
                ('frist', 'TEXT'),
                ('status', 'TEXT'),
                ('publication_date', 'DATE'),
                ('created_at', 'DATE'),
                ('updated_at', 'DATE'),
                ('metadata', 'TEXT')  # JSON als Text
            ]
            
            for prop_name, prop_type in property_keys:
                try:
                    schema.propertyKey(prop_name).asText().ifNotExist().create()
                except Exception as e:
                    logger.debug(f"Property Key {prop_name} bereits vorhanden: {e}")
            
            # Vertex Labels definieren
            vertex_labels = [
                'Document',
                'Concept', 
                'Entity',
                'Verfahren',
                'Behoerde',
                'SpatialData',
                'Koordinaten'
            ]
            
            for label in vertex_labels:
                try:
                    schema.vertexLabel(label).properties(
                        'id', 'title', 'content', 'metadata', 'created_at', 'updated_at'
                    ).primaryKeys('id').ifNotExist().create()
                except Exception as e:
                    logger.debug(f"Vertex Label {label} bereits vorhanden: {e}")
            
            # Edge Labels definieren
            edge_labels = [
                'RELATES_TO',
                'REFERENCES',
                'CONTAINS',
                'BELONGS_TO',
                'LOCATED_IN',
                'MANAGED_BY',
                'PART_OF'
            ]
            
            for label in edge_labels:
                try:
                    schema.edgeLabel(label).sourceLabel('Document').targetLabel('Document').properties(
                        'relationship', 'weight', 'metadata', 'created_at'
                    ).ifNotExist().create()
                except Exception as e:
                    logger.debug(f"Edge Label {label} bereits vorhanden: {e}")
            
            logger.info("✅ HugeGraph Schema initialisiert")
            
        except Exception as e:
            logger.warning(f"Schema-Initialisierung fehlgeschlagen: {e}")
    
    def create_node(self, node_id: str, label: str, properties: Dict[str, Any]) -> bool:
        """Erstellt einen Vertex in HugeGraph"""
        try:
            vertex = self.client.graph().addVertex(
                label=label,
                properties={
                    'id': node_id,
                    'metadata': json.dumps(properties),
                    'created_at': properties.get('created_at', ''),
                    'updated_at': properties.get('updated_at', ''),
                    **{k: str(v) for k, v in properties.items() if k not in ['created_at', 'updated_at']}
                }
            )
            
            logger.debug(f"✅ Vertex erstellt: {node_id} ({label})")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Vertex {node_id}: {e}")
            return False
    
    def create_relationship(self, from_id: str, to_id: str, relationship: str, 
                          properties: Optional[Dict[str, Any]] = None) -> bool:
        """Erstellt eine Edge in HugeGraph"""
        try:
            properties = properties or {}
            
            edge = self.client.graph().addEdge(
                label=relationship,
                outVertex=from_id,
                inVertex=to_id,
                properties={
                    'relationship': relationship,
                    'weight': properties.get('weight', 1.0),
                    'metadata': json.dumps(properties),
                    'created_at': properties.get('created_at', ''),
                    **{k: str(v) for k, v in properties.items() if k not in ['weight', 'created_at']}
                }
            )
            
            logger.debug(f"✅ Edge erstellt: {from_id} --[{relationship}]--> {to_id}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Edge {from_id}->{to_id}: {e}")
            return False
    
    def find_nodes(self, label: Optional[str] = None, properties: Optional[Dict] = None) -> List[Dict]:
        """Findet Vertices mit Gremlin Traversal"""
        try:
            # Gremlin Query erstellen
            g = self.client.gremlin()
            
            if label:
                traversal = g.V().hasLabel(label)
            else:
                traversal = g.V()
            
            # Property Filter
            if properties:
                for key, value in properties.items():
                    traversal = traversal.has(key, value)
            
            # Vertices mit Properties abrufen
            traversal = traversal.valueMap(True)  # Include ID and Label
            
            results = traversal.toList()
            
            # Ergebnisse formatieren
            nodes = []
            for vertex_data in results:
                node = {
                    'id': vertex_data.get('id'),
                    'label': vertex_data.get('label'),
                    'properties': {}
                }
                
                # Properties extrahieren
                for key, value in vertex_data.items():
                    if key not in ['id', 'label'] and value:
                        if isinstance(value, list) and len(value) > 0:
                            node['properties'][key] = value[0]
                        else:
                            node['properties'][key] = value
                
                # Metadata JSON parsen
                if 'metadata' in node['properties']:
                    try:
                        metadata = json.loads(node['properties']['metadata'])
                        node['properties'].update(metadata)
                        del node['properties']['metadata']
                    except:
                        pass
                
                nodes.append(node)
            
            return nodes
            
        except Exception as e:
            logger.error(f"Fehler beim Suchen von Vertices: {e}")
            return []
    
    def get_neighbors(self, node_id: str, relationship: Optional[str] = None, 
                     direction: str = 'both') -> List[Dict]:
        """Findet Nachbar-Vertices mit Gremlin"""
        try:
            g = self.client.gremlin()
            
            # Start Vertex
            traversal = g.V(node_id)
            
            # Richtung und Relationship
            if direction == 'outgoing':
                if relationship:
                    traversal = traversal.outE(relationship).inV()
                else:
                    traversal = traversal.out()
            elif direction == 'incoming':
                if relationship:
                    traversal = traversal.inE(relationship).outV()
                else:
                    traversal = traversal.in_()
            else:  # both
                if relationship:
                    traversal = traversal.bothE(relationship).otherV()
                else:
                    traversal = traversal.both()
            
            # Ergebnisse mit Properties
            traversal = traversal.valueMap(True).dedup()
            
            results = traversal.toList()
            
            # Formatierung wie bei find_nodes
            neighbors = []
            for vertex_data in results:
                neighbor = {
                    'id': vertex_data.get('id'),
                    'label': vertex_data.get('label'),
                    'properties': {}
                }
                
                for key, value in vertex_data.items():
                    if key not in ['id', 'label'] and value:
                        if isinstance(value, list) and len(value) > 0:
                            neighbor['properties'][key] = value[0]
                        else:
                            neighbor['properties'][key] = value
                
                # Metadata verarbeiten
                if 'metadata' in neighbor['properties']:
                    try:
                        metadata = json.loads(neighbor['properties']['metadata'])
                        neighbor['properties'].update(metadata)
                        del neighbor['properties']['metadata']
                    except:
                        pass
                
                neighbors.append(neighbor)
            
            return neighbors
            
        except Exception as e:
            logger.error(f"Fehler beim Finden von Nachbarn für {node_id}: {e}")
            return []
    
    def execute_gremlin(self, gremlin_query: str) -> List[Dict]:
        """Führt rohe Gremlin Query aus"""
        try:
            result = self.client.gremlin().execute(gremlin_query)
            
            # Ergebnis als Liste von Dictionaries zurückgeben
            if isinstance(result, list):
                return [{'result': item} for item in result]
            else:
                return [{'result': result}]
                
        except Exception as e:
            logger.error(f"Fehler beim Ausführen der Gremlin Query: {e}")
            return []
    
    def execute_cypher(self, cypher_query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Führt Cypher Query aus (falls von HugeGraph unterstützt)"""
        try:
            # HugeGraph unterstützt Cypher über REST API
            result = self.client.cypher().execute(cypher_query, params or {})
            return result
            
        except Exception as e:
            logger.error(f"Fehler beim Ausführen der Cypher Query: {e}")
            return []
    
    def get_node_count(self, label: Optional[str] = None) -> int:
        """Zählt Anzahl der Vertices"""
        try:
            g = self.client.gremlin()
            
            if label:
                count = g.V().hasLabel(label).count().next()
            else:
                count = g.V().count().next()
            
            return int(count)
            
        except Exception as e:
            logger.error(f"Fehler beim Zählen der Vertices: {e}")
            return 0
    
    def get_relationship_count(self, relationship: Optional[str] = None) -> int:
        """Zählt Anzahl der Edges"""
        try:
            g = self.client.gremlin()
            
            if relationship:
                count = g.E().hasLabel(relationship).count().next()
            else:
                count = g.E().count().next()
            
            return int(count)
            
        except Exception as e:
            logger.error(f"Fehler beim Zählen der Edges: {e}")
            return 0
    
    def pagerank(self, iterations: int = 20, damping: float = 0.85) -> Dict[str, float]:
        """Führt PageRank Algorithmus aus"""
        try:
            # HugeGraph Algorithm API verwenden
            result = self.client.algorithm().pagerank(
                iterations=iterations,
                damping=damping
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Fehler beim PageRank Algorithmus: {e}")
            return {}
    
    def shortest_path(self, source_id: str, target_id: str, max_depth: int = 6) -> List[str]:
        """Findet kürzesten Pfad zwischen zwei Vertices"""
        try:
            g = self.client.gremlin()
            
            # Shortest Path mit Gremlin
            path = g.V(source_id).repeat(
                g.both().simplePath()
            ).until(
                g.hasId(target_id).or_().loops().is_(max_depth)
            ).hasId(target_id).path().by('id').limit(1).next()
            
            return [str(vertex_id) for vertex_id in path]
            
        except Exception as e:
            logger.error(f"Fehler beim Finden des kürzesten Pfads: {e}")
            return []
    
    def community_detection(self, algorithm: str = 'louvain') -> Dict[str, int]:
        """Community Detection Algorithmus"""
        try:
            if algorithm == 'louvain':
                result = self.client.algorithm().louvain()
            elif algorithm == 'label_propagation':
                result = self.client.algorithm().lpa()
            else:
                raise ValueError(f"Unbekannter Algorithmus: {algorithm}")
            
            return result
            
        except Exception as e:
            logger.error(f"Fehler bei Community Detection: {e}")
            return {}
    
    def close(self):
        """Schließt HugeGraph Verbindung"""
        try:
            if self.client:
                self.client.close()
                logger.info("HugeGraph Verbindung geschlossen")
        except Exception as e:
            logger.error(f"Fehler beim Schließen der HugeGraph Verbindung: {e}")


# Utility Funktionen für HugeGraph
def install_hugegraph_dependencies():
    """Installiert HugeGraph Python Dependencies"""
    import subprocess
    import sys
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyhugegraph'])
        logger.info("✅ pyhugegraph erfolgreich installiert")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Fehler beim Installieren von pyhugegraph: {e}")
        return False


def validate_hugegraph_connection(config: Dict[str, Any]) -> bool:
    """Validiert HugeGraph Verbindung"""
    try:
        backend = HugeGraphBackend(config)
        
        # Einfacher Test
        count = backend.get_node_count()
        logger.info(f"✅ HugeGraph Verbindung erfolgreich - {count} Vertices gefunden")
        
        backend.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ HugeGraph Verbindung fehlgeschlagen: {e}")
        return False

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_hugegraph"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...D/l7XA0="  # Gekuerzt fuer Sicherheit
module_organization_key = "4ff582d2e7fbe7d8707674c0f9c81694d71c86a162fff557098c4c702c352265"
module_file_key = "07c9ca99dc125ec92fe3878b8c85fb966bd344929ef82079ee73807b6e4d8984"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
