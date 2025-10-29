from fastapi import FastAPI
from fastapi.testclient import TestClient
import types


def test_v2_ingest_chunk_smoke(monkeypatch):
    # Arrange: monkeypatch create_pipeline to avoid real UDS3
    from ingestionV2 import factory as v2_factory

    class FakeWriter:
        async def write(self, chunk):
            return True

        async def write_batch(self, chunks):
            return {"success": True, "written": len(chunks), "failed": 0, "errors": []}

        async def health_check(self):
            return True

    class FakeRouter:
        def __init__(self, writer, fail_fast=False):
            self._writer = writer

        async def process(self, chunk):
            ok = await self._writer.write(chunk)
            return types.SimpleNamespace(success=ok, error=None if ok else "write_failed")

    def fake_create_pipeline(config=None):
        return FakeRouter(FakeWriter()), FakeWriter()

    monkeypatch.setattr(v2_factory, "create_pipeline", fake_create_pipeline)

    # Build app with V2 router
    from ingestionV2.api_v2 import build_v2_router
    app = FastAPI()
    app.include_router(build_v2_router(cfg={}))

    client = TestClient(app)

    # Act
    payload = {
        "text": "hello world",
        "metadata": {"source_file": "file.txt", "chunk_index": 0, "total_chunks": 1},
    }
    resp = client.post("/v2/ingest/chunk", json=payload)

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["error"] is None
