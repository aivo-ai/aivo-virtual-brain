"""
Authentication and authorization for AIVO Admin Service
Strict RBAC with JWT validation and audit logging
"""

import jwt
import time
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging

from app.config import settings
from app.audit import log_auth_event

logger = logging.getLogger(__name__)
security = HTTPBearer()


class AdminUser(BaseModel):
    """Admin user model"""
    user_id: str
    email: str
    roles: List[str]
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    exp: int
    iat: int
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        return any(role in self.roles for role in roles)
    
    def is_staff(self) -> bool:
        """Check if user is staff (minimum admin requirement)"""
        return self.has_any_role(["staff", "tenant_admin", "system_admin"])
    
    def is_tenant_admin(self) -> bool:
        """Check if user is tenant admin"""
        return self.has_any_role(["tenant_admin", "system_admin"])
    
    def is_system_admin(self) -> bool:
        """Check if user is system admin"""
        return self.has_role("system_admin")
    
    def can_manage_queues(self) -> bool:
        """Check if user can manage job queues"""
        return self.has_any_role(["tenant_admin", "system_admin"])
    
    def can_access_learner_data(self) -> bool:
        """Check if user can access learner data"""
        return self.has_any_role(["staff", "tenant_admin", "system_admin"])
    
    def can_manage_flags(self) -> bool:
        """Check if user can manage feature flags"""
        return self.has_role("system_admin")


class AdminPermissions:
    """Admin permission levels"""
    STAFF = "staff"
    TENANT_ADMIN = "tenant_admin" 
    SYSTEM_ADMIN = "system_admin"
    
    ALL_ROLES = [STAFF, TENANT_ADMIN, SYSTEM_ADMIN]
    ADMIN_ROLES = [TENANT_ADMIN, SYSTEM_ADMIN]


async def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AdminUser:
    """
    Verify and decode admin JWT token
    Ensures user has minimum staff role
    """
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extract user information
        user_id = payload.get("sub")
        email = payload.get("email")
        roles = payload.get("roles", [])
        tenant_id = payload.get("tenant_id")
        exp = payload.get("exp")
        iat = payload.get("iat")
        
        # Validate required fields
        if not user_id or not email or not roles:
            await log_auth_event(
                event_type="invalid_token",
                user_id=user_id,
                details={"error": "Missing required fields"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing required fields"
            )
        
        # Check token expiration
        if exp and exp < time.time():
            await log_auth_event(
                event_type="token_expired",
                user_id=user_id,
                details={"exp": exp, "current_time": time.time()}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        # Create admin user
        admin_user = AdminUser(
            user_id=user_id,
            email=email,
            roles=roles,
            tenant_id=tenant_id,
            exp=exp,
            iat=iat
        )
        
        # Verify user has admin access (minimum staff role)
        if not admin_user.is_staff():
            await log_auth_event(
                event_type="insufficient_permissions",
                user_id=user_id,
                details={
                    "roles": roles,
                    "required": "staff minimum"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions: staff role required"
            )
        
        # Log successful authentication
        await log_auth_event(
            event_type="admin_login",
            user_id=user_id,
            details={
                "email": email,
                "roles": roles,
                "tenant_id": tenant_id
            }
        )
        
        return admin_user
        
    except jwt.ExpiredSignatureError:
        await log_auth_event(
            event_type="token_expired", 
            details={"token": token[:20] + "..."}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        await log_auth_event(
            event_type="invalid_token",
            details={"error": str(e), "token": token[:20] + "..."}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        await log_auth_event(
            event_type="auth_error",
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


def require_role(required_role: str):
    """
    Dependency to require specific role
    """
    async def role_checker(admin: AdminUser = Depends(verify_admin_token)) -> AdminUser:
        if not admin.has_role(required_role):
            await log_auth_event(
                event_type="role_required",
                user_id=admin.user_id,
                details={
                    "required_role": required_role,
                    "user_roles": admin.roles
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return admin
    
    return role_checker


def require_any_role(required_roles: List[str]):
    """
    Dependency to require any of the specified roles
    """
    async def role_checker(admin: AdminUser = Depends(verify_admin_token)) -> AdminUser:
        if not admin.has_any_role(required_roles):
            await log_auth_event(
                event_type="roles_required",
                user_id=admin.user_id,
                details={
                    "required_roles": required_roles,
                    "user_roles": admin.roles
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(required_roles)}"
            )
        return admin
    
    return role_checker


def require_tenant_admin(admin: AdminUser = Depends(verify_admin_token)) -> AdminUser:
    """Require tenant admin or system admin role"""
    if not admin.is_tenant_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin role required"
        )
    return admin


def require_system_admin(admin: AdminUser = Depends(verify_admin_token)) -> AdminUser:
    """Require system admin role"""
    if not admin.is_system_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System admin role required"
        )
    return admin


async def create_admin_session(admin_user: AdminUser) -> str:
    """
    Create a tracked admin session
    Returns session ID for audit tracking
    """
    import uuid
    from app.database import get_redis
    
    session_id = str(uuid.uuid4())
    session_data = {
        "user_id": admin_user.user_id,
        "email": admin_user.email,
        "roles": admin_user.roles,
        "tenant_id": admin_user.tenant_id,
        "created_at": time.time(),
        "last_activity": time.time()
    }
    
    # Store session in Redis with expiration
    redis = await get_redis()
    session_key = f"admin_session:{session_id}"
    await redis.setex(
        session_key,
        settings.ADMIN_SESSION_TIMEOUT_MINUTES * 60,
        str(session_data)
    )
    
    # Log session creation
    await log_auth_event(
        event_type="session_created",
        user_id=admin_user.user_id,
        details={
            "session_id": session_id,
            "timeout_minutes": settings.ADMIN_SESSION_TIMEOUT_MINUTES
        }
    )
    
    return session_id


async def validate_admin_session(session_id: str) -> bool:
    """Validate if admin session is still active"""
    from app.database import get_redis
    
    redis = await get_redis()
    session_key = f"admin_session:{session_id}"
    session_data = await redis.get(session_key)
    
    if not session_data:
        return False
    
    # Update last activity
    await redis.expire(session_key, settings.ADMIN_SESSION_TIMEOUT_MINUTES * 60)
    return True


async def invalidate_admin_session(session_id: str, user_id: str):
    """Invalidate admin session"""
    from app.database import get_redis
    
    redis = await get_redis()
    session_key = f"admin_session:{session_id}"
    await redis.delete(session_key)
    
    # Log session invalidation
    await log_auth_event(
        event_type="session_invalidated",
        user_id=user_id,
        details={"session_id": session_id}
    )


def generate_jwt_token(user_id: str, email: str, roles: List[str], 
                      tenant_id: Optional[str] = None) -> str:
    """
    Generate JWT token for testing purposes
    DO NOT use in production - tokens should come from auth service
    """
    if not settings.ENVIRONMENT == "development":
        raise ValueError("Token generation only available in development")
    
    payload = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "tenant_id": tenant_id,
        "iat": int(time.time()),
        "exp": int(time.time() + (settings.JWT_EXPIRES_HOURS * 3600))
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
