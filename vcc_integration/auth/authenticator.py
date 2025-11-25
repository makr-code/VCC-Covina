"""
VCC Authenticator
Phase 2: VCC Ecosystem Integration

OAuth2/OIDC authenticator for VCC ecosystem.
On-premise deployment - connects to self-hosted identity provider.
"""

import logging
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import httpx
from urllib.parse import urlencode

from .models import VCCUser, VCCRole, AuthenticationResult
from .token_validator import VCCTokenValidator, TokenGenerator

logger = logging.getLogger(__name__)


class VCCAuthenticator:
    """
    OAuth2/OIDC Authenticator for VCC Ecosystem
    
    Provides authentication via:
    - OAuth2 Authorization Code flow
    - OAuth2 Client Credentials flow (service-to-service)
    - Direct username/password authentication (internal use)
    
    On-premise deployment - connects to self-hosted identity provider.
    
    Usage:
        auth = VCCAuthenticator(
            identity_provider_url="http://identity.local:8080",
            client_id="covina",
            client_secret="secret"
        )
        result = await auth.authenticate_user(username, password)
    """
    
    def __init__(
        self,
        identity_provider_url: str = "http://identity-provider.covina.svc.cluster.local:8080",
        client_id: str = "covina",
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scopes: Optional[list] = None,
        token_validator: Optional[VCCTokenValidator] = None,
        token_generator: Optional[TokenGenerator] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the Authenticator
        
        Args:
            identity_provider_url: URL of the on-premise identity provider
            client_id: OAuth2 client ID for Covina
            client_secret: OAuth2 client secret
            redirect_uri: OAuth2 redirect URI
            scopes: OAuth2 scopes to request
            token_validator: Token validator instance
            token_generator: Token generator for local authentication
            timeout: HTTP request timeout
        """
        self.identity_provider_url = identity_provider_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or ["openid", "profile", "email", "roles"]
        self.token_validator = token_validator
        self.token_generator = token_generator
        self.timeout = timeout
        
        # OAuth2 endpoints (standard OIDC discovery)
        self.authorization_endpoint = f"{self.identity_provider_url}/oauth2/authorize"
        self.token_endpoint = f"{self.identity_provider_url}/oauth2/token"
        self.userinfo_endpoint = f"{self.identity_provider_url}/oauth2/userinfo"
        self.introspect_endpoint = f"{self.identity_provider_url}/oauth2/introspect"
        self.revoke_endpoint = f"{self.identity_provider_url}/oauth2/revoke"
        self.jwks_endpoint = f"{self.identity_provider_url}/.well-known/jwks.json"
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def get_authorization_url(
        self,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Get OAuth2 authorization URL for browser redirect
        
        Args:
            state: Optional state parameter (generated if not provided)
            nonce: Optional nonce for OIDC (generated if not provided)
            prompt: Optional prompt parameter (login, consent, etc.)
            
        Returns:
            Tuple of (url, state, nonce)
        """
        state = state or secrets.token_urlsafe(32)
        nonce = nonce or secrets.token_urlsafe(32)
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "nonce": nonce,
        }
        
        if prompt:
            params["prompt"] = prompt
        
        url = f"{self.authorization_endpoint}?{urlencode(params)}"
        return url, state, nonce
    
    async def exchange_code(
        self,
        code: str,
        code_verifier: Optional[str] = None
    ) -> AuthenticationResult:
        """
        Exchange authorization code for tokens
        
        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier (if used)
            
        Returns:
            AuthenticationResult with tokens
        """
        client = await self._get_client()
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        if code_verifier:
            data["code_verifier"] = code_verifier
        
        try:
            response = await client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json()
                return AuthenticationResult(
                    success=False,
                    error_message=error_data.get("error_description", "Token exchange failed"),
                    error_code=error_data.get("error", "token_error")
                )
            
            token_data = response.json()
            
            # Validate and get user from token
            user = None
            if self.token_validator:
                user = self.token_validator.validate_token(token_data["access_token"])
            
            return AuthenticationResult(
                success=True,
                user=user,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in", 3600),
                token_type=token_data.get("token_type", "Bearer")
            )
            
        except httpx.RequestError as e:
            logger.error(f"Token exchange request failed: {e}")
            return AuthenticationResult(
                success=False,
                error_message=str(e),
                error_code="request_error"
            )
    
    async def authenticate_client_credentials(
        self,
        scopes: Optional[list] = None
    ) -> AuthenticationResult:
        """
        Authenticate using client credentials (service-to-service)
        
        Args:
            scopes: OAuth2 scopes to request
            
        Returns:
            AuthenticationResult with service token
        """
        client = await self._get_client()
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "scope": " ".join(scopes or self.scopes),
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        try:
            response = await client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json()
                return AuthenticationResult(
                    success=False,
                    error_message=error_data.get("error_description", "Authentication failed"),
                    error_code=error_data.get("error", "auth_error")
                )
            
            token_data = response.json()
            
            # Build service user
            user = VCCUser(
                user_id=self.client_id,
                username=self.client_id,
                roles=[VCCRole.SERVICE],
                is_service_account=True
            )
            
            return AuthenticationResult(
                success=True,
                user=user,
                access_token=token_data["access_token"],
                expires_in=token_data.get("expires_in", 3600),
                token_type=token_data.get("token_type", "Bearer")
            )
            
        except httpx.RequestError as e:
            logger.error(f"Client credentials request failed: {e}")
            return AuthenticationResult(
                success=False,
                error_message=str(e),
                error_code="request_error"
            )
    
    async def authenticate_user(
        self,
        username: str,
        password: str
    ) -> AuthenticationResult:
        """
        Authenticate user with username and password
        
        Uses Resource Owner Password Credentials grant.
        Note: This should only be used for trusted applications.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            AuthenticationResult with tokens
        """
        client = await self._get_client()
        
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": username,
            "password": password,
            "scope": " ".join(self.scopes),
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        try:
            response = await client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json()
                return AuthenticationResult(
                    success=False,
                    error_message=error_data.get("error_description", "Authentication failed"),
                    error_code=error_data.get("error", "auth_error")
                )
            
            token_data = response.json()
            
            # Validate and get user from token
            user = None
            if self.token_validator:
                user = self.token_validator.validate_token(token_data["access_token"])
            
            return AuthenticationResult(
                success=True,
                user=user,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in", 3600),
                token_type=token_data.get("token_type", "Bearer")
            )
            
        except httpx.RequestError as e:
            logger.error(f"User authentication request failed: {e}")
            return AuthenticationResult(
                success=False,
                error_message=str(e),
                error_code="request_error"
            )
    
    async def refresh_token(self, refresh_token: str) -> AuthenticationResult:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            AuthenticationResult with new tokens
        """
        client = await self._get_client()
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        try:
            response = await client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json()
                return AuthenticationResult(
                    success=False,
                    error_message=error_data.get("error_description", "Token refresh failed"),
                    error_code=error_data.get("error", "refresh_error")
                )
            
            token_data = response.json()
            
            # Validate and get user from token
            user = None
            if self.token_validator:
                user = self.token_validator.validate_token(token_data["access_token"])
            
            return AuthenticationResult(
                success=True,
                user=user,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", refresh_token),
                expires_in=token_data.get("expires_in", 3600),
                token_type=token_data.get("token_type", "Bearer")
            )
            
        except httpx.RequestError as e:
            logger.error(f"Token refresh request failed: {e}")
            return AuthenticationResult(
                success=False,
                error_message=str(e),
                error_code="request_error"
            )
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user info from identity provider
        
        Args:
            access_token: Valid access token
            
        Returns:
            User info dict or None
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except httpx.RequestError as e:
            logger.error(f"User info request failed: {e}")
            return None
    
    async def revoke_token(self, token: str, token_type: str = "access_token") -> bool:
        """
        Revoke a token
        
        Args:
            token: Token to revoke
            token_type: Type of token (access_token or refresh_token)
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        data = {
            "token": token,
            "token_type_hint": token_type,
            "client_id": self.client_id,
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        try:
            response = await client.post(
                self.revoke_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            return response.status_code == 200
            
        except httpx.RequestError as e:
            logger.error(f"Token revocation request failed: {e}")
            return False
    
    async def introspect_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Introspect a token (get token info from identity provider)
        
        Args:
            token: Token to introspect
            
        Returns:
            Token info or None
        """
        client = await self._get_client()
        
        data = {
            "token": token,
            "client_id": self.client_id,
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        try:
            response = await client.post(
                self.introspect_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except httpx.RequestError as e:
            logger.error(f"Token introspection request failed: {e}")
            return None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
