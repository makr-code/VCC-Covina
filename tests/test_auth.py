"""Tests for authentication and authorization (OAuth2/JWT + RBAC)."""
import os
import time
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from security.auth import (
    Role,
    Principal,
    TokenData,
    create_access_token,
    verify_jwt_token,
    JWT_SECRET,
    JWT_ALGORITHM,
)


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_token_basic(self):
        """Test basic token creation with subject and roles."""
        token = create_access_token(
            subject="test_user",
            roles=[Role.user, Role.manager],
            scopes=["read", "write"],
        )
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_create_token_with_custom_expiry(self):
        """Test token creation with custom expiry."""
        token = create_access_token(
            subject="test_user",
            roles=[Role.admin],
            expires_minutes=5,
        )
        
        # Decode and verify expiry
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        exp = payload.get("exp")
        iat = payload.get("iat")
        
        assert exp is not None
        assert iat is not None
        assert (exp - iat) == 5 * 60  # 5 minutes in seconds

    def test_token_contains_correct_claims(self):
        """Test that token contains all required claims."""
        roles = [Role.admin, Role.manager]
        scopes = ["upload", "delete"]
        
        token = create_access_token(
            subject="admin_user",
            roles=roles,
            scopes=scopes,
        )
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        assert payload["sub"] == "admin_user"
        assert set(payload["roles"]) == {"admin", "manager"}
        assert set(payload["scopes"]) == {"upload", "delete"}
        assert "iat" in payload
        assert "exp" in payload


class TestTokenVerification:
    """Test JWT token verification."""

    def test_verify_valid_token(self):
        """Test verification of a valid token."""
        token = create_access_token(
            subject="test_user",
            roles=[Role.user],
            scopes=["read"],
        )
        
        token_data = verify_jwt_token(token)
        
        assert isinstance(token_data, TokenData)
        assert token_data.sub == "test_user"
        assert Role.user in token_data.roles
        assert "read" in token_data.scopes

    def test_verify_expired_token(self):
        """Test that expired tokens are rejected."""
        # Create token that expires immediately
        token = create_access_token(
            subject="test_user",
            roles=[Role.user],
            expires_minutes=-1,  # Already expired
        )
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    def test_verify_token_with_invalid_secret(self):
        """Test that tokens signed with wrong secret are rejected."""
        # Create token with different secret
        wrong_secret = "wrong_secret_key_12345"
        payload = {
            "sub": "test_user",
            "roles": ["user"],
            "exp": datetime.utcnow() + timedelta(minutes=60),
        }
        bad_token = jwt.encode(payload, wrong_secret, algorithm=JWT_ALGORITHM)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(bad_token)
        
        assert exc_info.value.status_code == 401

    def test_verify_token_without_subject(self):
        """Test that tokens without 'sub' claim are rejected."""
        payload = {
            "roles": ["user"],
            "exp": datetime.utcnow() + timedelta(minutes=60),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(token)
        
        assert exc_info.value.status_code == 401
        assert "missing subject" in str(exc_info.value.detail).lower()


class TestRoleBasedAccessControl:
    """Test RBAC functionality."""

    def test_principal_creation(self):
        """Test Principal model creation."""
        principal = Principal(
            user_id="test_user",
            roles=[Role.admin, Role.manager],
            scopes=["read", "write", "delete"],
        )
        
        assert principal.user_id == "test_user"
        assert len(principal.roles) == 2
        assert Role.admin in principal.roles
        assert len(principal.scopes) == 3

    def test_role_enum_values(self):
        """Test that Role enum has correct values."""
        assert Role.admin.value == "admin"
        assert Role.manager.value == "manager"
        assert Role.user.value == "user"
        assert Role.guest.value == "guest"

    def test_multiple_roles_in_token(self):
        """Test token with multiple roles."""
        roles = [Role.admin, Role.manager, Role.user]
        token = create_access_token(
            subject="super_user",
            roles=roles,
        )
        
        token_data = verify_jwt_token(token)
        
        # All roles should be preserved
        assert len(token_data.roles) == 3
        assert "admin" in token_data.roles
        assert "manager" in token_data.roles
        assert "user" in token_data.roles


class TestSecurityConfiguration:
    """Test security configuration from environment."""

    def test_jwt_secret_is_set(self):
        """Test that JWT_SECRET is configured."""
        assert JWT_SECRET is not None
        assert len(JWT_SECRET) > 0

    def test_jwt_algorithm_is_set(self):
        """Test that JWT_ALGORITHM is configured."""
        assert JWT_ALGORITHM == "HS256"

    def test_enable_auth_flag(self):
        """Test ENABLE_AUTH environment flag."""
        from security.auth import ENABLE_AUTH
        
        # In tests, should be false by default
        assert isinstance(ENABLE_AUTH, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
