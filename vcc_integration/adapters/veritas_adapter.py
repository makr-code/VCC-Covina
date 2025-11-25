"""
VERITAS Adapter
Phase 2: VCC Ecosystem Integration

Adapter for VERITAS Legal Intelligence Service.
Provides legal reference extraction, entity recognition, and compliance checks.

On-premise deployment - connects to self-hosted VERITAS service.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from .base_adapter import VCCServiceAdapter, VCCServiceError

logger = logging.getLogger(__name__)


# VERITAS Data Models

class LegalReference(BaseModel):
    """Legal reference identified in document"""
    reference_id: str
    reference_type: str  # law, regulation, court_decision, directive
    citation: str
    full_title: Optional[str] = None
    jurisdiction: str = "DE"  # ISO country code
    effective_date: Optional[datetime] = None
    relevance_score: float = 0.0
    context: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LegalEntity(BaseModel):
    """Legal entity identified in document"""
    entity_id: str
    entity_type: str  # person, organization, court, authority
    name: str
    normalized_name: Optional[str] = None
    role: Optional[str] = None
    confidence: float = 0.0
    positions: List[Dict[str, int]] = Field(default_factory=list)  # [{start, end}]


class ComplianceFinding(BaseModel):
    """Compliance finding from VERITAS analysis"""
    finding_id: str
    finding_type: str  # violation, warning, recommendation
    severity: str  # critical, high, medium, low, info
    regulation: str
    description: str
    affected_text: Optional[str] = None
    recommendation: Optional[str] = None
    deadline: Optional[datetime] = None


class VeritasAnalysisResult(BaseModel):
    """Complete VERITAS analysis result"""
    request_id: str
    document_id: str
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: int = 0
    legal_references: List[LegalReference] = Field(default_factory=list)
    entities: List[LegalEntity] = Field(default_factory=list)
    compliance_findings: List[ComplianceFinding] = Field(default_factory=list)
    summary: Optional[str] = None
    risk_score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VeritasAdapter(VCCServiceAdapter):
    """
    Adapter for VERITAS Legal Intelligence Service
    
    VERITAS provides:
    - Legal reference extraction (laws, regulations, court decisions)
    - Named Entity Recognition for legal entities
    - Compliance checking against regulatory requirements
    - Legal document summarization
    
    Usage:
        async with VeritasAdapter(
            base_url="http://veritas.local:8080"
        ) as veritas:
            result = await veritas.analyze_document(doc_id, content)
    """
    
    SERVICE_NAME = "veritas"
    
    def __init__(
        self,
        base_url: str = "http://veritas-service.covina.svc.cluster.local:8080",
        **kwargs
    ):
        """
        Initialize VERITAS adapter
        
        Args:
            base_url: VERITAS service URL (on-premise)
            **kwargs: Additional adapter configuration
        """
        super().__init__(base_url=base_url, **kwargs)
        self._supported_jurisdictions: List[str] = []
        self._available_models: List[str] = []
    
    async def connect(self) -> bool:
        """Connect to VERITAS service"""
        try:
            healthy = await self.health_check()
            if healthy:
                # Load service capabilities
                capabilities = await self._request("GET", "/api/v1/capabilities")
                self._supported_jurisdictions = capabilities.get("jurisdictions", ["DE"])
                self._available_models = capabilities.get("models", [])
                logger.info(f"Connected to VERITAS: {self.base_url}")
            return healthy
        except Exception as e:
            logger.error(f"Failed to connect to VERITAS: {e}")
            return False
    
    async def analyze_document(
        self,
        document_id: str,
        content: str,
        jurisdiction: str = "DE",
        analysis_types: Optional[List[str]] = None,
        include_summary: bool = True
    ) -> VeritasAnalysisResult:
        """
        Perform comprehensive legal analysis on a document
        
        Args:
            document_id: Document identifier
            content: Document text content
            jurisdiction: Legal jurisdiction (default: DE)
            analysis_types: Types of analysis to perform
            include_summary: Include document summary
            
        Returns:
            VeritasAnalysisResult with all findings
        """
        analysis_types = analysis_types or [
            "legal_references",
            "entities",
            "compliance"
        ]
        
        data = {
            "document_id": document_id,
            "content": content,
            "jurisdiction": jurisdiction,
            "analysis_types": analysis_types,
            "include_summary": include_summary,
            "options": {
                "language": "de",
                "max_references": 100,
                "min_confidence": 0.5
            }
        }
        
        result = await self._request("POST", "/api/v1/analyze", data=data)
        
        return VeritasAnalysisResult(
            request_id=result.get("request_id", ""),
            document_id=document_id,
            processing_time_ms=result.get("processing_time_ms", 0),
            legal_references=[
                LegalReference(**ref) for ref in result.get("legal_references", [])
            ],
            entities=[
                LegalEntity(**ent) for ent in result.get("entities", [])
            ],
            compliance_findings=[
                ComplianceFinding(**f) for f in result.get("compliance_findings", [])
            ],
            summary=result.get("summary"),
            risk_score=result.get("risk_score", 0.0),
            metadata=result.get("metadata", {})
        )
    
    async def extract_legal_references(
        self,
        content: str,
        jurisdiction: str = "DE",
        reference_types: Optional[List[str]] = None
    ) -> List[LegalReference]:
        """
        Extract legal references from text
        
        Args:
            content: Text content to analyze
            jurisdiction: Legal jurisdiction
            reference_types: Filter by reference types
            
        Returns:
            List of legal references
        """
        data = {
            "content": content,
            "jurisdiction": jurisdiction,
            "reference_types": reference_types or ["law", "regulation", "directive"]
        }
        
        result = await self._request("POST", "/api/v1/references/extract", data=data)
        
        return [
            LegalReference(**ref) for ref in result.get("references", [])
        ]
    
    async def recognize_entities(
        self,
        content: str,
        entity_types: Optional[List[str]] = None
    ) -> List[LegalEntity]:
        """
        Recognize legal entities in text
        
        Args:
            content: Text content to analyze
            entity_types: Filter by entity types
            
        Returns:
            List of recognized entities
        """
        data = {
            "content": content,
            "entity_types": entity_types or ["person", "organization", "court"]
        }
        
        result = await self._request("POST", "/api/v1/entities/recognize", data=data)
        
        return [
            LegalEntity(**ent) for ent in result.get("entities", [])
        ]
    
    async def check_compliance(
        self,
        document_id: str,
        content: str,
        regulations: Optional[List[str]] = None,
        check_level: str = "standard"
    ) -> List[ComplianceFinding]:
        """
        Check document compliance against regulations
        
        Args:
            document_id: Document identifier
            content: Document content
            regulations: Specific regulations to check (default: all applicable)
            check_level: Check thoroughness (quick, standard, thorough)
            
        Returns:
            List of compliance findings
        """
        data = {
            "document_id": document_id,
            "content": content,
            "regulations": regulations,
            "check_level": check_level
        }
        
        result = await self._request("POST", "/api/v1/compliance/check", data=data)
        
        return [
            ComplianceFinding(**f) for f in result.get("findings", [])
        ]
    
    async def resolve_reference(
        self,
        citation: str,
        jurisdiction: str = "DE"
    ) -> Optional[LegalReference]:
        """
        Resolve a legal citation to full reference details
        
        Args:
            citation: Legal citation string
            jurisdiction: Legal jurisdiction
            
        Returns:
            Resolved legal reference or None
        """
        data = {
            "citation": citation,
            "jurisdiction": jurisdiction
        }
        
        try:
            result = await self._request("POST", "/api/v1/references/resolve", data=data)
            if result.get("reference"):
                return LegalReference(**result["reference"])
        except VCCServiceError as e:
            if e.status_code == 404:
                return None
            raise
        
        return None
    
    async def get_regulation_info(
        self,
        regulation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a regulation
        
        Args:
            regulation_id: Regulation identifier
            
        Returns:
            Regulation details or None
        """
        try:
            return await self._request("GET", f"/api/v1/regulations/{regulation_id}")
        except VCCServiceError as e:
            if e.status_code == 404:
                return None
            raise
    
    async def search_regulations(
        self,
        query: str,
        jurisdiction: str = "DE",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for regulations
        
        Args:
            query: Search query
            jurisdiction: Legal jurisdiction
            limit: Maximum results
            
        Returns:
            List of matching regulations
        """
        params = {
            "q": query,
            "jurisdiction": jurisdiction,
            "limit": limit
        }
        
        result = await self._request("GET", "/api/v1/regulations/search", params=params)
        
        return result.get("results", [])
    
    @property
    def supported_jurisdictions(self) -> List[str]:
        """Get supported jurisdictions"""
        return self._supported_jurisdictions
    
    @property
    def available_models(self) -> List[str]:
        """Get available analysis models"""
        return self._available_models
