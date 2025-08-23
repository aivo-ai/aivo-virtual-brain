"""
Legal Hold & eDiscovery Service

FastAPI application for managing legal data preservation requirements,
eDiscovery exports, and compliance with litigation holds.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base
from .routes import (
    legal_holds_router,
    ediscovery_router,
    compliance_router,
    audit_router
)
from .config import get_settings
from .auth import get_current_user
from .exceptions import (
    LegalHoldException,
    eDiscoveryException,
    ComplianceException
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Settings
settings = get_settings()

# Database setup
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Legal Hold Service")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize background tasks
    # await initialize_retention_monitor()
    # await initialize_hold_notification_service()
    
    logger.info("Legal Hold Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Legal Hold Service")
    
    # Cleanup background tasks
    # await cleanup_background_tasks()
    
    logger.info("Legal Hold Service shut down complete")


# FastAPI app initialization
app = FastAPI(
    title="Legal Hold & eDiscovery Service",
    description="Compliance service for legal data preservation and eDiscovery exports",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None
)

# Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)


# Exception handlers
@app.exception_handler(LegalHoldException)
async def legal_hold_exception_handler(request: Request, exc: LegalHoldException):
    """Handle legal hold specific exceptions"""
    logger.error(f"Legal Hold Error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "legal_hold_error",
            "message": exc.detail,
            "error_code": getattr(exc, 'error_code', 'LEGAL_HOLD_ERROR')
        }
    )


@app.exception_handler(eDiscoveryException)
async def ediscovery_exception_handler(request: Request, exc: eDiscoveryException):
    """Handle eDiscovery specific exceptions"""
    logger.error(f"eDiscovery Error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "ediscovery_error",
            "message": exc.detail,
            "error_code": getattr(exc, 'error_code', 'EDISCOVERY_ERROR')
        }
    )


@app.exception_handler(ComplianceException)
async def compliance_exception_handler(request: Request, exc: ComplianceException):
    """Handle compliance specific exceptions"""
    logger.error(f"Compliance Error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "compliance_error",
            "message": exc.detail,
            "error_code": getattr(exc, 'error_code', 'COMPLIANCE_ERROR')
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred"
        }
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": "legal-hold-svc"}


@app.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with database connectivity"""
    try:
        # Test database connectivity
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Test external dependencies
    dependencies = {
        "database": db_status,
        "s3_storage": "healthy",  # Would test S3 connectivity
        "notification_service": "healthy"  # Would test notification service
    }
    
    overall_status = "healthy" if all(status == "healthy" for status in dependencies.values()) else "degraded"
    
    return {
        "status": overall_status,
        "service": "legal-hold-svc",
        "version": "1.0.0",
        "dependencies": dependencies,
        "timestamp": "2025-08-23T00:00:00Z"
    }


# Metrics endpoint
@app.get("/metrics")
async def get_metrics(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Service metrics for monitoring"""
    if not current_user or current_user.role not in ["admin", "compliance_officer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        from .models import LegalHold, eDiscoveryExport, HoldAuditLog
        
        # Basic metrics
        active_holds = db.query(LegalHold).filter(LegalHold.status == "active").count()
        pending_exports = db.query(eDiscoveryExport).filter(eDiscoveryExport.status == "pending").count()
        in_progress_exports = db.query(eDiscoveryExport).filter(eDiscoveryExport.status == "in_progress").count()
        
        # Audit metrics
        audit_events_today = db.query(HoldAuditLog).filter(
            HoldAuditLog.event_timestamp >= "2025-08-23T00:00:00Z"
        ).count()
        
        return {
            "active_holds": active_holds,
            "pending_exports": pending_exports,
            "in_progress_exports": in_progress_exports,
            "audit_events_today": audit_events_today,
            "service_uptime": "healthy"
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect metrics")


# Include routers
app.include_router(
    legal_holds_router,
    prefix="/api/v1/legal-holds",
    tags=["legal-holds"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    ediscovery_router,
    prefix="/api/v1/ediscovery",
    tags=["ediscovery"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    compliance_router,
    prefix="/api/v1/compliance",
    tags=["compliance"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    audit_router,
    prefix="/api/v1/audit",
    tags=["audit"],
    dependencies=[Depends(get_current_user)]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Legal Hold & eDiscovery Service",
        "version": "1.0.0",
        "description": "Compliance service for legal data preservation and eDiscovery exports",
        "endpoints": {
            "legal_holds": "/api/v1/legal-holds",
            "ediscovery": "/api/v1/ediscovery",
            "compliance": "/api/v1/compliance",
            "audit": "/api/v1/audit",
            "health": "/health",
            "docs": "/docs" if settings.debug else None
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
        access_log=True
    )
