"""
Handelsregister API Client - Minimal Re-Implementation
Restored: 16. Oktober 2025
Status: STUB ONLY (API calls disabled)
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class HandelsregisterClient:
    """
    Handelsregister API Client
    
    MINIMAL RE-IMPLEMENTATION:
    - Provides API stubs for backend compatibility
    - Actual API calls DISABLED (awaiting full restore)
    """
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize Handelsregister client
        
        Args:
            api_key: API authentication key (optional)
            api_url: API endpoint URL (optional)
        """
        self.api_key = api_key
        self.api_url = api_url or "https://handelsregister.de/api"
        self.is_available = False
        logger.warning("⚠️ HandelsregisterClient initialized in STUB mode")
    
    async def search_company(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Search for company by name (STUB - returns None)
        
        Args:
            name: Company name
            
        Returns:
            None (STUB implementation)
        """
        logger.warning(f"⚠️ search_company called in STUB mode: {name}")
        return None
    
    async def get_company_details(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Get company details by ID (STUB - returns None)
        
        Args:
            company_id: Company registration ID
            
        Returns:
            None (STUB implementation)
        """
        logger.warning(f"⚠️ get_company_details called in STUB mode: {company_id}")
        return None
    
    def is_available(self) -> bool:
        """Check if service is available (STUB - returns False)"""
        return False
    
    @property
    def status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "available": False,
            "mode": "STUB",
            "api_url": self.api_url,
            "message": "Minimal re-implementation - awaiting full restore"
        }


class CompanyExtractor:
    """
    Company Entity Extractor from Documents
    
    MINIMAL RE-IMPLEMENTATION:
    - Stub for NLP-based company extraction
    """
    
    def __init__(self):
        logger.warning("⚠️ CompanyExtractor initialized in STUB mode")
    
    def extract_companies(self, text: str) -> List[str]:
        """
        Extract company names from text (STUB - returns empty list)
        
        Args:
            text: Document text
            
        Returns:
            Empty list (STUB implementation)
        """
        logger.warning("⚠️ extract_companies called in STUB mode")
        return []


class CompanyEntity:
    """
    Company Entity Data Model
    
    MINIMAL RE-IMPLEMENTATION:
    - Basic data structure only
    """
    
    def __init__(self, name: str, registration_id: Optional[str] = None):
        self.name = name
        self.registration_id = registration_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "registration_id": self.registration_id
        }


# Compatibility exports
__all__ = ["HandelsregisterClient", "CompanyExtractor", "CompanyEntity"]
