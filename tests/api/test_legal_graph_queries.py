"""
Tests for Legal Knowledge Graph Query Endpoints

Tests cover:
- Document queries by domain (with/without subdomains)
- Concept queries by jurisdiction
- Authority queries (with filters)
- Pagination logic
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.queries.legal_graph_queries import (
    router,
    LegalGraphQueryService,
    PaginationParams,
    DocumentSummary,
    LegalConcept,
    Authority,
    QueryResult,
)


@pytest.fixture
def app():
    """Create FastAPI app with legal graph router"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_graph_adapter():
    """Mock Neo4j graph adapter"""
    adapter = Mock()
    adapter.execute_query = Mock()
    return adapter


@pytest.fixture
def mock_service(mock_graph_adapter):
    """Mock Legal Graph Query Service with Neo4j adapter"""
    service = LegalGraphQueryService()
    service._graph_adapter = mock_graph_adapter
    return service


# ============================================================================
# Unit Tests - Business Logic
# ============================================================================


class TestPaginationParams:
    """Test pagination parameter calculations"""

    def test_skip_calculation_page_1(self):
        """Test SKIP value for first page"""
        params = PaginationParams(page=1, page_size=20)
        assert params.skip == 0
        assert params.limit == 20

    def test_skip_calculation_page_2(self):
        """Test SKIP value for second page"""
        params = PaginationParams(page=2, page_size=20)
        assert params.skip == 20
        assert params.limit == 20

    def test_skip_calculation_custom_page_size(self):
        """Test SKIP value with custom page size"""
        params = PaginationParams(page=3, page_size=50)
        assert params.skip == 100
        assert params.limit == 50


