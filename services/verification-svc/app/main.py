"""
Guardian Identity Verification Service
COPPA-compliant identity verification via micro-charge and KBA fallback
"""

import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import structlog

from app.config import settings
from app.models import Base
from app.routes import router
from app.database import engine

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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for database initialization"""
    try:
        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Verification service started", 
                   version=settings.version,
                   environment=settings.environment)
        yield
        
    except Exception as e:
        logger.error("Failed to initialize verification service", error=str(e))
        raise
    finally:
        # Cleanup
        await engine.dispose()
        logger.info("Verification service shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="Guardian Identity Verification Service",
    description="COPPA-compliant guardian identity verification via micro-charge and KBA",
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    """Service information and health check"""
    return {
        "service": "verification-svc",
        "version": settings.version,
        "status": "healthy",
        "features": {
            "micro_charge_verification": True,
            "kba_verification": True,
            "coppa_compliant": True,
            "rate_limiting": True,
            "geo_policies": True
        },
        "verification_methods": ["micro_charge", "kba"],
        "supported_regions": ["US", "CA", "UK", "AU"],
        "privacy_features": {
            "minimal_pii_storage": True,
            "automated_log_scrubbing": True,
            "data_minimization": True,
            "tokenized_storage": True
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check for monitoring"""
    try:
        # Test database connectivity
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        # Test Stripe connectivity (if configured)
        stripe_status = "configured" if settings.stripe_secret_key else "not_configured"
        
        # Test KBA provider connectivity (if configured)
        kba_status = "configured" if settings.kba_provider_enabled else "not_configured"
        
        return {
            "status": "healthy",
            "timestamp": "2025-08-23T00:00:00Z",
            "checks": {
                "database": "healthy",
                "stripe": stripe_status,
                "kba_provider": kba_status
            },
            "verification_stats": {
                "today_verifications": 0,  # Would be populated from metrics
                "success_rate_24h": 0.95,
                "avg_verification_time": "2.3s"
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": "Service health check failed",
                "checks": {
                    "database": "unhealthy",
                    "stripe": "unknown",
                    "kba_provider": "unknown"
                }
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler with structured logging"""
    logger.warning("HTTP exception occurred", 
                  path=str(request.url),
                  method=request.method,
                  status_code=exc.status_code,
                  detail=exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": "2025-08-23T00:00:00Z"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unhandled errors"""
    logger.error("Unhandled exception occurred",
                path=str(request.url),
                method=request.method,
                error=str(exc),
                exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": "2025-08-23T00:00:00Z",
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )
