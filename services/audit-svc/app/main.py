"""
Audit Service Main Application
FastAPI application for comprehensive audit logging and compliance management
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .database import init_db_pool, close_db_pool, get_db_pool
from .routes import router as audit_router
from .models import AuditEvent, AuditEventType, AuditSeverity, UserRole

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    
    logger.info("Starting Audit Service")
    
    # Initialize database
    try:
        await init_db_pool()
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    # Log startup audit event
    try:
        from .audit_logger import AuditLogger
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            action="service_start",
            resource="audit_service",
            severity=AuditSeverity.LOW,
            actor_type=UserRole.SYSTEM,
            metadata={
                "service": "audit-svc",
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development")
            }
        )
    except Exception as e:
        logger.warning("Failed to log startup event", error=str(e))
    
    yield
    
    # Cleanup
    logger.info("Shutting down Audit Service")
    
    try:
        # Log shutdown audit event
        from .audit_logger import AuditLogger
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            action="service_stop",
            resource="audit_service",
            severity=AuditSeverity.LOW,
            actor_type=UserRole.SYSTEM,
            metadata={
                "service": "audit-svc",
                "shutdown_reason": "normal"
            }
        )
    except Exception as e:
        logger.warning("Failed to log shutdown event", error=str(e))
    
    await close_db_pool()
    logger.info("Database pool closed")


# Create FastAPI application
app = FastAPI(
    title="AIVO Audit Service",
    description="""
    Comprehensive audit logging and compliance management service for AIVO platform.
    
    ## Features
    
    - **Audit Logging**: Complete who/what/when/why logging for sensitive operations
    - **Access Reviews**: Quarterly access certification and role reviews
    - **Just-In-Time Support**: Guardian-approved time-boxed support sessions
    - **Compliance Reporting**: Automated compliance dashboards and reports
    
    ## Security
    
    All endpoints require valid JWT authentication. Support session endpoints 
    require additional guardian consent verification.
    
    ## Audit Events
    
    The service logs all significant security and data access events including:
    - Data reads/writes/deletes
    - Authentication and authorization events  
    - Support session activities
    - Administrative actions
    - System configuration changes
    
    ## Access Reviews
    
    Quarterly reviews ensure proper access controls with:
    - Role-based access certification
    - Risk-based user prioritization
    - Automated revocation workflows
    - Compliance reporting
    
    ## Just-In-Time Support
    
    Support sessions provide secure, time-limited access with:
    - Guardian consent requirements
    - Read-only access controls
    - Session recording and audit trails
    - Automatic token expiration
    """,
    version="1.0.0",
    contact={
        "name": "AIVO Security Team",
        "email": "security@aivo.com",
    },
    license_info={
        "name": "Proprietary",
    },
    lifespan=lifespan
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Include routers
app.include_router(audit_router, prefix="/api/v1", tags=["audit"])


# Middleware for request auditing
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Middleware to audit API requests"""
    
    start_time = time.time()
    request_id = str(uuid4())
    
    # Add request ID to context
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log API access (async to avoid blocking)
    try:
        # Skip health check endpoints
        if request.url.path not in ["/health", "/metrics"]:
            from .audit_logger import AuditLogger
            audit_logger = AuditLogger()
            
            # Determine if this was a sensitive endpoint
            sensitive_paths = ["/audit", "/access-review", "/support-session"]
            is_sensitive = any(path in str(request.url.path) for path in sensitive_paths)
            
            if is_sensitive or response.status_code >= 400:
                asyncio.create_task(audit_logger.log_api_access(
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    duration_ms=round(process_time * 1000, 2),
                    request_id=request_id,
                    user_agent=request.headers.get("user-agent"),
                    ip_address=request.client.host if request.client else None
                ))
    except Exception as e:
        logger.warning("Failed to log API access", error=str(e), path=request.url.path)
    
    # Add security headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response


# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate JWT token"""
    
    try:
        # Import JWT validation (would be implemented separately)
        from .auth import validate_jwt_token
        
        payload = await validate_jwt_token(credentials.credentials)
        return payload
        
    except Exception as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with audit logging"""
    
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        request_id=getattr(request.state, 'request_id', None)
    )
    
    # Log security exception
    try:
        from .audit_logger import AuditLogger
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            action="system_error",
            resource="audit_service",
            outcome="error",
            severity=AuditSeverity.HIGH,
            reason=str(exc),
            metadata={
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__
            }
        )
    except Exception as audit_error:
        logger.error("Failed to log exception audit event", error=str(audit_error))
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, 'request_id', None),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "service": "audit-svc",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get basic audit metrics
            total_events = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_events WHERE timestamp >= NOW() - INTERVAL '24 hours'"
            )
            
            critical_events = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_events WHERE severity = 'critical' AND timestamp >= NOW() - INTERVAL '24 hours'"
            )
            
            active_sessions = await conn.fetchval(
                "SELECT COUNT(*) FROM support_sessions WHERE status = 'active'"
            )
            
            pending_reviews = await conn.fetchval(
                "SELECT COUNT(*) FROM access_reviews WHERE status = 'pending'"
            )
        
        return {
            "audit_events_24h": total_events,
            "critical_events_24h": critical_events,
            "active_support_sessions": active_sessions,
            "pending_access_reviews": pending_reviews,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Metrics collection failed", error=str(e))
        return {
            "error": "Failed to collect metrics",
            "timestamp": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    import time
    import asyncio
    from uuid import uuid4
    from datetime import datetime
    
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
