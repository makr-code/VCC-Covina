"""
VCC Token Validator
Phase 2: VCC Ecosystem Integration

JWT token validation for VCC ecosystem.
Supports both user tokens and service-to-service tokens.
On-premise deployment - no external identity provider dependency.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from .models import VCCTokenPayload, VCCUser, VCCRole, VCCPermission, ROLE_PERMISSIONS

logger = logging.getLogger(__name__)


class VCCTokenValidator:
    """
    JWT Token Validator for VCC Ecosystem
    
    Validates JWT tokens issued by the VCC identity provider.
    Supports RS256 (asymmetric) and HS256 (symmetric) algorithms.
    
    Usage:
        validator = VCCTokenValidator(
            public_key="...",
            issuer="vcc-identity-provider"
        )
        user = validator.validate_token(token)
    """
    
    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        issuer: str = "vcc-identity-provider",
        audience: str = "vcc-ecosystem",
        algorithms: List[str] = None,
        leeway: int = 30,  # seconds
        jwks_uri: Optional[str] = None
    ):
        """
        Initialize the Token Validator
        
        Args:
            public_key: RSA public key for RS256 (PEM format)
            secret_key: Secret key for HS256
            issuer: Expected token issuer
            audience: Expected token audience
            algorithms: Allowed algorithms (default: RS256, HS256)
            leeway: Clock skew tolerance in seconds
            jwks_uri: JWKS endpoint for key rotation (on-premise)
        """
        self.public_key = public_key
        self.secret_key = secret_key
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms or ["RS256", "HS256"]
        self.leeway = leeway
        self.jwks_uri = jwks_uri
        
        # Parse public key if provided
        self._parsed_public_key = None
        if public_key:
            try:
                self._parsed_public_key = serialization.load_pem_public_key(
                    public_key.encode(),
                    backend=default_backend()
                )
            except Exception as e:
                logger.warning(f"Failed to parse public key: {e}")
    
    def _get_verification_key(self, algorithm: str) -> Any:
        """Get the appropriate key for verification"""
        if algorithm.startswith("RS"):
            if self._parsed_public_key:
                return self._parsed_public_key
            elif self.public_key:
                return self.public_key
            else:
                raise ValueError("Public key required for RS* algorithms")
        elif algorithm.startswith("HS"):
            if self.secret_key:
                return self.secret_key
            else:
                raise ValueError("Secret key required for HS* algorithms")
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def validate_token(
        self,
        token: str,
        verify_exp: bool = True,
        required_permissions: Optional[List[VCCPermission]] = None
    ) -> Optional[VCCUser]:
        """
        Validate a JWT token and return the user
        
        Args:
            token: JWT token string
            verify_exp: Whether to verify expiration
            required_permissions: Optional permissions to check
            
        Returns:
            VCCUser if valid, None if invalid
            
        Raises:
            jwt.InvalidTokenError: If token validation fails
        """
        try:
            # Determine key based on token header
            unverified_header = jwt.get_unverified_header(token)
            algorithm = unverified_header.get('alg', 'RS256')
            
            if algorithm not in self.algorithms:
                logger.warning(f"Unsupported algorithm: {algorithm}")
                return None
            
            key = self._get_verification_key(algorithm)
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                issuer=self.issuer,
                audience=self.audience,
                leeway=self.leeway,
                options={"verify_exp": verify_exp}
            )
            
            # Parse payload
            token_payload = VCCTokenPayload(**payload)
            
            # Build user from token
            user = self._build_user_from_payload(token_payload)
            
            # Check required permissions
            if required_permissions:
                if not user.has_all_permissions(required_permissions):
                    logger.warning(
                        f"User {user.user_id} lacks required permissions: "
                        f"{required_permissions}"
                    )
                    return None
            
            return user
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    def _build_user_from_payload(self, payload: VCCTokenPayload) -> VCCUser:
        """Build VCCUser from token payload"""
        # Parse roles
        roles = []
        for role in payload.roles:
            if isinstance(role, str):
                try:
                    roles.append(VCCRole(role))
                except ValueError:
                    pass
            elif isinstance(role, VCCRole):
                roles.append(role)
        
        # Build permission set from roles
        permissions = set(payload.permissions)
        
        return VCCUser(
            user_id=payload.sub,
            username=payload.sub,
            roles=roles,
            permissions=permissions,
            organization_id=payload.organization_id,
            department=payload.department,
            is_service_account=payload.type == "service"
        )
    
    def decode_token_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token without verification (for debugging)
        
        WARNING: Do not use for authentication!
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False}
            )
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return None
    
    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time
        
        Args:
            token: JWT token string
            
        Returns:
            Expiration datetime or None
        """
        payload = self.decode_token_unsafe(token)
        if payload and 'exp' in payload:
            return datetime.fromtimestamp(payload['exp'])
        return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired
        
        Args:
            token: JWT token string
            
        Returns:
            True if expired
        """
        exp = self.get_token_expiration(token)
        if exp:
            return exp < datetime.utcnow()
        return True
    
    def validate_service_token(
        self,
        token: str,
        allowed_services: Optional[List[str]] = None
    ) -> Optional[VCCUser]:
        """
        Validate a service-to-service token
        
        Args:
            token: JWT token string
            allowed_services: Optional list of allowed service names
            
        Returns:
            VCCUser (service account) if valid
        """
        user = self.validate_token(token, required_permissions=None)
        
        if not user:
            return None
        
        if not user.is_service_account:
            logger.warning("Token is not a service token")
            return None
        
        if allowed_services:
            # Check if service is in allowed list
            payload = self.decode_token_unsafe(token)
            service_name = payload.get('service_name', '')
            if service_name not in allowed_services:
                logger.warning(f"Service {service_name} not allowed")
                return None
        
        return user


class TokenGenerator:
    """
    JWT Token Generator for VCC Ecosystem
    
    Generates JWT tokens for users and services.
    On-premise deployment - uses local keys.
    """
    
    def __init__(
        self,
        private_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        issuer: str = "vcc-identity-provider",
        audience: str = "vcc-ecosystem",
        algorithm: str = "RS256",
        access_token_ttl: int = 3600,  # 1 hour
        refresh_token_ttl: int = 86400 * 7,  # 7 days
    ):
        """
        Initialize the Token Generator
        
        Args:
            private_key: RSA private key for RS256 (PEM format)
            secret_key: Secret key for HS256
            issuer: Token issuer
            audience: Token audience
            algorithm: Signing algorithm
            access_token_ttl: Access token lifetime in seconds
            refresh_token_ttl: Refresh token lifetime in seconds
        """
        self.private_key = private_key
        self.secret_key = secret_key
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm
        self.access_token_ttl = access_token_ttl
        self.refresh_token_ttl = refresh_token_ttl
    
    def _get_signing_key(self) -> Any:
        """Get the appropriate key for signing"""
        if self.algorithm.startswith("RS"):
            if not self.private_key:
                raise ValueError("Private key required for RS* algorithms")
            return self.private_key
        elif self.algorithm.startswith("HS"):
            if not self.secret_key:
                raise ValueError("Secret key required for HS* algorithms")
            return self.secret_key
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
    
    def generate_access_token(
        self,
        user: VCCUser,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate an access token for a user
        
        Args:
            user: VCCUser to generate token for
            additional_claims: Additional JWT claims
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        
        payload = {
            "sub": user.user_id,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.access_token_ttl)).timestamp()),
            "type": "service" if user.is_service_account else "access",
            "roles": [r.value for r in user.roles],
            "permissions": list(user.permissions),
            "organization_id": user.organization_id,
            "department": user.department,
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(
            payload,
            self._get_signing_key(),
            algorithm=self.algorithm
        )
    
    def generate_refresh_token(
        self,
        user: VCCUser,
        jti: Optional[str] = None
    ) -> str:
        """
        Generate a refresh token for a user
        
        Args:
            user: VCCUser to generate token for
            jti: Optional JWT ID
            
        Returns:
            JWT token string
        """
        import uuid
        now = datetime.utcnow()
        
        payload = {
            "sub": user.user_id,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.refresh_token_ttl)).timestamp()),
            "type": "refresh",
            "jti": jti or str(uuid.uuid4()),
        }
        
        return jwt.encode(
            payload,
            self._get_signing_key(),
            algorithm=self.algorithm
        )
    
    def generate_service_token(
        self,
        service_name: str,
        service_id: str,
        permissions: List[VCCPermission],
        allowed_services: Optional[List[str]] = None,
        ttl: Optional[int] = None
    ) -> str:
        """
        Generate a service-to-service token
        
        Args:
            service_name: Name of the service
            service_id: Service identifier
            permissions: Permissions to grant
            allowed_services: Services this token can call
            ttl: Token lifetime (default: access_token_ttl)
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        token_ttl = ttl or self.access_token_ttl
        
        payload = {
            "sub": service_id,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=token_ttl)).timestamp()),
            "type": "service",
            "service_name": service_name,
            "roles": [VCCRole.SERVICE.value],
            "permissions": [p.value for p in permissions],
            "allowed_services": allowed_services or [],
        }
        
        return jwt.encode(
            payload,
            self._get_signing_key(),
            algorithm=self.algorithm
        )
