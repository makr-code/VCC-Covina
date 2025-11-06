"""
Process Analytics - Frequent Patterns, Transitions, Bottlenecks

Computes mining metrics from the process graph (Neo4j):
- Frequent steps (by usage across processes)
- Frequent transitions (by NEXT relation count)
- Bottlenecks (by duration, degree centrality)

Optionally persists metrics back into the graph as properties:
- Step.usage_count
- Step.bottleneck_score
- NEXT.freq
- NEXT.last_computed_at
"""
from __future__ import annotations
from datetime import datetime
from typing import Any


class DataMiningService:
    """Mining/analytics on the process graph using Neo4j."""

    def __init__(self, graph_adapter):
        self.graph = graph_adapter

    # ---------------------------------------------------------------------
    # Frequent Steps
    # ---------------------------------------------------------------------
    def frequent_steps(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Count how often each Step appears across all Processes.
        Returns list sorted by count desc.
        """
        cypher = """
        MATCH (p:Process)-[:HAS_STEP]->(s:Step)
        RETURN s.id AS step_id,
               s.key AS key,
               s.name AS name,
               s.type AS type,
               count(DISTINCT p) AS processes,
               count(*) AS usage
        ORDER BY usage DESC
        LIMIT $limit
        """
        rows = self.graph.execute_query(cypher, {"limit": limit})
        return [
            {
                "step_id": r["step_id"],
                "key": r.get("key"),
                "name": r.get("name"),
                "type": r.get("type"),
                "processes": r.get("processes", 0),
                "usage": r.get("usage", 0),
            }
            for r in rows
        ]

    # ---------------------------------------------------------------------
    # Frequent Transitions
    # ---------------------------------------------------------------------
    def frequent_transitions(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Count how often each NEXT transition occurs across all Processes.
        """
        cypher = """
        MATCH (p:Process)-[:HAS_STEP]->(s1:Step)-[r:NEXT]->(s2:Step)<-[:HAS_STEP]-(p)
        RETURN s1.id AS from_id,
               s1.name AS from_name,
               s2.id AS to_id,
               s2.name AS to_name,
               count(*) AS freq
        ORDER BY freq DESC
        LIMIT $limit
        """
        rows = self.graph.execute_query(cypher, {"limit": limit})
        return [
            {
                "from_id": r["from_id"],
                "from_name": r.get("from_name"),
                "to_id": r["to_id"],
                "to_name": r.get("to_name"),
                "freq": r.get("freq", 0),
            }
            for r in rows
        ]

    # ---------------------------------------------------------------------
    # Bottlenecks (heuristic)
    # ---------------------------------------------------------------------
    def bottlenecks(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Identify bottleneck candidates using a simple heuristic:
        score = normalized(duration_days) * 0.6 + normalized(in_degree*out_degree) * 0.4
        """
        cypher = """
        MATCH (s:Step)
        OPTIONAL MATCH (s)<-[:NEXT]-(:Step)  WITH s, count(*) AS in_deg
        OPTIONAL MATCH (s)-[:NEXT]->(:Step)  WITH s, in_deg, count(*) AS out_deg
        WITH s,
             coalesce(s.duration_days, 0) AS duration,
             in_deg AS indegree,
             out_deg AS outdegree,
             (in_deg * out_deg) AS connectivity
        WITH s, duration, indegree, outdegree, connectivity,
             max(duration) OVER () AS max_dur,
             max(connectivity) OVER () AS max_conn
        WITH s,
             (CASE WHEN max_dur > 0 THEN toFloat(duration)/toFloat(max_dur) ELSE 0.0 END) AS ndur,
             (CASE WHEN max_conn > 0 THEN toFloat(connectivity)/toFloat(max_conn) ELSE 0.0 END) AS nconn,
             indegree, outdegree, duration
        WITH s, ndur, nconn, indegree, outdegree, duration,
             (ndur*0.6 + nconn*0.4) AS score
        RETURN s.id AS step_id,
               s.name AS name,
               s.key AS key,
               duration AS duration_days,
               indegree,
               outdegree,
               score
        ORDER BY score DESC
        LIMIT $limit
        """
        rows = self.graph.execute_query(cypher, {"limit": limit})
        return [
            {
                "step_id": r["step_id"],
                "name": r.get("name"),
                "key": r.get("key"),
                "duration_days": r.get("duration_days", 0),
                "indegree": r.get("indegree", 0),
                "outdegree": r.get("outdegree", 0),
                "bottleneck_score": round(float(r.get("score", 0.0)), 4),
            }
            for r in rows
        ]

    # ---------------------------------------------------------------------
    # Persist metrics to graph
    # ---------------------------------------------------------------------
    def persist_metrics(self, steps: list[dict[str, Any]], transitions: list[dict[str, Any]]) -> dict[str, int]:
        """
        Write usage_count and bottleneck_score to Step nodes,
        and freq + last_computed_at to NEXT relations.
        """
        timestamp = datetime.utcnow().isoformat()
        updated_steps = 0
        updated_transitions = 0

        # Update steps
        if steps:
            cypher_steps = """
            UNWIND $items AS it
            MATCH (s:Step {id: it.step_id})
            SET s.usage_count = coalesce(it.usage, s.usage_count),
                s.bottleneck_score = coalesce(it.bottleneck_score, s.bottleneck_score),
                s.metrics_updated_at = datetime($ts)
            RETURN count(s) AS updated
            """
            res = self.graph.execute_query(cypher_steps, {"items": steps, "ts": timestamp})
            if res:
                updated_steps = res[0].get("updated", 0)

        # Update transitions
        if transitions:
            cypher_trans = """
            UNWIND $items AS it
            MATCH (s1:Step {id: it.from_id})-[r:NEXT]->(s2:Step {id: it.to_id})
            SET r.freq = coalesce(it.freq, r.freq),
                r.last_computed_at = datetime($ts)
            RETURN count(r) AS updated
            """
            res2 = self.graph.execute_query(cypher_trans, {"items": transitions, "ts": timestamp})
            if res2:
                updated_transitions = res2[0].get("updated", 0)

        return {"steps": updated_steps, "transitions": updated_transitions}
