"""Tests for Legal Domain Taxonomy Loader.

Validates:
- Seed loading (JSON parsing, node counts)
- Idempotent upserts (multiple runs don't change counts)
- Parent-child relationships (SUBDOMAIN_OF)
- Repository contract (execute or domain-specific methods)
"""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import List, Tuple, Dict, Any

from ingestion.graph.legal_domain_taxonomy import (
    DomainNode,
    TaxonomySeed,
    LegalDomainTaxonomyLoader,
)


class DummyGraphRepo:
    """Mock repository tracking all upserts and relationships."""

    def __init__(self) -> None:
        self.domains: Dict[str, Dict[str, Any]] = {}  # id -> {name, tier, keywords}
        self.relationships: List[Tuple[str, str]] = []  # (child, parent)
        self.execute_calls: List[Tuple[str, dict]] = []

    async def upsert_legal_domain(
        self, node_id: str, name: str, tier: int, keywords: List[str]
    ) -> None:
        """Domain-specific upsert method."""
        self.domains[node_id] = {"name": name, "tier": tier, "keywords": keywords}

    async def link_subdomain_of(self, child_id: str, parent_id: str) -> None:
        """Domain-specific relationship method."""
        rel = (child_id, parent_id)
        if rel not in self.relationships:
            self.relationships.append(rel)

    async def execute(self, cypher: str, params: dict) -> None:
        """Fallback execute method."""
        self.execute_calls.append((cypher, params))


@pytest.fixture
def seed_file() -> Path:
    """Path to legal_domains_seed.json."""
    return Path(__file__).parent.parent.parent / "ingestion" / "data" / "legal_domains_seed.json"


@pytest.fixture
def dummy_repo() -> DummyGraphRepo:
    """Fresh repository for each test."""
    return DummyGraphRepo()


@pytest.mark.asyncio
async def test_seed_loads_correctly(seed_file: Path):
    """Verify JSON parsing and node creation."""
    seed = TaxonomySeed.load(seed_file)

    assert seed.version == "1.0"
    assert seed.last_updated == "2025-10-29"
    assert len(seed.nodes) > 0

    # Check expected top-level domains (tier 1)
    tier1_ids = {n.id for n in seed.nodes if n.tier == 1}
    assert "oeffentliches_recht" in tier1_ids
    assert "privatrecht" in tier1_ids

    # Check tier 2 has parents
    tier2_nodes = [n for n in seed.nodes if n.tier == 2]
    assert all(n.parent is not None for n in tier2_nodes)


@pytest.mark.asyncio
async def test_loader_creates_nodes_and_relationships(
    seed_file: Path, dummy_repo: DummyGraphRepo
):
    """Verify loader calls upsert methods correctly."""
    seed = TaxonomySeed.load(seed_file)
    loader = LegalDomainTaxonomyLoader(dummy_repo)

    stats = await loader.load(seed)

    # Check stats match seed
    assert stats["nodes"] == len(seed.nodes)
    assert stats["relationships"] > 0

    # Check domains were created
    assert len(dummy_repo.domains) == len(seed.nodes)

    # Verify specific nodes
    assert "oeffentliches_recht" in dummy_repo.domains
    assert dummy_repo.domains["oeffentliches_recht"]["tier"] == 1

    # Check relationships created
    assert len(dummy_repo.relationships) == stats["relationships"]


@pytest.mark.asyncio
async def test_idempotent_loading(seed_file: Path, dummy_repo: DummyGraphRepo):
    """Multiple loads should not duplicate nodes/rels."""
    seed = TaxonomySeed.load(seed_file)
    loader = LegalDomainTaxonomyLoader(dummy_repo)

    # First load
    stats1 = await loader.load(seed)
    nodes_count1 = len(dummy_repo.domains)
    rels_count1 = len(dummy_repo.relationships)

    # Second load (simulating idempotent MERGE)
    stats2 = await loader.load(seed)
    nodes_count2 = len(dummy_repo.domains)
    rels_count2 = len(dummy_repo.relationships)

    # Counts should be identical (idempotent)
    assert stats1 == stats2
    assert nodes_count1 == nodes_count2
    assert rels_count1 == rels_count2


