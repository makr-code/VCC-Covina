"""
Argus Adapter
Phase 2: VCC Ecosystem Integration

Adapter for Argus Media Management Service.
Provides media asset management, format conversion, and content moderation.

On-premise deployment - connects to self-hosted Argus service.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from .base_adapter import VCCServiceAdapter, VCCServiceError

logger = logging.getLogger(__name__)


# Argus Data Models

class MediaAsset(BaseModel):
    """Media asset information"""
    asset_id: str
    filename: str
    mime_type: str
    file_size: int
    checksum: str
    storage_url: str
    thumbnail_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversionJob(BaseModel):
    """Media conversion job"""
    job_id: str
    source_asset_id: str
    target_format: str
    status: str = "pending"  # pending, processing, completed, failed
    progress: int = 0
    result_asset_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class ModerationResult(BaseModel):
    """Content moderation result"""
    asset_id: str
    is_safe: bool
    categories: Dict[str, float] = Field(default_factory=dict)
    flagged_content: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class ArgusAdapter(VCCServiceAdapter):
    """
    Adapter for Argus Media Management Service
    
    Argus provides:
    - Media asset storage and retrieval
    - Format conversion
    - Thumbnail generation
    - Content moderation
    - Metadata extraction
    
    Usage:
        async with ArgusAdapter(
            base_url="http://argus.local:8080"
        ) as argus:
            asset = await argus.upload_asset(file_content, filename)
    """
    
    SERVICE_NAME = "argus"
    
    def __init__(
        self,
        base_url: str = "http://argus-service.covina.svc.cluster.local:8080",
        **kwargs
    ):
        """
        Initialize Argus adapter
        
        Args:
            base_url: Argus service URL (on-premise)
            **kwargs: Additional adapter configuration
        """
        super().__init__(base_url=base_url, **kwargs)
        self._supported_formats: Dict[str, List[str]] = {}
        self._storage_quota: Optional[int] = None
    
    async def connect(self) -> bool:
        """Connect to Argus service"""
        try:
            healthy = await self.health_check()
            if healthy:
                # Load service capabilities
                capabilities = await self._request("GET", "/api/v1/capabilities")
                self._supported_formats = capabilities.get("formats", {})
                self._storage_quota = capabilities.get("storage_quota")
                logger.info(f"Connected to Argus: {self.base_url}")
            return healthy
        except Exception as e:
            logger.error(f"Failed to connect to Argus: {e}")
            return False
    
    async def upload_asset(
        self,
        content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MediaAsset:
        """
        Upload a media asset
        
        Args:
            content: File content as bytes
            filename: Original filename
            mime_type: MIME type (auto-detected if not provided)
            metadata: Additional metadata
            
        Returns:
            Created media asset
        """
        import base64
        
        data = {
            "filename": filename,
            "content": base64.b64encode(content).decode(),
            "mime_type": mime_type,
            "metadata": metadata or {},
            "source_service": "covina"
        }
        
        result = await self._request("POST", "/api/v1/assets", data=data)
        
        return MediaAsset(**result)
    
    async def get_asset(
        self,
        asset_id: str
    ) -> Optional[MediaAsset]:
        """
        Get asset information
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            MediaAsset or None
        """
        try:
            result = await self._request("GET", f"/api/v1/assets/{asset_id}")
            return MediaAsset(**result)
        except VCCServiceError as e:
            if e.status_code == 404:
                return None
            raise
    
    async def download_asset(
        self,
        asset_id: str
    ) -> bytes:
        """
        Download asset content
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            File content as bytes
        """
        import base64
        
        result = await self._request("GET", f"/api/v1/assets/{asset_id}/download")
        return base64.b64decode(result.get("content", ""))
    
    async def delete_asset(
        self,
        asset_id: str
    ) -> bool:
        """
        Delete an asset
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            True if deleted
        """
        await self._request("DELETE", f"/api/v1/assets/{asset_id}")
        return True
    
    async def convert_format(
        self,
        asset_id: str,
        target_format: str,
        options: Optional[Dict[str, Any]] = None
    ) -> ConversionJob:
        """
        Convert asset to different format
        
        Args:
            asset_id: Source asset ID
            target_format: Target format (e.g., 'pdf', 'png', 'mp4')
            options: Conversion options
            
        Returns:
            Conversion job
        """
        data = {
            "source_asset_id": asset_id,
            "target_format": target_format,
            "options": options or {}
        }
        
        result = await self._request("POST", "/api/v1/convert", data=data)
        
        return ConversionJob(**result)
    
    async def get_conversion_status(
        self,
        job_id: str
    ) -> ConversionJob:
        """
        Get conversion job status
        
        Args:
            job_id: Job identifier
            
        Returns:
            Conversion job with current status
        """
        result = await self._request("GET", f"/api/v1/convert/{job_id}")
        return ConversionJob(**result)
    
    async def generate_thumbnail(
        self,
        asset_id: str,
        width: int = 200,
        height: int = 200
    ) -> str:
        """
        Generate thumbnail for asset
        
        Args:
            asset_id: Asset identifier
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            Thumbnail URL
        """
        data = {
            "width": width,
            "height": height
        }
        
        result = await self._request(
            "POST",
            f"/api/v1/assets/{asset_id}/thumbnail",
            data=data
        )
        
        return result.get("thumbnail_url", "")
    
    async def moderate_content(
        self,
        asset_id: str,
        categories: Optional[List[str]] = None
    ) -> ModerationResult:
        """
        Perform content moderation
        
        Args:
            asset_id: Asset identifier
            categories: Moderation categories to check
            
        Returns:
            Moderation result
        """
        data = {
            "categories": categories or [
                "violence", "adult", "hate_speech", "self_harm"
            ]
        }
        
        result = await self._request(
            "POST",
            f"/api/v1/assets/{asset_id}/moderate",
            data=data
        )
        
        return ModerationResult(
            asset_id=asset_id,
            is_safe=result.get("is_safe", True),
            categories=result.get("categories", {}),
            flagged_content=result.get("flagged_content", []),
            confidence=result.get("confidence", 0.0)
        )
    
    async def extract_metadata(
        self,
        asset_id: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from media asset
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            Extracted metadata
        """
        result = await self._request(
            "GET",
            f"/api/v1/assets/{asset_id}/metadata"
        )
        
        return result.get("metadata", {})
    
    async def search_assets(
        self,
        query: Optional[str] = None,
        mime_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[MediaAsset]:
        """
        Search for media assets
        
        Args:
            query: Search query
            mime_type: Filter by MIME type
            tags: Filter by tags
            created_after: Filter by creation date
            created_before: Filter by creation date
            page: Page number
            page_size: Results per page
            
        Returns:
            List of matching assets
        """
        params = {
            "q": query,
            "mime_type": mime_type,
            "tags": ",".join(tags) if tags else None,
            "created_after": created_after.isoformat() if created_after else None,
            "created_before": created_before.isoformat() if created_before else None,
            "page": page,
            "page_size": page_size
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        result = await self._request("GET", "/api/v1/assets", params=params)
        
        return [MediaAsset(**a) for a in result.get("assets", [])]
    
    async def update_metadata(
        self,
        asset_id: str,
        metadata: Dict[str, Any]
    ) -> MediaAsset:
        """
        Update asset metadata
        
        Args:
            asset_id: Asset identifier
            metadata: New metadata
            
        Returns:
            Updated asset
        """
        result = await self._request(
            "PATCH",
            f"/api/v1/assets/{asset_id}/metadata",
            data={"metadata": metadata}
        )
        
        return MediaAsset(**result)
    
    @property
    def supported_formats(self) -> Dict[str, List[str]]:
        """Get supported format conversions"""
        return self._supported_formats
    
    @property
    def storage_quota(self) -> Optional[int]:
        """Get storage quota in bytes"""
        return self._storage_quota
