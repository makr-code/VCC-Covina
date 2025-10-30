"""Integration test for Legal Domain Taxonomy with real Neo4j.

This test requires:
- Neo4j running (configured via UDS3)
- ENABLE_INTEGRATION_TESTS=true env var

Run with: pytest tests/integration/test_legal_taxonomy_neo4j.py
"""
from __future__ import annotations

import os
import pytest
from pathlib import Path

# Skip entire module if integration tests disabled
pytestmark = pytest.mark.skipif(
    os.getenv("ENABLE_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled (set ENABLE_INTEGRATION_TESTS=true)",
)


@pytest.mark.asyncio
async def test_load_taxonomy_to_neo4j():
    """Load legal taxonomy into real Neo4j and verify."""
    from uds3.database.database_manager import DatabaseManager
    from ingestion.graph.legal_domain_taxonomy import TaxonomySeed, LegalDomainTaxonomyLoader
    from ingestion.graph.setup_indices import setup_indices

    # Initialize UDS3 with Neo4j
    db = DatabaseManager(autostart=True)
    if not db.graph_backend:
        pytest.skip("Neo4j backend not available")

    # Adapter for taxonomy loader
    class Neo4jAdapter:
        def __init__(self, backend):
            self.backend = backend

        async def execute(self, cypher: str, params: dict) -> None:
            self.backend.execute(cypher, params)

    adapter = Neo4jAdapter(db.graph_backend)

    # Setup indices first
    index_count = await setup_indices(adapter)
    assert index_count == 7

    # Load seed data
    seed_path = Path(__file__).parent.parent.parent / "ingestion" / "data" / "legal_domains_seed.json"
    seed = TaxonomySeed.load(seed_path)

    loader = LegalDomainTaxonomyLoader(adapter)
    stats = await loader.load(seed)

    # Verify stats
    assert stats["nodes"] > 0
    assert stats["relationships"] > 0
    print(f"Loaded {stats['nodes']} nodes and {stats['relationships']} relationships")

    # Query Neo4j to verify
    count_query = "MATCH (d:LegalDomain) RETURN count(d) as cnt"
    result = db.graph_backend.execute(count_query, {})
    node_count = list(result)[0]["cnt"]
    assert node_count == stats["nodes"]

    # Verify tier 1 domains exist
    tier1_query = "MATCH (d:LegalDomain {tier: 1}) RETURN d.id as id"
    tier1_result = db.graph_backend.execute(tier1_query, {})
    tier1_ids = {record["id"] for record in tier1_result}
    assert "oeffentliches_recht" in tier1_ids
    assert "privatrecht" in tier1_ids

    # Verify relationships
    rel_query = "MATCH ()-[r:SUBDOMAIN_OF]->() RETURN count(r) as cnt"
    rel_result = db.graph_backend.execute(rel_query, {})
    rel_count = list(rel_result)[0]["cnt"]
    assert rel_count == stats["relationships"]

    # Verify specific hierarchy (baurecht -> verwaltungsrecht -> oeffentliches_recht)
    path_query = """
    MATCH path = (child:LegalDomain {id: 'baurecht'})-[:SUBDOMAIN_OF*]->(root:LegalDomain {id: 'oeffentliches_recht'})
    RETURN length(path) as depth
    """
    path_result = db.graph_backend.execute(path_query, {})
    path_records = list(path_result)
    if path_records:
        depth = path_records[0]["depth"]
        assert depth == 2  # baurecht -> verwaltungsrecht -> oeffentliches_recht

    print("✅ Legal taxonomy successfully loaded to Neo4j")


@pytest.mark.asyncio
async def test_idempotent_reload():
    """Verify reloading taxonomy doesn't duplicate nodes."""
    from uds3.database.database_manager import DatabaseManager
    from ingestion.graph.legal_domain_taxonomy import TaxonomySeed, LegalDomainTaxonomyLoader

    db = DatabaseManager(autostart=True)
    if not db.graph_backend:
        pytest.skip("Neo4j backend not available")

    class Neo4jAdapter:
        def __init__(self, backend):
            self.backend = backend

        async def execute(self, cypher: str, params: dict) -> None:
            self.backend.execute(cypher, params)

    adapter = Neo4jAdapter(db.graph_backend)
    seed_path = Path(__file__).parent.parent.parent / "ingestion" / "data" / "legal_domains_seed.json"
    seed = TaxonomySeed.load(seed_path)

    # First load
    loader = LegalDomainTaxonomyLoader(adapter)
    stats1 = await loader.load(seed)

    # Get counts from Neo4j
    count_query = "MATCH (d:LegalDomain) RETURN count(d) as cnt"
    result1 = db.graph_backend.execute(count_query, {})
    count1 = list(result1)[0]["cnt"]

    # Second load (should be idempotent)
    stats2 = await loader.load(seed)
    result2 = db.graph_backend.execute(count_query, {})
    count2 = list(result2)[0]["cnt"]

    # Counts should be identical
    assert count1 == count2
    assert stats1 == stats2

    print(f"✅ Idempotent reload verified: {count1} nodes maintained")
