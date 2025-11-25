"""
Clara Adapter
Phase 2: VCC Ecosystem Integration

Adapter for Clara Document Intelligence Service.
Provides document classification, parsing, and metadata extraction.

On-premise deployment - connects to self-hosted Clara service.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from .base_adapter import VCCServiceAdapter, VCCServiceError

logger = logging.getLogger(__name__)


# Clara Data Models

class DocumentClassification(BaseModel):
    """Document classification result"""
    document_id: str
    primary_class: str
    confidence: float
    secondary_classes: List[Dict[str, float]] = Field(default_factory=list)
    model_version: str = "1.0"
    processing_time_ms: int = 0


class ExtractedMetadata(BaseModel):
    """Extracted document metadata"""
    document_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    language: str = "de"
    page_count: int = 0
    word_count: int = 0
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class StructuredContent(BaseModel):
    """Structured document content"""
    document_id: str
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    figures: List[Dict[str, Any]] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    footnotes: List[str] = Field(default_factory=list)


class ClaraProcessingResult(BaseModel):
    """Complete Clara processing result"""
    document_id: str
    classification: Optional[DocumentClassification] = None
    metadata: Optional[ExtractedMetadata] = None
    structure: Optional[StructuredContent] = None
    processing_status: str = "completed"
    total_processing_time_ms: int = 0
    errors: List[str] = Field(default_factory=list)


class ClaraAdapter(VCCServiceAdapter):
    """
    Adapter for Clara Document Intelligence Service
    
    Clara provides:
    - Document classification
    - Metadata extraction
    - Structured content parsing
    - Language detection
    - Text summarization
    
    Usage:
        async with ClaraAdapter(
            base_url="http://clara.local:8080"
        ) as clara:
            result = await clara.process_document(doc_id, content)
    """
    
    SERVICE_NAME = "clara"
    
    def __init__(
        self,
        base_url: str = "http://clara-service.covina.svc.cluster.local:8080",
        **kwargs
    ):
        """
        Initialize Clara adapter
        
        Args:
            base_url: Clara service URL (on-premise)
            **kwargs: Additional adapter configuration
        """
        super().__init__(base_url=base_url, **kwargs)
        self._available_classifiers: List[str] = []
        self._supported_formats: List[str] = []
    
    async def connect(self) -> bool:
        """Connect to Clara service"""
        try:
            healthy = await self.health_check()
            if healthy:
                # Load service capabilities
                capabilities = await self._request("GET", "/api/v1/capabilities")
                self._available_classifiers = capabilities.get("classifiers", [])
                self._supported_formats = capabilities.get("formats", [])
                logger.info(f"Connected to Clara: {self.base_url}")
            return healthy
        except Exception as e:
            logger.error(f"Failed to connect to Clara: {e}")
            return False
    
    async def process_document(
        self,
        document_id: str,
        content: str,
        file_type: str = "text/plain",
        processing_options: Optional[Dict[str, Any]] = None
    ) -> ClaraProcessingResult:
        """
        Process document with all Clara capabilities
        
        Args:
            document_id: Document identifier
            content: Document content (text or base64 for binary)
            file_type: MIME type of the document
            processing_options: Additional processing options
            
        Returns:
            Complete processing result
        """
        data = {
            "document_id": document_id,
            "content": content,
            "file_type": file_type,
            "options": processing_options or {
                "classify": True,
                "extract_metadata": True,
                "parse_structure": True,
                "summarize": True
            }
        }
        
        result = await self._request("POST", "/api/v1/process", data=data)
        
        return ClaraProcessingResult(
            document_id=document_id,
            classification=DocumentClassification(**result["classification"]) 
                if result.get("classification") else None,
            metadata=ExtractedMetadata(**result["metadata"]) 
                if result.get("metadata") else None,
            structure=StructuredContent(**result["structure"]) 
                if result.get("structure") else None,
            processing_status=result.get("status", "completed"),
            total_processing_time_ms=result.get("processing_time_ms", 0),
            errors=result.get("errors", [])
        )
    
    async def classify_document(
        self,
        document_id: str,
        content: str,
        classifier: str = "default",
        top_k: int = 5
    ) -> DocumentClassification:
        """
        Classify a document
        
        Args:
            document_id: Document identifier
            content: Document text content
            classifier: Classifier model to use
            top_k: Number of top classes to return
            
        Returns:
            Classification result
        """
        data = {
            "document_id": document_id,
            "content": content,
            "classifier": classifier,
            "top_k": top_k
        }
        
        result = await self._request("POST", "/api/v1/classify", data=data)
        
        return DocumentClassification(
            document_id=document_id,
            primary_class=result.get("primary_class", "unknown"),
            confidence=result.get("confidence", 0.0),
            secondary_classes=result.get("secondary_classes", []),
            model_version=result.get("model_version", "1.0"),
            processing_time_ms=result.get("processing_time_ms", 0)
        )
    
    async def extract_metadata(
        self,
        document_id: str,
        content: str,
        file_type: str = "text/plain"
    ) -> ExtractedMetadata:
        """
        Extract metadata from document
        
        Args:
            document_id: Document identifier
            content: Document content
            file_type: MIME type
            
        Returns:
            Extracted metadata
        """
        data = {
            "document_id": document_id,
            "content": content,
            "file_type": file_type
        }
        
        result = await self._request("POST", "/api/v1/metadata/extract", data=data)
        
        return ExtractedMetadata(
            document_id=document_id,
            title=result.get("title"),
            author=result.get("author"),
            creation_date=datetime.fromisoformat(result["creation_date"]) 
                if result.get("creation_date") else None,
            language=result.get("language", "de"),
            page_count=result.get("page_count", 0),
            word_count=result.get("word_count", 0),
            entities=result.get("entities", []),
            keywords=result.get("keywords", []),
            summary=result.get("summary"),
            custom_fields=result.get("custom_fields", {})
        )
    
    async def parse_structure(
        self,
        document_id: str,
        content: str,
        file_type: str = "text/plain"
    ) -> StructuredContent:
        """
        Parse document structure
        
        Args:
            document_id: Document identifier
            content: Document content
            file_type: MIME type
            
        Returns:
            Structured content
        """
        data = {
            "document_id": document_id,
            "content": content,
            "file_type": file_type
        }
        
        result = await self._request("POST", "/api/v1/structure/parse", data=data)
        
        return StructuredContent(
            document_id=document_id,
            sections=result.get("sections", []),
            tables=result.get("tables", []),
            figures=result.get("figures", []),
            references=result.get("references", []),
            footnotes=result.get("footnotes", [])
        )
    
    async def detect_language(
        self,
        content: str
    ) -> Dict[str, Any]:
        """
        Detect document language
        
        Args:
            content: Text content
            
        Returns:
            Language detection result
        """
        data = {"content": content}
        return await self._request("POST", "/api/v1/language/detect", data=data)
    
    async def summarize(
        self,
        content: str,
        max_length: int = 200,
        style: str = "abstractive"
    ) -> str:
        """
        Generate document summary
        
        Args:
            content: Document content
            max_length: Maximum summary length (words)
            style: Summary style (abstractive/extractive)
            
        Returns:
            Summary text
        """
        data = {
            "content": content,
            "max_length": max_length,
            "style": style
        }
        
        result = await self._request("POST", "/api/v1/summarize", data=data)
        return result.get("summary", "")
    
    async def harmonize_metadata(
        self,
        source_metadata: Dict[str, Any],
        target_schema: str = "covina"
    ) -> Dict[str, Any]:
        """
        Harmonize metadata to target schema
        
        Args:
            source_metadata: Source metadata
            target_schema: Target schema name
            
        Returns:
            Harmonized metadata
        """
        data = {
            "metadata": source_metadata,
            "target_schema": target_schema
        }
        
        result = await self._request("POST", "/api/v1/metadata/harmonize", data=data)
        return result.get("harmonized", {})
    
    @property
    def available_classifiers(self) -> List[str]:
        """Get available classifiers"""
        return self._available_classifiers
    
    @property
    def supported_formats(self) -> List[str]:
        """Get supported file formats"""
        return self._supported_formats
