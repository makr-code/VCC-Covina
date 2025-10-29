"""
Legal Analytics Query Endpoints (PostgreSQL-based)

Provides REST API endpoints for simple analytical counts:
- Laws per domain (date range)
- Norms per jurisdiction
- Documents per concept (optionally filtered by domain)

All queries use the UDS3 relational backend via a pluggable adapter.
Tests inject a mock adapter; production can obtain it via UDS3 PolyglotManager
or another gateway. This module does not hard-depend on UDS3 at import time.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import date

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class LawsPerDomainItem(BaseModel):
    domain_id: str
    domain_name: str
    laws_count: int


class NormsPerJurisdictionItem(BaseModel):
    jurisdiction_id: str
    jurisdiction_name: str
    norms_count: int


class DocsPerConceptItem(BaseModel):
    concept_id: str
    concept_name: str
    document_count: int


class QueryResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_count: int
    page: int
    page_size: int
    total_pages: int
    items: List[Any]


class LegalAnalyticsService:
    """Service for analytics queries using a relational adapter.

    The relational adapter is expected to implement execute_query(sql, params) -> list[dict] or similar.
    """

    def __init__(self, relational_adapter: Any = None):
        self._rel = relational_adapter  # Inject in tests; prod can be set via a factory

    def set_relational_adapter(self, adapter: Any) -> None:
        self._rel = adapter

    def _get_rel(self):
        if self._rel is None:
            # Lazy import to avoid hard dependency during tests
            try:
                from uds3.core.polyglot_manager import UDS3PolyglotManager  # type: ignore
                mgr = UDS3PolyglotManager(backend_config={"relational": {"enabled": True}})
                self._rel = mgr.db_manager.get_relational_backend()
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Relational backend unavailable: {e}")
        return self._rel

    def get_laws_per_domain(self, date_from: Optional[str], date_to: Optional[str]) -> List[LawsPerDomainItem]:
        rel = self._get_rel()
        # Simplified SQL; in production use materialized views if available
        sql = (
            "SELECT d.id as domain_id, d.name as domain_name, COUNT(DISTINCT l.id) as laws_count "
            "FROM dim_domain d "
            "LEFT JOIN legal_laws l ON l.domain_id = d.id "
            "WHERE (%(from)s IS NULL OR l.created_at >= %(from)s) AND (%(to)s IS NULL OR l.created_at <= %(to)s) "
            "GROUP BY d.id, d.name ORDER BY laws_count DESC"
        )
        params = {"from": date_from, "to": date_to}
        try:
            rows = rel.execute_query(sql, params) or []
            return [LawsPerDomainItem(**row) for row in rows]
        except Exception as e:
            logger.exception("laws_per_domain_failed")
            raise HTTPException(status_code=500, detail=f"Query failed: {e}")

    def get_norms_per_jurisdiction(self, jurisdiction_id: Optional[str], pagination: PaginationParams) -> QueryResult:
        rel = self._get_rel()
        # Count
        count_sql = (
            "SELECT COUNT(*) as total FROM (") + \
            (
                "SELECT j.id, COUNT(DISTINCT n.id) as norms_count "
                "FROM dim_jurisdiction j "
                "LEFT JOIN legal_norms n ON n.jurisdiction_id = j.id "
                "{where} GROUP BY j.id"
            ) + ") t"
        where = "WHERE j.id = %(jurisdiction_id)s" if jurisdiction_id else ""
        try:
            total_rows = rel.execute_query(count_sql.format(where=where), {"jurisdiction_id": jurisdiction_id}) or []
            total = int(total_rows[0].get("total", 0)) if total_rows else 0
        except Exception as e:
            logger.exception("norms_per_jurisdiction_count_failed")
            raise HTTPException(status_code=500, detail=f"Count failed: {e}")

        # Page
        page_sql = (
            "SELECT j.id as jurisdiction_id, j.name as jurisdiction_name, COUNT(DISTINCT n.id) as norms_count "
            "FROM dim_jurisdiction j "
            "LEFT JOIN legal_norms n ON n.jurisdiction_id = j.id "
            f"{where} "
            "GROUP BY j.id, j.name ORDER BY norms_count DESC LIMIT %(limit)s OFFSET %(offset)s"
        )
        params = {"jurisdiction_id": jurisdiction_id, "limit": pagination.page_size, "offset": pagination.offset}
        try:
            rows = rel.execute_query(page_sql, params) or []
            items = [NormsPerJurisdictionItem(**row) for row in rows]
            total_pages = max(1, (total + pagination.page_size - 1) // pagination.page_size)
            return QueryResult(total_count=total, page=pagination.page, page_size=pagination.page_size, total_pages=total_pages, items=items)
        except Exception as e:
            logger.exception("norms_per_jurisdiction_page_failed")
            raise HTTPException(status_code=500, detail=f"Query failed: {e}")

    def get_docs_per_concept(self, domain_id: Optional[str], pagination: PaginationParams) -> QueryResult:
        rel = self._get_rel()
        where = "WHERE c.domain_id = %(domain_id)s" if domain_id else ""
        # Count
        count_sql = (
            "SELECT COUNT(*) as total FROM ("
            "SELECT c.id, COUNT(DISTINCT d.id) as doc_count FROM dim_concept c "
            "LEFT JOIN doc_concept_link dcl ON dcl.concept_id = c.id "
            "LEFT JOIN documents d ON d.id = dcl.document_id "
            f"{where} GROUP BY c.id"
            ") t"
        )
        try:
            total_rows = rel.execute_query(count_sql, {"domain_id": domain_id}) or []
            total = int(total_rows[0].get("total", 0)) if total_rows else 0
        except Exception as e:
            logger.exception("docs_per_concept_count_failed")
            raise HTTPException(status_code=500, detail=f"Count failed: {e}")

        # Page
        page_sql = (
            "SELECT c.id as concept_id, c.name as concept_name, COUNT(DISTINCT d.id) as document_count "
            "FROM dim_concept c "
            "LEFT JOIN doc_concept_link dcl ON dcl.concept_id = c.id "
            "LEFT JOIN documents d ON d.id = dcl.document_id "
            f"{where} GROUP BY c.id, c.name ORDER BY document_count DESC "
            "LIMIT %(limit)s OFFSET %(offset)s"
        )
        try:
            rows = rel.execute_query(page_sql, {"domain_id": domain_id, "limit": pagination.page_size, "offset": pagination.offset}) or []
            items = [DocsPerConceptItem(**row) for row in rows]
            total_pages = max(1, (total + pagination.page_size - 1) // pagination.page_size)
            return QueryResult(total_count=total, page=pagination.page, page_size=pagination.page_size, total_pages=total_pages, items=items)
        except Exception as e:
            logger.exception("docs_per_concept_page_failed")
            raise HTTPException(status_code=500, detail=f"Query failed: {e}")


# Dependency for DI in tests
def get_service() -> LegalAnalyticsService:
    return LegalAnalyticsService()


router = APIRouter(prefix="/legal-analytics", tags=["legal-analytics"])


@router.get("/laws-per-domain", response_model=List[LawsPerDomainItem])
def laws_per_domain(
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
    service: LegalAnalyticsService = Depends(get_service),
):
    return service.get_laws_per_domain(from_date, to_date)


@router.get("/norms-per-jurisdiction", response_model=QueryResult)
def norms_per_jurisdiction(
    jurisdiction_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: LegalAnalyticsService = Depends(get_service),
):
    return service.get_norms_per_jurisdiction(jurisdiction_id, PaginationParams(page=page, page_size=page_size))


@router.get("/docs-per-concept", response_model=QueryResult)
def docs_per_concept(
    domain_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: LegalAnalyticsService = Depends(get_service),
):
    return service.get_docs_per_concept(domain_id, PaginationParams(page=page, page_size=page_size))
