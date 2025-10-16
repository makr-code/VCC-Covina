#!/usr/bin/env python3
"""
Cayley Graph Database Backend
HTTP API basierte Implementierung
"""

import logging
import json
import uuid
try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    requests = None
    _HAS_REQUESTS = False
    # lightweight shim when requests is absent
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error
    import json as _json

    class _RequestsShimResponse:
        def __init__(self, code, content, headers=None):
            self.status_code = code
            self.text = content
            self._content = content
            self.headers = headers or {}

        def json(self):
            try:
                return _json.loads(self._content) if self._content else {}
            except Exception:
                return {}

        def raise_for_status(self):
            if 400 <= int(self.status_code):
                raise _urllib_error.HTTPError(None, int(self.status_code), 'HTTP error', None, None)

    class _RequestsShim:
        def __init__(self):
            self.auth = None

        def _do(self, method, url, json=None, timeout=5):
            data = None
            headers = {'Content-Type': 'application/json'} if json is not None else {}
            if json is not None:
                data = _json.dumps(json).encode('utf-8')
            req = _urllib_request.Request(url, data=data, headers=headers, method=method)
            try:
                with _urllib_request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                    charset = resp.headers.get_content_charset() or 'utf-8'
                    text = raw.decode(charset) if raw else ''
                    return _RequestsShimResponse(resp.getcode(), text, resp.headers)
            except _urllib_error.HTTPError as e:
                try:
                    body = e.read().decode('utf-8') if hasattr(e, 'read') else ''
                except Exception:
                    body = ''
                return _RequestsShimResponse(e.code if hasattr(e, 'code') else 500, body)

        def get(self, url, timeout=5):
            return self._do('GET', url, timeout=timeout)

        def post(self, url, json=None, timeout=5):
            return self._do('POST', url, json=json, timeout=timeout)

        def close(self):
            return None
from typing import Dict, List, Optional
from datetime import datetime, timezone
from database.database_api_base import GraphDatabaseBackend

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None


