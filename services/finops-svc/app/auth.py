"""
Authentication and authorization for the FinOps service.

This module provides JWT token validation, role-based access control,
and tenant-based data isolation for the FinOps API.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from functools import wraps

import jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from .config import config
from .database import get_db_session

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


class AuthenticationError(Exception):
    """Authentication-related errors."""
    pass


class AuthorizationError(Exception):
    """Authorization-related errors."""
    pass


class User:
    """User model for authentication."""
    
    def __init__(
        self,
        user_id: str,
        email: str,
        roles: List[str],
        tenant_id: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        **kwargs
    ):
        self.user_id = user_id
        self.email = email
        self.roles = roles
        self.tenant_id = tenant_id
        self.permissions = permissions or []
        self.metadata = kwargs
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def can_access_tenant(self, tenant_id: str) -> bool:
        """Check if user can access a specific tenant's data."""
        # Super admin can access all tenants
        if "super_admin" in self.roles:
            return True
        
        # System roles can access all tenants
        if "system" in self.roles or "finops_admin" in self.roles:
            return True
        
        # User can access their own tenant
        return self.tenant_id == tenant_id
    
    def can_access_learner(self, learner_id: str, tenant_id: str) -> bool:
        """Check if user can access a specific learner's data."""
        # Must be able to access the tenant first
        if not self.can_access_tenant(tenant_id):
            return False
        
        # Teachers can access learners in their tenant
        if "teacher" in self.roles:
            return True
        
        # Learners can only access their own data
        if "learner" in self.roles:
            return self.user_id == learner_id
        
        # Admins can access all learners in their tenant
        return "admin" in self.roles or "finops_admin" in self.roles


