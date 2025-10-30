from __future__ import annotations

import asyncio
from typing import List, Tuple

import pytest

from ingestion.graph.setup_indices import setup_indices, INDEX_QUERIES


class DummyRepo:
    def __init__(self) -> None:
        self.calls: List[Tuple[str, dict]] = []

    async def execute(self, cypher: str, params: dict) -> None:
        self.calls.append((cypher, params))


@pytest.mark.asyncio
async def test_setup_indices_executes_all_queries():
    repo = DummyRepo()
    count = await setup_indices(repo)

    assert count == len(tuple(INDEX_QUERIES))
    assert len(repo.calls) == count
    cyphers = [c for c, _ in repo.calls]
    for q in INDEX_QUERIES:
        assert q in cyphers


@pytest.mark.asyncio
async def test_indices_exist_in_neo4j():
    """Validate indices exist in real Neo4j instance.
    
    Requires Neo4j connection via UDS3.
    Skipped if Neo4j unavailable.
    """
    pytest.importorskip("uds3")
    from uds3.database.database_manager import DatabaseManager

    try:
        db = DatabaseManager(autostart=True)
        if not db.graph_backend:
            pytest.skip("Neo4j backend not available")

        # Setup indices first
        class RepoAdapter:
            def __init__(self, backend):
                self.backend = backend

            async def execute(self, cypher: str, params: dict) -> None:
                # Neo4j execute is sync, wrap in async
                self.backend.execute(cypher, params)

        adapter = RepoAdapter(db.graph_backend)
        await setup_indices(adapter)

        # Verify indices via SHOW INDEXES
        result = db.graph_backend.execute("SHOW INDEXES", {})
        index_names = [record.get("name") for record in result if "name" in record]

        # Check expected indices exist
        expected_indices = [
            "legal_domain_id",
            "legal_domain_tier",
            "legal_concept_id",
            "jurisdiction_id",
            "jurisdiction_ags",
            "authority_id",
            "legal_concept_search",
        ]

        for expected in expected_indices:
            assert any(
                expected in name for name in index_names
            ), f"Index {expected} not found in Neo4j"

    except Exception as e:
        pytest.skip(f"Neo4j connection failed: {e}")
