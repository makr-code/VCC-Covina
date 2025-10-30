from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import List

from backend.queries.legal_graph_queries import router, DomainSummary, DomainPath, QueryResult, LegalGraphQueryService

class FakeService(LegalGraphQueryService):
    def __init__(self):
        pass
    def list_domains_by_tier(self, tier: int) -> List[DomainSummary]:
        return [DomainSummary(id="privatrecht", name="Privatrecht", tier=1)]
    def get_domain_children(self, domain_id: str) -> List[DomainSummary]:
        return [DomainSummary(id="baurecht", name="Baurecht", tier=2, parent_id=domain_id)]
    def get_domain_path(self, domain_id: str) -> DomainPath:
        return DomainPath(nodes=[
            DomainSummary(id=domain_id, name="Baurecht", tier=2),
            DomainSummary(id="oeffentliches_recht", name="Öffentliches Recht", tier=1),
        ])
    def search_concepts(self, keyword: str, pagination):
        return QueryResult(total_count=1, page=pagination.page, page_size=pagination.page_size, total_pages=1, items=[{"concept_id":"x","name":"Bauplanungsrecht","domain":"Baurecht","score":1.0}])

app = FastAPI()
app.include_router(router)

# Override dependency
from backend.queries.legal_graph_queries import get_query_service
app.dependency_overrides[get_query_service] = lambda: FakeService()

client = TestClient(app)

def test_list_domains_by_tier():
    r = client.get("/legal-graph/domains?tier=1")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["id"] == "privatrecht"


def test_get_domain_children():
    r = client.get("/legal-graph/domain/oeffentliches_recht/children")
    assert r.status_code == 200
    data = r.json()
    assert data[0]["parent_id"] == "oeffentliches_recht"


def test_get_domain_path():
    r = client.get("/legal-graph/domain/baurecht/path")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data and len(data["nodes"]) == 2


def test_search_concepts():
    r = client.get("/legal-graph/search?keyword=bau&page=1&page_size=10")
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] == 1
    assert data["items"][0]["name"].startswith("Bau")
