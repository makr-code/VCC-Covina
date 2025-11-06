"""
Multi-Hop Reasoner for Legal Knowledge Graph

Features:
- BFS/DFS up to max_hops
- find_path(source, target, max_hops)
- find_authority_for_concept(concept_id)
- explain_relationship(a, b)
- Simple LRU caching for query results (size=1000)
- Query templates loaded from YAML (ingestion/queries/graph_queries.yaml)

Abstraction:
- Works with a "graph" wrapper exposing run_cypher(query, params) and neighbors(node_id)
- Default wrapper uses UDS3RelationsCore if available, else neo4j driver when configured, else raises

Notes:
- This module avoids heavy coupling to DB; can be fully mocked in tests
- Caching layer is per-process in-memory
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import os
import yaml

try:
    from uds3.core.relations import UDS3RelationsCore  # type: ignore
except Exception:
    UDS3RelationsCore = None  # optional


# ---------- Query Templates ----------

_DEFAULT_QUERIES_PATH = os.path.join(os.path.dirname(__file__), "..", "queries", "graph_queries.yaml")


def load_query_templates(path: Optional[str] = None) -> Dict[str, str]:
    p = path or _DEFAULT_QUERIES_PATH
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Expect mapping: { name: cypher }
    return {str(k): str(v) for k, v in data.items()}


# ---------- Graph Wrapper ----------

@dataclass
class GraphBackend:
    wrapper: Any

    def run_cypher(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        if hasattr(self.wrapper, "neo4j_session"):
            with self.wrapper.neo4j_session() as s:
                res = s.run(query, params)
                return [r.data() for r in res]
        elif hasattr(self.wrapper, "run"):
            res = self.wrapper.run(query, params)
            return [r.data() for r in res]
        else:
            raise RuntimeError("Unsupported graph wrapper: missing run capability")

    def neighbors(self, node_id: str, max_degree: int = 100) -> List[str]:
        query = (
            "MATCH (n {id: $id})-[*1..1]-(m) RETURN DISTINCT m.id AS id LIMIT $lim"
        )
        rows = self.run_cypher(query, {"id": node_id, "lim": max_degree})
        return [r.get("id") for r in rows if r.get("id")]


# ---------- Reasoner ----------

class MultiHopReasoner:
    def __init__(self, graph: GraphBackend, templates: Optional[Dict[str, str]] = None):
        self.graph = graph
        self.templates = templates or load_query_templates()

    @staticmethod
    def _bfs(start: str, goal: str, neighbor_fn, max_hops: int = 5) -> Optional[List[str]]:
        if start == goal:
            return [start]
        from collections import deque
        q = deque([(start, [start])])
        visited: Set[str] = {start}
        while q:
            node, path = q.popleft()
            if len(path) - 1 >= max_hops:
                continue
            for nb in neighbor_fn(node):
                if nb in visited:
                    continue
                if nb == goal:
                    return path + [nb]
                visited.add(nb)
                q.append((nb, path + [nb]))
        return None

    @staticmethod
    def _dfs(start: str, goal: str, neighbor_fn, max_hops: int = 5) -> Optional[List[str]]:
        if start == goal:
            return [start]
        visited: Set[str] = set()
        def dfs_rec(node: str, path: List[str]) -> Optional[List[str]]:
            if node == goal:
                return path
            if len(path) - 1 >= max_hops:
                return None
            visited.add(node)
            for nb in neighbor_fn(node):
                if nb not in visited:
                    result = dfs_rec(nb, path + [nb])
                    if result:
                        return result
            return None
        return dfs_rec(start, [start])

    @lru_cache(maxsize=1000)
    def find_path(self, source_id: str, target_id: str, max_hops: int = 5, strategy: str = "bfs") -> Optional[List[str]]:
        """Find path from source to target using BFS or DFS.
        
        Args:
            source_id: Starting node ID
            target_id: Target node ID
            max_hops: Maximum hops (default 5)
            strategy: "bfs" or "dfs" (default "bfs")
        
        Returns:
            List of node IDs forming the path, or None if not found
        """
        if strategy == "dfs":
            return self._dfs(source_id, target_id, self.graph.neighbors, max_hops=max_hops)
        return self._bfs(source_id, target_id, self.graph.neighbors, max_hops=max_hops)

    @lru_cache(maxsize=1000)
    def find_authority_for_concept(self, concept_id: str) -> Optional[str]:
        # Uses template: authority_for_concept
        cypher = self.templates.get("authority_for_concept")
        if not cypher:
            # Fallback: local neighborhood search for Authority nodes
            query = (
                "MATCH (c:LegalConcept {id: $id})-[:REFERENCES_AUTHORITY]->(a:Authority) RETURN a.id AS id LIMIT 1"
            )
        else:
            query = cypher
        rows = self.graph.run_cypher(query, {"id": concept_id})
        return rows[0]["id"] if rows else None

    def explain_relationship(self, a_id: str, b_id: str, max_hops: int = 5) -> Dict[str, Any]:
        """Explain the relationship between two nodes.
        
        Returns:
            {
                "path_found": bool,
                "path": List[str] or None,
                "hops": int or None,
                "explanation": str
            }
        """
        # Use our own BFS for consistent results
        path = self.find_path(a_id, b_id, max_hops=max_hops)
        if path:
            return {
                "path_found": True,
                "path": path,
                "hops": len(path) - 1,
                "explanation": f"{a_id} → {b_id} via {len(path) - 1} hops: {' → '.join(path)}"
            }
        
        return {
            "path_found": False,
            "path": None,
            "hops": None,
            "explanation": f"No path found between {a_id} and {b_id} within {max_hops} hops"
        }


# ---------- Factory ----------

def create_default_reasoner() -> MultiHopReasoner:
    # Try to create a UDS3 wrapper if available
    if UDS3RelationsCore is None:
        raise RuntimeError("UDS3RelationsCore not available. Provide a custom graph wrapper.")
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "neo4j")
    wrapper = UDS3RelationsCore(neo4j_uri=neo4j_uri, neo4j_auth=(neo4j_user, neo4j_password))
    graph = GraphBackend(wrapper)
    templates = load_query_templates()
    return MultiHopReasoner(graph, templates)
