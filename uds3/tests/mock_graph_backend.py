#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
In-Memory Mock Graph Backend für Tests

Implementiert GraphDatabaseBackend für Tests ohne echte Neo4j-Instanz.
"""

import logging
from typing import Dict, List, Any, Optional
from database.database_api_base import GraphDatabaseBackend

logger = logging.getLogger(__name__)


class InMemoryGraphBackend(GraphDatabaseBackend):
    """In-Memory Graph Backend für Tests"""

    def __init__(self, **config):
        super().__init__()
        self.config = config
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.relationships: List[Dict[str, Any]] = []
        self._connected = False
        logger.info("InMemoryGraphBackend initialized")

    def connect(self) -> bool:
        """Verbindung simulieren"""
        self._connected = True
        logger.info("InMemoryGraphBackend connected (mock)")
        return True

    def disconnect(self) -> bool:
        """Trennung simulieren"""
        self._connected = False
        logger.info("InMemoryGraphBackend disconnected (mock)")
        return True

    def is_connected(self) -> bool:
        """Verbindungsstatus prüfen"""
        return self._connected

    def health_check(self) -> Dict[str, Any]:
        """Health Check"""
        return {
            "status": "healthy" if self._connected else "disconnected",
            "backend_type": "in_memory_graph",
            "nodes_count": len(self.nodes),
            "relationships_count": len(self.relationships),
        }

    # ============================================================
    # Node Operations
    # ============================================================

    def create_node(
        self,
        node_type: str,
        properties: Dict[str, Any],
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Erstellt einen Node"""
        if not node_id:
            node_id = properties.get("id") or f"{node_type}_{len(self.nodes)}"

        node_data = {
            "id": node_id,
            "type": node_type,
            "properties": properties.copy(),
        }

        self.nodes[node_id] = node_data
        logger.debug(f"Created node: {node_type} with id {node_id}")

        return {"success": True, "node_id": node_id, "graph_id": node_id}

    def add_node(
        self, node_id: str, node_type: str, properties: Dict[str, Any]
    ) -> bool:
        """Fügt einen Node hinzu (Alias für create_node)"""
        result = self.create_node(node_type, properties, node_id)
        return result.get("success", False)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Holt einen Node"""
        return self.nodes.get(node_id)

    def query_nodes(
        self,
        node_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query Nodes mit Filtern"""
        results = []

        for node_id, node_data in self.nodes.items():
            # Filter by type
            if node_type and node_data.get("type") != node_type:
                continue

            # Filter by properties
            if filters:
                props = node_data.get("properties", {})
                match = True
                for key, value in filters.items():
                    if props.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            results.append(node_data)

            if len(results) >= limit:
                break

        return results

    def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """Update Node Properties"""
        if node_id not in self.nodes:
            return False

        self.nodes[node_id]["properties"].update(properties)
        return True

    def delete_node(self, node_id: str) -> bool:
        """Löscht einen Node"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            # Remove relationships
            self.relationships = [
                rel
                for rel in self.relationships
                if rel["source"] != node_id and rel["target"] != node_id
            ]
            return True
        return False

    # ============================================================
    # Relationship Operations
    # ============================================================

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Erstellt eine Relationship"""
        rel_data = {
            "source": source_id,
            "target": target_id,
            "type": relationship_type,
            "properties": properties or {},
        }

        self.relationships.append(rel_data)
        logger.debug(
            f"Created relationship: {source_id} -[{relationship_type}]-> {target_id}"
        )

        return {
            "success": True,
            "relationship_id": f"{source_id}_{relationship_type}_{target_id}",
        }

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Fügt eine Relationship hinzu (Alias)"""
        result = self.create_relationship(
            source_id, target_id, relationship_type, properties
        )
        return result.get("success", False)

    def query_relationships(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query Relationships"""
        results = []

        for rel in self.relationships:
            if source_id and rel["source"] != source_id:
                continue
            if target_id and rel["target"] != target_id:
                continue
            if relationship_type and rel["type"] != relationship_type:
                continue

            results.append(rel)

        return results

    def delete_relationship(
        self, source_id: str, target_id: str, relationship_type: str
    ) -> bool:
        """Löscht eine Relationship"""
        original_len = len(self.relationships)
        self.relationships = [
            rel
            for rel in self.relationships
            if not (
                rel["source"] == source_id
                and rel["target"] == target_id
                and rel["type"] == relationship_type
            )
        ]
        return len(self.relationships) < original_len

    # ============================================================
    # Batch Operations
    # ============================================================

    def batch_create_nodes(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch Node Creation"""
        created = []
        for node_spec in nodes:
            result = self.create_node(
                node_spec.get("type", "Node"),
                node_spec.get("properties", {}),
                node_spec.get("id"),
            )
            if result.get("success"):
                created.append(result["node_id"])

        return {"success": True, "created_count": len(created), "node_ids": created}

    def batch_create_relationships(
        self, relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Batch Relationship Creation"""
        created = 0
        for rel_spec in relationships:
            result = self.create_relationship(
                rel_spec["source"],
                rel_spec["target"],
                rel_spec["type"],
                rel_spec.get("properties"),
            )
            if result.get("success"):
                created += 1

        return {"success": True, "created_count": created}

    # ============================================================
    # Query Operations
    # ============================================================

    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> Any:
        """Cypher Query ausführen (Mock - nur Basis-Support)"""
        # Für Tests: einfache Simulation
        logger.warning(f"Mock execute_query called with: {query[:100]}")
        return []

    def query(
        self, cypher: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """Alias für execute_query"""
        return self.execute_query(cypher, parameters)

    # ============================================================
    # Statistics
    # ============================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Backend Statistiken"""
        return {
            "nodes_count": len(self.nodes),
            "relationships_count": len(self.relationships),
            "node_types": list(set(n["type"] for n in self.nodes.values())),
            "relationship_types": list(set(r["type"] for r in self.relationships)),
        }
