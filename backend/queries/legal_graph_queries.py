"""
Legal Knowledge Graph Query Endpoints

Provides REST API endpoints for querying the Legal Knowledge Graph:
- Documents by Legal Domain
- Legal Concepts by Jurisdiction
- Responsible Authorities

All queries use Neo4j via UDS3 Gateway (no direct database connections).
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict

# Import UDS3 Gateway for Neo4j access
from ingestion.infrastructure.clients.uds3_gateway import UDS3Gateway

logger = logging.getLogger(__name__)

# ============================================================================
# Request/Response Models (Pydantic)
# ============================================================================


class PaginationParams(BaseModel):
    """Pagination parameters for all queries"""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def skip(self) -> int:
        """Calculate SKIP value for Cypher queries"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Calculate LIMIT value for Cypher queries"""
        return self.page_size


class DocumentSummary(BaseModel):
    """Summary of a document in Legal Graph"""

    model_config = ConfigDict(from_attributes=True)

    document_id: str = Field(..., description="Unique document identifier")
    file_path: str = Field(..., description="Original file path")
    classification: str = Field(..., description="Document classification")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    domains: List[str] = Field(default_factory=list, description="Legal domains")
    norms_count: int = Field(default=0, description="Number of cited norms")
    concepts_count: int = Field(default=0, description="Number of legal concepts")


class LegalConcept(BaseModel):
    """Legal concept node"""

    model_config = ConfigDict(from_attributes=True)

    concept_id: str = Field(..., description="Normalized concept ID")
    name: str = Field(..., description="Concept name")
    domain: Optional[str] = Field(None, description="Legal domain")
    jurisdictions: List[str] = Field(
        default_factory=list, description="Applicable jurisdictions"
    )
    document_count: int = Field(default=0, description="Documents mentioning concept")


class Authority(BaseModel):
    """Legal authority node"""

    model_config = ConfigDict(from_attributes=True)

    authority_id: str = Field(..., description="Normalized authority ID")
    name: str = Field(..., description="Authority name")
    authority_type: str = Field(..., description="Type (court, agency, etc.)")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction")
    document_count: int = Field(default=0, description="Documents from authority")


