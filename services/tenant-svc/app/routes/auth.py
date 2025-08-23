"""
Authentication and Authorization for SCIM Endpoints

Provides tenant-based authentication and SCIM permission management.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Tenant
from ..config import get_settings

security = HTTPBearer()
settings = get_settings()


class SCIMPermissions:
    """SCIM permission definitions."""
    
    # User permissions
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"
    
    # Group permissions
    GROUPS_READ = "groups:read"
    GROUPS_WRITE = "groups:write"
    GROUPS_DELETE = "groups:delete"
    
    # Schema permissions
    SCHEMAS_READ = "schemas:read"
    
    # Admin permissions
    ADMIN_ALL = "admin:all"
    
    @classmethod
    def get_all_permissions(cls) -> list[str]:
        """Get all available SCIM permissions."""
        return [
            cls.USERS_READ,
            cls.USERS_WRITE,
            cls.USERS_DELETE,
            cls.GROUPS_READ,
            cls.GROUPS_WRITE,
            cls.GROUPS_DELETE,
            cls.SCHEMAS_READ,
            cls.ADMIN_ALL
        ]


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Get current tenant from JWT token.
    
    Validates JWT and extracts tenant information.
    """
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Extract tenant information
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing tenant_id",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get tenant from database
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: tenant not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if tenant is active
        if not tenant.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is not active",
            )
        
        # Check SCIM configuration
        if not tenant.scim_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SCIM is not enabled for this tenant",
            )
        
        return tenant
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_scim_permission(permission: str):
    """
    Dependency to require specific SCIM permission.
    
    Args:
        permission: Required permission (e.g., "users:read")
    
    Returns:
        Dependency function that validates permission
    """
    
    def check_permission(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        tenant: Tenant = Depends(get_current_tenant)
    ) -> bool:
        """Check if current user has required permission."""
        
        try:
            # Decode JWT token to get user permissions
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            # Extract permissions from token
            permissions = payload.get("permissions", [])
            scim_permissions = payload.get("scim_permissions", [])
            
            # Check for admin permission (grants all access)
            if SCIMPermissions.ADMIN_ALL in scim_permissions:
                return True
            
            # Check for specific permission
            if permission in scim_permissions:
                return True
            
            # Permission denied
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission} required",
            )
            
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return check_permission


class SCIMTokenGenerator:
    """Generate SCIM-specific JWT tokens."""
    
    @staticmethod
    def create_scim_token(
        tenant_id: str,
        client_id: str,
        permissions: list[str],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create SCIM JWT token.
        
        Args:
            tenant_id: Tenant ID
            client_id: SCIM client ID
            permissions: List of SCIM permissions
            expires_delta: Token expiration time
        
        Returns:
            JWT token string
        """
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        payload = {
            "sub": client_id,
            "tenant_id": tenant_id,
            "scim_permissions": permissions,
            "iat": datetime.utcnow(),
            "exp": expire,
            "iss": "aivo-scim",
            "aud": "scim-api"
        }
        
        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
    
    @staticmethod
    def create_admin_token(tenant_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create admin SCIM token with all permissions.
        
        Args:
            tenant_id: Tenant ID
            expires_delta: Token expiration time
        
        Returns:
            JWT token string
        """
        
        return SCIMTokenGenerator.create_scim_token(
            tenant_id=tenant_id,
            client_id="admin",
            permissions=[SCIMPermissions.ADMIN_ALL],
            expires_delta=expires_delta
        )


async def validate_ip_allowlist(
    request,
    tenant: Tenant = Depends(get_current_tenant)
) -> bool:
    """
    Validate client IP against tenant's SCIM IP allowlist.
    
    Args:
        request: FastAPI request object
        tenant: Current tenant
    
    Returns:
        True if IP is allowed
    
    Raises:
        HTTPException: If IP is not allowed
    """
    
    # Skip IP validation if no allowlist configured
    if not tenant.scim_ip_allowlist:
        return True
    
    client_ip = request.client.host
    allowed_ips = tenant.scim_ip_allowlist
    
    # Check if client IP is in allowlist
    # This is a simplified check - in production, you'd want proper CIDR support
    if client_ip not in allowed_ips:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP address {client_ip} is not allowed for SCIM access",
        )
    
    return True


class SCIMRateLimiter:
    """Rate limiting for SCIM endpoints."""
    
    def __init__(self):
        self.requests = {}  # Simple in-memory store
    
    def is_allowed(self, tenant_id: str, client_ip: str, limit: int = 100, window: int = 60) -> bool:
        """
        Check if request is within rate limits.
        
        Args:
            tenant_id: Tenant ID
            client_ip: Client IP address
            limit: Request limit per window
            window: Time window in seconds
        
        Returns:
            True if request is allowed
        """
        
        key = f"{tenant_id}:{client_ip}"
        now = datetime.utcnow()
        
        # Clean old entries
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if (now - req_time).total_seconds() < window
            ]
        else:
            self.requests[key] = []
        
        # Check if within limit
        if len(self.requests[key]) >= limit:
            return False
        
        # Record this request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = SCIMRateLimiter()


def require_rate_limit(limit: int = 100, window: int = 60):
    """
    Dependency to enforce rate limiting.
    
    Args:
        limit: Request limit per window
        window: Time window in seconds
    
    Returns:
        Dependency function that enforces rate limit
    """
    
    def check_rate_limit(
        request,
        tenant: Tenant = Depends(get_current_tenant)
    ) -> bool:
        """Check if request is within rate limits."""
        
        client_ip = request.client.host
        
        if not rate_limiter.is_allowed(str(tenant.id), client_ip, limit, window):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(window)}
            )
        
        return True
    
    return check_rate_limit