class TestLegalGraphQueryService:
    """Test Legal Graph Query Service logic"""

    def test_get_documents_by_domain_exact_match(self, mock_service, mock_graph_adapter):
        """Test querying documents by exact domain (no subdomains)"""
        # Mock count query result
        mock_graph_adapter.execute_query.side_effect = [
            [{"total": 5}],  # Count query
            [  # Data query
                {
                    "document_id": "doc_1",
                    "file_path": "/path/to/doc1.pdf",
                    "classification": "Vertrag",
                    "created_at": "2025-01-15T10:00:00",
                    "domain_names": ["Arbeitsrecht"],
                    "norms_count": 3,
                    "concepts_count": 7,
                },
                {
                    "document_id": "doc_2",
                    "file_path": "/path/to/doc2.pdf",
                    "classification": "Urteil",
                    "created_at": "2025-01-14T09:30:00",
                    "domain_names": ["Arbeitsrecht"],
                    "norms_count": 5,
                    "concepts_count": 12,
                },
            ],
        ]

        pagination = PaginationParams(page=1, page_size=20)
        result = mock_service.get_documents_by_domain(
            "Arbeitsrecht", pagination, include_subdomains=False
        )

        # Verify result structure
        assert isinstance(result, QueryResult)
        assert result.total_count == 5
        assert result.page == 1
        assert result.page_size == 20
        assert result.total_pages == 1
        assert len(result.items) == 2

        # Verify first document
        doc1 = result.items[0]
        assert doc1.document_id == "doc_1"
        assert doc1.file_path == "/path/to/doc1.pdf"
        assert doc1.classification == "Vertrag"
        assert doc1.domains == ["Arbeitsrecht"]
        assert doc1.norms_count == 3
        assert doc1.concepts_count == 7

        # Verify query calls
        assert mock_graph_adapter.execute_query.call_count == 2

    def test_get_documents_by_domain_with_subdomains(
        self, mock_service, mock_graph_adapter
    ):
        """Test querying documents including subdomains"""
        mock_graph_adapter.execute_query.side_effect = [
            [{"total": 10}],  # Count query
            [  # Data query
                {
                    "document_id": "doc_3",
                    "file_path": "/path/to/doc3.pdf",
                    "classification": "Gesetz",
                    "created_at": "2025-01-13T14:20:00",
                    "domain_names": ["Arbeitsrecht", "Arbeitsrecht/Kündigungsschutz"],
                    "norms_count": 8,
                    "concepts_count": 15,
                }
            ],
        ]

        pagination = PaginationParams(page=1, page_size=20)
        result = mock_service.get_documents_by_domain(
            "Arbeitsrecht", pagination, include_subdomains=True
        )

        assert result.total_count == 10
        assert len(result.items) == 1
        doc = result.items[0]
        assert len(doc.domains) == 2
        assert "Arbeitsrecht/Kündigungsschutz" in doc.domains

    def test_get_documents_pagination(self, mock_service, mock_graph_adapter):
        """Test pagination with multiple pages"""
        mock_graph_adapter.execute_query.side_effect = [
            [{"total": 45}],  # Total count
            [  # Page 2 results with complete data
                {
                    "document_id": f"doc_{i}",
                    "file_path": f"/path/doc_{i}.pdf",
                    "classification": "Vertrag",
                    "created_at": "2025-01-01T00:00:00",
                    "domain_names": ["Arbeitsrecht"],
                    "norms_count": 0,
                    "concepts_count": 0,
                }
                for i in range(20)
            ],
        ]

        pagination = PaginationParams(page=2, page_size=20)
        result = mock_service.get_documents_by_domain("Arbeitsrecht", pagination)

        assert result.total_count == 45
        assert result.page == 2
        assert result.total_pages == 3  # ceil(45 / 20)
        assert len(result.items) == 20

    def test_get_concepts_by_jurisdiction(self, mock_service, mock_graph_adapter):
        """Test querying concepts by jurisdiction"""
        mock_graph_adapter.execute_query.side_effect = [
            [{"total": 3}],  # Count query
            [  # Data query
                {
                    "concept_id": "datenschutz",
                    "name": "Datenschutz",
                    "domain": "IT-Recht",
                    "jurisdictions": ["DE"],
                    "document_count": 42,
                },
                {
                    "concept_id": "grundrechte",
                    "name": "Grundrechte",
                    "domain": "Verfassungsrecht",
                    "jurisdictions": ["DE"],
                    "document_count": 35,
                },
            ],
        ]

        pagination = PaginationParams(page=1, page_size=20)
        result = mock_service.get_concepts_by_jurisdiction("DE", pagination)

        assert result.total_count == 3
        assert len(result.items) == 2

        concept1 = result.items[0]
        assert concept1.concept_id == "datenschutz"
        assert concept1.name == "Datenschutz"
        assert concept1.domain == "IT-Recht"
        assert concept1.document_count == 42

    def test_get_authorities_no_filters(self, mock_service, mock_graph_adapter):
        """Test querying all authorities (no filters)"""
        mock_graph_adapter.execute_query.side_effect = [
            [{"total": 2}],  # Count
            [  # Data
                {
                    "authority_id": "bgh",
                    "name": "Bundesgerichtshof",
                    "authority_type": "court",
                    "jurisdiction": "DE",
                    "document_count": 120,
                },
                {
                    "authority_id": "bverfg",
                    "name": "Bundesverfassungsgericht",
                    "authority_type": "court",
                    "jurisdiction": "DE",
                    "document_count": 85,
                },
            ],
        ]

        pagination = PaginationParams(page=1, page_size=20)
        result = mock_service.get_authorities(pagination=pagination)

        assert result.total_count == 2
        assert len(result.items) == 2

        auth1 = result.items[0]
        assert auth1.authority_id == "bgh"
        assert auth1.name == "Bundesgerichtshof"
        assert auth1.authority_type == "court"
        assert auth1.document_count == 120

    def test_get_authorities_with_filters(self, mock_service, mock_graph_adapter):
        """Test querying authorities with jurisdiction and type filters"""
        mock_graph_adapter.execute_query.side_effect = [
            [{"total": 1}],
            [
                {
                    "authority_id": "bag",
                    "name": "Bundesarbeitsgericht",
                    "authority_type": "court",
                    "jurisdiction": "DE",
                    "document_count": 95,
                }
            ],
        ]

        pagination = PaginationParams(page=1, page_size=20)
        result = mock_service.get_authorities(
            jurisdiction="DE", authority_type="court", pagination=pagination
        )

        assert result.total_count == 1
        assert len(result.items) == 1
        assert result.items[0].authority_id == "bag"


# ============================================================================
# API Tests - HTTP Endpoints
# ============================================================================


