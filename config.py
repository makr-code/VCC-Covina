"""Compatibility shim at project root so modules that import `from config import config` work.
This simply forwards the `uds3.database.config` implementation used inside this workspace.
"""
from uds3.database.config import DatabaseConnection, DatabaseType, DatabaseBackend  # re-export useful symbols

# Create a compatibility class alias
class CovinaConfig:
    """Compatibility wrapper for database configuration"""
    pass

# Provide the same global instance name many modules expect
config = CovinaConfig()

# Convenience functions used in some modules
def get_database_config():
    return config.get_legacy_config() if hasattr(config, 'get_legacy_config') else config.get_database_backend_dict()

# Expose class for explicit imports
__all__ = ['config', 'CovinaConfig', 'DatabaseConnection', 'DatabaseType', 'DatabaseBackend', 'get_database_config']
