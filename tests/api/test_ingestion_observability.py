from __future__ import annotations
from fastapi.testclient import TestClient
from backend.ingestion_server.app_factory import get_app
from utils.metrics import metrics_registry

def get_metric_value(name: str, labels: dict[str, str] | None = None) -> float:
    metric = metrics_registry.get(name)
    if not metric:
        return 0.0
    # Only Counter/Gauge used here
    try:
        return metric.get(labels or {})
    except Exception:
        # Counter.get expects labels dict
        return 0.0


def test_health_and_metrics_endpoints_basic():
    app = get_app()
    client = TestClient(app)

    # Health returns ok and metrics highlights
    r = client.get("/ingestion/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "metrics" in data
    assert set(data["metrics"].keys()) >= {"extractions_total", "extractions_success", "extractions_error"}

    # Metrics returns full registry dump
    r2 = client.get("/ingestion/metrics")
    assert r2.status_code == 200
    m = r2.json()
    assert "metrics" in m
    assert isinstance(m["metrics"], list)


def test_ingest_increments_extraction_counter():
    app = get_app()
    client = TestClient(app)

    before = get_metric_value("legal_nlp_extractions_total", labels={"status": "success"})

    # Trigger ingestion
    r = client.post("/ingestion/ingest", json={"text": "Test document content."})
    assert r.status_code == 200
    payload = r.json()
    assert payload.get("status") == "ok"

    after = get_metric_value("legal_nlp_extractions_total", labels={"status": "success"})
    assert after >= before + 1
