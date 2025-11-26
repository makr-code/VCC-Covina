"""
VCC Authentication Models
Phase 2: VCC Ecosystem Integration

Data models for VCC authentication and authorization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from enum import Enum
from pydantic import BaseModel, Field


class VCCRole(str, Enum):
    """VCC System Roles"""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    SERVICE = "service"


class VCCPermission(str, Enum):
    """VCC Permissions (RBAC)"""
    # Document permissions
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_WRITE = "documents.write"
    DOCUMENTS_DELETE = "documents.delete"
    DOCUMENTS_EXPORT = "documents.export"
    
    # Search permissions
    SEARCH_BASIC = "search.basic"
    SEARCH_ADVANCED = "search.advanced"
    SEARCH_SEMANTIC = "search.semantic"
    
    # Compliance permissions
    COMPLIANCE_VIEW = "compliance.view"
    COMPLIANCE_MANAGE = "compliance.manage"
    COMPLIANCE_AUDIT = "compliance.audit"
    
    # Admin permissions
    ADMIN_USERS = "admin.users"
    ADMIN_SYSTEM = "admin.system"
    ADMIN_CONFIG = "admin.config"
    
    # VCC ecosystem permissions
    VCC_VERITAS = "vcc.veritas"
    VCC_THEMIS = "vcc.themis"
    VCC_CLARA = "vcc.clara"
    VCC_ARGUS = "vcc.argus"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[VCCRole, Set[VCCPermission]] = {
    VCCRole.ADMIN: set(VCCPermission),  # All permissions
    VCCRole.MANAGER: {
        VCCPermission.DOCUMENTS_READ,
        VCCPermission.DOCUMENTS_WRITE,
        VCCPermission.DOCUMENTS_DELETE,
        VCCPermission.DOCUMENTS_EXPORT,
        VCCPermission.SEARCH_BASIC,
        VCCPermission.SEARCH_ADVANCED,
        VCCPermission.SEARCH_SEMANTIC,
        VCCPermission.COMPLIANCE_VIEW,
        VCCPermission.COMPLIANCE_MANAGE,
        VCCPermission.VCC_VERITAS,
        VCCPermission.VCC_THEMIS,
        VCCPermission.VCC_CLARA,
        VCCPermission.VCC_ARGUS,
    },
    VCCRole.ANALYST: {
        VCCPermission.DOCUMENTS_READ,
        VCCPermission.DOCUMENTS_WRITE,
        VCCPermission.SEARCH_BASIC,
        VCCPermission.SEARCH_ADVANCED,
        VCCPermission.SEARCH_SEMANTIC,
        VCCPermission.COMPLIANCE_VIEW,
        VCCPermission.VCC_VERITAS,
        VCCPermission.VCC_THEMIS,
    },
    VCCRole.VIEWER: {
        VCCPermission.DOCUMENTS_READ,
        VCCPermission.SEARCH_BASIC,
        VCCPermission.COMPLIANCE_VIEW,
    },
    VCCRole.SERVICE: {
        VCCPermission.DOCUMENTS_READ,
        VCCPermission.DOCUMENTS_WRITE,
        VCCPermission.SEARCH_BASIC,
        VCCPermission.SEARCH_ADVANCED,
        VCCPermission.SEARCH_SEMANTIC,
        VCCPermission.VCC_VERITAS,
        VCCPermission.VCC_THEMIS,
        VCCPermission.VCC_CLARA,
        VCCPermission.VCC_ARGUS,
    },
}


class VCCTokenPayload(BaseModel):
    """JWT Token Payload for VCC"""
    # Standard JWT claims
    sub: str  # Subject (user_id or service_id)
    iss: str = "vcc-identity-provider"
    aud: str = "vcc-ecosystem"
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    nbf: Optional[int] = None  # Not before timestamp
    jti: Optional[str] = None  # JWT ID (unique identifier)
    
    # VCC-specific claims
    type: str = "access"  # access, refresh, service
    roles: List[VCCRole] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    organization_id: Optional[str] = None
    department: Optional[str] = None
    
    # Service-to-service claims
    service_name: Optional[str] = None
    allowed_services: List[str] = Field(default_factory=list)


class VCCUser(BaseModel):
    """VCC User Model"""
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: List[VCCRole] = Field(default_factory=list)
    permissions: Set[str] = Field(default_factory=set)
    organization_id: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True
    is_service_account: bool = False
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def has_permission(self, permission: VCCPermission) -> bool:
        """Check if user has a specific permission"""
        # Direct permission check
        if permission.value in self.permissions:
            return True
        
        # Role-based permission check
        for role in self.roles:
            if permission in ROLE_PERMISSIONS.get(role, set()):
                return True
        
        return False
    
    def has_any_permission(self, permissions: List[VCCPermission]) -> bool:
        """Check if user has any of the given permissions"""
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, permissions: List[VCCPermission]) -> bool:
        """Check if user has all of the given permissions"""
        return all(self.has_permission(p) for p in permissions)
    
    def has_role(self, role: VCCRole) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def get_effective_permissions(self) -> Set[VCCPermission]:
        """Get all effective permissions (direct + role-based)"""
        permissions = set()
        
        # Add direct permissions
        for p in self.permissions:
            try:
                permissions.add(VCCPermission(p))
            except ValueError:
                pass
        
        # Add role-based permissions
        for role in self.roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        
        return permissions
    
    class Config:
        arbitrary_types_allowed = True


class VCCServiceAccount(BaseModel):
    """VCC Service Account for service-to-service auth"""
    service_id: str
    service_name: str
    description: Optional[str] = None
    allowed_services: List[str] = Field(default_factory=list)
    permissions: List[VCCPermission] = Field(default_factory=list)
    api_key_hash: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None


class AuthenticationResult(BaseModel):
    """Result of authentication attempt"""
    success: bool
    user: Optional[VCCUser] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: int = 3600  # seconds
    token_type: str = "Bearer"
    error_message: Optional[str] = None
    error_code: Optional[str] = None
