import asyncio
from unittest.mock import AsyncMock

import pytest

from ingestion.core.ingest_router import ChunkRouter, RouteResult
from ingestion.core.interfaces import Chunk, ChunkMetadata


@pytest.mark.asyncio
async def test_chunk_router_success():
    writer = AsyncMock()
    writer.write = AsyncMock(return_value=True)

    router = ChunkRouter(writer)
    chunk = Chunk(text="hello", metadata=ChunkMetadata(source_file="a.txt", chunk_index=0, total_chunks=1))
    res = await router.process(chunk)

    assert isinstance(res, RouteResult)
    assert res.success is True
    writer.write.assert_awaited_once()


@pytest.mark.asyncio
async def test_chunk_router_failure_collects_error():
    writer = AsyncMock()
    writer.write = AsyncMock(side_effect=RuntimeError("db down"))

    router = ChunkRouter(writer, fail_fast=False)
    chunk = Chunk(text="x", metadata=ChunkMetadata(source_file="b.txt", chunk_index=0, total_chunks=1))
    res = await router.process(chunk)

    assert res.success is False
    assert "db down" in (res.error or "")
