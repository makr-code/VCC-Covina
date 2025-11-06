from __future__ import annotations
"""
Temporal Canon for Neo4j (UDS3-compatible)
------------------------------------------

Provides small, reusable helpers to model time consistently in the graph.
Reuses existing conventions already present in Covina/UDS3 code:
- created_at/updated_at timestamps set via Neo4j datetime()/timestamp()
- Idempotent MERGE-based upserts

Canonical nodes:
- (:Year {y})
- (:Month {y, m})
- (:Day {y, m, d})
- (:Date {iso, year, month, day})

Canonical relations:
- (:Year)-[:HAS_MONTH]->(:Month)
- (:Month)-[:HAS_DAY]->(:Day)
- (:Day)-[:IS_DATE]->(:Date)
- AnyNode-[:OCCURS_ON]->(:Date)
- AnyNode-[:SCHEDULED_FOR]->(:Date)
- AnyNode-[:EFFECTIVE_FROM]->(:Date)
- AnyNode-[:EFFECTIVE_UNTIL]->(:Date)

Usage example:
    canon = TemporalCanon(graph_adapter)
    canon.link_occurs_on('ProcessStep', step_id, '2025-10-30')

The graph_adapter is expected to provide execute_query(cypher: str, params: dict) -> Any
as provided by the UDS3 Neo4j backend used elsewhere in Covina.
"""

from dataclasses import dataclass
from typing import Any, Optional


def _parse_iso_date(iso: str) -> tuple[int, int, int]:
    parts = iso.strip().split("-")
    if len(parts) != 3:
        raise ValueError(f"Invalid ISO date: {iso}")
    y, m, d = map(int, parts)
    return y, m, d


@dataclass
class TemporalCanon:
    graph: Any  # expects .execute_query(cypher, params)

    def upsert_date(self, iso: str) -> dict[str, Any]:
        """Ensure Year/Month/Day/Date nodes exist and are linked.
        Returns a dict with ids of created/merged nodes.
        """
        y, m, d = _parse_iso_date(iso)
        cypher = """
        MERGE (y:Year {y: $y})
          ON CREATE SET y.created_at = datetime(), y.updated_at = datetime()
          ON MATCH  SET y.updated_at = datetime()
        MERGE (mo:Month {y: $y, m: $m})
          ON CREATE SET mo.created_at = datetime(), mo.updated_at = datetime()
          ON MATCH  SET mo.updated_at = datetime()
        MERGE (y)-[:HAS_MONTH]->(mo)
        MERGE (da:Day {y: $y, m: $m, d: $d})
          ON CREATE SET da.created_at = datetime(), da.updated_at = datetime()
          ON MATCH  SET da.updated_at = datetime()
        MERGE (mo)-[:HAS_DAY]->(da)
        MERGE (dt:Date {iso: $iso})
          ON CREATE SET dt.year = $y, dt.month = $m, dt.day = $d, dt.created_at = datetime(), dt.updated_at = datetime()
          ON MATCH  SET dt.updated_at = datetime()
        MERGE (da)-[:IS_DATE]->(dt)
        RETURN y.y AS year, mo.m AS month, da.d AS day, dt.iso AS iso
        """
        return self.graph.execute_query(cypher, {"y": y, "m": m, "d": d, "iso": iso})

    def link_occurs_on(self, label: str, node_id: str, iso: str) -> None:
        """Link an arbitrary node (by id and label) to a Date via OCCURS_ON."""
        y, m, d = _parse_iso_date(iso)
        cypher = f"""
        MERGE (dt:Date {{iso: $iso}})
          ON CREATE SET dt.year=$y, dt.month=$m, dt.day=$d, dt.created_at=datetime(), dt.updated_at=datetime()
          ON MATCH  SET dt.updated_at=datetime()
        MATCH (n:{label} {{id: $id}})
        MERGE (n)-[r:OCCURS_ON]->(dt)
          ON CREATE SET r.created_at = datetime(), r.updated_at = datetime()
          ON MATCH  SET r.updated_at = datetime()
        """
        self.graph.execute_query(cypher, {"id": node_id, "iso": iso, "y": y, "m": m, "d": d})

    def link_scheduled_for(self, label: str, node_id: str, iso: str) -> None:
        y, m, d = _parse_iso_date(iso)
        cypher = f"""
        MERGE (dt:Date {{iso: $iso}})
          ON CREATE SET dt.year=$y, dt.month=$m, dt.day=$d, dt.created_at=datetime(), dt.updated_at=datetime()
          ON MATCH  SET dt.updated_at=datetime()
        MATCH (n:{label} {{id: $id}})
        MERGE (n)-[r:SCHEDULED_FOR]->(dt)
          ON CREATE SET r.created_at = datetime(), r.updated_at = datetime()
          ON MATCH  SET r.updated_at = datetime()
        """
        self.graph.execute_query(cypher, {"id": node_id, "iso": iso, "y": y, "m": m, "d": d})

    def link_effective_range(self, label: str, node_id: str, start_iso: Optional[str], end_iso: Optional[str]) -> None:
        """Link EFFECTIVE_FROM and/or EFFECTIVE_UNTIL to Date nodes if provided."""
        if start_iso:
            self._link_effective(label, node_id, start_iso, rel_type="EFFECTIVE_FROM")
        if end_iso:
            self._link_effective(label, node_id, end_iso, rel_type="EFFECTIVE_UNTIL")

    def _link_effective(self, label: str, node_id: str, iso: str, rel_type: str) -> None:
        y, m, d = _parse_iso_date(iso)
        cypher = f"""
        MERGE (dt:Date {{iso: $iso}})
          ON CREATE SET dt.year=$y, dt.month=$m, dt.day=$d, dt.created_at=datetime(), dt.updated_at=datetime()
          ON MATCH  SET dt.updated_at=datetime()
        MATCH (n:{label} {{id: $id}})
        MERGE (n)-[r:{rel_type}]->(dt)
          ON CREATE SET r.created_at = datetime(), r.updated_at = datetime()
          ON MATCH  SET r.updated_at = datetime()
        """
        self.graph.execute_query(cypher, {"id": node_id, "iso": iso, "y": y, "m": m, "d": d})
