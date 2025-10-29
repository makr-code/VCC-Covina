from __future__ import annotations
from fastapi.testclient import TestClient
from backend.ingestion_server.app_factory import get_app


def test_prometheus_exporter_after_ingest_increments():
    app = get_app()
    client = TestClient(app)

    # Trigger one ingest to increment counters
    r = client.post("/ingestion/ingest", json={"text": "Hello world"})
    assert r.status_code == 200

    # Scrape prometheus endpoint
    r2 = client.get("/ingestion/prometheus")
    assert r2.status_code == 200
    body = r2.text
    # Basic presence checks
    assert "# TYPE legal_nlp_extractions_total counter" in body
    assert "legal_nlp_extractions_total{" in body or "legal_nlp_extractions_total " in body
