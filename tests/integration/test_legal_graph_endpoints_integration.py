import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Integration only when explicitly enabled
ENABLE = os.getenv("ENABLE_INTEGRATION_TESTS", "false").lower() == "true"
pytestmark = pytest.mark.skipif(not ENABLE, reason="Enable with ENABLE_INTEGRATION_TESTS=true")

from backend.queries.legal_graph_queries import router, get_query_service, LegalGraphQueryService

class RealAdapterService(LegalGraphQueryService):
    def __init__(self):
        super().__init__()
        # Ensure adapter can connect early to fail fast
        adapter = self._get_graph_adapter()
        # Quick connectivity check
        adapter.execute_query("RETURN 1 AS ok", {})

app = FastAPI()
app.include_router(router)

@app.on_event("startup")
def override_dep():
    # Use the real service (which uses UDS3Gateway -> Neo4j)
    app.dependency_overrides[get_query_service] = lambda: RealAdapterService()

client = TestClient(app)


def test_domains_by_tier_real():
    r = client.get("/legal-graph/domains?tier=1")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Should contain at least root domains after setup
    assert len(data) >= 1


def test_domain_path_real():
    # Use a known domain id from seed, e.g. 'baurecht' if available
    # Query tier 2 first to find any id
    r = client.get("/legal-graph/domains?tier=2")
    assert r.status_code == 200
    items = r.json()
    if not items:
        pytest.skip("No tier 2 domains present")
    domain_id = items[0]["id"]
    rp = client.get(f"/legal-graph/domain/{domain_id}/path")
    assert rp.status_code == 200
    path = rp.json()
    assert "nodes" in path and len(path["nodes"]) >= 1
