"""Ensure critical local modules are importable early in test session.
This stabilizes subsequent imports in case other tests alter sys.path.
"""

# Import at module import time, so it's executed during collection
import security  # noqa: F401
import security.auth  # noqa: F401
import security.secrets  # noqa: F401


def test_bootstrap_security_imports():
    # Simple smoke assertion that modules are present
    assert hasattr(security, "__file__")
