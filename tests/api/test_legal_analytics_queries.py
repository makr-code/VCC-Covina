from __future__ import annotations
from unittest.mock import Mock
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from backend.queries.legal_analytics_queries import (
    router,
    LegalAnalyticsService,
    PaginationParams,
    LawsPerDomainItem,
    NormsPerJurisdictionItem,
    DocsPerConceptItem,
    QueryResult,
    get_service as _get_service,
)


class FakeRelationalAdapter:
    def __init__(self, responses: list[list[dict]]):
        self._responses = responses
        self.calls = []

    def execute_query(self, sql: str, params: dict):
        self.calls.append((sql, params))
        return self._responses.pop(0) if self._responses else []


def create_app_with_service(service: LegalAnalyticsService) -> FastAPI:
    app = FastAPI()

    def get_service_override():
        return service

    app.dependency_overrides[_get_service] = get_service_override
    app.include_router(router)
    return app


def test_laws_per_domain_basic():
    # Prepare fake rows
    rows = [
        {"domain_id": "bau", "domain_name": "Baurecht", "laws_count": 12},
        {"domain_id": "imm", "domain_name": "Immissionsschutz", "laws_count": 9},
    ]
    adapter = FakeRelationalAdapter([rows])
    service = LegalAnalyticsService(adapter)
    app = create_app_with_service(service)
    client = TestClient(app)

    r = client.get("/legal-analytics/laws-per-domain?from=2025-01-01&to=2025-12-31")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["domain_id"] == "bau"
    assert data[0]["laws_count"] == 12


def test_norms_per_jurisdiction_pagination():
    # Prepare count and page rows
    count_rows = [{"total": 3}]
    page_rows = [
        {"jurisdiction_id": "DE", "jurisdiction_name": "Deutschland", "norms_count": 20},
        {"jurisdiction_id": "BW", "jurisdiction_name": "Baden-Württemberg", "norms_count": 12},
    ]
    adapter = FakeRelationalAdapter([count_rows, page_rows])
    service = LegalAnalyticsService(adapter)
    app = create_app_with_service(service)
    client = TestClient(app)

    r = client.get("/legal-analytics/norms-per-jurisdiction?page=1&page_size=2")
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["jurisdiction_id"] == "DE"


def test_docs_per_concept_with_domain_filter():
    # Prepare count and page rows
    count_rows = [{"total": 2}]
    page_rows = [
        {"concept_id": "baurecht", "concept_name": "Baurecht", "document_count": 7},
        {"concept_id": "wasserrecht", "concept_name": "Wasserrecht", "document_count": 5},
    ]
    adapter = FakeRelationalAdapter([count_rows, page_rows])
    service = LegalAnalyticsService(adapter)
    app = create_app_with_service(service)
    client = TestClient(app)

    r = client.get("/legal-analytics/docs-per-concept?domain_id=oere")
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["concept_id"] == "baurecht"
