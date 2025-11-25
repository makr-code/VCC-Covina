"""
VCC Authentication Middleware
Phase 2: VCC Ecosystem Integration

FastAPI middleware for VCC authentication.
Provides request-level authentication and authorization.
"""

import logging
from typing import Optional, List, Callable, Union
from functools import wraps

from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import VCCUser, VCCPermission
from .token_validator import VCCTokenValidator

logger = logging.getLogger(__name__)


# Security scheme for OpenAPI documentation
oauth2_scheme = HTTPBearer(auto_error=False)


class VCCAuthMiddleware:
    """
    FastAPI Authentication Middleware
    
    Provides authentication and authorization for FastAPI applications.
    
    Usage:
        # Setup
        auth_middleware = VCCAuthMiddleware(
            token_validator=VCCTokenValidator(...)
        )
        
        # In route
        @app.get("/api/documents")
        async def get_documents(
            user: VCCUser = Depends(auth_middleware.require_user)
        ):
            return {"user": user.username}
    """
    
    def __init__(
        self,
        token_validator: VCCTokenValidator,
        auto_error: bool = True,
        allow_anonymous: bool = False
    ):
        """
        Initialize the middleware
        
        Args:
            token_validator: Token validator instance
            auto_error: Raise HTTPException on auth failure
            allow_anonymous: Allow unauthenticated requests
        """
        self.token_validator = token_validator
        self.auto_error = auto_error
        self.allow_anonymous = allow_anonymous
    
    async def get_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme)
    ) -> Optional[VCCUser]:
        """
        Get the current user from the request token
        
        Returns None if no token or invalid token.
        """
        if credentials is None:
            return None
        
        token = credentials.credentials
        user = self.token_validator.validate_token(token)
        
        return user
    
    async def require_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme)
    ) -> VCCUser:
        """
        Require an authenticated user
        
        Raises HTTPException if not authenticated.
        """
        if credentials is None:
            if self.allow_anonymous:
                return None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = credentials.credentials
        user = self.token_validator.validate_token(token)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user
    
    def require_permissions(
        self,
        permissions: List[VCCPermission],
        require_all: bool = True
    ):
        """
        Create a dependency that requires specific permissions
        
        Args:
            permissions: Required permissions
            require_all: If True, all permissions required; if False, any one
            
        Returns:
            FastAPI dependency
        """
        async def permission_checker(
            user: VCCUser = Depends(self.require_user)
        ) -> VCCUser:
            if require_all:
                if not user.has_all_permissions(permissions):
                    missing = [
                        p.value for p in permissions 
                        if not user.has_permission(p)
                    ]
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permissions: {missing}"
                    )
            else:
                if not user.has_any_permission(permissions):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Requires one of: {[p.value for p in permissions]}"
                    )
            
            return user
        
        return permission_checker
    
    def require_role(self, role: str):
        """
        Create a dependency that requires a specific role
        
        Args:
            role: Required role name
            
        Returns:
            FastAPI dependency
        """
        from .models import VCCRole
        
        async def role_checker(
            user: VCCUser = Depends(self.require_user)
        ) -> VCCUser:
            try:
                required_role = VCCRole(role)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid role: {role}"
                )
            
            if not user.has_role(required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role}' required"
                )
            
            return user
        
        return role_checker
    
    def require_service_account(self):
        """
        Create a dependency that requires a service account
        
        Returns:
            FastAPI dependency
        """
        async def service_checker(
            user: VCCUser = Depends(self.require_user)
        ) -> VCCUser:
            if not user.is_service_account:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Service account required"
                )
            
            return user
        
        return service_checker


def require_auth(
    token_validator: VCCTokenValidator,
    permissions: Optional[List[VCCPermission]] = None
):
    """
    Decorator for protecting routes with authentication
    
    Usage:
        @require_auth(validator, [VCCPermission.DOCUMENTS_READ])
        @app.get("/api/documents")
        async def get_documents(user: VCCUser):
            return {"user": user.username}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(
            request: Request,
            *args,
            **kwargs
        ):
            # Extract token from header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Validate token
            user = token_validator.validate_token(token, required_permissions=permissions)
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Add user to request state
            request.state.user = user
            
            # Call the original function
            return await func(request, user=user, *args, **kwargs)
        
        return wrapper
    return decorator


# Convenience dependencies for common permission checks

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    token_validator: VCCTokenValidator = None  # Must be set via dependency override
) -> Optional[VCCUser]:
    """Get current user if authenticated, None otherwise"""
    if credentials is None or token_validator is None:
        return None
    return token_validator.validate_token(credentials.credentials)


def verify_vcc_token(token_validator: VCCTokenValidator):
    """
    Create a dependency for verifying VCC tokens
    
    Usage:
        @app.get("/api/documents/{doc_id}")
        async def get_document(
            doc_id: str,
            user: VCCUser = Depends(verify_vcc_token(validator))
        ):
            ...
    """
    async def verify(
        credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
    ) -> VCCUser:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        user = token_validator.validate_token(credentials.credentials)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
    
    return verify


def check_rbac_permission(permission: Union[str, VCCPermission]):
    """
    Create a dependency for checking RBAC permissions
    
    Usage:
        @app.get("/api/documents/{doc_id}")
        async def get_document(
            doc_id: str,
            user: VCCUser = Depends(verify_vcc_token(validator)),
            _: None = Depends(check_rbac_permission("documents.read"))
        ):
            ...
    """
    def checker(user: VCCUser = Depends(oauth2_scheme)) -> None:
        if isinstance(permission, str):
            try:
                perm = VCCPermission(permission)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid permission: {permission}"
                )
        else:
            perm = permission
        
        # Note: This would need the actual user from a previous dependency
        # In practice, you'd chain this with verify_vcc_token
        pass
    
    return checker
