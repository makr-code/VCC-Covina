"""
VCC Authentication Module
Phase 2: VCC Ecosystem Integration

OAuth2/OIDC authentication for VCC ecosystem.
On-premise deployment - uses self-hosted identity provider.
"""

from .authenticator import VCCAuthenticator
from .token_validator import VCCTokenValidator
from .middleware import VCCAuthMiddleware
from .models import VCCUser, VCCTokenPayload, VCCPermission

__all__ = [
    "VCCAuthenticator",
    "VCCTokenValidator",
    "VCCAuthMiddleware",
    "VCCUser",
    "VCCTokenPayload",
    "VCCPermission"
]
