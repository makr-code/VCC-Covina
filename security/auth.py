"""
Security module for OAuth2/JWT authentication and RBAC authorization.

Usage:
- Import require_roles in FastAPI endpoints to protect routes.
- Use get_current_user to retrieve the authenticated principal.

Note:
- Token issuing endpoint (/token) should be implemented in the API app.
- This module is framework-agnostic except for FastAPI dependencies.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# ENV configuration
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"

# OAuth2 token URL (should match the API route)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    user = "user"
    guest = "guest"


class TokenData(BaseModel):
    sub: str
    roles: List[Role] = []
    scopes: List[str] = []
    iat: Optional[int] = None
    exp: Optional[int] = None


class Principal(BaseModel):
    user_id: str
    roles: List[Role]
    scopes: List[str] = []


def create_access_token(subject: str, roles: List[str] | List[Role], scopes: Optional[List[str]] = None,
                        expires_minutes: Optional[int] = None) -> str:
    """Create a signed JWT access token."""
    # Use time.time() for consistent Unix timestamps
    now = time.time()
    exp_minutes = expires_minutes if expires_minutes is not None else JWT_EXPIRES_MINUTES
    payload: Dict[str, Any] = {
        "sub": subject,
        "roles": [r.value if isinstance(r, Role) else r for r in roles],
        "scopes": scopes or [],
        "iat": int(now),
        "exp": int(now + (exp_minutes * 60)),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token: str) -> TokenData:
    """Verify and decode a JWT token into TokenData."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing subject")
        roles = payload.get("roles", [])
        scopes = payload.get("scopes", [])
        return TokenData(sub=sub, roles=roles, scopes=scopes, iat=payload.get("iat"), exp=payload.get("exp"))
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Principal:
    """FastAPI dependency that returns the authenticated principal.

    If ENABLE_AUTH is false, returns a permissive dev principal.
    """
    if not ENABLE_AUTH:
        # Development fallback (do NOT use in production)
        return Principal(user_id="dev", roles=[Role.admin, Role.manager, Role.user], scopes=["*"])

    data = verify_jwt_token(token)
    # Normalize roles into Role enum
    norm_roles: List[Role] = []
    for r in data.roles:
        try:
            norm_roles.append(Role(r))
        except Exception:
            # Unknown role: ignore
            continue
    return Principal(user_id=data.sub, roles=norm_roles, scopes=data.scopes)


def require_roles(allowed_roles: List[Role]):
    """Create a FastAPI dependency that enforces RBAC for the given roles.

    Example:
        @app.get("/admin")
        async def admin_only(_: Principal = Depends(require_roles([Role.admin]))):
            return {"ok": True}
    """
    async def dependency(principal: Principal = Depends(get_current_user)) -> Principal:
        if not ENABLE_AUTH:
            return principal
        if not principal.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: no roles")
        role_names = set([r.value for r in principal.roles])
        allowed = set([r.value for r in allowed_roles])
        if role_names.isdisjoint(allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: insufficient role")
        return principal

    return dependency


__all__ = [
    "Role",
    "TokenData",
    "Principal",
    "create_access_token",
    "verify_jwt_token",
    "get_current_user",
    "require_roles",
]
