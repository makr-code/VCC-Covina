"""
VCC Service Base Adapter
Phase 2: VCC Ecosystem Integration

Base class for all VCC service adapters.
Provides common functionality for service communication.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class VCCServiceAdapter(ABC):
    """
    Base adapter for VCC ecosystem services
    
    Provides:
    - HTTP client management
    - Authentication handling
    - Retry logic
    - Error handling
    - Health checks
    """
    
    SERVICE_NAME: str = "base"
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_ssl: bool = True
    ):
        """
        Initialize the adapter
        
        Args:
            base_url: Base URL of the VCC service (on-premise)
            api_key: Optional API key for authentication
            auth_token: Optional bearer token for authentication
            timeout: HTTP request timeout
            max_retries: Maximum retry attempts
            verify_ssl: Verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._last_health_check: Optional[datetime] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            headers = self._build_headers()
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                verify=self.verify_ssl,
                headers=headers
            )
        return self._client
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Service-Name": "covina",
            "X-Request-ID": self._generate_request_id()
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        return headers
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return f"covina-{uuid.uuid4().hex[:12]}"
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connected = False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to VCC service
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request body (for POST/PUT)
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Response data
            
        Raises:
            VCCServiceError: On request failure
        """
        client = await self._get_client()
        
        request_headers = self._build_headers()
        if headers:
            request_headers.update(headers)
        
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
                params=params,
                headers=request_headers
            )
            
            response.raise_for_status()
            
            if response.status_code == 204:
                return {}
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"{self.SERVICE_NAME} request failed: "
                f"{e.response.status_code} - {e.response.text}"
            )
            raise VCCServiceError(
                service=self.SERVICE_NAME,
                message=f"HTTP {e.response.status_code}",
                status_code=e.response.status_code,
                details=e.response.text
            )
        except httpx.RequestError as e:
            logger.error(f"{self.SERVICE_NAME} request error: {e}")
            raise VCCServiceError(
                service=self.SERVICE_NAME,
                message=str(e),
                status_code=None
            )
    
    async def health_check(self) -> bool:
        """
        Check service health
        
        Returns:
            True if service is healthy
        """
        try:
            client = await self._get_client()
            response = await client.get("/health")
            self._connected = response.status_code == 200
            self._last_health_check = datetime.utcnow()
            return self._connected
        except Exception as e:
            logger.warning(f"{self.SERVICE_NAME} health check failed: {e}")
            self._connected = False
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if adapter is connected"""
        return self._connected
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the VCC service
        
        Returns:
            True if connection successful
        """
        pass
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class VCCServiceError(Exception):
    """Exception for VCC service errors"""
    
    def __init__(
        self,
        service: str,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[str] = None
    ):
        self.service = service
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(f"[{service}] {message}")
