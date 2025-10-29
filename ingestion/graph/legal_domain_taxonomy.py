from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

@dataclass
class DomainNode:
    id: str
    name: str
    tier: int
    parent: Optional[str]
    keywords: List[str]

@dataclass
class TaxonomySeed:
    version: str
    last_updated: str
    nodes: List[DomainNode]

    @classmethod
    def load(cls, file_path: str | Path) -> "TaxonomySeed":
        data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        nodes: List[DomainNode] = []
        for item in data.get("domains", []):
            nodes.append(
                DomainNode(
                    id=item["id"],
                    name=item.get("name", item["id"]).strip(),
                    tier=int(item.get("tier", 0)),
                    parent=item.get("parent"),
                    keywords=item.get("keywords", []),
                )
            )
        return cls(
            version=data.get("version", "0.0"),
            last_updated=data.get("last_updated", ""),
            nodes=nodes,
        )

class LegalDomainTaxonomyLoader:
    """Build idempotent upserts for LegalDomain nodes and SUBDOMAIN_OF relationships.

    Repository should implement an `execute(cypher: str, params: dict)` method
    or provide higher-level `upsert_domain(node)` and `link_subdomain(parent, child)`.
    """

    def __init__(self, repository) -> None:
        self.repo = repository

    async def load(self, seed: TaxonomySeed) -> Dict[str, int]:
        created_nodes = 0
        created_rels = 0
        # Upsert nodes
        for node in seed.nodes:
            await self._upsert_domain(node)
            created_nodes += 1
        # Upsert relationships (child -> parent)
        by_id: Dict[str, DomainNode] = {n.id: n for n in seed.nodes}
        for node in seed.nodes:
            if node.parent and node.parent in by_id:
                await self._link_subdomain(node_id=node.id, parent_id=node.parent)
                created_rels += 1
        return {"nodes": created_nodes, "relationships": created_rels}

    async def _upsert_domain(self, node: DomainNode) -> None:
        if hasattr(self.repo, "upsert_legal_domain"):
            await self.repo.upsert_legal_domain(
                node_id=node.id,
                name=node.name,
                tier=node.tier,
                keywords=node.keywords,
            )
            return
        # Fallback to cypher execution contract
        cypher = (
            "MERGE (d:LegalDomain {id: $id})\n"
            "ON CREATE SET d.name=$name, d.tier=$tier, d.keywords=$keywords\n"
            "ON MATCH SET d.name=coalesce(d.name,$name), d.tier=$tier\n"
        )
        params = {"id": node.id, "name": node.name, "tier": node.tier, "keywords": node.keywords}
        await self.repo.execute(cypher, params)

    async def _link_subdomain(self, node_id: str, parent_id: str) -> None:
        if hasattr(self.repo, "link_subdomain_of"):
            await self.repo.link_subdomain_of(child_id=node_id, parent_id=parent_id)
            return
        cypher = (
            "MATCH (c:LegalDomain {id:$child_id}), (p:LegalDomain {id:$parent_id})\n"
            "MERGE (c)-[:SUBDOMAIN_OF]->(p)"
        )
        await self.repo.execute(cypher, {"child_id": node_id, "parent_id": parent_id})
