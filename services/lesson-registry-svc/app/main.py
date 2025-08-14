"""
Lesson Registry Service - Main FastAPI Application

Educational content management system with versioning, asset management,
and CDN-signed delivery for secure lesson distribution.
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.exc import SQLAlchemyError

from .database import engine, Base, get_db
from .routes import router
from .config import get_settings
from .middleware import request_id_middleware, error_handling_middleware
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown tasks."""
    try:
        # Create database tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialization complete")
        
        # Additional startup tasks
        settings = get_settings()
        logger.info(f"Starting Lesson Registry Service on port {settings.port}")
        logger.info(f"Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url}")
        logger.info(f"CDN Type: {settings.cdn_config.get('type', 'minio')}")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        logger.info("Lesson Registry Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Lesson Registry Service",
    description="""
    Educational Content Management System with versioning and CDN delivery.
    
    ## Features
    
    * **Lesson Management**: Create and organize educational content
    * **Version Control**: Semantic versioning for content iterations  
    * **Asset Management**: File upload and integrity validation
    * **CDN Signing**: Secure, time-limited asset URLs
    * **Role-Based Access**: Permission control for different user types
    * **Manifest Generation**: Complete lesson packages with signed URLs
    
    ## Roles & Permissions
    
    * **subject_brain**: Full content creation and management
    * **teacher**: Metadata updates and content access
    * **parent/student**: Read-only access to published content
    * **admin**: Full system access
    
    ## Version Format
    
    Uses semantic versioning (major.minor.patch) for content versions.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add custom middleware
app.middleware("http")(request_id_middleware)
app.middleware("http")(error_handling_middleware)

# Include API routes
app.include_router(router)


# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "lesson-registry",
        "version": "1.0.0",
        "timestamp": "2025-08-14T00:00:00Z"
    }


@app.get("/health/detailed", tags=["health"])
async def detailed_health_check(db = Depends(get_db)):
    """Detailed health check with database connectivity."""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Test CDN signer configuration
    try:
        from .signer import create_signer_from_config
        signer = create_signer_from_config(settings.cdn_config)
        cdn_status = "configured"
    except Exception as e:
        logger.error(f"CDN signer health check failed: {e}")
        cdn_status = "misconfigured"
    
    health_data = {
        "service": "lesson-registry",
        "version": "1.0.0",
        "status": "healthy" if db_status == "healthy" and cdn_status == "configured" else "degraded",
        "checks": {
            "database": db_status,
            "cdn_signer": cdn_status
        },
        "timestamp": "2025-08-14T00:00:00Z"
    }
    
    status_code = 200 if health_data["status"] == "healthy" else 503
    return JSONResponse(content=health_data, status_code=status_code)


# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with consistent error format."""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Database error handler."""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    logger.error(f"Database error in request {request_id}: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "DatabaseError", 
            "message": "Internal database error occurred",
            "request_id": request_id,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Value error handler for invalid input."""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "ValidationError",
            "message": str(exc),
            "request_id": request_id,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    """Permission error handler for authorization failures."""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    return JSONResponse(
        status_code=403,
        content={
            "error": "PermissionDenied",
            "message": str(exc),
            "request_id": request_id,
            "path": str(request.url.path)
        }
    )


# OpenAPI customization
def custom_openapi():
    """Custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Lesson Registry API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Add common response schemas
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "error": {"type": "string"},
            "message": {"type": "string"},
            "status_code": {"type": "integer"},
            "request_id": {"type": "string"},
            "path": {"type": "string"}
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Development and debugging endpoints
@app.get("/debug/config", tags=["debug"], include_in_schema=False)
async def debug_config():
    """Debug endpoint to view configuration (development only)."""
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not found")
    
    return {
        "environment": settings.environment,
        "database_url": settings.database_url.split('@')[1] if '@' in settings.database_url else "****",
        "cdn_type": settings.cdn_config.get('type'),
        "cors_origins": settings.cors_origins,
        "port": settings.port
    }


@app.get("/debug/signer", tags=["debug"], include_in_schema=False)
async def debug_signer():
    """Debug endpoint to test CDN signer configuration."""
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not found")
    
    try:
        from .signer import create_signer_from_config
        signer = create_signer_from_config(settings.cdn_config)
        
        # Test signing with dummy data
        test_result = signer.sign_url("test/asset.png", "teacher", 300)
        
        return {
            "signer_type": type(signer).__name__,
            "test_signing": "success",
            "expires_in": "300 seconds",
            "sample_url_length": len(test_result["signed_url"])
        }
    except Exception as e:
        return {
            "signer_type": "error",
            "test_signing": "failed",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level="info"
    )
