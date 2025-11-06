"""
Gap Detection Engine - Process Quality Rules

Detects structural gaps in process graphs:
- Missing Roles: Steps without PERFORMED_BY relation
- Dead-Ends: Non-terminal steps without outgoing NEXT
- Cycles: Simple cycle detection (optional/minimal)
"""
from __future__ import annotations
from typing import Any


class GapDetectionService:
    """Detects gaps using Neo4j queries."""

    def __init__(self, graph_adapter):
        self.graph = graph_adapter

    def detect_missing_roles(self, process_id: str | None = None) -> list[dict[str, Any]]:
        """Steps without PERFORMED_BY relation (optionally scoped to one process)."""
        where = "WHERE p.id = $process_id" if process_id else ""
        cypher = f"""
        MATCH (p:Process)-[:HAS_STEP]->(s:Step)
        {where}
        OPTIONAL MATCH (s)-[:PERFORMED_BY]->(r:Role)
        WITH p, s, count(r) AS role_count
        WHERE role_count = 0
        RETURN p.id AS process_id, s.id AS step_id, s.name AS step_name, s.key AS step_key
        ORDER BY p.id, s.created_at
        """
        params = {"process_id": process_id} if process_id else {}
        rows = self.graph.execute_query(cypher, params)
        return rows

    def detect_dead_ends(self, process_id: str | None = None) -> list[dict[str, Any]]:
        """Steps with no outgoing NEXT but not terminal 'end' type."""
        where = "WHERE p.id = $process_id" if process_id else ""
        cypher = f"""
        MATCH (p:Process)-[:HAS_STEP]->(s:Step)
        {where}
        OPTIONAL MATCH (s)-[:NEXT]->(n:Step)
        WITH p, s, count(n) AS out_degree
        WHERE out_degree = 0 AND coalesce(s.type, '') <> 'end'
        RETURN p.id AS process_id, s.id AS step_id, s.name AS step_name, s.type AS step_type
        ORDER BY p.id, s.created_at
        """
        params = {"process_id": process_id} if process_id else {}
        rows = self.graph.execute_query(cypher, params)
        return rows

    def detect_unconnected_steps(self, process_id: str | None = None) -> list[dict[str, Any]]:
        """Steps with neither incoming nor outgoing NEXT, excluding start/end types."""
        where = "WHERE p.id = $process_id" if process_id else ""
        cypher = f"""
        MATCH (p:Process)-[:HAS_STEP]->(s:Step)
        {where}
        OPTIONAL MATCH inE = ()-[:NEXT]->(s)
        OPTIONAL MATCH outE = (s)-[:NEXT]->()
        WITH p, s, count(inE) AS in_deg, count(outE) AS out_deg
        WHERE in_deg = 0 AND out_deg = 0 AND coalesce(s.type, '') NOT IN ['start','end']
        RETURN p.id AS process_id, s.id AS step_id, s.name AS step_name, s.type AS step_type
        ORDER BY p.id, s.created_at
        """
        params = {"process_id": process_id} if process_id else {}
        return self.graph.execute_query(cypher, params)

    def detect_missing_controls(self, process_id: str | None = None) -> list[dict[str, Any]]:
        """Steps without CONTROLS relation to a Control node."""
        where = "WHERE p.id = $process_id" if process_id else ""
        cypher = f"""
        MATCH (p:Process)-[:HAS_STEP]->(s:Step)
        {where}
        OPTIONAL MATCH (s)-[:CONTROLS]->(c:Control)
        WITH p, s, count(c) AS ctl
        WHERE ctl = 0
        RETURN p.id AS process_id, s.id AS step_id, s.name AS step_name
        ORDER BY p.id, s.created_at
        """
        params = {"process_id": process_id} if process_id else {}
        return self.graph.execute_query(cypher, params)

    def detect_missing_legal_refs(self, process_id: str | None = None) -> list[dict[str, Any]]:
        """Steps without CITES relation to a LegalRef node."""
        where = "WHERE p.id = $process_id" if process_id else ""
        cypher = f"""
        MATCH (p:Process)-[:HAS_STEP]->(s:Step)
        {where}
        OPTIONAL MATCH (s)-[:CITES]->(l:LegalRef)
        WITH p, s, count(l) AS refs
        WHERE refs = 0
        RETURN p.id AS process_id, s.id AS step_id, s.name AS step_name
        ORDER BY p.id, s.created_at
        """
        params = {"process_id": process_id} if process_id else {}
        return self.graph.execute_query(cypher, params)

    def detect_cycles(self, process_id: str | None = None, max_len: int = 20) -> list[dict[str, Any]]:
        """Detect simple NEXT cycles up to max_len. Returns sample cycles per process.

        Note: Limits path length to avoid combinatorial explosions.
        """
        where = "WHERE p.id = $process_id" if process_id else ""
        cypher = f"""
        MATCH (p:Process)-[:HAS_STEP]->(s:Step)
        {where}
        MATCH path = (s)-[:NEXT*2..{max_len}]->(s)
        WITH p, path, [n IN nodes(path) | n.id][0] AS step_id, length(path) AS len
        RETURN p.id AS process_id, step_id AS start_step_id, len AS cycle_length
        ORDER BY p.id, len ASC
        LIMIT 100
        """
        params = {"process_id": process_id} if process_id else {}
        return self.graph.execute_query(cypher, params)

    def detect_temporal_inconsistencies(self, process_id: str | None = None) -> list[dict[str, Any]]:
        """Detect edges where successor occurs before predecessor based on Date nodes.

        Uses OCCURS_ON -> (d:Date {date: ISO-8601}) links when present.
        """
        where = "WHERE p.id = $process_id" if process_id else ""
        cypher = f"""
        MATCH (p:Process)-[:HAS_STEP]->(a:Step)-[:NEXT]->(b:Step)
        {where}
    OPTIONAL MATCH (a)-[:OCCURS_ON]->(d1:Date)
    OPTIONAL MATCH (b)-[:OCCURS_ON]->(d2:Date)
    WITH p, a, b, coalesce(d1.date, d1.iso) AS from_date, coalesce(d2.date, d2.iso) AS to_date
    WHERE from_date IS NOT NULL AND to_date IS NOT NULL AND to_date < from_date
    RETURN p.id AS process_id, a.id AS from_step_id, b.id AS to_step_id, from_date, to_date
        ORDER BY p.id, from_date
        """
        params = {"process_id": process_id} if process_id else {}
        return self.graph.execute_query(cypher, params)

    def summarize(self, process_id: str | None = None) -> dict[str, Any]:
        """Run all gap checks and return grouped results with counts.

        Returns:
            {
              "counts": {"missing_roles": n, ...},
              "results": {
                  "missing_roles": [...],
                  "dead_ends": [...],
                  "unconnected_steps": [...],
                  "missing_controls": [...],
                  "missing_legal_refs": [...],
                  "cycles": [...],
                  "temporal_inconsistencies": [...]
              }
            }
        """
        missing_roles = self.detect_missing_roles(process_id)
        dead_ends = self.detect_dead_ends(process_id)
        unconnected = self.detect_unconnected_steps(process_id)
        missing_controls = self.detect_missing_controls(process_id)
        missing_legal = self.detect_missing_legal_refs(process_id)
        cycles = self.detect_cycles(process_id)
        temporal_bad = self.detect_temporal_inconsistencies(process_id)

        results = {
            "missing_roles": missing_roles,
            "dead_ends": dead_ends,
            "unconnected_steps": unconnected,
            "missing_controls": missing_controls,
            "missing_legal_refs": missing_legal,
            "cycles": cycles,
            "temporal_inconsistencies": temporal_bad,
        }
        counts = {k: len(v) for k, v in results.items()}
        return {"counts": counts, "results": results}
