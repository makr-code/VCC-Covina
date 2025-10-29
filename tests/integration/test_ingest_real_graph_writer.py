from __future__ import annotations
import os
from fastapi.testclient import TestClient
from backend.ingestion_server.app_factory import get_app
import ingestion.boot.container as container_module

class StubExtractor:
    async def extract(self, text: str):
        return {
            "document_id": "doc_test_1",
            "concepts": [
                {"id": "baurecht", "name": "Baurecht", "tier": 1, "count": 1}
            ],
            "norms": [
                {"id": "§3_abs1_baugb", "norm_text": "§ 3 Abs. 1 BauGB", "paragraph": "3", "sentence": "1"}
            ],
            # keep relations optional; link may no-op if Document doesn't exist
        }


def test_ingest_with_real_graph_writer(monkeypatch):
    os.environ["ENABLE_GRAPH_WRITER"] = "true"

    # Patch extractor to emit entities and doc_id
    monkeypatch.setattr(container_module.container, "extractor", StubExtractor(), raising=False)

    app = get_app()
    client = TestClient(app)

    r = client.post("/ingestion/ingest", json={"text": "Any content that triggers stub."})
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