class CayleyGraphBackend(GraphDatabaseBackend):
    """Cayley Graph Database über HTTP API"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.base_url = config.get('url', 'http://localhost:64210')
        self.api_version = config.get('api_version', 'v2')
        self.timeout = config.get('timeout', 30)
        self.session = None
        
        # API Endpoints
        self.endpoints = {
            'write': f"{self.base_url}/api/{self.api_version}/write",
            'query': f"{self.base_url}/api/{self.api_version}/query",
            'delete': f"{self.base_url}/api/{self.api_version}/delete",
            'read': f"{self.base_url}/api/{self.api_version}/read"
        }
        
    def connect(self) -> bool:
        try:
            if _HAS_REQUESTS:
                self.session = requests.Session()
                self.session.timeout = self.timeout
            else:
                self.session = _RequestsShim()
            
            # Test connection
            response = self.session.get(f"{self.base_url}/api/{self.api_version}")
            
            if response.status_code == 200:
                logging.info(f"Cayley verbunden: {self.base_url}")
                return True
            else:
                logging.error(f"Cayley Verbindung fehlgeschlagen: Status {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"Cayley Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        if self.session:
            self.session.close()
            self.session = None
    
    def is_available(self) -> bool:
        try:
            if self.session:
                response = self.session.get(f"{self.base_url}/api/{self.api_version}", timeout=5)
                return response.status_code == 200
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        return "Cayley Graph"
    
    def create_node(self, node_type: str, properties: Dict) -> str:
        """
        Erstellt einen Knoten mit beliebigen Properties (inkl. Metadaten, Relationen etc.)
        """
        node_id = properties.get("chunk_id") or properties.get("id") or str(uuid.uuid4())
        node = {
            "id": node_id,
            "type": node_type,
            "properties": properties,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        # Annahme: HTTP API unterstützt JSON-Properties
        try:
            # HTTP POST an Cayley API
            response = self.session.post(
                self.endpoints['write'],
                json=node,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return node_id
            else:
                logging.error(f"Cayley Node erstellen fehlgeschlagen: Status {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Cayley Node erstellen fehlgeschlagen: {e}")
            return None
    
    def create_edge(self, from_id: str, to_id: str, edge_type: str, properties: Dict = None) -> str:
        """
        Erstellt eine Kante mit beliebigen Properties (inkl. Relationen, Kontext etc.)
        """
        edge_id = str(uuid.uuid4())
        edge = {
            "id": edge_id,
            "from": from_id,
            "to": to_id,
            "type": edge_type,
            "properties": properties or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        # Annahme: HTTP API unterstützt JSON-Properties
        try:
            # HTTP POST an Cayley API
            response = self.session.post(
                self.endpoints['write'],
                json=edge,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return edge_id
            else:
                logging.error(f"Cayley Edge erstellen fehlgeschlagen: Status {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Cayley Edge erstellen fehlgeschlagen: {e}")
            return None
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Hole Node-Daten via Gizmo Query"""
        try:
            node_iri = f"urn:node:{node_id}"
            
            # Gizmo Query für Node-Eigenschaften
            query = {
                "query": f"""
                    g.V("{node_iri}").Has("rdf:type").As("type")
                        .Back("type").Out().As("props")
                        .All()
                """,
                "lang": "gizmo"
            }
            
            response = self.session.post(
                self.endpoints['query'],
                json=query,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_node_result(result, node_id)
            
            return None
            
        except Exception as e:
            logging.error(f"Cayley Get Node fehlgeschlagen: {e}")
            return None
    
    def find_nodes(self, node_type: str, filters: Dict = None) -> List[Dict]:
        """Suche Nodes nach Typ und Filtern"""
        try:
            # Basis Gizmo Query
            query_str = f'g.V().Has("rdf:type", "urn:type:{node_type}")'
            
            # Filter hinzufügen
            if filters:
                for key, value in filters.items():
                    query_str += f'.Has("urn:prop:{key}", "{self._serialize_value(value)}")'
            
            query_str += '.All()'
            
            query = {
                "query": query_str,
                "lang": "gizmo"
            }
            
            response = self.session.post(
                self.endpoints['query'],
                json=query,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_nodes_result(result)
            
            return []
            
        except Exception as e:
            logging.error(f"Cayley Find Nodes fehlgeschlagen: {e}")
            return []
    
    def get_relationships(self, node_id: str, direction: str = "both") -> List[Dict]:
        """Hole Beziehungen eines Nodes"""
        try:
            node_iri = f"urn:node:{node_id}"
            
            if direction == "outgoing":
                query_str = f'g.V("{node_iri}").Out().As("target").All()'
            elif direction == "incoming":
                query_str = f'g.V("{node_iri}").In().As("source").All()'
            else:  # both
                query_str = f'g.V("{node_iri}").Both().As("connected").All()'
            
            query = {
                "query": query_str,
                "lang": "gizmo"
            }
            
            response = self.session.post(
                self.endpoints['query'],
                json=query,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_relationships_result(result, node_id, direction)
            
            return []
            
        except Exception as e:
            logging.error(f"Cayley Get Relationships fehlgeschlagen: {e}")
            return []
    
    def delete_node(self, node_id: str) -> bool:
        """Lösche Node und alle verbundenen Edges"""
        try:
            node_iri = f"urn:node:{node_id}"
            
            # Alle Quads mit diesem Node finden und löschen
            query = {
                "query": f'g.V("{node_iri}").Out().All()',
                "lang": "gizmo"
            }
            
            # TODO: Implementiere Delete-Funktionalität
            # Cayley Delete API ist komplex, vereinfachte Implementation
            logging.warning("Delete Node noch nicht vollständig implementiert")
            return True
            
        except Exception as e:
            logging.error(f"Cayley Delete Node fehlgeschlagen: {e}")
            return False
    
    def run_gizmo_query(self, query_string: str) -> List[Dict]:
        """Führe custom Gizmo Query aus"""
        try:
            query = {
                "query": query_string,
                "lang": "gizmo"
            }
            
            response = self.session.post(
                self.endpoints['query'],
                json=query,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Gizmo Query fehlgeschlagen: {response.text}")
                return []
                
        except Exception as e:
            logging.error(f"Gizmo Query ausführen fehlgeschlagen: {e}")
            return []
    
    def run_graphql_query(self, query_string: str, variables: Dict = None) -> Dict:
        """Führe GraphQL Query aus"""
        try:
            payload = {
                "query": query_string,
                "lang": "graphql"
            }
            
            if variables:
                payload["variables"] = variables
            
            response = self.session.post(
                self.endpoints['query'],
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"GraphQL Query fehlgeschlagen: {response.text}")
                return {}
                
        except Exception as e:
            logging.error(f"GraphQL Query ausführen fehlgeschlagen: {e}")
            return {}
    
    def get_graph_stats(self) -> Dict:
        """Graph Statistiken abrufen"""
        try:
            # Anzahl Nodes
            node_query = {
                "query": 'g.V().Count()',
                "lang": "gizmo"
            }
            
            response = self.session.post(
                self.endpoints['query'],
                json=node_query,
                headers={'Content-Type': 'application/json'}
            )
            
            stats = {
                'nodes': 0,
                'edges': 0,
                'backend': 'Cayley'
            }
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    stats['nodes'] = result[0].get('id', 0)
            
            # Edges zählen ist komplexer in Cayley
            # Vereinfachte Implementation
            stats['edges'] = -1  # Nicht implementiert
            
            return stats
            
        except Exception as e:
            logging.error(f"Cayley Stats abrufen fehlgeschlagen: {e}")
            return {}
    
    def _write_quads(self, quads: List[Dict]) -> bool:
        """Schreibe Quads an Cayley"""
        try:
            # Quads in N-Quads Format konvertieren
            nquads_lines = []
            for quad in quads:
                nquad = self._quad_to_nquad(quad)
                if nquad:
                    nquads_lines.append(nquad)
            
            if not nquads_lines:
                return False
            
            nquads_content = '\n'.join(nquads_lines)
            
            response = self.session.post(
                self.endpoints['write'],
                data=nquads_content,
                headers={'Content-Type': 'application/n-quads'}
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logging.error(f"Cayley Write Quads fehlgeschlagen: {e}")
            return False
    
    def _quad_to_nquad(self, quad: Dict) -> str:
        """Konvertiere Quad Dict zu N-Quad String"""
        try:
            subject = f"<{quad['subject']}>"
            predicate = f"<{quad['predicate']}>"
            
            # Object kann IRI oder Literal sein
            obj = quad['object']
            if obj.startswith('urn:') or obj.startswith('http'):
                object_str = f"<{obj}>"
            else:
                # Literal
                object_str = f'"{obj}"'
            
            # Label (optional)
            label_str = f" <{quad['label']}>" if quad.get('label') else ""
            
            return f"{subject} {predicate} {object_str}{label_str} ."
            
        except Exception as e:
            logging.error(f"Quad zu N-Quad Konvertierung fehlgeschlagen: {e}")
            return None
    
    def _serialize_value(self, value) -> str:
        """Serialisiere Python Werte für RDF"""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        elif isinstance(value, bool):
            return str(value).lower()
        else:
            return str(value)
    
    def _parse_node_result(self, result: List[Dict], node_id: str) -> Optional[Dict]:
        """Parse Cayley Query Result für einzelnen Node"""
        try:
            if not result:
                return None
            
            # Vereinfachtes Parsing - abhängig von Cayley Response Format
            node_data = {
                'id': node_id,
                'type': 'Unknown',
                'properties': {},
                'created_at': None
            }
            
            # TODO: Implementiere vollständiges Result Parsing
            # basierend auf tatsächlichem Cayley Response Format
            
            return node_data
            
        except Exception as e:
            logging.error(f"Node Result Parsing fehlgeschlagen: {e}")
            return None
    
    def _parse_nodes_result(self, result: List[Dict]) -> List[Dict]:
        """Parse Cayley Query Result für mehrere Nodes"""
        try:
            nodes = []
            
            for item in result:
                # Vereinfachtes Parsing
                node = {
                    'id': item.get('id', ''),
                    'type': 'Unknown',
                    'properties': {}
                }
                nodes.append(node)
            
            return nodes
            
        except Exception as e:
            logging.error(f"Nodes Result Parsing fehlgeschlagen: {e}")
            return []
    
    def _parse_relationships_result(self, result: List[Dict], node_id: str, direction: str) -> List[Dict]:
        """Parse Relationships Result"""
        try:
            relationships = []
            
            for item in result:
                rel = {
                    'edge_id': '',
                    'edge_type': 'unknown',
                    'edge_properties': {},
                    'target_id': item.get('id', ''),
                    'target_type': 'Unknown',
                    'target_properties': {}
                }
                relationships.append(rel)
            
            return relationships
            
        except Exception as e:
            logging.error(f"Relationships Result Parsing fehlgeschlagen: {e}")
            return []


def get_backend_class():
    """Factory-Funktion für Cayley Backend"""
    return CayleyGraphBackend

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_cayley"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...SVVf8nM="  # Gekuerzt fuer Sicherheit
module_organization_key = "2c50222bb6216bb1f80f73f2d26f42da04f0e92d377ef9bf07058c261e9cf38d"
module_file_key = "bc77233d7250215470884460175b6848236ed585ed9ba959357b538e0703378b"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