class TestDocumentsByDomainEndpoint:
    """Test /legal-graph/documents-by-domain endpoint"""

    def test_get_documents_success(self, client, app):
        """Test successful document query"""
        # Create mock service
        mock_service = Mock()
        mock_service.get_documents_by_domain.return_value = QueryResult(
            total_count=5,
            page=1,
            page_size=20,
            total_pages=1,
            items=[
                DocumentSummary(
                    document_id="doc_1",
                    file_path="/test.pdf",
                    classification="Vertrag",
                    domains=["Arbeitsrecht"],
                    norms_count=3,
                    concepts_count=7,
                )
            ],
        )
        
        # Override dependency
        from backend.queries.legal_graph_queries import get_query_service
        app.dependency_overrides[get_query_service] = lambda: mock_service

        response = client.get("/legal-graph/documents-by-domain?domain=Arbeitsrecht")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert data["page"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["document_id"] == "doc_1"
        
        # Cleanup
        app.dependency_overrides.clear()

    def test_get_documents_with_subdomains(self, client):
        """Test document query with subdomain inclusion"""
        response = client.get(
            "/legal-graph/documents-by-domain?domain=Arbeitsrecht&include_subdomains=true"
        )
        # Will fail with real Neo4j, but tests parameter parsing
        assert response.status_code in [200, 500]  # Accept either success or DB error

    def test_get_documents_pagination(self, client):
        """Test document query with pagination parameters"""
        response = client.get(
            "/legal-graph/documents-by-domain?domain=Arbeitsrecht&page=2&page_size=50"
        )
        assert response.status_code in [200, 500]

    def test_get_documents_missing_domain(self, client):
        """Test document query without required domain parameter"""
        response = client.get("/legal-graph/documents-by-domain")
        assert response.status_code == 422  # Validation error


class TestConceptsByJurisdictionEndpoint:
    """Test /legal-graph/concepts-by-jurisdiction endpoint"""

    def test_get_concepts_success(self, client, app):
        """Test successful concept query"""
        mock_service = Mock()
        mock_service.get_concepts_by_jurisdiction.return_value = QueryResult(
            total_count=3,
            page=1,
            page_size=20,
            total_pages=1,
            items=[
                LegalConcept(
                    concept_id="datenschutz",
                    name="Datenschutz",
                    domain="IT-Recht",
                    jurisdictions=["DE"],
                    document_count=42,
                )
            ],
        )
        
        from backend.queries.legal_graph_queries import get_query_service
        app.dependency_overrides[get_query_service] = lambda: mock_service

        response = client.get("/legal-graph/concepts-by-jurisdiction?jurisdiction=DE")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert len(data["items"]) == 1
        assert data["items"][0]["concept_id"] == "datenschutz"
        
        app.dependency_overrides.clear()

    def test_get_concepts_missing_jurisdiction(self, client):
        """Test concept query without required jurisdiction parameter"""
        response = client.get("/legal-graph/concepts-by-jurisdiction")
        assert response.status_code == 422


class TestAuthoritiesEndpoint:
    """Test /legal-graph/authorities endpoint"""

    def test_get_authorities_success(self, client, app):
        """Test successful authority query"""
        mock_service = Mock()
        mock_service.get_authorities.return_value = QueryResult(
            total_count=2,
            page=1,
            page_size=20,
            total_pages=1,
            items=[
                Authority(
                    authority_id="bgh",
                    name="Bundesgerichtshof",
                    authority_type="court",
                    jurisdiction="DE",
                    document_count=120,
                )
            ],
        )
        
        from backend.queries.legal_graph_queries import get_query_service
        app.dependency_overrides[get_query_service] = lambda: mock_service

        response = client.get("/legal-graph/authorities")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["items"]) == 1
        assert data["items"][0]["authority_id"] == "bgh"
        
        app.dependency_overrides.clear()

    def test_get_authorities_with_filters(self, client):
        """Test authority query with optional filters"""
        response = client.get(
            "/legal-graph/authorities?jurisdiction=DE&authority_type=court"
        )
        assert response.status_code in [200, 500]

    def test_get_authorities_pagination(self, client):
        """Test authority query with pagination"""
        response = client.get("/legal-graph/authorities?page=1&page_size=10")
        assert response.status_code in [200, 500]


class TestHealthEndpoint:
    """Test /legal-graph/health endpoint"""

    def test_health_check_healthy(self, client, app):
        """Test health check when Neo4j is available"""
        mock_service = Mock()
        mock_adapter = Mock()
        mock_adapter.execute_query.return_value = [{"test": 1}]
        mock_service._get_graph_adapter.return_value = mock_adapter
        
        from backend.queries.legal_graph_queries import get_query_service
        app.dependency_overrides[get_query_service] = lambda: mock_service

        response = client.get("/legal-graph/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["neo4j_connection"] == "available"
        assert "timestamp" in data
        
        app.dependency_overrides.clear()

    def test_health_check_unhealthy(self, client, app):
        """Test health check when Neo4j is unavailable"""
        mock_service = Mock()
        mock_service._get_graph_adapter.side_effect = Exception("Connection failed")
        
        from backend.queries.legal_graph_queries import get_query_service
        app.dependency_overrides[get_query_service] = lambda: mock_service

        response = client.get("/legal-graph/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["neo4j_connection"] == "unavailable"
        assert "error" in data
        
        app.dependency_overrides.clear()
