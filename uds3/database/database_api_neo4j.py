#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight Neo4j adapter for the Veritas database layer.
This adapter follows the project's `GraphDatabaseBackend` abstract base and
uses the official `neo4j` driver when available. It aims to be small and
easy to read and maintain.

Usage:
    from database.database_api_neo4j import Neo4jGraphBackend
    backend = Neo4jGraphBackend({'uri': 'neo4j://localhost:7687', 'user': 'neo4j', 'password': 'pw'})
    backend.connect()
    backend.execute_query('MATCH (n) RETURN count(n) as c')

This file intentionally implements a subset of features needed by the
higher-level manager: connect/disconnect, is_available, get_backend_type,
execute_query and simple node/relationship helpers.
"""
from __future__ import annotations

import logging
import socket
from typing import Dict, Any, List, Optional

from database.database_api_base import GraphDatabaseBackend

logger = logging.getLogger(__name__)

# Python 3.13 auf Windows entfernt socket.EAI_ADDRFAMILY. Der offizielle neo4j-Treiber
# referenziert die Konstante jedoch weiterhin beim Import. Wir stellen sie daher
# defensiv bereit, falls sie fehlt.
if not hasattr(socket, "EAI_ADDRFAMILY"):
    try:
        fallback_value = getattr(socket, "EAI_FAMILY", getattr(socket, "EAI_FAIL", -9))
    except Exception:
        fallback_value = -9
    setattr(socket, "EAI_ADDRFAMILY", fallback_value)
    logger.debug("Injected socket.EAI_ADDRFAMILY fallback=%s", fallback_value)

# Try to import official neo4j driver. If missing, surface a clear error on connect().
NEO4J_AVAILABLE = False
try:
    from neo4j import GraphDatabase, basic_auth
    from neo4j import Driver, Session, Result
    NEO4J_AVAILABLE = True
except Exception as _e:
    NEO4J_AVAILABLE = False
    _NEO4J_IMPORT_ERROR = _e


class Neo4jGraphBackend(GraphDatabaseBackend):
    """Simple Neo4j adapter using the official neo4j driver.

    Config keys accepted:
    - uri (str): bolt://neo4j:7687 or neo4j://host:port
    - user (str): username
    - password (str): password
    - encrypted (bool): whether to use encrypted connection (driver handles it)
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        cfg = config or {}
        settings = cfg.get('settings') or {}

        host = cfg.get('host') or settings.get('host')
        port = cfg.get('port') or settings.get('port')
        if host and port:
            fallback_uri = f"neo4j://{host}:{port}"
        else:
            fallback_uri = 'neo4j://localhost:7687'

        explicit_uri = cfg.get('uri') or settings.get('uri')
        if explicit_uri and not (host and port and ('127.0.0.1' in explicit_uri or 'localhost' in explicit_uri)):
            self.uri = explicit_uri
        else:
            self.uri = fallback_uri
        self.user = (
            cfg.get('user')
            or cfg.get('username')
            or settings.get('user')
            or settings.get('username')
            or 'neo4j'
        )
        self.password = cfg.get('password') or settings.get('password') or ''
        self.database_name = cfg.get('database') or settings.get('db_name')
        self._driver: Optional["Driver"] = None
        self._is_connected = False

    def connect(self) -> bool:
        if not NEO4J_AVAILABLE:
            logger.warning("Neo4j driver nicht verfügbar: %s", getattr(_NEO4J_IMPORT_ERROR, 'args', _NEO4J_IMPORT_ERROR))
            logger.info("💡 Installation: pip install neo4j")
            self._is_connected = False
            return False
        try:
            # Create driver
            self._driver = GraphDatabase.driver(self.uri, auth=basic_auth(self.user, self.password))
            # test simple session
            session_kwargs = {}
            if self.database_name:
                session_kwargs['database'] = self.database_name
            with self._driver.session(**session_kwargs) as session:
                # run a trivial query
                res = session.run('RETURN 1 as ok')
                _ = list(res)
            self._is_connected = True
            logger.info('Neo4j connected %s', self.uri)
            return True
        except Exception as exc:
            logger.exception('Failed to connect to Neo4j: %s', exc)
            self._driver = None
            self._is_connected = False
            return False

    def disconnect(self) -> bool:
        try:
            if self._driver:
                self._driver.close()
            self._driver = None
            self._is_connected = False
            logger.info('Neo4j disconnected')
            return True
        except Exception:
            logger.exception('Error while disconnecting Neo4j')
            return False

    def is_available(self) -> bool:
        return bool(self._is_connected and self._driver is not None)

    def get_backend_type(self) -> str:
        return 'neo4j'

    def execute_query(self, query: str, params: Dict = None) -> List[Dict[str, Any]]:
        """Execute a cypher query and return list of dict rows.

        Non-select operations will return an empty list or the summary depending
        on what the driver returns. We try to normalize to a list of dicts.
        """
        if not self._driver:
            logger.debug('Neo4j driver not connected - skipping query in development mode')
            return []  # Graceful fallback für Entwicklungsumgebung
        params = params or {}
        try:
            session_kwargs = {}
            if self.database_name:
                session_kwargs['database'] = self.database_name
            with self._driver.session(**session_kwargs) as session:
                result = session.run(query, params)
                records = []
                for rec in result:
                    try:
                        records.append(dict(rec.items()))
                    except Exception:
                        # Fallback: convert values manually
                        row = {k: getattr(v, 'value', v) for k, v in rec.items()}
                        records.append(row)
                return records
        except Exception as exc:
            logger.exception('Neo4j query failed: %s', exc)
            raise

    # Simple convenience helpers
    def create_node(self, label: str, properties: Dict[str, Any], merge_key: str = None) -> Optional[str]:
        """Create or merge a node with the given label and properties.
        
        Args:
            label: Node label (e.g., "Document")
            properties: Node properties
            merge_key: If specified, use MERGE instead of CREATE on this property
                      (e.g., "id" will MERGE on the 'id' property to avoid duplicates)
        
        Returns:
            Internal node ID as string
        """
        if merge_key and merge_key in properties:
            # Use MERGE to avoid duplicates
            match_props = {merge_key: properties[merge_key]}
            set_props = {k: v for k, v in properties.items() if k != merge_key}
            return self.merge_node(label, match_props, set_props if set_props else None)
        else:
            # Standard CREATE
            props = ', '.join([f'{k}: ${k}' for k in properties.keys()])
            cypher = f'CREATE (n:{label} {{ {props} }}) RETURN elementId(n) as id'
            rows = self.execute_query(cypher, properties)
            if rows and 'id' in rows[0]:
                return str(rows[0]['id'])
            return None

    def find_node_by_id(self, node_id: Any) -> Optional[Dict[str, Any]]:
        cypher = 'MATCH (n) WHERE elementId(n) = $id RETURN n, elementId(n) as id'
        rows = self.execute_query(cypher, {'id': str(node_id)})
        if not rows:
            return None
        row = rows[0]
        node = row.get('n')
        if hasattr(node, 'items'):
            try:
                return dict(node.items())
            except Exception:
                return {k: getattr(v, 'value', v) for k, v in node.items()}
        # Fallback when driver returned plain map
        return node

    def merge_node(self, label: str, match_props: Dict[str, Any], set_props: Dict[str, Any] = None) -> Optional[str]:
        """Merge a node by match_props and optionally set additional properties.

        Returns the internal id as string when successful.
        """
        params = {}
        # prepare match clause
        match_items = []
        for k, v in match_props.items():
            params[f'm_{k}'] = v
            match_items.append(f"{k}: $m_{k}")
        match_map = ', '.join(match_items)
        cypher = f"MERGE (n:{label} {{ {match_map} }})"
        # optional SET
        if set_props:
            set_items = []
            for k, v in set_props.items():
                params[f's_{k}'] = v
                set_items.append(f"n.{k} = $s_{k}")
            cypher += " SET " + ', '.join(set_items)
        cypher += " RETURN elementId(n) as id"
        rows = self.execute_query(cypher, params)
        if rows and 'id' in rows[0]:
            return str(rows[0]['id'])
        return None

    def find_nodes_by_label_and_props(self, label: str, props: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find nodes by label and equality on provided properties."""
        params = {}
        conds = []
        for k, v in props.items():
            params[k] = v
            conds.append(f"n.{k} = ${k}")
        where = (' WHERE ' + ' AND '.join(conds)) if conds else ''
        cypher = f"MATCH (n:{label}){where} RETURN n, elementId(n) as id"
        rows = self.execute_query(cypher, params)
        out = []
        for r in rows:
            node = r.get('n')
            if hasattr(node, 'items'):
                try:
                    data = dict(node.items())
                except Exception:
                    data = {k: getattr(v, 'value', v) for k, v in node.items()}
            else:
                data = node
            data['_id'] = r.get('id')
            out.append(data)
        return out

    def update_node_by_id(self, node_id: Any, props: Dict[str, Any]) -> bool:
        """Update properties for a node by its internal id."""
        if not props:
            return False
        params = {f'p_{k}': v for k, v in props.items()}
        set_items = [f"n.{k} = $p_{k}" for k in props.keys()]
        cypher = f"MATCH (n) WHERE elementId(n) = $id SET {', '.join(set_items)} RETURN elementId(n) as id"
        params['id'] = str(node_id)
        rows = self.execute_query(cypher, params)
        return bool(rows)

    def delete_node_by_id(self, node_id: Any) -> bool:
        """Delete a node by internal id. If relationships exist, uses DETACH DELETE."""
        try:
            cypher = 'MATCH (n) WHERE elementId(n) = $id DETACH DELETE n'
            self.execute_query(cypher, {'id': str(node_id)})
            return True
        except Exception:
            return False

    def delete_node(self, identifier: str) -> bool:
        """
        Delete a node by identifier. Identifier can be:
        - Internal Neo4j node ID (numeric string)
        - Document ID (string with 'id' property)
        
        Uses DETACH DELETE to also remove relationships.
        Compatible with saga_crud compensation.
        """
        try:
            # Try as internal ID first (elementId or legacy numeric)
            try:
                # First try as elementId (string)
                cypher = 'MATCH (n) WHERE elementId(n) = $id DETACH DELETE n'
                self.execute_query(cypher, {'id': identifier})
                return True
            except Exception:
                # If elementId fails, try as property-based identifier
                # Assume it's a document_id stored in 'id' property
                cypher = 'MATCH (n {id: $identifier}) DETACH DELETE n'
                self.execute_query(cypher, {'identifier': identifier})
                return True
        except Exception as exc:
            logger.exception(f'Neo4j delete_node failed for {identifier}: {exc}')
            return False

    # Relationship helpers
    def create_relationship(self, from_id: Any, to_id: Any, rel_type: str, properties: Dict[str, Any] = None) -> Optional[str]:
        """Create a relationship between two nodes identified by internal ids."""
        props = properties or {}
        params = {f'p_{k}': v for k, v in props.items()}
        params['from_id'] = str(from_id)
        params['to_id'] = str(to_id)
        props_cypher = ''
        if props:
            items = [f'{k}: $p_{k}' for k in props.keys()]
            props_cypher = ' {' + ', '.join(items) + '}'
        cypher = f"MATCH (a), (b) WHERE elementId(a) = $from_id AND elementId(b) = $to_id CREATE (a)-[r:{rel_type}{props_cypher}]->(b) RETURN elementId(r) as id"
        rows = self.execute_query(cypher, params)
        if rows and 'id' in rows[0]:
            return str(rows[0]['id'])
        return None

    def delete_relationship(self, rel_id: Any) -> bool:
        """Delete a relationship by internal id."""
        try:
            cypher = 'MATCH ()-[r]-() WHERE elementId(r) = $id DELETE r'
            self.execute_query(cypher, {'id': str(rel_id)})
            return True
        except Exception:
            return False

    # The GraphDatabaseBackend abstract methods expected by the base
    def create_edge(self, from_id: str, to_id: str, edge_type: str, properties: Dict = None) -> str:
        """Wrapper to create an edge using internal relationship helper.
        Returns the created relationship id as string.
        """
        rel_id = self.create_relationship(from_id, to_id, edge_type, properties or {})
        return rel_id

    def find_nodes(self, node_type: str, filters: Dict = None) -> List[Dict]:
        """Wrapper around find_nodes_by_label_and_props to match base signature."""
        return self.find_nodes_by_label_and_props(node_type, filters or {})

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Wrapper around find_node_by_id to match base signature."""
        return self.find_node_by_id(node_id)

    def get_relationships(self, node_id: str, direction: str = "both") -> List[Dict]:
        """Return relationships for a node. Direction is best-effort (in/out/both)."""
        try:
            # direction handling is simple: both / out / in
            if direction not in ('both', 'in', 'out'):
                direction = 'both'
            if direction == 'both':
                cypher = 'MATCH (n)-[r]-() WHERE elementId(n) = $id RETURN r, elementId(r) as id'
            elif direction == 'out':
                cypher = 'MATCH (n)-[r]->() WHERE elementId(n) = $id RETURN r, elementId(r) as id'
            else:
                cypher = 'MATCH (n)<-[r]-() WHERE elementId(n) = $id RETURN r, elementId(r) as id'
            rows = self.execute_query(cypher, {'id': str(node_id)})
            out = []
            for r in rows:
                rel = r.get('r')
                try:
                    props = dict(rel.items())
                except Exception:
                    props = {k: getattr(v, 'value', v) for k, v in rel.items()}
                props['_id'] = r.get('id')
                out.append(props)
            return out
        except Exception:
            return []


def get_backend_class():
    return Neo4jGraphBackend