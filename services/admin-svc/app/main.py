"""
AIVO Admin Service - S4-17 Implementation
Internal admin backoffice with strict RBAC and audit logging.
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
import logging
import time
from contextlib import asynccontextmanager

from app.auth import verify_admin_token, AdminUser
from app.routes import system, approvals, queues, support, audit
from app.middleware import AuditMiddleware, SecurityHeadersMiddleware
from app.database import init_db, close_db
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting AIVO Admin Service")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down AIVO Admin Service")
    await close_db()
    logger.info("Database connections closed")


# FastAPI app
app = FastAPI(
    title="AIVO Admin Service",
    description="Internal admin backoffice with strict RBAC and audit logging",
    version="1.0.0",
    docs_url="/admin/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/admin/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# CORS middleware (restricted for admin interface)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "admin-svc",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness probe"""
    try:
        # Check database connectivity
        from app.database import get_db
        async with get_db() as db:
            await db.execute("SELECT 1")
        
        return {
            "status": "ready",
            "checks": {
                "database": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/admin/status")
async def admin_status(admin: AdminUser = Depends(verify_admin_token)):
    """Admin service status - requires authentication"""
    return {
        "status": "operational",
        "admin_user": {
            "user_id": admin.user_id,
            "email": admin.email,
            "roles": admin.roles,
            "tenant_id": admin.tenant_id
        },
        "permissions": {
            "system_monitor": admin.has_role("staff"),
            "queue_management": admin.has_role("tenant_admin"),
            "system_admin": admin.has_role("system_admin"),
            "audit_access": admin.has_role("staff")
        }
    }


# Include route modules
app.include_router(
    system.router,
    prefix="/admin",
    tags=["System"],
    dependencies=[Depends(verify_admin_token)]
)

app.include_router(
    approvals.router,
    prefix="/admin",
    tags=["Approvals"],
    dependencies=[Depends(verify_admin_token)]
)

app.include_router(
    queues.router,
    prefix="/admin",
    tags=["Queues"],
    dependencies=[Depends(verify_admin_token)]
)

app.include_router(
    support.router,
    prefix="/admin",
    tags=["Support"],
    dependencies=[Depends(verify_admin_token)]
)

app.include_router(
    audit.router,
    prefix="/admin",
    tags=["Audit"],
    dependencies=[Depends(verify_admin_token)]
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with audit logging"""
    logger.warning(
        f"HTTP {exc.status_code} - {exc.detail} - "
        f"Path: {request.url.path} - IP: {request.client.host}"
    )
    
    # Log security-related errors
    if exc.status_code in [401, 403, 404]:
        from app.audit import log_security_event
        await log_security_event(
            event_type="access_denied",
            details={
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "ip_address": request.client.host,
                "user_agent": request.headers.get("user-agent"),
                "detail": exc.detail
            }
        )
    
    return {
        "error": True,
        "status_code": exc.status_code,
        "detail": exc.detail,
        "timestamp": time.time()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Log system errors
    from app.audit import log_system_event
    await log_system_event(
        event_type="system_error",
        details={
            "error": str(exc),
            "path": str(request.url.path),
            "ip_address": request.client.host
        }
    )
    
    return {
        "error": True,
        "status_code": 500,
        "detail": "Internal server error",
        "timestamp": time.time()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8020,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
