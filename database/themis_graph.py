"""
Themis Graph Backend

Implements Neo4j/Cypher-like graph operations on top of Themis HTTP API.

Author: VCC Covina Team
Created: 2025-11-07
Version: 0.1.0
"""
from __future__ import annotations

import json
import uuid
import re
from typing import Optional, List, Dict, Any

from .themis_adapter import ThemisAdapter
from .themis_exceptions import (
    create_graph_error,
    ThemisValidationError,
)


class ThemisGraphBackend:
    """Graph Backend for Themis (Neo4j → Themis Graph Traversal + Dijkstra)

    Provides UDS3-compatible operations:
    - execute_query(cypher, params=None): Translate simple Cypher to AQL and execute
    - create_node(label, properties): Create node as entity
    - create_relationship(from_node, to_node, rel_type, properties=None): Create edge as entity
    - traverse(start_vertex, max_depth=3, direction="OUTBOUND"): BFS traversal
    - shortest_path(start, target): Dijkstra (fallback to iterative BFS)
    """

    def __init__(self, adapter: ThemisAdapter):
        self.adapter = adapter
        self.client = adapter  # use adapter's retry-enabled methods
        self.logger = adapter.logger

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    async def execute_query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute Cypher-like query by translating to AQL.

        Supports a minimal subset:
            MATCH (a:Label)-[r:TYPE]->(b) WHERE ... RETURN b
        """
        aql = self._translate_cypher_to_aql(cypher, params)
        try:
            response = await self.client.post("/query/aql", json={"query": aql, "allow_full_scan": True})
            entities = [json.loads(e) for e in response.json().get("entities", [])]
            return entities
        except ThemisValidationError as e:
            raise create_graph_error(str(e), query=aql)

    async def create_node(self, label: str, properties: Dict[str, Any]) -> str:
        """Create graph node as entity with label metadata."""
        pk = properties.get("_key") or properties.get("id") or str(uuid.uuid4())
        key = f"{label}:{pk}"
        payload = {**properties, "_label": label}
        await self.client.put(f"/entities/{key}", json={"key": key, "blob": json.dumps(payload)})
        return key

    async def create_relationship(
        self,
        from_node: str,
        to_node: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create edge as entity in a generic 'edges' collection."""
        edge_id = f"edge_{uuid.uuid4()}"
        edge_key = f"edges:{edge_id}"
        edge_doc = {
            "id": edge_id,
            "_from": from_node,
            "_to": to_node,
            "type": rel_type,
            **(properties or {}),
        }
        await self.client.put(f"/entities/{edge_key}", json={"key": edge_key, "blob": json.dumps(edge_doc)})
        return edge_key

    async def traverse(self, start_vertex: str, max_depth: int = 3, direction: str = "OUTBOUND") -> List[str]:
        """Breadth-first traversal returning visited node keys."""
        payload = {"start_vertex": start_vertex, "max_depth": max_depth}
        # Note: direction currently unused until API supports it
        response = await self.client.post("/graph/traverse", json=payload)
        data = response.json()
        return data.get("visited", [])

    async def shortest_path(self, start: str, target: str) -> Dict[str, Any]:
        """Find shortest path. Fallback to iterative BFS up to depth 10."""
        # TODO: Switch to native Dijkstra endpoint once exposed in HTTP API
        for depth in range(1, 11):
            visited = await self.traverse(start, max_depth=depth)
            if target in visited:
                return {"path": self._approximate_path(start, target, visited), "distance": depth}
        return {"path": [], "distance": -1}

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _translate_cypher_to_aql(self, cypher: str, params: Optional[Dict[str, Any]]) -> str:
        """Translate a tiny subset of Cypher to AQL graph traversal."""
        # Pattern: MATCH (a:LabelA)-[r:TYPE]->(b:LabelB) WHERE <expr> RETURN b
        m = re.search(r"MATCH\s*\((\w+):?(\w*)\)-\[(\w+):(\w+)\]->\((\w+):?(\w*)\)", cypher, re.IGNORECASE)
        if not m:
            raise ThemisValidationError(f"Unsupported Cypher: {cypher}", status_code=400)
        var_a, label_a, var_r, rel_type, var_b, label_b = m.groups()

        # Starting point heuristic: If WHERE contains a.id='...' use it; otherwise wildcard start
        start_vertex = f"{label_a}:*" if label_a else "*"

        aql_lines: List[str] = []
        aql_lines.append(f"FOR {var_b}, {var_r}, p IN 1..1 OUTBOUND '{start_vertex}' {rel_type}")

        where_m = re.search(r"WHERE\s+(.+?)(?:\s+RETURN|$)", cypher, re.IGNORECASE)
        if where_m:
            where_clause = where_m.group(1)
            aql_lines.append(f"FILTER {where_clause}")

        ret_m = re.search(r"RETURN\s+(.+)$", cypher, re.IGNORECASE)
        if ret_m:
            aql_lines.append(f"RETURN {ret_m.group(1)}")
        else:
            aql_lines.append(f"RETURN {var_b}")

        return "\n".join(aql_lines)

    def _approximate_path(self, start: str, target: str, visited: List[str]) -> List[str]:
        # Placeholder: returns [start, ..., target] without actual edges
        if start in visited and target in visited:
            return [start, target]
        return [target]

__all__ = ["ThemisGraphBackend"]
