"""
Main FastAPI application for Coursework Ingest Service.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from .routers import upload_router
from .models import HealthCheckResponse
from .ocr import ocr_service
from .topic_map import topic_mapping_service

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    
    # Startup
    logger.info("Starting Coursework Ingest Service")
    
    # Verify OCR providers
    ocr_status = ocr_service.get_provider_status()
    logger.info("OCR providers initialized", providers=ocr_status)
    
    # Verify topic mapping
    classification_stats = topic_mapping_service.get_classification_stats()
    logger.info("Topic mapping initialized", stats=classification_stats)
    
    logger.info("Coursework Ingest Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Coursework Ingest Service")


# Create FastAPI app
app = FastAPI(
    title="Coursework Ingest Service",
    description="Service for uploading, processing, and analyzing educational coursework via OCR and topic mapping",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    
    # Check OCR providers
    ocr_status = ocr_service.get_provider_status()
    ocr_providers = {
        provider: status["available"] 
        for provider, status in ocr_status.items()
    }
    
    # Check dependencies
    dependencies = {
        "ocr_service": "healthy" if any(ocr_providers.values()) else "unhealthy",
        "topic_mapping": "healthy",
        "storage": "healthy"  # Mock storage always healthy
    }
    
    overall_status = "healthy" if all(
        status == "healthy" for status in dependencies.values()
    ) else "unhealthy"
    
    return HealthCheckResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        dependencies=dependencies,
        ocr_providers=ocr_providers
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with comprehensive status."""
    
    ocr_status = ocr_service.get_provider_status()
    classification_stats = topic_mapping_service.get_classification_stats()
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "ocr": {
                "status": "healthy",
                "providers": ocr_status,
                "available_providers": [
                    provider for provider, status in ocr_status.items()
                    if status["available"]
                ]
            },
            "topic_mapping": {
                "status": "healthy",
                "classification_stats": classification_stats,
                "supported_subjects": topic_mapping_service.get_supported_subjects(),
                "supported_topics": topic_mapping_service.get_supported_topics()
            },
            "storage": {
                "status": "healthy",
                "type": "mock",
                "bucket": "coursework-uploads"
            }
        },
        "configuration": {
            "max_file_size_mb": 50,
            "supported_file_types": ["pdf", "jpeg", "png", "webp"],
            "default_ocr_provider": "tesseract"
        }
    }


# Include routers
app.include_router(upload_router)


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    
    logger.error("Unhandled exception", 
                path=request.url.path,
                method=request.method,
                error=str(exc),
                exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    
    return {
        "service": "Coursework Ingest Service",
        "version": "1.0.0",
        "description": "Upload and analyze educational coursework with OCR and topic mapping",
        "endpoints": {
            "upload": "/v1/upload",
            "analysis": "/v1/analysis/{upload_id}",
            "health": "/health",
            "docs": "/docs"
        },
        "features": [
            "Multi-format file upload (PDF, images)",
            "Multiple OCR providers (Tesseract, Vision API, Textract)",
            "Automatic subject/topic classification",
            "Difficulty level estimation",
            "Event emission on completion",
            "Real-time processing status"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    # Development server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_config=None,  # Use structlog configuration
    )
