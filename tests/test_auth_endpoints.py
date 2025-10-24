"""Integration tests for auth-protected endpoints."""
import os
import pytest
from fastapi.testclient import TestClient

# Set test environment before imports
os.environ["ENABLE_AUTH"] = "true"
os.environ["JWT_SECRET"] = "test_secret_key_for_testing_only"
os.environ["ADMIN_PASSWORD"] = "test_admin"
os.environ["USER_PASSWORD"] = "test_user"

from main_backend import app as main_app


@pytest.fixture
def main_client():
    """Create test client for main backend."""
    return TestClient(main_app)


@pytest.fixture
def admin_token(main_client):
    """Get admin token for tests."""
    response = main_client.post(
        "/token",
        data={"username": "admin", "password": "test_admin"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def user_token(main_client):
    """Get user token for tests."""
    response = main_client.post(
        "/token",
        data={"username": "user", "password": "test_user"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestTokenEndpoint:
    """Test /token endpoint."""

    def test_token_endpoint_valid_credentials(self, main_client):
        """Test token issuance with valid credentials."""
        response = main_client.post(
            "/token",
            data={"username": "admin", "password": "test_admin"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 50

    def test_token_endpoint_invalid_credentials(self, main_client):
        """Test token rejection with invalid credentials."""
        response = main_client.post(
            "/token",
            data={"username": "admin", "password": "wrong_password"},
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_token_endpoint_unknown_user(self, main_client):
        """Test token rejection for unknown user."""
        response = main_client.post(
            "/token",
            data={"username": "unknown", "password": "any"},
        )
        
        assert response.status_code == 401


class TestMeEndpoint:
    """Test /me endpoint."""

    def test_me_endpoint_with_valid_token(self, main_client, admin_token):
        """Test /me endpoint returns correct user info."""
        response = main_client.get(
            "/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "admin"
        assert "admin" in data["roles"]
        assert "manager" in data["roles"]

    def test_me_endpoint_without_token(self, main_client):
        """Test /me endpoint rejects requests without token."""
        response = main_client.get("/me")
        
        assert response.status_code == 401

    def test_me_endpoint_with_invalid_token(self, main_client):
        """Test /me endpoint rejects invalid tokens."""
        response = main_client.get(
            "/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Test RBAC on protected endpoints."""

    def test_compliance_check_with_admin(self, main_client, admin_token):
        """Test compliance check endpoint with admin token."""
        response = main_client.post(
            "/compliance/check",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "document_id": "test_doc",
                "check_type": "gdpr",
            },
        )
        
        # May return 503 if service not available, but should not be 401/403
        assert response.status_code in [200, 503]

    def test_compliance_check_without_token(self, main_client):
        """Test compliance endpoint rejects requests without token."""
        response = main_client.post(
            "/compliance/check",
            json={
                "document_id": "test_doc",
                "check_type": "gdpr",
            },
        )
        
        assert response.status_code == 401

    def test_compliance_checks_with_manager(self, main_client, admin_token):
        """Test compliance list endpoint with manager role."""
        # Admin has manager role too
        response = main_client.get(
            "/compliance/checks",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        # May return 503 if service not available
        assert response.status_code in [200, 503]

    def test_compliance_dsgvo_status_protected(self, main_client):
        """Test DSGVO status endpoint requires authentication."""
        response = main_client.get("/compliance/dsgvo/test_doc")
        
        assert response.status_code == 401


class TestRoleEnforcement:
    """Test that role requirements are enforced."""

    def test_user_role_cannot_access_manager_endpoint(self, main_client, user_token):
        """Test that user role is rejected from manager-only endpoints."""
        response = main_client.post(
            "/compliance/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "document_id": "test_doc",
                "check_type": "gdpr",
            },
        )
        
        # User role should be forbidden (403)
        assert response.status_code == 403

    def test_admin_role_has_full_access(self, main_client, admin_token):
        """Test that admin role can access all endpoints."""
        # Test compliance endpoint (requires manager/admin)
        response = main_client.get(
            "/compliance/checks",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code in [200, 503]  # Not 401 or 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
