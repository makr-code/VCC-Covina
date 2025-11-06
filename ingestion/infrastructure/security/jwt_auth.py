"""
JWT Authentication and Validation

Provides:
- JWT token validation
- Token expiration checking
- Claims extraction
- FastAPI dependency for protected endpoints

Usage:
    from ingestion.infrastructure.security.jwt_auth import JWTAuth, get_current_user
    
    jwt_auth = JWTAuth(secret_key="your-secret-key", algorithm="HS256")
    
    @app.get("/protected")
    async def protected_endpoint(user=Depends(get_current_user)):
        return {"user": user}
"""
from __future__ import annotations

import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class JWTUser(BaseModel):
    """JWT user model."""
    sub: str  # Subject (user ID)
    email: Optional[str] = None
    roles: list[str] = []
    exp: Optional[int] = None  # Expiration timestamp


class JWTAuth:
    """JWT authentication handler."""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_expiration_minutes: int = 60,
        require_exp: bool = True
    ):
        """Initialize JWT auth.
        
        Args:
            secret_key: Secret key for JWT signing/verification
            algorithm: JWT algorithm (HS256, RS256, etc.)
            token_expiration_minutes: Default token expiration
            require_exp: Require expiration claim
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiration_minutes = token_expiration_minutes
        self.require_exp = require_exp
        
        logger.info(f"JWTAuth initialized: algorithm={algorithm}, expiration={token_expiration_minutes}min")
    
    def create_token(
        self,
        user_id: str,
        email: Optional[str] = None,
        roles: Optional[list[str]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT token.
        
        Args:
            user_id: User ID (sub claim)
            email: User email
            roles: User roles
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.token_expiration_minutes)
        
        expire = datetime.utcnow() + expires_delta
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        if email:
            payload["email"] = email
        if roles:
            payload["roles"] = roles
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Created token for user {user_id}, expires at {expire}")
        
        return token
    
    def verify_token(self, token: str) -> JWTUser:
        """Verify and decode JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded user information
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require_exp": self.require_exp}
            )
            
            user = JWTUser(
                sub=payload["sub"],
                email=payload.get("email"),
                roles=payload.get("roles", []),
                exp=payload.get("exp")
            )
            
            logger.debug(f"Token verified for user {user.sub}")
            return user
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def verify_role(self, user: JWTUser, required_role: str) -> bool:
        """Verify user has required role.
        
        Args:
            user: JWT user
            required_role: Required role
            
        Returns:
            True if user has role
        """
        return required_role in user.roles
    
    def require_role(self, required_role: str):
        """Create dependency that requires specific role.
        
        Args:
            required_role: Required role
            
        Returns:
            FastAPI dependency
        """
        async def role_checker(user: JWTUser = Depends(self.get_current_user)):
            if not self.verify_role(user, required_role):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required role: {required_role}"
                )
            return user
        
        return role_checker
    
    def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
    ) -> JWTUser:
        """FastAPI dependency to get current user from JWT.
        
        Args:
            credentials: HTTP Bearer credentials
            
        Returns:
            Decoded user information
        """
        return self.verify_token(credentials.credentials)


# Global instance
_jwt_auth: Optional[JWTAuth] = None


def configure_jwt_auth(
    secret_key: str,
    algorithm: str = "HS256",
    token_expiration_minutes: int = 60
) -> JWTAuth:
    """Configure global JWT auth instance.
    
    Args:
        secret_key: Secret key for JWT
        algorithm: JWT algorithm
        token_expiration_minutes: Token expiration
        
    Returns:
        Configured JWTAuth instance
    """
    global _jwt_auth
    _jwt_auth = JWTAuth(
        secret_key=secret_key,
        algorithm=algorithm,
        token_expiration_minutes=token_expiration_minutes
    )
    return _jwt_auth


def get_jwt_auth() -> JWTAuth:
    """Get global JWT auth instance.
    
    Returns:
        JWTAuth instance
        
    Raises:
        RuntimeError: If not configured
    """
    if _jwt_auth is None:
        raise RuntimeError("JWTAuth not configured. Call configure_jwt_auth() first.")
    return _jwt_auth


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
) -> JWTUser:
    """FastAPI dependency to get current user.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Decoded user information
    """
    return get_jwt_auth().get_current_user(credentials)