class QueryResult(BaseModel):
    """Generic query result with pagination"""

    model_config = ConfigDict(from_attributes=True)

    total_count: int = Field(..., description="Total matching items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    items: List[Any] = Field(..., description="Result items")


# ============================================================================
# Query Service (Business Logic)
# ============================================================================


class LegalGraphQueryService:
    """
    Service for querying Legal Knowledge Graph via Neo4j.

    Uses UDS3Gateway to access Neo4j graph backend.
    All queries are read-only and optimized for pagination.
    """

    def __init__(self):
        self.gateway = UDS3Gateway()
        self._graph_adapter = None
        logger.info("[LegalGraphQueryService] Initialized")

    def _get_graph_adapter(self):
        """Lazy-load Neo4j graph adapter"""
        if self._graph_adapter is None:
            self._graph_adapter = self.gateway.get_graph_adapter()
        return self._graph_adapter

    def get_documents_by_domain(
        self,
        domain: str,
        pagination: PaginationParams,
        include_subdomains: bool = False,
    ) -> QueryResult:
        """
        Query documents by legal domain.

        Args:
            domain: Legal domain name (e.g., "Arbeitsrecht")
            pagination: Pagination parameters
            include_subdomains: If True, include documents from subdomains

        Returns:
            Paginated list of documents
        """
        try:
            adapter = self._get_graph_adapter()

            # Build Cypher query
            if include_subdomains:
                # Match domain and all subdomains
                query = """
                MATCH (domain:LegalDomain {name: $domain})
                OPTIONAL MATCH (domain)<-[:SUBDOMAIN_OF*0..]-(subdomain:LegalDomain)
                WITH COLLECT(DISTINCT COALESCE(subdomain, domain)) AS domains
                UNWIND domains AS d
                MATCH (doc:Document)-[:BELONGS_TO]->(d)
                WITH doc, COLLECT(DISTINCT d.name) AS domain_names
                """
            else:
                # Match exact domain only
                query = """
                MATCH (domain:LegalDomain {name: $domain})
                MATCH (doc:Document)-[:BELONGS_TO]->(domain)
                WITH doc, [domain.name] AS domain_names
                """

            # Add counts for norms and concepts
            query += """
            OPTIONAL MATCH (doc)-[:CITES_NORM]->(norm:LegalNorm)
            WITH doc, domain_names, COUNT(DISTINCT norm) AS norms_count
            OPTIONAL MATCH (doc)-[:MENTIONS_CONCEPT]->(concept:LegalConcept)
            WITH doc, domain_names, norms_count, COUNT(DISTINCT concept) AS concepts_count
            """

            # Count total results
            count_query = query + "RETURN COUNT(DISTINCT doc) AS total"
            count_result = adapter.execute_query(
                count_query,
                {"domain": domain, "skip": 0, "limit": 1},
            )
            total_count = count_result[0]["total"] if count_result else 0

            # Fetch paginated results
            data_query = (
                query
                + """
            RETURN doc.document_id AS document_id,
                   doc.file_path AS file_path,
                   doc.classification AS classification,
                   doc.created_at AS created_at,
                   domain_names,
                   norms_count,
                   concepts_count
            ORDER BY doc.created_at DESC
            SKIP $skip
            LIMIT $limit
            """
            )

            results = adapter.execute_query(
                data_query,
                {
                    "domain": domain,
                    "skip": pagination.skip,
                    "limit": pagination.limit,
                },
            )

            # Map to DocumentSummary objects
            documents = [
                DocumentSummary(
                    document_id=r["document_id"],
                    file_path=r["file_path"],
                    classification=r["classification"],
                    created_at=r.get("created_at"),
                    domains=r["domain_names"],
                    norms_count=r["norms_count"],
                    concepts_count=r["concepts_count"],
                )
                for r in results
            ]

            total_pages = (total_count + pagination.page_size - 1) // pagination.page_size

            return QueryResult(
                total_count=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                items=documents,
            )

        except Exception as e:
            logger.error(f"[ERROR] Query documents by domain failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query documents: {str(e)}"
            )

    def get_concepts_by_jurisdiction(
        self,
        jurisdiction: str,
        pagination: PaginationParams,
    ) -> QueryResult:
        """
        Query legal concepts by jurisdiction.

        Args:
            jurisdiction: Jurisdiction code (e.g., "DE", "EU", "DE-BY")
            pagination: Pagination parameters

        Returns:
            Paginated list of legal concepts
        """
        try:
            adapter = self._get_graph_adapter()

            # Build Cypher query
            query = """
            MATCH (j:Jurisdiction {code: $jurisdiction})
            MATCH (concept:LegalConcept)-[:APPLIES_TO]->(j)
            """

            # Count total results
            count_query = query + "RETURN COUNT(DISTINCT concept) AS total"
            count_result = adapter.execute_query(
                count_query,
                {"jurisdiction": jurisdiction},
            )
            total_count = count_result[0]["total"] if count_result else 0

            # Fetch paginated results with document counts
            data_query = (
                query
                + """
            OPTIONAL MATCH (doc:Document)-[:MENTIONS_CONCEPT]->(concept)
            WITH concept, j, COUNT(DISTINCT doc) AS doc_count
            RETURN concept.concept_id AS concept_id,
                   concept.name AS name,
                   concept.domain AS domain,
                   [j.code] AS jurisdictions,
                   doc_count AS document_count
            ORDER BY doc_count DESC, concept.name ASC
            SKIP $skip
            LIMIT $limit
            """
            )

            results = adapter.execute_query(
                data_query,
                {
                    "jurisdiction": jurisdiction,
                    "skip": pagination.skip,
                    "limit": pagination.limit,
                },
            )

            # Map to LegalConcept objects
            concepts = [
                LegalConcept(
                    concept_id=r["concept_id"],
                    name=r["name"],
                    domain=r.get("domain"),
                    jurisdictions=r["jurisdictions"],
                    document_count=r["document_count"],
                )
                for r in results
            ]

            total_pages = (total_count + pagination.page_size - 1) // pagination.page_size

            return QueryResult(
                total_count=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                items=concepts,
            )

        except Exception as e:
            logger.error(f"[ERROR] Query concepts by jurisdiction failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query concepts: {str(e)}"
            )

    def get_authorities(
        self,
        jurisdiction: Optional[str] = None,
        authority_type: Optional[str] = None,
        pagination: PaginationParams = PaginationParams(),
    ) -> QueryResult:
        """
        Query legal authorities with optional filters.

        Args:
            jurisdiction: Filter by jurisdiction code (optional)
            authority_type: Filter by authority type (optional)
            pagination: Pagination parameters

        Returns:
            Paginated list of authorities
        """
        try:
            adapter = self._get_graph_adapter()

            # Build WHERE clause
            where_clauses = []
            params = {
                "skip": pagination.skip,
                "limit": pagination.limit,
            }

            if jurisdiction:
                where_clauses.append("j.code = $jurisdiction")
                params["jurisdiction"] = jurisdiction

            if authority_type:
                where_clauses.append("a.authority_type = $authority_type")
                params["authority_type"] = authority_type

            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Build Cypher query
            query = f"""
            MATCH (a:Authority)
            OPTIONAL MATCH (a)-[:APPLIES_TO]->(j:Jurisdiction)
            {where_clause}
            """

            # Count total results
            count_query = query + "RETURN COUNT(DISTINCT a) AS total"
            count_result = adapter.execute_query(count_query, params)
            total_count = count_result[0]["total"] if count_result else 0

            # Fetch paginated results with document counts
            data_query = (
                query
                + """
            OPTIONAL MATCH (doc:Document)-[:ISSUED_BY]->(a)
            WITH a, j, COUNT(DISTINCT doc) AS doc_count
            RETURN a.authority_id AS authority_id,
                   a.name AS name,
                   a.authority_type AS authority_type,
                   j.code AS jurisdiction,
                   doc_count AS document_count
            ORDER BY doc_count DESC, a.name ASC
            SKIP $skip
            LIMIT $limit
            """
            )

            results = adapter.execute_query(data_query, params)

            # Map to Authority objects
            authorities = [
                Authority(
                    authority_id=r["authority_id"],
                    name=r["name"],
                    authority_type=r["authority_type"],
                    jurisdiction=r.get("jurisdiction"),
                    document_count=r["document_count"],
                )
                for r in results
            ]

            total_pages = (total_count + pagination.page_size - 1) // pagination.page_size

            return QueryResult(
                total_count=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                items=authorities,
            )

        except Exception as e:
            logger.error(f"[ERROR] Query authorities failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query authorities: {str(e)}"
            )


# ============================================================================
# FastAPI Router (HTTP Layer)
# ============================================================================

router = APIRouter(prefix="/legal-graph", tags=["Legal Knowledge Graph"])

# Singleton service instance
_query_service: Optional[LegalGraphQueryService] = None


def get_query_service() -> LegalGraphQueryService:
    """Dependency injection for query service"""
    global _query_service
    if _query_service is None:
        _query_service = LegalGraphQueryService()
    return _query_service


@router.get(
    "/documents-by-domain",
    response_model=QueryResult,
    summary="Get documents by legal domain",
    description="""
    Query documents belonging to a specific legal domain.
    
    Supports:
    - Exact domain matching
    - Subdomain inclusion (optional)
    - Pagination
    - Counts for norms and concepts per document
    """,
)
def get_documents_by_domain(
    domain: str = Query(..., description="Legal domain name (e.g., 'Arbeitsrecht')"),
    include_subdomains: bool = Query(
        False, description="Include documents from subdomains"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: LegalGraphQueryService = Depends(get_query_service),
) -> QueryResult:
    """Get documents by legal domain"""
    pagination = PaginationParams(page=page, page_size=page_size)
    return service.get_documents_by_domain(domain, pagination, include_subdomains)


@router.get(
    "/concepts-by-jurisdiction",
    response_model=QueryResult,
    summary="Get legal concepts by jurisdiction",
    description="""
    Query legal concepts applicable to a specific jurisdiction.
    
    Results are ordered by:
    1. Document count (most referenced first)
    2. Concept name (alphabetical)
    """,
)
def get_concepts_by_jurisdiction(
    jurisdiction: str = Query(
        ..., description="Jurisdiction code (e.g., 'DE', 'EU', 'DE-BY')"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: LegalGraphQueryService = Depends(get_query_service),
) -> QueryResult:
    """Get legal concepts by jurisdiction"""
    pagination = PaginationParams(page=page, page_size=page_size)
    return service.get_concepts_by_jurisdiction(jurisdiction, pagination)


@router.get(
    "/authorities",
    response_model=QueryResult,
    summary="Get legal authorities",
    description="""
    Query legal authorities with optional filters.
    
    Filters:
    - jurisdiction: Filter by jurisdiction code
    - authority_type: Filter by authority type (court, agency, etc.)
    
    Results include document counts for each authority.
    """,
)
def get_authorities(
    jurisdiction: Optional[str] = Query(
        None, description="Filter by jurisdiction code"
    ),
    authority_type: Optional[str] = Query(None, description="Filter by authority type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: LegalGraphQueryService = Depends(get_query_service),
) -> QueryResult:
    """Get legal authorities with optional filters"""
    pagination = PaginationParams(page=page, page_size=page_size)
    return service.get_authorities(jurisdiction, authority_type, pagination)


# ============================================================================
# Health Check
# ============================================================================


@router.get(
    "/health",
    summary="Legal Graph Query Health Check",
    description="Check if Neo4j connection is available",
)
def health_check(service: LegalGraphQueryService = Depends(get_query_service)) -> Dict[str, Any]:
    """Health check for Legal Graph queries"""
    try:
        adapter = service._get_graph_adapter()
        # Simple connectivity test
        result = adapter.execute_query("RETURN 1 AS test", {})
        
        return {
            "status": "healthy" if result else "degraded",
            "neo4j_connection": "available" if result else "unavailable",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[HEALTH] Neo4j health check failed: {e}")
        return {
            "status": "unhealthy",
            "neo4j_connection": "unavailable",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
