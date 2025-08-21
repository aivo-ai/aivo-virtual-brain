"""
Middleware for AIVO Admin Service
Security headers, audit logging, and request tracking
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import logging

from app.audit import log_admin_action, extract_request_info

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Admin service specific headers
        response.headers["X-Admin-Service"] = "aivo-admin-svc"
        response.headers["X-Audit-Required"] = "true"
        
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """Log all admin service requests for audit trail"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract request information
        request_info = extract_request_info(request)
        
        # Skip audit logging for health checks and static assets
        skip_paths = ["/health", "/ready", "/metrics", "/favicon.ico"]
        should_audit = not any(request.url.path.startswith(path) for path in skip_paths)
        
        if should_audit:
            # Log request start
            logger.info(
                f"REQUEST_START: {request.method} {request.url.path} - "
                f"ID: {request_id} - IP: {request_info.get('ip_address')}"
            )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
            
            if should_audit:
                # Log request completion
                logger.info(
                    f"REQUEST_COMPLETE: {request.method} {request.url.path} - "
                    f"Status: {response.status_code} - Time: {process_time:.3f}s - "
                    f"ID: {request_id}"
                )
                
                # Log to audit system for admin endpoints
                if request.url.path.startswith("/admin"):
                    try:
                        # Extract user ID from token if available
                        user_id = getattr(request.state, "user_id", None)
                        
                        await log_admin_action(
                            user_id=user_id or "anonymous",
                            action_type="api_request",
                            details={
                                "method": request.method,
                                "path": str(request.url.path),
                                "status_code": response.status_code,
                                "process_time_ms": round(process_time * 1000, 2),
                                "request_id": request_id,
                                "query_params": dict(request.query_params),
                                "user_agent": request_info.get("user_agent")
                            },
                            success=response.status_code < 400,
                            ip_address=request_info.get("ip_address"),
                            user_agent=request_info.get("user_agent")
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log admin request audit: {e}")
            
            return response
            
        except Exception as e:
            # Calculate processing time for error case
            process_time = time.time() - start_time
            
            if should_audit:
                logger.error(
                    f"REQUEST_ERROR: {request.method} {request.url.path} - "
                    f"Error: {str(e)} - Time: {process_time:.3f}s - ID: {request_id}"
                )
                
                # Log error to audit system
                if request.url.path.startswith("/admin"):
                    try:
                        user_id = getattr(request.state, "user_id", None)
                        
                        await log_admin_action(
                            user_id=user_id or "anonymous",
                            action_type="api_request_error",
                            details={
                                "method": request.method,
                                "path": str(request.url.path),
                                "error": str(e),
                                "process_time_ms": round(process_time * 1000, 2),
                                "request_id": request_id
                            },
                            success=False,
                            ip_address=request_info.get("ip_address"),
                            user_agent=request_info.get("user_agent")
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to log error audit: {audit_error}")
            
            # Re-raise the exception
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting for admin endpoints"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        current_minute = int(time.time() // 60)
        key = f"{client_ip}:{current_minute}"
        
        # Check request count
        current_count = self.request_counts.get(key, 0)
        
        if current_count >= self.requests_per_minute:
            logger.warning(
                f"RATE_LIMIT_EXCEEDED: IP {client_ip} - "
                f"Count: {current_count}/{self.requests_per_minute}"
            )
            
            # Log rate limit violation
            try:
                from app.audit import log_security_event
                await log_security_event(
                    event_type="rate_limit_exceeded",
                    details={
                        "ip_address": client_ip,
                        "request_count": current_count,
                        "limit": self.requests_per_minute,
                        "path": str(request.url.path)
                    },
                    ip_address=client_ip
                )
            except Exception as e:
                logger.warning(f"Failed to log rate limit audit: {e}")
            
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please slow down your requests."
            )
        
        # Increment counter
        self.request_counts[key] = current_count + 1
        
        # Clean up old entries (simple cleanup)
        cutoff_time = current_minute - 5  # Keep last 5 minutes
        keys_to_remove = [k for k in self.request_counts.keys() 
                         if int(k.split(":")[1]) < cutoff_time]
        for k in keys_to_remove:
            del self.request_counts[k]
        
        return await call_next(request)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Track admin user requests for session management"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Process request
        response = await call_next(request)
        
        # Update admin session activity if authenticated
        if hasattr(request.state, "admin_user"):
            admin_user = request.state.admin_user
            
            try:
                # Update session last activity in Redis
                from app.database import get_redis
                redis = await get_redis()
                
                if hasattr(admin_user, "session_id") and admin_user.session_id:
                    session_key = f"admin_session:{admin_user.session_id}"
                    # Update last activity timestamp
                    await redis.hset(session_key, "last_activity", str(time.time()))
                    
            except Exception as e:
                logger.warning(f"Failed to update session activity: {e}")
        
        return response


class AdminContextMiddleware(BaseHTTPMiddleware):
    """Add admin context to requests for audit logging"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Try to extract admin user from authorization header
        auth_header = request.headers.get("authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.auth import verify_admin_token
                from fastapi.security import HTTPAuthorizationCredentials
                
                # Create credentials object
                credentials = HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials=auth_header.split(" ")[1]
                )
                
                # Verify token (this will raise exception if invalid)
                admin_user = await verify_admin_token(credentials)
                
                # Store admin user in request state
                request.state.admin_user = admin_user
                request.state.user_id = admin_user.user_id
                
            except Exception as e:
                # Don't fail the request, just log the issue
                logger.debug(f"Could not extract admin context: {e}")
        
        return await call_next(request)


# Middleware factory functions

def create_security_middleware():
    """Create security headers middleware"""
    return SecurityHeadersMiddleware


def create_audit_middleware():
    """Create audit logging middleware"""
    return AuditMiddleware


def create_rate_limit_middleware(requests_per_minute: int = 60):
    """Create rate limiting middleware"""
    def factory(app):
        return RateLimitMiddleware(app, requests_per_minute)
    return factory


def create_request_tracking_middleware():
    """Create request tracking middleware"""
    return RequestTrackingMiddleware


def create_admin_context_middleware():
    """Create admin context middleware"""
    return AdminContextMiddleware
