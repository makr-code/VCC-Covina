from __future__ import annotations
from typing import Protocol, Any, Dict, Optional

from ingestion.infrastructure.clients.uds3_gateway import UDS3Gateway

class GraphRepository(Protocol):
    async def upsert_extraction(self, data: Any) -> None: ...
    async def upsert_legal_domain(self, node_id: str, name: str, tier: int, keywords: list[str]) -> None: ...
    async def link_subdomain_of(self, child_id: str, parent_id: str) -> None: ...

class Neo4jGraphRepository(GraphRepository):
    """GraphRepository-Implementierung auf Basis von UDS3 (Neo4j-Adapter)."""

    def __init__(self, uds3_gateway: Optional[UDS3Gateway] = None, graph_adapter: Optional[Any] = None) -> None:
        # Bevorzugt: Adapter via UDS3Gateway beziehen; alternativ direkten Adapter entgegennehmen (Tests)
        self._gateway = uds3_gateway or UDS3Gateway()
        self._graph = graph_adapter or self._gateway.get_graph_adapter()

    async def upsert_extraction(self, data: Any) -> None:
        # Platzhalter: spätere Extraktionspersistenz (Nodes/Edges) via Cypher
        return None

    async def upsert_legal_domain(self, node_id: str, name: str, tier: int, keywords: list[str]) -> None:
        cypher = (
            "MERGE (d:LegalDomain {id: $id})\n"
            "ON CREATE SET d.name=$name, d.tier=$tier, d.keywords=$keywords, d.created_at=timestamp()\n"
            "ON MATCH SET d.name=coalesce(d.name,$name), d.tier=$tier, d.updated_at=timestamp()"
        )
        params = {"id": node_id, "name": name, "tier": int(tier), "keywords": keywords or []}
        self._execute_sync(cypher, params)

    async def link_subdomain_of(self, child_id: str, parent_id: str) -> None:
        cypher = (
            "MATCH (c:LegalDomain {id:$child_id}), (p:LegalDomain {id:$parent_id})\n"
            "MERGE (c)-[:SUBDOMAIN_OF]->(p)"
        )
        params = {"child_id": child_id, "parent_id": parent_id}
        self._execute_sync(cypher, params)

    async def execute(self, cypher: str, params: Optional[Dict] = None) -> None:
        """Fallback-API für einfache Cypher-Ausführung (für Loader-Kompatibilität)."""
        self._execute_sync(cypher, params or {})

    def _execute_sync(self, cypher: str, params: Dict) -> None:
        # UDS3 Neo4j-Backend stellt execute_query(cypher, params) bereit
        try:
            _ = self._graph.execute_query(cypher, params)
        except Exception as e:
            # Konsistenter Fehlerpfad; Upserts sind idempotent → Escalate
            raise RuntimeError(f"Neo4j execution failed: {e}")
