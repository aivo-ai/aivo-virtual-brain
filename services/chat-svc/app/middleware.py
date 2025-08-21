"""
Chat Service Middleware
Authentication, CORS, and security middleware
"""

import time
import logging
import uuid
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
import jwt
from datetime import datetime

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


def setup_cors(app: FastAPI) -> None:
    """
    Setup CORS middleware for the application
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )


def setup_logging(app: FastAPI) -> None:
    """
    Setup request logging middleware
    """
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        # Add request ID to state
        request.state.request_id = request_id
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            raise


def setup_auth_middleware(app: FastAPI) -> None:
    """
    Setup authentication middleware
    """
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # Skip auth for health checks and docs
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Extract and validate JWT token
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_jwt_token(token)
                if payload:
                    # Add user context to request state
                    request.state.user_id = payload.get("sub")
                    request.state.tenant_id = payload.get("tenant_id")
                    request.state.learner_scope = payload.get("learner_scope", [])
                    request.state.role = payload.get("role")
                    request.state.permissions = payload.get("permissions", [])
            except Exception as e:
                logger.warning(f"Token validation failed: {e}")
        
        return await call_next(request)


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            logger.warning("Token has expired")
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get current user from request state
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return {
        "user_id": user_id,
        "tenant_id": getattr(request.state, "tenant_id"),
        "learner_scope": getattr(request.state, "learner_scope", []),
        "role": getattr(request.state, "role"),
        "permissions": getattr(request.state, "permissions", []),
    }


def get_tenant_id(request: Request) -> str:
    """
    Get tenant ID from request state
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required"
        )
    return tenant_id


def check_learner_access(request: Request, learner_id: str) -> bool:
    """
    Check if user has access to the specified learner
    """
    learner_scope = getattr(request.state, "learner_scope", [])
    role = getattr(request.state, "role", "")
    
    # Admins have access to all learners
    if role in ["admin", "super_admin"]:
        return True
    
    # Check if learner is in scope
    if learner_id in learner_scope:
        return True
    
    # Teachers and guardians might have wildcard access
    if role in ["teacher", "guardian"] and "*" in learner_scope:
        return True
    
    return False


def require_permission(permission: str):
    """
    Decorator to require specific permission
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user = get_current_user(request)
            permissions = user.get("permissions", [])
            
            if permission not in permissions and "admin" not in user.get("role", ""):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_learner_access(request: Request, learner_id: str) -> None:
    """
    Validate that the user has access to the specified learner
    Raises HTTPException if access is denied
    """
    if not check_learner_access(request, learner_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Insufficient permissions for this learner"
        )


def get_request_context(request: Request) -> Dict[str, Any]:
    """
    Get full request context for logging and auditing
    """
    return {
        "request_id": getattr(request.state, "request_id", None),
        "user_id": getattr(request.state, "user_id", None),
        "tenant_id": getattr(request.state, "tenant_id", None),
        "learner_scope": getattr(request.state, "learner_scope", []),
        "role": getattr(request.state, "role", None),
        "permissions": getattr(request.state, "permissions", []),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "method": request.method,
        "path": request.url.path,
    }


# Rate limiting middleware (basic implementation)
class RateLimiter:
    """
    Simple in-memory rate limiter
    In production, use Redis-based rate limiting
    """
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed based on rate limit
        """
        now = time.time()
        window_start = now - window
        
        # Clean old entries
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
        else:
            self.requests[key] = []
        
        # Check limit
        if len(self.requests[key]) >= limit:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Setup rate limiting middleware
    """
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Use IP address as rate limit key
        client_ip = request.client.host if request.client else "unknown"
        
        # Apply rate limit
        if not rate_limiter.is_allowed(
            key=client_ip,
            limit=settings.rate_limit_requests_per_minute,
            window=60  # 1 minute
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        return await call_next(request)