@pytest.mark.asyncio
async def test_parent_child_chains(seed_file: Path, dummy_repo: DummyGraphRepo):
    """Verify hierarchical relationships are correct."""
    seed = TaxonomySeed.load(seed_file)
    loader = LegalDomainTaxonomyLoader(dummy_repo)
    await loader.load(seed)

    # Build parent map
    parent_map = {child: parent for child, parent in dummy_repo.relationships}

    # Check baurecht → verwaltungsrecht → oeffentliches_recht
    if "baurecht" in parent_map:
        assert parent_map["baurecht"] == "verwaltungsrecht"
        assert parent_map["verwaltungsrecht"] == "oeffentliches_recht"

    # Check immissionsschutzrecht chains correctly
    if "immissionsschutzrecht" in parent_map:
        immediate_parent = parent_map["immissionsschutzrecht"]
        # Should be either umweltrecht or baurecht depending on seed
        assert immediate_parent in {"umweltrecht", "baurecht"}


@pytest.mark.asyncio
async def test_fallback_to_execute_method():
    """Test fallback when repo lacks domain-specific methods."""

    class ExecuteOnlyRepo:
        def __init__(self):
            self.calls: List[Tuple[str, dict]] = []

        async def execute(self, cypher: str, params: dict) -> None:
            self.calls.append((cypher, params))

    repo = ExecuteOnlyRepo()
    seed = TaxonomySeed(
        version="test",
        last_updated="2025-10-30",
        nodes=[
            DomainNode(
                id="test_domain",
                name="Test Domain",
                tier=1,
                parent=None,
                keywords=["test"],
            )
        ],
    )

    loader = LegalDomainTaxonomyLoader(repo)
    await loader.load(seed)

    # Should have called execute() instead of domain methods
    assert len(repo.calls) == 1  # 1 node, no relationships
    cypher, params = repo.calls[0]
    assert "MERGE (d:LegalDomain" in cypher
    assert params["id"] == "test_domain"


@pytest.mark.asyncio
async def test_keywords_persisted(seed_file: Path, dummy_repo: DummyGraphRepo):
    """Verify keywords are stored correctly."""
    seed = TaxonomySeed.load(seed_file)
    loader = LegalDomainTaxonomyLoader(dummy_repo)
    await loader.load(seed)

    # Check domain has keywords
    oeff_recht = dummy_repo.domains.get("oeffentliches_recht")
    assert oeff_recht is not None
    assert isinstance(oeff_recht["keywords"], list)
    assert len(oeff_recht["keywords"]) > 0
    # Expected keywords from seed
    assert any("Verwaltung" in kw for kw in oeff_recht["keywords"])


@pytest.mark.asyncio
async def test_tier_assignment(seed_file: Path, dummy_repo: DummyGraphRepo):
    """Verify tier values are correctly assigned."""
    seed = TaxonomySeed.load(seed_file)
    loader = LegalDomainTaxonomyLoader(dummy_repo)
    await loader.load(seed)

    # Tier 1: Top-level
    tier1_domains = [
        did for did, data in dummy_repo.domains.items() if data["tier"] == 1
    ]
    assert len(tier1_domains) >= 2  # At least oeffentliches_recht, privatrecht

    # Tier 2: Sub-domains
    tier2_domains = [
        did for did, data in dummy_repo.domains.items() if data["tier"] == 2
    ]
    assert len(tier2_domains) > 0

    # Tier 3: Specific areas
    tier3_domains = [
        did for did, data in dummy_repo.domains.items() if data["tier"] == 3
    ]
    assert len(tier3_domains) > 0
