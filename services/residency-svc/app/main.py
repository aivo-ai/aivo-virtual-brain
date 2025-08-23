"""
Data Residency Service
Enforces region pinning for storage and inference routing
"""

import structlog
import uvicorn
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from app.config import settings
from app.routes import router
from app.inference_routing import inference_router
from app.models import init_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info(
        "Data Residency Service starting up",
        version="1.0.0",
        environment=settings.environment,
        supported_regions=settings.supported_regions
    )
    
    # Initialize database
    await init_db()
    
    logger.info("Data Residency Service startup complete")
    yield
    
    # Shutdown
    logger.info("Data Residency Service shutting down")


# Create FastAPI application
app = FastAPI(
    title="Data Residency Service",
    description="Enforces region pinning for storage and inference routing",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Region", "X-Data-Location"]
)

# Include API routes
app.include_router(router)
app.include_router(inference_router)


@app.middleware("http")
async def region_enforcement_middleware(request: Request, call_next):
    """
    Middleware to enforce region-based request routing and data residency
    """
    # Extract region from headers or resolve from request
    region = request.headers.get("X-Region")
    tenant_id = request.headers.get("X-Tenant-ID")
    
    # Add region context to request
    request.state.region = region
    request.state.tenant_id = tenant_id
    
    response = await call_next(request)
    
    # Add region headers to response
    if hasattr(request.state, "resolved_region"):
        response.headers["X-Region"] = request.state.resolved_region
        response.headers["X-Data-Location"] = request.state.resolved_region
    
    return response


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with region context"""
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        region=getattr(request.state, "region", None),
        tenant_id=getattr(request.state, "tenant_id", None),
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "region": getattr(request.state, "resolved_region", None)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        region=getattr(request.state, "region", None),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error", 
            "path": request.url.path,
            "region": getattr(request.state, "resolved_region", None)
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Service health check"""
    return {
        "status": "healthy",
        "service": "residency-svc",
        "version": "1.0.0",
        "supported_regions": settings.supported_regions,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
