"""Tests for secure secrets management."""
import os
import tempfile
from pathlib import Path

import pytest

from security.secrets import (
    DPAPISecretsBackend,
    EnvSecretsBackend,
    SecretsManager,
    DPAPI_AVAILABLE,
)


class TestEnvSecretsBackend:
    """Test environment variable backend (development fallback)."""
    
    def test_set_and_get_secret(self):
        """Test setting and getting a secret from environment."""
        backend = EnvSecretsBackend()
        
        backend.set_secret("TEST_SECRET", "test_value_123")
        value = backend.get_secret("TEST_SECRET")
        
        assert value == "test_value_123"
    
    def test_get_nonexistent_secret(self):
        """Test getting a secret that doesn't exist."""
        backend = EnvSecretsBackend()
        
        value = backend.get_secret("NONEXISTENT_SECRET")
        
        assert value is None
    
    def test_delete_secret(self):
        """Test deleting a secret."""
        backend = EnvSecretsBackend()
        
        backend.set_secret("DELETE_ME", "temp_value")
        assert backend.get_secret("DELETE_ME") == "temp_value"
        
        backend.delete_secret("DELETE_ME")
        assert backend.get_secret("DELETE_ME") is None


@pytest.mark.skipif(not DPAPI_AVAILABLE, reason="DPAPI not available on this system")
class TestDPAPISecretsBackend:
    """Test Windows DPAPI backend (encrypted storage)."""
    
    def test_set_and_get_secret(self):
        """Test setting and getting an encrypted secret."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_secrets.json"
            backend = DPAPISecretsBackend(storage_path=storage_path)
            
            # Set secret
            backend.set_secret("DB_PASSWORD", "super_secure_password_123")
            
            # Get secret
            value = backend.get_secret("DB_PASSWORD")
            assert value == "super_secure_password_123"
    
    def test_persistence(self):
        """Test that secrets persist across backend instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_secrets.json"
            
            # First backend instance - set secret
            backend1 = DPAPISecretsBackend(storage_path=storage_path)
            backend1.set_secret("PERSISTENT_SECRET", "this_should_persist")
            
            # Second backend instance - should load from disk
            backend2 = DPAPISecretsBackend(storage_path=storage_path)
            value = backend2.get_secret("PERSISTENT_SECRET")
            
            assert value == "this_should_persist"
    
    def test_list_secrets(self):
        """Test listing all secret keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_secrets.json"
            backend = DPAPISecretsBackend(storage_path=storage_path)
            
            backend.set_secret("SECRET_1", "value1")
            backend.set_secret("SECRET_2", "value2")
            backend.set_secret("SECRET_3", "value3")
            
            keys = backend.list_secrets()
            
            assert len(keys) == 3
            assert "SECRET_1" in keys
            assert "SECRET_2" in keys
            assert "SECRET_3" in keys
    
    def test_delete_secret(self):
        """Test deleting a secret."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_secrets.json"
            backend = DPAPISecretsBackend(storage_path=storage_path)
            
            backend.set_secret("DELETE_ME", "temp_value")
            assert backend.get_secret("DELETE_ME") == "temp_value"
            
            backend.delete_secret("DELETE_ME")
            assert backend.get_secret("DELETE_ME") is None
    
    def test_encrypted_storage_format(self):
        """Test that secrets are actually encrypted on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_secrets.json"
            backend = DPAPISecretsBackend(storage_path=storage_path)
            
            secret_value = "plaintext_secret_value_123"
            backend.set_secret("ENCRYPTED_TEST", secret_value)
            
            # Read raw file content
            with open(storage_path, 'r') as f:
                file_content = f.read()
            
            # Secret should NOT appear in plaintext in file
            assert secret_value not in file_content
            assert "ENCRYPTED_TEST" in file_content  # Key should be visible


class TestSecretsManager:
    """Test high-level secrets manager."""
    
    def test_get_secret_with_default(self):
        """Test getting secret with default value."""
        backend = EnvSecretsBackend()
        manager = SecretsManager(backend=backend)
        
        # Non-existent secret should return default
        value = manager.get_secret("NONEXISTENT", default="default_value")
        assert value == "default_value"
    
    def test_migrate_from_env(self):
        """Test migrating secrets from environment variables."""
        # Set some environment variables
        os.environ["TEST_MIGRATE_1"] = "value1"
        os.environ["TEST_MIGRATE_2"] = "value2"
        
        backend = EnvSecretsBackend()
        manager = SecretsManager(backend=backend)
        
        # Migrate secrets
        migrated = manager.migrate_from_env(["TEST_MIGRATE_1", "TEST_MIGRATE_2"])
        
        assert migrated == 2
        assert manager.get_secret("TEST_MIGRATE_1") == "value1"
        assert manager.get_secret("TEST_MIGRATE_2") == "value2"


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_jwt_secret_fallback(self):
        """Test JWT secret retrieval with ENV fallback."""
        from security.secrets import get_jwt_secret
        
        # Should fallback to ENV if not in secure storage
        os.environ["JWT_SECRET"] = "test_jwt_secret_123"
        secret = get_jwt_secret()
        
        assert secret is not None
        assert len(secret) > 0
    
    def test_get_database_password(self):
        """Test database password retrieval."""
        from security.secrets import get_database_password
        
        os.environ["POSTGRES_PASSWORD"] = "test_db_password"
        password = get_database_password("POSTGRES")
        
        assert password == "test_db_password"
    
    def test_get_admin_password_fallback(self):
        """Test admin password with default fallback."""
        from security.secrets import get_admin_password
        
        # Should fallback to default if not set
        if "ADMIN_PASSWORD" in os.environ:
            del os.environ["ADMIN_PASSWORD"]
        
        password = get_admin_password()
        assert password == "admin"  # Default value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
