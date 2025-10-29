from __future__ import annotations
import json
from pathlib import Path

import pytest

from ingestion.graph.legal_domain_taxonomy import TaxonomySeed, LegalDomainTaxonomyLoader


class FakeRepo:
    def __init__(self):
        self.nodes = []
        self.rels = []

    async def upsert_legal_domain(self, node_id: str, name: str, tier: int, keywords: list[str]) -> None:
        self.nodes.append((node_id, name, tier, tuple(keywords or [])))

    async def link_subdomain_of(self, child_id: str, parent_id: str) -> None:
        self.rels.append((child_id, parent_id))


@pytest.mark.asyncio
async def test_taxonomy_loader_counts_and_parent_chain(tmp_path: Path):
    # Arrange: temp seed file
    seed_data = {
        "version": "1.0",
        "last_updated": "2025-10-29",
        "domains": [
            {"id": "recht", "name": "Recht", "tier": 0, "keywords": ["gesetz"], "parent": None},
            {"id": "verwaltungsrecht", "name": "Verwaltungsrecht", "tier": 1, "keywords": ["amt"], "parent": "recht"},
            {"id": "baurecht", "name": "Baurecht", "tier": 2, "keywords": ["bau"], "parent": "verwaltungsrecht"},
        ],
    }
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps(seed_data, ensure_ascii=False), encoding="utf-8")

    seed = TaxonomySeed.load(seed_file)
    repo = FakeRepo()
    loader = LegalDomainTaxonomyLoader(repo)

    # Act
    result = await loader.load(seed)

    # Assert node count
    assert result["nodes"] == 3
    # Assert relationship count (2 parent links)
    assert result["relationships"] == 2

    # Node upserts captured
    node_ids = [n[0] for n in repo.nodes]
    assert set(node_ids) == {"recht", "verwaltungsrecht", "baurecht"}

    # Parent chain: verwaltungsrecht -> recht, baurecht -> verwaltungsrecht
    assert ("verwaltungsrecht", "recht") in repo.rels
    assert ("baurecht", "verwaltungsrecht") in repo.rels