class AuthManager:
    """Manages authentication and authorization."""
    
    def __init__(self):
        self.jwt_secret = config.JWT_SECRET
        self.jwt_algorithm = config.JWT_ALGORITHM
        self.jwt_expiration = config.JWT_EXPIRATION_HOURS * 3600
        
        # Role hierarchy and permissions
        self.role_permissions = {
            "super_admin": [
                "finops:*",
                "budgets:*",
                "costs:*",
                "alerts:*",
                "pricing:*",
                "admin:*"
            ],
            "finops_admin": [
                "finops:read",
                "finops:write",
                "budgets:*",
                "costs:*",
                "alerts:*",
                "pricing:read"
            ],
            "admin": [
                "finops:read",
                "budgets:read",
                "budgets:write",
                "costs:read",
                "alerts:read",
                "alerts:acknowledge"
            ],
            "teacher": [
                "finops:read",
                "budgets:read",
                "costs:read",
                "alerts:read"
            ],
            "learner": [
                "finops:read:own",
                "costs:read:own"
            ],
            "service": [
                "finops:write",
                "usage:write"
            ]
        }
    
    async def verify_token(
        self, 
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> User:
        """Verify JWT token and return user information."""
        try:
            token = credentials.credentials
            
            # Decode JWT token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            # Extract user information
            user_id = payload.get("sub")
            email = payload.get("email")
            roles = payload.get("roles", [])
            tenant_id = payload.get("tenant_id")
            
            if not user_id or not email:
                raise AuthenticationError("Invalid token payload")
            
            # Check token expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                raise AuthenticationError("Token expired")
            
            # Get permissions for roles
            permissions = []
            for role in roles:
                permissions.extend(self.role_permissions.get(role, []))
            
            # Remove duplicates
            permissions = list(set(permissions))
            
            user = User(
                user_id=user_id,
                email=email,
                roles=roles,
                tenant_id=tenant_id,
                permissions=permissions,
                **{k: v for k, v in payload.items() if k not in ["sub", "email", "roles", "tenant_id", "exp", "iat"]}
            )
            
            logger.debug(f"Authenticated user {user_id} with roles {roles}")
            return user
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except AuthenticationError as e:
            logger.warning(f"Authentication error: {e}")
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    def require_roles(self, required_roles: List[str]):
        """Decorator to require specific roles."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Find the user parameter
                user = None
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
                
                if not user:
                    # Look in kwargs
                    user = kwargs.get("current_user")
                
                if not user:
                    raise HTTPException(status_code=401, detail="Authentication required")
                
                if not user.has_any_role(required_roles):
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Required roles: {required_roles}"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_permissions(self, required_permissions: List[str]):
        """Decorator to require specific permissions."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Find the user parameter
                user = None
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
                
                if not user:
                    user = kwargs.get("current_user")
                
                if not user:
                    raise HTTPException(status_code=401, detail="Authentication required")
                
                # Check permissions
                for permission in required_permissions:
                    if not self._check_permission(user, permission):
                        raise HTTPException(
                            status_code=403,
                            detail=f"Required permission: {permission}"
                        )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _check_permission(self, user: User, permission: str) -> bool:
        """Check if user has a specific permission."""
        # Wildcard permissions
        if "finops:*" in user.permissions or "*" in user.permissions:
            return True
        
        # Direct permission match
        if permission in user.permissions:
            return True
        
        # Wildcard matching (e.g., budgets:* allows budgets:read)
        permission_parts = permission.split(":")
        if len(permission_parts) >= 2:
            wildcard_permission = f"{permission_parts[0]}:*"
            if wildcard_permission in user.permissions:
                return True
        
        return False
    
    def check_tenant_access(self, user: User, tenant_id: str) -> bool:
        """Check if user can access tenant data."""
        if not tenant_id:
            return True  # No tenant restriction
        
        return user.can_access_tenant(tenant_id)
    
    def check_learner_access(self, user: User, learner_id: str, tenant_id: str) -> bool:
        """Check if user can access learner data."""
        if not learner_id:
            return self.check_tenant_access(user, tenant_id)
        
        return user.can_access_learner(learner_id, tenant_id)
    
    def filter_tenant_data(self, user: User, tenant_id: Optional[str]) -> Optional[str]:
        """Filter tenant ID based on user permissions."""
        # Super admins can access all data
        if user.has_any_role(["super_admin", "system", "finops_admin"]):
            return tenant_id
        
        # Other users can only access their own tenant
        if tenant_id and not user.can_access_tenant(tenant_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied to tenant data"
            )
        
        # If no tenant specified, use user's tenant
        return tenant_id or user.tenant_id
    
    def validate_data_access(
        self,
        user: User,
        tenant_id: Optional[str] = None,
        learner_id: Optional[str] = None,
        service_name: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Validate and filter data access parameters."""
        # Filter tenant access
        filtered_tenant_id = self.filter_tenant_data(user, tenant_id)
        
        # Check learner access
        if learner_id:
            if not filtered_tenant_id:
                raise HTTPException(
                    status_code=400,
                    detail="Tenant ID required for learner data access"
                )
            
            if not self.check_learner_access(user, learner_id, filtered_tenant_id):
                raise HTTPException(
                    status_code=403,
                    detail="Access denied to learner data"
                )
        
        # Service access (basic check - could be extended)
        if service_name and user.has_role("learner"):
            # Learners typically shouldn't access service-level data
            raise HTTPException(
                status_code=403,
                detail="Access denied to service-level data"
            )
        
        return filtered_tenant_id, learner_id


# Create global auth manager instance
auth_manager = AuthManager()

# FastAPI dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """FastAPI dependency to get current authenticated user."""
    return await auth_manager.verify_token(credentials)

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency to require admin user."""
    if not current_user.has_any_role(["admin", "finops_admin", "super_admin"]):
        raise HTTPException(
            status_code=403,
            detail="Admin role required"
        )
    return current_user

async def get_finops_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency to require FinOps admin user."""
    if not current_user.has_any_role(["finops_admin", "super_admin"]):
        raise HTTPException(
            status_code=403,
            detail="FinOps admin role required"
        )
    return current_user

async def get_service_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency to require service user."""
    if not current_user.has_any_role(["service", "finops_admin", "super_admin"]):
        raise HTTPException(
            status_code=403,
            detail="Service role required"
        )
    return current_user

def validate_tenant_access(tenant_id: str):
    """FastAPI dependency to validate tenant access."""
    async def _validate(current_user: User = Depends(get_current_user)) -> User:
        if not auth_manager.check_tenant_access(current_user, tenant_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied to tenant data"
            )
        return current_user
    return _validate

def validate_learner_access(learner_id: str, tenant_id: str):
    """FastAPI dependency to validate learner access."""
    async def _validate(current_user: User = Depends(get_current_user)) -> User:
        if not auth_manager.check_learner_access(current_user, learner_id, tenant_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied to learner data"
            )
        return current_user
    return _validate

# API Key authentication (for service-to-service communication)
async def verify_api_key(api_key: str) -> bool:
    """Verify API key for service-to-service authentication."""
    # This would typically check against a database or external service
    # For now, just check against configured API keys
    valid_api_keys = config.VALID_API_KEYS
    return api_key in valid_api_keys

async def get_api_key_user(api_key: str = None) -> User:
    """Get service user from API key."""
    if not api_key or not await verify_api_key(api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    # Return a service user
    return User(
        user_id="service",
        email="service@finops.internal",
        roles=["service"],
        permissions=["finops:write", "usage:write"]
    )
