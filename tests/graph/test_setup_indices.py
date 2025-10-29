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
